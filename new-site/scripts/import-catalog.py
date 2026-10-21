#!/usr/bin/env python3
"""Rebuild the product dataset from original molberty.ru HTML.

Run with bs4 and Pillow installed (or available in /tmp/molberty-import-deps).
The source option prices are authoritative: visible option labels occasionally
contain older amounts. Such differences are kept in the source audit report.
"""
from pathlib import Path
import collections
import hashlib
import html
import json
import re
import sys
import argparse
from datetime import datetime
from urllib.parse import urlparse
import requests

sys.path.insert(0, '/tmp/molberty-import-deps')
from bs4 import BeautifulSoup
from PIL import Image, ImageOps

SITE = Path(__file__).resolve().parents[1]
CACHE = SITE.parent / 'offline-page'
OUT = SITE / 'assets/catalog'
SOURCES = {'for_artist': 'artist', 'for_exibition': 'exhibition',
           'for_interior': 'interior', 'for_studio': 'studio'}
GROUPS = {'46139268': 'stationaries', '49043039': 'transformers',
          '49043414': 'lira', '49044079': 'a-style', '49044175': 'clappers',
          '49047569': 'drawing-tables', '1570890501': 'desktops'}
CYR = dict(zip('абвгдеёжзийклмнопрстуфхцчшщъыьэюя',
               ['a','b','v','g','d','e','e','zh','z','i','y','k','l','m',
                'n','o','p','r','s','t','u','f','kh','ts','ch','sh','shch',
                '', 'y','', 'e','yu','ya']))

def norm(value):
    return re.sub(r'\s+', ' ', value or '').strip()

def slug(value):
    return re.sub(r'[^a-z0-9]+', '-', ''.join(CYR.get(c, c) for c in value.lower())).strip('-')

def number(value):
    value = re.sub(r'\s+', '', value or '').replace(',', '.')
    try:
        result = float(value)
        return int(result) if result.is_integer() else result
    except ValueError:
        return None

def description_markup(node):
    soup = BeautifulSoup(str(node), 'html.parser')
    for child in list(soup.find_all(True)):
        if child.name in ('script', 'style', 'iframe', 'object'):
            child.decompose()
        elif child.name in ('p', 'br', 'b', 'strong', 'em', 'i', 'ul', 'ol', 'li'):
            child.attrs = {}
        else:
            child.unwrap()
    return str(soup).strip()

