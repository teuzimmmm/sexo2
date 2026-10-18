const {chromium}=require('../ui-test-runtime/node_modules/playwright');
const path=require('node:path'),fs=require('node:fs'),assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({headless:true});
 try{
 const page=await browser.newPage({viewport:{width:1280,height:720}}),errors=[];
 page.on('pageerror',e=>errors.push(e.message));
 await page.route('http://127.0.0.1:*/asset/golden_rose.png',route=>route.fulfill({contentType:'image/png',body:fs.readFileSync('assets/golden_rose.png')}));
 await page.setContent(`<html><head><style>.right-nav-menu{position:absolute;right:120px;top:18px;display:flex;gap:20px}.menu-item-icon{width:20px;height:20px;background:#cdbe91}body{background:#09141b;margin:0}</style></head><body><div class="right-nav-menu"><lol-uikit-navigation-item class="menu_item_Golden Rose"><div class="menu-item-icon-wrapper"><div class="menu-item-icon"></div></div></lol-uikit-navigation-item></div><div class="lol-social-actions-bar"></div><div class="parties-game-info-panel"></div><div class="skin-selection-item" id="native-skin">Skin do cliente</div></body></html>`);
 await page.evaluate(()=>{
  window.sent=[];window.handlers={};window.fakePhase='Lobby';window.confirm=()=>true;
  window.rcp={postInit(){}};
  document.querySelector('.menu-item-icon').style.webkitMaskImage='url(http://127.0.0.1:50000/asset/golden_rose.png)';
  document.querySelector('.menu-item-icon').style.webkitMaskSize='contain';
  window.emit=(type,data)=>{for(const cb of window.handlers[type]||[])cb(data);};
  window.fetch=async()=>({ok:true,json:async()=>({port:50000}),text:async()=>'{"port":50000}'});
  window.sample={type:'friends-state',phase:'Lobby',editable:true,automatic:'favorites',favorites:{11:[11001]},profiles:{Arcane:{11:{skinId:11001,name:'Arcane'}}},activeProfile:null,excluded:[],themes:['Qualquer','Arcane'],lotteryOptin:false,message:'',champions:[{championId:11,name:'Master Yi',selectedSkinId:11001,skins:Array.from({length:35},(_,i)=>({skinId:11000+i,name:'Skin '+i,available:true}))}],members:[],readiness:{localReady:true,groupReady:false,title:'Arquivos preparados',checks:[]},room:{status:'idle',connected:false}};
  window.__roseBridge={ready:true,port:50000,subscribe(type,cb){(window.handlers[type]??=[]).push(cb);},onReady(cb){cb();},waitUntilReady(){return Promise.resolve();},send(p){window.sent.push(p);if(p.type==='friends-request'){if(p.action==='room-host')window.sample.room={status:'hosting',hosting:true,connected:true,link:'https://example.test/#rose=TESTTOKEN',message:'Sala disponível.'};if(p.action==='room-join')window.sample.room.message='Reconectando…';const data=structuredClone(window.sample);data.requestId=p.requestId;data.phase=window.fakePhase;setTimeout(()=>window.emit('friends-state',data),0);}else if(p.type==='settings-request'){setTimeout(()=>window.emit('settings-data',{type:'settings-data',requestId:p.requestId,threshold:.5,monitorAutoResumeTimeout:60,autostart:false,hideEmptyCategories:false,gamePath:'C:/Riot/Game',version:'1.4.7'}),0);}else if(p.type==='settings-save'){setTimeout(()=>window.emit('settings-saved',{type:'settings-saved',requestId:p.requestId,success:p.gamePath!=='invalid',error:p.gamePath==='invalid'?'Pasta inválida':undefined,settings:p}),0);}else if(p.type==='swiftplay-pins-request'){setTimeout(()=>window.emit('swiftplay-pins-state',{type:'swiftplay-pins-state',requestId:p.requestId,active:true,editable:true,championIds:[11],champions:[{championId:11,name:'Master Yi',pin:null,skins:window.sample.champions[0].skins}]}),0);}}};
  class FakeSocket{static OPEN=1;constructor(){this.readyState=1;setTimeout(()=>this.onopen?.(),0);}send(text){window.sent.push(JSON.parse(text));}close(){this.readyState=3;}}
  window.WebSocket=FakeSocket;
 });
 for(const name of ['SEXO2-Amigos','SEXO2-SwiftplayPins','SEXO2-PartyMode','SEXO2-SettingsPanel','SEXO2-ModLibrary','SEXO2-Settings','SEXO2-Hub','SEXO2-UI'])await page.addScriptTag({path:path.resolve('Pengu Loader/plugins',name,'index.js')});
 await page.waitForTimeout(200);
 await page.locator('.menu_item_Golden').last().click();
 await page.getByRole('button',{name:'Criar sala',exact:true}).waitFor();
 assert.equal(await page.locator('#rose-hub>header .hub-brand').textContent(),'SEXO2');
 assert.deepEqual(await page.locator('#rose-hub>nav button').allTextContents(),['Sala','Favoritas','Configurações','Suporte','Swiftplay']);
 assert.equal(await page.locator('#rose-hub').evaluate(e=>getComputedStyle(e).borderRadius),'0px');
 await page.evaluate(()=>window.__roseBridge.ready=false);
 await page.getByText('Reconectando ao SEXO2…',{exact:true}).waitFor();
 assert.equal(await page.locator('#rose-hub').getByText(/O Rose/).count(),0);
 await page.evaluate(()=>window.__roseBridge.ready=true);
 await page.waitForFunction(()=>!document.querySelector('#rose-hub')?.textContent.includes('Reconectando ao SEXO2…'));
 await page.getByRole('button',{name:'Criar sala',exact:true}).waitFor();

 const icon=await page.locator('.menu_item_Golden .menu-item-icon').last().evaluate(e=>({width:e.clientWidth,height:e.clientHeight,color:getComputedStyle(e).backgroundColor}));
 assert.deepEqual(icon,{width:20,height:20,color:'rgb(205, 190, 145)'});
 assert.equal(await page.locator('#rose-amigos-launch').isVisible(),false);
 assert.equal(await page.locator('.rsp-launch').isVisible(),false);
 await page.locator('#rose-hub>nav').getByRole('button',{name:'Swiftplay',exact:true}).click();
 await page.getByRole('button',{name:'Escolher',exact:true}).click();
 await page.locator('.rsp-grid').evaluate(e=>e.scrollTop=e.scrollHeight);
 const scroll=await page.locator('.rsp-grid').evaluate(e=>e.scrollTop);assert.ok(scroll>0);
 await page.waitForTimeout(3200);assert.equal(await page.locator('.rsp-grid').evaluate(e=>e.scrollTop),scroll);
 await page.evaluate(()=>{
   window.sample.libraryChampions=[{championId:11,name:'Master Yi'},{championId:22,name:'Ashe'}];
   const original=window.__roseBridge.send;
   window.__roseBridge.send=p=>{
     if(p.action==='library-open')window.sample.browseChampion={championId:p.championId,name:'Ashe',skins:[{skinId:22001,name:'Ashe Freljord',favorite:false},{skinId:22002,name:'Ashe PROJETO',favorite:false}]};
     if(p.action==='favorite'){window.sample.browseChampion.skins.find(s=>s.skinId===p.skinId).favorite=p.enabled;}
     if(p.action==='skin-index')window.sample.skinIndex=[[22001,'Ashe Freljord']];
     original(p);
   };
 });
 await page.locator('#rose-hub>nav').getByRole('button',{name:'Favoritas',exact:true}).click();
 await page.getByRole('searchbox',{name:'Buscar campeão ou skin',exact:true}).fill('Ashe');
 await page.getByRole('button',{name:'Ashe',exact:true}).click();
 await page.getByRole('button',{name:'Favoritar Ashe Freljord',exact:true}).click();
 await page.getByRole('button',{name:'Favoritar Ashe PROJETO',exact:true}).click();
 await page.waitForTimeout(100);
 assert.equal(await page.getByRole('button',{name:'Favoritar Ashe Freljord',exact:true}).getAttribute('aria-pressed'),'true');
 assert.equal(await page.getByRole('button',{name:'Favoritar Ashe PROJETO',exact:true}).getAttribute('aria-pressed'),'true');
 fs.mkdirSync('preview-r6',{recursive:true});await page.screenshot({path:'preview-r6/favorites-editor.png'});
 await page.locator('#rose-hub>nav').getByRole('button',{name:'Sala',exact:true}).click();
 await page.getByRole('button',{name:'Criar sala',exact:true}).click();await page.getByRole('button',{name:'Copiar link',exact:true}).waitFor();
 assert.equal(await page.locator('#rose-hub #rose-party-panel').count(),0);
 // Room recovery remains available after accepting a match.
 await page.evaluate(()=>{window.fakePhase='ChampSelect';window.emit('phase-change',{phase:'ChampSelect'});});
 await page.getByRole('textbox',{name:'Endereço para entrar'}).fill('https://new-room.test/#rose=TOKEN');
 await page.getByRole('button',{name:'Conectar',exact:true}).click();
 fs.mkdirSync('preview-r6',{recursive:true});await page.screenshot({path:'preview-r6/hub-room.png'});
 assert.equal((await page.evaluate(()=>window.sent.find(p=>p.action==='room-join'))).link,'https://new-room.test/#rose=TOKEN');
 await page.locator('#native-skin').click();assert.ok(await page.evaluate(()=>window.sent.some(p=>p.type==='manual-skin-choice')));
 await page.evaluate(()=>window.__roseHub.open(document.querySelector('.menu_item_Golden')));
 await page.locator('#rose-hub>nav').getByRole('button',{name:'Configurações',exact:true}).click();
 await page.locator('#rose-hub #sexo2-settings-panel').waitFor();
 assert.equal(await page.locator('#rose-hub lol-uikit-flyout-frame').count(),0);
 await page.getByText('Créditos da base',{exact:true}).waitFor();
 // The new form preserves draft fields across unrelated state and tab changes.
 await page.getByRole('spinbutton',{name:'Limite de pausa do jogo (s)'}).fill('75');
 await page.getByRole('textbox',{name:'Pasta do LoL (Game)'}).fill('invalid');
 await page.getByRole('button',{name:'Salvar alterações',exact:true}).click();
 await page.getByText('Pasta inválida',{exact:true}).waitFor();
 assert.equal(await page.getByRole('spinbutton',{name:'Limite de pausa do jogo (s)'}).inputValue(),'75');
 await page.locator('#rose-hub>nav').getByRole('button',{name:'Sala',exact:true}).click();
 await page.locator('#rose-hub>nav').getByRole('button',{name:'Configurações',exact:true}).click();
 assert.equal(await page.getByRole('textbox',{name:'Pasta do LoL (Game)'}).inputValue(),'invalid');
 await page.getByRole('textbox',{name:'Pasta do LoL (Game)'}).fill('C:/Riot/Game');
 await page.getByRole('button',{name:'Salvar alterações',exact:true}).click();
 await page.getByText('Configurações salvas.',{exact:true}).waitFor();
 await page.evaluate(()=>window.emit('sexo2-update-state',{available:true,latest:'v1.5.1',message:'Nova versão disponível: v1.5.1',github:'https://github.com/example/sexo2'}));
 assert.equal(await page.getByRole('link',{name:'Abrir GitHub do projeto'}).getAttribute('href'),'https://github.com/example/sexo2');
 await page.getByRole('button',{name:'Atualizar',exact:true}).click();
 assert.ok(await page.evaluate(()=>window.sent.some(p=>p.type==='sexo2-update-open')));
 await page.locator('#rose-hub-content').evaluate(e=>e.scrollTop=0);
 await page.screenshot({path:'preview-r6/settings-adapted.png'});
 // A biblioteca de mods agora vive na aba Mods do assistente da seleção (SEXO2-Assistant).

 await page.locator('#rose-hub>nav').getByRole('button',{name:'Suporte',exact:true}).click();
 await page.getByText('Aceitar partidas automaticamente',{exact:true}).waitFor();
 assert.equal(await page.locator('#rose-hub #rose-settings-panel').count(),0);
 const box=await page.locator('#rose-hub').boundingBox();assert.ok(box.x>=0&&box.y>=0&&box.x+box.width<=1280&&box.y+box.height<=720);
 fs.mkdirSync('preview-r6',{recursive:true});await page.screenshot({path:'preview-r6/hub-check.png'});
 await page.evaluate(()=>window.emit('phase-change',{phase:'InProgress'}));assert.equal(await page.locator('#rose-hub').isVisible(),false);
 assert.deepEqual(errors,[]);console.log('PASS: unified HUD, hidden launchers, scrolling, profiles, lottery, room controls in ChampSelect, manual guard, settings and diagnostics, viewport, game hide.');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
