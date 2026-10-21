const test = require('node:test');
const assert = require('node:assert/strict');
const {reconcileDraft,makeSave} = require('../Pengu Loader/plugins/SEXO2-SwiftplayPins/index.js');
const a={championId:234,pin:{skinId:234001},skins:[{skinId:234001},{skinId:234002}]};
const b={championId:555,pin:null,skins:[{skinId:555001}]};
test('reorder preserves unsaved choice by champion',()=>assert.deepEqual(reconcileDraft({234:234002,555:null},[b,a],false),{234:234002,555:null}));
test('replacement drops departed champion',()=>assert.deepEqual(reconcileDraft({999:999001},[a,b],false),{234:234001,555:null}));
test('saved ack refreshes draft',()=>assert.deepEqual(reconcileDraft({234:234002},[a,b],true),{234:234001,555:null}));
test('removed choice stays removed across polling',()=>assert.equal(reconcileDraft({234:null},[a],false)[234],null));
test('missing catalog skin cannot stay in draft',()=>assert.equal(reconcileDraft({234:234999},[a],false)[234],null));
test('save uses current slot order and explicit removals',()=>assert.deepEqual(makeSave({championIds:[555,234]},{234:234002,555:null}),{type:'swiftplay-pins-save',championIds:[555,234],selections:[{championId:555,skinId:null},{championId:234,skinId:234002}]}));

const vm = require('node:vm');
const fs = require('node:fs');
const pluginSource=fs.readFileSync(require('node:path').join(__dirname,'../Pengu Loader/plugins/SEXO2-SwiftplayPins/index.js'),'utf8');
function harness(loading, legacyModule=false) {
  let readyListener=null, timers=0;
  const nodes=[];
  const body={appendChild(n){nodes.push(n);n.isConnected=true}};
  const head={appendChild(n){nodes.push(n)}};
  const document={readyState:loading?'loading':'complete',body:loading?null:body,head:loading?null:head,
    createElement(){return {style:{},replaceChildren(){},addEventListener(){}}},
    addEventListener(event,fn){if(event==='DOMContentLoaded')readyListener=fn}};
  const context={document,window:{addEventListener(){}},Date,Math,console,setInterval(){timers++},setTimeout(){}};
  if(legacyModule)context.module={exports:{}};
  vm.runInNewContext(pluginSource,context);
  return {context,nodes,get timers(){return timers},ready(){document.body=body;document.head=head;document.readyState='interactive';readyListener()}};
}
test('client DOM is not touched before DOMContentLoaded',()=>{
  const h=harness(true);
  assert.equal(h.nodes.length,0);assert.equal(h.timers,0);
  h.ready();assert.equal(h.nodes.length,2);assert.equal(h.timers,1);
});
test('already-loaded client initializes immediately',()=>{
  const h=harness(false);assert.equal(h.nodes.length,2);assert.equal(h.timers,1);
});
test('browser global module cannot suppress plugin initialization',()=>{
  const h=harness(false,true);assert.equal(h.nodes.length,2);assert.equal(h.timers,1);
});