def material(name, size):
    value = (name + ' ' + size).lower()
    result = []
    for pattern, label in [(r'\bбук\b', 'Бук'), (r'\bсосна\b', 'Сосна'),
                           (r'фанер', 'Фанера'), (r'берез|берёз', 'Берёза'),
                           (r'металл', 'Металл')]:
        if re.search(pattern, value):
            result.append(label)
    return ', '.join(result) or None

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-directory', type=Path, help='Directory containing complete source HTML (all four routes).')
    parser.add_argument('--snapshot', action='store_true', help='Explicitly use the old offline-page snapshot instead of live source.')
    parser.add_argument('--source-date', default=datetime.now().strftime('%Y-%m-%d'))
    args = parser.parse_args()
    manifest = json.loads((CACHE / 'asset-manifest.json').read_text())
    original_urls = {value: key for key, value in manifest['assets'].items()}
    source_directory = args.source_directory or (CACHE if args.snapshot else Path('/tmp/molberty-live-source'))
    source_directory.mkdir(parents=True, exist_ok=True)
    if args.source_directory is None and not args.snapshot:
        for route in SOURCES:
            last_error = None
            for attempt in range(8):
                try:
                    response = requests.get('https://www.molberty.ru:443/' + route, timeout=(8, 20))
                    response.raise_for_status()
                    assert len(response.content) > 20000
                    (source_directory / (route + '.html')).write_bytes(response.content)
                    break
                except (requests.RequestException, AssertionError) as error:
                    last_error = error
            else:
                raise RuntimeError(f'Unable to retrieve complete live source for {route}: {last_error}; no stale fallback is used.')
    previous = json.loads((SITE / 'data/products-source.json').read_text()) if (SITE / 'data/products-source.json').exists() else {'products': [], 'legacyIdMap': {}}
    previous_by_source = {p['sourceId']: p for p in previous['products']}
    products, anomalies = [], []
    exported_images = {}
    seen_slugs = collections.Counter()
    OUT.mkdir(parents=True, exist_ok=True)

    def save_image(local, source):
        if source in exported_images:
            return exported_images[source]
        filename = 'catalog/' + hashlib.sha256(source.encode()).hexdigest()[:16] + '.webp'
        dest = SITE / 'assets' / filename
        if dest.is_file():
            exported_images[source] = filename
            return filename
        cached = manifest['assets'].get(source)
        local_path = CACHE / cached if cached else CACHE / local
        if not local_path.is_file():
            downloaded = Path('/tmp/molberty-live-source-images')
            downloaded.mkdir(exist_ok=True)
            local_path = downloaded / (hashlib.sha256(source.encode()).hexdigest() + Path(urlparse(source).path).suffix)
            if not local_path.is_file():
                response = requests.get(source, timeout=30)
                response.raise_for_status()
                local_path.write_bytes(response.content)
        with Image.open(local_path) as opened:
            img = ImageOps.exif_transpose(opened)
            if img.mode not in ('RGB', 'RGBA'):
                img = img.convert('RGBA' if 'transparency' in img.info else 'RGB')
            img.thumbnail((1400, 1400), Image.Resampling.LANCZOS)
            img.save(dest, 'WEBP', quality=89, method=6)
        exported_images[source] = filename
        return filename

    for route, family in SOURCES.items():
        soup = BeautifulSoup((source_directory / (route + '.html')).read_text(), 'html.parser')
        seen_source_ids = set()
        for card in soup.select('.t754__col.js-product'):
            rec = card.find_parent(class_='r')
            recid, lid = rec['id'].removeprefix('rec'), card['data-product-lid']
            source_id = f'{route}-{recid}-{lid}'
            if source_id in seen_source_ids:
                continue
            seen_source_ids.add(source_id)
            popup = rec.select_one('#t754__product-' + lid)
            name = norm(popup.select_one('.js-product-name').get_text(' ', strip=True))
            product_slug = slug(name)
            seen_slugs[product_slug] += 1
            if seen_slugs[product_slug] > 1:
                product_slug += '-' + family
            size_node = card.select_one('.t754__descr')
            size = norm(size_node.get_text(' ', strip=True)) if size_node else ''
            descr = popup.select_one('.t754__wrapper > .t754__descr')
            assert descr is not None, name
            description_html = description_markup(descr)
            description_plain = norm(descr.get_text(' ', strip=True))
            raw_price = norm(card.select_one('.js-product-price').get_text(' ', strip=True))
            options = []
            price_index = retail_size_index = wholesale_size_index = None
            minimum = None
            notes = []
            for opt in popup.select('.t-product__option'):
                title = norm(opt.select_one('.js-product-option-name').get_text(' ', strip=True))
                values = []
                for value in opt.select('option'):
                    label = norm(value.get_text(' ', strip=True))
                    raw = norm(value.get('data-product-variant-price', ''))
                    amount = number(raw)
                    mode = 'delta' if raw.startswith(('+', '-')) and amount is not None else 'absolute' if amount is not None else 'none'
                    price_source = 'data' if amount is not None else 'none'
                    if amount is None:
                        label_delta = re.fullmatch(r'\+\s*(\d+)(?:\s*р(?:уб)?\.?)?', label)
                        label_absolute = re.search(r';\s*(\d+)\s*р(?:уб)?\.?\s*$', label)
                        if label_delta:
                            amount, mode, price_source = int(label_delta[1]), 'delta', 'label'
                        elif label_absolute:
                            amount, mode, price_source = int(label_absolute[1]), 'absolute', 'label'
                        if price_source == 'label':
                            note = f'Для опции «{title}: {label}» числовая надбавка взята из явно указанной цены в подписи: атрибут цены в источнике пуст.'
                            notes.append(note)
                            anomalies.append({'product': product_slug, 'type': 'option-price-from-label', 'note': note})
                    values.append({'label': label, 'price': amount, 'mode': mode,
                                   'rawVariantPrice': raw, 'priceSource': price_source})
                    if amount is not None and mode == 'delta':
                        label_amount = re.search(r'(\d+)\s*р(?:уб)?\.?\s*$', label)
                        if label_amount and int(label_amount.group(1)) != amount:
                            anomalies.append({'product': product_slug, 'type': 'option-label-price-mismatch',
                                              'option': title, 'label': label, 'price': amount})
                    elif amount is None and re.search(r'\+\s*\d', label):
                        note = f'Для опции «{title}: {label}» источник не задаёт числовую надбавку.'
                        notes.append(note)
                        anomalies.append({'product': product_slug, 'type': 'missing-option-price', 'note': note})
                idx = len(options)
                option = {'name': title, 'values': values}
                if re.search(r'выберите цену', title, re.I):
                    price_index = idx
                elif re.search(r'розниц', title, re.I):
                    option['priceTier'] = 'retail'
                    retail_size_index = idx
                elif re.search(r'опт', title, re.I):
                    option['priceTier'] = 'wholesale'
                    wholesale_size_index = idx
                tier_text = title + ' ' + ' '.join(v['label'] for v in values)
                if re.search(r'опт', tier_text, re.I):
                    match = re.search(r'от\s*(\d+)\s*шт', tier_text, re.I)
                    minimum = int(match.group(1)) if match else 10
                options.append(option)

            retail = wholesale = None
            retail_from = wholesale_from = False
            if price_index is not None:
                for value in options[price_index]['values']:
                    if re.search(r'розниц', value['label'], re.I):
                        retail = value['price']
                    elif re.search(r'опт', value['label'], re.I):
                        wholesale = value['price']
                raw_pair = re.fullmatch(r'(\d+)\s*/\s*(\d+)(?:\s+.*)?', raw_price)
                if raw_pair and [int(raw_pair[1]), int(raw_pair[2])] != [wholesale, retail]:
                    anomalies.append({'product': product_slug, 'type': 'raw-price-option-mismatch',
                                      'rawPrice': raw_price, 'retailPrice': retail, 'wholesalePrice': wholesale})
            elif retail_size_index is not None:
                retail = next((v['price'] for v in options[retail_size_index]['values'] if v['price'] is not None), None)
                if wholesale_size_index is not None:
                    wholesale = next((v['price'] for v in options[wholesale_size_index]['values'] if v['price'] is not None), None)
            else:
                pair = re.fullmatch(r'(\d+)\s*/\s*(\d+)(?:\s+.*)?', raw_price)
                if pair:
                    wholesale, retail = int(pair[1]), int(pair[2])
                    minimum = 10
                else:
                    match = re.search(r'\d[\d\s]*(?:[.,]\d+)?', raw_price)
                    retail = number(match[0]) if match else None
                    retail_from = bool(re.search(r'\bот\b', raw_price, re.I))
                # A size option gives an exact price for the default selected variant.
                for option in options:
                    if 'размер' in option['name'].lower():
                        first = next((v for v in option['values'] if v['price'] is not None), None)
                        if first and first['mode'] == 'absolute':
                            retail = first['price']
                            retail_from = False
                            break
            if 'за секцию' in raw_price:
                notes.append('Цена указана за одну секцию.')
            gallery = []
            seen_images = set()
            for img in popup.select('.t754__default-gallery [data-img-zoom-url]'):
                local = img['data-img-zoom-url']
                if local in seen_images:
                    continue
                seen_images.add(local)
                source = local if local.startswith('https://') else original_urls.get(local)
                if not source:
                    parent = img.find_parent(class_='t-slds__wrapper')
                    meta = parent.select_one('meta[itemprop=image]') if parent else None
                    source = meta['content'] if meta else local
                gallery.append({'file': save_image(local, source), 'source': source})
            assert gallery, name
            group_title = rec.find_previous(class_='t-title')
            product = {'id': product_slug, 'name': name,
                       'sourceId': source_id,
                       'sourceUrl': f'https://www.molberty.ru/{route}#!/tproduct/{recid}-{lid}',
                       'sourceFamily': family,
                       'sourceGroup': GROUPS.get(recid, family),
                       'sourceGroupTitle': norm(group_title.get_text(' ', strip=True)) if group_title else '',
                       'description': description_plain, 'descriptionHtml': description_html,
                       'size': size, 'material': material(name, size),
                       'isNew': bool(card.select_one('.t754__mark') and 'NEW' in card.select_one('.t754__mark').get_text().upper()),
                       'gallery': gallery, 'image': gallery[0]['file'],
                       'options': options, 'priceOptionIndex': price_index,
                       'retailSizeOptionIndex': retail_size_index,
                       'wholesaleSizeOptionIndex': wholesale_size_index,
                       'retailPrice': retail, 'wholesalePrice': wholesale,
                       'retailFrom': retail_from, 'wholesaleFrom': wholesale_from,
                       'fromPrice': bool(re.search(r'\bот\b', raw_price, re.I)),
                       'rawPrice': raw_price, 'wholesaleMin': minimum,
                       'priceNote': ' '.join(notes)}
            if retail_size_index is not None:
                product['minRetailPrice'] = min(v['price'] for v in options[retail_size_index]['values'] if v['price'] is not None)
            if wholesale_size_index is not None:
                product['minWholesalePrice'] = min(v['price'] for v in options[wholesale_size_index]['values'] if v['price'] is not None)
            products.append(product)

    by_name = {p['name']: p['id'] for p in products}
    legacy_names = {'lira-classic': 'Раскладной "Лира"', 'lira-beech': 'Раскладной "Лира" (бук)',
                    'studio-beech': 'Станковый стационарный (бук)', 'studio-pine': 'Станковый стационарный (сосна)',
                    'hlopushka-a1': 'Хлопушка А1', 'hlopushka-double': 'Хлопушка А1 двусторонний',
                    'transformer-a1': 'Трансформер А1 (бук)', 'desktop': 'Настольный (сосна)',
                    'mini': 'Настольный "Мини" (бук)', 'grafika': 'Планшет настольный "Графика"',
                    'expo': 'Экспо-1', 'tripod': 'Тренога 1500', 'gift': '"Лира" подарочный (бук)',
                    'still-life': 'Стол для натюрморта складной', 'table-transformer': 'Стол-трансформер для натюрморта.',
                    'rack': 'Подставка для рисунков (бук)'}
    legacy = {old: by_name[name] for old, name in legacy_names.items() if name in by_name}
    current_by_source = {p['sourceId']: p for p in products}
    old_slug_to_current = {old['id']: current_by_source[sid]['id'] for sid, old in previous_by_source.items() if sid in current_by_source}
    for old_alias, old_target in previous.get('legacyIdMap', {}).items():
        if old_target in old_slug_to_current:
            legacy[old_alias] = old_slug_to_current[old_target]
    renamed = []
    for source_id, current in current_by_source.items():
        old = previous_by_source.get(source_id)
        if old and old['name'] != current['name']:
            renamed.append({'sourceId': source_id, 'oldId': old['id'], 'newId': current['id'], 'oldName': old['name'], 'newName': current['name']})
            if old['id'] != current['id']:
                legacy[old['id']] = current['id']
    added = [{'sourceId': p['sourceId'], 'id': p['id'], 'name': p['name']} for p in products if p['sourceId'] not in previous_by_source]
    removed = [p for sid, p in previous_by_source.items() if sid not in current_by_source]
    # Persist earlier removed records so repeat imports do not lose the audit trail.
    removed_by_source = {p['sourceId']: p for p in previous.get('report', {}).get('removedProducts', [])}
    removed_by_source.update({p['sourceId']: p for p in removed})
    removed_by_source = {sid: p for sid, p in removed_by_source.items() if sid not in current_by_source}
    counts = dict(collections.Counter(p['sourceFamily'] for p in products))
    assert all(counts.get(family, 0) > 0 for family in SOURCES.values()), counts
    assert len(set(p['id'] for p in products)) == len(products)
    assert len(current_by_source) == len(products)
    report = {'source': f'Original molberty.ru HTML {"offline snapshot" if args.snapshot else "live source"}, retrieved {args.source_date}',
              'sourceDate': args.source_date,
              'sourceHtml': {route: {'url': 'https://www.molberty.ru/' + route,
                                    'sha256': hashlib.sha256((source_directory / (route + '.html')).read_bytes()).hexdigest(),
                                    'productCount': counts[family]} for route, family in SOURCES.items()},
              'sourceCounts': counts,
              'artistGroups': dict(collections.Counter(p['sourceGroup'] for p in products if p['sourceFamily'] == 'artist')),
              'productCount': len(products), 'galleryImageCount': sum(len(p['gallery']) for p in products),
              'uniqueImages': len(exported_images), 'newProducts': [p['id'] for p in products if p['isNew']],
              'optionModes': dict(collections.Counter(v['mode'] for p in products for option in p['options'] for v in option['values'])),
              'splitTierSizeProducts': [p['id'] for p in products if p['retailSizeOptionIndex'] is not None],
              'wholesaleMinimums': dict(collections.Counter(str(p['wholesaleMin']) for p in products if p['wholesalePrice'] is not None)),
              'priceHandling': 'Explicit option data-product-variant-price wins over conflicting visible amounts. Options with no source price have no invented surcharge.',
              'previousProductCount': len(previous['products']), 'addedProducts': added, 'renamedProducts': renamed,
              'removedProducts': list(removed_by_source.values()),
              'anomalies': anomalies}
    (SITE / 'data/products-source.json').write_text(json.dumps({'products': products, 'legacyIdMap': legacy, 'report': report}, ensure_ascii=False, indent=2) + '\n')
    (SITE / 'data/source-catalog-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({k: v for k, v in report.items() if k != 'anomalies'}, ensure_ascii=False, indent=2))
    print('Source price anomalies:', len(anomalies))

if __name__ == '__main__':
    main()
