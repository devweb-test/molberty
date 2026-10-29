"""Generate the error page from the current shared shell; keep Pages' root copy."""
from pathlib import Path
import argparse
import json
import re
from mobile_navigation import mobile_navigation

ROOT = Path(__file__).resolve().parents[1]
LOCAL_BASE = '<base id="error-page-base" href="/">'
PAGES_BASE = '<base id="error-page-base" href="/molberty/new-site/">'


def copy_deployment_page(root=ROOT):
    # GitHub Pages publishes the repository root, while the site lives in new-site.
    # A static base also keeps its nested missing URLs usable without JavaScript.
    source = (root / '404.html').read_text()
    (root.parent / '404.html').write_text(source.replace(LOCAL_BASE, PAGES_BASE))


def write_error_page(root=ROOT):
    source = (root / 'index.html').read_text()
    source = re.sub(r'<link rel="stylesheet" href="assets/clients.css">|<script defer src="assets/clients-data.js"></script>', '', source)
    source = re.sub(r'<title>.*?</title>', '<title>Страница не найдена — Мольберты.ру</title>', source, count=1)
    source = re.sub(r'<meta name="description"[^>]*>', '<meta name="description" content="Такой страницы не существует. Вернитесь на главную, выберите раздел каталога или посмотрите новинки нашего производства.">', source, count=1)
    source = re.sub(r'<link rel="canonical"[^>]*>', '', source, count=1)
    crumbs = {'@context': 'https://schema.org', '@type': 'BreadcrumbList', 'itemListElement': [
        {'@type': 'ListItem', 'position': 1, 'name': 'Главная', 'item': 'https://www.molberty.ru/'},
        {'@type': 'ListItem', 'position': 2, 'name': 'Страница не найдена', 'item': 'https://www.molberty.ru/404.html'},
    ]}
    source = re.sub(r'(<script id="breadcrumb-schema"[^>]*>).*?(</script>)', lambda m: m[1] + json.dumps(crumbs, ensure_ascii=False) + m[2], source, count=1, flags=re.S)
    # Resolve every shared link and asset from a missing URL at any nesting depth.
    bootstrap = LOCAL_BASE + '''<script>(function(){var base=document.getElementById('error-page-base');if(location.hostname==='devweb-test.github.io')base.setAttribute('href','/molberty/new-site/');else if(location.protocol==='file:')base.href=new URL('.',location.href).href;else base.setAttribute('href','/');})();</script>'''
    source = source.replace('<head>', '<head>' + bootstrap, 1)
    source = source.replace('<link rel="stylesheet" href="assets/motion.css">', '<link rel="stylesheet" href="assets/motion.css"><link rel="stylesheet" href="assets/not-found.css">', 1)
    source = re.sub(r'<main id="main">.*?</main>', '<main id="main"><div id="not-found"></div></main>', source, count=1, flags=re.S)
    source = re.sub(r'<nav id="mobile-bottom-nav".*?</nav>', lambda _: mobile_navigation('', 'https://www.molberty.ru/404.html'), source, count=1, flags=re.S)
    (root / '404.html').write_text(source)
    copy_deployment_page(root)
    examples_path = root / 'qa/generated-schema.json'
    examples = json.loads(examples_path.read_text())
    examples['404.html'] = [json.loads(value) for value in re.findall(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', source)]
    examples_path.write_text(json.dumps(examples, ensure_ascii=False, indent=2) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--copy-only', action='store_true')
    args = parser.parse_args()
    copy_deployment_page() if args.copy_only else write_error_page()
