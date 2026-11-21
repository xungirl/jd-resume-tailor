#!/usr/bin/env python3
"""One-page resume builder driven by a bullet bank (TOML).

The idea: you write every true bullet you have ONCE in resume.toml, then a
"variant" just picks which skill groups and which project bullets to show, in
what order. Tailoring to a JD = adding a 6-line variant, not editing a doc.

    uv run --with reportlab python build_resume.py resume.toml                 # all variants
    uv run --with reportlab python build_resume.py resume.toml --variant backend
    OUTDIR=out FONT_DIR=~/fonts uv run --with reportlab python build_resume.py resume.toml

Checks on every build:
  * OVERFLOW  - content runs past one page (exit code 1)
  * WRAP      - a skills line wraps to 2 lines (warning; recruiters scan one line per group)

Fonts are embedded in the PDF. Set FONT_DIR to a folder with Carlito-{Regular,Bold,Italic,BoldItalic}.ttf
(metric-compatible with Calibri, SIL OFL) for a nicer look; otherwise the builder embeds Liberation Sans
or Arial (both metric-compatible with Helvetica, so page fit is unchanged). If none is found it falls back
to bare Helvetica and warns. NO_EMBED=1 forces bare Helvetica.
"""
import argparse
import os
import sys
import tomllib
from pathlib import Path

from reportlab.lib.colors import HexColor
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph

WIDTH, HEIGHT = 612, 792            # US Letter
LEFT, RIGHT = 40, 572
TEXT_WIDTH = RIGHT - LEFT
BODY = float(os.environ.get('FS', 10.2))
LEADING = BODY + 1.8
BOTTOM = 28
BLACK = HexColor('#151515')
LINK = '#183A70'

STYLES = ('regular', 'bold', 'italic', 'bolditalic')


def _font_candidates():
    """TrueType families to EMBED in the PDF, best first: Carlito from FONT_DIR, then a
    Helvetica-metric sans the OS already has (Liberation Sans on Linux, Arial on macOS/Windows).
    Embedding matters: with bare Helvetica the PDF only names the font, and viewers or ATS
    parsers without it substitute one (poppler, for instance, renders the bold as regular)."""
    fd = os.environ.get('FONT_DIR')
    if fd:
        d = Path(fd).expanduser()
        yield 'Carlito', [d / f'Carlito-{s}.ttf' for s in ('Regular', 'Bold', 'Italic', 'BoldItalic')]
    for d in ('/usr/share/fonts/truetype/liberation', '/usr/share/fonts/truetype/liberation2',
              '/usr/share/fonts/liberation-sans', '/usr/share/fonts/liberation'):
        yield 'LiberationSans', [Path(d) / f'LiberationSans-{s}.ttf' for s in ('Regular', 'Bold', 'Italic', 'BoldItalic')]
    mac = Path('/System/Library/Fonts/Supplemental')
    yield 'Arial', [mac / f for f in ('Arial.ttf', 'Arial Bold.ttf', 'Arial Italic.ttf', 'Arial Bold Italic.ttf')]
    win = Path(os.environ.get('WINDIR', 'C:/Windows')) / 'Fonts'
    yield 'Arial', [win / f for f in ('arial.ttf', 'arialbd.ttf', 'ariali.ttf', 'arialbi.ttf')]


FONT = {'regular': 'Helvetica', 'bold': 'Helvetica-Bold', 'italic': 'Helvetica-Oblique', 'bolditalic': 'Helvetica-BoldOblique'}
FONT_EMBEDDED = False
for fam, files in ([] if os.environ.get('NO_EMBED') else _font_candidates()):
    if all(f.exists() for f in files):
        names = {s: f'{fam}-{s}' for s in STYLES}
        for s, f in zip(STYLES, files):
            pdfmetrics.registerFont(TTFont(names[s], str(f)))
        FONT, FONT_EMBEDDED = names, True
        break
pdfmetrics.registerFontFamily(FONT['regular'], normal=FONT['regular'], bold=FONT['bold'],
                              italic=FONT['italic'], boldItalic=FONT['bolditalic'])  # makes <b>/<i> work


