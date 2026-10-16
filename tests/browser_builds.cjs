// Isolated browser + synthetic bridge. Does not connect to the League client.
const {chromium}=require('../ui-test-runtime/node_modules/playwright');
const assert=require('node:assert/strict');
const {execFileSync}=require('node:child_process');
const path=require('node:path');
const fixture=JSON.parse(execFileSync('python',['-c',`
import json
from tests.test_build_workflow import service,query
s,lcu,t=service();context=s.context();result=query(s)
from sexo2.services.loadouts import GameCatalog
catalog=GameCatalog(lcu);result['itemNames']=catalog.names('items');result['runeNames']=catalog.names('perks')
print(json.dumps({'context':context,'result':result}));s.close()
`],{encoding:'utf8'}));
(async()=>{
 const browser=await chromium.launch({headless:true,...(process.env.SEXO2_TEST_BROWSER_PATH?{executablePath:process.env.SEXO2_TEST_BROWSER_PATH}:{})});
 try{
  const page=await browser.newPage({viewport:{width:1280,height:720}}),errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  await page.setContent('<html><head><style>body{margin:0;background:#09141b;color:#c8aa6e;font:16px Arial}.champion-select{height:100vh;background:linear-gradient(#172b37,#08121a)}.team{position:absolute;top:90px;width:190px;padding:15px}.enemy{right:0}.timer{text-align:center;padding:20px}.actions{position:absolute;bottom:15px;left:40%;padding:20px;border:1px solid #c8aa6e}</style></head><body><div id="home">Cliente simulado · início</div></body></html>');
  await page.evaluate(sample=>{
   window.sample=sample;window.handlers={};window.sent=[];window.holdQueries=false;window.pending=[];window.queryError=false;
   window.emit=(type,message)=>(window.handlers[type]||[]).forEach(fn=>fn(message));
   window.__roseBridge={ready:true,subscribe(type,fn){(window.handlers[type]??=[]).push(fn);},onReady(fn){fn();},send(message){
    window.sent.push(message);
    if(message.type==='sexo2-build-context')setTimeout(()=>window.emit('sexo2-build-context-data',{requestId:message.requestId,context:structuredClone(window.sample.context)}),0);
    if(message.type==='sexo2-build-query'){
     const response={requestId:message.requestId,result:{...structuredClone(window.sample.result),revision:message.revision}};
     if(window.holdQueries)window.pending.push(response);
     else if(window.queryError)setTimeout(()=>window.emit('sexo2-build-error',{requestId:message.requestId,error:'Fonte temporariamente indisponível.'}),0);
     else setTimeout(()=>window.emit('sexo2-build-data',response),0);
    }
    if(message.type==='sexo2-build-import')setTimeout(()=>window.emit('sexo2-build-imported',{requestId:message.requestId,result:{verified:true,message:'Importação confirmada no cliente simulado.'}}),0);
   }};
  },fixture);
  await page.addScriptTag({path:path.resolve('Pengu Loader/plugins/SEXO2-Builds/index.js')});
  assert.equal(await page.locator('#sexo2-builds').count(),0,'must not mount on the normal screen');
  await page.evaluate(()=>{
   document.body.innerHTML='<main class="champion-select"><div class="timer">SELEÇÃO SIMULADA · 00:30</div><aside class="team">Seu time<br>Ahri</aside><aside class="team enemy">Adversários<br>Annie<br>Ryze</aside><button class="actions">Confirmar campeão</button></main>';
  });
  await page.getByRole('button',{name:'Abrir builds do SEXO2'}).waitFor();
  assert.equal(await page.evaluate(()=>window.sent.filter(x=>x.type==='sexo2-build-query').length),0,'closed panel must not scrape');
  await page.getByRole('button',{name:'Abrir builds do SEXO2'}).click();
  await page.getByRole('button',{name:'Importar runas',exact:true}).waitFor();
  await page.waitForFunction(()=>!document.querySelector('#sexo2-builds button')?.disabled&&document.querySelector('#sexo2-builds')?.textContent.includes('Sugestões prontas'));
  assert.equal(await page.getByRole('combobox',{name:'Adversário',exact:true}).isDisabled(),true);
  assert.equal(await page.getByRole('combobox',{name:'Sugestão',exact:true}).locator('option').count(),2);
  await page.getByRole('button',{name:'Importar runas',exact:true}).click();
  await page.getByText('Importação confirmada no cliente simulado.',{exact:true}).waitFor();
  assert.equal(await page.evaluate(()=>window.sent.filter(x=>x.type==='sexo2-build-import').at(-1).entryId),'wr');
  await page.screenshot({path:'/tmp/sexo2-builds-1280x720.png'});
  // A late response from an older revision cannot restore obsolete recommendations.
  await page.evaluate(()=>{window.holdQueries=true;});
  await page.getByRole('button',{name:'Consultar',exact:true}).click();
  await page.waitForFunction(()=>window.pending.length===1);
  await page.evaluate(()=>{window.sample.context.revision='next-draft';window.sample.context.finalization=true;});
  await page.waitForFunction(()=>window.pending.length===2);
  await page.evaluate(()=>window.emit('sexo2-build-data',window.pending.shift()));
  assert.equal(await page.getByRole('button',{name:'Importar runas',exact:true}).isDisabled(),true);
  await page.evaluate(()=>{window.emit('sexo2-build-data',window.pending.shift());window.holdQueries=false;});
  await page.waitForFunction(()=>!Array.from(document.querySelectorAll('#sexo2-builds button')).find(b=>b.textContent==='Importar runas').disabled);
  assert.equal(await page.getByRole('combobox',{name:'Adversário',exact:true}).isEnabled(),true);
  // Source failure does not become an automatic retry loop on every context poll.
  await page.evaluate(()=>window.queryError=true);
  await page.getByRole('button',{name:'Consultar',exact:true}).click();
  await page.getByText('Fonte temporariamente indisponível.',{exact:true}).waitFor();
  const count=await page.evaluate(()=>window.sent.filter(x=>x.type==='sexo2-build-query').length);
  await page.waitForTimeout(2100);
  assert.equal(await page.evaluate(()=>window.sent.filter(x=>x.type==='sexo2-build-query').length),count);
  for(const [width,height]of [[1024,576],[1280,720]]){
   await page.setViewportSize({width,height});
   const box=await page.locator('.s2-build-panel').boundingBox();
   assert.ok(box.x>=0&&box.y>=0&&box.x+box.width<=width&&box.y+box.height<=height);
   for(const selector of ['.team:not(.enemy)','.team.enemy','.actions']){const other=await page.locator(selector).boundingBox();assert.ok(box.x+box.width<=other.x||other.x+other.width<=box.x||box.y+box.height<=other.y||other.y+other.height<=box.y,'panel covers a simulated roster or confirmation button');}
  }
  await page.evaluate(()=>{window.sample.context.phase='InProgress';window.emit('phase-change',{phase:'InProgress'});});
  assert.equal(await page.locator('#sexo2-builds').count(),0);
  const contextCount=await page.evaluate(()=>window.sent.filter(x=>x.type==='sexo2-build-context').length);
  await page.waitForTimeout(2100);
  assert.equal(await page.evaluate(()=>window.sent.filter(x=>x.type==='sexo2-build-context').length),contextCount,'context polling must pause in game');
  assert.deepEqual(errors,[]);
  console.log('Build panel: isolated mount, explicit import, stale replies, source errors, 2 viewports and phase exit passed.');
 }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exit(1);});
