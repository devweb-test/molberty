from pathlib import Path
import json,re,sys
root=Path(__file__).resolve().parents[1]
d=json.loads((root/'data/catalog.json').read_text());errors=[]
structure=json.loads((root/'data/catalog-structure.json').read_text())
review=json.loads((root/'data/structure-product-review.json').read_text())
assert [c['id'] for c in d['categories']]==[c['id'] for c in structure['categories']]
assert d['categoryRoots']==[d['categoryRoles'][role] for role in structure['roots']]
by_id={c['id']:c for c in d['categories']}
for category in d['categories']:
 assert category['pathIds'][-1]==category['id']
 assert category['parentId']==(category['pathIds'][-2] if len(category['pathIds'])>1 else None)
 assert category['childIds']==[c['id'] for c in d['categories'] if c['parentId']==category['id']]
 assert any(category['id'] in p['categories'] for p in d['products']),category['id']+' empty'
 assert all(by_id[id]['depth']==index for index,id in enumerate(category['pathIds']))
assert {role:sum(id in p['categories'] for p in d['products']) for role,id in d['categoryRoles'].items() if role in structure['roots']}==review['uniqueRootCounts']
for product in d['products']:
 placement=review['mapping'][product['id']]
 expected={id for role in [placement['primaryGroup'],*placement['secondaryGroups']] for id in by_id[d['categoryRoles'][role]]['pathIds']}
 assert set(product['categories'])==expected and len(product['categories'])==len(expected)
 assert product['primaryCategoryId']==d['categoryRoles'][placement['primaryGroup']]
 assert product['primaryRootId']==by_id[product['primaryCategoryId']]['pathIds'][0]
excluded=set(json.loads((root/'data/category-exclusions.json').read_text()))
assert not excluded.intersection(c['id'] for c in d['categories'])
assert all(not excluded.intersection(p['categories']) for p in d['products'])
assert all(p['categories'] and p['primaryCategoryId'] not in excluded for p in d['products'])
assert all(not (root/id/'index.html').exists() for id in excluded)
for c in d['categories']:
 if not (root/c['id']/'index.html').is_file(): errors.append(c['id'])
for p in d['products']:
 for f in [root/'assets'/p['image'],root/'product'/p['id']/'index.html']:
  if not f.is_file():errors.append(str(f))
for a in d.get('articles',[]):
 if not (root/'blog'/a['id']/'index.html').is_file():errors.append(a['id'])
 if not (root/'assets'/a['image']).is_file():errors.append(a['image'])
 if not a.get('sections') or not a.get('source'):errors.append('Missing article content: '+a['id'])
if 'prices' in d:
 price=d['prices'];items=[item for section in price['sections'] for item in section['items']]
 if len(items)!=106 or len({x['id'] for x in items})!=106:errors.append('Price list row count or IDs')
 if not (root/price['sourceFile']).is_file():errors.append('Price PDF missing')
 for item in items:
  for field in ['wholesale','retail']:
   if item[field] is not None and (not isinstance(item[field],int) or item[field]<0):errors.append(item['id']+' invalid '+field)
for f in root.rglob('*.html'):
 s=f.read_text()
 for href in re.findall(r'(?:href|src)="([^"]+)"',s):
  if href.startswith(('http:','https:','mailto:','tel:','#','data:')):continue
  target=(f.parent/href.split('#')[0]).resolve()
  if not target.exists():errors.append(f'{f}: {href}')
print(f'{len(list(root.rglob("*.html")))} страниц; {len(d["categories"])} категории; {len(d["products"])} товаров.')
if errors:print('\n'.join(errors));sys.exit(1)
print('Локальные файлы, ссылки и изображения: OK')
# Catalogue integrity and JSON-LD in the exported HTML, without executing JavaScript.
from html.parser import HTMLParser
class Page(HTMLParser):
 def __init__(self,text):
  super().__init__();self.in_json=False;self.in_h1=False;self.json_text='';self.schemas=[];self.heading='';self.nested_heading=False;self.feed(text)
 def handle_starttag(self,tag,attrs):
  attrs=dict(attrs)
  if self.in_h1:self.nested_heading=True
  if tag=='h1':self.in_h1=True
  if tag=='script' and attrs.get('type')=='application/ld+json':self.in_json=True;self.json_text=''
 def handle_endtag(self,tag):
  if tag=='h1':self.in_h1=False
  if tag=='script' and self.in_json:self.schemas.append(json.loads(self.json_text));self.in_json=False
 def handle_data(self,data):
  if self.in_json:self.json_text+=data
  if self.in_h1:self.heading+=data
