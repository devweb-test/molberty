#!/usr/bin/env python3
"""Import the original four articles and their original imagery, without rewriting.

Source HTML and original assets are the local molberty.ru snapshot. Page chrome,
navigation and footer are excluded. Text, spelling, captions, and article order
are retained. Only unsafe HTML and presentation attributes are removed.
"""
import hashlib
import json
from pathlib import Path
import re
import sys

sys.path.insert(0, '/tmp/molberty-import-deps')
from bs4 import BeautifulSoup, NavigableString
from PIL import Image, ImageOps

SITE = Path(__file__).resolve().parents[1]
CACHE = SITE.parent / 'offline-page'
ROUTES = {
    'kak-vybrat-molbert': 'how_to_make_choice',
    'instrument-dlya-tvorchestva-molbert': 'page2566204',
    'molbert-v-sovremennom-interere': 'page2781362',
    'dvadcat-let-plodotvornoj-raboty': 'page2781437',
}

def norm(text):
    return re.sub(r'\s+', ' ', text or '').strip()

def plain(markup):
    return norm(BeautifulSoup(markup, 'html.parser').get_text(' ', strip=True))

def sanitize(markup):
    soup = BeautifulSoup(markup, 'html.parser')
    for tag in list(soup.find_all(True)):
        if tag.name in ('script', 'style', 'iframe', 'object'):
            tag.decompose()
        elif tag.name in ('p', 'br', 'strong', 'b', 'em', 'i', 'ul', 'ol', 'li', 'sub', 'sup'):
            tag.attrs = {}
        elif tag.name == 'a':
            href = tag.get('href', '')
            # External websites are removed from article copy; retain their label.
            if href.startswith(('mailto:', 'tel:', '#')) or (href.startswith('/') and not href.startswith('//')):
                tag.attrs = {'href': href}
            else:
                tag.unwrap()
        else:
            tag.unwrap()
    return str(soup).strip()

def paragraphs(node):
    # Blank lines in Tilda correspond to paragraph breaks. A single original br
    # remains a line break; no sentence splitting or editorial rewriting occurs.
    safe = sanitize(node.decode_contents())
    parts = re.split(r'(?:<br\s*/?>\s*){2,}', safe)
    result = []
    for part in parts:
        part = re.sub(r'^(?:\s*<br\s*/?>)+|(?:<br\s*/?>\s*)+$', '', part).strip()
        if plain(part):
            result.append((part, plain(part)))
    return result

def digest(value):
    return hashlib.sha256(value.encode('utf-8')).hexdigest()

