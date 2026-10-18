const {chromium}=require('../ui-test-runtime/node_modules/playwright');
const path=require('node:path'),assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({headless:true});
 try {
 const page=await browser.newPage({viewport:{width:1280,height:720}});
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.setContent('<html><head></head><body></body></html>');
 await page.evaluate(()=>{
  window.callbacks={};window.pendingRequest=null;
  window.sample={type:'swiftplay-pins-state',active:true,editable:true,championIds:[1,2],champions:[1,2].map(id=>({championId:id,name:'Campeão '+id,pin:null,skins:Array.from({length:80},(_,i)=>({skinId:id*1000+i,name:'Skin '+String(i).padStart(2,'0')}))}))};
  window.__roseBridge={ready:true,subscribe(t,cb){window.callbacks[t]=cb;},send(p){window.pendingRequest=p;}};
  window.reply=()=>{const p=window.pendingRequest;window.pendingRequest=null;if(p)window.callbacks['swiftplay-pins-state']({...structuredClone(window.sample),requestId:p.requestId});};
 });
 await page.addScriptTag({path:path.resolve('Pengu Loader/plugins/SEXO2-SwiftplayPins/index.js')});
 await page.evaluate(()=>window.reply());
 await page.getByRole('button',{name:'SEXO2 · Fixar skins',exact:true}).click();
 await page.getByRole('button',{name:'Escolher',exact:true}).first().click();
 await page.locator('.rsp-grid').evaluate(e=>{e.scrollTop=e.scrollHeight;e.dataset.original='yes';});
 const bottom=await page.locator('.rsp-grid').evaluate(e=>e.scrollTop);assert.ok(bottom>0);
 await page.waitForTimeout(1650);await page.evaluate(()=>window.reply());
 assert.equal(await page.locator('.rsp-grid').evaluate(e=>e.scrollTop),bottom);
 assert.equal(await page.locator('.rsp-grid').getAttribute('data-original'),'yes');
 // A genuine update must preserve scroll even when focus is outside the picker.
 await page.evaluate(()=>{document.activeElement.blur();window.sample.champions[0].status={state:'ready',message:'Pronto'};});
 await page.waitForTimeout(1550);await page.evaluate(()=>window.reply());
 assert.equal(await page.locator('.rsp-grid').evaluate(e=>e.scrollTop),bottom);
 await page.locator('.rsp-search').fill('Skin 7');
 await page.evaluate(()=>{window.sample.editable=false;});
 await page.waitForTimeout(1550);await page.evaluate(()=>window.reply());
 assert.equal(await page.locator('.rsp-search').inputValue(),'Skin 7');
 assert.equal(await page.locator('.rsp-tile:disabled').count(),10);
 await page.evaluate(()=>{window.sample.editable=true;window.sample.championIds=[2,3];window.sample.champions=window.sample.champions.slice(1);});
 await page.waitForTimeout(1550);await page.evaluate(()=>window.reply());
 assert.equal(await page.locator('.rsp-search').count(),0);
 await page.getByRole('button',{name:'Escolher',exact:true}).first().click();
 assert.equal(await page.locator('.rsp-search').inputValue(),'');
 assert.equal(await page.locator('.rsp-grid').evaluate(e=>e.scrollTop),0);
 assert.deepEqual(errors,[]);
 console.log('PASS: unchanged poll preserves DOM, changed status preserves scroll, search/focus retained, controls disable, changed champions reset picker.');
 } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
