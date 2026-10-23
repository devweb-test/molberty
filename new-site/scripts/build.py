from pathlib import Path
import json,html,os,hashlib
from legal_content import cookie_markup, document_markup
ROOT=Path(__file__).resolve().parents[1]
# Word taxonomy with the user's subsequent amendments; the original DOC stays unchanged.
structure=json.loads((ROOT/'data/catalog-structure.json').read_text())
review=json.loads((ROOT/'data/structure-product-review.json').read_text())
source=json.loads((ROOT/'data/products-source.json').read_text())
category_images=json.loads((ROOT/'data/home-category-images.json').read_text())
material_review=json.loads((ROOT/'data/product-materials.json').read_text())
assert set(material_review['products']).issubset(p['id'] for p in source['products'])
cats=structure['categories'];roles={c['role']:c['id'] for c in cats};by_id={c['id']:c for c in cats}
assert len(roles)==len(cats)==len(by_id)
for category in cats:
 category['parentId']=roles[category['parentRole']] if category['parentRole'] else None
 category['childIds']=[c['id'] for c in cats if c['parentRole']==category['role']]
 path=[];cursor=category
 while cursor:
  assert cursor['id'] not in path,'Category cycle'
  path.insert(0,cursor['id']);cursor=by_id[cursor['parentId']] if cursor['parentId'] else None
 category['pathIds']=path;category['depth']=len(path)-1
root_ids=[roles[role] for role in structure['roots']]
products=source['products'];mapping=review['mapping']
assert set(mapping)=={p['id'] for p in products},'Review every current product against the document'
for item in products:
 placement=mapping[item['id']];assert placement['sourceId']==item['sourceId']
 primary=roles[placement['primaryGroup']]
 assigned={id for role in [placement['primaryGroup'],*placement['secondaryGroups']] for id in by_id[roles[role]]['pathIds']}
 item['categories']=[c['id'] for c in cats if c['id'] in assigned]
 item['primaryCategoryId']=primary;item['primaryRootId']=by_id[primary]['pathIds'][0]
 item['illustration']=False;item['imageType']='source'
 safe=placement['safeFeatures']
 materials=sorted({e['value'] for e in [*safe['descriptionMaterials'],*safe['nameMaterials']]})
 if not materials and item.get('material'):materials=[item['material']]
 # Exhibition wood groups are supplied explicitly by the Word document.
 if placement['primaryGroup']=='exhibitions/pine' and not materials:materials=['Сосна']
 if placement['primaryGroup']=='exhibitions/beech' and not materials:materials=['Бук']
 resolved=material_review['products'].get(item['id'])
 if resolved:
  assert resolved['sourceId']==item['sourceId']
  assert resolved['sourceDescriptionSha256']==hashlib.sha256(item['description'].encode()).hexdigest(),item['id']+' material needs re-review'
  assert resolved['label'].strip() and resolved['materials'] and resolved['evidence']
  item['material']=resolved['label'];materials=resolved['materials'][:]
 item['features']={'materials':materials,'shelf':safe['shelf'],'sidedness':safe['sidedness']}
 item['source']=item['sourceUrl']
 text=(item['name']+' '+item['description']).lower()
 item['minimumOrder']=10 if ('только оптом от 10' in text or 'изготавливаются по заказу от 10' in text) else 1
 item['wholesaleOnly']='только оптом' in text
 # The original description says the inclined bar is available on request.
 for option in item['options']:
  if option['name']=='Наклонная штанга' and len(option['values'])==1:
   option['values'].insert(0,dict(label='Без наклонной штанги',price=None,mode='none',priceSource='description',rawVariantPrice=''))
 def initial_price(product):
  base=product['retailPrice'];delta=0
  for j,opt in enumerate(product['options']):
   if j==product['priceOptionIndex'] or opt.get('priceTier')=='wholesale':continue
   vals=[v for v in opt['values'] if v['label'].strip()]
   if opt.get('priceTier') or (vals and all(v['mode']=='absolute' for v in vals if v['label'] not in ['–','-'])):
    vals=[v for v in vals if v['mode']=='absolute']
   if not vals:continue
   v=vals[0]
   if v['mode']=='absolute':base=v['price']
   elif v['mode']=='delta':delta+=v['price']
  return base+delta
 item['defaultPrice']=initial_price(item)
 retail_variants=[v['price'] for j,o in enumerate(item['options']) if j!=item['priceOptionIndex'] and o.get('priceTier')!='wholesale' for v in o['values'] if v['mode']=='absolute']
 item['listingPrice']=min(retail_variants) if retail_variants else item['defaultPrice']
 item['listingFrom']=item['retailFrom'] or len(set(retail_variants))>1

for category in cats:
 match=next((item for item in products if item['primaryCategoryId']==category['id']),None) or next((item for item in products if category['id'] in item['categories']),None)
 assert match,'Empty category: '+category['id']
 presentation=category_images['categories'].get(category['role'])
 category['image']=presentation['image'] if presentation else match['image']
 if presentation:
  assert (ROOT/'assets'/presentation['image']).is_file()
  category['imageWidth']=presentation['width'];category['imageHeight']=presentation['height']
