#!/usr/bin/env python3
"""Fetch a job description as plain text from a public ATS posting URL.

Most career sites are JavaScript apps, so scraping the page gives you nothing.
But the big applicant-tracking systems all expose the same posting through a
public JSON endpoint. This script recognizes the URL, calls that endpoint, and
prints the title, location, whether the posting is still open, and the JD text.

Supported: Greenhouse, Ashby, Lever, Workday, Oracle Recruiting Cloud,
SmartRecruiters. Anything else falls back to stripping the HTML.

    python3 fetch_jd.py "<posting url>"            # text to stdout
    python3 fetch_jd.py "<posting url>" --json     # machine-readable

Exit code 0 = fetched, 2 = posting not found / closed, 1 = other error.
Standard library only.
"""
import html
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

UA = 'Mozilla/5.0 (compatible; jd-resume-tailor/1.0)'


def get(url, headers=None):
    req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept': 'application/json', **(headers or {})})
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read().decode('utf-8', 'replace'), r.geturl()


def get_json(url, headers=None):
    body, _ = get(url, headers)
    return json.loads(body)


def text(s):
    s = html.unescape(s or '')
    s = re.sub(r'<(br|/p|/li|/h\d|/div)[^>]*>', '\n', s, flags=re.I)
    s = re.sub(r'<li[^>]*>', '\n- ', s, flags=re.I)
    s = re.sub(r'<[^>]+>', ' ', s)
    s = re.sub(r'[ \t\xa0]+', ' ', s)
    return re.sub(r'\n\s*\n+', '\n\n', s).strip()


def resolve(url):
    """Follow redirects (short links, referral links) to the real posting URL."""
    try:
        _, final = get(url, {'Accept': 'text/html'})
        return final
    except Exception:
        return url


# ---------------------------------------------------------------- per-ATS fetchers
def greenhouse(url):
    q = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
    jid = (q.get('gh_jid') or q.get('token') or [None])[0]
    m = re.search(r'greenhouse\.io/(?:embed/job_app\?for=)?([\w-]+)/jobs/(\d+)', url)
    board = m.group(1) if m else None
    jid = jid or (m.group(2) if m else None)
    if not jid:
        return None
    boards = [board] if board else []
    # gh_jid links on company domains don't name the board; try the company name from the host
    host = urllib.parse.urlparse(url).hostname or ''
    if 'greenhouse.io' in host and not board:
        # token-only embed links: the page itself names the board as "for=<board>"
        try:
            page, _ = get(url, {'Accept': 'text/html'})
            boards += sorted(set(re.findall(r'for=([a-z0-9_-]+)', page)))
        except Exception:  # noqa: BLE001
            pass
    boards += [p for p in host.split('.') if p not in ('www', 'careers', 'jobs', 'com', 'io', 'boards', 'job-boards', 'greenhouse')]
    for b in boards:
        try:
            d = get_json(f'https://boards-api.greenhouse.io/v1/boards/{b}/jobs/{jid}')
            return dict(ats='greenhouse', title=d['title'], location=(d.get('location') or {}).get('name'),
                        open=True, text=text(d.get('content')))
        except urllib.error.HTTPError:
            continue
    return dict(ats='greenhouse', open=False, title=None, location=None, text='')


def ashby(url):
    m = re.search(r'ashbyhq\.com/([\w.-]+)/([0-9a-f-]{36})', url)
    if not m:
        return None
    org, jid = m.groups()
    d = get_json(f'https://api.ashbyhq.com/posting-api/job-board/{org}')
    for j in d.get('jobs', []):
        if j['id'] == jid:
            return dict(ats='ashby', title=j['title'], location=j.get('location'), open=True,
                        text=j.get('descriptionPlain') or text(j.get('descriptionHtml')))
    return dict(ats='ashby', open=False, title=None, location=None, text='')


def lever(url):
    m = re.search(r'lever\.co/([\w.-]+)/([0-9a-f-]{36})', url)
    if not m:
        return None
    org, jid = m.groups()
    try:
        d = get_json(f'https://api.lever.co/v0/postings/{org}/{jid}')
    except urllib.error.HTTPError:
        return dict(ats='lever', open=False, title=None, location=None, text='')
    lists = '\n\n'.join(f"{l['text']}\n{text(l['content'])}" for l in d.get('lists', []))
    return dict(ats='lever', title=d['text'], location=(d.get('categories') or {}).get('location'), open=True,
                text=d.get('descriptionPlain', '') + '\n\n' + lists + '\n\n' + d.get('additionalPlain', ''))


