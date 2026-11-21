"""Run the app's flow on a made-up person against real public JDs, and keep everything for the demo.

    python3 app/eval/run_eval.py [--only slug] [--mode quick|thorough]

Each JD gets a fresh copy of the example bank (builder/example/resume.toml, a fictional candidate),
so runs don't affect each other. Results go to app/eval/results/<slug>/ and app/eval/RESULTS.md.
Uses your logged-in Claude Code (Opus by default). Never reads your own config or bank.
"""
import argparse, json, os, re, shutil, subprocess, sys, tempfile, time
from pathlib import Path

APP = Path(__file__).resolve().parent.parent
REPO = APP.parent
OUT = APP / 'eval' / 'results'
JDS = [
    ('snowflake-db', 'https://jobs.ashbyhq.com/snowflake/0223923d-4f0f-44e6-9649-0d1a9eda950d', 'strong fit: databases and storage'),
    ('airbnb-swe', 'https://careers.airbnb.com/positions/8360478?gh_jid=8360478', 'general software engineering'),
    ('roblox-engine', 'https://careers.roblox.com/jobs/8386080?gh_jid=8386080', 'stretch: C++ engine work the bank does not show'),
    ('anduril-ml', 'https://boards.greenhouse.io/andurilindustries/jobs/5274037007', 'eligibility: defense, likely US-person rules'),
    ('octaura-data', 'https://job-boards.greenhouse.io/octaura/jobs/4662934007', 'data engineering'),
]
KEEP = ['jd.md', 'analysis.md', 'notes.md', 'resume_source.md', 'resume.pdf', 'writer.json', 'result.json', 'state.json',
        'bank_changes.diff', 'check.json', 'check0.json', 'check1.json', 'check2.json', 'check3.json']


def fetch(url):
    p = subprocess.run([sys.executable, '-I', str(REPO / 'skills/jd-resume-tailor/fetch_jd.py'), url, '--json'],
                       capture_output=True, text=True, timeout=120)
    if p.returncode:
        raise RuntimeError(f'fetch failed ({p.returncode}): {(p.stderr or p.stdout)[-300:]}')
    return json.loads(p.stdout)


HEADINGS = {'EDUCATION', 'EXPERIENCE', 'PROJECTS', 'SKILLS', 'TECHNICAL', 'SUMMARY', 'AWARDS', 'PUBLICATIONS', 'LEADERSHIP'}


def tokens(text):
    out = set()
    for t in re.findall(r'[A-Za-z][A-Za-z0-9+#.\-]*[A-Za-z0-9+#]|[A-Za-z]', text):
        out.add(t.lower())
        out.update(x.lower() for x in re.split(r'[-/.]', t) if x)  # "CRC-checked" also counts as "CRC"
    return out


def audit(bank_text, final_text):
    """Numbers and technical-looking words on the page that the bank never contains."""
    have_n = set(n.replace(',', '') for n in re.findall(r'\d[\d,]*(?:\.\d+)?', bank_text))
    new_n = sorted(set(n.replace(',', '') for n in re.findall(r'\d[\d,]*(?:\.\d+)?', final_text)) - have_n)
    techy = set(t for t in re.findall(r'\b(?:[A-Z][A-Za-z0-9+#.]*[A-Z0-9+#][A-Za-z0-9+#.]*|[A-Za-z]+\+\+|C#|[A-Z]{2,}[a-z]*)\b', final_text))
    bank_tokens = tokens(bank_text)
    new_t = sorted(t for t in techy if t.lower() not in bank_tokens and t.upper() not in HEADINGS)
    return new_n, new_t


