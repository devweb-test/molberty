const {chromium}=require('playwright'),assert=require('node:assert/strict'),fs=require('node:fs');
const base=process.env.PREVIEW_URL||'http://127.0.0.1:4173/';
const audit=()=>{
 window.motionAudit=[];
 const animate=Element.prototype.animate;
 Element.prototype.animate=function(...args){const animation=animate.apply(this,args);window.motionAudit.push({element:this,animation});return animation};
};
(async()=>{
 const browser=await chromium.launch({headless:true}),errors=[];
 try{
  const context=await browser.newContext({viewport:{width:1440,height:1000}});await context.addInitScript(audit);
  const page=await context.newPage();page.on('pageerror',e=>errors.push(e.message));
  const go=async route=>{await page.goto(new URL(route,base).href,{waitUntil:'domcontentloaded'});await page.evaluate(()=>document.documentElement.style.scrollBehavior='auto')};
  const count=selector=>page.locator(selector).first().evaluate(element=>window.motionAudit.filter(r=>r.element===element&&r.animation.id==='site-scroll-reveal').length);
  const running=()=>page.evaluate(()=>document.getAnimations().filter(a=>a.id==='site-scroll-reveal').length);
  await go('');await page.waitForFunction(()=>window.motionAudit.some(r=>r.element.matches('.hero-copy>h1')&&r.animation.id==='site-scroll-reveal'));
  // Below-fold content is visible by default; enhancement never leaves hidden CSS behind.
  assert.equal(await page.locator('.case-card').first().evaluate(e=>getComputedStyle(e).opacity),'1');
  await page.locator('.category-tile').first().scrollIntoViewIfNeeded();
  await page.waitForFunction(()=>window.motionAudit.some(r=>r.element.matches('.category-tile')&&r.animation.id==='site-scroll-reveal'));
  const timings=await page.locator('.category-tiles').evaluate(e=>window.motionAudit.filter(r=>e.contains(r.element)&&r.animation.id==='site-scroll-reveal').map(r=>r.animation.effect.getTiming()));
  assert.ok(timings.length>=2);assert.ok(timings.some(t=>t.delay>0));assert.ok(timings.every(t=>t.delay<=180&&t.duration<=520));
  await page.locator('.category-tile').first().focus();
  assert.equal(await page.locator('.category-tile').first().evaluate(e=>e.getAnimations().filter(a=>a.id==='site-scroll-reveal').length),0);
  const before=await count('.category-tile');await page.evaluate(()=>scrollTo(0,0));await page.locator('.category-tile').first().scrollIntoViewIfNeeded();
  assert.equal(await count('.category-tile'),before);
  await page.locator('.category-tile').first().hover();assert.equal(await page.locator('.category-tile').first().evaluate(e=>getComputedStyle(e).backgroundColor),'rgb(255, 255, 255)');

  await go('catalog/');await page.locator('#catalog-search').fill('Лира');
  await page.waitForFunction(()=>document.querySelectorAll('.product-card').length<91);
  const last=page.locator('.product-card').last(),lastId=await last.getAttribute('data-product-id');await last.scrollIntoViewIfNeeded();
  await page.waitForFunction(id=>window.motionAudit.some(r=>r.element.dataset.productId===id&&r.animation.id==='site-scroll-reveal'),lastId);
  await page.selectOption('#sort','price-asc');
  assert.equal(await page.evaluate(()=>window.motionAudit.filter(r=>!r.element.isConnected&&r.animation.id==='site-scroll-reveal'&&r.animation.playState==='running').length),0);
  await page.locator('#reset-filters').click();await page.waitForFunction(()=>document.querySelectorAll('.product-card').length===91);

  await page.emulateMedia({reducedMotion:'reduce'});await go('');assert.equal(await running(),0);
  await page.emulateMedia({reducedMotion:'no-preference'});await page.locator('.category-tile').first().scrollIntoViewIfNeeded();
  await page.waitForFunction(()=>window.motionAudit.some(r=>r.element.matches('.category-tile')&&r.animation.id==='site-scroll-reveal'));
  await page.emulateMedia({reducedMotion:'reduce'});await page.waitForFunction(()=>document.getAnimations().every(a=>a.id!=='site-scroll-reveal'));
  assert.equal(await page.locator('.category-tile').first().evaluate(e=>getComputedStyle(e).opacity),'1');
  await page.emulateMedia({reducedMotion:'no-preference'});await go('');
  await page.evaluate(()=>dispatchEvent(new Event('beforeprint')));assert.equal(await running(),0);
  assert.equal(await page.locator('.hero-copy>h1').evaluate(e=>getComputedStyle(e).opacity),'1');
  await page.evaluate(()=>dispatchEvent(new Event('afterprint')));
  await page.evaluate(()=>dispatchEvent(new PageTransitionEvent('pagehide',{persisted:true})));assert.equal(await running(),0);
  await page.evaluate(()=>dispatchEvent(new PageTransitionEvent('pageshow',{persisted:true})));
  await page.locator('.case-card').first().scrollIntoViewIfNeeded();
  await page.waitForFunction(()=>window.motionAudit.some(r=>r.element.matches('.case-card')&&r.animation.id==='site-scroll-reveal'));

  for(const width of [320,390,768,1440]){await page.setViewportSize({width,height:950});for(const route of ['', 'catalog/','product/bolshoy-stankovyy-buk/','blog/','prices/']){await go(route);assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),route+' '+width)}}
  const plainContext=await browser.newContext({javaScriptEnabled:false}),plain=await plainContext.newPage();
  await plain.goto(base);assert.ok(await plain.locator('main h1').isVisible());assert.equal(await plain.locator('.case-card').first().evaluate(e=>getComputedStyle(e).opacity),'1');
  const noObserver=await browser.newContext();await noObserver.addInitScript(()=>{window.IntersectionObserver=undefined});const fallback=await noObserver.newPage();fallback.on('pageerror',e=>errors.push(e.message));
  await fallback.goto(base,{waitUntil:'domcontentloaded'});await fallback.locator('.category-tile').first().scrollIntoViewIfNeeded();assert.equal(await fallback.locator('.category-tile').first().evaluate(e=>getComputedStyle(e).opacity),'1');await fallback.locator('.header-contact [data-callback]').click();assert.ok(await fallback.locator('#request-dialog').isVisible());
  assert.deepEqual(errors,[]);
  fs.writeFileSync('qa/scroll-motion-test-result.json',JSON.stringify({passed:true,checkedAt:new Date().toISOString(),checks:['viewport reveal and bounded stagger','first screen entrance','content visible without enhancement','one-time playback','focus cancels reveal','dynamic filter cards and removed-node cleanup','live reduced motion','print and restored-page cleanup','no-JavaScript and no-IntersectionObserver fallbacks','responsive overflow'],viewports:[320,390,768,1440]},null,2));
  console.log('Scroll entrances, dynamic content, accessibility and fallbacks: PASS');
 }finally{await browser.close()}
})().catch(error=>{console.error(error);process.exit(1)});
