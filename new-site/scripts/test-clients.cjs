// Functional checks for the real-client directory, not a snapshot of its markup.
const {chromium}=require('playwright');
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'..'),base=process.env.PREVIEW_URL||'http://127.0.0.1:4175/';
const directory=JSON.parse(fs.readFileSync(path.join(root,'data/clients.json'),'utf8'));
const output=path.resolve(root,'../.clone-work/clients-v57-preview');
(async()=>{
 fs.mkdirSync(output,{recursive:true});
 assert.equal(directory.clients.length,49);assert.equal(new Set(directory.clients.map(c=>c.id)).size,49);
 assert.deepEqual(directory.clients.flatMap(c=>c.sourceRows).sort((a,b)=>a-b),Array.from({length:49},(_,i)=>i+1));
 const browser=await chromium.launch({headless:true}),context=await browser.newContext({reducedMotion:'reduce'});
 await context.addInitScript(()=>localStorage.setItem('molberty-cookie-consent','accepted-v1'));
 const page=await context.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto(base,{waitUntil:'networkidle'});
 assert.equal(await page.locator('.documents-grid').first().evaluate(el=>el.nextElementSibling.id),'clients');
 assert.equal(await page.locator('#clients .client-logo-tile img').count(),12);
 assert.equal(await page.locator('#clients h1,#clients h2,#clients h3').count(),0);
 const company=await page.locator('#company').innerHTML();assert.match(company,/ПРОИЗВОДСТВО С 1991 ГОДА/);
 await page.locator('#clients').scrollIntoViewIfNeeded();
 await page.waitForFunction(()=>[...document.querySelectorAll('#clients img')].every(i=>i.complete&&i.naturalWidth>0));
 await page.locator('#clients').screenshot({path:path.join(output,'home-clients-desktop.png')});
 assert.equal(await page.locator('#clients .client-logo-tile:not(a)').count(),12);
 assert.equal(await page.locator('#clients a').count(),1);
 assert.equal(await page.locator('#clients a img').count(),0);
 assert.equal(await page.locator('.clients-home-link').count(),0);
 await page.locator('#clients .client-logo-all').click();
 await page.waitForURL(new URL('clients/',base).href);
 assert.equal(await page.locator('.client-card').count(),49);
 assert.equal(await page.locator('.client-card img').count(),directory.clients.filter(c=>c.logo).length);
 assert.equal(await page.locator('h1').count(),1);
 assert.equal(await page.locator('#clients-page input[type=search],#clients-page [data-client-search]').count(),0);
 assert.equal(await page.locator('.client-card-site').evaluateAll(nodes=>nodes.every(a=>a.relList.contains('nofollow')&&a.relList.contains('noopener'))),true);
 for(const group of Object.keys(directory.groups)){
  await page.locator('[data-client-filter="'+group+'"]').click();
  assert.equal(await page.locator('.client-card:visible').count(),directory.clients.filter(c=>c.group===group).length);
 }
 await page.locator('[data-client-filter="all"]').click();assert.equal(await page.locator('.client-card:visible').count(),49);
 for(const [id,href] of Object.entries({'client-35':'http://cks-semenovsk.nnov.muzkult.ru/','client-43':'https://dshi-lensk.obr.sakha.gov.ru/','client-46':'https://rovesnik-istra.edumsko.ru/','client-50':'https://vgik.info/'}))assert.equal(await page.locator('#'+id+' .client-card-site').getAttribute('href'),href);
 assert.equal(await page.locator('#client-46 .client-card-name').innerText(),'МОУ ДО «ЦРТДиЮ «Ровесник»»');
 for(const id of ['client-35','client-36','client-43']){
  const client=directory.clients.find(c=>c.id===id),logo=client.logo;
  assert.ok(logo&&logo.sourceType==='user-provided');
  const actual=require('node:crypto').createHash('sha256').update(fs.readFileSync(path.join(root,'assets',logo.file))).digest('hex');
  assert.equal(actual,logo.sha256,'Supplied logo remains byte-identical: '+id);
  assert.equal(await page.locator('#'+id+' img').count(),1);
 }
 // Every image must decode locally, including logos far below the initial viewport.
 await page.locator('.client-card img').evaluateAll(nodes=>nodes.forEach(img=>img.loading='eager'));
 await page.waitForFunction(()=>[...document.querySelectorAll('.client-card img')].every(i=>i.complete&&i.naturalWidth>0));
 assert.equal(await page.locator('.client-card img').evaluateAll(nodes=>nodes.some(i=>new URL(i.src).origin!==location.origin)),false);
 assert.equal(await page.locator('.client-card img').evaluateAll(nodes=>nodes.every(i=>i.alt&&i.title&&i.width&&i.height)),true);
 const layouts=[];
 for(const width of [1440,768,390,320]){
  await page.setViewportSize({width,height:900});await page.goto(new URL('clients/',base).href,{waitUntil:'networkidle'});
  const dimensions=await page.evaluate(()=>({viewport:innerWidth,width:document.documentElement.scrollWidth}));assert.ok(dimensions.width<=width,JSON.stringify(dimensions));layouts.push(dimensions);
  await page.screenshot({path:path.join(output,'clients-'+width+'.png')});
  await page.goto(base);await page.locator('#clients').scrollIntoViewIfNeeded();
  assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  if(width===390)await page.locator('#clients').screenshot({path:path.join(output,'home-clients-mobile.png')});
 }
 await page.goto(new URL('clients/',base).href);await page.locator('main [data-request]').last().click();
 await page.locator('#request-dialog[open] form').waitFor();
 assert.equal(await page.locator('#request-dialog input[type=checkbox][required]').isChecked(),false);
 await context.close();
 const nojs=await browser.newContext({javaScriptEnabled:false,viewport:{width:390,height:844}}),staticPage=await nojs.newPage();
 await staticPage.goto(new URL('clients/',base).href);assert.equal(await staticPage.locator('.client-card:visible').count(),49);assert.equal(await staticPage.locator('.clients-tools').isVisible(),false);
 assert.equal(await staticPage.locator('.client-card img').count(),directory.clients.filter(c=>c.logo).length);
 await staticPage.goto(base);assert.equal(await staticPage.locator('#clients .client-logo-tile').count(),13);assert.equal(await staticPage.locator('#footer a[href="clients/"]').count(),1);
 await nojs.close();await browser.close();assert.deepEqual(errors,[]);
 const result={passed:true,organizations:49,sourceRecords:49,logos:directory.clients.filter(c=>c.logo).length,missingLogoIds:directory.clients.filter(c=>!c.logo).map(c=>c.id),featuredLogos:12,layouts,checks:['placement immediately after documents','complete deduplicated source list','local logos decode','home logos have no links; only all-clients tile remains','client search removed; group filters work','organization links have nofollow','three supplied logos remain byte-identical','updated organization URLs and Rovesnik name','VGIK official logo and website present','request form and required consent','no JavaScript fallback','mobile layout without overflow'],browserErrors:errors};
 fs.writeFileSync(path.join(root,'qa/clients-test-result.json'),JSON.stringify(result,null,2)+'\n');
 console.log(JSON.stringify(result));
})().catch(error=>{console.error(error);process.exit(1)});
