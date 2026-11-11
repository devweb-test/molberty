"""Shared static-guide data and styles, loaded only in their own categories."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def category_guides_assets(prefix, content):
    guides = json.loads((ROOT / 'data/category-guides.json').read_text())
    copy_asset = f'<script defer src="{prefix}assets/category-copy.js?v=101"></script>' if 'id="category"' in content else ''
    if not any(f'id="category" data-id="{category_id}"' in content for category_id in guides):
        return copy_asset
    return copy_asset + (f'<link rel="stylesheet" href="{prefix}assets/category-guides.css?v=61">'
            f'<script defer src="{prefix}assets/category-guides-data.js?v=61"></script>')


def sync_category_guides(root=ROOT):
    guides = json.loads((root / 'data/category-guides.json').read_text())
    (root / 'assets/category-guides-data.js').write_text(
        'window.CATEGORY_GUIDES = ' + json.dumps(guides, ensure_ascii=False) + ';\n')
    copy = json.loads((root / 'data/category-copy.json').read_text())
    ids = {c['id'] for c in json.loads((root / 'data/catalog-structure.json').read_text())['categories']}
    assert set(copy) == ids, 'Provide individual copy for every category'
    assert all(len(entry['paragraphs']) >= 2 and all(p.strip() for p in entry['paragraphs']) for entry in copy.values())
    assert all(copy[id].get('actionText') for id in guides)
    (root / 'assets/category-copy.js').write_text('window.CATEGORY_COPY = ' + json.dumps(copy, ensure_ascii=False) + ';\n')
    return guides
