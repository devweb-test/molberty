/* Load on all frontend pages, including categories reached by /for_artist redirects.
 * Server emits <script id="molberty-legacy-products" type="application/json">
 * {"46139268-1498486363994":"https://current-site/product/molbert-bolshoy-stankovyy-buk/"}
 * </script>. Build the full map from exports/legacy_fragments.json using home_url().
 */
(() => {
  'use strict';
  const node=document.getElementById('molberty-legacy-products');
  if(!node||!location.hash)return;
  let fragment;
  try{fragment=decodeURIComponent(location.hash)}catch{return}
  const match=fragment.match(/^#!?\/?tproduct\/(\d+-\d+)(?:[/?&].*)?$/);
  if(!match)return;
  try{
    const target=JSON.parse(node.textContent)[match[1]];
    if(typeof target!=='string')return;
    const url=new URL(target,location.origin);
    if(url.origin!==location.origin||url.username||url.password)return;
    url.search=location.search;url.hash='';
    location.replace(url.href);
  }catch{/* Leave unknown fragments untouched. */}
})();