seo=json.loads((ROOT/'data/category-seo.json').read_text())
for category in cats:
 if category['id'] in seo:category['seo']=seo[category['id']]
# Previously removed global keyword categories stay absent; their contextual DOC branches have new URLs.
excluded=set(json.loads((ROOT/'data/category-exclusions.json').read_text()))
assert not excluded.intersection(by_id)
for id in excluded:
 directory=ROOT/id;(directory/'index.html').unlink(missing_ok=True)
 if directory.exists():directory.rmdir()
showcase=json.loads((ROOT/'data/showcase.json').read_text())
articles=json.loads((ROOT/'data/articles.json').read_text())
presentation=json.loads((ROOT/'data/article-presentation.json').read_text())
for article in articles:article['presentation']=presentation[article['id']]
prices=json.loads((ROOT/'data/prices.json').read_text())
price_links=json.loads((ROOT/'data/price-product-links.json').read_text())
price_ids={item['id'] for section in prices['sections'] for item in section['items']}
assert set(price_links['links']).isdisjoint(price_links['unlinked'])
assert set(price_links['links'])|set(price_links['unlinked'])==price_ids,'Review links for all price rows'
assert set(price_links['links'].values())<={product['id'] for product in products},'Price link points to a missing product'
sales=json.loads((ROOT/'data/sales.json').read_text())
company=json.loads((ROOT/'data/company.json').read_text())
data={'categories':cats,'products':products,'articles':articles,'showcase':showcase,'prices':prices,'priceProductLinks':price_links['links'],'sales':sales,'company':company,'legacyIdMap':source['legacyIdMap'],'categoryRoots':root_ids,'categoryRoles':roles}
(ROOT/'data/catalog.json').write_text(json.dumps(data,ensure_ascii=False,indent=2))
(ROOT/'assets/data.js').write_text('window.CATALOG = '+json.dumps(data,ensure_ascii=False)+';')
legal_pages=json.loads((ROOT/'data/legal-pages.json').read_text())
(ROOT/'assets/legal.js').write_text('window.LEGAL_PAGES='+json.dumps(legal_pages,ensure_ascii=False,separators=(',',':'))+';\n')
BASE='https://www.molberty.ru/'
def category_trail(id):
 return [(by_id[c]['name'],c+'/') for c in by_id[id]['pathIds']]
def structured(trail,product=None):
 blocks=[('breadcrumb-schema',{'@context':'https://schema.org','@type':'BreadcrumbList','itemListElement':[{'@type':'ListItem','position':i+1,'name':name,'item':BASE+route} for i,(name,route) in enumerate(trail)]})]
 if product:
  offer={'@type':'Offer','url':BASE+'product/'+product['id']+'/','priceCurrency':'RUB','price':product['defaultPrice']}
  if product['retailFrom']:
   offer={'@type':'AggregateOffer','url':offer['url'],'priceCurrency':'RUB','lowPrice':product['defaultPrice']}
  elif product['minimumOrder']>1:offer['eligibleQuantity']={'@type':'QuantitativeValue','minValue':product['minimumOrder']}
  blocks.append(('product-schema',{'@context':'https://schema.org','@type':'Product','@id':BASE+'product/'+product['id']+'/#product','url':BASE+'product/'+product['id']+'/','name':product['name'],'description':product['description'],'image':[BASE+'assets/'+img['file'] for img in product['gallery']],'offers':offer}))
 return ''.join('<script id="'+id+'" type="application/ld+json">'+json.dumps(obj,ensure_ascii=False).replace('<','\\u003c')+'</script>' for id,obj in blocks)
def shell(title,content,prefix='',desc=None,trail=None,product=None):
 schema=structured(trail or [('Главная','')],product)
 canonical=BASE+(trail[-1][1] if trail else '')
 legal_script=f'<script defer src="{prefix}assets/legal.js"></script>' if trail and trail[-1][1] in ('privacy/','consent/') else ''
 return f'''<!doctype html><html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="description" content="{html.escape(desc or 'Мольберты и оборудование для изостудий из натурального дерева. Мастерская Иванова Д. В. С 1991 года.')}"><meta name="robots" content="noindex, nofollow"><meta name="theme-color" content="#34483d"><link rel="canonical" href="{canonical}">{schema}<title>{html.escape(title)} — Мольберты.ру</title><link rel="icon" href="{prefix}assets/favicon.svg" type="image/svg+xml"><link rel="stylesheet" href="{prefix}assets/style.css"><link rel="stylesheet" href="{prefix}assets/motion.css"><script>window.SITE_ROOT={json.dumps(prefix)};</script><script defer src="{prefix}assets/cookies.js"></script>{legal_script}<script defer src="{prefix}assets/data.js"></script><script defer src="{prefix}assets/app.js"></script><script defer src="{prefix}assets/motion.js"></script></head><body><a class="skip" href="#main">Перейти к содержимому</a><div id="header"></div><main id="main">{content}</main><div id="footer"></div>{cookie_markup(prefix)}<dialog id="request-dialog"><button class="close" data-close aria-label="Закрыть">×</button><div id="dialog-content"></div></dialog><dialog id="image-dialog" aria-label="Просмотр изображения"><button class="close" data-image-close aria-label="Закрыть изображение">×</button><div class="image-viewer-toolbar"><button data-zoom="out" aria-label="Уменьшить">−</button><button data-zoom="reset">100%</button><button data-zoom="in" aria-label="Увеличить">+</button></div><div class="image-viewer-stage"><img id="viewer-image" alt=""></div><p id="viewer-caption"></p><a id="viewer-document" target="_blank" rel="noopener">Открыть PDF ↗</a></dialog><button class="back-top" data-top aria-label="Наверх страницы" hidden>↑</button><div id="toast" role="status"></div></body></html>'''
