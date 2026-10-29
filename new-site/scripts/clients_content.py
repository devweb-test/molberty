"""Shared assets and a focused export of the real-client directory."""
from pathlib import Path
import json
import os
import re
from mobile_navigation import mobile_navigation
from error_page import copy_deployment_page

ROOT = Path(__file__).resolve().parents[1]


def clients_assets(prefix, content):
    if 'id="home"' not in content and 'id="clients-page"' not in content:
        return ''
    return f'<link rel="stylesheet" href="{prefix}assets/clients.css?v=59"><script defer src="{prefix}assets/clients-data.js?v=59"></script>'


def sync_clients_data(root=ROOT):
    directory = json.loads((root / 'data/clients.json').read_text())
    clients = directory['clients']
    source = directory['source']
    assert len(clients) == len({c['id'] for c in clients})
    assert len([c for c in clients if c['sourceRows']]) == source['uniqueOrganizations']
    assert {c['id'] for c in clients if not c['sourceRows']} == set(source.get('additionalClientIds', []))
    assert sorted(row for c in clients for row in c['sourceRows']) == list(range(1, source['sourceRows'] + 1))
    assert len(directory['featuredIds']) == len(set(directory['featuredIds']))
    assert set(directory['featuredIds']) <= {c['id'] for c in clients}
    assert all(c['group'] in directory['groups'] and c['name'] and c['identitySources'] for c in clients)
    for client in clients:
        logo = client.get('logo')
        if not logo:
            continue
        assert (root / 'assets' / logo['file']).is_file(), client['id']
        assert logo['width'] > 0 and logo['height'] > 0
        assert not logo.get('background') or re.fullmatch(r'#[0-9a-fA-F]{6}', logo['background'])
    (root / 'assets/clients-data.js').write_text('window.CLIENT_DIRECTORY = ' + json.dumps(directory, ensure_ascii=False) + ';\n')
    return directory


def write_clients_page(root=ROOT):
    """Reuse a service-page shell without rebuilding unrelated content pages."""
    sync_clients_data(root)
    # Add the directory to the shared footer, preserving every existing main body.
    for file in [*root.rglob('index.html'), root / '404.html']:
        source = file.read_text()
        if '<main id="main">' not in source:
            continue
        prefix = os.path.relpath(root, file.parent).replace(os.sep, '/')
        prefix = '' if prefix == '.' else prefix + '/'
        footer = source.index('<div id="footer">')
        head, tail = source[:footer], source[footer:]
        link = f'<a href="{prefix}clients/">Наши клиенты</a>'
        if link not in tail:
            anchor = f'<a href="{prefix}documents/">Документы</a>'
            assert tail.count(anchor) == 1, file
            tail = tail.replace(anchor, anchor + link, 1)
            file.write_text(head + tail)
    home = root / 'index.html'
    source = home.read_text()
    if 'assets/clients-data.js' not in source:
        source = source.replace('<script defer src="assets/app.js">', clients_assets('', '<div id="home">') + '<script defer src="assets/app.js">', 1)
        home.write_text(source)
    source = (root / 'about/index.html').read_text()
    source = re.sub(r'<title>.*?</title>', '<title>Наши клиенты — Мольберты.ру</title>', source, count=1)
    source = re.sub(r'<meta name="description"[^>]*>', '<meta name="description" content="Клиенты нашего производства: университеты, художественные школы, музеи, театры и другие организации. Логотипы и полный список.">', source, count=1)
    source = re.sub(r'<link rel="canonical"[^>]*>', '<link rel="canonical" href="https://www.molberty.ru/clients/">', source, count=1)
    crumbs = {'@context': 'https://schema.org', '@type': 'BreadcrumbList', 'itemListElement': [
        {'@type': 'ListItem', 'position': 1, 'name': 'Главная', 'item': 'https://www.molberty.ru/'},
        {'@type': 'ListItem', 'position': 2, 'name': 'Наши клиенты', 'item': 'https://www.molberty.ru/clients/'},
    ]}
    source = re.sub(r'(<script id="breadcrumb-schema"[^>]*>).*?(</script>)', lambda m: m[1] + json.dumps(crumbs, ensure_ascii=False) + m[2], source, count=1, flags=re.S)
    source = re.sub(r'<main id="main">.*?</main>', '<main id="main"><div id="clients-page"></div></main>', source, count=1, flags=re.S)
    source = source.replace('<script defer src="../assets/app.js">', clients_assets('../', '<div id="clients-page">') + '<script defer src="../assets/app.js">', 1)
    source = re.sub(r'<nav id="mobile-bottom-nav".*?</nav>', lambda _: mobile_navigation('../', 'https://www.molberty.ru/clients/'), source, count=1, flags=re.S)
    target = root / 'clients'
    target.mkdir(exist_ok=True)
    (target / 'index.html').write_text(source)
    examples_path = root / 'qa/generated-schema.json'
    examples = json.loads(examples_path.read_text())
    examples['clients/index.html'] = [json.loads(value) for value in re.findall(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', source)]
    examples_path.write_text(json.dumps(examples, ensure_ascii=False, indent=2) + '\n')
    copy_deployment_page(root)


if __name__ == '__main__':
    write_clients_page()
