/** @name SEXO2-Skins @description Preparo, perfis, sorteio coordenado, sala e diagnóstico. */
(function(){
  'use strict';
  function memberStatus(m){
    if(!m.connected)return 'Desconectado';
    if(!m.sameLobby)return 'Em outro lobby';
    if(!m.supportsTools)return 'Atualize o SEXO2 deste participante';
    if(m.ready===true)return m.skinReceived?'Pronto · escolha recebida':'Pronto';
    return 'Preparando';
  }
  function profileSelections(champions,draft){
    const result={};for(const c of champions||[]){const sid=draft[c.championId]??c.selectedSkinId;const skin=c.skins.find(s=>s.skinId===Number(sid));if(skin)result[c.championId]={skinId:skin.skinId,name:skin.name};}return result;
  }
  if(typeof window==='undefined'&&typeof module!=='undefined'&&module.exports){module.exports={memberStatus,profileSelections};return;}
  function start(){
    if(!document.body||!document.head){setTimeout(start,100);return;}
    if(window.__roseAmigosLoaded)return;window.__roseAmigosLoaded=true;
    const style=document.createElement('style');style.textContent=`
#rose-amigos-launch{position:fixed;left:2.5%;bottom:65px;z-index:10002;padding:9px 14px;background:#071d25;color:#f0e6d2;border:1px solid #c89b3c;border-radius:5px;font:13px Arial;cursor:pointer}
#rose-amigos-backdrop{position:fixed;inset:0;z-index:10009;background:#0008}#rose-amigos-backdrop[hidden]{display:none!important}
#rose-amigos-panel{position:fixed;left:50%;top:50%;transform:translate(-50%,-50%);z-index:10010;width:min(840px,88vw);max-height:82vh;overflow:auto;background:#07151d;color:#f0e6d2;border:1px solid #c89b3c;border-radius:10px;padding:20px;box-shadow:0 15px 50px #000a;font:13px Arial,sans-serif}
#rose-amigos-panel[hidden],#rose-amigos-launch[hidden]{display:none!important}#rose-amigos-panel *{box-sizing:border-box}
#rose-amigos-panel h2{font:21px Georgia;margin:0}#rose-amigos-panel h3{font:16px Georgia;margin:14px 0 8px}#rose-amigos-panel button,#rose-amigos-panel input,#rose-amigos-panel select{font:inherit;border:1px solid #725f32;border-radius:4px;color:#f0e6d2;background:#10252e;padding:8px;margin:3px}
#rose-amigos-panel button{cursor:pointer}#rose-amigos-panel button:hover{border-color:#d8b764}#rose-amigos-panel button:disabled{opacity:.45;cursor:default}#rose-amigos-panel input[type=checkbox]{width:16px;height:16px;vertical-align:middle}
#rose-amigos-panel .fav-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(96px,1fr));gap:6px;max-height:340px;overflow:auto}#rose-amigos-panel .fav-champ{display:flex;flex-direction:column;align-items:center;gap:4px;font-size:11px;margin:0;padding:6px}#rose-amigos-panel .fav-portrait{width:48px;height:48px;object-fit:cover;background:#0c2834}#rose-amigos-panel .fav-hits{max-height:160px;overflow:auto}#rose-amigos-panel .fav-hit{display:block;width:100%;text-align:left}#rose-amigos-panel .fav-skins{max-height:380px;overflow:auto}#rose-amigos-panel .fav-skin{border-bottom:1px solid #25343d;padding:4px 0}#rose-amigos-panel .fav-skin>.ra-row{cursor:pointer}#rose-amigos-panel .fav-open{background:#10252e}#rose-amigos-panel .fav-tile{width:72px;height:42px;object-fit:cover;background:#0c2834}#rose-amigos-panel .fav-chroma{padding:4px 0 4px 24px}#rose-amigos-panel .fav-dot{width:22px;height:22px;object-fit:cover;border-radius:50%}#rose-amigos-panel button.fav-on,#rose-amigos-panel button[aria-pressed=true]{border-color:#c8aa6e;color:#c8aa6e}
#rose-amigos-panel .ra-row{display:flex;align-items:center;flex-wrap:wrap;gap:8px}#rose-amigos-panel .ra-between{justify-content:space-between}#rose-amigos-panel .ra-muted{color:#a8aaa2;font-size:12px;line-height:1.5}#rose-amigos-panel .ra-card{padding:12px;margin:8px 0;border:1px solid #36474b;border-radius:6px}#rose-amigos-panel .ra-ok{color:#7bd5a7}#rose-amigos-panel .ra-error{color:#f3a090}#rose-amigos-panel .ra-tabs{margin:14px 0;border-bottom:1px solid #534a30;padding-bottom:10px}#rose-amigos-panel .ra-active{border-color:#c89b3c;background:#29413d}#rose-amigos-panel .ra-notice{white-space:pre-wrap;padding:9px;border-left:3px solid #c89b3c;color:#e4d3a2}#rose-amigos-panel .ra-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px}#rose-amigos-panel .ra-skins{max-height:190px;overflow:auto}#rose-amigos-panel footer{margin-top:16px;border-top:1px solid #4c4430;padding-top:10px}#rose-amigos-panel select{max-width:100%}
`;document.head.appendChild(style);
    const launch=document.createElement('button');launch.id='rose-amigos-launch';launch.textContent='SEXO2 · verificar';document.body.appendChild(launch);
    const panel=document.createElement('section');panel.id='rose-amigos-panel';panel.hidden=true;panel.setAttribute('role','dialog');panel.setAttribute('aria-label','SEXO2');document.body.appendChild(panel);
    const backdrop=document.createElement('div');backdrop.id='rose-amigos-backdrop';backdrop.hidden=true;document.body.appendChild(backdrop);
    function close(){panel.hidden=true;backdrop.hidden=true;if(window.__roseHub)window.__roseHub.close();else launch.focus();}
    backdrop.onclick=close;
    let bridge=null,state=null,pending=null,sequence=0,tab='Preparo',nameDraft='',skinDraft={},theme='Qualquer',phase=null,notice='',search='',lastSeen=0,roomDraft='',lastRender='';
    let championSearch='',skinSearch='',favChampion=null,favSkin=null,skinIndex=null,skinIndexAsked=false,skinIndexFailed=false,libraryLoaded=false,favoriteQueue=[],favoriteDraft={},transportNotice=false;
    window.addEventListener('rose-hub-friends',e=>{tab=e.detail.tab;e.detail.target.appendChild(panel);panel.hidden=false;backdrop.hidden=true;request();render();});
    const prefix='amigos-r5-'+Date.now()+'-'+Math.random().toString(36).slice(2);
    function node(tag,text,cls){const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(cls)n.className=cls;return n;}
    function button(text,fn,disabled=false){const n=node('button',text);n.type='button';n.disabled=disabled;n.onclick=fn;return n;}
    function request(action='snapshot',extra={}){
      if(!bridge||!bridge.ready)return;
      if(action==='favorite')favoriteDraft[extra.championId+':'+extra.skinId]=extra.enabled;
      if(pending&&action==='favorite'){favoriteQueue.push(extra);notice='Salvando favoritas…';render();return;}
      if(pending){if(action==='snapshot')return;notice='Aguarde a confirmação da operação atual.';render();return;}
      const id=prefix+'-'+(++sequence);pending={id,action,extra,since:Date.now()};bridge.send({type:'friends-request',action,requestId:id,...extra});
      if(action!=='snapshot'){notice='Confirmando…';render();}
    }
    function online(){return !!bridge?.ready&&Date.now()-lastSeen<12000;}
    function assetPath(path){return typeof path==='string'&&path.startsWith('/lol-game-data/assets/')?path:null;}
    function image(path,cls){const img=node('img');img.className=cls||'';img.alt='';img.loading='lazy';const src=assetPath(path);if(src)img.src=src;img.addEventListener('error',()=>img.removeAttribute('src'));return img;}
    function plain(text){return String(text).normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();}
    function isFavorite(championId,skinId){return favoriteDraft[championId+':'+skinId]??(state.favorites?.[championId]||[]).includes(skinId);}
    function favoriteButton(championId,skin){const on=isFavorite(championId,skin.skinId);const b=button('Favoritar',e=>{e.stopPropagation();request('favorite',{championId,skinId:skin.skinId,enabled:!on});});b.setAttribute('aria-pressed',String(on));b.setAttribute('aria-label','Favoritar '+skin.name);b.className=on?'fav-on':'';return b;}
    function openChampion(championId,skinId){favChampion=championId;favSkin=skinId||null;skinSearch='';request('library-open',{championId});}
    function renderFavorites(){
      const query=plain(championSearch);
      const search=node('input');search.type='search';search.placeholder='Buscar campeão ou skin';search.value=championSearch;search.setAttribute('aria-label','Buscar campeão ou skin');
      search.oninput=()=>{championSearch=search.value;favChampion=null;render();};
      panel.append(search);
      const champions=state.libraryChampions||[];
      if(favChampion===null||query){
        if(!champions.length){panel.append(node('p','Carregando campeões…','ra-muted'),button('Carregar campeões',()=>request('library-list')));return;}
        const grid=node('div',undefined,'ra-skins fav-grid');
        for(const c of champions.filter(c=>!query||plain(c.name).includes(query))){const b=button('',()=>openChampion(c.championId));b.className='fav-champ';b.append(image(c.portrait,'fav-portrait'),node('span',c.name));b.setAttribute('aria-label',c.name);grid.append(b);}
        if(!grid.childElementCount&&!query)grid.append(node('p','Nenhum campeão encontrado.','ra-muted'));
        panel.append(grid);
        if(query.length>=2){
          const hits=(skinIndex||[]).filter(([,name])=>plain(name).includes(query)).slice(0,40);
          if(hits.length){panel.append(node('h3','Skins'));const list=node('div',undefined,'ra-skins fav-hits');for(const [sid,name] of hits){const champion=champions.find(c=>c.championId===Math.floor(sid/1000));const b=button('',()=>{championSearch='';openChampion(Math.floor(sid/1000),sid);});b.className='fav-hit';b.setAttribute('aria-label',name);b.append(node('strong',name),node('span',champion?champion.name:'','ra-muted'));list.append(b);}panel.append(list);}
          else if(!skinIndex)panel.append(node('p',skinIndexFailed?'A busca por skin não carregou.':'Carregando a busca por skin…','ra-muted'),skinIndexFailed?button('Tentar novamente',()=>{skinIndexFailed=false;request('skin-index');}):node('span'));
        }
        return;
      }
      const chosen=state.browseChampion;
      const back=button('← Campeões',()=>{favChampion=null;favSkin=null;render();});panel.append(back);
      if(!chosen||chosen.championId!==favChampion){panel.append(node('p','Carregando skins…','ra-muted'));return;}
      panel.append(node('h3',chosen.name));
      const filter=node('input');filter.type='search';filter.placeholder='Buscar skin de '+chosen.name;filter.value=skinSearch;filter.setAttribute('aria-label','Buscar skin favorita');panel.append(filter);
      const list=node('div',undefined,'ra-skins fav-skins');panel.append(list);
      const chromas={};for(const s of chosen.skins)if(s.chroma)(chromas[s.baseSkinId]??=[]).push(s);
      function drawSkins(){list.replaceChildren();const term=plain(skinSearch);
        for(const s of chosen.skins.filter(s=>s.skinId%1000!==0&&!s.chroma&&plain(s.name).includes(term))){
          const open=favSkin===s.skinId,row=node('div',undefined,'fav-skin'+(open?' fav-open':''));
          const head=node('div',undefined,'ra-row ra-between');head.tabIndex=0;head.setAttribute('role','button');head.setAttribute('aria-expanded',String(open));head.setAttribute('aria-label',s.name);
          const toggle=()=>{favSkin=open?null:s.skinId;drawSkins();};head.onclick=toggle;head.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();toggle();}};
          const left=node('div',undefined,'ra-row');left.append(image(s.tilePath,'fav-tile'),node('span',s.name));head.append(left,favoriteButton(chosen.championId,s));row.append(head);
          if(open)for(const c of chromas[s.skinId]||[]){const line=node('div',undefined,'ra-row ra-between fav-chroma');const l=node('div',undefined,'ra-row');const dot=image(c.tilePath,'fav-dot s2-chroma-dot');l.append(dot,node('span',c.name.split(' · ').pop()));line.append(l,favoriteButton(chosen.championId,c));row.append(line);}
          list.append(row);}
        if(!list.childElementCount)list.append(node('p','Nenhuma skin encontrada.','ra-muted'));}
      filter.oninput=()=>{skinSearch=filter.value;drawSkins();};drawSkins();
    }
    function render(){
      const scrollParent=panel.closest('#rose-hub-content');const parentScroll=scrollParent?.scrollTop||0;
      const scrolls=[panel,...panel.querySelectorAll('.ra-skins')].map(n=>n.scrollTop);
      const active=document.activeElement;const focused=panel.contains(active)?active.getAttribute('aria-label'):null;
      const selection=active?.selectionStart;
      panel.replaceChildren();
      const header=node('header',undefined,'ra-row ra-between');header.append(node('h2','Ferramentas'),button('Fechar',close));panel.append(header);
      panel.append(node('p','Perfis e sorteios alteram apenas as suas escolhas. O preparo não confirma a aplicação dentro da partida.','ra-muted'));
      const tabs=node('nav',undefined,'ra-tabs');for(const t of ['Preparo','Perfis','Sorteio','Sala']){const b=button(t,()=>{tab=t;render();});if(tab===t)b.className='ra-active';tabs.append(b);}panel.append(tabs);
      if(notice)panel.append(node('div',notice,'ra-notice'));
      if(!state){panel.append(node('p','Aguardando resposta do SEXO2…'));return;}
      if(state.preferenceError)panel.append(node('p',state.preferenceError,'ra-error'));
      if(state.preferenceError)panel.append(button('Restaurar backup das preferências',()=>{if(window.confirm('Restaurar o backup? O arquivo atual será preservado.'))request('restore-preferences');}));
      if(tab==='Favoritas')renderFavorites();
      if(tab==='Automático'){
        panel.append(node('h3','Skin automática'));
        const mode=node('select');mode.setAttribute('aria-label','Skin automática');
        for(const [value,label] of [['off','Desligada'],['favorite','Minha favorita'],['random','Aleatória'],['favorites','Entre favoritas']]){const option=node('option',label);option.value=value;mode.append(option);}
        mode.value=state.automatic||'off';mode.onchange=()=>request('automatic',{mode:mode.value});panel.append(mode,button('Sortear agora',()=>request('random-now'),!state.editable),node('p','Entre favoritas usa uma aleatória disponível quando não houver favoritas para o campeão.','ra-muted'));
        if(state.manualChoice)panel.append(node('p','Sua escolha manual está preservada nesta seleção.','ra-ok'));
        const list=node('div',undefined,'ra-skins');
        for(const c of state.champions){list.append(node('strong',c.name));for(const s of c.skins){if(s.skinId%1000===0)continue;const row=node('div',undefined,'ra-row');const cb=node('input');cb.type='checkbox';cb.checked=(state.favorites?.[c.championId]||[]).includes(s.skinId);cb.setAttribute('aria-label','Favorita '+s.name);cb.onchange=()=>request('favorite',{championId:c.championId,skinId:s.skinId,enabled:cb.checked});row.append(cb,node('span',s.name+(s.available?'':' · arquivo ausente')),button('Usar',()=>request('use-skin',{championId:c.championId,skinId:s.skinId}),!state.editable||!s.available));list.append(row);}}
        panel.append(list);if(!state.champions.length)panel.append(node('p','Escolha um campeão para editar suas favoritas.','ra-muted'));
      }
      if(tab==='Preparo'){
        const label=node('label',undefined,'ra-row');const accept=node('input');accept.type='checkbox';accept.checked=state.autoAccept===true;accept.onchange=()=>request('auto-accept',{enabled:accept.checked});label.append(accept,node('span','Aceitar partidas automaticamente'));panel.append(label,node('p','Desligado por padrão. Aceita apenas a confirmação de partida; não inicia a busca.','ra-muted'));
        panel.append(node('h3',online()?state.readiness.title:'Sem resposta do SEXO2'));
        for(const check of state.readiness.checks){const card=node('div',undefined,'ra-card');card.append(node('strong',(check.status==='ok'?'✓ ':check.status==='waiting'?'… ':'! ')+check.title,check.status==='ok'?'ra-ok':'ra-error'),node('p',check.detail,'ra-muted'));panel.append(card);}
        panel.append(button('Conferir novamente',()=>request('check')));
      }
      if(tab==='Perfis'){
        panel.append(node('p','Salve um conjunto por campeão. O perfil ativo usa sua escolha quando o campeão estiver confirmado; no Swiftplay, usa os dois slots.','ra-muted'));
        const profiles=state.profiles||{};
        for(const [name,picks]of Object.entries(profiles)){const row=node('div',undefined,'ra-card ra-row ra-between');row.append(node('strong',name+(state.activeProfile===name?' · ativo':'')),node('span',Object.keys(picks).length+' campeões','ra-muted'),button('Usar perfil',()=>request('apply-profile',{name}),!online()),button('Excluir',()=>{if(window.confirm('Excluir o perfil “'+name+'”?'))request('delete-profile',{name});}));panel.append(row);}
        panel.append(node('h3','Salvar conjunto'));
        const input=node('input');input.placeholder='Nome: favoritas, Arcane, grupo…';input.maxLength=50;input.value=nameDraft;input.oninput=()=>nameDraft=input.value;input.setAttribute('aria-label','Nome do perfil');panel.append(input);
        for(const c of state.champions){const row=node('div',undefined,'ra-card');row.append(node('strong',c.name));const select=node('select');select.setAttribute('aria-label','Skin de '+c.name);for(const skin of c.skins){const option=node('option',skin.name);option.value=skin.skinId;select.append(option);}select.value=skinDraft[c.championId]??c.selectedSkinId;select.onchange=()=>skinDraft[c.championId]=Number(select.value);row.append(select);panel.append(row);}
        panel.append(button('Salvar escolhas no perfil',()=>request('save-profile',{name:nameDraft,selections:profileSelections(state.champions,skinDraft)})),button('Desligar perfil automático',()=>request('release')));
      }
      if(tab==='Sorteio'){
        panel.append(node('p','Entrar no sorteio desliga o perfil automático. Quem inicia escolhe a temática; cada participante sorteia uma skin disponível para seus próprios campeões.','ra-muted'));
        const row=node('div',undefined,'ra-row');const themes=node('select');themes.setAttribute('aria-label','Temática do sorteio');for(const t of state.themes){const o=node('option',t);o.value=t;themes.append(o);}themes.value=theme;themes.onchange=()=>theme=themes.value;row.append(themes,button(state.lotteryOptin?'Sair do sorteio':'Entrar no sorteio',()=>request('lottery-optin',{enabled:!state.lotteryOptin})),button('Sortear grupo',()=>request('lottery-start',{theme}),!state.editable||state.readiness.checks.find(c=>c.id==='server')?.status!=='ok'),button('Sortear só para mim',()=>request('lottery-local',{theme}),!state.editable));panel.append(row);
        if(state.drawResult){const result=state.drawResult;panel.append(node('p',result.success?'Sorteio: '+Object.values(result.choices).map(s=>s.name).join(' · '):result.error,result.success?'ra-ok':'ra-error'));}
        panel.append(node('h3','Excluir skins indesejadas'));
        const filter=node('input');filter.placeholder='Pesquisar skins';filter.value=search;filter.oninput=()=>{search=filter.value;drawExclusions();};panel.append(filter);
        const list=node('div',undefined,'ra-skins');panel.append(list);
        function drawExclusions(){list.replaceChildren();for(const c of state.champions){list.append(node('strong',c.name));for(const s of c.skins.filter(s=>s.name.toLocaleLowerCase().includes(search.toLocaleLowerCase()))){const label=node('label',undefined,'ra-card');label.style.display='block';const cb=node('input');cb.type='checkbox';cb.checked=state.excluded.includes(s.skinId);cb.onchange=()=>request('exclude',{skinId:s.skinId,excluded:cb.checked});label.append(cb,node('span',' Excluir '+s.name));list.append(label);}}}drawExclusions();
      }
      if(tab==='Sala'){
        const room=state.room||{};
        panel.append(node('h3','Hospedar sala'),node('p','A hospedagem continua enquanto este aplicativo estiver aberto.','ra-muted'));
        panel.append(button(room.status==='starting'?'Criando sala…':'Criar sala',()=>request('room-host'),['starting','hosting','stopping'].includes(room.status)),button('Encerrar hospedagem',()=>request('room-stop'),!['starting','hosting'].includes(room.status)));
        if(room.link){const link=node('input');link.value=room.link;link.readOnly=true;link.setAttribute('aria-label','Endereço da sala');panel.append(link,button('Copiar link',async()=>{try{await navigator.clipboard.writeText(room.link);notice='Link copiado.';}catch{link.focus();link.select();notice='Selecione e copie o endereço completo.';}render();}));}
        panel.append(node('h3','Entrar na sala'));const address=node('input');address.placeholder='Cole o endereço completo';address.value=roomDraft;address.setAttribute('aria-label','Endereço para entrar');address.oninput=()=>roomDraft=address.value;panel.append(address,button('Conectar',()=>{window.__roseRoomLeft=false;request('room-join',{link:roomDraft});}));
        panel.append(button('Tentar reconectar',()=>{window.__roseRoomLeft=false;request('room-reconnect');}),button('Sair da sala',()=>{window.__roseRoomLeft=true;request('room-leave');}));
        panel.append(node('p',room.message|| (room.connected?'Conectado':'Reconectando ou aguardando endereço'),'ra-muted'));
        if(state.phase==='InProgress')panel.append(node('p','Conexão recuperada; alterações de skin ficam para a próxima partida.','ra-muted'));
        panel.append(node('p','“Pronto” é a conferência enviada pelo SEXO2 de cada participante. “Escolha recebida” significa sincronização, não aplicação em partida.','ra-muted'));
        if(!state.members.length)panel.append(node('p','Nenhum participante identificado.','ra-muted'));
        for(const m of state.members){const card=node('div',undefined,'ra-card');card.append(node('strong',m.name+(m.local?' · você':'')),node('p',memberStatus(m),m.ready===true&&m.sameLobby?'ra-ok':'ra-muted'),node('p',m.lotteryOptin?'Participa do sorteio':'Fora do sorteio','ra-muted'));if(m.choices.length)card.append(node('p',m.choices.map(p=>(p.champion_name||'Campeão '+p.champion_id)+' · '+(p.skin_name||'skin '+p.skin_id)).join(' / '),'ra-muted'));panel.append(card);}
      }
      if(tab==='Preparo'){const footer=node('footer');footer.append(button('Gerar diagnóstico sem chave da sala',()=>request('export-diagnostic')),button('Abrir pasta do relatório',()=>request('open-diagnostic'),!state.diagnostic));if(state.diagnostic)footer.append(node('p',state.diagnostic.name,'ra-muted'));panel.append(footer);}
      if(focused){const input=[...panel.querySelectorAll('[aria-label]')].find(n=>n.getAttribute('aria-label')===focused);if(input){input.focus({preventScroll:true});if(selection!==null&&selection!==undefined&&input.type!=='checkbox')try{input.setSelectionRange(selection,selection);}catch{}}}
      [panel,...panel.querySelectorAll('.ra-skins')].forEach((n,i)=>n.scrollTop=scrolls[i]||0);
      if(scrollParent)scrollParent.scrollTop=parentScroll;
    }
    function receive(data){
      if(!pending||data.requestId!==pending.id)return;
      const action=pending.action,extra=pending.extra;pending=null;
      if(action==='favorite')delete favoriteDraft[extra.championId+':'+extra.skinId];
      if(data.type==='friends-error'){if(action==='skin-index'){skinIndexAsked=false;skinIndexFailed=true;}transportNotice=false;notice=data.error||'Não foi possível confirmar a operação.';render();if(favoriteQueue.length)request('favorite',favoriteQueue.shift());return;}
      const recovered=transportNotice;
      if(recovered){notice='';transportNotice=false;}
      const signature=JSON.stringify({...data,requestId:undefined});const changed=signature!==lastRender;lastRender=signature;
      state=data;lastSeen=Date.now();phase=data.phase;launch.hidden=!['Lobby','ChampSelect','Matchmaking','ReadyCheck'].includes(phase);launch.textContent='Ferramentas · '+(data.readiness.localReady?'preparado':'verificar');
      if(action==='library-list')libraryLoaded=true;
      notice=action==='snapshot'?notice:data.message||'';
      if(action==='save-profile'){nameDraft='';skinDraft={};}
      const editing=panel.contains(document.activeElement)&&['INPUT','SELECT','TEXTAREA'].includes(document.activeElement?.tagName);
      if(changed||recovered||action!=='snapshot')render();
      if(favoriteQueue.length){request('favorite',favoriteQueue.shift());return;}
      if(action==='skin-index'&&Array.isArray(data.skinIndex))skinIndex=data.skinIndex;
      if(tab==='Favoritas'){if(!libraryLoaded){libraryLoaded=true;request('library-list');}else if(!skinIndex&&!skinIndexAsked&&!skinIndexFailed){skinIndexAsked=true;request('skin-index');}}
    }
    launch.onclick=()=>{panel.hidden=!panel.hidden;backdrop.hidden=panel.hidden;if(!panel.hidden){request();render();}};
    document.addEventListener('keydown',e=>{if(e.key==='Escape')close();});
    function tick(){
      if(!launch.isConnected)document.body.appendChild(launch);if(!panel.isConnected)document.body.appendChild(panel);if(!backdrop.isConnected)document.body.appendChild(backdrop);
      if(!bridge&&window.__roseBridge){bridge=window.__roseBridge;bridge.subscribe('friends-state',receive);bridge.subscribe('friends-error',receive);bridge.subscribe('phase-change',data=>{phase=data.phase;if(phase==='InProgress'){close();launch.hidden=true;}else request();});}
      if(pending&&Date.now()-pending.since>15000){pending=null;favoriteQueue=[];favoriteDraft={};transportNotice=true;notice='O SEXO2 demorou a responder. Tente novamente.';if(!panel.hidden)render();}
      if(bridge&&!bridge.ready){
        if(pending?.action==='snapshot')pending=null;
        launch.textContent='SEXO2 · reconectando';
        if(!transportNotice||notice!=='Reconectando ao SEXO2…'){transportNotice=true;notice='Reconectando ao SEXO2…';if(!panel.hidden)render();}
      }
      if(phase!=='InProgress')request();
    }
    setInterval(tick,3000);tick();
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start);else start();
})();
