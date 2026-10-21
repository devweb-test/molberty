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
 document.querySelectorAll('#catalog-results,#price-results').forEach(host=>{
  new MutationObserver(()=>animateContent(host,[{opacity:.65,transform:'translateY(3px)'},{opacity:1,transform:'translateY(0)'}])).observe(host,{childList:true});
 });
 document.addEventListener('load',event=>{
  const image=event.target;
  if(image instanceof HTMLImageElement&&image.matches('.product-main-image img,#viewer-image'))animateContent(image,[{opacity:.65},{opacity:1}],220);
 },true);
 preference.addEventListener('change',()=>{
  if(!preference.matches)return;
  for(const [details,state] of [...detailsAnimations])finishDetails(details,state);
  for(const [modal,state] of [...closingDialogs]){closingDialogs.delete(modal);state.animation.cancel();modal.classList.remove('motion-closing');modal.style.removeProperty('--backdrop-from');modal.close()}
  for(const animation of openingDialogs.values())animation.cancel();openingDialogs.clear();
  for(const animation of contentAnimations.values())animation.cancel();contentAnimations.clear();
 });
})();
