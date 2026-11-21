#!/usr/bin/env python3
"""Script checks on a built resume, so the model doesn't have to eyeball them.

    check.py resume.pdf analysis.md [--json]

Fails (exit 1) when: not exactly one page; no extractable text; an ATS keyword from analysis.md
never appears and isn't listed under "Known gaps"; a keyword appears more than 4 times.
Warns about: a lot of empty space at the bottom; bullets over 200 characters in resume_source.md.
Needs poppler (pdfinfo, pdftotext).
"""
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

MAX_REPEAT = 4
BOTTOM_WARN_IN = 1.0   # empty space under the last line, margin included (~0.5in margin + ~3 lines)


def run(*cmd):
    return subprocess.run(cmd, capture_output=True, text=True, timeout=60)


def field(analysis: str, label: str) -> str:
    m = re.search(rf'^\s*{re.escape(label)}\s*:\s*(.*)$', analysis, re.M | re.I)
    return m.group(1).strip() if m else ''


def known_gaps(analysis: str) -> str:
    m = re.search(r'^\s*Known gaps\s*:(.*?)(?=^\s*[A-Z][A-Za-z /]+:\s|\Z)', analysis, re.M | re.S | re.I)
    return (m.group(1) if m else '').lower()


def keywords(analysis: str) -> list[list[str]]:
    raw = field(analysis, 'ATS keywords')
    out = []
    for part in re.split(r'[,;]', raw):
        alts = [a.strip(' .[]"\'') for a in part.split('/') if a.strip(' .[]"\'')]
        if alts:
            out.append(alts)
    return out


def count(text: str, word: str) -> int:
    pat = r'(?<![A-Za-z0-9])' + re.escape(word) + r'(?![A-Za-z0-9])'
    return len(re.findall(pat, text, re.I))


def bottom_gap_in(pdf: str):
    p = run('pdftotext', '-bbox', '-f', '1', '-l', '1', pdf, '-')
    if p.returncode:
        return None
    page = re.search(r'<page width="([\d.]+)" height="([\d.]+)"', p.stdout)
    ys = [float(y) for y in re.findall(r'<word [^>]*yMax="([\d.]+)"', p.stdout)]
    if not page or not ys:
        return None
    return (float(page.group(2)) - max(ys)) / 72


def check(pdf: str, analysis_path: str) -> dict:
    res = {'ok': True, 'pages': None, 'failures': [], 'warnings': [], 'keywords': {}, 'bottom_gap_in': None}
    if not (shutil.which('pdfinfo') and shutil.which('pdftotext')):
        res['ok'] = False
        res['failures'].append('poppler is not installed (brew install poppler): cannot check the PDF')
        return res
    if not Path(pdf).exists():
        res['ok'] = False
        res['failures'].append(f'{pdf} does not exist')
        return res
    info = run('pdfinfo', pdf).stdout
    m = re.search(r'^Pages:\s+(\d+)', info, re.M)
    res['pages'] = int(m.group(1)) if m else None
    if res['pages'] != 1:
        res['failures'].append(f'the PDF has {res["pages"]} pages, it must have exactly 1')
    text = run('pdftotext', '-layout', pdf, '-').stdout
    if len(text.strip()) < 300:
        res['failures'].append('almost no text can be extracted from the PDF (an ATS would see an empty resume)')
    analysis = Path(analysis_path).read_text() if Path(analysis_path).exists() else ''
    if not analysis:
        res['warnings'].append(f'{analysis_path} not found: keyword checks skipped')
    gaps = known_gaps(analysis)
    for alts in keywords(analysis):
        n = sum(count(text, a) for a in alts)
        name = '/'.join(alts)
        res['keywords'][name] = n
        if n == 0 and not any(a.lower() in gaps for a in alts):
            res['failures'].append(f'keyword "{name}" never appears; write it in if your bank has the fact, otherwise list it under Known gaps')
        if n > MAX_REPEAT:
            res['failures'].append(f'keyword "{name}" appears {n} times (more than {MAX_REPEAT} reads as stuffing)')
    gap = bottom_gap_in(pdf)
    res['bottom_gap_in'] = round(gap, 2) if gap is not None else None
    if gap is not None and gap > BOTTOM_WARN_IN:
        res['warnings'].append(f'{gap:.1f} in empty at the bottom of the page: add a relevant true bullet if your bank has one')
    src = Path(pdf).with_name('resume_source.md')
    if src.exists():
        for line in src.read_text().splitlines():
            b = re.match(r'^\s*[-*•]\s+(.*)$', line)
            if b and len(b.group(1)) > 200:
                res['warnings'].append(f'bullet over 200 characters ({len(b.group(1))}): {b.group(1)[:60]}…')
    res['ok'] = not res['failures']
    return res


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    if len(args) != 2:
        print(__doc__.strip())
        sys.exit(2)
    r = check(*args)
    if '--json' in sys.argv:
        print(json.dumps(r, indent=2))
    else:
        print('PASS' if r['ok'] else 'FAIL', f"(pages: {r['pages']}, bottom gap: {r['bottom_gap_in']} in)")
        for f in r['failures']:
            print('  FAIL', f)
        for w in r['warnings']:
            print('  WARN', w)
        if r['keywords']:
            print('  keywords:', ', '.join(f'{k}={v}' for k, v in r['keywords'].items()))
    sys.exit(0 if r['ok'] else 1)


if __name__ == '__main__':
    main()
