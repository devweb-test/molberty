"""Validate icon inventory, binary dimensions and links on all exported pages."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit, unquote
from xml.etree import ElementTree
import json
import re
import struct

from icon_links import icon_links

ROOT = Path(__file__).resolve().parents[1]


def png_size(path):
    data = path.read_bytes()
    assert data[:8] == b'\x89PNG\r\n\x1a\n', path
    return struct.unpack('>II', data[16:24])


class Head(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.links = []
        self.feed(text.split('</head>', 1)[0])

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'link' and attrs.get('rel') in ('icon', 'apple-touch-icon', 'mask-icon', 'manifest'):
            self.links.append(attrs)


inventory = json.loads((ROOT / 'data/icons.json').read_text())['files']
assert len(inventory) == len({entry['file'] for entry in inventory}) == 18
for item in inventory:
    path = ROOT / item['file']
    assert path.is_file(), path
    if path.suffix == '.png':
        size = tuple(map(int, item['sizes'].split('x')))
        assert png_size(path) == size, path
        if item['role'] != 'browser-png':
            assert path.read_bytes()[25] == 2, 'Device icons must be opaque RGB: ' + str(path)
    elif path.suffix == '.svg':
        svg = ElementTree.parse(path).getroot()
        assert svg.tag == '{http://www.w3.org/2000/svg}svg'
        assert svg.attrib['viewBox'] == '0 0 1024 1024'
        assert not re.search(r'<(?:text|image)\b|(?:font-family|href)=', path.read_text()), path

data = (ROOT / 'favicon.ico').read_bytes()
reserved, kind, count = struct.unpack('<HHH', data[:6])
assert (reserved, kind, count) == (0, 1, 7)
ico_sizes = set()
for index in range(count):
    width, height, _, _, _, _, length, offset = struct.unpack('<BBBBHHII', data[6 + index * 16:22 + index * 16])
    ico_sizes.add((width or 256, height or 256))
    assert length > 0 and offset + length <= len(data)
assert ico_sizes == {(s, s) for s in (16, 24, 32, 48, 64, 128, 256)}

manifest = json.loads((ROOT / 'site.webmanifest').read_text())
assert manifest['id'] == manifest['start_url'] == manifest['scope'] == './'
assert manifest['name'] == manifest['short_name'] == 'Мольберты.ру'
assert len(manifest['icons']) == 4
assert {(x['purpose'], x['sizes']) for x in manifest['icons']} == {(purpose, f'{s}x{s}') for purpose in ('any', 'maskable') for s in (192, 512)}
for icon in manifest['icons']:
    assert icon['type'] == 'image/png' and not urlsplit(icon['src']).scheme and not icon['src'].startswith('/')
    assert png_size(ROOT / icon['src']) == tuple(map(int, icon['sizes'].split('x')))
config = ElementTree.parse(ROOT / 'browserconfig.xml').getroot()
assert png_size(ROOT / config.find('msapplication/tile/square150x150logo').attrib['src']) == (150, 150)

pages = [*ROOT.rglob('*.html'), ROOT.parent / '404.html']
for file in pages:
    text = file.read_text()
    prefix = '' if 'id="error-page-base"' in text else '../' * len(file.parent.relative_to(ROOT).parts)
    assert text.count('<!-- site-icons:start -->') == text.count('<!-- site-icons:end -->') == 1, file
    assert icon_links(prefix) in text, file
    links = Head(text).links
    assert len(links) == 12, (file, len(links))
    for item in links:
        path = unquote(urlsplit(item['href']).path)
        base = ROOT if 'id="error-page-base"' in text else file.parent
        assert (base / path).resolve().is_file(), (file, path)
assert len(pages) == 219
print('Иконки: 18 файлов, 7 размеров ICO, 4 версии manifest, 219 страниц: OK')
