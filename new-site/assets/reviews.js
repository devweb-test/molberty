'use strict';
// Native scrolling remains available when scripts are disabled.
(()=>{
 if(window.SITE_PRERENDER)return;
 function init(){
 const section=document.querySelector('#reviews'),track=section?.querySelector('#reviews-track');
 if(!track)return;
 const cards=[...track.querySelectorAll('.review-card')],controls=section.querySelector('.reviews-controls');
 const previous=section.querySelector('[data-reviews-prev]'),next=section.querySelector('[data-reviews-next]');
 if(!cards.length||!controls||!previous||!next)return;
 const preference=matchMedia('(prefers-reduced-motion: reduce)');
 let frame=0;
 const step=()=>cards.length>1?cards[1].offsetLeft-cards[0].offsetLeft:cards[0].getBoundingClientRect().width;
 function sync(){
  const maximum=Math.max(0,track.scrollWidth-track.clientWidth),offset=track.scrollLeft;
  previous.disabled=offset<=2;next.disabled=maximum-offset<=2;
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
  if(!frame)frame=requestAnimationFrame(()=>{frame=0;sync()});
 },{passive:true});
 if('ResizeObserver' in window)new ResizeObserver(()=>sync()).observe(track);
 else addEventListener('resize',()=>sync());
 controls.hidden=false;sync();
 }
 if(document.readyState==='complete'||document.querySelector('#reviews-track'))init();
 else document.addEventListener('DOMContentLoaded',init,{once:true});
})();
