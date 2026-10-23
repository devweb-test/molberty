const {chromium}=require('playwright'),assert=require('node:assert/strict'),fs=require('node:fs');
const {acceptCookieNotice}=require('./test-helpers.cjs');
const base=process.env.PREVIEW_URL||'http://127.0.0.1:4175/';
(async()=>{const browser=await chromium.launch({headless:true});try{
 const context=await browser.newContext({viewport:{width:390,height:844},isMobile:true,hasTouch:true,reducedMotion:'reduce'});
 await acceptCookieNotice(context);await context.route('**/*',r=>new URL(r.request().url()).origin===new URL(base).origin?r.continue():r.abort());
 const page=await context.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));
 const go=async route=>{await page.goto(new URL(route,base).href);await page.locator('main h1').waitFor()};
 const dock=page.locator('#mobile-bottom-nav'),cart=dock.locator('[data-mobile-cart]');
 const close=async()=>{await page.keyboard.press('Escape');await page.waitForFunction(()=>!document.querySelector('#request-dialog').open)};
 await go('');assert.equal(await dock.count(),1);assert.equal(await dock.locator('a,button').count(),4);
 assert.equal(await dock.locator('[aria-current]').textContent(),'Главная');assert.equal(await cart.isDisabled(),false);
 for(const width of [320,390,600,768,900]){
  await page.setViewportSize({width,height:844});assert.ok(await dock.isVisible());
  const size=await dock.boundingBox();assert.equal(Math.round(size.y+size.height),844);
  assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
  for(const item of await dock.locator('a,button').all()){const box=await item.boundingBox();assert.ok(box.width>=44&&box.height>=44)}
 }
 await page.setViewportSize({width:901,height:844});assert.equal(await dock.isVisible(),false);assert.equal(await page.evaluate(()=>getComputedStyle(document.body).paddingBottom),'0px');
 await page.setViewportSize({width:390,height:844});await dock.getByRole('link',{name:'Каталог',exact:true}).click();await page.waitForURL('**/catalog/');assert.equal(await dock.locator('[aria-current]').textContent(),'Каталог');
 await dock.getByRole('link',{name:'Контакты',exact:true}).click();await page.waitForURL('**/contacts/');assert.equal(await dock.locator('[aria-current]').textContent(),'Контакты');
 await dock.getByRole('link',{name:'Главная',exact:true}).click();await page.waitForURL('**/index.html');
 await go('product/bolshoy-stankovyy-buk/');assert.equal(await dock.locator('[aria-current]').textContent(),'Каталог');
 await page.locator('[data-order]').click();assert.equal(await dock.isVisible(),false);await close();assert.equal(await dock.locator('[data-mobile-count]').textContent(),'1');
 await page.locator('.mobile-menu').click();assert.equal(await page.locator('.mobile-menu').getAttribute('aria-expanded'),'true');
 await cart.click();assert.equal(await page.locator('#dialog-content h2').textContent(),'Ваша корзина');assert.equal(await page.locator('.mobile-menu').getAttribute('aria-expanded'),'false');
 await page.locator('[data-qty]').fill('3');await page.locator('[data-qty]').dispatchEvent('change');await close();
 assert.equal(await dock.locator('[data-mobile-count]').textContent(),'3');assert.equal(await page.locator('[data-count]').textContent(),'3');assert.match(await cart.getAttribute('aria-label'),/3/);
 await page.reload();assert.equal(await dock.locator('[data-mobile-count]').textContent(),'3');
 await cart.click();await page.locator('[data-remove]').click();await close();assert.equal(await dock.locator('[data-mobile-count]').isVisible(),false);
 await go('catalog/');await page.locator('#catalog-search').focus();
 await page.evaluate(()=>{Object.defineProperty(visualViewport,'height',{configurable:true,get:()=>innerHeight-280});visualViewport.dispatchEvent(new Event('resize'))});assert.equal(await dock.isVisible(),false);
 await page.evaluate(()=>{delete visualViewport.height;document.activeElement.blur();visualViewport.dispatchEvent(new Event('resize'))});await dock.waitFor({state:'visible'});
 await page.evaluate(()=>scrollTo(0,document.documentElement.scrollHeight));
 assert.ok((await page.locator('.footer-bottom').boundingBox()).y+(await page.locator('.footer-bottom').boundingBox()).height<=(await dock.boundingBox()).y+1);
 await page.locator('[data-top]').waitFor({state:'visible'});const top=await page.locator('[data-top]').boundingBox();assert.ok(top.y+top.height<(await dock.boundingBox()).y);
 await go('');await page.evaluate(()=>siteCookies.reset());
 for(const [width,height] of [[320,360],[390,844],[844,390]]){
  await page.setViewportSize({width,height});const notice=await page.locator('#cookie-notice').boundingBox(),bar=await dock.boundingBox();assert.ok(notice.y>=0&&notice.y+notice.height<=bar.y);assert.ok(bar.y+bar.height<=height+1);
  await page.locator('[data-cookie-accept]').scrollIntoViewIfNeeded();assert.ok(await page.locator('[data-cookie-accept]').isVisible());
 }
 await page.locator('[data-cookie-accept]').click();await page.setViewportSize({width:390,height:844});await go('');await page.evaluate(()=>document.fonts.ready);await page.screenshot({path:'../.clone-work/mobile-nav-home.png',animations:'disabled'});
 const plainContext=await browser.newContext({javaScriptEnabled:false,viewport:{width:390,height:844}}),plain=await plainContext.newPage();await plain.goto(new URL('product/bolshoy-stankovyy-buk/',base).href);assert.ok(await plain.locator('#mobile-bottom-nav').isVisible());assert.ok(await plain.locator('[data-mobile-cart]').isDisabled());await plain.locator('#mobile-bottom-nav').getByRole('link',{name:'Каталог',exact:true}).click();await plain.waitForURL('**/catalog/');await plainContext.close();
 assert.deepEqual(errors,[]);fs.writeFileSync('qa/mobile-nav-test-result.json',JSON.stringify({passed:true,checkedAt:new Date().toISOString(),checks:['four mobile destinations and active page/section','fixed bar with 44px+ targets at 320–900px','hidden on desktop','working nested links and no-JavaScript navigation','shared cart, quantity updates, removals and persistence','closing header menu before cart','hidden behind native dialogs and virtual keyboard','footer, back-to-top and cookie notice stay clear of dock','short screens and landscape','reduced motion'],widths:[320,390,600,768,900,901]},null,2));console.log('Mobile bottom navigation, shared cart, responsive layout and fallbacks: PASS');
 }finally{await browser.close()}})().catch(e=>{console.error(e);process.exit(1)});
