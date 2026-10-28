/* Optional review mode. Loaded only after an explicit preview link or in the same preview tab. */
(()=>{
 'use strict';
 const storageKey='molberty-logo-review',scriptURL=new URL(document.currentScript.src),assetsURL=new URL('.',scriptURL);
 const params=new URLSearchParams(location.search),queryId=params.get('logo');
 let stored={};try{stored=JSON.parse(sessionStorage.getItem(storageKey)||'{}')||{}}catch{}
 let selectedId='current',sequence=0,stopped=false,collapsed=!!stored.collapsed;
 const originals=new Map(),reduced=matchMedia('(prefers-reduced-motion: reduce)');
 const sheet=document.createElement('link');sheet.rel='stylesheet';sheet.href=new URL('logo-preview.css',assetsURL).href;
 const cssReady=new Promise((resolve,reject)=>{sheet.onload=resolve;sheet.onerror=reject});document.head.append(sheet);
 const escape=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const drawing=(name)=>`<svg viewBox="0 0 24 24" width="19" height="19" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="${{grid:'M3 3h7v7H3zM14 3h7v7h-7zM3 14h7v7H3zM14 14h7v7h-7z',collapse:'m6 14 6-6 6 6',expand:'m6 10 6 6 6-6',close:'m6 6 12 12M6 18 18 6'}[name]}"/></svg>`;
 const manifestReady=fetch(new URL('../data/logo-options.json',assetsURL)).then(r=>{if(!r.ok)throw Error('Logo options unavailable');return r.json()});
 Promise.all([cssReady,manifestReady]).then(async([,manifest])=>{
  const options=manifest.options;if(!Array.isArray(options)||!options.length)throw Error('Empty logo options');
  const optionById=id=>options.find(option=>option.id===id);
  const imageURL=option=>new URL(option.asset,assetsURL).href;
  document.querySelectorAll('.header>.logo,.footer-grid .logo').forEach(logo=>originals.set(logo,logo.innerHTML));
  const header=document.querySelector('#header');
  const toolbar=document.createElement('section');toolbar.className='logo-preview-toolbar';toolbar.setAttribute('aria-label','Примерка логотипа');
  toolbar.innerHTML=`<div class="wrap logo-preview-inner"><div class="logo-preview-label"><span>Варианты логотипа</span><strong data-logo-current></strong></div><div class="logo-preview-settings"><button type="button" class="logo-preview-button" data-logo-prev aria-label="Предыдущий логотип">←</button><label class="logo-preview-select"><span class="sr-only">Выберите логотип</span><select data-logo-select>${options.map((option,i)=>`<option value="${escape(option.id)}">${i===0?'Текущий':String(i).padStart(2,'0')+' · '+escape(option.title)}</option>`).join('')}</select></label><button type="button" class="logo-preview-button" data-logo-next aria-label="Следующий логотип">→</button></div><p class="logo-preview-description" data-logo-description></p><div class="logo-preview-tools"><button type="button" class="logo-preview-button logo-preview-compare" data-logo-compare aria-label="Сравнить все варианты" title="Сравнить все варианты">${drawing('grid')}<span class="logo-compare-label">Сравнить все</span></button><button type="button" class="logo-preview-button" data-logo-collapse aria-label="Свернуть панель" title="Свернуть панель">${drawing('collapse')}</button><button type="button" class="logo-preview-button" data-logo-exit aria-label="Выйти из примерки" title="Выйти из примерки">${drawing('close')}</button></div><span class="sr-only" aria-live="polite" data-logo-status></span></div>`;
  header.after(toolbar);
  const select=toolbar.querySelector('[data-logo-select]'),status=toolbar.querySelector('[data-logo-status]');
  const gallery=document.createElement('dialog');gallery.className='logo-compare-dialog';gallery.setAttribute('aria-labelledby','logo-compare-title');
  gallery.innerHTML=`<button class="logo-compare-close" type="button" data-logo-gallery-close aria-label="Закрыть сравнение">${drawing('close')}</button><div class="eyebrow"><span>Мольберты.ру</span> ЛОГОТИП</div><h2 id="logo-compare-title">Выберите направление</h2><p class="logo-compare-intro">Четыре новых варианта по вашим референсам и текущий логотип для сравнения. Нажмите на вариант, чтобы увидеть его в шапке.</p><div class="logo-compare-grid">${options.map((option,i)=>`<article class="logo-compare-card"><button type="button" data-logo-choice="${escape(option.id)}" aria-pressed="false"><span class="logo-choice-number">${i===0?'Сейчас':String(i).padStart(2,'0')}</span><img src="${imageURL(option)}" alt="${escape(option.title)} — Мольберты.ру" width="280" height="72" loading="lazy"><strong>${escape(option.title)}</strong><span class="logo-choice-description">${escape(option.description)}</span></button><a href="${imageURL(option)}" download="molberty-${escape(option.id)}.svg">Скачать SVG ↗</a></article>`).join('')}</div><p class="logo-compare-note">Выбор действует в этой вкладке. Для согласования можно назвать вариант или скопировать адрес страницы.</p>`;
  document.body.append(gallery);
  const save=()=>{try{sessionStorage.setItem(storageKey,JSON.stringify({active:true,id:selectedId,collapsed}))}catch{}};
  const updateURL=()=>{const address=new URL(location.href);address.searchParams.set('logo-preview','1');address.searchParams.set('logo',selectedId);history.replaceState(history.state,'',address)};
  function setCollapsed(value){collapsed=value;toolbar.classList.toggle('is-collapsed',collapsed);toolbar.querySelector('.logo-preview-settings').hidden=collapsed;toolbar.querySelector('.logo-preview-description').hidden=collapsed;const button=toolbar.querySelector('[data-logo-collapse]');button.innerHTML=drawing(collapsed?'expand':'collapse');button.setAttribute('aria-expanded',String(!collapsed));button.setAttribute('aria-label',collapsed?'Показать варианты':'Свернуть панель');button.title=collapsed?'Показать варианты':'Свернуть панель';save()}
  function syncControls(option){select.value=option.id;toolbar.querySelector('[data-logo-current]').textContent=option.title;toolbar.querySelector('[data-logo-description]').textContent=option.description;gallery.querySelectorAll('[data-logo-choice]').forEach(button=>button.setAttribute('aria-pressed',String(button.dataset.logoChoice===option.id)))}
  function preload(option){return new Promise((resolve,reject)=>{const img=new Image();img.onload=()=>resolve(img);img.onerror=reject;img.src=imageURL(option)})}
  async function choose(id){
   const option=optionById(id)||optionById(manifest.defaultId),ticket=++sequence;select.value=option.id;
   try{
    if(option.id!=='current')await preload(option);
    if(stopped||ticket!==sequence)return;
    for(const [logo,original] of originals){
     logo.classList.toggle('logo--preview',option.id!=='current');
     if(option.id==='current')logo.innerHTML=original;
     else{const image=document.createElement('img');image.src=imageURL(option);image.alt='Мольберты.ру — '+option.title;image.className='logo-variant-image';image.width=280;image.height=72;logo.replaceChildren(image)}
     if(!reduced.matches&&logo.animate)logo.animate([{opacity:.35},{opacity:1}],{duration:180,easing:'ease-out'});
    }
    selectedId=option.id;syncControls(option);save();updateURL();status.textContent='Логотип «'+option.title+'». '+option.description;
   }catch{if(ticket===sequence&&!stopped){select.value=selectedId;status.textContent='Не удалось загрузить вариант. Попробуйте выбрать его ещё раз.'}}
  }
  const headerHeight=()=>document.documentElement.style.setProperty('--logo-preview-header-height',header.getBoundingClientRect().height+'px');
  const observer=typeof ResizeObserver==='function'?new ResizeObserver(headerHeight):null;observer?.observe(header);addEventListener('resize',headerHeight);headerHeight();
  function dismissGallery(){if(window.siteMotion)window.siteMotion.closeDialog(gallery);else gallery.close()}
  function exit(){stopped=true;sequence++;observer?.disconnect();removeEventListener('resize',headerHeight);removeEventListener('pageshow',restorePreview);for(const [logo,original] of originals){logo.innerHTML=original;logo.classList.remove('logo--preview')}if(gallery.open)gallery.close();gallery.remove();toolbar.remove();sheet.remove();document.documentElement.style.removeProperty('--logo-preview-header-height');try{sessionStorage.removeItem(storageKey)}catch{}const address=new URL(location.href);address.searchParams.delete('logo-preview');address.searchParams.delete('logo');history.replaceState(history.state,'',address);header.querySelector('.logo')?.focus({preventScroll:true})}
  function restorePreview(event){if(!event.persisted||stopped)return;let saved=null;try{saved=JSON.parse(sessionStorage.getItem(storageKey)||'null')}catch{return}if(!saved?.active){exit();return}setCollapsed(!!saved.collapsed);choose(optionById(saved.id)?saved.id:manifest.defaultId)}
  addEventListener('pageshow',restorePreview);
  select.addEventListener('change',()=>choose(select.value));
  toolbar.querySelector('[data-logo-prev]').addEventListener('click',()=>{const index=options.findIndex(option=>option.id===select.value);choose(options[(index-1+options.length)%options.length].id)});
  toolbar.querySelector('[data-logo-next]').addEventListener('click',()=>{const index=options.findIndex(option=>option.id===select.value);choose(options[(index+1)%options.length].id)});
  toolbar.querySelector('[data-logo-collapse]').addEventListener('click',()=>setCollapsed(!collapsed));
  toolbar.querySelector('[data-logo-exit]').addEventListener('click',exit);
  toolbar.querySelector('[data-logo-compare]').addEventListener('click',()=>{if(window.siteMotion)window.siteMotion.openDialog(gallery);else gallery.showModal()});
  gallery.querySelector('[data-logo-gallery-close]').addEventListener('click',dismissGallery);
  gallery.querySelectorAll('[data-logo-choice]').forEach(button=>button.addEventListener('click',()=>{choose(button.dataset.logoChoice);dismissGallery()}));
  gallery.addEventListener('click',event=>{if(event.target===gallery){const r=gallery.getBoundingClientRect();if(event.clientX<r.left||event.clientX>r.right||event.clientY<r.top||event.clientY>r.bottom)dismissGallery()}});
  await choose(optionById(queryId)?queryId:optionById(stored.id)?stored.id:manifest.defaultId);setCollapsed(collapsed);
 }).catch(()=>{sheet.remove();console.warn('Не удалось открыть примерку логотипов.')});
})();