def main():
    assets = json.loads((CACHE / 'asset-manifest.json').read_text())['assets']
    source_urls = {value: key for key, value in assets.items()}
    existing = json.loads((SITE / 'data/articles.json').read_text())
    output, reports = [], []
    exported = {}
    (SITE / 'assets/articles').mkdir(parents=True, exist_ok=True)

    def export_image(local, alt='', caption=''):
        original = source_urls.get(local)
        assert original and original.startswith('https://'), local
        if local not in exported:
            filename = 'articles/' + digest(original)[:16] + '.webp'
            dest = SITE / 'assets' / filename
            with Image.open(CACHE / local) as opened:
                image = ImageOps.exif_transpose(opened)
                if image.mode not in ('RGB', 'RGBA'):
                    image = image.convert('RGBA' if 'transparency' in image.info else 'RGB')
                image.thumbnail((1600, 1600), Image.Resampling.LANCZOS)
                image.save(dest, 'WEBP', quality=92, method=6)
                width, height = image.size
            exported[local] = {'file': filename, 'source': original, 'width': width, 'height': height,
                               'sourceSha256': hashlib.sha256((CACHE / local).read_bytes()).hexdigest(),
                               'outputSha256': hashlib.sha256(dest.read_bytes()).hexdigest()}
        record = exported[local]
        block = {k: record[k] for k in ('file', 'source', 'width', 'height')}
        block.update(type='image', alt=alt or caption or 'Иллюстрация статьи')
        if caption:
            block['caption'] = caption
        return block

    for prior in existing:
        aid, route = prior['id'], ROUTES[prior['id']]
        raw = (CACHE / (route + '.html')).read_text()
        soup = BeautifulSoup(raw, 'html.parser')
        header = soup.select_one('.r[data-record-type="18"]')
        title = norm(header.select_one('[field="title"]').get_text(' ', strip=True))
        descr = header.select_one('[field="descr"]')
        intro = BeautifulSoup(str(descr), 'html.parser')
        publication = None
        for text in list(intro.find_all(string=True)):
            if 'Журнал' in text:
                publication = norm(str(text))
                text.extract()
        summary = norm(intro.get_text(' ', strip=True))
        intro_html = sanitize(intro.select_one('[field="descr"]').decode_contents())
        intro_html = re.sub(r'<(?:strong|b|em|i)>\s*</(?:strong|b|em|i)>', '', intro_html)
        intro_html = re.sub(r'(?:<br\s*/?>\s*)+$', '', intro_html).strip()
        year = re.search(r'\b(?:19|20)\d{2}\b', publication or '')
        author = None
        blocks = []
        source_text_list, source_caption_list = [], []
        source_records = []
        for rec in soup.select('.r'):
            typ = rec.get('data-record-type')
            if typ in ('451', '18', '144'):
                continue
            if typ == '372':
                author = norm(rec.select_one('[field="text"]').get_text(' ', strip=True))
                continue
            assert typ in ('106', '222', '223', '94', '36', '508'), (route, rec['id'], typ)
            record = {'id': rec['id'], 'type': typ, 'text': [], 'images': []}
            for element in rec.select('[field], img'):
                field = element.get('field', '')
                if field == 'text' or field.startswith('li_descr__') or (typ == '94' and field == 'title'):
                    record['text'].append(norm(element.get_text(' ', strip=True)))
                    source_text_list.append(norm(element.get_text(' ', strip=True)))
                    for html, text in paragraphs(element):
                        blocks.append({'type': 'paragraph', 'html': html, 'text': text, 'sourceRecord': rec['id']})
                elif element.name == 'img':
                    local = element.get('data-original', element.get('src'))
                    captions = [norm(x.get_text(' ', strip=True)) for x in rec.select('[field="imgtitle"], [field="imgdescr"]')]
                    caption = ' '.join(x for x in captions if x)
                    if caption:
                        source_caption_list.append(caption)
                    block = export_image(local, norm(element.get('alt', '')), caption)
                    block['sourceRecord'] = rec['id']
                    blocks.append(block)
                    record['images'].append(block['source'])
            source_records.append(record)
        reconstructed = norm(' '.join(b['text'] for b in blocks if b['type'] == 'paragraph'))
        expected_text = norm(' '.join(source_text_list))
        assert reconstructed == expected_text, (aid, 'text differs after sanitization')
        expected_images = len(soup.select('.r[data-record-type="222"] img, .r[data-record-type="223"] img, .r[data-record-type="94"] img'))
        body_images = [b for b in blocks if b['type'] == 'image']
        assert len(body_images) == expected_images
        assert len(body_images) == (3 if route == 'how_to_make_choice' else 4)
        cover_local = header.select_one('[data-content-cover-bg]')['data-content-cover-bg']
        cover = export_image(cover_local, title)
        article = {key: prior[key] for key in ('id', 'topic', 'category')}
        article.update(title=title, source=prior['source'], year=year[0] if year else None,
                       publication=publication, originalAuthor=author, summary=summary,
                       introHtml=intro_html, verbatim=True, image=body_images[0]['file'],
                       imageStyle='source', imageWidth=body_images[0]['width'], imageHeight=body_images[0]['height'],
                       coverImage=cover['file'], coverSource=cover['source'],
                       coverWidth=cover['width'], coverHeight=cover['height'], blocks=blocks,
                       sections=[{'id': 'original', 'title': '', 'paragraphs': [b['text'] for b in blocks if b['type'] == 'paragraph']}])
        output.append(article)
        reports.append({'id': aid, 'source': prior['source'], 'sourceFile': str(CACHE / (route + '.html')),
                        'sourceHtmlSha256': hashlib.sha256((CACHE / (route + '.html')).read_bytes()).hexdigest(), 'title': title,
                        'intro': summary, 'publication': publication, 'originalAuthor': author,
                        'bodyTextSha256': digest(expected_text), 'exportedTextSha256': digest(reconstructed),
                        'textMatchesOriginal': reconstructed == expected_text,
                        'bodyCharacters': len(expected_text), 'originalTextList': source_text_list,
                        'originalCaptionList': source_caption_list,
                        'paragraphCount': sum(b['type'] == 'paragraph' for b in blocks),
                        'bodyImageCount': len(body_images), 'coverSource': cover['source'],
                        'sourceRecords': source_records,
                        'bodyImages': [{k: b[k] for k in ('file', 'source', 'width', 'height')} for b in body_images]})
    assert len(output) == 4
    assert sum(len([b for b in a['blocks'] if b['type'] == 'image']) for a in output) == 15
    (SITE / 'data/articles.json').write_text(json.dumps(output, ensure_ascii=False, indent=2) + '\n')
    report = {'source': 'Original molberty.ru HTML snapshot from 2026-10-16',
              'policy': 'Original text, original spelling, original image order. No editorial additions, generated illustrations or retouching. Only whitespace, HTML presentation attributes and paragraph boundaries normalized.',
              'articleCount': len(output), 'bodyImageCount': 15, 'coverImageCount': 4,
              'uniqueExportedImages': len(exported), 'articles': reports,
              'images': list(exported.values())}
    (SITE / 'data/article-source-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps([{k: a[k] for k in ('id', 'bodyCharacters', 'paragraphCount', 'bodyImageCount', 'textMatchesOriginal')} for a in reports], ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
