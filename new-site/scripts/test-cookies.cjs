const {chromium}=require('playwright'),assert=require('node:assert/strict'),fs=require('node:fs');
const base=process.env.PREVIEW_URL||'http://127.0.0.1:4173/';
const notice=JSON.parse(fs.readFileSync('data/cookie-notice.json','utf8'));
const documents=JSON.parse(fs.readFileSync('data/legal-pages.json','utf8'));
(async()=>{const browser=await chromium.launch({headless:true});try{
 const context=await browser.newContext({viewport:{width:1440,height:1000},reducedMotion:'reduce'});
 await context.route('**/*',r=>new URL(r.request().url()).origin===new URL(base).origin?r.continue():r.abort());
 const page=await context.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));
 let release;const gate=new Promise(resolve=>{release=resolve});await page.route('**/assets/data.js',async request=>{await gate;await request.continue()});
 const first=page.goto(base,{waitUntil:'load'});await page.locator('#cookie-notice:not([hidden])').waitFor();
 assert.equal(await page.locator('#cookie-message').textContent(),notice.text);assert.equal(await page.locator('[data-cookie-accept]').textContent(),notice.button);
 assert.equal(await page.evaluate(()=>localStorage.getItem('molberty-cookie-consent')),null);
 assert.equal(await page.locator('#cookie-notice').getByRole('link',{name:notice.linkText,exact:true}).getAttribute('href'),'privacy/');
 assert.equal(await page.locator('#cookie-notice').getByRole('link',{name:notice.consentLinkText,exact:true}).getAttribute('href'),'consent/');
 assert.equal(await page.locator('#cookie-notice').getAttribute('role'),'region');
 assert.equal(await page.locator('dialog[open]').count(),0);
 release();await first;await page.unroute('**/assets/data.js');
 for(const [width,height] of [[320,360],[320,812],[390,844],[768,950],[1440,1000]]){
  await page.setViewportSize({width,height});
  assert.ok(await page.locator('#cookie-notice').evaluate(e=>{const r=e.getBoundingClientRect();return r.left>=0&&r.top>=0&&r.right<=innerWidth+1&&r.bottom<=innerHeight+1&&e.scrollWidth<=e.clientWidth+1}),'notice overflow '+width+'×'+height);
  await page.locator('[data-cookie-accept]').scrollIntoViewIfNeeded();assert.ok(await page.locator('[data-cookie-accept]').isVisible());
 }
 assert.equal(await page.locator('#cookie-notice').evaluate(e=>e.getAnimations().length),0);
 await page.locator('[data-cookie-accept]').click();assert.equal(await page.locator('#cookie-notice').isVisible(),false);assert.equal(await page.evaluate(()=>localStorage.getItem('molberty-cookie-consent')),'accepted-v1');
 await page.reload();assert.equal(await page.locator('#cookie-notice').isVisible(),false);
 for(const route of ['prices/','product/bolshoy-stankovyy-buk/','privacy/','consent/']){await page.goto(new URL(route,base).href);assert.equal(await page.locator('#cookie-notice').isVisible(),false);assert.equal(await page.locator('.footer-bottom a').first().textContent(),'Политика конфиденциальности')}
 for(const id of ['privacy','consent']){
  await page.goto(new URL(id+'/',base).href);
  assert.equal(await page.locator('main h1').textContent(),documents[id].title);assert.equal(await page.locator('main h1').count(),1);
  const blocks=await page.locator('.legal-document > p,.legal-document > h2,.legal-document > h3').evaluateAll(elements=>elements.map(e=>({tag:e.tagName.toLowerCase(),text:e.textContent})));
  assert.deepEqual(blocks,documents[id].blocks);
  assert.ok(!(await page.locator('main').textContent()).match(/орлан|orlan|автошкол|образовательн|whatsapp|гибдд/i));
  assert.ok((await page.locator('main').textContent()).includes('molberty@gmail.com'));
  assert.ok((await page.locator('main').textContent()).includes('www.molberty.ru'));
  assert.equal(await page.locator('link[rel="canonical"]').getAttribute('href'),'https://www.molberty.ru/'+id+'/');
  for(const width of [320,390,1440]){await page.setViewportSize({width,height:950});await page.evaluate(()=>document.fonts.ready);assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),id+' page overflow '+width)}
 }
 const other=await context.newPage();await other.goto(new URL('contacts/',base).href);await other.evaluate(()=>window.siteCookies.reset());
 await page.waitForFunction(()=>!document.querySelector('#cookie-notice').hidden);await page.locator('[data-cookie-accept]').click();await other.waitForFunction(()=>document.querySelector('#cookie-notice').hidden);
 await page.goto(new URL('privacy/',base).href);await page.evaluate(()=>{localStorage.setItem('molberty-draft','{}');localStorage.setItem('molberty-checkout-draft','{}')});await page.locator('[data-clear]').click();assert.equal(await page.evaluate(()=>localStorage.getItem('molberty-cookie-consent')),null);assert.equal(await page.evaluate(()=>localStorage.getItem('molberty-draft')),null);assert.ok(await page.locator('#cookie-notice').isVisible());
 const unavailable=await browser.newContext();await unavailable.addInitScript(()=>{Object.defineProperty(window,'localStorage',{get(){throw new DOMException('Storage blocked','SecurityError')}})});const blocked=await unavailable.newPage();blocked.on('pageerror',e=>errors.push(e.message));await blocked.goto(base);assert.ok(await blocked.locator('#cookie-notice').isVisible());await blocked.locator('[data-cookie-accept]').click();assert.equal(await blocked.locator('#cookie-notice').isVisible(),false);await unavailable.close();
 const noJs=await browser.newContext({javaScriptEnabled:false});const plain=await noJs.newPage();for(const id of ['privacy','consent']){await plain.goto(new URL(id+'/',base).href,{waitUntil:'domcontentloaded'});assert.equal(await plain.locator('main h1').textContent(),documents[id].title);assert.equal(await plain.locator('#cookie-notice').isVisible(),false);assert.equal(await plain.locator('.legal-document>p').count(),documents[id].blocks.filter(b=>b.tag==='p').length)}await noJs.close();
 const forced=await browser.newContext();await forced.addInitScript(()=>{window.SITE_PRERENDER=true});const exportPage=await forced.newPage();for(const id of ['privacy','consent']){await exportPage.goto(new URL(id+'/',base).href);assert.equal(await exportPage.locator('main h1').textContent(),documents[id].title);assert.equal(await exportPage.locator('.legal-document>p').count(),documents[id].blocks.filter(b=>b.tag==='p').length)}await forced.close();
 assert.deepEqual(errors,[]);fs.writeFileSync('qa/cookie-legal-test-result.json',JSON.stringify({passed:true,checkedAt:new Date().toISOString(),checks:['exact cookie message and policy link','notice works before catalogue data loads','non-modal, no forced focus','responsive notice including 320×360','reduced motion','explicit acceptance only','persistence across reload and product/service pages','cross-tab decision synchronization','graceful disabled storage','reset through clear saved data','both legal documents and adapted contacts','updated footer link','static content without JavaScript','explicit export mode'],legalBlocks:{privacy:documents.privacy.blocks.length,consent:documents.consent.blocks.length}},null,2));
 console.log('Cookie notice, persistence, legal documents, footer, responsive layout and fallbacks: PASS');await context.close();
}finally{await browser.close()}})().catch(e=>{console.error(e);process.exit(1)});
