/** @name ROSE-Hub @description Single native navigation entry for all Rose tools. */
(function(){
 'use strict';
 function start(){
  if(!document.body||!document.head){setTimeout(start,100);return;}
  if(window.__roseHub)return;
  const css=document.createElement('style');css.textContent=`
  #rose-amigos-launch,#rose-party-button,#rose-party-lobby-button,#rose-party-champ-status,.rsp-launch{display:none!important}
  #rose-hub{position:fixed;z-index:11000;width:min(820px,calc(100vw - 24px));max-height:calc(100vh - 100px);color:#f0e6d2;background:#09141b;border:1px solid #463e2f;font:13px Inter,'Segoe UI',sans-serif;box-shadow:0 8px 22px #0007}
  #rose-hub,#rose-hub *{border-radius:0!important}#rose-hub .s2-chroma-dot{border-radius:50%!important}
  #rose-hub>header{display:flex;align-items:center;justify-content:space-between;padding:8px 8px 0 14px}#rose-hub .hub-brand{font:600 20px Oswald,'Segoe UI',sans-serif;letter-spacing:.08em;color:#f0e6d2}
  #rose-hub[hidden],#rose-hub [hidden]{display:none!important}#rose-hub *{box-sizing:border-box}
  .menu_item_Golden.Rose[data-sexo2-update] .menu-item-icon-wrapper::after{content:'';position:absolute;width:5px;height:5px;background:#c8aa6e;border-radius:50%;right:0;top:0}
  #rose-hub>nav{display:flex;border-bottom:1px solid #36474b;padding:6px;gap:2px}
  #rose-hub button,#rose-hub select,#rose-hub input{font:inherit;color:#f0e6d2;background:#15232b;border:1px solid #463e2f;border-radius:0;padding:7px;max-width:100%}
  #rose-hub button{cursor:pointer}#rose-hub button:disabled{opacity:.45;cursor:default}#rose-hub button:hover{border-color:#cdbe91}
  #rose-hub>nav button{border:0;background:transparent;flex:1}#rose-hub>nav .active{border-bottom:2px solid #c8aa6e}#rose-hub>header .hub-close{border:0;background:transparent;font-size:20px;line-height:1;padding:4px 10px}
  #rose-hub-content{overflow:auto;max-height:calc(100vh - 155px);padding:10px}
  #rose-hub-content .hub-subnav{display:flex;gap:5px;margin-bottom:10px}
  #rose-hub-content #rose-amigos-panel,#rose-hub-content #rose-swiftplay-pins,#rose-hub-content #rose-party-panel,#rose-hub-content #rose-settings-panel{position:static!important;inset:auto!important;transform:none!important;width:100%!important;max-height:none!important;height:auto!important;border:0!important;border-radius:0!important;background:transparent!important;padding:0!important;box-shadow:none!important;opacity:1!important;pointer-events:auto!important;display:block}
  #rose-hub-content #rose-amigos-panel>header,#rose-hub-content #rose-amigos-panel>.ra-tabs,#rose-hub-content #rose-amigos-panel>header+p,#rose-hub-content .rsp-close,#rose-hub-content .party-close-btn,#rose-hub-content .party-header,#rose-hub-content .party-description,#rose-hub-content .s3xo-room-badge{display:none!important}
  #rose-hub-content .rsp-panel{margin:0;padding:0;border:0;background:transparent;border-radius:0;box-shadow:none;max-height:none;overflow:visible}
  #rose-hub-content .rsp-panel header{display:none}#rose-hub-content .rsp-grid{max-height:220px}
  #rose-hub-content .ra-card{border-radius:0;padding:8px;margin:6px 0}#rose-hub-content .party-content{padding:0!important}
  #rose-hub-content #rose-settings-panel>div:first-child{display:none!important}
  #rose-hub-content #rose-settings-flyout{position:static!important;inset:auto!important;transform:none!important;width:100%!important;max-width:100%!important;opacity:1!important;overflow:visible!important;margin:0!important}
  #rose-hub-content .settings-title{display:none!important}#rose-amigos-backdrop{display:none!important}
  #rose-hub #rose-hub-content [hidden]{display:none!important}
  .lu-random-dice-button{display:none!important}
  #rose-hub-content button,#rose-hub-content input,#rose-hub-content select{border-radius:0!important;background:#15232b!important;color:#f0e6d2!important;border-color:#6e644b!important}
  #rose-hub-content #rose-settings-flyout{font:13px Inter,'Segoe UI',sans-serif!important}
  #rose-hub #rose-settings-flyout{min-width:0!important;align-items:stretch!important}
  #rose-hub #rose-settings-flyout .sexo2-settings-content{display:block!important;width:100%!important;min-width:0!important;max-width:100%!important;background:transparent!important;border:0!important;padding:0!important;box-shadow:none!important}
  #rose-hub #rose-settings-flyout .sexo2-settings-content>div{min-width:0;max-width:100%;overflow-wrap:anywhere}
  #rose-hub-content #rose-settings-flyout .settings-section{width:100%!important;padding:8px 0!important;margin:0!important;border-bottom:1px solid #25343d}
  #rose-hub-content #rose-settings-flyout details{width:100%;font-size:11px;color:#a0adb5;margin-top:12px}
  #rose-hub input[type=checkbox]{appearance:auto!important;-webkit-appearance:checkbox!important;accent-color:#c8aa6e;width:16px!important;height:16px!important;padding:0!important;flex:none;cursor:pointer}
  `;document.head.append(css);
  const panel=document.createElement('section');panel.id='rose-hub';panel.hidden=true;panel.setAttribute('role','dialog');panel.setAttribute('aria-label','SEXO2');
  const fontFace=document.createElement('style');const fontBase='http://127.0.0.1:'+(window.__roseBridge?.port||50000)+'/asset/fonts/';
  fontFace.textContent=`@font-face{font-family:Oswald;font-weight:200 700;font-display:swap;src:url(${fontBase}oswald-latin-wght-normal.woff2) format('woff2')}@font-face{font-family:Inter;font-weight:100 900;font-display:swap;src:url(${fontBase}inter-latin-wght-normal.woff2) format('woff2')}`;document.head.append(fontFace);
  const head=document.createElement('header'),brand=document.createElement('span');brand.className='hub-brand';brand.textContent='SEXO2';head.append(brand);
  const nav=document.createElement('nav'),content=document.createElement('div');content.id='rose-hub-content';panel.append(head,nav,content);document.body.append(panel);
  let current='Sala',anchor=null,phase=null,swift=false;const containers={};
  function dispatch(type,detail){window.dispatchEvent(new CustomEvent(type,{detail}));}
  function hide(){panel.hidden=true;}
  function position(){const rect=anchor?.getBoundingClientRect();if(!rect)return;panel.style.top=Math.min(rect.bottom+8,window.innerHeight-120)+'px';panel.style.left=Math.max(12,Math.min(rect.right-panel.offsetWidth,window.innerWidth-panel.offsetWidth-12))+'px';}
  function createButton(text,fn){const b=document.createElement('button');b.textContent=text;b.type='button';b.onclick=fn;return b;}
  const x=createButton('×',hide);x.className='hub-close';x.setAttribute('aria-label','Fechar painel');head.append(x);
  function mount(){
   nav.replaceChildren();for(const label of ['Sala','Favoritas','Configurações','Suporte',...(swift?['Swiftplay']:[])]){const b=createButton(label,()=>{current=label;mount();});if(current===label)b.className='active';nav.append(b);}
   for(const node of Object.values(containers))node.hidden=true;
   if(!containers[current]){containers[current]=document.createElement('div');content.append(containers[current]);}
   const target=containers[current];target.hidden=false;
   if(current==='Sala'){
    dispatch('rose-hub-friends',{target,tab:'Sala'});
    const legacyParty=document.getElementById('rose-party-panel');if(legacyParty)legacyParty.hidden=true;
   }else if(current==='Favoritas'){
    dispatch('rose-hub-friends',{target,tab:'Favoritas'});
   }else if(current==='Swiftplay'){
    dispatch('rose-hub-swiftplay',{target});
   }else if(current==='Suporte'){
    dispatch('rose-hub-settings-close');dispatch('rose-hub-friends',{target,tab:'Preparo'});
   }else showSettings(target);
   position();
  }
  function showSettings(target){const friends=document.getElementById('rose-amigos-panel');if(friends&&target.contains(friends))friends.hidden=true;dispatch('rose-hub-settings',{target,anchor});}
  window.__roseHub={open(navItem){anchor=navItem;if(phase==='InProgress')return;panel.hidden=!panel.hidden;if(!panel.hidden){current='Sala';mount();}},close:hide,show(label){anchor=anchor||document.querySelector('lol-uikit-navigation-item.menu_item_Golden.Rose');if(phase==='InProgress')return;current=label;panel.hidden=false;mount();},refreshSettings(){if(current==='Configurações'&&containers[current])showSettings(containers[current]);}};
  window.addEventListener('rose-open-settings',e=>{e.stopImmediatePropagation();window.__roseHub.open(e.detail?.navItem||document.querySelector('lol-uikit-navigation-item.menu_item_Golden.Rose'));},true);
  window.addEventListener('rose-swiftplay-state',e=>{const active=e.detail?.active===true;if(active===swift)return;swift=active;if(!swift&&current==='Swiftplay')current='Sala';if(!panel.hidden)mount();});
  window.addEventListener('resize',position);
  document.addEventListener('pointerdown',e=>{if(!panel.hidden&&!panel.contains(e.target)&&!anchor?.contains(e.target)&&!e.target.closest('lol-uikit-dialog,.chroma-view,[id$="-flyout"],[id$="-dialog"]'))hide();});
  document.addEventListener('keydown',e=>{if(e.key==='Escape')hide();});
  document.addEventListener('click',e=>{if(e.target.closest('.skin-selection-item')&&!e.target.closest('.lu-random-dice-button,.chroma-button'))window.__roseBridge?.send({type:'manual-skin-choice'});},true);
  let attached=false;
  setInterval(()=>{if(!panel.isConnected)document.body.append(panel);const bridge=window.__roseBridge;if(bridge&&!attached){attached=true;bridge.subscribe('phase-change',data=>{phase=data.phase;if(phase==='InProgress')hide();});}if(!panel.hidden)position();},1000);
 }
 if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else start();
})();
