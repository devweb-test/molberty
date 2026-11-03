/* Manual, accessible carousel; the first slide is present before JavaScript. */
(()=>{
 'use strict';
 if(window.SITE_PRERENDER)return;
 const root=document.querySelector('[data-hero-carousel]');if(!root)return;
 const slides=[...root.querySelectorAll('[data-hero-slide]')],controls=root.querySelector('[data-hero-controls]'),dots=[...root.querySelectorAll('[data-hero-dot]')],status=root.querySelector('[data-hero-status]'),stage=root.querySelector('[data-hero-stage]'),reduced=matchMedia('(prefers-reduced-motion: reduce)');
 let index=0,request=0,start=null,suppressClick=false;
 controls.hidden=false;
 const announce=i=>{dots.forEach((dot,n)=>dot.setAttribute('aria-pressed',String(n===i)));status.textContent='Слайд '+(i+1)+' из '+slides.length+': '+slides[i].dataset.heroName;};
 async function choose(target){
  const next=(target+slides.length)%slides.length;if(next===index){request++;return}
  const ticket=++request,slide=slides[next],img=slide.querySelector('img');
  if(!img.complete||!img.naturalWidth){
   const probe=new Image();probe.src=img.currentSrc||img.src;
   try{await new Promise((resolve,reject)=>{if(probe.complete&&probe.naturalWidth)resolve();else{probe.onload=resolve;probe.onerror=reject}});if(probe.decode)await probe.decode().catch(()=>{});}catch{if(ticket===request)status.textContent='Не удалось загрузить изображение. Попробуйте ещё раз.';return;}
  }
  if(ticket!==request)return;
  slides[index].hidden=true;slide.hidden=false;img.loading='eager';index=next;announce(index);
  if(!reduced.matches&&slide.animate)slide.animate([{opacity:.35},{opacity:1}],{duration:240,easing:'ease-out'});
 }
 root.querySelector('[data-hero-prev]').addEventListener('click',()=>choose(index-1));
 root.querySelector('[data-hero-next]').addEventListener('click',()=>choose(index+1));
 dots.forEach((dot,n)=>dot.addEventListener('click',()=>choose(n)));
 root.addEventListener('keydown',event=>{if(event.key==='ArrowLeft'||event.key==='ArrowRight'){event.preventDefault();choose(index+(event.key==='ArrowLeft'?-1:1));}});
 stage.addEventListener('pointerdown',event=>{if(event.pointerType==='touch'||event.pointerType==='pen')start={x:event.clientX,y:event.clientY};},{passive:true});
 stage.addEventListener('pointercancel',()=>{start=null},{passive:true});
 stage.addEventListener('pointerup',event=>{if(!start)return;const dx=event.clientX-start.x,dy=event.clientY-start.y;start=null;if(Math.abs(dx)>50&&Math.abs(dx)>Math.abs(dy)*1.2){suppressClick=true;choose(index+(dx<0?1:-1));setTimeout(()=>{suppressClick=false},350)}},{passive:true});
 stage.addEventListener('click',event=>{if(suppressClick){event.preventDefault();event.stopPropagation();suppressClick=false}},true);
 announce(0);
})();
