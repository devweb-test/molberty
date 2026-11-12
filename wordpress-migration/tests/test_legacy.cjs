'use strict';
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict');
const source=fs.readFileSync(path.join(__dirname,'../integration/legacy-fragments.js'),'utf8');
function run(hash,map,search='?utm_source=test'){
 let target=null;
 const location={hash,search,origin:'https://staging.example.test',
   replace:url=>{target=url}};
 const document={getElementById:()=>({textContent:JSON.stringify(map)})};
 vm.runInNewContext(source,{location,document,URL});
 return target;
}
const map={'46139268-1498486363994':'https://staging.example.test/product/molbert-bolshoy-stankovyy-buk/'};
for(const hash of ['#!/tproduct/46139268-1498486363994','#/tproduct/46139268-1498486363994']){
 assert.equal(run(hash,map),'https://staging.example.test/product/molbert-bolshoy-stankovyy-buk/?utm_source=test');
}
assert.equal(run('#!/tproduct/111-222',map),null);
assert.equal(run('#section',map),null);
assert.equal(run('#%GG',map),null);
assert.equal(run('#!/tproduct/46139268-1498486363994',{'46139268-1498486363994':'https://other.example/'}),null);
assert.equal(run('#!/tproduct/46139268-1498486363994',{'46139268-1498486363994':'https://user:pass@staging.example.test/'}),null);
console.log(JSON.stringify({passed:true,cases:7,externalRedirectBlocked:true}));
