'use strict';
// Loaded only on the interior category. Measurements stay in memory until passed to a request.
(()=>{
 if(window.SITE_PRERENDER||!document.querySelector('#category[data-id="molberty-dekorativnye"]'))return;
 const fields=[
  {title:'Габариты картины',help:'Измерьте работу вместе с рамой. Все размеры укажите в сантиметрах.',items:[['width','Ширина, см','60'],['height','Высота, см','80']]},
  {title:'Высота экспозиции',help:'Укажите расстояние от пола до нижнего края картины, а не до её центра.',items:[['exposure','Нижний край картины от пола, см','70']]},
  {title:'Вес картины и глубина рамы',help:'Вес укажите вместе с рамой и стеклом. Глубину измерьте в самом выступающем месте рамы.',items:[['weight','Вес с рамой, кг','5'],['depth','Глубина рамы, см','4']]}
 ];
 // Format, tray depth and total height are from the original product descriptions.
 // No load rating or tray-height range is assumed for these two models.
 const rules=[
  {id:'molbert-ampir',width:80,height:100,depth:10,easelHeight:185},
  {id:'molbert-eksklyuziv',width:95,height:110,depth:7.5,easelHeight:185}
 ];
 let step=0,values={},selected=[];
 const number=n=>Number(n).toLocaleString('ru-RU',{maximumFractionDigits:1});
 function summary(){return [['Габариты с рамой',`${number(values.width)} × ${number(values.height)} см`],['Нижний край от пола',`${number(values.exposure)} см`],['Вес с рамой',`${number(values.weight)} кг`],['Глубина рамы',`${number(values.depth)} см`]];}
 function requestText(){return 'Подбор интерьерного мольберта для картины.\n'+summary().map(([key,value])=>key+': '+value).join('\n')+'\n'+(selected.length?'Предварительно рассматриваем: '+selected.map(r=>productById(r.id).name).join(', ')+'.':'Нужно согласовать модель или изготовление по размерам.')+'\nПрошу подтвердить высоту размещения, допустимую нагрузку и крепление рамы.';}
 function showStep(){
  const question=fields[step];
  openDialog(`<div class="interior-quiz">${eyebrow(`Шаг ${step+1} из 3`,'ДЛЯ ВАШЕЙ КАРТИНЫ')}<div class="quiz-progress" aria-hidden="true"><span style="width:${(step+1)/3*100}%"></span></div><h2 id="interior-question-title">${question.title}</h2><p id="interior-question-help">${question.help}</p><form id="request-form" class="interior-quiz-form" aria-labelledby="interior-question-title" aria-describedby="interior-question-help"><div class="interior-fields">${question.items.map(([key,label,example])=>`<label>${label}<input name="${key}" type="number" inputmode="decimal" min="${key==='exposure'?'0':'0.1'}" max="1000" step="0.1" required value="${esc(values[key]??'')}" placeholder="Например, ${example}"></label>`).join('')}</div>${step===2?formConsent():''}<div class="dialog-actions">${step?'<button class="text-link" type="button" data-interior-back>← Назад</button>':''}<button class="btn" type="submit">${step===2?'Показать варианты':'Далее'} ${icon('arrow')}</button></div></form></div>`);
  const form=document.querySelector('.interior-quiz-form');
  form.addEventListener('input',event=>{if(question.items.some(([key])=>key===event.target.name))values[event.target.name]=event.target.value;});
  form.addEventListener('submit',event=>{
   event.preventDefault();if(!form.reportValidity())return;
   for(const [key] of question.items){const input=form.elements.namedItem(key),value=input.valueAsNumber;if(!Number.isFinite(value))return;values[key]=value;}
   if(step===2)showResult();else{step++;showStep();}
  });
  form.querySelector('input').focus();
 }
 function showResult(){
  selected=rules.filter(rule=>productById(rule.id)&&values.width<=rule.width&&values.height<=rule.height&&values.depth<=rule.depth&&values.exposure<rule.easelHeight);
  openDialog(`<div class="interior-quiz">${eyebrow('Ваши параметры','ПРЕДВАРИТЕЛЬНЫЙ ПОДБОР')}<h2>Мольберт для Вашей картины.</h2><dl class="interior-quiz-summary">${summary().map(([key,value])=>`<div><dt>${key}</dt><dd>${value}</dd></div>`).join('')}</dl><p>${selected.length?'Эти модели можно рассмотреть по габаритам работы и глубине рамы.':'Для этих параметров нужно отдельно согласовать конструкцию и размеры мольберта.'}</p>${selected.length?`<div class="interior-quiz-models">${selected.map(rule=>{const p=productById(rule.id);return `<a class="interior-quiz-model" href="${url('product/'+p.id+'/')}"><img src="${asset(p.image)}" alt="${esc(p.name)}" title="${esc(p.name)}" width="75" height="95" loading="lazy"><span><strong>${esc(p.name)}</strong><small>Формат до ${number(rule.width)} × ${number(rule.height)} см, глубина лотка ${number(rule.depth)} см</small><span class="interior-quiz-price">${p.listingFrom?'От ':''}${money(p.listingPrice)}</span></span></a>`;}).join('')}</div>`:''}<p class="interior-quiz-note">Высоту установки, допустимую нагрузку для работы весом ${number(values.weight)} кг и способ фиксации рамы подтвердим перед заказом.</p><div class="dialog-actions"><button class="btn" type="button" data-interior-request>Согласовать подбор ${icon('arrow')}</button><button class="text-link" type="button" data-interior-edit>Изменить параметры</button></div></div>`);
 }
 document.querySelectorAll('[data-interior-quiz]').forEach(button=>button.disabled=false);
 document.addEventListener('click',event=>{
  const target=event.target.closest('button');if(!target)return;
  if(target.matches('[data-interior-quiz]')){step=0;values={};selected=[];showStep();}
  if(target.matches('[data-interior-back]')){step=Math.max(0,step-1);showStep();}
  if(target.matches('[data-interior-edit]')){step=0;showStep();}
  if(target.matches('[data-interior-request]'))request(requestText());
 });
})();
