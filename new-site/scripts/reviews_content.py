"""Home-only data and stylesheet for the explicitly fictional review examples."""
import json
import re
from pathlib import Path


def reviews_assets(root, content):
    if 'id="home"' not in content:
        return ''
    data = json.loads((root / 'data/reviews.json').read_text())
    payload = json.dumps(data, ensure_ascii=False, separators=(',', ':')).replace('<', '\\u003c')
    return '<link rel="stylesheet" href="assets/reviews.css?v=54"><script id="reviews-data" type="application/json">' + payload + '</script><script defer src="assets/reviews.js?v=51"></script>'


def update_home(root):
    page = root / 'index.html'
    content = page.read_text()
    content = re.sub(r'<link rel="stylesheet" href="assets/reviews\.css(?:\?[^\"]*)?">', '', content)
    content = re.sub(r'<script defer src="assets/reviews\.js(?:\?[^\"]*)?"></script>', '', content)
    content = re.sub(r'<script id="reviews-data" type="application/json">.*?</script>', '', content, flags=re.S)
    content = content.replace('</head>', reviews_assets(root, content) + '</head>')
    page.write_text(content)


if __name__ == '__main__':
    update_home(Path(__file__).resolve().parents[1])
