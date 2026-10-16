/** @name SEXO2-Builds @description Recomendações e importação durante ChampSelect. */
(function(){
'use strict';
if(window.__sexo2Builds)return;
window.__sexo2Builds={};
let bridge=null,host=null,panel=null,ctx=null,data=null,opened=false,sequence=0;
let contextRequest=null,queryRequest=null,importRequest=null,queryTimer=null,lastQuery=null,pausedForGame=false;
let summary,status,entries,enemy,position,tier,details,runesButton,itemsButton,queryButton;
const selectors='.champion-select,.skin-selection-carousel'; // Selectors already used by ROSE-UI; always gated by LCU phase.
const el=(tag,text)=>{const n=document.createElement(tag);if(text!==undefined)n.textContent=text;return n;};
function button(text,fn){const n=el('button',text);n.type='button';n.onclick=fn;return n;}
function option(value,label){const n=el('option',label);n.value=value;return n;}
function requestId(){return 's2-build-'+Date.now().toString(36)+'-'+(++sequence);}
function say(text,error=false){if(status){status.textContent=text;status.dataset.error=String(error);}}
function selected(){return data?.entries?.find(row=>row.id===entries?.value);}
function lock(){
 const available=!!ctx?.available&&bridge?.ready;
 if(queryButton)queryButton.disabled=!available||!!importRequest;
 if(runesButton)runesButton.disabled=!available||!selected()||!!queryRequest||!!importRequest;
 if(itemsButton)itemsButton.disabled=runesButton.disabled;
 if(enemy)enemy.disabled=!available||ctx.mode!=='ranked'||!ctx.finalization||!!importRequest;
 if(position)position.disabled=ctx?.mode!=='ranked'||!!importRequest;
 if(tier)tier.disabled=!!importRequest;
 if(entries)entries.disabled=!!importRequest;
}
function reset(){
 data=null;queryRequest=null;importRequest=null;lastQuery=null;clearTimeout(queryTimer);
 if(entries)entries.replaceChildren();if(details)details.replaceChildren();lock();
}
function requestContext(){
 if(!bridge?.ready||contextRequest)return;
 contextRequest={id:requestId(),at:Date.now()};
 bridge.send({type:'sexo2-build-context',requestId:contextRequest.id});
}
function schedule(){
 clearTimeout(queryTimer);
 if(opened&&ctx?.available&&!importRequest)queryTimer=setTimeout(()=>query(false),350);
}
function query(force){
 if(!bridge?.ready||!ctx?.available||importRequest)return;
 const target=Number(enemy.value)||0;
 const payload={revision:ctx.revision,selection:target?'matchup':'general',opponentId:target,
                lane:ctx.mode==='ranked'?(position.value||ctx.lane):'all',tier:tier.value};
 const signature=JSON.stringify(payload);
 if(!force&&signature===lastQuery)return;
 lastQuery=signature;data=null;entries.replaceChildren();details.replaceChildren();
 queryRequest={id:requestId(),at:Date.now()};lock();say('Consultando LoLalytics…');
 bridge.send({type:'sexo2-build-query',requestId:queryRequest.id,...payload});
}
function importPage(target){
 const page=selected();
 if(!page||!data||queryRequest||importRequest||!bridge?.ready)return;
 importRequest={id:requestId(),at:Date.now()};lock();say('Importando e verificando no cliente…');
 bridge.send({type:'sexo2-build-import',requestId:importRequest.id,revision:ctx.revision,
              resultId:data.resultId,entryId:page.id,target});
}
function renderPage(){
 details.replaceChildren();const row=selected();
 if(!row){lock();return;}
 const page=row.page,metric=row.runeMetrics;
 const title=el('p',`${page.resolved.champion_name||ctx.champion.name} · patch ${page.resolved.patch}`);details.append(title);
 details.append(el('p',`Primária: ${metric.win_rate??'—'}% · ${metric.games??'—'} jogos. Amostra da runa principal.`));
 const runeBox=el('div');runeBox.className='s2-build-runes';
 for(const key of ['pri','sec','mod'])runeBox.append(el('p',page.runes[key].map(id=>data.runeNames?.[id]||id).join(' · ')));
 details.append(runeBox);
 for(const block of page.blocks){
  const names={starting:'Iniciais',core:'Core · três itens',item1:'Item 1',item2:'Item 2',item3:'Item 3',item4:'Item 4',item5:'Item 5',item6:'Item 6'};
  const section=el('section');section.className='s2-build-block';section.append(el('strong',names[block.kind]||block.kind));
  const itemName=c=>(data.itemNames?.[c.identifier]||`Item ${c.identifier}`)+(c.count>1?` ×${c.count}`:'');
  if(block.ordered)section.append(el('p',block.choices.map(itemName).join(block.kind==='core'?' → ':' + ')));
  else for(const choice of block.choices){
   section.append(el('p',itemName(choice)));
   if(choice.metrics?.games!=null)section.append(el('small',`${choice.metrics.win_rate??'—'}% · ${choice.metrics.games} jogos desse item`));
  }
  if(block.metrics?.games!=null)section.append(el('small',`${block.metrics.win_rate??'—'}% · ${block.metrics.games} jogos desse conjunto`));
  details.append(section);
 }
 const note=el('p','Itens 4–6 são alternativas por posição. As runas não têm WR conjunta confirmada.'+(page.conditioning==='opponent'?' Itens filtrados pelo adversário; o filtro conjunto de adversário + runa está indisponível.':''));note.className='s2-build-help';details.append(note);
 const link=el('a','Ver fonte no LoLalytics');
 if(/^https:\/\/lolalytics\.com\/lol\/[a-z0-9/-]+\/q-data\.json\?/.test(page.source_url)){
  const url=new URL(page.source_url);url.pathname=url.pathname.replace(/q-data\.json$/,'');link.href=url.href;link.target='_blank';link.rel='noopener noreferrer';details.append(link);
 }
 lock();
}
function arenaRows(result){
 details.replaceChildren();
 for(const [key,rows]of Object.entries(result.arena||{})){
  const section=el('section');section.className='s2-build-block';
  section.append(el('strong',key.includes('augment')?'Aprimoramentos · popularidade':'Itens · popularidade'));
  for(const row of rows)section.append(el('p',`${row.identifiers.map(id=>(key.includes('augment')?result.augmentNames?.[id]:result.itemNames?.[id])||id).join(' + ')} · frequência ${row.metrics.pick_rate??'—'} · ${row.metrics.games??'—'} jogos`));
  details.append(section);
 }
 details.append(el('p','Arena: consulta de popularidade; importação de páginas e WR de itens/aprimoramentos indisponíveis.'));
}
function receiveContext(message){
 if(message.requestId!==contextRequest?.id)return;
 contextRequest=null;const previous=ctx;ctx=message.context;pausedForGame=['GameStart','InProgress','Reconnect'].includes(ctx?.phase);
 if(!ctx||ctx.phase!=='ChampSelect'){reset();if(host)host.remove();host=null;return;}
 mount();if(!host)return;
 if(previous?.revision!==ctx.revision){reset();}
 summary.textContent=ctx.champion?`${ctx.champion.name} · ${({ranked:'SR · dados Ranked',aram:'ARAM',arena:'Arena'})[ctx.mode]||'modo indisponível'} · risco ${({ 'very-low':'muito baixo',low:'baixo',medium:'médio',high:'alto','very-high':'muito alto'})[ctx.riskLevel]||ctx.riskLevel}`:'Escolha seu campeão.';
 const chosen=enemy.value;
 enemy.replaceChildren(option('','Geral · WR / Common'));
 for(const row of ctx.enemies||[])enemy.append(option(String(row.id),`vs ${row.name}`));
 if([...enemy.options].some(o=>o.value===chosen))enemy.value=chosen;
 if(!ctx.finalization||ctx.mode!=='ranked')enemy.value='';
 if(!ctx.available)say(ctx.warning||'Aguardando a escolha de um campeão.');
 else if(!ctx.finalization&&ctx.mode==='ranked'&&!queryRequest&&!data)say('Matchups serão liberados na finalização do draft.');
 if(ctx.warning)summary.textContent+=' · '+ctx.warning;
 lock();schedule();
}
function receiveData(message){
 if(message.requestId!==queryRequest?.id)return;
 queryRequest=null;
 if(message.result.revision!==ctx?.revision){lock();return;}
 data=message.result;entries.replaceChildren();
 for(const row of data.entries)entries.append(option(row.id,row.label));
 if(enemy.value&&[...entries.options].some(o=>o.value==='vs:'+enemy.value))entries.value='vs:'+enemy.value;
 if(data.arena)arenaRows(data);else renderPage();
 say(data.arena?'Arena · popularidade.':'Sugestões prontas. Itens reúne as opções preparadas em até dois conjuntos próprios.');lock();
}
function receiveImported(message){
 if(message.requestId!==importRequest?.id)return;
 importRequest=null;say(message.result.verified?message.result.message:'Importação não confirmada.',!message.result.verified);lock();
}
function receiveError(message){
 if(message.requestId===contextRequest?.id){contextRequest=null;reset();ctx=null;say(message.error,true);}
 else if(message.requestId===queryRequest?.id){queryRequest=null;say(message.error,true);lock();}
 else if(message.requestId===importRequest?.id){importRequest=null;say(message.error,true);lock();}
}
function mount(){
 const screen=document.querySelector(selectors);
 if(!screen||ctx?.phase!=='ChampSelect')return;
 if(host?.isConnected)return;
 host=el('aside');host.id='sexo2-builds';host.setAttribute('aria-label','SEXO2 · builds da seleção');
 const style=el('style');style.textContent=`
 #sexo2-builds{position:fixed;left:50%;transform:translateX(-50%);top:84px;z-index:10900;font:13px Spiegel,Arial,sans-serif;color:#c8c1ae;max-width:calc(100vw - 24px)}
 #sexo2-builds *{box-sizing:border-box}#sexo2-builds [hidden]{display:none!important}
 #sexo2-builds button,#sexo2-builds select{font:inherit;color:#cdbe91;background:#101e26;border:1px solid #5a513b;border-radius:0;padding:7px;max-width:100%}
 #sexo2-builds button{cursor:pointer}#sexo2-builds button:disabled{opacity:.45;cursor:default}
 #sexo2-builds .s2-build-panel{display:flex;flex-direction:column;width:440px;max-width:calc(100vw - 24px);height:calc(100vh - 220px);max-height:calc(100vh - 220px);overflow:hidden;background:#09141bf5;border:1px solid #5a513b;padding:12px}
 #sexo2-builds p{line-height:1.45;margin:6px 0}#sexo2-builds label{display:block;margin:8px 0}
 #sexo2-builds .s2-build-fields{display:grid;grid-template-columns:1fr 1fr;gap:0 8px;flex:none}#sexo2-builds .s2-build-details{overflow:auto;min-height:0;flex:1}#sexo2-builds select{width:100%;margin-top:4px}#sexo2-builds .s2-build-actions{display:flex;gap:6px;margin:10px 0;flex-wrap:wrap}
 #sexo2-builds .s2-build-block{border-top:1px solid #26343c;padding:8px 0}#sexo2-builds small,#sexo2-builds .s2-build-help{font-size:11px;color:#a09b8c}
 #sexo2-builds [data-error=true]{color:#e5aa8a}#sexo2-builds a{color:#c8aa6e}
 `;
 const launch=button('SEXO2 · Builds',()=>{opened=!opened;panel.hidden=!opened;if(opened){requestContext();schedule();}});
 launch.setAttribute('aria-label','Abrir builds do SEXO2');host.append(style,launch);
 panel=el('div');panel.className='s2-build-panel';panel.hidden=!opened;host.append(panel);
 summary=el('p');panel.append(summary);const fields=el('div');fields.className='s2-build-fields';panel.append(fields);
 function select(label){const row=el('label',label),input=el('select');input.setAttribute('aria-label',label);row.append(input);fields.append(row);return input;}
 position=select('Sua rota');position.append(option('','Automática'),...Object.entries({top:'Topo',jungle:'Selva',middle:'Meio',bottom:'Atirador',support:'Suporte'}).map(([v,t])=>option(v,t)));
 tier=select('Amostra');tier.append(option('emerald_plus','Emerald+'),option('all','Todos os elos'));
 enemy=select('Adversário');enemy.append(option('','Geral · WR / Common'));enemy.title='Matchups disponíveis ao finalizar o draft de Summoner’s Rift.';
 for(const input of [position,tier,enemy])input.onchange=()=>{data=null;queryRequest=null;entries.replaceChildren();details.replaceChildren();lastQuery=null;lock();query(false);};
 entries=select('Sugestão');entries.onchange=renderPage;
 const actions=el('div');actions.className='s2-build-actions';
 queryButton=button('Consultar',()=>query(true));runesButton=button('Importar runas',()=>importPage('runes'));itemsButton=button('Importar itens',()=>importPage('items'));
 actions.append(queryButton,runesButton,itemsButton);panel.append(actions);
 status=el('p');status.setAttribute('role','status');panel.append(status);details=el('div');details.className='s2-build-details';panel.append(details);
 screen.append(host);lock();
}
function attach(){
 if(bridge||!window.__roseBridge)return;
 bridge=window.__roseBridge;
 bridge.subscribe('sexo2-build-context-data',receiveContext);bridge.subscribe('sexo2-build-data',receiveData);
 bridge.subscribe('sexo2-build-error',receiveError);bridge.subscribe('sexo2-build-imported',receiveImported);
 bridge.subscribe('phase-change',message=>{reset();contextRequest=null;pausedForGame=['GameStart','InProgress','Reconnect'].includes(message.phase);if(message.phase!=='ChampSelect'){ctx=null;host?.remove();host=null;opened=false;}else requestContext();});
 bridge.onReady(()=>{reset();pausedForGame=false;contextRequest=null;requestContext();});
}
const tick=setInterval(()=>{
 attach();
 if(host&&!host.isConnected){host=null;reset();}
 if(!bridge?.ready){if(host){reset();say('Reconectando ao SEXO2…',true);}contextRequest=null;return;}
 if(!pausedForGame&&document.querySelector(selectors))requestContext();
 else if(host){host.remove();host=null;opened=false;reset();}
 const now=Date.now();
 if(contextRequest&&now-contextRequest.at>12000){contextRequest=null;reset();say('O cliente não respondeu. Tentando reconectar…',true);}
 if(queryRequest&&now-queryRequest.at>180000){queryRequest=null;say('A fonte demorou demais. Tente novamente.',true);lock();}
 if(importRequest&&now-importRequest.at>45000){importRequest=null;say('A confirmação demorou. Confira a página no cliente antes de repetir.',true);lock();}
},1500);
window.addEventListener('keydown',event=>{if(event.key==='Escape'&&panel){opened=false;panel.hidden=true;}});
attach();
})();