TAG_COLOR = os.environ.get('TAG_COLOR', '#5A5A5A')  # tags dimmer than the description


def link(url, label):
    return f'<link href="{url}" color="{LINK}">{label}</link>'


def build(data, name, spec, outdir):
    out = outdir / f"{data['profile'].get('file_prefix', 'Resume')}_{name}.pdf"
    st = {
        'body': ParagraphStyle('body', fontName=FONT['regular'], fontSize=BODY, leading=LEADING, textColor=BLACK),
        'contact': ParagraphStyle('contact', fontName=FONT['regular'], fontSize=9.6, leading=12, alignment=1, textColor=BLACK),
        'title': ParagraphStyle('title', fontName=FONT['bold'], fontSize=22, leading=24, alignment=1, textColor=BLACK),
        'right': ParagraphStyle('right', fontName=FONT['regular'], fontSize=BODY, leading=LEADING, alignment=2, textColor=BLACK),
    }
    c = canvas.Canvas(str(out), pagesize=(WIDTH, HEIGHT), pageCompression=1, initialFontName=FONT['regular'])
    c.setTitle(f"{data['profile']['name']} Resume")
    c.setAuthor(data['profile']['name'])
    y = [757]
    warnings = []

    def para(t, style='body', x=LEFT, width=TEXT_WIDTH, gap=0):
        p = Paragraph(t, st[style]); _, h = p.wrap(width, HEIGHT)
        p.drawOn(c, x, y[0] - h); y[0] -= h + gap
        return h

    def row(left, right='', italic=False, gap=0):
        font = FONT['italic'] if italic else FONT['regular']
        rw = pdfmetrics.stringWidth(right, font, BODY)
        p = Paragraph(left, st['body']); _, h = p.wrap(TEXT_WIDTH - rw - (14 if right else 0), HEIGHT)
        if h > LEADING + .1:
            warnings.append(f'heading wraps: {left[:60]}')
        p.drawOn(c, LEFT, y[0] - h)
        if right:
            c.setFont(font, BODY); c.setFillColor(BLACK); c.drawRightString(RIGHT, y[0] - BODY, right)
        y[0] -= max(h, LEADING) + gap

    def section(label):
        y[0] -= 6
        c.setFont(FONT['bold'], 11.2); c.setFillColor(BLACK); c.drawString(LEFT, y[0] - 10.5, label)
        c.setLineWidth(.55); c.setStrokeColor(BLACK); c.line(LEFT, y[0] - 14, RIGHT, y[0] - 14)
        y[0] -= 18

    def bullet(t):
        top = y[0]
        para(t, x=LEFT + 12, width=TEXT_WIDTH - 12, gap=1.0)
        c.setFillColor(BLACK); c.circle(LEFT + 4.2, top - 6.3, 1.3, fill=1, stroke=0)

    pr = data['profile']
    para(pr['name'], 'title', gap=3)
    contact = [pr.get('location', '')] + [link(l['url'], l['label']) for l in pr.get('links', [])]
    para(' | '.join(x for x in contact if x), 'contact', gap=1)

    section('EDUCATION')
    for i, e in enumerate(data.get('education', [])):
        if i:
            y[0] -= 3
        row(f"<b>{e['school']}</b>", e.get('location', ''))
        row(f"<i>{e['degree']}</i>", e.get('dates', ''), italic=True)
        for line in e.get('lines', []):
            para(line)
        if spec.get('availability') and i == 0 and pr.get('availability'):
            para(f"<b>Availability:</b> {pr['availability']}")

    section('TECHNICAL SKILLS')
    for k in spec['skills']:
        label, t = data['skills'][k]['label'], data['skills'][k]['text']
        h = para(f'<b>{label}:</b> {t}')
        if h > LEADING + .1:
            warnings.append(f'WRAP skills line "{label}" ({h / LEADING:.0f} lines) - shorten it')

    section('PROJECTS')
    for p in spec['projects']:
        proj = data['projects'][p['key']]
        y[0] -= 2.5
        # tags: 2-3 core words after the title ("Go · Raft Consensus"); a variant can re-pick them per JD
        tags = spec.get('tags', {}).get(p['key'], proj.get('tags'))
        links = [(proj['url'], proj.get('url_label', 'GitHub'))] if proj.get('url') else []
        if proj.get('live'):
            links.append((proj['live'], proj.get('live_label', 'Live')))
        if spec.get('project_dates'):
            # dates take the right column, so links stay inline
            head = f"<b>{proj['name']}</b> | <i>{proj['desc']}</i>" + (f" | <i>{tags}</i>" if tags else '')
            head += ''.join(' | ' + link(u, l) for u, l in links)
            row(head, proj.get('dates', ''), gap=1)
        else:
            # bold name — regular description | italic tags, links right-aligned like the date column above
            head = f"<b>{proj['name']}</b> — {proj['desc']}" + (f' <font color="{TAG_COLOR}">| <i>{tags}</i></font>' if tags else '')
            plain = ' · '.join(l for _, l in links)
            rw = pdfmetrics.stringWidth(plain, FONT['regular'], BODY) if links else 0
            hp = Paragraph(head, st['body']); _, h = hp.wrap(TEXT_WIDTH - rw - (14 if links else 0), HEIGHT)
            if h > LEADING + .1:
                warnings.append(f"heading wraps: {proj['name']} - shorten desc or tags")
            hp.drawOn(c, LEFT, y[0] - h)
            if links:
                rp = Paragraph(' · '.join(link(u, l) for u, l in links), st['right']); _, hr = rp.wrap(rw + 4, HEIGHT)
                rp.drawOn(c, RIGHT - rw - 4, y[0] - hr)
            y[0] -= max(h, LEADING) + 1
        for b in p['bullets']:
            if b not in proj['bullets']:
                raise SystemExit(f"variant {name}: project {p['key']} has no bullet '{b}' (have: {', '.join(proj['bullets'])})")
            bullet(proj['bullets'][b])

    if data.get('experience'):
        section('EXPERIENCE')
        for e in data['experience']:
            row(f"<b>{e['company']}</b>", e.get('location', ''))
            row(f"<i>{e['title']}</i>", e.get('dates', ''), italic=True, gap=1)
            for b in e.get('bullets', []):
                bullet(b)

    ok = y[0] >= BOTTOM
    c.showPage(); c.save()
    print(f"{'OK      ' if ok else 'OVERFLOW'} {out.name}: bottom y={y[0]:.1f}pt (needs >= {BOTTOM}); "
          f"{'room for ~%d more lines' % ((y[0] - BOTTOM) // LEADING) if ok else 'cut ~%d lines' % (-(y[0] - BOTTOM) // LEADING + 1)}")
    for w in warnings:
        print('   warning:', w)
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('bank', help='resume.toml (bullet bank + variants)')
    ap.add_argument('--variant', action='append', help='build only these variants (repeatable)')
    a = ap.parse_args()
    data = tomllib.loads(Path(a.bank).read_text())
    outdir = Path(os.environ.get('OUTDIR', Path(a.bank).parent / 'out')).expanduser()
    outdir.mkdir(parents=True, exist_ok=True)
    print(f"font: {FONT['regular'].rsplit('-', 1)[0]} ({'embedded' if FONT_EMBEDDED else 'NOT embedded'})")
    if not FONT_EMBEDDED:
        print('   warning: fonts are not embedded; some viewers and ATS parsers will substitute them. '
              'Set FONT_DIR to a Carlito folder or install Liberation Sans.')
    names = a.variant or list(data['variants'])
    unknown = [n for n in names if n not in data['variants']]
    if unknown:
        raise SystemExit(f"unknown variant(s): {unknown}; have {list(data['variants'])}")
    sys.exit(0 if all([build(data, n, data['variants'][n], outdir) for n in names]) else 1)


if __name__ == '__main__':
    main()
