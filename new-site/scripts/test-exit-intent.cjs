const fs=require('fs'),assert=require('assert'),{chromium}=require('playwright');
const base=process.env.MOLBERTY_TEST_URL||'http://127.0.0.1:4173/';
const output=process.env.MOLBERTY_TEST_OUTPUT||'/tmp/molberty-exit-intent-qa';
fs.mkdirSync(output,{recursive:true});
const key='molberty-exit-offer-until',errors=[],checks=[];
checks.push=(...items)=>{console.log(items.join('; '));return Array.prototype.push.apply(checks,items)};
const clockTime=new Date('2026-11-11T16:00:00Z');
async function installClock(page){await page.clock.install({time:clockTime});await page.clock.pauseAt(new Date(clockTime.getTime()+1000))}
async function visit(page,route=''){await page.goto(base+route,{waitUntil:'domcontentloaded'});await page.waitForFunction(()=>typeof callbackRequest==='function')}
async function leave(page,edge='top'){const {width,height}=page.viewportSize();await page.mouse.move(width/2,height/2);const point={top:[width/2,-10],left:[-10,height/2],right:[width+10,height/2],bottom:[width/2,height+10]}[edge];await page.mouse.move(...point)}
async function open(page){return page.locator('#request-dialog').evaluate(dialog=>dialog.open)}
async function close(page,way='cross'){
 if(way==='escape')await page.keyboard.press('Escape');
 else if(way==='continue')await page.locator('.exit-offer-continue').click();
 else if(way==='backdrop')await page.mouse.click(5,5);
 else await page.locator('#request-dialog>.close').click();
 await page.clock.runFor(40);
 await page.locator('#request-dialog').waitFor({state:'hidden'});
}
async function allowAgain(page,edge='top'){
 const remaining=await page.evaluate(key=>Number(localStorage.getItem(key))-Date.now(),key);
 if(remaining>=0)await page.clock.fastForward(remaining+1);
 await page.locator('main').click({position:{x:8,y:8}});
 await leave(page,edge);
 assert(await open(page),'Exit offer becomes available after expiry');
}
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:process.env.MOLBERTY_CHROMIUM||'/home/v_chernyshov/.cache/ms-playwright/chromium_headless_shell-1248/chrome-headless-shell-linux64/chrome-headless-shell'});
 const context=await browser.newContext({viewport:{width:1440,height:1000},reducedMotion:'reduce'});
 const page=await context.newPage();page.setDefaultTimeout(10000);page.on('pageerror',e=>errors.push(e.message));
 await installClock(page);await visit(page);
 await leave(page);assert(!await open(page));checks.push('No offer before the initial eight seconds');
 await page.clock.fastForward(8001);await leave(page);
 assert(await open(page));assert.equal(await page.locator('#request-form[data-exit-offer]').count(),1);
 assert.equal(await page.locator('#request-dialog h1,#request-dialog h2,#request-dialog h3').count(),0);
 assert.equal(await page.locator('#request-form [name=name]').getAttribute('required'),'');
 assert.equal(await page.locator('#request-form [name=contact]').getAttribute('type'),'tel');
 assert.equal(await page.locator('#request-form [name=message]').getAttribute('rows'),'2');
 assert.equal(await page.locator('#request-form [name=personal_data_consent]').isChecked(),false);
 assert.equal(await page.locator('#request-form .form-consent a').count(),2);
 assert.equal(await page.locator('#request-dialog').getAttribute('aria-labelledby'),'callback-title');
 assert.equal(await page.locator('h1').count(),1);
 await page.screenshot({path:output+'/desktop.png'});checks.push('Desktop exit, callback fields, consent, accessible name and heading semantics');
 await page.clock.fastForward(60000);await close(page);
 let remaining=await page.evaluate(key=>Number(localStorage.getItem(key))-Date.now(),key);
 assert(remaining>359000&&remaining<=360000,'Six minutes counted from closing, not from first showing: '+remaining);
 await visit(page,'catalog/');await page.clock.fastForward(8001);await leave(page);assert(!await open(page));
 remaining=await page.evaluate(key=>Number(localStorage.getItem(key))-Date.now(),key);
 await page.clock.fastForward(remaining-1);await leave(page);assert(!await open(page),'Blocked one millisecond before expiry');
 await page.clock.fastForward(2);await leave(page);assert(await open(page));checks.push('Six-minute dismissal interval survives navigation, exact expiry checked');
 await close(page,'escape');
 await allowAgain(page,'left');await close(page,'continue');
 await allowAgain(page,'right');await close(page,'backdrop');checks.push('Cross, Escape, continue and backdrop all start cooldown');

 // A second tab uses the stored interval, instead of showing a new popup.
 const second=await context.newPage();second.on('pageerror',e=>errors.push(e.message));await installClock(second);
 await visit(second,'contacts/');await second.clock.fastForward(20000);await leave(second);assert(!await open(second));
 await second.close();await page.bringToFront();checks.push('Suppression also applies in another tab');

 // An expired offer may not replace an open cart or interrupt typing.
 remaining=await page.evaluate(key=>Number(localStorage.getItem(key))-Date.now(),key);
 await page.clock.fastForward(remaining+1);
 await page.locator('[data-selection]').click();const cartText=await page.locator('#dialog-content').innerText();
 await leave(page);assert.equal(await page.locator('#dialog-content').innerText(),cartText);await close(page);
 await page.locator('#catalog-search').fill('Лира');await leave(page);assert(!await open(page));
 await page.locator('#catalog-search').blur();await page.locator('.header-contact [data-callback]').click();
 await page.locator('#request-form [name=name]').fill('Тестовый посетитель');await leave(page);
 assert.equal(await page.locator('#request-form [name=name]').inputValue(),'Тестовый посетитель');
 assert.equal(await page.locator('[data-exit-offer]').count(),0);await close(page);
 checks.push('Existing cart, manual callback and typing are never replaced');

 await leave(page,'bottom');assert(await open(page));
 await page.locator('#request-form [name=name]').fill('Тестовый посетитель');
 await page.locator('#request-form [name=contact]').fill('+7 999 123-45-67');
 await page.locator('#request-form [name=message]').fill('С 10:00 до 12:00');
 await page.locator('#request-form [type=submit]').click();assert.equal(await page.locator('#request-form').count(),1);
 await page.locator('#request-form [name=personal_data_consent]').check();
 await page.locator('#request-form [type=submit]').click();
 assert.equal(await page.locator('#request-form').count(),0);
 assert.match(await page.locator('#dialog-content').innerText(),/Данные не отправлены/);
 assert.equal(await page.locator('#request-dialog').getAttribute('aria-labelledby'),null);
 assert.equal(await page.locator('#request-dialog.exit-offer-dialog').count(),0);
 await close(page);await leave(page);assert(!await open(page));
 checks.push('Consent is required; valid submission uses the demo result and suppresses further offers');

 // A blocked storage implementation falls back to the current page's memory.
 const blocked=await browser.newContext({viewport:{width:1440,height:1000},reducedMotion:'reduce'});
 await blocked.addInitScript(()=>{Storage.prototype.getItem=()=>{throw new DOMException('Blocked','SecurityError')};Storage.prototype.setItem=()=>{throw new DOMException('Blocked','SecurityError')}});
 const noStorage=await blocked.newPage();noStorage.on('pageerror',e=>errors.push(e.message));
 await installClock(noStorage);await visit(noStorage,'about/');await noStorage.clock.fastForward(9000);await leave(noStorage);assert(await open(noStorage));
 await close(noStorage);await leave(noStorage);assert(!await open(noStorage));await blocked.close();checks.push('Closing still suppresses the popup if browser storage is unavailable');

 const mobile=await browser.newContext({viewport:{width:390,height:844},isMobile:true,hasTouch:true,reducedMotion:'reduce'});
 const phone=await mobile.newPage();phone.on('pageerror',e=>errors.push(e.message));await installClock(phone);await visit(phone);await phone.clock.fastForward(20000);
 await phone.evaluate(()=>{document.dispatchEvent(new PointerEvent('pointermove',{pointerType:'touch',clientX:120,clientY:200}));document.dispatchEvent(new PointerEvent('pointerout',{pointerType:'mouse',clientX:120,clientY:-1,relatedTarget:null}))});
 assert(!await open(phone));checks.push('No automatic popup on touch-only devices');
 // Preview narrow layouts even though touch-only visitors are not auto-targeted.
 await phone.evaluate(()=>callbackRequest({capture:true}));
 for(const width of [320,390]){
  await phone.setViewportSize({width,height:844});
  const overflow=await phone.locator('#request-dialog').evaluate(el=>el.scrollWidth>el.clientWidth+1);
  assert.equal(overflow,false,'Dialog has no horizontal overflow at '+width+'px');
  const overlap=await phone.evaluate(()=>{const a=document.querySelector('.exit-offer-symbol').getBoundingClientRect(),b=document.querySelector('#request-dialog>.close').getBoundingClientRect();return a.left<b.right&&a.right>b.left&&a.top<b.bottom&&a.bottom>b.top});
  assert.equal(overlap,false,'The thematic icon leaves the close button clear at '+width+'px');
  assert(await phone.locator('#request-form [name=contact]').isVisible());
  await phone.screenshot({path:output+'/mobile-'+width+'.png'});
 }
 await mobile.close();checks.push('320px and 390px layouts retain readable fields and controls');
 await context.close();await browser.close();assert.deepEqual(errors,[]);
 const result={base,checks,jsErrors:errors,cooldownMs:360000,firstEligibleAfterMs:8000};
 fs.writeFileSync(output+'/browser.json',JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify(result,null,2));
})().catch(error=>{console.error(error);process.exit(1)});
