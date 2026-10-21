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
  let bridge, state = null, draft = {}, dirty = false, open = false, chooser = null, tab = "skins";
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
#sexo2-swiftplay-pins .rsp-sub {margin:14px 0 8px}
#sexo2-swiftplay-pins .rsp-tabs {display:flex;margin:12px 0 0;border-bottom:1px solid var(--s2-line)}
#sexo2-swiftplay-pins .rsp-tabs button {border:0;background:transparent;margin:0;padding:7px 12px 6px;font:500 13px var(--s2-font-display);letter-spacing:.05em;text-transform:uppercase;color:var(--s2-fg-3)}
#sexo2-swiftplay-pins .rsp-tabs button:hover {color:var(--s2-fg-2)}
#sexo2-swiftplay-pins .rsp-tabs button[aria-selected="true"] {color:var(--s2-fg);box-shadow:inset 0 -2px 0 var(--s2-fg)}
#sexo2-swiftplay-pins .rsp-build {margin-top:8px}
#sexo2-swiftplay-pins .rsp-champs {display:grid;grid-template-columns:repeat(auto-fill,minmax(96px,1fr));gap:6px;margin-top:6px}
#sexo2-swiftplay-pins .rsp-champ {display:flex;flex-direction:column;align-items:center;gap:4px;padding:6px 4px;margin:0;min-width:0}
#sexo2-swiftplay-pins .rsp-champ img {width:56px;height:56px;display:block;object-fit:cover}
#sexo2-swiftplay-pins .rsp-champ span {font-size:12px;max-width:100%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
#sexo2-swiftplay-pins .rsp-champ small {font-size:11px;color:var(--s2-fg-2);max-width:100%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
#sexo2-swiftplay-pins .rsp-champ .rsp-error {color:#f3a090}
#sexo2-swiftplay-pins .rsp-message {font-size:12px;line-height:1.5;color:var(--s2-fg-2);margin-top:10px}
#sexo2-swiftplay-pins .rsp-head {display:flex;align-items:center;gap:8px}
#sexo2-swiftplay-pins .rsp-head h3 {margin:0 0 0 6px}
#sexo2-swiftplay-pins .rsp-search {margin:10px 0 0}
#sexo2-swiftplay-pins .rsp-grid {display:grid;grid-template-columns:repeat(auto-fill,minmax(140px,1fr));gap:10px;margin-top:8px}
#sexo2-swiftplay-pins .rsp-card {display:flex;flex-direction:column;gap:6px;min-width:0}
#sexo2-swiftplay-pins .rsp-tile {position:relative;display:flex;flex-direction:column;padding:0;margin:0;overflow:hidden;text-align:left}
#sexo2-swiftplay-pins .rsp-tile img {width:100%;aspect-ratio:1;object-fit:cover;display:block;filter:grayscale(.7) brightness(.6);transition:filter .12s}
#sexo2-swiftplay-pins .rsp-tile:hover img {filter:grayscale(.2) brightness(.85)}
#sexo2-swiftplay-pins .rsp-tile[aria-pressed=true] img {filter:none}
#sexo2-swiftplay-pins .rsp-tile[aria-pressed=true] {outline:2px solid var(--s2-fg);outline-offset:-2px}
#sexo2-swiftplay-pins .rsp-tile[aria-pressed=true]::after {content:'Fixada';position:absolute;top:6px;left:6px;font-size:11px;line-height:1;padding:4px 6px;background:rgba(0,0,0,.75);color:var(--s2-fg)}
#sexo2-swiftplay-pins .rsp-tile span {padding:6px 8px;font-size:12px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
`;
  document.head.appendChild(style);
  document.body.appendChild(root);
  window.addEventListener('sexo2-hub-friends',e=>{if(root.closest('#sexo2-hub')){hubActive=e.detail.tab==='Swiftplay';if(!hubActive){root.hidden=true;leaveBuild();}}});
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
  function thumbnail(path, cls, lazy) {
    const img = el("img", cls);
    img.alt = "";
    if (lazy) img.loading = "lazy";
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
  const plain = value => value.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
  // The runes and items page is the champion select assistant, shown inside this screen
  const assistant = () => window.__sexo2Assistant;
  function leaveBuild() {
    try { assistant()?.release?.(); } catch (e) { /* the assistant is optional */ }
  }
  function render() {
    const viewKey = JSON.stringify([state?.championIds || [], chooser, tab]);
    const sameView = root.dataset.viewKey === viewKey;
    const oldSearch = root.querySelector('.rsp-search');
    const position = sameView ? {
      scroll: (root.closest('#sexo2-hub-content') || root.querySelector('.rsp-panel'))?.scrollTop || 0,
      query: oldSearch?.value || '',
      focused: oldSearch === document.activeElement,
      start: oldSearch?.selectionStart,
      end: oldSearch?.selectionEnd
    } : null;
    root.dataset.viewKey = viewKey;
    root.hidden = !available();
    root.replaceChildren();
    if (root.hidden) { leaveBuild(); return; }
    let buildHost = null;
    if (open) {
      const panel = el("section", "rsp-panel");
      panel.setAttribute("aria-label", "Skins fixadas de Swiftplay");
      const header = el("header");
      header.append(el("h3", "", "SEXO2 · SKINS SWIFTPLAY"), button("×", () => {open=false; render();}, "rsp-close"));
      panel.append(header);
      const c = chooser !== null ? state.champions.find(c => c.championId === chooser) : null;
      if (c) {
        // One champion: Skins (cards; clicking pins or unpins and saves at once) and Runas e itens
        const head = el("div", "rsp-head");
        head.append(button("← Voltar", () => {chooser=null;render();}, ""), el("h3", "", c.name));
        const tabs = el("div", "rsp-tabs");
        tabs.setAttribute("role", "tablist");
        for (const [key, label] of [["skins", "Skins"], ["runes", "Runas"], ["items", "Itens"]]) {
          const tabButton = button(label, () => {tab=key; render();}, "");
          tabButton.setAttribute("role", "tab");
          tabButton.setAttribute("aria-selected", String(tab === key));
          tabs.append(tabButton);
        }
        panel.append(head, tabs);
        if (tab === "runes" || tab === "items") {
          buildHost = el("div", "rsp-build");
          panel.append(buildHost);
        } else {
          const search = el("input", "rsp-search");
          search.type = "search"; search.placeholder = "Buscar skin";
          search.setAttribute("aria-label", `Buscar skin de ${c.name}`);
          search.value = position?.query || '';
          const grid = el("div", "rsp-grid");
          const draw = () => {
            grid.replaceChildren();
            const query = plain(search.value);
            for (const skin of c.skins.filter(s => plain(s.name).includes(query))) {
              const picked = draft[c.championId] === skin.skinId;
              const card = el("div", "rsp-card");
              const tile = button("", () => {
                if (!editable()) return;
                draft[c.championId] = picked ? null : skin.skinId;
                dirty = true; message = "";
                request(makeSave(state, draft));
              }, "rsp-tile");
              tile.disabled = !editable();
              tile.setAttribute("aria-pressed", String(picked));
              tile.setAttribute("aria-label", "Fixar " + skin.name);
              if (asset(skin.tilePath)) tile.append(thumbnail(skin.tilePath, "", true));
              tile.append(el("span", "", skin.name));
              card.append(tile);
              grid.append(card);
            }
            if (!grid.childElementCount) grid.append(el("p", "rsp-muted", "Nenhuma skin com esse nome."));
          };
          search.addEventListener("input", draw); draw();
          panel.append(search, grid);
        }
      } else {
        panel.append(el("h3", "rsp-sub", "Skins, runas e itens por campeão"));
        const champs = el("div", "rsp-champs");
        for (const c of state.champions) {
          const skin = c.skins.find(s => s.skinId === draft[c.championId]);
          const pick = button("", () => {chooser=c.championId; tab="skins"; render();}, "rsp-champ");
          pick.disabled = !editable();
          pick.setAttribute("aria-label", c.name);
          pick.append(thumbnail(c.portrait, ""), el("span", "", c.name));
          if (skin) pick.append(el("small", "", skin.name));
          if (c.status?.message) pick.append(el("small", c.status.state === "error" ? "rsp-error" : "", c.status.message));
          champs.append(pick);
        }
        panel.append(champs);
      }
      if (!state.editable) panel.append(el("div", "rsp-message", "Busca em andamento. Cancele para alterar as escolhas."));
      if (state.error || message) panel.append(el("div", "rsp-message", state.error || message));
      root.append(panel);
    }
    root.append(button("SEXO2 · Fixar skins", () => {open=!open;render();}, "rsp-launch"));
    if (buildHost && assistant()?.embed) assistant().embed(buildHost, chooser, tab);
    else {
      if (buildHost) buildHost.textContent = "Runas e itens indisponíveis.";
      leaveBuild();
    }
    if (position) {
      const search = root.querySelector('.rsp-search');
      if (position.focused && search) {
        search.focus({preventScroll:true});
        if (position.start !== null && position.start !== undefined) {
          search.setSelectionRange(position.start, position.end);
        }
      }
    }
    // One scroll only: the hub content, or the floating panel. A new view starts at the top.
    const scroller = root.closest('#sexo2-hub-content') || root.querySelector('.rsp-panel');
    if (scroller) scroller.scrollTop = position ? position.scroll : 0;
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
    if (wasSave) {dirty=false;message="";}
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
