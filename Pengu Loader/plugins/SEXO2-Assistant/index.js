/** @name SEXO2-Assistant @description Assistente da seleção de campeões: runas, itens e mods (452×492, ancorado ao botão SEXO2). */
(()=>{
'use strict';
const LANES={top:'Topo',jungle:'Selva',middle:'Meio',bottom:'Atirador',support:'Suporte',all:'Qualquer'};
const TABS=['Runas','Itens','Mods','Preferências rápidas','Todas as configurações'];
const ERRORS={unsupported_mode:'Sem estatísticas para este modo de jogo.',stats_unavailable:'Estatísticas indisponíveis agora.',stats_unknown_champion:'Campeão sem estatísticas.',unknown_recommendation:'Escolha um adversário para ver esta recomendação.',busy:'O SEXO2 está ocupado. Tente de novo.',no_free_page:'Sem página de runas livre. Nenhuma página sua foi alterada.'};
const KINDS={starting:'Inicial',core:'Essenciais',suggested_core:'Essenciais'};
const SELECTION={win:'Maior WR',pick:'Mais comum'};
const css=`
#sexo2-assistant-btn{position:fixed;right:16px;bottom:12px;z-index:10020;height:36px;padding:0 18px;background:#c8aa6e;color:#010a13;border:0;border-radius:0;font:600 15px Oswald,'Segoe UI',sans-serif;letter-spacing:.08em;cursor:pointer}
#sexo2-assistant-btn[hidden],#sexo2-assistant[hidden]{display:none!important}
#sexo2-assistant{position:fixed;right:16px;bottom:56px;z-index:10020;width:min(452px,calc(100vw - 32px));height:min(492px,calc(100vh - 72px));display:flex;flex-direction:column;background:#09141b;color:#f0e6d2;border:1px solid #463e2f;border-radius:0;font:13px Inter,'Segoe UI',sans-serif;box-shadow:0 8px 24px #0009;overflow:hidden}
#sexo2-assistant,#sexo2-assistant *{box-sizing:border-box;border-radius:0}
#sexo2-assistant header{display:grid;grid-template-columns:1fr 1.3fr 1fr;gap:8px;padding:8px 10px;border-bottom:1px solid #36474b}
#sexo2-assistant label{display:flex;flex-direction:column;gap:2px;font-size:11px;color:#a09b8c;min-width:0}
#sexo2-assistant select,#sexo2-assistant input[type=search]{font:inherit;color:#f0e6d2;background:#15232b;border:1px solid #463e2f;padding:4px;width:100%;min-width:0}
#sexo2-assistant .a-lane{color:#f0e6d2;padding:5px 0;font-size:13px}
#sexo2-assistant nav{display:flex;border-bottom:1px solid #36474b}
#sexo2-assistant nav button{flex:1;min-width:0;padding:8px 2px;background:transparent;color:#a09b8c;border:0;border-bottom:2px solid transparent;font:500 11px Oswald,'Segoe UI',sans-serif;letter-spacing:.04em;text-transform:uppercase;cursor:pointer}
#sexo2-assistant nav button[aria-selected=true]{color:#f0e6d2;border-bottom-color:#c8aa6e}
#sexo2-assistant .a-body{flex:1;overflow:auto;padding:10px}
#sexo2-assistant .a-card{display:block;width:100%;text-align:left;margin:0 0 6px;padding:8px;background:#15232b;color:#f0e6d2;border:1px solid #463e2f;cursor:pointer;font:inherit}
#sexo2-assistant .a-card:hover,#sexo2-assistant .a-card[aria-pressed=true]{border-color:#c8aa6e}
#sexo2-assistant .a-card img{width:24px;height:24px;vertical-align:middle;margin-right:3px;background:#0c2834}
#sexo2-assistant .a-card strong{display:block;margin-bottom:4px;font:600 13px Oswald,'Segoe UI',sans-serif;letter-spacing:.04em;text-transform:uppercase}
#sexo2-assistant h4{margin:10px 0 6px;font:600 13px Oswald,'Segoe UI',sans-serif;letter-spacing:.06em;text-transform:uppercase;color:#c8aa6e}
#sexo2-assistant .a-muted{color:#a09b8c;font-size:12px;margin:6px 0}
#sexo2-assistant .a-items img{width:30px;height:30px;margin:0 3px 3px 0;background:#0c2834}
#sexo2-assistant button.a-action{padding:7px 12px;background:#15232b;color:#f0e6d2;border:1px solid #6e644b;cursor:pointer;font:inherit}
#sexo2-assistant button.a-action:disabled{opacity:.45;cursor:default}
#sexo2-assistant details{border-top:1px solid #25343d;padding:6px 0}
#sexo2-assistant #sexo2-mod-library>button:nth-child(2){display:none}
`;
let bridge,state=null,tab='Runas',open=false,phase=null,btn,panel,body,selOpp,laneText,names={},items={},perks={},dataLoaded=false,friends=null,seq=0,libraryHost;
function el(tag,text,cls){const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(cls)n.className=cls;return n;}
function asset(path){return typeof path==='string'&&path.startsWith('/lol-game-data/assets/')?path:null;}
function icon(path,title){const img=el('img');img.alt='';if(title)img.title=title;const src=asset(path);if(src)img.src=src;img.addEventListener('error',()=>img.removeAttribute('src'));return img;}
function send(payload){if(bridge?.ready)bridge.send(payload);}
function inSelect(){return phase==='ChampSelect'||phase==='FINALIZATION';}
async function loadData(){
 if(dataLoaded)return;dataLoaded=true;
 const get=async url=>{try{const r=await fetch(url);return r.ok?await r.json():null;}catch{return null;}};
 const [champions,itemList,perkList]=await Promise.all([get('/lol-game-data/assets/v1/champion-summary.json'),get('/lol-game-data/assets/v1/items.json'),get('/lol-game-data/assets/v1/perks.json')]);
 for(const c of champions||[])if(c&&c.id>0)names[c.id]=c.name;
 for(const i of itemList||[])if(i&&i.id)items[i.id]={name:i.name,icon:i.iconPath};
 for(const p of perkList||[])if(p&&p.id)perks[p.id]={name:p.name,icon:p.iconPath};
 render();
}
function build(){
 const style=el('style',css);document.head.append(style);
 const base='http://127.0.0.1:'+(window.__roseBridge?.port||50000)+'/asset/fonts/';
 document.head.append(el('style',`@font-face{font-family:Oswald;font-weight:200 700;font-display:swap;src:url(${base}oswald-latin-wght-normal.woff2) format('woff2')}@font-face{font-family:Inter;font-weight:100 900;font-display:swap;src:url(${base}inter-latin-wght-normal.woff2) format('woff2')}`));
 btn=el('button','SEXO2');btn.id='sexo2-assistant-btn';btn.type='button';btn.hidden=true;btn.setAttribute('aria-haspopup','dialog');btn.onclick=()=>toggle();
 panel=el('section');panel.id='sexo2-assistant';panel.hidden=true;panel.setAttribute('role','dialog');panel.setAttribute('aria-label','Assistente de seleção');
 const head=el('header');
 const lane=el('label','Rota');laneText=el('span','—','a-lane');lane.append(laneText);
 const opp=el('label','Confronto');selOpp=el('select');selOpp.setAttribute('aria-label','Confronto');selOpp.onchange=()=>send({type:'assistant-opponent',championId:Number(selOpp.value)||null});opp.append(selOpp);
 const src=el('label','Fonte');const sel=el('select');sel.setAttribute('aria-label','Fonte');const a=el('option','Lolalytics');a.value='lolalytics';sel.append(a);src.append(sel);
 head.append(lane,opp,src);
 const nav=el('nav');nav.setAttribute('role','tablist');
 for(const t of TABS){const x=el('button',t);x.type='button';x.setAttribute('role','tab');x.dataset.tab=t;x.onclick=()=>selectTab(t);nav.append(x);}
 body=el('div',undefined,'a-body');
 panel.append(head,nav,body);document.body.append(btn,panel);
 libraryHost=el('div');
}
function toggle(force){
 open=force===undefined?!open:force;panel.hidden=!open||!inSelect();
 if(!panel.hidden){loadData();send({type:'assistant-request'});requestFriends();render();}
}
function selectTab(t){
 if(t==='Todas as configurações'){toggle(false);window.__roseHub?.show?.('Configurações');return;}
 tab=t;if(t==='Itens'&&state&&state.builds==null)send({type:'assistant-items-request'});
 if(t==='Preferências rápidas')requestFriends();
 render();
}
function requestFriends(){send({type:'friends-request',action:'snapshot',requestId:'assistant-'+(++seq)});}
function laneLabel(){return LANES[state?.lane]||'—';}
function renderHeader(){
 laneText.textContent=laneLabel();
 const keep=String(state?.opponentId||'');selOpp.replaceChildren();
 const none=el('option','Nenhum');none.value='';selOpp.append(none);
 for(const id of state?.enemies||[]){const o=el('option',names[id]||'Campeão '+id);o.value=id;selOpp.append(o);}
 selOpp.value=keep;
 for(const x of panel.querySelectorAll('nav button'))x.setAttribute('aria-selected',String(x.dataset.tab===tab));
}
function message(error){return ERRORS[error]||'Não foi possível concluir. Tente novamente.';}
function perkRow(page){const row=el('div');for(const id of [page?.perks||[]].flat())row.append(icon(perks[id]?.icon,perks[id]?.name));return row;}
function runeCard(layout,matchup){
 const page=layout.page,runes=state.runes;
 const same=p=>p&&page&&p.primary===page.primary&&p.sub===page.sub&&JSON.stringify(p.perks)===JSON.stringify(page.perks);
 const card=el('button',undefined,'a-card');card.type='button';card.setAttribute('aria-pressed',String(same(runes.applied)||same(runes.chosen)));
 const opponent=names[state.opponentId]||'';
 const label=(matchup?'Contra '+opponent+' · ':'')+(SELECTION[layout.selection]||layout.selection);
 card.append(el('strong',label),perkRow(page));
 const stat=layout.keystoneWinRate==null?'':`${layout.keystoneWinRate.toFixed(1).replace('.',',')}% de vitórias`;
 const small=el('div',[stat,layout.games?layout.games.toLocaleString('pt-BR')+' partidas':''].filter(Boolean).join(' · '),'a-muted');small.title='Vitórias e partidas da runa-chave';card.append(small);
 card.onclick=()=>send({type:'assistant-runes-choose',selection:layout.selection,matchup});
 return card;
}
function renderRunes(){
 if(state?.error&&!(state.runes?.general||[]).length){body.append(el('p',message(state.error),'a-muted'));return;}
 const runes=state?.runes;if(!runes||!(runes.general||[]).length){body.append(el('p',state?'Sem recomendações por enquanto.':'Aguardando a seleção de campeões.','a-muted'));return;}
 body.append(el('h4','Geral'));for(const l of runes.general)body.append(runeCard(l,false));
 if((runes.matchup||[]).length){body.append(el('h4','Confronto'));for(const l of runes.matchup)body.append(runeCard(l,true));}
 const status=runes.pending?'Importando a página…':runes.error?message(runes.error):runes.applied?'Página importada.':'Clique numa recomendação para importar a página.';
 const line=el('p',status,'a-muted');line.setAttribute('role','status');body.append(line);
}
function itemRow(block){
 const row=el('div',undefined,'a-items');
 const seen=new Set();for(const it of block.items){if(seen.has(it.id))continue;seen.add(it.id);const info=items[it.id];const win=it.winRate==null?'':' · '+it.winRate.toFixed(1).replace('.',',')+'% de vitórias do item';row.append(icon(info?.icon,(info?.name||'Item '+it.id)+win));}
 return row;
}
function groups(page){
 const out={Inicial:[],Essenciais:[],Situacionais:[]};
 for(const block of page.blocks){const name=KINDS[block.kind]||'Situacionais';out[name].push(block);}
 return out;
}
function pageView(page,box){
 const g=groups(page);
 for(const [name,blocks] of Object.entries(g)){if(!blocks.length)continue;box.append(el('h4',name));for(const b of blocks)box.append(itemRow(b));}
}
function renderItems(){
 const builds=state?.builds;
 if(builds==null){body.append(el('p','Carregando builds…','a-muted'));return;}
 if(!builds.length){body.append(el('p',state?.error?message(state.error):'Sem builds para este campeão.','a-muted'));return;}
 const main=builds.find(b=>b.selection==='win')||builds[0],others=builds.filter(b=>b!==main);
 const picks=new Set([main.selection]);
 body.append(el('h4','Build padrão'));pageView(main,body);
 if(others.length){
  const d=el('details');d.append(el('summary','Outras builds e trios'));
  for(const b of others){const box=el('div');const label=el('label');label.style.flexDirection='row';label.style.gap='6px';const cb=el('input');cb.type='checkbox';cb.setAttribute('aria-label','Importar '+(b.label||b.selection));cb.onchange=()=>cb.checked?picks.add(b.selection):picks.delete(b.selection);label.append(cb,el('span',SELECTION[b.selection]||b.label||b.selection));box.append(label);pageView(b,box);d.append(box);}
  body.append(d);
 }
 const imported=state.items||{};
 const go=el('button',imported.pending?'Importando…':'Importar para o cliente','a-action');go.type='button';go.disabled=!!imported.pending;go.onclick=()=>send({type:'assistant-items-import',selections:[...picks]});
 body.append(go);
 const status=imported.confirmed?'Conjuntos de itens importados.':imported.error?message(imported.error):'';
 if(status){const p=el('p',status,'a-muted');p.setAttribute('role','status');body.append(p);}
}
function renderMods(){
 body.append(libraryHost);
 if(window.__sexo2ModLibrary)window.__sexo2ModLibrary.open(libraryHost,'all');
 else body.append(el('p','A biblioteca de mods não está disponível.','a-muted'));
}
function renderPrefs(){
 const label=el('label');label.style.flexDirection='row';label.style.gap='8px';label.style.color='#f0e6d2';label.style.fontSize='13px';
 const cb=el('input');cb.type='checkbox';cb.checked=friends?.autoAccept===true;cb.setAttribute('aria-label','Aceitar partidas automaticamente');
 cb.onchange=()=>send({type:'friends-request',action:'auto-accept',enabled:cb.checked,requestId:'assistant-'+(++seq)});
 label.append(cb,el('span','Aceitar partidas automaticamente'));
 body.append(label,el('p','As demais opções estão em Todas as configurações.','a-muted'));
}
function render(){
 if(!panel)return;
 renderHeader();
 if(tab!=='Mods'&&libraryHost.parentNode===body)libraryHost.remove();
 const scroll=body.scrollTop;
 if(tab==='Mods'){if(!body.contains(libraryHost)){body.replaceChildren();renderMods();}}
 else{body.replaceChildren();if(tab==='Runas')renderRunes();else if(tab==='Itens')renderItems();else if(tab==='Preferências rápidas')renderPrefs();}
 body.scrollTop=scroll;
}
function receive(data){state=data;if(!panel.hidden)render();}
function start(){
 if(!document.body||!document.head){setTimeout(start,100);return;}
 if(window.__sexo2Assistant)return;window.__sexo2Assistant=true;
 build();
 window.addEventListener('keydown',e=>{if(e.key==='Escape'&&open){toggle(false);btn.focus();}});
 const attach=()=>{
  if(bridge||!window.__roseBridge)return false;
  bridge=window.__roseBridge;
  bridge.subscribe('assistant-state',receive);
  bridge.subscribe('friends-state',d=>{if(String(d.requestId||'').startsWith('assistant-')){friends=d;if(phase===null&&d.phase){phase=d.phase;btn.hidden=!inSelect();}if(!panel.hidden&&tab==='Preferências rápidas')render();}});
  bridge.subscribe('phase-change',d=>{phase=d.phase;btn.hidden=!inSelect();if(!inSelect()){open=false;panel.hidden=true;state=null;}else if(open){panel.hidden=false;send({type:'assistant-request'});}});
  requestFriends();
  return true;
 };
 if(!attach()){const t=setInterval(()=>{if(attach())clearInterval(t);},500);}
}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else start();
})();
