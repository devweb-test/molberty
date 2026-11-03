// The review is complete: verify the approved logo cannot be overridden.
const {chromium}=require('playwright'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const {acceptCookieNotice}=require('./test-helpers.cjs');
const manifest=require('../data/logo-options.json'),base=process.env.PREVIEW_URL||'http://127.0.0.1:4175/';
const shots=path.resolve(__dirname,'../../.clone-work/logo-v65-approved');
(async()=>{
 assert.equal(manifest.status,'approved');assert.equal(manifest.defaultId,'lira');
 const browser=await chromium.launch({headless:true});const errors=[],requests=[],checks=[];
 try{
  const context=await browser.newContext({viewport:{width:1440,height:1000},reducedMotion:'reduce'});
  await acceptCookieNotice(context);
  await context.addInitScript(()=>sessionStorage.setItem('molberty-logo-review',JSON.stringify({active:true,id:'holst'})));
  const page=await context.newPage();page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>requests.push(r.url()));
  const verify=async()=>{
   await page.locator('main h1').waitFor();
   await page.waitForFunction(()=>document.querySelectorAll('.brand-logo-image').length===2&&[...document.querySelectorAll('.brand-logo-image')].every(img=>img.complete&&img.naturalWidth>0));
   assert.equal(await page.locator('.logo-preview-toolbar,.logo-compare-dialog').count(),0);
   for(const img of await page.locator('.brand-logo-image').all()){assert.match(await img.getAttribute('src'),/assets\/logo\.svg\?v=65$/);assert.equal(await img.getAttribute('alt'),'Мольберты.ру');assert.equal(await img.getAttribute('title'),'Мольберты.ру');}
   assert.equal(await page.evaluate(()=>sessionStorage.getItem('molberty-logo-review')),null);
   const layout=await page.evaluate(()=>{
    const logo=document.querySelector('.header>.logo').getBoundingClientRect(),actions=document.querySelector('.header-actions').getBoundingClientRect(),menu=document.querySelector('.header nav');
    const nav=getComputedStyle(menu).display==='none'||getComputedStyle(menu).position==='absolute'?null:menu.getBoundingClientRect();
    return {width:innerWidth,overflow:document.documentElement.scrollWidth-innerWidth,logoRight:logo.right,actionsLeft:actions.left,navLeft:nav?.left};
   });
   assert.ok(layout.overflow<=1,JSON.stringify(layout));assert.ok(layout.logoRight<=layout.actionsLeft+1,JSON.stringify(layout));if(layout.navLeft)assert.ok(layout.logoRight<=layout.navLeft+1,JSON.stringify(layout));
   return layout;
  };
  const routes=['','catalog/','product/bolshoy-stankovyy-buk/','contacts/','prices/','clients/','privacy/','404.html'];
  for(const route of routes){await page.goto(new URL(route,base).href,{waitUntil:'domcontentloaded'});checks.push({route,...await verify()});}
  await page.goto(new URL('?logo-preview=1&logo=chertezh',base).href,{waitUntil:'domcontentloaded'});
  fs.mkdirSync(shots,{recursive:true});
  for(const width of [320,360,390,600,768,900,901,1100,1280,1440,1920]){
   await page.setViewportSize({width,height:1000});checks.push({route:'legacy-preview-url',...await verify()});
   if([390,1440].includes(width)){
    await page.evaluate(()=>document.fonts.ready);await page.screenshot({path:path.join(shots,'header-'+width+'.png'),animations:'disabled'});
    await page.locator('#footer').scrollIntoViewIfNeeded();await page.screenshot({path:path.join(shots,'footer-'+width+'.png'),animations:'disabled'});await page.evaluate(()=>scrollTo(0,0));
   }
  }
  await page.setViewportSize({width:390,height:844});await page.locator('.mobile-menu').click();assert.equal(await page.locator('.mobile-menu').getAttribute('aria-expanded'),'true');await page.locator('.header nav a[href="catalog/"]').first().click();await page.waitForURL('**/catalog/*');await verify();
  await page.locator('.header>.logo').click();await page.waitForURL('**/index.html');await verify();
  const iconResponse=await context.request.get(new URL('assets/favicon.svg?v=64',base).href);assert.ok(iconResponse.ok());assert.ok((await iconResponse.text()).includes('M25 5v55'));
  const logoResponse=await context.request.get(new URL('assets/logo.svg?v=65',base).href);assert.ok(logoResponse.ok());const logo=await logoResponse.text();assert.ok(logo.includes('<title id="title">Мольберты.ру</title>'));assert.ok(logo.includes('width="560" height="144"'));
  assert.ok(!requests.some(u=>/logo-preview\.(?:css|js)|logo-options/.test(u)));
  const noJS=await browser.newContext({javaScriptEnabled:false,viewport:{width:390,height:844}});
  const staticPage=await noJS.newPage();
  for(const route of ['','product/bolshoy-stankovyy-buk/']){await staticPage.goto(new URL(route,base).href,{waitUntil:'load'});assert.equal(await staticPage.locator('.brand-logo-image').count(),2);assert.ok(await staticPage.locator('.header .brand-logo-image').evaluate(img=>img.complete&&img.naturalWidth>0));}
  await noJS.close();assert.deepEqual(errors,[]);
  const result={passed:true,checkedAt:new Date().toISOString(),approvedLogo:'03 Лира',viewports:[320,360,390,600,768,900,901,1100,1280,1440,1920],routes,checks,oldPreviewCannotOverride:true,noPreviewAssetsRequested:true,noJavaScript:true,faviconMatches:true,screenshots:shots};
  fs.writeFileSync(path.resolve(__dirname,'../qa/logo-preview-test-result.json'),JSON.stringify(result,null,2)+'\n');console.log('Approved Lira logo: header, footer, mobile navigation, favicon, legacy preview and no-JS — PASS');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});
