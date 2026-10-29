"""Shared static-guide data and styles, loaded only in their own categories."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def category_guides_assets(prefix, content):
    guides = json.loads((ROOT / 'data/category-guides.json').read_text())
    if not any(f'id="category" data-id="{category_id}"' in content for category_id in guides):
        return ''
    return (f'<link rel="stylesheet" href="{prefix}assets/category-guides.css?v=61">'
            f'<script defer src="{prefix}assets/category-guides-data.js?v=61"></script>')


def sync_category_guides(root=ROOT):
    guides = json.loads((root / 'data/category-guides.json').read_text())
    (root / 'assets/category-guides-data.js').write_text(
        'window.CATEGORY_GUIDES = ' + json.dumps(guides, ensure_ascii=False) + ';\n')
    return guides
