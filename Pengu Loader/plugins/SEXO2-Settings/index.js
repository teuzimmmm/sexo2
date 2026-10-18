/** @name SEXO2-Settings @description Configurações próprias integradas ao HUD. */
(function(){
'use strict';
if(window.__sexo2Settings)return;
const CATEGORIES={skins:'Skins',maps:'Mapas',fonts:'Fontes',announcers:'Anunciadores',ui:'Interface',voiceover:'Vozes',loading_screen:'Carregamento',vfx:'Efeitos visuais',sfx:'Sons',others:'Outros'};
let bridge=null,root=null,form=null,status=null,dirty=false,pending=null,sequence=0,settings=null;
const fields={};let updateStatus=null,updateButton=null,github=null;
window.__sexo2Settings={};
function el(tag,text){const node=document.createElement(tag);if(text)node.textContent=text;return node;}
function button(text,fn){const b=el('button',text);b.type='button';b.onclick=fn;return b;}
function message(text,error=false){status.textContent=text;status.dataset.error=String(error);}
function field(key,label,type,min,max,step){
 const row=el('label');row.className='s2-setting';const title=el('span',label);const input=el('input');input.type=type;input.name=key;input.setAttribute('aria-label',label);
 if(min!=null)input.min=min;if(max!=null)input.max=max;if(step!=null)input.step=step;
 fields[key]=input;row.append(title,input);form.append(row);
 input.addEventListener('input',()=>{dirty=true;message('Alterações ainda não salvas.');});return input;
}
function build(){
 root=el('section');root.id='sexo2-settings-panel';root.setAttribute('aria-label','Configurações SEXO2');
 const style=el('style');style.textContent=`
 #sexo2-settings-panel{font:13px var(--s2-font-text);color:var(--s2-fg-2)}
 #sexo2-settings-panel h2,#sexo2-settings-panel h3{font-family:var(--s2-font-display);text-transform:uppercase;color:var(--s2-fg-2);font-weight:500;letter-spacing:.06em;margin:4px 0 14px}
 #sexo2-settings-panel h2{font-size:18px}#sexo2-settings-panel h3{font-size:13px;margin-top:18px}
 #sexo2-settings-panel .s2-setting{display:flex;align-items:center;justify-content:space-between;gap:16px;min-height:42px;border-bottom:1px solid var(--s2-line);padding:8px 0}
 #sexo2-settings-panel .s2-setting span{color:var(--s2-fg-2);max-width:68%}
 #sexo2-settings-panel input[type=number]{width:90px;text-align:right}
 #sexo2-settings-panel input[type=text]{width:100%;font-size:12px;margin-top:6px}
 #sexo2-settings-panel input[type=checkbox]{accent-color:var(--s2-fg)}
 #sexo2-settings-panel .s2-path{display:block}#sexo2-settings-panel .s2-path span{max-width:none}
 #sexo2-settings-panel .s2-help{font-size:11px;line-height:1.5;color:var(--s2-fg-3);margin:8px 0 12px}
 #sexo2-settings-panel .s2-actions{display:flex;gap:8px;margin-top:12px;flex-wrap:wrap}
 #sexo2-settings-panel [role=status]{font-size:12px;line-height:1.5;min-height:20px;margin:10px 0;color:var(--s2-fg-2)}
 #sexo2-settings-panel [data-error=true]{color:#d9a796}
 #sexo2-settings-panel details{border-top:1px solid var(--s2-line);margin-top:16px;padding-top:12px;font-size:11px}
 #sexo2-settings-panel a{color:var(--s2-fg)}#sexo2-settings-panel summary{cursor:pointer}
 `;root.append(style,el('h2','Configurações'));
 form=el('form');form.noValidate=true;root.append(form);
 field('threshold','Espera após o fim da seleção (s)','number',.3,2,.05);
 field('monitorAutoResumeTimeout','Limite de pausa do jogo (s)','number',20,180,1);
 form.append(el('p','s2'));form.lastChild.className='s2-help';form.lastChild.textContent='A pausa dá tempo para preparar as skins. Ao atingir o limite, o aplicativo tenta liberar o jogo.';
 field('autostart','Iniciar com Windows','checkbox');field('hideEmptyCategories','Ocultar categorias de mods vazias','checkbox');
 form.append(el('h3','Overlays'));field('goldOverlay','Ouro no placar (Tab)','checkbox');field('augmentsOverlay','Aprimoramentos na Arena e no Mayhem','checkbox');
 const overlayHelp=el('p','O jogo precisa estar em tela sem bordas.');overlayHelp.className='s2-help';form.append(overlayHelp);
 const path=field('gamePath','Pasta do LoL (Game)','text');path.placeholder='Automática';path.parentElement.classList.add('s2-path');
 const help=el('p','Deixe em branco para usar a detecção automática.');help.className='s2-help';form.append(help);
 const language=el('label');language.className='s2-setting';language.append(el('span','Idioma dos menus'));
 const select=el('select');select.setAttribute('aria-label','Idioma dos menus');
 const languages={auto:'Automático (cliente)',...(window.RoseI18n?.languages||{pt_BR:'Português',en:'English'})};
 for(const [value,name] of Object.entries(languages)){const option=el('option',name);option.value=value;select.append(option);}select.value=window.RoseI18n?.setting||'auto';
 select.onchange=()=>bridge?.send({type:'language-save',language:select.value});language.append(select);form.append(language);
 status=el('p','Conectando ao aplicativo…');status.setAttribute('role','status');form.append(status);
 const actions=el('div');actions.className='s2-actions';const save=button('Salvar alterações',saveSettings);save.id='sexo2-settings-save';actions.append(save,button('Descartar alterações',()=>{dirty=false;if(settings)populate(settings);message('Alterações descartadas.');}));form.append(actions);
 form.addEventListener('submit',e=>{e.preventDefault();saveSettings();});
 root.append(el('h3','Mods personalizados'));const tools=el('div');tools.className='s2-actions';const libraryHost=el('div');
 let configHidden=[];
 function openLibrary(){root.dataset.libraryOpen='true';const subnav=root.closest('#rose-hub-content')?.querySelector('.hub-subnav');if(subnav)subnav.hidden=true;configHidden=[...root.children].filter(node=>node!==libraryHost&&node.tagName!=='STYLE').map(node=>[node,node.hidden]);for(const[node]of configHidden)node.hidden=true;libraryHost.hidden=false;window.dispatchEvent(new CustomEvent('sexo2-mod-library-open',{detail:{target:libraryHost,category:'all',add:false}}));}
 window.addEventListener('sexo2-mod-library-close',()=>{for(const[node,hidden]of configHidden)node.hidden=hidden;configHidden=[];delete root.dataset.libraryOpen;const subnav=root.closest('#rose-hub-content')?.querySelector('.hub-subnav');if(subnav)subnav.hidden=false;libraryHost.hidden=true;});
 tools.append(button('Biblioteca de mods',openLibrary),button('Diagnóstico detalhado',()=>window.dispatchEvent(new CustomEvent('sexo2-settings-tool',{detail:{action:'diagnostics',category:'skins'}}))));root.append(tools,libraryHost);
 root.append(el('h3','Atualizações'));updateStatus=el('p','Verificando atualizações…');updateStatus.setAttribute('role','status');root.append(updateStatus);
 const updates=el('div');updates.className='s2-actions';updates.append(button('Verificar atualização',()=>checkUpdate()));
 updateButton=button('Atualizar',()=>bridge?.send({type:'sexo2-update-open'}));updateButton.disabled=true;updates.append(updateButton);
 github=el('a','Abrir GitHub do projeto');github.target='_blank';github.rel='noopener noreferrer';github.setAttribute('aria-disabled','true');updates.append(github);root.append(updates);
 const credits=el('details');credits.append(el('summary','Créditos da base'));const note=el('p','SEXO2 utiliza componentes de Rose, Pengu Loader e LTK. BORK pertence à Riot Games; o escudo pertence ao Clube Atlético Mineiro.');credits.append(note);const link=el('a','Código e licença da base Rose');link.href='https://github.com/Alban1911/Rose';link.target='_blank';link.rel='noopener noreferrer';credits.append(link);root.append(credits);
}
function populate(data){settings=data;if(dirty||pending?.saving)return;for(const[key,input]of Object.entries(fields)){if(input.type==='checkbox')input.checked=data[key]===true;else input.value=data[key]??'';}}
function lock(value){for(const input of form.querySelectorAll('input,button'))input.disabled=value;}
function request(){if(!bridge?.ready||pending)return;pending={id:'s2-settings-'+(++sequence),saving:false,at:Date.now()};bridge.send({type:'settings-request',requestId:pending.id});}
function saveSettings(){
 if(!bridge?.ready){message('O aplicativo está desconectado. Suas alterações foram mantidas.',true);return;}
 if(pending){message('Aguarde a confirmação anterior.');return;}
 if(!form.reportValidity())return;
 const values={threshold:Number(fields.threshold.value),monitorAutoResumeTimeout:Number(fields.monitorAutoResumeTimeout.value),autostart:fields.autostart.checked,hideEmptyCategories:fields.hideEmptyCategories.checked,goldOverlay:fields.goldOverlay.checked,augmentsOverlay:fields.augmentsOverlay.checked,gamePath:fields.gamePath.value.trim()};
 pending={id:'s2-settings-'+(++sequence),saving:true,at:Date.now()};lock(true);message('Salvando…');bridge.send({type:'settings-save',requestId:pending.id,...values});
}
function checkUpdate(){if(bridge?.ready){updateStatus.textContent='Verificando atualizações…';bridge.send({type:'sexo2-update-request',requestId:'s2-update-'+(++sequence)});}}
function updateReceived(data){
 updateStatus.textContent=data.message||'';updateButton.disabled=!data.available;
 if(data.github&&/^https:\/\/github\.com\/[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+$/.test(data.github)){github.href=data.github;github.removeAttribute('aria-disabled');}
 for(const item of document.querySelectorAll('.menu_item_Golden.Rose')){item.toggleAttribute('data-sexo2-update',data.available===true);item.title=data.available?'SEXO2: atualização disponível':'SEXO2';}
}
function receive(data){
 if(!pending||data.requestId!==pending.id)return;const saving=pending.saving;pending=null;lock(false);
 if(data.error||data.success===false){message(data.error||'Não foi possível salvar. Suas alterações foram mantidas.',true);return;}
 if(saving){dirty=false;populate(data.settings);message('Configurações salvas.');}
 else{populate(data);if(!dirty)message('');}
}
window.addEventListener('rose-hub-settings',e=>{if(!root)build();root.hidden=false;e.detail.target.append(root);if(root.dataset.libraryOpen==='true'){const subnav=root.closest('#rose-hub-content')?.querySelector('.hub-subnav');if(subnav)subnav.hidden=true;}request();});
window.addEventListener('rose-hub-settings-close',()=>{if(root)root.hidden=true;});
const timer=setInterval(()=>{if(!root)build();if(!bridge&&window.__roseBridge){bridge=window.__roseBridge;bridge.subscribe('settings-data',receive);bridge.subscribe('settings-saved',receive);bridge.subscribe('sexo2-update-state',updateReceived);bridge.onReady(()=>{pending=null;lock(false);request();checkUpdate();});clearInterval(timer);}},100);
setInterval(()=>{if(pending&&Date.now()-pending.at>15000){pending=null;lock(false);message('Não houve confirmação. Confira a conexão; suas alterações foram mantidas.',true);}},1000);
})();
