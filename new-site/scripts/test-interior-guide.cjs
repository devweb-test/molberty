// Exercise measurement validation, recommendation boundaries and request handoff.
const {chromium}=require('playwright'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const root=path.resolve(__dirname,'..'),base=process.env.PREVIEW_URL||'http://127.0.0.1:4175/';
(async()=>{
 const browser=await chromium.launch(),checks=[],errors=[];
 for(const width of [320,390,1440]){
  const context=await browser.newContext({viewport:{width,height:1000},reducedMotion:'reduce'});
  await context.addInitScript(()=>localStorage.setItem('molberty-cookie-consent','accepted-v1'));
  const page=await context.newPage();page.on('pageerror',error=>errors.push(error.message));
  await page.goto(new URL('molberty-dekorativnye/',base).href,{waitUntil:'networkidle'});
  const guide=page.locator('#interior-guide');assert.equal(await guide.locator('.guide-step').count(),4);assert.equal(await guide.locator('h2').innerText(),'Мольберт для Вашей картины.');
  assert.equal(await guide.locator('a[href$="guide/"]').count(),0);
  const initialCount=await page.locator('#catalog-results .product-card').count();assert(initialCount>0);
  await page.locator('#sort').selectOption('price-desc');assert.equal(await page.locator('#catalog-results .product-card').count(),initialCount);
  await guide.locator('[data-interior-quiz]').click();
  const form=()=>page.locator('.interior-quiz-form');
  await form().locator('button[type=submit]').click();assert.equal(await page.locator('#interior-question-title').innerText(),'Габариты картины');
  await form().locator('[name=width]').fill('-1');assert.equal(await form().locator('[name=width]').evaluate(input=>input.checkValidity()),false);
  await form().locator('[name=width]').fill('60');await form().locator('[name=height]').fill('80');await form().locator('button[type=submit]').click();
  await form().locator('[name=exposure]').fill('70');await page.locator('[data-interior-back]').click();assert.equal(await form().locator('[name=width]').inputValue(),'60');await form().locator('button[type=submit]').click();assert.equal(await form().locator('[name=exposure]').inputValue(),'70');await form().locator('button[type=submit]').click();
  await form().locator('[name=weight]').fill('5.5');await form().locator('[name=depth]').fill('4');
  assert.equal(await form().locator('input[type=checkbox][required]').isChecked(),false);await form().locator('button[type=submit]').click();assert.equal(await page.locator('#interior-question-title').innerText(),'Вес картины и глубина рамы');
  await form().locator('input[type=checkbox][required]').check();await form().locator('button[type=submit]').click();
  assert.equal(await page.locator('.interior-quiz-model').count(),2);assert.match(await page.locator('.interior-quiz-summary').innerText(),/5,5 кг/);assert.match(await page.locator('.interior-quiz-note').innerText(),/подтвердим/);
  assert(await page.locator('.interior-quiz-model').evaluateAll(nodes=>nodes.every(a=>a.getAttribute('href').includes('product/')&&a.querySelector('img[alt][title]')&&a.querySelector('.interior-quiz-price'))));
  assert(await page.evaluate(()=>document.querySelector('#request-dialog').scrollWidth<=document.querySelector('#request-dialog').clientWidth));
  if(width===1440){await page.locator('#request-dialog').screenshot({path:path.resolve(root,'../.clone-work/interior-guide-v60-result.png')});}
  await page.locator('[data-interior-request]').click();const message=await page.locator('#request-form textarea').inputValue();for(const text of ['60 × 80 см','70 см','5,5 кг','4 см'])assert(message.includes(text),text);assert.equal(await page.locator('#request-form input[type=checkbox][required]').isChecked(),false);
  await page.locator('[data-close]').click();await page.waitForFunction(()=>!document.querySelector('#request-dialog').open);
  async function choose(data){await guide.locator('[data-interior-quiz]').click();for(const fields of [['width','height'],['exposure'],['weight','depth']]){for(const field of fields)await form().locator('[name='+field+']').fill(String(data[field]));if(fields.includes('depth'))await form().locator('input[type=checkbox][required]').check();await form().locator('button[type=submit]').click();}}
  if(width===1440){
   await choose({width:80,height:100,exposure:70,weight:8,depth:8});assert.equal(await page.locator('.interior-quiz-model').count(),1);assert((await page.locator('.interior-quiz-model').getAttribute('href')).includes('molbert-ampir'));
   await page.locator('[data-close]').click();await page.waitForFunction(()=>!document.querySelector('#request-dialog').open);
   await choose({width:90,height:105,exposure:70,weight:8,depth:6});assert.equal(await page.locator('.interior-quiz-model').count(),1);assert((await page.locator('.interior-quiz-model').getAttribute('href')).includes('molbert-eksklyuziv'));
   await page.locator('[data-close]').click();await page.waitForFunction(()=>!document.querySelector('#request-dialog').open);
   await choose({width:200,height:150,exposure:70,weight:15,depth:12});assert.equal(await page.locator('.interior-quiz-model').count(),0);assert.match(await page.locator('#dialog-content').innerText(),/отдельно согласовать/);
   await page.locator('[data-close]').click();await page.waitForFunction(()=>!document.querySelector('#request-dialog').open);
  }
  await guide.scrollIntoViewIfNeeded();await page.mouse.click(5,200);assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  if(width!==390)await guide.screenshot({path:path.resolve(root,'../.clone-work/interior-guide-v60-'+width+'.png'),style:'#header,.back-top,.mobile-bottom-nav{visibility:hidden!important}'});
  checks.push({width,steps:4,validation:true,backPreservesValues:true,consentRequired:true,requestContainsAllMeasurements:true,noOverflow:true});await context.close();
 }
 // The original guide keeps its original questionnaire.
 const context=await browser.newContext({reducedMotion:'reduce'}),page=await context.newPage();await page.goto(new URL('guide/',base).href,{waitUntil:'networkidle'});assert.equal(await page.locator('script[src*="interior-guide.js"]').count(),0);await page.locator('[data-quiz]').click();for(const answer of [0,0,0])await page.locator('[data-answer="'+answer+'"]').click();assert((await page.locator('#dialog-content>a.btn').getAttribute('href')).includes('molberty-nastolnye/'));await context.close();
 const nojs=await browser.newContext({javaScriptEnabled:false}),staticPage=await nojs.newPage();await staticPage.goto(new URL('molberty-dekorativnye/',base).href);assert.equal(await staticPage.locator('#interior-guide .guide-step').count(),4);assert(await staticPage.locator('#interior-guide noscript a[href^="tel:"]').isVisible());await nojs.close();
 const prerender=await browser.newContext();await prerender.addInitScript(()=>window.SITE_PRERENDER=true);const rendered=await prerender.newPage();await rendered.goto(new URL('molberty-dekorativnye/',base).href,{waitUntil:'networkidle'});assert.equal(await rendered.locator('#interior-guide .guide-step').count(),4);assert.equal(await rendered.locator('#category [data-quiz]').count(),0);await prerender.close();await browser.close();assert.deepEqual(errors,[]);
 const report={passed:true,checks,recommendationBoundaries:true,manualSelectionFallback:true,originalGuideQuizUnchanged:true,noJavaScriptGuide:true,prerender:true,browserErrors:errors};fs.writeFileSync(path.join(root,'qa/interior-guide-test-result.json'),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report));
})().catch(error=>{console.error(error);process.exit(1)});
