// Run against serve.py; covers missing URLs, shared UI, back navigation and Pages.
const {chromium}=require('playwright');
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'..'),base=process.env.PREVIEW_URL||'http://127.0.0.1:4175/';
const catalog=JSON.parse(fs.readFileSync(path.join(root,'data/catalog.json'),'utf8'));
const output=path.resolve(root,'../.clone-work/not-found-v42-preview');
const expectedNew=catalog.products.filter(p=>p.isNew).slice(0,4);
const missing='catalog/this-page-does-not-exist/product/';
(async()=>{
 fs.mkdirSync(output,{recursive:true});
 const browser=await chromium.launch({headless:true}),context=await browser.newContext({reducedMotion:'reduce'});
 await context.addInitScript(()=>localStorage.setItem('molberty-cookie-consent','accepted-v1'));
 const page=await context.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));
 const response=await page.goto(new URL(missing,base).href,{waitUntil:'networkidle'});
 assert.equal(response.status(),404);assert.equal(page.url(),new URL(missing,base).href);
 assert.equal(await page.locator('h1').count(),1);
 await page.locator('#not-found h1').waitFor();
 assert.match(await page.locator('h1').innerText(),/Такой страницы\s+не существует/);
 assert.equal(await page.locator('.not-found-reasons li').count(),3);
 assert.equal(await page.locator('.not-found-category').count(),6);
 assert.equal(await page.locator('.not-found-offers').count(),0);
 assert.equal(await page.locator('#not-found .cta-section').count(),1);
 assert.match(await page.locator('#not-found .cta-section .text-h2').innerText(),/С чего начнётся\s+ваша следующая работа\?/);
 assert.equal(await page.locator('#not-found .cta-section h2,#not-found .cta-section h3').count(),0);
 assert.equal(await page.locator('.not-found-new').evaluate(el=>el.nextElementSibling.classList.contains('cta-section')),true);
 assert.deepEqual(await page.locator('.not-found-new .product-card').evaluateAll(nodes=>nodes.map(n=>n.dataset.productId)),expectedNew.map(p=>p.id));
 assert.equal(await page.locator('.not-found-new .new-badge').count(),4);
 for(let i=0;i<4;i++)assert.match(await page.locator('.not-found-new .card-price').nth(i).innerText(),/^От /);
 for(const href of await page.locator('#not-found a').evaluateAll(nodes=>nodes.map(n=>n.href).filter(href=>/^https?:/.test(href))))assert.equal((await context.request.get(href)).status(),200,href);
 assert.equal(await page.locator('#not-found .cta-section a[href^="tel:"]').getAttribute('href'),'tel:+79258809539');
 const layout=[];
 for(const width of [320,390,768,1440]){
  await page.setViewportSize({width,height:900});
  const dimensions=await page.evaluate(()=>({viewport:innerWidth,width:document.documentElement.scrollWidth}));
  assert.ok(dimensions.width<=dimensions.viewport,JSON.stringify(dimensions));
  assert.equal(await page.locator('#mobile-bottom-nav').isVisible(),width<=768);
  await page.screenshot({path:path.join(output,'404-'+width+'.png'),fullPage:true});layout.push(dimensions);
 }
 await page.locator('.not-found-new .quick-button').first().click();
 await page.locator('#request-dialog[open] .quick-view').waitFor();
 assert.match(await page.locator('#dialog-content').innerText(),new RegExp(expectedNew[0].name.replace(/[.*+?^${}()|[\]\\]/g,'\\$&')));
 await page.locator('#request-dialog [data-close]').click();
 await page.locator('#not-found .cta-section [data-request]').click();
 await page.locator('#request-dialog[open] form').waitFor();
 const consent=page.locator('#request-dialog input[type=checkbox][required]');
 assert.equal(await consent.count(),1);assert.equal(await consent.isChecked(),false);
 await page.locator('#request-dialog [data-close]').click();
 await page.goto(new URL('prices/',base).href);
 await page.goto(new URL(missing,base).href);
 await page.locator('[data-history-back]').click();await page.waitForURL(new URL('prices/',base).href);
 // A fresh tab with no earlier page falls back to the home link.
 const fresh=await context.newPage();await fresh.goto(new URL(missing,base).href);
 assert.equal(await fresh.evaluate(()=>window.navigation.canGoBack),false);
 await fresh.locator('[data-history-back]').click();await fresh.waitForURL(new URL('index.html',base).href);await fresh.close();
 // Static HTML retains the content, shared navigation and functional home fallback.
 const plain=await browser.newContext({javaScriptEnabled:false,viewport:{width:390,height:844}}),plainPage=await plain.newPage();
 assert.equal((await plainPage.goto(new URL(missing,base).href)).status(),404);
 assert.equal(await plainPage.locator('#not-found .product-card').count(),4);
 assert.equal(await plainPage.locator('#not-found .cta-section').count(),1);
 assert.equal(await plainPage.locator('.not-found-offers').count(),0);
 await plainPage.locator('[data-history-back]').click();await plainPage.waitForURL(new URL('index.html',base).href);await plain.close();
 // The repository-root 404 is served by GitHub Pages, including at nested URLs.
 const source=fs.readFileSync(path.join(root,'404.html'),'utf8'),deployed=fs.readFileSync(path.join(root,'../404.html'),'utf8');
 assert.equal(deployed,source.replace('<base id="error-page-base" href="/">','<base id="error-page-base" href="/molberty/new-site/">'));
 for(const javaScriptEnabled of [true,false]){
  const pages=await browser.newContext({javaScriptEnabled,viewport:{width:390,height:844}});
  await pages.route('https://devweb-test.github.io/**',async route=>{
   const pathname=new URL(route.request().url()).pathname,prefix='/molberty/new-site/';
   let file=pathname.startsWith(prefix)?path.join(root,decodeURIComponent(pathname.slice(prefix.length))):'';
   if(file&&fs.existsSync(file)&&fs.statSync(file).isDirectory())file=path.join(file,'index.html');
   if(file&&fs.existsSync(file))return route.fulfill({path:file,status:200});
   return route.fulfill({status:404,contentType:'text/html; charset=utf-8',body:deployed});
  });
  const tab=await pages.newPage();const result=await tab.goto('https://devweb-test.github.io/molberty/new-site/missing/nested/page/');
  assert.equal(result.status(),404);
  assert.equal(await tab.locator('.not-found-category').first().evaluate(n=>n.href),'https://devweb-test.github.io/molberty/new-site/'+catalog.categoryRoles.artists+'/');
  assert.ok((await tab.locator('.not-found-new img').first().evaluate(n=>n.src)).startsWith('https://devweb-test.github.io/molberty/new-site/assets/'));
  await tab.locator('.not-found-category').first().click();await tab.waitForURL('https://devweb-test.github.io/molberty/new-site/'+catalog.categoryRoles.artists+'/');
  await pages.close();
 }
 assert.deepEqual(errors,[]);
 await browser.close();
 const result={passed:true,missingHttpStatus:404,novelties:expectedNew.map(p=>p.id),layouts:layout,checks:['nested URLs and asset bases','shared navigation','back and home fallback','original new products and wholesale prices','quick view','shared CTA replaces special offers and opens request form with required consent','static HTML without JavaScript','GitHub Pages root fallback with and without JavaScript','no horizontal overflow'],browserErrors:errors};
 fs.writeFileSync(path.join(root,'qa/not-found-test-result.json'),JSON.stringify(result,null,2)+'\n');
 console.log('404: HTTP status, navigation, mobile layout, products, forms, back, no-JS and GitHub Pages: PASS');
})().catch(error=>{console.error(error);process.exit(1)});
