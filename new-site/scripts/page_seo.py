"""Apply only explicitly supplied page SEO fields; omitted fields remain intact."""
from pathlib import Path
from html import escape
import json
import re

FIELDS = {'title', 'description', 'h1', 'keywords'}
DATA_PATTERN = r'<script id="page-seo-data" type="application/json">.*?</script>'


def load_page_seo(root):
    path = Path(root) / 'data/page-seo.json'
    if not path.exists():
        return {}
    data = json.loads(path.read_text())
    for route, fields in data.items():
        assert isinstance(route, str) and isinstance(fields, dict)
        assert set(fields).issubset(FIELDS)
        assert all(isinstance(value, str) and value.strip() for value in fields.values())
    return data


def apply_page_seo(document, fields):
    if not fields:
        return document
    if 'title' in fields:
        document, count = re.subn(r'<title>.*?</title>', lambda _: '<title>' + escape(fields['title']) + '</title>', document, flags=re.S)
        assert count == 1, 'Expected one title'
    for name in ('description', 'keywords'):
        if name not in fields:
            continue
        tag = '<meta name="' + name + '" content="' + escape(fields[name]) + '">'
        pattern = r'<meta\b(?=[^>]*\bname="' + name + r'")[^>]*>'
        document, count = re.subn(pattern, lambda _: tag, document, flags=re.I)
        assert count <= 1, 'Duplicate ' + name
        if not count:
            document = document.replace('</head>', tag + '</head>', 1)
    if 'h1' in fields:
        # Fresh build shells get their H1 from the browser/prerender template.
        document, count = re.subn(r'(<h1\b[^>]*>).*?(</h1>)', lambda m: m[1] + escape(fields['h1'], quote=False) + m[2], document, flags=re.S)
        assert count <= 1, 'Duplicate H1'
    payload = json.dumps(fields, ensure_ascii=False, separators=(',', ':')).replace('<', '\\u003c')
    data = '<script id="page-seo-data" type="application/json">' + payload + '</script>'
    document, count = re.subn(DATA_PATTERN, lambda _: data, document, flags=re.S)
    assert count <= 1, 'Duplicate page SEO data'
    if not count:
        document = document.replace('</head>', data + '</head>', 1)
    return document
