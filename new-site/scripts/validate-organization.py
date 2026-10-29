"""Validate Organization, its static delivery and Product seller references."""
import argparse
import json
import re
from collections import Counter
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit
from xml.etree import ElementTree
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]


class Schemas(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.active = False
        self.buffer = ''
        self.items = []
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        if tag == 'script' and dict(attrs).get('type') == 'application/ld+json':
            self.active = True
            self.buffer = ''

    def handle_data(self, data):
        if self.active:
            self.buffer += data

    def handle_endtag(self, tag):
        if tag == 'script' and self.active:
            self.items.append(json.loads(self.buffer))
            self.active = False


def absolute(value):
    url = urlsplit(value)
    assert url.scheme == 'https' and url.netloc == 'www.molberty.ru', value


def vocabulary_check(organization, path):
    """Check type/property names, inherited domains and value ranges."""
    graph = {node['@id']: node for node in json.loads(path.read_text())['@graph']}

    def ids(value):
        values = value if isinstance(value, list) else [value]
        return [v['@id'] for v in values if isinstance(v, dict) and '@id' in v]

    def ancestors(type_id):
        result = {type_id}
        for parent in ids(graph[type_id].get('rdfs:subClassOf', [])):
            if parent in graph:
                result.update(ancestors(parent))
        return result

    checked = Counter()

    def visit(node):
        type_id = 'schema:' + node['@type']
        assert type_id in graph and graph[type_id]['@type'] == 'rdfs:Class', type_id
        inherited = ancestors(type_id)
        checked['types'] += 1
        for key, values in node.items():
            if key.startswith('@'):
                continue
            prop = graph.get('schema:' + key)
            assert prop and prop['@type'] == 'rdf:Property', key
            assert inherited.intersection(ids(prop.get('schema:domainIncludes', []))), (type_id, key)
            allowed = set(ids(prop['schema:rangeIncludes']))
            for value in values if isinstance(values, list) else [values]:
                if isinstance(value, dict):
                    assert ancestors('schema:' + value['@type']).intersection(allowed), (key, allowed)
                    visit(value)
                else:
                    assert isinstance(value, str), (key, value)
                    assert 'schema:Text' in allowed or ('schema:URL' in allowed and urlsplit(value).scheme == 'https'), (key, allowed)
            checked['properties'] += 1

    visit(organization)
    seller = graph['schema:seller']
    assert 'schema:Organization' in ids(seller['schema:rangeIncludes'])
    for type_id in ['schema:Offer', 'schema:AggregateOffer']:
        assert ancestors(type_id).intersection(ids(seller['schema:domainIncludes']))
    return dict(checked)


def validate(vocabulary=None):
    org = json.loads((ROOT / 'data/organization.json').read_text())
    sales = json.loads((ROOT / 'data/sales.json').read_text())
    assert org['@context'] == 'https://schema.org' and org['@type'] == 'Organization'
    assert org['@id'] == org['url'] + '#organization'
    assert org['name'] == 'Мольберты.ру' and org['alternateName'] == 'Мастерская Иванова Д. В.'
    assert org['description'].strip() and org['email'] == sales['email']
    assert org['telephone'] == sales['retailPhone']
    assert {p['telephone'] for p in org['contactPoint']} == {sales['retailPhone'], sales['wholesalePhone']}
    for point in org['contactPoint']:
        assert point['@type'] == 'ContactPoint' and point['contactType'].strip()
        assert point['email'] == org['email'] and point['availableLanguage'] == 'ru'
        assert re.fullmatch(r'\+7 \(\d{3}\) \d{3}-\d{2}-\d{2}', point['telephone'])
        absolute(point['url'])
    address = org['address']
    assert address['@type'] == 'PostalAddress' and address['addressCountry'] == 'RU'
    assert address['addressLocality'] == 'Мытищи' and address['addressRegion'] == 'Московская область'
    assert address['streetAddress'] in sales['address']
    for key in ['@id', 'url', 'logo']:
        absolute(org[key])
    logo_path = ROOT / urlsplit(org['logo']).path.lstrip('/')
    logo = ElementTree.parse(logo_path).getroot()
    assert logo.tag == '{http://www.w3.org/2000/svg}svg'
    assert int(logo.attrib['width']) >= 112 and int(logo.attrib['height']) >= 112
    examples = json.loads((ROOT / 'qa/generated-schema.json').read_text())
    assert examples['index.html'][0] == org
    for route, schemas in examples.items():
        assert schemas == Schemas((ROOT / route).read_text()).items, route
    pages = redirects = products = blocks = 0
    for file in sorted([*ROOT.rglob('index.html'), ROOT / '404.html']):
        text = file.read_text()
        schemas = Schemas(text).items
        organizations = [s for s in schemas if s.get('@type') == 'Organization']
        if '<main id="main">' not in text:
            assert not organizations, file
            redirects += 1
            continue
        assert organizations == [org], file
        assert text.index('id="organization-schema"') < text.index('</head>'), file
        assert sum(s.get('@type') == 'BreadcrumbList' for s in schemas) == 1, file
        for product in [s for s in schemas if s.get('@type') == 'Product']:
            assert product['offers']['seller'] == {'@id': org['@id']}, file
            assert product['offers']['@type'] in ['Offer', 'AggregateOffer'], file
            products += 1
        pages += 1
        blocks += len(schemas)
    assert pages == 141 and redirects == 25 and products == 91
    result = {'passed': True, 'pages': pages, 'redirectsExcluded': redirects,
              'jsonLdBlocks': blocks, 'organizationNodes': pages, 'linkedProductOffers': products,
              'errors': [], 'warnings': [], 'logo': {'file': str(logo_path.relative_to(ROOT)), 'width': 512, 'height': 512}}
    if vocabulary:
        result['officialVocabulary'] = vocabulary_check(org, vocabulary)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--vocabulary', type=Path)
    parser.add_argument('--report', action='store_true')
    args = parser.parse_args()
    result = validate(args.vocabulary)
    if args.report:
        result['checkedAt'] = datetime.now(ZoneInfo('Europe/Moscow')).isoformat()
        (ROOT / 'qa/organization-schema-validation.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print('Organization: 141 страница, 91 связь Product → seller, JSON-LD и контакты: OK')