source=json.loads((root/'data/products-source.json').read_text())
materials=json.loads((root/'data/product-materials.json').read_text())
for product in d['products']:
 assert product.get('material') and product['material']!='Мастерская Иванова Д. В.'
 if product['id'] in materials['products']:
  entry=materials['products'][product['id']]
  assert product['material']==entry['label'] and product['features']['materials']==entry['materials']
  assert entry['evidence'] and entry['sourceId']==product['sourceId']
for file in root.rglob('index.html'):
 text=file.read_text()
 for meta in re.findall(r'<div class="product-meta">(.*?)</div>',text,re.S):
  assert meta.strip() and 'Мастерская Иванова' not in meta,file

assert len(d['products'])==len(source['products'])==len({p['sourceId'] for p in d['products']})==review['actualProductCount']
assert {p['id'] for p in d['products']}==set(review['mapping'])
assert sum(len(p['gallery']) for p in d['products'])==sum(len(p['gallery']) for p in source['products'])
assert sum(p['isNew'] for p in d['products'])==sum(p['isNew'] for p in source['products'])
for role,count in {'artists/floor/professional':13,'artists/floor/students':9,'artists/floor/lira':10,'artists/desktop':8}.items():
 assert sum(d['categoryRoles'][role] in p['categories'] for p in d['products'])==count,role
# Requested children must contain the complete original construction groups.
for id,parent,source_group,name in [
 ('molberty-stankovye','professionalnye-molberty','stationaries','Станковые мольберты'),
 ('molberty-transformery','professionalnye-molberty','transformers','Мольберты трансформеры'),
 ('molberty-hlopushka','molberty-dlya-hudozhestvennyh-shkol','clappers','Мольберты Хлопушка')]:
 category=by_id[id]
 assert category['parentId']==parent and category['name']==name
 assert {p['sourceId'] for p in d['products'] if id in p['categories']}=={p['sourceId'] for p in source['products'] if p['sourceGroup']==source_group}
 html=(root/id/'index.html').read_text()
 assert 'http-equiv="refresh"' not in html and Page(html).heading==name
assert Page((root/'molberty-dlya-hudozhestvennyh-shkol/index.html').read_text()).heading=='Мольберты для художественной школы'
for product in d['products']:
 original=next(x for x in source['products'] if x['sourceId']==product['sourceId'])
 for key in ['name','description','descriptionHtml','gallery','isNew']:assert product[key]==original[key],product['id']+' '+key
 assert re.fullmatch('[a-z0-9]+(?:-[a-z0-9]+)*',product['id'])
 for image in product['gallery']:assert (root/'assets'/image['file']).is_file()
 page=Page((root/'product'/product['id']/'index.html').read_text())
 assert page.heading==product['name'] and not page.nested_heading,product['id']+' h1'
 schema=next(s for s in page.schemas if s['@type']=='Product')
 assert schema['name']==product['name'] and schema['description']==product['description']
 assert len(schema['image'])==len(product['gallery'])
 assert schema['offers'].get('price',schema['offers'].get('lowPrice'))==product['defaultPrice'],product['id']+' price'
 assert schema['offers']['priceCurrency']=='RUB'
 trail=next(s for s in page.schemas if s['@type']=='BreadcrumbList')['itemListElement']
 assert [x['item'] for x in trail][2:-1]==['https://www.molberty.ru/'+id+'/' for id in by_id[product['primaryCategoryId']]['pathIds']]
 assert 'availability' not in schema['offers'] and 'aggregateRating' not in schema
for file in root.rglob('index.html'):
 text=file.read_text()
 if '<main id="main">' not in text:continue # legacy redirects
 assert 'assets/motion.css' in text and 'assets/motion.js' in text,file
 page=Page(text);breadcrumb=[s for s in page.schemas if s['@type']=='BreadcrumbList']
 assert len(breadcrumb)==1,file
 items=breadcrumb[0]['itemListElement']
 assert [x['position'] for x in items]==list(range(1,len(items)+1))
 for item in items:assert item['item'].startswith('https://www.molberty.ru/') and item['name'].strip()
 assert 'Фото изделия' not in text and 'Фотография этой модели' not in text
