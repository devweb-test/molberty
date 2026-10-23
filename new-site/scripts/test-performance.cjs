// Regression: the first screen must survive runtime initialization unchanged.
const {chromium}=require('playwright'),assert=require('node:assert/strict'),fs=require('node:fs');
const base=process.env.PREVIEW_URL||'http://127.0.0.1:4173/';
const routes=['','catalog/','molberty-stankovye/','product/bolshoy-stankovyy-buk/','prices/','contacts/','about/','delivery/','guide/','privacy/','blog/','blog/kak-vybrat-molbert/'];
(async()=>{const browser=await chromium.launch({headless:true});try{
 const context=await browser.newContext({viewport:{width:1440,height:1000},reducedMotion:'reduce'});await context.route('**/*',r=>new URL(r.request().url()).origin===new URL(base).origin?r.continue():r.abort());
 const errors=[],page=await context.newPage();page.on('pageerror',e=>errors.push(e.message));
 for(const route of routes){
  let release;const gate=new Promise(resolve=>{release=resolve});
  await page.route('**/assets/app.js',async request=>{await gate;await request.continue()});
  const navigation=page.goto(new URL(route,base).href,{waitUntil:'load'});
  await page.locator('main h1').waitFor({state:'attached'});
  await page.evaluate(()=>{window.firstScreen={heading:document.querySelector('main h1'),header:document.querySelector('#header').firstElementChild,footer:document.querySelector('#footer').firstElementChild,results:document.querySelector('#catalog-results')?.firstElementChild,prices:document.querySelector('#price-results')?.firstElementChild,map:document.querySelector('iframe'),photo:document.querySelector('.product-main-image img'),description:document.querySelector('meta[name="description"]').content,canonical:document.querySelector('link[rel="canonical"]').href}});
  release();await navigation;
  const reused=await page.evaluate(()=>{const before=window.firstScreen;return {heading:before.heading===document.querySelector('main h1'),header:before.header===document.querySelector('#header').firstElementChild,footer:before.footer===document.querySelector('#footer').firstElementChild,results:before.results===document.querySelector('#catalog-results')?.firstElementChild,prices:before.prices===document.querySelector('#price-results')?.firstElementChild,map:before.map===document.querySelector('iframe'),photo:before.photo===document.querySelector('.product-main-image img'),description:before.description===document.querySelector('meta[name="description"]').content,canonical:before.canonical===document.querySelector('link[rel="canonical"]').href}});
  for(const [key,value] of Object.entries(reused))assert.ok(value,route+' replaced '+key);
  await page.unroute('**/assets/app.js');
 }
 await page.goto(new URL('catalog/',base).href);await page.locator('#catalog-search').fill('несуществующее название 123');assert.equal(await page.locator('#catalog-results .product-card').count(),0);await page.locator('#reset-filters').click();assert.equal(await page.locator('#catalog-results .product-card').count(),91);
 await page.goto(new URL('prices/',base).href);const allRows=await page.locator('[data-price-id]').count();assert.equal(allRows,106);await page.locator('#price-search').fill('несуществующее название 123');assert.equal(await page.locator('[data-price-id]').count(),0);await page.locator('#price-reset').click();assert.equal(await page.locator('[data-price-id]').count(),allRows);
 await page.goto(new URL('contacts/',base).href);await page.locator('.header-contact [data-callback]').click();assert.equal(await page.locator('#dialog-content h2').textContent(),'Заказать звонок');
 const forced=await browser.newContext();await forced.addInitScript(()=>{window.SITE_PRERENDER=true});const exportPage=await forced.newPage();await exportPage.goto(new URL('catalog/',base).href,{waitUntil:'load'});assert.equal(await exportPage.locator('#catalog-results .product-card').count(),91);assert.equal(await exportPage.locator('main h1').textContent(),'Каталог мольбертов и оборудования');await forced.close();
 assert.deepEqual(errors,[]);
 fs.writeFileSync('qa/performance-test-result.json',JSON.stringify({passed:true,checkedAt:new Date().toISOString(),routes,checks:['first-screen DOM identity before and after delayed app.js','no reload of existing map, gallery, product results or price tables','header/footer preserved','description and canonical unchanged','catalog search and reset','price search and reset','callback form','explicit prerender mode']},null,2));
 console.log('Existing HTML, maps and first screen retained; filters, forms and explicit export: PASS');
 await context.close();
}finally{await browser.close()}})().catch(e=>{console.error(e);process.exit(1)});
