// Browser stress of the Equipe tab (D-153): random full and partial states in the real plugin;
// no script error, no scrollbar, no broken text, no row wider or taller than its place.
// Not run in CI (needs the ui-test-runtime): node tests/browser_equipe_stress.cjs
const {chromium}=require('../ui-test-runtime/node_modules/playwright');
const fs=require('node:fs'),assert=require('node:assert/strict');
const root='Pengu Loader/plugins/';
let seed=20261022;const rnd=()=>((seed=(seed*1664525+1013904223)>>>0)/2**32);const pick=xs=>xs[Math.floor(rnd()*xs.length)];
const some=(good,bad=null,p=0.7)=>rnd()<p?good():bad;
const NAMES=['Fulano','Beltrano de Tal','Ciclano com um nome absurdamente comprido para testar o corte','Ünïcödé 日本語','<img src=x onerror=1>','A B','','Zé'];
const player=(cell)=>({cellId:cell,position:pick(['top','jungle','middle','bottom','support','']),name:pick(NAMES),tag:'BR1',
 championId:pick([0,86,103,266,64,22]),
 elo:some(()=>({queue:pick(['RANKED_SOLO_5x5','RANKED_FLEX_SR']),tier:pick(['IRON','GOLD','PLATINUM','MASTER','CHALLENGER']),division:pick(['I','II','III','IV',null]),leaguePoints:some(()=>Math.floor(rnd()*1000),null),wins:some(()=>Math.floor(rnd()*3000),null),losses:some(()=>Math.floor(rnd()*3000),null)})),
 form:some(()=>{const g=1+Math.floor(rnd()*20);return{games:g,wins:Math.floor(rnd()*(g+1)),recent:Array.from({length:Math.min(g,5)},()=>rnd()<.5),role:some(()=>pick(['top','jungle','middle','bottom','support'])),top:[{id:22,games:9},{id:86,games:3},{id:202,games:1}],withChampion:some(()=>{const n=1+Math.floor(rnd()*30);return{games:n,wins:Math.floor(rnd()*(n+1))};},null,.5)};},null,.65),
 canOpen:rnd()<.6});
(async()=>{
 const b=await chromium.launch({headless:true});let worst={h:0};
 try{
  for(let i=0;i<150;i++){
   const p=await b.newPage({viewport:{width:1280,height:720}});const errs=[];p.on('pageerror',e=>errs.push(String(e)));
   await p.setContent('<html><body style="background:#0d0e10;margin:0"><div class="champion-select"><div class="bottom-right-buttons"></div></div></body></html>');
   await p.evaluate(()=>{const n=[{id:86,name:'Garen'},{id:103,name:'Ahri'},{id:266,name:'Aatrox'},{id:64,name:'Lee Sin'},{id:22,name:'Ashe'},{id:202,name:'Jhin'}];window.fetch=u=>Promise.resolve(String(u).includes('champion-summary')?{ok:true,json:()=>Promise.resolve(n)}:{ok:false,json:()=>Promise.resolve(null)});});
   const team=Array.from({length:1+Math.floor(rnd()*5)},(_,k)=>player(k));
   await p.evaluate(st=>{window.handlers={};window.__sexo2Bridge={ready:true,subscribe(t,cb){window.handlers[t]=cb;},send(m){window.sent.push(m);}};window.sent=[];window.__st=st;},{type:'assistant-state',supported:true,championId:103,lane:'middle',mode:'ranked',enemies:[],opponentId:null,error:null,runes:{general:[],matchup:[],keystone:[]},items:{},favorite:{},ranked:{available:true,enemies:[],team}});
   for(const f of ['SEXO2-Style','SEXO2-Assistant']) await p.addScriptTag({content:fs.readFileSync(root+f+'/index.js','utf8')});
   await p.waitForFunction(()=>window.handlers&&window.handlers['assistant-state'],null,{timeout:3000}); // the panel connects to the bridge by itself
   await p.evaluate(()=>{window.handlers['assistant-state'](window.__st);window.__sexo2Assistant.toggle(document.querySelector('.bottom-right-buttons'));});
   await p.waitForTimeout(80);
   await p.evaluate(()=>{window.handlers['assistant-state'](window.__st);});
   const tab=await p.$('#sexo2-assistant [data-tab=team]');assert.ok(tab,'the Equipe tab is there');await tab.click();await p.waitForTimeout(60);
   const m=await p.evaluate(()=>{const body=document.querySelector('#sexo2-assistant .asst-body');const rows=[...document.querySelectorAll('#sexo2-assistant .rank-row')];
    return{scroll:body.scrollHeight-body.clientHeight,rows:rows.length,maxH:Math.max(...rows.map(r=>r.getBoundingClientRect().height)),wide:rows.some(r=>r.scrollWidth>r.clientWidth+1),text:rows.map(r=>r.innerText).join('\n'),injected:!!document.querySelector('#sexo2-assistant img[onerror]')};});
   assert.deepEqual(errs,[],'no script error');assert.ok(m.scroll<=1,'no scrollbar: '+m.scroll);assert.equal(m.rows,team.length);assert.ok(m.maxH<=90,'row height '+m.maxH);
   assert.ok(!m.wide,'no horizontal overflow');assert.ok(!/undefined|NaN|\bnull\b|\[object/.test(m.text),'broken text: '+m.text);assert.ok(!m.injected,'names are escaped');
   const buttons=await p.$$('#sexo2-assistant .rank-row .open');
   assert.equal(buttons.length,team.filter(x=>x.canOpen).length,'a button exactly where the service allows it');
   if(buttons.length){await buttons[0].click();const sent=await p.evaluate(()=>window.sent.filter(x=>x.type==='assistant-open-profile'));
    assert.deepEqual(sent,[{type:'assistant-open-profile',cellId:team.find(x=>x.canOpen).cellId}],'the button asks for that player only');}
   worst.h=Math.max(worst.h,m.maxH);await p.close();
  }
  console.log('Equipe browser stress: 150 random states, no error, no scroll, tallest row',worst.h,'px');
 }finally{await b.close();}
})().catch(e=>{console.error(e);process.exit(1);});
