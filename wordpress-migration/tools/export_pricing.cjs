#!/usr/bin/env node
'use strict';
// Produce price fixtures from the accepted JS implementation, without executing its UI.
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const kit=path.resolve(__dirname,'..');
const candidates=[process.argv[2],path.join(kit,'reference/new-site'),path.join(kit,'../new-site')].filter(Boolean);
const source=candidates.find(dir=>fs.existsSync(path.join(dir,'data/catalog.json')));
if(!source)throw Error('Pass /path/to/new-site as the first argument.');
const data=JSON.parse(fs.readFileSync(path.join(source,'data/catalog.json'),'utf8'));
const app=fs.readFileSync(path.join(source,'assets/app.js'),'utf8');
const functions=app.slice(app.indexOf('function optionValues('),app.indexOf('function migrateSelection('));
const context={};vm.createContext(context);vm.runInContext(functions,context);
const fixtures=[];
for(const p of data.products){
 const tiers=p.wholesaleOnly?['wholesale']:p.wholesalePrice!==null?['retail','wholesale']:['retail'];
 for(const tier of tiers){
  context.p=p;
  const state=vm.runInContext('defaultState(p)',context);state.tier=tier;context.state=state;
  const options=vm.runInContext('activeOptions(p,state)',context);
  const combinations=[];
  function enumerate(index,indices){
   if(index===options.length){combinations.push([...indices]);return;}
   const option=options[index];context.option=option;
   for(const value of vm.runInContext('optionValues(option)',context)){
    const next=[...indices];next[option.index]=value.index;enumerate(index+1,next);
   }
  }
  enumerate(0,state.indices);
  for(const indices of combinations){
   context.state={...state,indices};
   const unit=vm.runInContext('unitPrice(p,state)',context);
   const minimum=vm.runInContext('minQuantity(p,state)',context);
   const from=vm.runInContext('Boolean(isFrom(p,state))',context);
   if(!Number.isFinite(unit)||unit<0)throw Error('Invalid price '+p.id);
   fixtures.push({productId:p.id,tier,indices,unitPrice:unit,minQuantity:minimum,
     quantity:minimum,total:unit*minimum,displayFrom:from});
  }
 }
}
fs.mkdirSync(path.join(kit,'exports'),{recursive:true});
fs.writeFileSync(path.join(kit,'exports/pricing-fixtures.json'),JSON.stringify(fixtures,null,2)+'\n');
console.log(JSON.stringify({products:data.products.length,priceFixtures:fixtures.length}));
