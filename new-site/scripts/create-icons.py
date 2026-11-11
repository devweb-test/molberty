"""Generate the M icon family from the local Prata font. Not needed for normal builds.

Design dependency setup: python3 -m pip install Pillow CairoSVG fonttools
"""
from pathlib import Path
from io import BytesIO
import hashlib
import json

import cairosvg
from PIL import Image
from fontTools.ttLib import TTFont
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.svgPathPen import SVGPathPen

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'assets/icons'
OUT.mkdir(parents=True, exist_ok=True)
FONT = ROOT / 'assets/prata.ttf'
font = TTFont(FONT)
glyphs = font.getGlyphSet()
glyph = glyphs[font.getBestCmap()[ord('М')]]
bounds = BoundsPen(glyphs)
glyph.draw(bounds)
pen = SVGPathPen(glyphs)
glyph.draw(pen)
path = pen.getCommands()
x0, y0, x1, y1 = bounds.bounds
inventory = []


def artwork(maskable=False, rounded=False, monochrome=False, optical_size=512):
    width, height = (584, 584) if maskable else (704, 640)
    scale = min(width / (x1 - x0), height / (y1 - y0))
    tx = (1024 - (x1 - x0) * scale) / 2 - x0 * scale
    ty = (1024 + (y1 - y0) * scale) / 2 + y0 * scale
    color = '#000000' if monochrome else '#f9f7f1'
    # Small optical correction keeps the serif hairlines visible in browser tabs.
    stroke = 24 if optical_size <= 32 else 8
    background = '' if monochrome else (
        '<defs><linearGradient id="green" x1="0" y1="0" x2="1" y2="1">'
        '<stop stop-color="#3c5546"/><stop offset="1" stop-color="#273e32"/>'
        '</linearGradient></defs><rect width="1024" height="1024" rx="' +
        ('144' if rounded else '0') + '" fill="url(#green)"/>'
    )
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1024 1024" width="1024" height="1024">'
        '<title>Мольберты.ру</title>' + background +
        f'<g transform="translate({tx:.6f} {ty:.6f}) scale({scale:.9f} {-scale:.9f})">'
        f'<path d="{path}" fill="{color}" stroke="{color}" stroke-width="{stroke}" stroke-linejoin="round"/>'
        '</g></svg>'
    )


def record(file, role, sizes=None):
    entry = {'file': str(file.relative_to(ROOT)), 'role': role}
    if sizes:
        entry['sizes'] = sizes
    inventory.append(entry)


def svg(file, source, role):
    file.write_text(source + '\n')
    record(file, role, 'any')


def png(file, size, role, maskable=False, rounded=False):
    source = artwork(maskable=maskable, rounded=rounded, optical_size=size)
    data = cairosvg.svg2png(bytestring=source.encode(), output_width=size, output_height=size)
    image = Image.open(BytesIO(data)).convert('RGBA' if rounded else 'RGB')
    image.save(file, optimize=True)
    record(file, role, f'{size}x{size}')
    return image


svg(ROOT / 'assets/favicon.svg', artwork(rounded=True, optical_size=16), 'browser-vector')
svg(OUT / 'icon-master.svg', artwork(), 'editable-master')
svg(OUT / 'maskable-master.svg', artwork(maskable=True), 'editable-maskable-master')
svg(OUT / 'safari-pinned-tab.svg', artwork(monochrome=True), 'safari-pinned-tab')
for size in (16, 32, 48, 96):
    png(OUT / f'favicon-{size}x{size}.png', size, 'browser-png', rounded=True)
for size in (120, 152, 167):
    png(OUT / f'apple-touch-icon-{size}x{size}.png', size, 'apple-touch')
png(ROOT / 'apple-touch-icon.png', 180, 'apple-touch-default')
for size in (192, 512):
    png(OUT / f'android-chrome-{size}x{size}.png', size, 'manifest-any')
    png(OUT / f'maskable-{size}x{size}.png', size, 'manifest-maskable', maskable=True)
png(OUT / 'mstile-150x150.png', 150, 'windows-tile')

ico_sizes = (16, 24, 32, 48, 64, 128, 256)
frames = []
for size in ico_sizes:
    data = cairosvg.svg2png(bytestring=artwork(rounded=True, optical_size=size).encode(), output_width=size, output_height=size)
    frames.append(Image.open(BytesIO(data)).convert('RGBA'))
# Supply individually rendered small frames rather than downsampling a fine serif.
frames[-1].save(ROOT / 'favicon.ico', format='ICO', sizes=[(s, s) for s in ico_sizes], append_images=frames[:-1])
record(ROOT / 'favicon.ico', 'browser-ico', [f'{s}x{s}' for s in ico_sizes])

manifest = {
    'id': './', 'name': 'Мольберты.ру', 'short_name': 'Мольберты.ру',
    'description': 'Мольберты и оборудование из натурального дерева от производителя.',
    'lang': 'ru', 'dir': 'ltr', 'start_url': './', 'scope': './', 'display': 'standalone',
    'theme_color': '#34483d', 'background_color': '#f9f7f1',
    'icons': [
        {'src': f'assets/icons/{stem}-{size}x{size}.png', 'sizes': f'{size}x{size}', 'type': 'image/png', 'purpose': purpose}
        for stem, purpose in [('android-chrome', 'any'), ('maskable', 'maskable')]
        for size in (192, 512)
    ],
}
(ROOT / 'site.webmanifest').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
(ROOT / 'browserconfig.xml').write_text(
    '<?xml version="1.0" encoding="utf-8"?>\n'
    '<browserconfig><msapplication><tile><square150x150logo src="assets/icons/mstile-150x150.png"/>'
    '<TileColor>#34483d</TileColor></tile></msapplication></browserconfig>\n'
)
(ROOT / 'data/icons.json').write_text(json.dumps({
    'concept': 'Светлая буква М с засечками на зелёном фоне; маскируемые версии с безопасными полями.',
    'font': 'assets/prata.ttf', 'fontSha256': hashlib.sha256(FONT.read_bytes()).hexdigest(),
    'sourceReference': 'https://www.molberty.ru/', 'files': inventory,
}, ensure_ascii=False, indent=2) + '\n')
print(f'Generated {len(inventory)} icon assets, web manifest and browser configuration.')
