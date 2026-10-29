'use strict';
// Native scrolling remains available when scripts are disabled.
(()=>{
 if(window.SITE_PRERENDER)return;
 function init(){
 const section=document.querySelector('#reviews'),track=section?.querySelector('#reviews-track');
 if(!track)return;
 const cards=[...track.querySelectorAll('.review-card')],controls=section.querySelector('.reviews-controls');
 const previous=section.querySelector('[data-reviews-prev]'),next=section.querySelector('[data-reviews-next]'),position=section.querySelector('.reviews-position');
 if(!cards.length||!controls||!previous||!next||!position)return;
 const preference=matchMedia('(prefers-reduced-motion: reduce)');
 let frame=0,announceTimer=0;
 const step=()=>cards.length>1?cards[1].offsetLeft-cards[0].offsetLeft:cards[0].getBoundingClientRect().width;
 function sync(announce=true){
  const maximum=Math.max(0,track.scrollWidth-track.clientWidth),offset=track.scrollLeft;
  previous.disabled=offset<=2;next.disabled=maximum-offset<=2;
  if(!announce)return;
  const distance=step(),gap=parseFloat(getComputedStyle(track).columnGap)||0;
  const visible=Math.max(1,Math.floor((track.clientWidth+gap+1)/distance));
  const first=Math.min(Math.max(0,cards.length-visible),Math.max(0,Math.round(offset/distance)));
  const last=Math.min(cards.length,first+visible);
  position.textContent=(first+1===last?String(last):`${first+1}–${last}`)+` из ${cards.length}`;
 }
 function move(direction){
  const distance=step(),maximum=track.scrollWidth-track.clientWidth;
  const target=Math.round(track.scrollLeft/distance)*distance+direction*distance;
  track.scrollTo({left:Math.max(0,Math.min(maximum,target)),behavior:preference.matches?'auto':'smooth'});
 }
 previous.addEventListener('click',()=>move(-1));next.addEventListener('click',()=>move(1));
 track.addEventListener('keydown',event=>{
  if(event.target!==track||event.altKey||event.ctrlKey||event.metaKey)return;
  if(event.key==='ArrowLeft'||event.key==='ArrowRight'){
   event.preventDefault();move(event.key==='ArrowRight'?1:-1);
  }else if(event.key==='Home'||event.key==='End'){
   event.preventDefault();track.scrollTo({left:event.key==='Home'?0:track.scrollWidth,behavior:preference.matches?'auto':'smooth'});
  }
 });
 track.addEventListener('scroll',()=>{
  if(!frame)frame=requestAnimationFrame(()=>{frame=0;sync(false)});
  clearTimeout(announceTimer);announceTimer=setTimeout(()=>sync(),120);
 },{passive:true});
 if('ResizeObserver' in window)new ResizeObserver(()=>sync()).observe(track);
 else addEventListener('resize',()=>sync());
 controls.hidden=false;sync();
 }
 if(document.readyState==='complete'||document.querySelector('#reviews-track'))init();
 else document.addEventListener('DOMContentLoaded',init,{once:true});
})();
