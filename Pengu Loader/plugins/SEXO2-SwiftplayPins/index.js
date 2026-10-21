/**
 * @name SEXO2-SwiftplayPins
 * @description Skins fixadas por campeão para Swiftplay — fork r2
 */
(function () {
  "use strict";
  function reconcileDraft(previous, champions, reset) {
    const result = {};
    for (const c of champions) {
      const value = !reset && Object.prototype.hasOwnProperty.call(previous, c.championId)
        ? previous[c.championId] : (c.pin?.skinId ?? null);
      result[c.championId] = value === null || c.skins.some(s => s.skinId === value)
        ? value : null;
    }
    return result;
  }
  function makeSave(state, draft) {
    return {type: "swiftplay-pins-save", championIds: [...state.championIds],
      selections: state.championIds.map(cid => ({championId: cid, skinId: draft[cid] ?? null}))};
  }
  if (typeof window === "undefined" && typeof module !== "undefined" && module.exports) {
    module.exports = {reconcileDraft, makeSave};
    return;
  }
  function start() {
  if (!document.body || !document.head) {
    setTimeout(start, 100);
    return;
  }
  if (window.__sexo2SwiftplayPinsLoaded) return;
  window.__sexo2SwiftplayPinsLoaded = true;
  let bridge, state = null, draft = {}, dirty = false, open = false, chooser = null;
  let pending = null, saving = false, lastState = 0, message = "", sequence = 0, transportHidden = false, hubActive = null;
  const prefix = `swiftplay-r2-${Date.now()}-${Math.random().toString(36).slice(2)}`;
  const root = document.createElement("div");
  root.id = "sexo2-swiftplay-pins";
  root.hidden = true;
  const style = document.createElement("style");
  style.textContent = `
#sexo2-swiftplay-pins {position:fixed;left:2.5%;bottom:110px;z-index:10001;width:min(32vw,410px);color:var(--s2-fg);font:13px var(--s2-font-text);pointer-events:none}
#sexo2-swiftplay-pins[hidden] {display:none!important}
#sexo2-swiftplay-pins * {box-sizing:border-box}
#sexo2-swiftplay-pins button,#sexo2-swiftplay-pins input {font:inherit;color:var(--s2-fg);border:1px solid var(--s2-line);border-radius:0;background:var(--s2-surface-2);padding:8px 12px}
#sexo2-swiftplay-pins button {cursor:pointer}
#sexo2-swiftplay-pins button:hover {background:var(--s2-hover)}
#sexo2-swiftplay-pins button:disabled {cursor:default;opacity:.45}
#sexo2-swiftplay-pins .rsp-launch {pointer-events:auto;font-weight:600}
#sexo2-swiftplay-pins .rsp-panel {pointer-events:auto;background:var(--s2-surface);border:1px solid var(--s2-line);border-radius:0;padding:16px;margin-bottom:14px;max-height:calc(100vh - 280px);overflow:auto}
#sexo2-swiftplay-pins header {display:flex;align-items:center;justify-content:space-between;gap:8px}
#sexo2-swiftplay-pins h3 {font:500 13px var(--s2-font-display);text-transform:uppercase;letter-spacing:.06em;margin:0;color:var(--s2-fg-2)}
#sexo2-swiftplay-pins .rsp-close {border:0;background:transparent;padding:3px 5px;font-size:20px}
#sexo2-swiftplay-pins .rsp-muted {color:var(--s2-fg-3);font-size:12px;margin:8px 0 12px}
#sexo2-swiftplay-pins .rsp-row {display:flex;align-items:center;gap:10px;padding:14px 0;border-top:1px solid var(--s2-line)}
#sexo2-swiftplay-pins .rsp-row:first-of-type {border-top:0}
#sexo2-swiftplay-pins .rsp-portrait {width:60px;height:60px;border:1px solid var(--s2-line);object-fit:cover;background:var(--s2-surface-2);flex-shrink:0}
#sexo2-swiftplay-pins .rsp-info {flex:1;min-width:0;overflow-wrap:anywhere}
#sexo2-swiftplay-pins .rsp-name {font:500 15px var(--s2-font-display);text-transform:uppercase;letter-spacing:.02em;margin-bottom:4px}
#sexo2-swiftplay-pins .rsp-skin {color:var(--s2-fg-2);font-size:12px}
#sexo2-swiftplay-pins .rsp-status {font-size:11px;color:var(--s2-fg-3);margin-top:6px}
#sexo2-swiftplay-pins .rsp-error {color:#f3a090}
#sexo2-swiftplay-pins .rsp-actions {display:flex;flex-direction:column;gap:6px}
#sexo2-swiftplay-pins .rsp-remove {border:0;background:transparent;color:var(--s2-fg-3);padding:2px 0;font-size:11px}
#sexo2-swiftplay-pins .rsp-save {width:100%;font-weight:600;margin-top:10px}
#sexo2-swiftplay-pins .rsp-message {font-size:12px;line-height:1.5;color:var(--s2-fg-2);margin-top:10px}
#sexo2-swiftplay-pins .rsp-head {display:flex;align-items:center;gap:8px;margin-top:12px}
#sexo2-swiftplay-pins .rsp-search {width:100%;margin:10px 0}
#sexo2-swiftplay-pins .rsp-grid {display:grid;grid-template-columns:repeat(auto-fill,minmax(140px,1fr));gap:10px;max-height:460px;overflow:auto}
#sexo2-swiftplay-pins .rsp-tile {position:relative;display:flex;flex-direction:column;padding:0;overflow:hidden;text-align:left}
#sexo2-swiftplay-pins .rsp-tile img {width:100%;aspect-ratio:1;object-fit:cover;display:block;filter:grayscale(.7) brightness(.6);transition:filter .12s}
#sexo2-swiftplay-pins .rsp-tile:hover img {filter:grayscale(.2) brightness(.85)}
#sexo2-swiftplay-pins .rsp-tile[aria-pressed=true] img {filter:none}
#sexo2-swiftplay-pins .rsp-tile[aria-pressed=true] {outline:2px solid var(--s2-fg);outline-offset:-2px}
#sexo2-swiftplay-pins .rsp-tile[aria-pressed=true]::after {content:'Fixada';position:absolute;top:6px;left:6px;font-size:11px;line-height:1;padding:4px 6px;background:rgba(0,0,0,.75);color:var(--s2-fg)}
#sexo2-swiftplay-pins .rsp-tile span {padding:6px 8px;font-size:12px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
`;
  document.head.appendChild(style);
  document.body.appendChild(root);
  window.addEventListener('sexo2-hub-friends',e=>{if(root.closest('#sexo2-hub')){hubActive=e.detail.tab==='Swiftplay';if(!hubActive)root.hidden=true;}});
  window.addEventListener('sexo2-hub-swiftplay',e=>{hubActive=true;e.detail.target.appendChild(root);open=true;render();});
  let announced = null;
  function announce() {
    const active = state?.active === true;
    if (active === announced) return;
    announced = active;
    window.dispatchEvent(new CustomEvent('sexo2-swiftplay-state', {detail: {active}}));
  }
  const el = (tag, cls, text) => {
    const node = document.createElement(tag);
    if (cls) node.className = cls;
    if (text !== undefined) node.textContent = text;
    return node;
  };
  function asset(path) {
    if (typeof path !== "string") return null;
    if (path.startsWith("/lol-game-data/assets/")) return path;
    if (path.toLowerCase().startsWith("/assets/")) return "/lol-game-data/assets" + path;
    return null;
  }
  function thumbnail(path, cls) {
    const img = el("img", cls);
    img.alt = "";
    const src = asset(path);
    if (src) img.src = src;
    img.addEventListener("error", () => { img.removeAttribute("src"); });
    return img;
  }
  function button(text, action, cls) {
    const b = el("button", cls, text);
    b.type = "button";
    b.addEventListener("click", action);
    return b;
  }
  function available() {
    return hubActive !== false && bridge?.ready && state?.active && Date.now() - lastState < 8000;
  }
  function editable() {return available() && state.editable && !saving && !state.error;}
  function render() {
    const viewKey = JSON.stringify([state?.championIds || [], chooser]);
    const sameView = root.dataset.viewKey === viewKey;
    const oldSearch = root.querySelector('.rsp-search');
    const position = sameView ? {
      panel: root.querySelector('.rsp-panel')?.scrollTop || 0,
      grid: root.querySelector('.rsp-grid')?.scrollTop || 0,
      query: oldSearch?.value || '',
      focused: oldSearch === document.activeElement,
      start: oldSearch?.selectionStart,
      end: oldSearch?.selectionEnd
    } : null;
    root.dataset.viewKey = viewKey;
    root.hidden = !available();
    root.replaceChildren();
    if (root.hidden) return;
    if (open) {
      const panel = el("section", "rsp-panel");
      panel.setAttribute("aria-label", "Skins fixadas de Swiftplay");
      const header = el("header");
      header.append(el("h3", "", "SEXO2 · SKINS SWIFTPLAY"), button("×", () => {open=false; render();}, "rsp-close"));
      panel.append(header);
      for (const c of state.champions) {
        const skin = c.skins.find(s => s.skinId === draft[c.championId]);
        const row = el("div", "rsp-row");
        row.append(thumbnail(skin?.tilePath || c.portrait, "rsp-portrait"));
        const info = el("div", "rsp-info");
        info.append(el("div", "rsp-name", c.name), el("div", "rsp-skin", skin?.name || "Nenhuma skin fixada"));
        const changed = (draft[c.championId] ?? null) !== (c.pin?.skinId ?? null);
        const status = changed ? "Alteração não salva" : c.pin ? "◆ Fixada" : "";
        if (status) info.append(el("div", "rsp-status", status));
        if (!changed && c.pin && c.status?.message) info.append(el("div", "rsp-status" + (c.status.state === "error" ? " rsp-error" : ""), c.status.message));
        const actions = el("div", "rsp-actions");
        const choose = button(skin ? "Trocar" : "Escolher", () => {chooser=c.championId; render();}, "");
        choose.disabled = !editable();
        actions.append(choose);
        if (skin) {
          const remove = button("Remover", () => {draft[c.championId]=null;dirty=true;render();}, "rsp-remove");
          remove.disabled = !editable();
          actions.append(remove);
        }
        row.append(info, actions);
        panel.append(row);
      }
      if (chooser !== null) {
        const c = state.champions.find(c => c.championId === chooser);
        if (c) {
          const head = el("div", "rsp-head");
          head.append(button("← Voltar", () => {chooser=null;render();}, ""), el("h3", "", c.name));
          panel.append(head);
          const search = el("input", "rsp-search");
          search.type = "search"; search.placeholder = "Buscar skin";
          search.setAttribute("aria-label",`Buscar skin de ${c.name}`);
          search.value = position?.query || '';
          const grid = el("div", "rsp-grid");
          const draw = () => {
            grid.replaceChildren();
            const query = search.value.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
            for (const skin of c.skins.filter(s => s.name.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().includes(query))) {
              const tile = button("", () => {
                if (!editable()) return;
                draft[c.championId]=skin.skinId; dirty=true; chooser=null; message="";render();
              }, "rsp-tile");
              tile.disabled = !editable();
              tile.setAttribute("aria-pressed",String(draft[c.championId]===skin.skinId));
              if (asset(skin.tilePath)) tile.append(thumbnail(skin.tilePath, ""));
              tile.append(el("span", "", skin.name));
              grid.append(tile);
            }
            if (!grid.childElementCount) grid.append(el("p", "rsp-muted", "Nenhuma skin encontrada"));
          };
          search.addEventListener("input",draw); draw(); panel.append(search,grid);
        }
      }
      const save = button(saving ? "Salvando…" : "Salvar e fixar", () => request(makeSave(state,draft)), "rsp-save");
      save.disabled = !editable() || !dirty;
      panel.append(save);
      if (!state.editable) panel.append(el("div", "rsp-message", "Busca em andamento. Cancele para alterar as escolhas."));
      if (state.error || message) panel.append(el("div", "rsp-message", state.error || message));
      root.append(panel);
    }
    root.append(button("SEXO2 · Fixar skins", () => {open=!open;render();}, "rsp-launch"));
    if (position) {
      const search = root.querySelector('.rsp-search');
      if (position.focused && search) {
        search.focus({preventScroll:true});
        if (position.start !== null && position.start !== undefined) {
          search.setSelectionRange(position.start, position.end);
        }
      }
      const panel = root.querySelector('.rsp-panel'), grid = root.querySelector('.rsp-grid');
      if (panel) panel.scrollTop = position.panel;
      if (grid) grid.scrollTop = position.grid;
    }
  }
  function request(payload) {
    if (!bridge?.ready || pending) return;
    const isSave = payload.type === "swiftplay-pins-save";
    if (isSave && !editable()) return;
    const requestId = `${prefix}-${++sequence}`;
    pending = {id:requestId, at:Date.now(), save:isSave};
    saving = isSave;
    bridge.send({...payload,requestId});
    if (isSave) {message="Confirmando campeões e salvando…";render();}
  }
  function receive(data) {
    if (!pending || data.requestId !== pending.id) return;
    const wasSave = pending.save;
    pending=null; saving=false;
    if (data.type === "swiftplay-pins-error") {
      message=data.error || "Não foi possível confirmar as escolhas";
      if (!wasSave) {state=null;lastState=0;}
      render();return;
    }
    const recovered = transportHidden;transportHidden = false;
    const oldIds = state?.championIds || [];
    const visibleState = value => JSON.stringify(value && {
      active:value.active, editable:value.editable, error:value.error,
      championIds:value.championIds, champions:value.champions
    });
    const updated = visibleState(state) !== visibleState(data);
    const changed = oldIds.slice().sort().join(",") !== data.championIds.slice().sort().join(",");
    state=data; lastState=Date.now();
    announce();
    draft=reconcileDraft(draft,data.champions,wasSave || !dirty || !data.active);
    if (wasSave) {dirty=false;message="Preferências salvas.";chooser=null;}
    else if (changed) {if (dirty) message="Os campeões mudaram. Confira as escolhas antes de salvar.";chooser=null;}
    if (!data.active) {open=false;dirty=false;chooser=null;}
    // Unchanged polls leave the DOM intact, including scrollbar dragging.
    // Real updates rebuild safely with search, focus and scroll retained.
    if (updated || changed || wasSave || !data.active || (recovered && hubActive !== false)) render();
  }
  function tick() {
    if (!root.isConnected && document.body) document.body.appendChild(root);
    if (!bridge) {
      bridge=window.__sexo2Bridge;
      if (!bridge) return;
      bridge.subscribe("swiftplay-pins-state",receive);
      bridge.subscribe("swiftplay-pins-error",receive);
      bridge.subscribe("phase-change", data => {
        const phase=data.phase;
        if (phase && !["Lobby","Matchmaking","ReadyCheck"].includes(phase)) {
          state=null;open=false;dirty=false;chooser=null;announce();render();
        }
      });
    }
    if (pending && Date.now()-pending.at>8000) {
      if (pending.save) {message="Confirmação demorou. Atualizando as preferências antes de tentar novamente.";dirty=false;}
      pending=null;saving=false;
    }
    if (!bridge.ready) {transportHidden=true;if(pending&&!pending.save)pending=null;}
    if (!available()) {root.hidden=true;}
    request({type:"swiftplay-pins-request"});
  }
  setInterval(tick,1500);
  tick();
  }
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start, {once:true});
  } else {
    start();
  }
})();