(ROOT/'index.html').write_text(shell('Место, где начинается творчество','<div id="home"></div>'))
for c in cats:
 d=ROOT/c['id'];d.mkdir(exist_ok=True)
 body=f'<div id="category" data-id="{c["id"]}"></div>'
 (d/'index.html').write_text(shell(c['name'],body,'../',c['description'],[('Главная',''),('Каталог','catalog/')]+category_trail(c['id'])))
for name,title in [('catalog','Каталог мольбертов и оборудования'),('about','Мастерская'),('contacts','Контакты'),('guide','Как выбрать мольберт'),('delivery','Доставка и оплата заказа'),('prices','Цены'),('privacy','Политика конфиденциальности'),('consent','Соглашение на обработку персональных данных')]:
 d=ROOT/name;d.mkdir(exist_ok=True)
 body=document_markup(name) if name in legal_pages else f'<div id="{name}"></div>'
 (d/'index.html').write_text(shell(title,body,'../',desc=legal_pages[name]['description'] if name in legal_pages else None,trail=[('Главная',''),(title,name+'/')]))
for item in products:
 d=ROOT/'product'/item['id'];d.mkdir(parents=True,exist_ok=True)
 (d/'index.html').write_text(shell(item['name'],f'<div id="product" data-id="{item["id"]}"></div>','../../',item['description'],[('Главная',''),('Каталог','catalog/')]+category_trail(item['primaryCategoryId'])+[(item['name'],'product/'+item['id']+'/')],item))
print(f'Built home, {len(cats)} categories, {len(products)} products, 8 service pages.')

# Editorial routes share the global shell and are included in every rebuild.
blog=ROOT/'blog';blog.mkdir(exist_ok=True)
(blog/'index.html').write_text(shell('Статьи и публикации','<div id="blog"></div>','../','Здесь Вы можете познакомиться с нашими публикациями в прессе.',[('Главная',''),('Блог','blog/')]))
for article in articles:
 d=blog/article['id'];d.mkdir(exist_ok=True)
 (d/'index.html').write_text(shell(article['title'],f'<div id="article" data-id="{article["id"]}"></div>','../../',article['summary'],[('Главная',''),('Блог','blog/'),(article['title'],'blog/'+article['id']+'/')]))
print(f'Built blog and {len(articles)} article pages.')

# Preserve local product links and merge the former flat categories into document branches.
BASE='https://www.molberty.ru/'
redirects={'/product/'+old+'/':'/product/'+new+'/' for old,new in source['legacyIdMap'].items() if old!=new}
for old,role in structure['legacyCategoryRoles'].items():
 assert old not in by_id and old not in excluded
 redirects['/'+old+'/']='/'+roles[role]+'/'
for retired in source['report'].get('removedProducts',[]):
 family=retired.get('sourceFamily');role={'artist':'artists','studio':'studio','exhibition':'exhibitions','interior':'interiors'}.get(family)
 redirects['/product/'+retired['id']+'/']='/'+roles[role]+'/' if role else '/catalog/'
for old,new in redirects.items():
 directory=ROOT/old.strip('/');directory.mkdir(parents=True,exist_ok=True)
 target=os.path.relpath(ROOT/new.strip('/'),directory)+'/'
 (directory/'index.html').write_text(f'<!doctype html><html lang="ru"><head><meta charset="utf-8"><meta name="robots" content="noindex"><meta http-equiv="refresh" content="0;url={target}"><link rel="canonical" href="{BASE}{new.lstrip("/")}"><title>Страница перемещена</title></head><body><h1>Страница перемещена</h1><a href="{target}">Продолжить просмотр каталога</a></body></html>')
(ROOT/'data/redirects.json').write_text(json.dumps(redirects,ensure_ascii=False,indent=2))
summary={'document':'data/catalog-structure.doc','documentSha256':structure['documentSha256'],'amendments':structure.get('amendments',[]),'categoryCount':len(cats),'productCount':len(products),'galleryCount':sum(len(p['gallery']) for p in products),'newCount':sum(p['isNew'] for p in products),'roots':{c['role']:sum(c['id'] in p['categories'] for p in products) for c in cats if not c['parentId']},'categoryProducts':{c['id']:[p['id'] for p in products if c['id'] in p['categories']] for c in cats},'redirectCount':len(redirects)}
(ROOT/'data/structure-report.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2))
print('Document hierarchy:',len(root_ids),'roots,',len(cats),'categories,',len(products),'current products.')
