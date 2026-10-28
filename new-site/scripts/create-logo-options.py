"""Generate editable SVG logo studies; optional dependency: fonttools.

Run with fontTools installed (no raster editing, font files stay unchanged).
All lettering is outlined, so exported SVGs do not require fonts or a network.
"""
from pathlib import Path
import json, html
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.varLib.instancer import instantiateVariableFont

ROOT = Path(__file__).resolve().parents[1]
GREEN, ORANGE = '#344b3f', '#ae6346'


def font(name, weight=None):
    f = TTFont(ROOT / 'assets' / (name + '.ttf'))
    if weight and 'fvar' in f:
        f = instantiateVariableFont(f, {'wght': weight}, inplace=False)
    return f


def outline(f, text, x, baseline, size, tracking=0):
    glyphs, cmap = f.getGlyphSet(), f.getBestCmap()
    scale = size / f['head'].unitsPerEm
    pen = SVGPathPen(glyphs)
    for character in text:
        glyph = cmap[ord(character)]
        glyphs[glyph].draw(TransformPen(pen, (scale, 0, 0, -scale, x, baseline)))
        x += f['hmtx'][glyph][0] * scale + tracking
    return pen.getCommands(), x


def width(f, text, size, tracking=0):
    return outline(f, text, 0, 0, size, tracking)[1]


# Original vector interpretations of the four client-supplied easel references.
marks = {
    'current': '<g fill="none" stroke="#344b3f" stroke-width="1.65" stroke-linecap="round" stroke-linejoin="round" transform="translate(1 3) scale(2.1 2.8)"><path d="m5 21 7-18 7 18M7 15h10M12 3v14M6 9h12"/></g>',
    'stanok': '<g stroke-linejoin="round"><path fill="#344b3f" d="M7 64V23h5v36h27V23h5v41ZM23 6h5v51h-5ZM2 62h47v5H2Z"/><path fill="#ae6346" d="M4 43h43v6H4ZM20 15h12v6H20Z"/><path d="M13 57h25M23 9h5" fill="none" stroke="#344b3f" stroke-width="2" stroke-linecap="round"/></g>',
    'holst': '<g fill="none" stroke="#344b3f" stroke-width="3.2" stroke-linecap="round" stroke-linejoin="round"><path d="M25 5v10M17 42 7 67M34 42l10 25M13 57h25M25 42v17"/><rect x="4" y="15" width="43" height="29" rx="1.5"/><path d="M11 38h29" stroke="#ae6346" stroke-width="2.2"/></g>',
    'lira': '<g fill="none" stroke="#344b3f" stroke-width="3.4" stroke-linecap="round" stroke-linejoin="round"><path d="M25 5v55M20 15 7 67M30 15l5 19m3 11 6 22M12 58h27M19 23h12M21 10h8"/><circle cx="36.5" cy="39.5" r="1.7" fill="#344b3f" stroke="none"/><path d="M6 45h38v6H6Z" fill="#ae6346" stroke="#ae6346" stroke-width="1.8"/></g>',
    'chertezh': '<g fill="none" stroke="#344b3f" stroke-width="1.65" stroke-linejoin="round" stroke-linecap="round"><path d="m4 58 30 10 14-7-30-9ZM4 58v5l30 8v-3m14-7v5l-14 5M15 56V26l4-2v31M40 58V28l-4-1v30M24 56V5l4-2v52M24 5l4 1v10M28 12l6 1v6l-6-1M19 31l5 1m4 0 8-2M12 57l3-6m24 8 1-7"/><path d="m10 43 30-5 4 4-31 7Z" fill="#ae6346" fill-opacity=".18" stroke="#ae6346" stroke-width="1.7"/><circle cx="17" cy="60" r=".8" fill="#344b3f"/><circle cx="37" cy="63" r=".8" fill="#344b3f"/></g>',
}
styles = {
    'current': ('prata', None, 'мольберты', '.ру', 29, 0),
    'stanok': ('prata', None, 'мольберты', '.ру', 30, -.12),
    'holst': ('manrope', 750, 'мольберты', '.ру', 30, -.35),
    'lira': ('prata', None, 'МОЛЬБЕРТЫ', '.РУ', 23.5, .1),
    'chertezh': ('manrope', 650, 'МОЛЬБЕРТЫ', '.РУ', 25, .1),
}
options = [
    {'id': 'current', 'title': 'Текущий', 'description': 'Действующий логотип для сравнения.', 'reference': None},
    {'id': 'stanok', 'title': 'Станок', 'description': 'Станковый мольберт и классическая надпись.', 'reference': 'ЛОГО.JPG'},
    {'id': 'holst', 'title': 'Холст', 'description': 'Мольберт с холстом и современный плотный шрифт.', 'reference': 'лого 2.JPG'},
    {'id': 'lira', 'title': 'Лира', 'description': 'А-образная опора, тёплый акцент полки и шрифт с засечками.', 'reference': 'лого 3.JPG'},
    {'id': 'chertezh', 'title': 'Чертёж', 'description': 'Объёмный станок тонкими линиями и строгая надпись.', 'reference': 'лого 4.JPG'},
]
subtitle_font = font('manrope', 600)
for option in options:
    id = option['id']
    family, weight, name, ending, size, tracking = styles[id]
    f = font(family, weight)
    size *= min(1, 220 / width(f, name + ending, size, tracking))
    first, x = outline(f, name, 57, 39, size, tracking)
    last, _ = outline(f, ending, x, 39, size, tracking)
    subtitle = 'ПРОИЗВОДСТВО С 1991 ГОДА'
    subtitle_size, spacing = 10.2, .6
    subtitle_size *= min(1, 218 / width(subtitle_font, subtitle, subtitle_size, spacing))
    caption, _ = outline(subtitle_font, subtitle, 58, 60, subtitle_size, spacing)
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 280 72" width="280" height="72" role="img" aria-labelledby="title desc"><title id="title">Мольберты.ру — {html.escape(option['title'])}</title><desc id="desc">{html.escape(option['description'])} Производство с 1991 года.</desc>{marks[id]}<path fill="{GREEN}" d="{first}"/><path fill="{ORANGE}" d="{last}"/><path fill="{GREEN}" d="{caption}"/></svg>'''
    option['asset'] = 'logo-options/' + id + '.svg'
    (ROOT / 'assets' / option['asset']).write_text(svg + '\n')
(ROOT / 'data/logo-options.json').write_text(json.dumps({'status': 'review', 'defaultId': 'current', 'options': options}, ensure_ascii=False, indent=2) + '\n')
print('Generated 4 new outlined SVG logos and the comparison image of the current logo.')
