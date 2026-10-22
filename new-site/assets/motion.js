'use strict';
// Progressive enhancement: content and native controls remain usable without animation.
(()=>{
 const preference=matchMedia('(prefers-reduced-motion: reduce)'),mobile=matchMedia('(max-width: 1350px)');
 const easing='cubic-bezier(.2,.7,.2,1)',detailsAnimations=new Map(),closingDialogs=new Map(),openingDialogs=new Map(),contentAnimations=new Map();
 const enabled=()=>!preference.matches&&typeof Element.prototype.animate==='function';
 function animateContent(element,keyframes,duration=180){
  contentAnimations.get(element)?.cancel();contentAnimations.delete(element);
  if(!enabled())return;
  const animation=element.animate(keyframes,{duration,easing});contentAnimations.set(element,animation);
  animation.finished.then(()=>{if(contentAnimations.get(element)===animation)contentAnimations.delete(element)}).catch(()=>{});
 }
 function openDialog(modal){
  const closing=closingDialogs.get(modal);
  if(closing){closingDialogs.delete(modal);closing.animation.cancel();modal.classList.remove('motion-closing');modal.style.removeProperty('--backdrop-from')}
  if(modal.open&&!closing){const content=modal.querySelector('#dialog-content');if(content)animateContent(content,[{opacity:.8},{opacity:1}],160);return;}
  openingDialogs.get(modal)?.cancel();openingDialogs.delete(modal);
  if(!modal.open)modal.showModal();
  if(enabled()){
   const animation=modal.animate([{opacity:0,transform:'translateY(10px) scale(.995)'},{opacity:1,transform:'translateY(0) scale(1)'}],{duration:260,easing});openingDialogs.set(modal,animation);
   animation.finished.then(()=>{if(openingDialogs.get(modal)===animation)openingDialogs.delete(modal)}).catch(()=>{});
  }
 }
 function closeDialog(modal){
  if(!modal.open||closingDialogs.has(modal))return;
  const from={opacity:getComputedStyle(modal).opacity,transform:getComputedStyle(modal).transform};
  openingDialogs.get(modal)?.cancel();openingDialogs.delete(modal);
  if(!enabled()){modal.close();return}
  modal.style.setProperty('--backdrop-from',getComputedStyle(modal,'::backdrop').opacity);
  modal.classList.add('motion-closing');
  const animation=modal.animate([from,{opacity:0,transform:'translateY(8px) scale(.995)'}],{duration:180,easing});
  const state={animation};closingDialogs.set(modal,state);
  animation.finished.then(()=>{
   if(closingDialogs.get(modal)!==state)return;
   closingDialogs.delete(modal);modal.classList.remove('motion-closing');modal.style.removeProperty('--backdrop-from');modal.close();
  }).catch(()=>{});
 }
 window.siteMotion={openDialog,closeDialog};
 document.querySelectorAll('dialog').forEach(modal=>modal.addEventListener('cancel',event=>{
  if(enabled()){event.preventDefault();closeDialog(modal)}
 }));
 function finishDetails(details,state){
  if(detailsAnimations.get(details)!==state)return;
  detailsAnimations.delete(details);details.open=state.expanded;for(const child of details.children)if(child.tagName!=='SUMMARY')child.inert=false;details.style.height='';details.style.overflow='';details.classList.remove('motion-collapsing');state.animation.cancel();
 }
 document.addEventListener('click',event=>{
  const summary=event.target.closest('summary');
  if(!summary||summary.parentElement?.tagName!=='DETAILS'||event.defaultPrevented||event.target.closest('a,button,input,select,textarea')||!enabled())return;
  event.preventDefault();
  const details=summary.parentElement,previous=detailsAnimations.get(details),expanded=previous?!previous.expanded:!details.open;
  const start=details.getBoundingClientRect().height;
  details.style.height=start+'px';previous?.animation.cancel();
  details.open=true;for(const child of details.children)if(child.tagName!=='SUMMARY')child.inert=!expanded;details.style.overflow='hidden';details.classList.toggle('motion-collapsing',!expanded);
  let end;
  if(expanded){details.style.height='auto';end=details.getBoundingClientRect().height;details.style.height=start+'px'}
  else{const style=getComputedStyle(details);end=summary.getBoundingClientRect().height+parseFloat(style.borderTopWidth)+parseFloat(style.borderBottomWidth)+parseFloat(style.paddingTop)+parseFloat(style.paddingBottom)}
  const animation=details.animate({height:[start+'px',end+'px']},{duration:260,easing,fill:'both'}),state={expanded,animation};detailsAnimations.set(details,state);
  animation.finished.then(()=>finishDetails(details,state)).catch(()=>{});
 });
 const menuButton=document.querySelector('.mobile-menu'),nav=document.querySelector('.header nav');
 function syncMenu(){
  if(!menuButton||!nav)return;
  const expanded=menuButton.getAttribute('aria-expanded')==='true',hidden=mobile.matches&&!expanded;
  nav.inert=hidden;nav.setAttribute('aria-hidden',String(hidden));menuButton.setAttribute('aria-label',expanded?'Закрыть меню':'Открыть меню');
 }
 if(menuButton&&nav){new MutationObserver(syncMenu).observe(menuButton,{attributes:true,attributeFilter:['aria-expanded']});mobile.addEventListener('change',syncMenu);syncMenu()}
 // Escape closes the mobile menu and returns keyboard focus to its trigger.
 document.addEventListener('keydown',event=>{
  if(event.key!=='Escape'||document.querySelector('dialog[open]')||!mobile.matches||menuButton?.getAttribute('aria-expanded')!=='true')return;
  nav.classList.remove('open');menuButton.setAttribute('aria-expanded','false');menuButton.focus();
 });
 // One-time viewport entrances. The default HTML/CSS stays fully visible;
 // only running Web Animations change opacity, so a missing API cannot hide content.
 const revealSelector=[
  '.hero-copy>.eyebrow','.hero-copy>h1','.hero-copy>p','.hero-buttons','.hero-proof','.hero-visual',
  '.page-intro','.section-heading','.trust-strip>div','.category-tile','.product-card',
  '.audience-grid>article','.steps>article','.production-gallery>figure','.workshop-copy',
  '.usecase-grid>a','.benefit-grid>article','.quiz-banner','.partner>div','.partner-list',
  '.company-original-history','.company-original-craft','.company-original-closing','.company-guide',
  '.price-section','.certificate-section','.case-card','.partner-object','.blog-card','.cta-section',
  '.home-contact-details','.contact-map','.contacts-hours','.route-steps>li','.sales-card',
  '.delivery-methods>a','.payment-summary','.guide-step','.price-group-heading',
  '.article-hero-cover','.article-chapter>h2','.article-original-figure',
  '.product-gallery','.product-info','.subcategory-grid>a','.footer-grid>div'
 ].join(',');
 const compact=matchMedia('(max-width: 600px)'),pendingReveals=new Set(),revealed=new WeakSet(),initialView=new WeakSet(),revealAnimations=new Map();
 let revealObserver=null;
 const inViewport=element=>{const rect=element.getBoundingClientRect();return rect.width>0&&rect.height>0&&rect.bottom>0&&rect.top<innerHeight};
 function cancelReveal(element){revealAnimations.get(element)?.cancel();revealAnimations.delete(element)}
 function reveal(element,delay){
  revealObserver?.unobserve(element);pendingReveals.delete(element);revealed.add(element);
  if(!element.isConnected||!enabled()||document.hidden||element.contains(document.activeElement)||element.closest(':target'))return;
  const first=initialView.has(element),distance=compact.matches?8:18;
  const frames=[{opacity:first?(element.matches('.hero-visual')?1:.7):.12},{opacity:1}];
  if(CSS.supports('translate','0 1px')){frames[0].translate='0 '+distance+'px';frames[1].translate='0 0'}
  try{
   const animation=element.animate(frames,{duration:first?340:(compact.matches?420:520),delay:first?Math.min(delay,120):delay,easing,fill:'backwards'});
   animation.id='site-scroll-reveal';revealAnimations.set(element,animation);
   animation.finished.then(()=>{if(revealAnimations.get(element)===animation){revealAnimations.delete(element);animation.cancel()}}).catch(()=>{});
  }catch{cancelReveal(element)}
 }
 function watchReveals(root,initial=false){
  if(!root||!revealObserver)return;
  for(const element of [...pendingReveals])if(!element.isConnected){revealObserver.unobserve(element);pendingReveals.delete(element)}
  for(const element of [...revealAnimations.keys()])if(!element.isConnected)cancelReveal(element);
  const candidates=[...(root.matches?.(revealSelector)?[root]:[]),...root.querySelectorAll(revealSelector)];
  for(const element of candidates){
   // Animate one level at a time, rather than fading a card and its contents twice.
   if(revealed.has(element)||pendingReveals.has(element)||element.parentElement?.closest(revealSelector))continue;
   if(!initial&&inViewport(element)){revealed.add(element);continue}
   if(initial&&inViewport(element))initialView.add(element);
   pendingReveals.add(element);revealObserver.observe(element);
  }
 }
 function startReveals(initial=false){
  if(!enabled()||typeof IntersectionObserver!=='function'||revealObserver)return;
  const observer=new IntersectionObserver(entries=>{
   if(revealObserver!==observer)return;
   const groups=new Map();
   for(const entry of entries){
    if(!entry.isIntersecting)continue;
    const element=entry.target,parent=element.parentElement,index=groups.get(parent)||0;
    groups.set(parent,index+1);reveal(element,Math.min(index*(compact.matches?40:65),compact.matches?100:180));
   }
  },{threshold:.02,rootMargin:'0px 0px -24px 0px'});
  revealObserver=observer;
  watchReveals(document.querySelector('main'),initial);watchReveals(document.querySelector('#footer'),initial);
 }
 function stopReveals(){
  revealObserver?.disconnect();revealObserver=null;pendingReveals.clear();
  for(const element of [...revealAnimations.keys()])cancelReveal(element);
 }
 document.addEventListener('focusin',event=>{
  for(const element of [...pendingReveals])if(element.contains(event.target)){revealObserver?.unobserve(element);pendingReveals.delete(element);revealed.add(element)}
  for(const element of [...revealAnimations.keys()])if(element.contains(event.target))cancelReveal(element);
 });
 addEventListener('beforeprint',stopReveals);
 addEventListener('afterprint',()=>startReveals());
 addEventListener('pagehide',stopReveals);
 addEventListener('pageshow',event=>{if(event.persisted)startReveals()});
 document.addEventListener('visibilitychange',()=>{if(document.hidden)for(const element of [...revealAnimations.keys()])cancelReveal(element)});
 document.querySelectorAll('#catalog-results,#price-results').forEach(host=>{
  new MutationObserver(()=>{
   animateContent(host,[{opacity:.65,transform:'translateY(3px)'},{opacity:1,transform:'translateY(0)'}]);
   // Visible filter results use the existing short fade; lower cards reveal on scroll.
   watchReveals(host);
  }).observe(host,{childList:true});
 });
 document.addEventListener('load',event=>{
  const image=event.target;
  if(image instanceof HTMLImageElement&&image.matches('.product-main-image img,#viewer-image'))animateContent(image,[{opacity:.65},{opacity:1}],220);
 },true);
 preference.addEventListener('change',()=>{
  if(!preference.matches){startReveals();return}
  stopReveals();
  for(const [details,state] of [...detailsAnimations])finishDetails(details,state);
  for(const [modal,state] of [...closingDialogs]){closingDialogs.delete(modal);state.animation.cancel();modal.classList.remove('motion-closing');modal.style.removeProperty('--backdrop-from');modal.close()}
  for(const animation of openingDialogs.values())animation.cancel();openingDialogs.clear();
  for(const animation of contentAnimations.values())animation.cancel();contentAnimations.clear();
 });
 startReveals(true);
})();
