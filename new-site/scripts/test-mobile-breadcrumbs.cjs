const {chromium}=require('playwright'),assert=require('node:assert/strict'),fs=require('node:fs');
const {acceptCookieNotice}=require('./test-helpers.cjs');
const base=process.env.PREVIEW_URL||'http://127.0.0.1:4175/';
(async()=>{const browser=await chromium.launch({headless:true});try{
 const context=await browser.newContext({viewport:{width:390,height:844},isMobile:true,hasTouch:true,reducedMotion:'reduce'});await acceptCookieNotice(context);
 await context.route('**/*',r=>new URL(r.request().url()).origin===new URL(base).origin?r.continue():r.abort());
 const page=await context.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));
 const product='product/transformer-a0-buk/';
 const routes=[product,'molberty-transformery/','molberty-hlopushka/','catalog/','blog/kak-vybrat-molbert/','contacts/','privacy/'];
 const go=route=>page.goto(new URL(route,base).href);
 const verify=async(p,mobile)=>{
  const compact=p.locator('.mobile-breadcrumb'),full=p.locator('.breadcrumbs');assert.equal(await compact.count(),1);assert.equal(await full.count(),1);
  assert.equal(await compact.isVisible(),mobile);assert.equal(await full.isVisible(),!mobile);
  const trail=await p.locator('#breadcrumb-schema').evaluate(e=>JSON.parse(e.textContent).itemListElement),parent=trail.at(-2);
  assert.equal(await compact.locator('span').textContent(),parent.name);assert.equal(new URL(await compact.getAttribute('href'),p.url()).pathname.replace(/\/index\.html$/,'/'),new URL(parent.item).pathname);
  assert.equal(await compact.getAttribute('aria-label'),'Назад: '+parent.name);
  if(mobile){const box=await compact.boundingBox();assert.equal(box.height,44);assert.ok(await compact.evaluate(e=>e.getBoundingClientRect().width<=e.parentElement.clientWidth));assert.ok(await p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1))}
 };
 for(const width of [320,390,768,900]){await page.setViewportSize({width,height:844});for(const route of routes){await go(route);await verify(page,true)}}
 await page.setViewportSize({width:320,height:844});await go('molberty-hlopushka/');assert.ok(await page.locator('.mobile-breadcrumb span').evaluate(e=>getComputedStyle(e).textOverflow==='ellipsis'&&e.scrollWidth>e.clientWidth));
 for(const width of [901,1440]){await page.setViewportSize({width,height:950});await go(product);await verify(page,false);assert.equal(await page.locator('.breadcrumbs>a').count(),6);assert.equal(await page.locator('#breadcrumb-schema').evaluate(e=>JSON.parse(e.textContent).itemListElement.length),7)}
 await page.setViewportSize({width:390,height:844});await go(product);await page.locator('.mobile-breadcrumb').click();await page.waitForURL('**/molberty-transformery/');await page.locator('.mobile-breadcrumb').click();await page.waitForURL('**/professionalnye-molberty/');
 await go(product);await page.evaluate(()=>document.fonts.ready);if(process.env.SCREENSHOT_PATH)await page.screenshot({path:process.env.SCREENSHOT_PATH,animations:'disabled'});
 const after=(await page.locator('.mobile-breadcrumb').boundingBox()).height,before=Number(process.env.BREADCRUMB_BASELINE_HEIGHT)||null;if(before)assert.ok(after<before);
 const plainContext=await browser.newContext({javaScriptEnabled:false,viewport:{width:390,height:844}}),plain=await plainContext.newPage();await plain.goto(new URL(product,base).href);await verify(plain,true);await plain.locator('.mobile-breadcrumb').click();await plain.waitForURL('**/molberty-transformery/');await plainContext.close();
 const exportContext=await browser.newContext({viewport:{width:390,height:844},reducedMotion:'reduce'});await acceptCookieNotice(exportContext);await exportContext.addInitScript(()=>{window.SITE_PRERENDER=true});const exported=await exportContext.newPage();for(const route of [product,'catalog/','blog/kak-vybrat-molbert/','privacy/']){await exported.goto(new URL(route,base).href);await verify(exported,true)}await exportContext.close();
 assert.deepEqual(errors,[]);fs.writeFileSync('qa/mobile-breadcrumbs-test-result.json',JSON.stringify({passed:true,checkedAt:new Date().toISOString(),mobileWidths:[320,390,768,900],desktopWidths:[901,1440],routes,exampleHeight:{before,after,saved:before===null?null:before-after},checks:['one-line parent link with a 44px target','long parent label truncation without overflow','correct parent links and full accessible label','working navigation up two category levels','full desktop trail retained','complete seven-level BreadcrumbList retained','static links without JavaScript','explicit prerender mode on products, catalogue, articles and legal pages']},null,2));console.log('Compact mobile breadcrumbs, parent links, desktop trail and schema: PASS');
 }finally{await browser.close()}})().catch(e=>{console.error(e);process.exit(1)});