seo=d['categories'][0]['seo'];assert 2000<=len(seo['title']+' '+' '.join(seo['paragraphs']))<=2600
print('Каталог по Word, актуальный ассортимент и фото, Product, полные BreadcrumbList и h1: OK')
# Editorial presentation is separate from the immutable original article content.
presentation=json.loads((root/'data/article-presentation.json').read_text())
assert len(presentation)==4 and len({p['previewImage'] for p in presentation.values()})==4
for article in d['articles']:
 p=presentation[article['id']]
 assert (root/'assets'/p['previewImage']).is_file()
 indices=[i for section in p['sections'] for i in range(section['start'],section['end'])]
 assert indices==list(range(len(article['blocks'])))
 text=(root/'blog'/article['id']/'index.html').read_text()
 assert 'article-original-link' not in text and 'ПУБЛИКАЦИЯ ИЗ АРХИВА' not in text and 'Архив ·' not in text
 for section in p['sections']:assert 'id="'+section['id']+'"' in text and 'href="#'+section['id']+'"' in text
 assert 'blog-previews/' in text
print('4 тематические обложки, содержание статей и полное покрытие оригинальных блоков: OK')

class ArticleLinks(HTMLParser):
 def __init__(self):super().__init__();self.external=[]
 def handle_starttag(self,tag,attrs):
  if tag=='a':
   href=dict(attrs).get('href','').strip()
   if href.startswith(('http://','https://','//')):self.external.append(href)
for article in d['articles']:
 links=ArticleLinks();links.feed(article.get('introHtml',''))
 for block in article['blocks']:links.feed(block.get('html',''))
 assert not links.external,(article['id'],links.external)
print('Внешние ссылки в тексте четырёх статей: отсутствуют')

redirects=json.loads((root/'data/redirects.json').read_text())
for old,new in redirects.items():
 page=(root/old.strip('/')/'index.html').read_text()
 assert 'http-equiv="refresh"' in page and 'https://www.molberty.ru/'+new.lstrip('/') in page
 assert (root/new.strip('/')/'index.html').is_file()
# Requested exhibition URLs are category pages, including the former beech alias.
for role,old,new in [('exhibitions/pine','vystavochnye-molberty-iz-sosny','molberty-iz-sosny'),('exhibitions/beech','vystavochnye-molberty-iz-buka','molbert-iz-buka')]:
 assert d['categoryRoles'][role]==new
 assert redirects['/'+old+'/']=='/'+new+'/' and '/'+new+'/' not in redirects
 page=(root/new/'index.html').read_text()
 assert 'http-equiv="refresh"' not in page and 'https://www.molberty.ru/'+new+'/' in page
 assert sum(new in p['categories'] for p in d['products'])==4
 for file in root.rglob('index.html'):
  text=file.read_text()
  if '<main id="main">' in text:
   assert not any(old+'/' in href for href in re.findall(r'href="([^"]+)"',text)),str(file)+' old exhibition link'
print('Переадресация старых категорий и карточек: OK')

# Legal documents and the shared cookie component are delivered as static HTML.
legal=json.loads((root/'data/legal-pages.json').read_text())
assert (root/'assets/legal.js').read_text()=='window.LEGAL_PAGES='+json.dumps(legal,ensure_ascii=False,separators=(',',':'))+';\n'
for id,document in legal.items():
 text=(root/id/'index.html').read_text()
 assert Page(text).heading==document['title']
 assert document['html'] in text
 assert 'assets/legal.js' in text
 assert 'orlan' not in text.lower() and 'орлан' not in text.lower()
 assert 'molberty@gmail.com' in text
for file in root.rglob('index.html'):
 text=file.read_text()
 if '<main id="main">' not in text:continue
 assert text.count('id="cookie-notice"')==1 and text.count('assets/cookies.js')==1,file
 assert '>Обработка данных</a>' not in text,file
 assert 'Политика конфиденциальности</a><span>Создано для творчества' in text,file
print('Политика, соглашение, общий cookie-компонент и ссылки футера: OK')
from mobile_navigation import mobile_navigation
mobile_pages=0
for file in root.rglob('index.html'):
 text=file.read_text()
 if '<main id="main">' not in text:continue
 prefix='../'*len(file.relative_to(root).parts[:-1])
 canonical=re.search(r'<link rel="canonical" href="([^"]+)"',text)[1]
 assert text.count('id="mobile-bottom-nav"')==1,file
 assert mobile_navigation(prefix,canonical) in text,file
 assert 'width=device-width,initial-scale=1,viewport-fit=cover' in text,file
 mobile_pages+=1
assert mobile_pages==139
print('Мобильная нижняя навигация, ссылки и активные разделы: 139 страниц OK')
