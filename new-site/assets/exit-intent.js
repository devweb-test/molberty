'use strict';

// One shared expiry survives navigation and is synchronised between tabs.
// A browser cannot render a custom dialog while actually closing the tab.
(()=>{
 const dialog=document.getElementById('request-dialog');
 if(window.SITE_PRERENDER||!dialog||typeof callbackRequest!=='function')return;
 const storageKey='molberty-exit-offer-until',cooldown=6*60*1000,armAt=performance.now()+8000;
 const mouseDevice=matchMedia('(any-hover: hover) and (any-pointer: fine)');
 let memoryUntil=0,pointerWasInside=false,active=false;
 function readUntil(){
  try{const value=Number(localStorage.getItem(storageKey));if(Number.isFinite(value)&&value>0)memoryUntil=Math.max(memoryUntil,value)}catch{}
  return memoryUntil;
 }
 function snooze(){
  memoryUntil=Date.now()+cooldown;
  try{localStorage.setItem(storageKey,String(memoryUntil))}catch{}
 }
 function finish(){if(!active)return;active=false;snooze()}
 function canShow(){
  return mouseDevice.matches&&pointerWasInside&&performance.now()>=armAt&&Date.now()>=readUntil()
   &&document.visibilityState==='visible'&&document.hasFocus()&&!document.querySelector('dialog[open]')
   &&!document.querySelector('.mobile-menu[aria-expanded="true"]')
   &&!document.activeElement?.matches('input,textarea,select,[contenteditable="true"]');
 }
 document.addEventListener('pointermove',event=>{
  if(event.pointerType==='mouse'&&event.clientX>0&&event.clientX<innerWidth&&event.clientY>0&&event.clientY<innerHeight)pointerWasInside=true;
 },{passive:true});
 document.addEventListener('pointerout',event=>{
  if(event.pointerType!=='mouse'||event.relatedTarget!==null)return;
  const atEdge=event.clientX<=0||event.clientY<=0||event.clientX>=innerWidth-1||event.clientY>=innerHeight-1;
  if(!atEdge||!canShow())return;
  active=true;
  // Reserve the interval now as well, so reloading or opening another tab
  // cannot immediately produce a second popup. Closing restarts six minutes.
  snooze();
  callbackRequest({capture:true});
 },{passive:true});
 dialog.addEventListener('close',finish);
 dialog.addEventListener('cancel',finish);
 new MutationObserver(()=>{
  // Track native closing immediately, even if the browser queues its close
  // event. A valid submission replaces the callback with the demo result.
  if(active&&(!dialog.open||!dialog.querySelector('[data-exit-offer]')))finish();
 }).observe(dialog,{attributes:true,attributeFilter:['open'],childList:true,subtree:true});
 addEventListener('pagehide',finish);
 addEventListener('storage',event=>{
  if(event.key!==storageKey)return;
  const until=Number(event.newValue);
  if(Number.isFinite(until)&&until>0)memoryUntil=Math.max(memoryUntil,until);
 });
 document.addEventListener('click',event=>{
  if(!event.target.closest('[data-clear]'))return;
  memoryUntil=0;
  try{localStorage.removeItem(storageKey)}catch{}
 });
})();
