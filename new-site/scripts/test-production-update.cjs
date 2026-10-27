const {chromium}=require('playwright');
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const data=require('../data/catalog.json'),{acceptCookieNotice}=require('./test-helpers.cjs');
const base=process.env.PREVIEW_URL||'http://127.0.0.1:4175/';
const captures=path.resolve(__dirname,'../../.clone-work/production-v34-preview');
(async()=>{
 const browser=await chromium.launch({headless:true});
 try{
  const context=await browser.newContext({viewport:{width:1440,height:1000},reducedMotion:'reduce'});
  await acceptCookieNotice(context);
  await context.route('**/*',r=>new URL(r.request().url()).origin===new URL(base).origin?r.continue():r.abort());
  const page=await context.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));
  const go=async route=>{await page.goto(new URL(route,base).href,{waitUntil:'domcontentloaded'});await page.locator('main h1').waitFor()};
  fs.mkdirSync(captures,{recursive:true});
  await go('');
  assert.equal(await page.locator('header .logo small').textContent(),'ПРОИЗВОДСТВО С 1991 ГОДА');
  assert.equal(await page.locator('#directions .section-heading p').textContent(),'Одна мастерская — целый мир возможностей — Оптовые партии для организаций');
  assert.match(await page.locator('.hero-proof').textContent(),/Своё производство/);
  for(const paragraph of data.company.paragraphs)assert.ok((await page.locator('#company').textContent()).includes(paragraph));
  assert.equal(await page.locator('.benefits .production-quality p').textContent(),data.production.compliance);
  assert.ok(await page.locator('footer a[href="documents/"]').count());
  await page.locator('.benefits').scrollIntoViewIfNeeded();await page.screenshot({path:path.join(captures,'home-quality-desktop.png')});
  const configurationResults=await page.evaluate(()=>D.products.map(p=>{
   const host=document.createElement('div');host._state=defaultState(p);renderConfig(host,p);
   return {id:p.id,tier:host.querySelector('[data-tier]').value,price:Number(host.querySelector('[data-unit-price]').textContent.replace(/\D/g,'')),minimum:Number(host.querySelector('[data-config-qty]').min),quantity:Number(host.querySelector('[data-config-qty]').value)};
  }));
  for(const item of configurationResults){const p=data.products.find(p=>p.id===item.id);assert.equal(item.tier,p.wholesalePrice!==null||p.wholesaleOnly?'wholesale':'retail',p.id);assert.equal(item.price,p.defaultPrice,p.id);assert.equal(item.quantity,item.minimum,p.id);assert.equal(item.quantity,p.defaultQuantity,p.id)}
  const legacy=await page.evaluate(()=>Object.values(migrateSelection({'bolshoy-stankovyy-buk':2}))[0]);assert.equal(legacy.tier,'retail');assert.equal(legacy.quantity,2);
  await go('catalog/');
  const cards=await page.locator('.product-card').evaluateAll(nodes=>nodes.map(e=>({id:e.dataset.productId,price:Number(e.dataset.price),text:e.querySelector('.card-price').textContent,note:e.querySelector('.card-price-note').textContent})));
  for(const c of cards){const p=data.products.find(p=>p.id===c.id);assert.ok(c.text.startsWith('От '));assert.equal(c.price,p.listingPrice);assert.match(c.note,p.defaultTier==='wholesale'?/Оптовая цена от \d+ шт\./:/Розничная цена/)}
  await go('delivery/');assert.ok(!/паспортн/i.test(await page.locator('main').textContent()));assert.match(await page.locator('#retail').textContent(),/ФИО получателя и мобильный номер телефона/);assert.equal(await page.locator('.wholesale-proposals').textContent(),data.sales.wholesale.competitiveProposals);
  await go('about/');assert.equal(await page.locator('.production-compliance').textContent(),data.production.compliance);
  await go('documents/');assert.equal(await page.locator('h1').textContent(),data.businessDocuments.title);assert.equal(await page.locator('.company-requisites>div').count(),data.businessDocuments.requisites.length);
  for(const doc of data.businessDocuments.downloads){const link=page.locator('.business-download').filter({hasText:doc.title});assert.equal(await link.getAttribute('download'),'');const response=await context.request.get(new URL(await link.getAttribute('href'),page.url()).href);assert.equal(response.status(),200);const bytes=await response.body();assert.equal(bytes.length,doc.bytes);assert.equal(bytes.subarray(0,5).toString(),'%PDF-')}
  await page.screenshot({path:path.join(captures,'documents-desktop.png')});
  await go('blog/kak-vybrat-molbert/');
  for(const [section,ids] of Object.entries({lira:['lira-s-naklonnoy-shtangoy','lira-s-podvizhnoy-shtangoy-buk'],'a-stil':['a-klass','a-profi']})){
   const models=page.locator('#'+section+' .article-model-image');assert.equal(await models.count(),2);
   for(let i=0;i<2;i++){const p=data.products.find(p=>p.id===ids[i]);const image=models.nth(i).locator('img');assert.ok((await image.getAttribute('src')).endsWith(p.image));assert.equal(await image.getAttribute('alt'),p.name);await image.scrollIntoViewIfNeeded();await page.waitForFunction(()=>[...document.querySelectorAll('.article-model-image img')].filter(img=>img.getBoundingClientRect().top<innerHeight).every(img=>img.complete&&img.naturalWidth>0));await models.nth(i).locator('button').click();assert.ok(await page.locator('#image-dialog').isVisible());assert.ok((await page.locator('#viewer-image').getAttribute('src')).endsWith(p.image));await page.keyboard.press('Escape')}
   await page.locator('#'+section).scrollIntoViewIfNeeded();await page.screenshot({path:path.join(captures,section+'-desktop.png')});
  }
  for(const width of [320,390,768,1440]){
   await page.setViewportSize({width,height:950});
   for(const route of ['','about/','documents/','delivery/','blog/kak-vybrat-molbert/','product/bolshoy-stankovyy-buk/']){await go(route);assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),route+' overflow '+width);if(width===390&&['documents/','product/bolshoy-stankovyy-buk/'].includes(route))await page.screenshot({path:path.join(captures,route.startsWith('product')?'product-mobile.png':'documents-mobile.png')})}
  }
  assert.deepEqual(errors,[]);
  fs.writeFileSync('qa/production-update-test-result.json',JSON.stringify({passed:true,checkedAt:new Date().toISOString(),products:91,wholesaleDefaults:83,retailOnlyPrices:8,documents:3,widths:[320,390,768,1440],checks:['production logo and marketing','protected company prose','standards and product completeness','all default configurations and minimum quantities','wholesale cards with honest retail fallback','recipient name and mobile only','three competitive proposals','requisites and exact PDF downloads','Lira and A-style photos with zoom','responsive layout'],screenshots:captures},null,2)+'\n');
  console.log('Production, wholesale defaults, documents and article images: PASS');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});
