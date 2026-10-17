/** @name SEXO2-Builds @description Recomendações e importação durante ChampSelect. */
(function(){
'use strict';
if(window.__sexo2Builds)return;
window.__sexo2Builds={};
let bridge=null,host=null,panel=null,ctx=null,data=null,opened=false,sequence=0;
let contextRequest=null,queryRequest=null,importRequest=null,queryTimer=null,lastQuery=null,pausedForGame=false,lastContextAt=0;
let summary,status,entries,enemy,position,tier,details,warnings,runesButton,itemsButton,queryButton,runeTarget;
const supportsPanel=context=>context?.phase==='ChampSelect'&&context.mode==='ranked';
const el=(tag,text)=>{const n=document.createElement(tag);if(text!==undefined)n.textContent=text;return n;};
function button(text,fn){const n=el('lol-uikit-flat-button',text);n.className='lol-uikit-flat-button idle';n.setAttribute('role','button');n.setAttribute('tabindex','0');n.onclick=e=>{if(n.hasAttribute('disabled')){e?.preventDefault();return;}fn();};n.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();n.click();}});return n;}
function disable(node,value){if(!node)return;node.toggleAttribute('disabled',!!value);node.setAttribute('aria-disabled',String(!!value));}
function close(){opened=false;if(panel)panel.hidden=true;}
function unmount(){host?.remove();panel?.remove();host=panel=null;opened=false;document.body?.classList.remove('sexo2-builds-in-draft');}
function option(value,label){const n=el('option',label);n.value=value;return n;}
function requestId(){return 's2-build-'+Date.now().toString(36)+'-'+(++sequence);}
function say(text,error=false){if(status){status.textContent=text;status.dataset.error=String(error);}}
function selected(){return data?.entries?.find(row=>row.id===entries?.value);}
function selectOverlay(){if(data&&ctx?.available&&bridge?.ready)bridge.send({type:'sexo2-build-select',requestId:requestId(),revision:ctx.revision,resultId:data.resultId,entryId:entries.value});}
function lock(){
 const available=!!ctx?.available&&bridge?.ready;
 disable(queryButton,!available||!!importRequest);
 const blocked=!available||!selected()||!!queryRequest||!!importRequest;
 disable(runesButton,blocked||!!runeTarget?.selectedOptions?.[0]?.disabled);
 disable(itemsButton,blocked);
 if(enemy)enemy.disabled=!available||ctx.mode!=='ranked'||!ctx.finalization||!!importRequest;
 if(position)position.disabled=ctx?.mode!=='ranked'||!!importRequest;
 if(tier)tier.disabled=!!importRequest;
 if(entries)entries.disabled=!!importRequest;
 if(runeTarget)runeTarget.disabled=!!importRequest;
}
function reset(){
 data=null;queryRequest=null;importRequest=null;lastQuery=null;clearTimeout(queryTimer);
 if(entries)entries.replaceChildren();if(details)details.replaceChildren();lock();
 if(warnings)warnings.replaceChildren();
}
function requestContext(){
 if(!bridge?.ready||contextRequest)return;
 contextRequest={id:requestId(),at:Date.now()};
 lastContextAt=contextRequest.at;
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
 warnings.replaceChildren();queryRequest={id:requestId(),at:Date.now()};lock();say('Consultando LoLalytics…');
 bridge.send({type:'sexo2-build-query',requestId:queryRequest.id,...payload});
}
function importPage(target){
 const page=selected();
 if(!page||!data||queryRequest||importRequest||!bridge?.ready)return;
 if(target==='runes')runeTarget.dataset.userSelected='true';
 importRequest={id:requestId(),at:Date.now()};lock();say('Importando e verificando no cliente…');
 bridge.send({type:'sexo2-build-import',requestId:importRequest.id,revision:ctx.revision,
              resultId:data.resultId,entryId:page.id,target,...(target==='runes'&&Number(runeTarget.value)>0?{runePageId:Number(runeTarget.value)}:{})});
}
function renderPage(){
 details.replaceChildren();const row=selected();
 if(!row){lock();return;}
 details.append(warnings);
 const page=row.page,metric=row.runeMetrics;
 const title=el('p',`${page.resolved.champion_name||ctx.champion.name} · patch ${page.resolved.patch}`);details.append(title);
 if(row.id==='wr')details.append(el('p','WR ajustada ao risco: compara as duas sugestões disponíveis na fonte. Não prevê a chance de vencer a partida.'));
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
function receiveContext(message){
 if(message.requestId!==contextRequest?.id)return;
 contextRequest=null;const previous=ctx;ctx=message.context;pausedForGame=['GameStart','InProgress','Reconnect'].includes(ctx?.phase);
 if(!supportsPanel(ctx)){reset();unmount();return;}
 mount();if(!host)return;
 if(previous?.revision!==ctx.revision){reset();}
 summary.textContent=ctx.champion?`${ctx.champion.name} · ${({ranked:'SR · dados Ranked',aram:'ARAM',arena:'Arena'})[ctx.mode]||'modo indisponível'} · risco ${({ 'very-low':'muito baixo',low:'baixo',medium:'médio',high:'alto','very-high':'muito alto'})[ctx.riskLevel]||ctx.riskLevel}`:'Escolha seu campeão.';
 const chosen=enemy.value;
 enemy.replaceChildren(option('','Geral · WR / Common'));
 const previousRune=runeTarget.value,hadRuneChoice=runeTarget.dataset.userSelected==='true';
 runeTarget.replaceChildren(option('','Página gerenciada SEXO2'));
 for(const row of ctx.runePages||[])runeTarget.append(option(String(row.id),row.name+(row.current?' · atual':'')));
 if(hadRuneChoice){
  if(previousRune&&![...runeTarget.options].some(o=>o.value===previousRune)){const missing=option(previousRune,'Página escolhida indisponível');missing.disabled=true;runeTarget.append(missing);}
  runeTarget.value=previousRune;
 }else runeTarget.value=String((ctx.runePages||[]).find(r=>r.current)?.id||'');

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
 warnings.replaceChildren();
 const notices=new Set([...(data.warnings||[]),...data.entries.flatMap(row=>row.page.warnings||[])].map(sourceNotice).filter(Boolean));
 for(const text of notices)warnings.append(el('p',text));
 for(const row of data.entries)entries.append(option(row.id,row.label));
 if(enemy.value&&[...entries.options].some(o=>o.value==='vs:'+enemy.value))entries.value='vs:'+enemy.value;
 renderPage();selectOverlay();
 say('Sugestões prontas. Itens reúne as opções preparadas em até dois conjuntos próprios.');lock();
}
function sourceNotice(code){
 if(typeof code!=='string')return null;
 if(['rune_scope_primary_not_joint_page','not_full_rune_page_joint_sample'].includes(code)||code.startsWith('Rune suggestions describe'))return 'A WR exibida corresponde à runa principal, não à página inteira.';
 if(['only_two_upstream_layout_candidates','local_risk_not_draftgap_prediction','selected_keystone_then_refresh_layout','keystone_conditioned','opponent_conditioned','keystone_filter_unavailable','not_joint_build_sample','risk_not_applicable_to_arena_popularity'].includes(code))return null; // Explained beside the selected suggestion.
 if(code==='missing_item_sample'||code==='low_item_sample')return 'Há itens com amostra pequena ou sem número de jogos disponível.';
 if(/^(starting_items|item[1-6])_unavailable$/.test(code))return 'Algumas posições de itens estão indisponíveis nesta amostra.';
 if(code.startsWith('Arena item, combination')||code.startsWith('Unrecognized Arena payload'))return 'Arena exibe somente popularidade; métricas restritas permanecem indisponíveis.';
 if(code.startsWith('Rune suggestion layout'))return 'Uma sugestão incompleta foi omitida pela fonte.';
 if(code.startsWith('Catálogo de nomes indisponível'))return 'Nomes indisponíveis no cliente; os itens e runas aparecem pelos IDs.';
 return 'A fonte informou uma limitação adicional. Confira a página de origem.';
}
function receiveImported(message){
 if(message.requestId!==importRequest?.id)return;
 importRequest=null;say(message.result.verified?message.result.message:'Importação não confirmada.',!message.result.verified);lock();
}
function receiveError(message){
 if(message.requestId===contextRequest?.id){contextRequest=null;reset();if(supportsPanel(ctx))ctx={...ctx,available:false};else ctx=null;say(message.error,true);lock();}
 else if(message.requestId===queryRequest?.id){queryRequest=null;say(message.error,true);lock();}
 else if(message.requestId===importRequest?.id){importRequest=null;say(message.error,true);lock();}
}
function mount(){
 if(!document.body||!supportsPanel(ctx))return;
 const anchor=document.querySelector('.bottom-right-buttons');
 if(!anchor)return; // Do not invent another floating launcher when the native slot is absent.
 if(host?.isConnected){if(host.parentElement!==anchor)anchor.append(host);if(!panel.isConnected)document.body.append(panel);return;}
 host=el('aside');host.id='sexo2-builds';host.setAttribute('aria-label','SEXO2 · builds da seleção');
 const style=el('style');style.textContent=`
 body.sexo2-builds-in-draft .rose-custom-wheel-button{display:none!important}
 #sexo2-builds{position:absolute;right:0;bottom:100%;margin-bottom:10px;z-index:10900}
 #sexo2-builds>lol-uikit-flat-button{white-space:nowrap}
 #sexo2-builds-panel{position:fixed;z-index:10901;left:50%;transform:translateX(-50%);top:100px;bottom:110px;display:flex;flex-direction:column;width:440px;max-width:calc(100vw - 48px);height:calc(100vh - 210px);max-height:600px;overflow:auto;box-sizing:border-box;background:#010a13;border:1px solid #785a28;padding:16px;color:#a09b8c;font:13px Spiegel,Arial,sans-serif;box-shadow:0 0 15px #000}
 #sexo2-builds-panel *{box-sizing:border-box}#sexo2-builds-panel[hidden]{display:none!important}
 #sexo2-builds-panel header{display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid #3c3c41;padding-bottom:10px}
 #sexo2-builds-panel h2{font:18px 'Beaufort for LOL',Georgia,serif;color:#cdbe91;margin:0;text-transform:uppercase;letter-spacing:.06em}
 #sexo2-builds-panel p{line-height:1.45;margin:6px 0}
 #sexo2-builds-panel label{display:block;margin:8px 0}
 #sexo2-builds-panel select{font:13px Spiegel,Arial,sans-serif;color:#cdbe91;background:#1e2328;border:1px solid #5b5a56;padding:6px;width:100%;margin-top:4px;border-radius:0}
 #sexo2-builds-panel .s2-build-fields{display:grid;grid-template-columns:1fr 1fr;gap:0 8px;flex:none}
 #sexo2-builds-panel .s2-build-details{overflow:auto;min-height:0;flex:1}
 #sexo2-builds-panel .s2-build-actions{display:flex;gap:8px;margin:10px 0;flex-wrap:wrap}
 #sexo2-builds-panel .s2-build-block{border-top:1px solid #1e282d;padding:8px 0}
 #sexo2-builds-panel small,#sexo2-builds-panel .s2-build-help{font-size:11px;color:#78796d}
 #sexo2-builds-panel [data-error=true]{color:#d9a796}#sexo2-builds-panel a{color:#c8aa6e}
 `;
 const launch=button('Runas e itens',()=>{opened=!opened;panel.hidden=!opened;if(opened){requestContext();schedule();}});
 launch.setAttribute('aria-label','Abrir builds do SEXO2');host.append(style,launch);
 panel=el('aside');panel.id='sexo2-builds-panel';panel.className='s2-build-panel';panel.setAttribute('aria-label','Runas e itens');panel.hidden=!opened;
 const header=el('header');header.append(el('h2','Runas e itens'),button('Fechar',close));panel.append(header);
 summary=el('p');panel.append(summary);const advanced=el('details'),filterFields=el('div');advanced.append(el('summary','Filtros e adversário'),filterFields);filterFields.className='s2-build-fields';panel.append(advanced);const fields=el('div');fields.className='s2-build-fields';panel.append(fields);
 function select(label,target=fields){const row=el('label',label),input=el('select');input.setAttribute('aria-label',label);row.append(input);target.append(row);return input;}
 position=select('Sua rota',filterFields);position.append(option('','Automática'),...Object.entries({top:'Topo',jungle:'Selva',middle:'Meio',bottom:'Atirador',support:'Suporte'}).map(([v,t])=>option(v,t)));
 tier=select('Amostra',filterFields);tier.append(option('emerald_plus','Emerald+'),option('all','Todos os elos'));
 enemy=select('Adversário',filterFields);enemy.append(option('','Geral · WR / Common'));enemy.title='Matchups disponíveis ao finalizar o draft de Summoner’s Rift.';
 for(const input of [position,tier,enemy])input.onchange=()=>{data=null;queryRequest=null;entries.replaceChildren();details.replaceChildren();lastQuery=null;lock();query(false);};
 entries=select('Sugestão');entries.onchange=()=>{renderPage();selectOverlay();};
 runeTarget=select('Página de runas no LoL');runeTarget.append(option('','Página gerenciada SEXO2'));runeTarget.onchange=()=>{runeTarget.dataset.userSelected='true';};
 const explanation=el('p','Aplicar runas substitui a página escolhida. O conteúdo anterior é preservado em backup local.');explanation.className='s2-build-help';panel.append(explanation);
 const actions=el('div');actions.className='s2-build-actions';
 queryButton=button('Consultar',()=>query(true));runesButton=button('Aplicar runas',()=>importPage('runes'));itemsButton=button('Importar itens',()=>importPage('items'));
 actions.append(queryButton,runesButton,itemsButton);panel.append(actions);
 status=el('p');status.setAttribute('role','status');panel.append(status);details=el('div');details.className='s2-build-details';panel.append(details);
 warnings=el('div');warnings.className='s2-build-help';warnings.setAttribute('aria-label','Avisos da fonte');
 const mods=button('Mods de aparência',()=>{close();window.dispatchEvent(new CustomEvent('sexo2-open-draft-mods'));});panel.append(mods);
 if(getComputedStyle(anchor).position==='static')anchor.style.position='relative';
 anchor.append(host);document.body.append(panel);document.body.classList.add('sexo2-builds-in-draft');lock();
}
function attach(){
 if(bridge||!window.__roseBridge)return;
 bridge=window.__roseBridge;
 bridge.subscribe('sexo2-build-context-data',receiveContext);bridge.subscribe('sexo2-build-data',receiveData);
 bridge.subscribe('sexo2-build-error',receiveError);bridge.subscribe('sexo2-build-imported',receiveImported);
 bridge.subscribe('phase-change',message=>{reset();contextRequest=null;pausedForGame=['GameStart','InProgress','Reconnect'].includes(message.phase);if(message.phase!=='ChampSelect'){ctx=null;unmount();}else requestContext();});
 bridge.onReady(()=>{reset();pausedForGame=false;contextRequest=null;requestContext();});
}
const tick=setInterval(()=>{
 attach();
 if(host&&!host.isConnected){unmount();reset();}
 if(supportsPanel(ctx))mount();
 if(!bridge?.ready){if(host){reset();say('Reconectando ao SEXO2…',true);}contextRequest=null;return;}
 const now=Date.now();
 // Discover late screen/phase changes even when no old carousel selector exists.
 // A slow in-game probe recovers a lost next-draft notification.
 // Only local context is read; source queries remain opt-in.
 if(now-lastContextAt>=(pausedForGame?10000:supportsPanel(ctx)?1200:5000))requestContext();
 if(!supportsPanel(ctx)&&host){unmount();reset();}
 if(contextRequest&&now-contextRequest.at>12000){contextRequest=null;reset();say('O cliente não respondeu. Tentando reconectar…',true);}
 if(queryRequest&&now-queryRequest.at>180000){queryRequest=null;say('A fonte demorou demais. Tente novamente.',true);lock();}
 if(importRequest&&now-importRequest.at>45000){importRequest=null;say('A confirmação demorou. Confira a página no cliente antes de repetir.',true);lock();}
},1500);
window.addEventListener('keydown',event=>{if(event.key==='Escape')close();});
attach();
})();