def reaudit():
    """Recompute the audit columns of saved results (the bank is the example bank plus what the run added)."""
    base = (REPO / 'builder/example/resume.toml').read_text()
    for d in sorted(OUT.iterdir()):
        sp = d / 'summary.json'
        if not sp.exists() or not (d / 'resume.pdf').exists():
            continue
        added = ''.join(l[1:] for l in (d / 'bank_changes.diff').read_text().splitlines(keepends=True)
                        if l.startswith('+') and not l.startswith('+++')) if (d / 'bank_changes.diff').exists() else ''
        final = subprocess.run(['pdftotext', '-layout', str(d / 'resume.pdf'), '-'], capture_output=True, text=True).stdout
        s = json.loads(sp.read_text())
        s['numbers_not_in_bank'], s['terms_not_in_bank'] = audit(base + added, final)
        sp.write_text(json.dumps(s, indent=2))
        print(d.name, s['numbers_not_in_bank'], s['terms_not_in_bank'])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--only')
    ap.add_argument('--mode', default='quick')
    ap.add_argument('--reaudit', action='store_true', help='recompute the audit of saved results, no runs')
    a = ap.parse_args()
    if a.reaudit:
        return reaudit()
    work = Path(tempfile.mkdtemp(prefix='jdrt-eval-'))
    os.environ['JD_RESUME_TAILOR_APP_HOME'] = str(work / 'home')
    sys.path.insert(0, str(APP / 'host'))
    import jdt
    OUT.mkdir(parents=True, exist_ok=True)
    for slug, url, why in JDS:
        if a.only and a.only != slug:
            continue
        print(f'== {slug}: {why}', flush=True)
        try:
            jd = fetch(url)
        except Exception as e:
            print('   skip:', e, flush=True)
            continue
        person = work / slug
        (person / 'out').mkdir(parents=True)
        shutil.copy(REPO / 'builder/example/resume.toml', person / 'resume.toml')
        (person / 'config.md').write_text(
            f'# jd-resume-tailor config for a made-up person (Alex Rivera)\n\n'
            f'- Bullet bank: {person}/resume.toml (builder TOML format)\n'
            f'- Build: the repo builder ({REPO}/builder/build_resume.py), OUTDIR={person}/out\n'
            f'- PDFs go to: {person}/out\n- Tracker: none\n')
        jdt.save_config({'writer': 'claude', 'reviewer': 'same', 'mode': a.mode, 'tailor_config': str(person / 'config.md'),
                         'max_budget_usd': 5, 'timeout_minutes': 25})
        r = jdt.handle({'cmd': 'tailor', 'job': {'url': jd.get('url') or url, 'company': jd.get('company') or slug.split('-')[0].title(),
                                                 'title': jd.get('title', ''), 'location': jd.get('location', ''), 'text': jd['text']}})
        if not r.get('ok'):
            print('   could not start:', r, flush=True)
            continue
        t0, last = time.time(), None
        while True:
            j = jdt.handle({'cmd': 'status', 'id': r['id']})['job']
            cur = (j['stage'], j['status'])
            if cur != last:
                print(f'   {time.time() - t0:5.0f}s {j["status"]} {j["stage"]}', flush=True)
                last = cur
            if j['status'] not in ('queued', 'running'):
                break
            time.sleep(5)
        d = Path(j['folder'])
        dest = OUT / slug
        if dest.exists():
            shutil.rmtree(dest)
        dest.mkdir(parents=True)
        for f in KEEP:
            if (d / f).exists():
                shutil.copy2(d / f, dest / f)
        for sub in ('versions',):
            if (d / sub).exists():
                shutil.copytree(d / sub, dest / sub)
        for rv in d.glob('review_*.md'):
            shutil.copy2(rv, dest / rv.name)
        for f in dest.rglob('*'):  # published: no local temp paths
            if f.is_file() and f.suffix in ('.md', '.json', '.diff'):
                t = f.read_text(errors='replace').replace(str(person) + '/', 'alex-rivera/').replace(str(d) + '/', './')
                f.write_text(re.sub(r'(/private)?/var/folders/\S*?/jdrt-eval-\w+/', '', t))
        bank_now = (person / 'resume.toml').read_text()
        final = subprocess.run(['pdftotext', '-layout', str(d / 'resume.pdf'), '-'], capture_output=True, text=True).stdout if (d / 'resume.pdf').exists() else ''
        new_n, new_t = audit(bank_now, final) if final else ([], [])
        res = j.get('result') or {}
        secs = None
        if j.get('started') and j.get('finished'):
            secs = time.mktime(time.strptime(j['finished'], '%Y-%m-%dT%H:%M:%S')) - time.mktime(time.strptime(j['started'], '%Y-%m-%dT%H:%M:%S'))
        summary = {'slug': slug, 'why': why, 'url': url, 'company': j['company'], 'title': j['title'], 'status': j['status'],
                   'gate': res.get('gate'), 'hm': res.get('hm'), 'ats': res.get('ats'), 'mode': a.mode,
                   'stages': [s['key'] for s in j['stages']], 'seconds': secs, 'cost_usd': round(j.get('cost') or 0, 2),
                   'numbers_not_in_bank': new_n, 'terms_not_in_bank': new_t,
                   'gaps': res.get('gaps', []), 'questions': res.get('questions', []), 'bank_changed': j.get('bank_changed')}
        (dest / 'summary.json').write_text(json.dumps(summary, indent=2))
        print('   ->', json.dumps({k: summary[k] for k in ('status', 'hm', 'ats', 'seconds', 'cost_usd', 'numbers_not_in_bank', 'terms_not_in_bank')}), flush=True)
    shutil.rmtree(work, ignore_errors=True)


if __name__ == '__main__':
    main()
