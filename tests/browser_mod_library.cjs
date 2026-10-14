const {chromium}=require('../ui-test-runtime/node_modules/playwright');
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({headless:true});
 try{
  const page=await browser.newPage({viewport:{width:1280,height:800}}),errors=[];
  page.on('pageerror',error=>errors.push(error.message));
  await page.setContent('<html><body style="background:#09141b"><div id="target" style="width:520px"></div></body></html>');
  await page.evaluate(()=>{
   window.sent=[];window.handlers={};window.confirm=()=>true;
   window.sample={type:'sexo2-library-state',message:'Biblioteca carregada.',champions:[{id:11,name:'Master Yi'},{id:22,name:'Ashe'}],mods:[{id:'known',name:'Meu mod',category:'skins',championId:22,targets:[22000]}],incoming:[{id:'unknown',file:'Outfit.fantome',category:'skins',status:'revisar'}]};
   window.emit=(type,data)=>{for(const handler of window.handlers[type]||[])handler(data);};
   window.__roseBridge={ready:true,subscribe(type,callback){(window.handlers[type]??=[]).push(callback);},onReady(callback){callback();},send(data){window.sent.push(data);
    if(data.type==='settings-request')setTimeout(()=>window.emit('settings-data',{requestId:data.requestId,threshold:.5,monitorAutoResumeTimeout:60,autostart:false,hideEmptyCategories:false,gamePath:''}),0);
    if(data.type==='sexo2-library-request'){
     if(data.action==='resolve'){window.sample.incoming[0].status='importado';window.sample.mods.push({id:'new',name:'Outfit',category:'skins',championId:data.championId,targets:data.targets});}
     if(data.action==='delete')window.sample.mods=window.sample.mods.filter(mod=>mod.id!==data.id);
     if(data.action==='skins')setTimeout(()=>window.emit('sexo2-library-skins',{id:data.id,championId:data.championId,skins:[{id:data.championId*1000,name:'Padrão'},{id:data.championId*1000+1,name:'Skin especial'}]}),0);
     else setTimeout(()=>window.emit('sexo2-library-state',structuredClone(window.sample)),0);
    }
   }};
  });
  for(const plugin of ['SEXO2-ModLibrary','SEXO2-Settings'])await page.addScriptTag({path:path.resolve('Pengu Loader/plugins',plugin,'index.js')});
  await page.waitForTimeout(150);
  await page.evaluate(()=>window.dispatchEvent(new CustomEvent('rose-hub-settings',{detail:{target:document.getElementById('target')}})));
  await page.getByLabel('Pasta do LoL (Game)').fill('C:/rascunho preservado');
  await page.getByRole('button',{name:'Biblioteca de mods',exact:true}).click();
  const library=page.locator('#sexo2-mod-library');await library.waitFor();
  assert.equal(await page.locator('lol-uikit-dialog-frame').count(),0);
  await library.getByLabel('Campeão do mod').selectOption('11');
  await library.getByLabel('Skin-base do mod').selectOption('11001');
  await library.getByRole('button',{name:'Importar',exact:true}).click();
  await library.getByText('1 arquivo(s) concluído(s). Originais preservados.',{exact:true}).waitFor();
  const resolve=await page.evaluate(()=>window.sent.find(data=>data.action==='resolve'));
  assert.equal(resolve.championId,11);assert.deepEqual(resolve.targets,[11001]);
  const row=library.locator('.s2-mod-row').filter({hasText:'Meu mod'});
  await row.getByRole('button',{name:'Editar',exact:true}).click();
  const name=row.getByLabel('Nome do mod');await name.fill('Rascunho preservado');
  await page.evaluate(()=>window.emit('sexo2-library-state',structuredClone(window.sample)));
  assert.equal(await name.inputValue(),'Rascunho preservado');
  await row.getByRole('button',{name:'Fechar edição',exact:true}).click();
  await row.getByRole('button',{name:'Remover',exact:true}).click();
  await row.getByRole('button',{name:'Confirmar remoção',exact:true}).click();
  await row.waitFor({state:'detached'});
  await library.getByRole('button',{name:'Exportar todos',exact:true}).click();
  assert.ok(await page.evaluate(()=>window.sent.some(data=>data.action==='export')));
  await library.getByRole('button',{name:'← Configurações',exact:true}).click();
  assert.equal(await page.getByLabel('Pasta do LoL (Game)').inputValue(),'C:/rascunho preservado');
  assert.deepEqual(errors,[]);
  fs.mkdirSync('preview-r6',{recursive:true});await page.screenshot({path:'preview-r6/mod-library.png'});
  console.log('Library panel: batch, manual skin-base, draft preservation, delete and export pass.');
 }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exit(1);});
