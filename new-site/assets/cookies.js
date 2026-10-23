'use strict';
// Independent of catalogue data: show the notice without waiting for app.js.
(()=>{
 const key='molberty-cookie-consent',accepted='accepted-v1',notice=document.getElementById('cookie-notice');
 if(!notice)return;
 const remembered=()=>{try{return localStorage.getItem(key)===accepted}catch{return false}};
 const sync=()=>{notice.hidden=remembered()};
 notice.querySelector('[data-cookie-accept]').addEventListener('click',()=>{
  try{localStorage.setItem(key,accepted)}catch{}
  notice.hidden=true;
 });
 window.addEventListener('storage',event=>{if(event.key===key||event.key===null)sync()});
 window.siteCookies={reset(){try{localStorage.removeItem(key)}catch{}notice.hidden=false}};
 sync();
})();
