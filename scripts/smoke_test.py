#!/usr/bin/env python3
"""Smoke test against the live internet: does the fetcher still read every ATS, and does the builder
still produce one-page PDFs with embedded fonts?

    python3 scripts/smoke_test.py            # fetcher on 6 ATSs + closed posting + builder
    python3 scripts/smoke_test.py --no-build # fetcher only (no uv / reportlab needed)

For each ATS it finds one currently open posting through that ATS's public listing API, then runs
fetch_jd.py on it the way a user would paste it. Boards come and go, so each ATS has a few companies to
try. Exit code 0 = everything passed.
"""
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FETCH = ROOT / 'skills' / 'jd-resume-tailor' / 'fetch_jd.py'
UA = {'User-Agent': 'jd-resume-tailor-smoke-test', 'Accept': 'application/json'}


def get_json(url, data=None):
    headers = dict(UA, **({'Content-Type': 'application/json'} if data else {}))
    req = urllib.request.Request(url, data=json.dumps(data).encode() if data else None, headers=headers)
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)


def greenhouse(co):
    return get_json(f'https://boards-api.greenhouse.io/v1/boards/{co}/jobs')['jobs'][0]['absolute_url']


def lever(co):
    return get_json(f'https://api.lever.co/v0/postings/{co}?limit=1&mode=json')[0]['hostedUrl']


def ashby(co):
    return get_json(f'https://api.ashbyhq.com/posting-api/job-board/{co}')['jobs'][0]['jobUrl']


def workday(spec):
    tenant, wd, site = spec.split('/')
    d = get_json(f'https://{tenant}.{wd}.myworkdayjobs.com/wday/cxs/{tenant}/{site}/jobs',
                 {'limit': 1, 'offset': 0, 'appliedFacets': {}, 'searchText': ''})
    return f'https://{tenant}.{wd}.myworkdayjobs.com/{site}' + d['jobPostings'][0]['externalPath']


def oracle(spec):
    host, site = spec.split('/')
    d = get_json(f'https://{host}/hcmRestApi/resources/latest/recruitingCEJobRequisitions'
                 f'?onlyData=true&expand=requisitionList&finder=findReqs;siteNumber={site},limit=1')
    return f'https://{host}/hcmUI/CandidateExperience/en/sites/{site}/job/' + d['items'][0]['requisitionList'][0]['Id']


def smartrecruiters(co):
    return f'https://jobs.smartrecruiters.com/{co}/' + get_json(
        f'https://api.smartrecruiters.com/v1/companies/{co}/postings?limit=1')['content'][0]['id']


ATS = [
    ('greenhouse', greenhouse, ['anthropic', 'figma', 'stripe']),
    ('lever', lever, ['palantir', 'spotify', 'plaid']),
    ('ashby', ashby, ['openai', 'notion', 'ramp']),
    ('workday', workday, ['nvidia/wd5/NVIDIAExternalCareerSite', 'salesforce/wd12/External_Career_Site']),
    ('oracle', oracle, ['jpmc.fa.oraclecloud.com/CX_1001']),
    ('smartrecruiters', smartrecruiters, ['BoschGroup', 'Visa', 'ServiceNow']),
]


def fetch(url):
    p = subprocess.run([sys.executable, '-I', str(FETCH), url], capture_output=True, text=True, timeout=60)
    return p.returncode, p.stdout


def main():
    failures = []
    for name, find, companies in ATS:
        url = None
        for co in companies:
            try:
                url = find(co)
                break
            except Exception:
                continue
        if not url:
            failures.append(name)
            print(f'FAIL  {name:15} no open posting found on {companies}')
            continue
        code, out = fetch(url)
        head = out.splitlines()[0] if out else ''
        ok = code == 0 and head.startswith(f'[{name}]') and head.endswith('OPEN') and len(out) > 1000
        failures += [] if ok else [name]
        print(f"{'ok   ' if ok else 'FAIL '} {name:15} exit={code} {len(out):>6} chars  {head[:90]}")

    code, out = fetch('https://job-boards.greenhouse.io/anthropic/jobs/1')
    ok = code == 2 and 'NOT FOUND' in out
    failures += [] if ok else ['closed-posting']
    print(f"{'ok   ' if ok else 'FAIL '} {'closed posting':15} exit={code} (want 2)")

    if '--no-build' not in sys.argv:
        with tempfile.TemporaryDirectory() as out_dir:
            p = subprocess.run(['uv', 'run', '-q', '--with', 'reportlab', 'python', 'build_resume.py',
                                'example/resume.toml'], cwd=ROOT / 'builder', capture_output=True, text=True,
                               env={**os.environ, 'OUTDIR': out_dir}, timeout=300)
            pdfs = sorted(Path(out_dir).glob('*.pdf'))
            pages = [len(re.findall(rb'/Type\s*/Page[^s]', f.read_bytes())) for f in pdfs]
            embedded = '(embedded)' in p.stdout
            ok = p.returncode == 0 and len(pdfs) == 3 and pages == [1, 1, 1] and embedded
            failures += [] if ok else ['builder']
            print(f"{'ok   ' if ok else 'FAIL '} {'builder':15} exit={p.returncode} {len(pdfs)} PDFs, pages={pages}, "
                  f"fonts {'embedded' if embedded else 'NOT embedded'}")
            if not ok:
                print(p.stdout + p.stderr)

    print('\nall passed' if not failures else f'\nfailed: {", ".join(failures)}')
    sys.exit(1 if failures else 0)


if __name__ == '__main__':
    main()