def workday(url):
    m = re.search(r'https://([\w-]+)\.(wd\d+)\.myworkdayjobs\.com/(?:[a-z]{2}-[A-Z]{2}/)?([\w-]+)/job/(.+?)(?:\?|$)', url)
    if not m:
        return None
    tenant, wd, site, path = m.groups()
    try:
        d = get_json(f'https://{tenant}.{wd}.myworkdayjobs.com/wday/cxs/{tenant}/{site}/job/{path}')
    except urllib.error.HTTPError:
        return dict(ats='workday', open=False, title=None, location=None, text='')
    j = d['jobPostingInfo']
    return dict(ats='workday', title=j['title'], location=j.get('location'), open=bool(j.get('canApply', True)),
                posted=j.get('startDate'), text=text(j.get('jobDescription')))


def oracle(url):
    m = re.search(r'https://([\w.-]+\.oraclecloud\.com)/hcmUI/CandidateExperience/[a-z]{2}/sites/([\w-]+)/job/(\d+)', url)
    if not m:
        return None
    host, site, jid = m.groups()
    api = (f'https://{host}/hcmRestApi/resources/latest/recruitingCEJobRequisitionDetails'
           f'?expand=all&onlyData=true&finder=ById;Id=%22{jid}%22,siteNumber={site}')
    items = get_json(api).get('items') or []
    if not items:
        return dict(ats='oracle', open=False, title=None, location=None, text='')
    j = items[0]
    body = '\n\n'.join(text(j.get(k)) for k in ('ExternalDescriptionStr', 'ExternalResponsibilitiesStr',
                                               'ExternalQualificationsStr') if j.get(k))
    locs = [j.get('PrimaryLocation')] + [l.get('Name') for l in j.get('secondaryLocations') or []]
    return dict(ats='oracle', title=j['Title'], location=' / '.join(l for l in locs if l), open=True, text=body)


def smartrecruiters(url):
    m = re.search(r'smartrecruiters\.com/([\w-]+)/(\d+)', url)
    if not m:
        return None
    co, jid = m.groups()
    try:
        d = get_json(f'https://api.smartrecruiters.com/v1/companies/{co}/postings/{jid}')
    except urllib.error.HTTPError:
        return dict(ats='smartrecruiters', open=False, title=None, location=None, text='')
    sec = (d.get('jobAd') or {}).get('sections') or {}
    body = '\n\n'.join(f"{v.get('title', '')}\n{text(v.get('text'))}" for v in sec.values() if isinstance(v, dict))
    loc = d.get('location') or {}
    return dict(ats='smartrecruiters', title=d.get('name'), location=', '.join(filter(None, [loc.get('city'), loc.get('region')])),
                open=bool(d.get('active', True)), text=body)


def generic(url):
    body, _ = get(url, {'Accept': 'text/html'})
    t = re.search(r'<title>(.*?)</title>', body, re.S | re.I)
    body = re.sub(r'<(script|style)[^>]*>.*?</\1>', ' ', body, flags=re.S | re.I)
    return dict(ats='html', title=text(t.group(1)) if t else None, location=None, open=None, text=text(body)[:20000])


FETCHERS = [ashby, lever, workday, oracle, smartrecruiters, greenhouse]


def fetch(url):
    candidates = [url]
    final = resolve(url)
    if final != url:
        candidates.append(final)
    for u in candidates:
        for f in FETCHERS:
            try:
                r = f(u)
            except Exception as e:  # noqa: BLE001 - try the next strategy
                r = None
                last_err = e
            if r:
                r['url'] = u
                return r
    r = generic(final)
    r['url'] = final
    return r


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    try:
        r = fetch(sys.argv[1])
    except Exception as e:  # noqa: BLE001
        print(f'error: {e}', file=sys.stderr)
        sys.exit(1)
    if '--json' in sys.argv:
        print(json.dumps(r, ensure_ascii=False, indent=1))
    else:
        state = {True: 'OPEN', False: 'NOT FOUND / CLOSED', None: 'unknown (plain HTML)'}[r.get('open')]
        print(f"[{r['ats']}] {r.get('title')} | {r.get('location')} | {state}\n{r['url']}\n")
        print(r.get('text', ''))
    sys.exit(2 if r.get('open') is False else 0)


if __name__ == '__main__':
    main()
