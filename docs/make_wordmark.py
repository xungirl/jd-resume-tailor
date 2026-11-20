#!/usr/bin/env python3
"""Generate docs/wordmark.svg: the README title as outlined glyphs, so it renders the same everywhere
(GitHub READMEs can't load web fonts, and an <img> SVG can't either).

    uv run --with fonttools python docs/make_wordmark.py

Font: Unbounded (SIL OFL 1.1), from @fontsource/unbounded@5.3.0 on jsDelivr.
"""
import io
import urllib.request
from pathlib import Path

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont

TEXT = 'JD-RESUME-TAILOR'
FONT_URL = 'https://cdn.jsdelivr.net/npm/@fontsource/unbounded@5.3.0/files/unbounded-latin-900-normal.woff'
SIZE = 78          # px, cap height ends up around 0.7 of this
TRACKING = 0.02    # extra space between letters, in em
PAD_X, PAD_Y = 12, 18
OUT = Path(__file__).with_name('wordmark.svg')


def main():
    font = TTFont(io.BytesIO(urllib.request.urlopen(FONT_URL, timeout=30).read()))
    upm = font['head'].unitsPerEm
    cmap, glyphs, hmtx = font.getBestCmap(), font.getGlyphSet(), font['hmtx']
    asc = font['OS/2'].sCapHeight or font['hhea'].ascent
    scale = SIZE / upm

    paths, x = [], 0.0
    for ch in TEXT:
        name = cmap[ord(ch)]
        pen = SVGPathPen(glyphs)
        # font units (y up) -> SVG px (y down), baseline at cap height + padding
        glyphs[name].draw(TransformPen(pen, (scale, 0, 0, -scale, PAD_X + x, PAD_Y + asc * scale)))
        paths.append(pen.getCommands())
        x += hmtx[name][0] * scale + TRACKING * SIZE
    x -= TRACKING * SIZE
    w, h = round(PAD_X * 2 + x), round(PAD_Y * 2 + asc * scale)
    d = ' '.join(paths)

    OUT.write_text(f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="{TEXT}">
  <title>{TEXT}</title>
  <defs>
    <linearGradient id="fill" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="#4c6ef5"/>
      <stop offset="0.55" stop-color="#845ef7"/>
      <stop offset="1" stop-color="#d6336c"/>
    </linearGradient>
  </defs>
  <path d="{d}" fill="#845ef7" fill-opacity="0.18" transform="translate(4 4)"/>
  <path d="{d}" fill="url(#fill)"/>
</svg>
''')
    print(f'wrote {OUT} ({w}x{h})')


if __name__ == '__main__':
    main()
