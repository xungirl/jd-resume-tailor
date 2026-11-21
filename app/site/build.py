"""Turn app/eval/results/* into the demo site's data (app/site/data/).

    python3 app/site/build.py

Everything shown on the site comes from real recorded runs on a made-up person (Alex Rivera).
"""
import json, re, shutil, subprocess
from pathlib import Path

APP = Path(__file__).resolve().parent.parent
RES = APP / 'eval' / 'results'
DATA = Path(__file__).resolve().parent / 'data'
ORDER = ['snowflake-db', 'airbnb-swe', 'octaura-data', 'anduril-ml', 'roblox-engine']


def read(p):
    return p.read_text(errors='replace') if p.exists() else ''


def jd_body(md):
    lines = md.split('\n')
    return '\n'.join(lines[4:]).strip() if len(lines) > 4 else md


def main():
    if DATA.exists():
        shutil.rmtree(DATA)
    DATA.mkdir(parents=True)
    runs = []
    slugs = [s for s in ORDER if (RES / s).exists()] + sorted(p.name for p in RES.iterdir() if p.is_dir() and p.name not in ORDER)
    for slug in slugs:
        d = RES / slug
        summ = json.loads(read(d / 'summary.json') or '{}')
        state = json.loads(read(d / 'state.json') or '{}')
        out = DATA / slug
        out.mkdir()
        versions = []
        for pdf in sorted((d / 'versions').glob('*.pdf'), key=lambda p: int(p.name.split('_')[0])):
            shutil.copy2(pdf, out / pdf.name)
            n, key = pdf.stem.split('_', 1)
            # a picture of the page: PDFs inside iframes don't show on every phone
            subprocess.run(['pdftoppm', '-r', '130', '-png', '-singlefile', str(pdf), str(out / pdf.stem)], check=True)
            versions.append({'n': int(n), 'stage': key, 'pdf': f'data/{slug}/{pdf.name}', 'png': f'data/{slug}/{pdf.stem}.png',
                             'text': read(pdf.with_suffix('.md'))})
        if not versions and (d / 'resume.pdf').exists():
            shutil.copy2(d / 'resume.pdf', out / 'resume.pdf')
            versions.append({'n': 1, 'stage': 'final', 'pdf': f'data/{slug}/resume.pdf', 'text': read(d / 'resume_source.md')})
        reviews = []
        for rv in sorted(d.glob('review_*.md')):
            m = re.match(r'review_(hm|ats)_(\d)', rv.stem)
            text = read(rv)
            v = re.findall(r'VERDICT:\s*\**\s*(yes|no|unsure|pass|fail)', text, re.I)
            reviews.append({'kind': m.group(1), 'round': int(m.group(2)), 'verdict': v[-1].lower() if v else '', 'text': text})
        runs.append({
            'slug': slug, 'company': summ.get('company') or state.get('company'), 'title': summ.get('title') or state.get('title'),
            'why': summ.get('why', ''), 'url': summ.get('url') or state.get('url'), 'summary': summ,
            'stages': [{k: s.get(k) for k in ('key', 'label', 'status', 'detail', 'seconds')} for s in state.get('stages', [])],
            'result': state.get('result') or {}, 'jd': jd_body(read(d / 'jd.md')), 'analysis': read(d / 'analysis.md'),
            'notes': read(d / 'notes.md'), 'diff': read(d / 'bank_changes.diff'), 'reviews': reviews, 'versions': versions,
            'writer': json.loads(read(d / 'writer.json') or '{}'),
        })
    (DATA / 'runs.json').write_text(json.dumps(runs, indent=1))
    print(f'{len(runs)} runs -> {DATA}')


if __name__ == '__main__':
    main()
