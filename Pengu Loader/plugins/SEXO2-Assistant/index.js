/**
 * @name SEXO2-Assistant
 * @description Assistente da seleção de campeões: Runas e Itens (protótipo aprovado, D-017/D-018), Mods.
 *
 * Abre acima do botão SEXO2 (ROSE-CustomWheel chama window.__sexo2Assistant.toggle). Os dados e as
 * importações vêm do SEXO2 pela ponte (mensagens assistant-*); nomes e ícones de runas, itens e
 * campeões vêm do próprio cliente. A aba Mods abre o painel de mods existente, com todas as funções.
 */
(function () {
  "use strict";

  // ------------------------------------------------------------- lógica pura
  const LANES = { top: "Topo", jungle: "Selva", middle: "Meio", bottom: "Atirador", support: "Suporte" };

  // /lol-perks/v1/styles + /lol-game-data/assets/v1/perks.json → modelo usado pelo editor.
  function gameFromClient(styles, perks) {
    const info = {};
    for (const p of perks || []) info[p.id] = { name: p.name, icon: p.iconPath, desc: p.shortDesc || "" };
    const rune = (id) => ({ id, name: (info[id] || {}).name || String(id), desc: (info[id] || {}).desc || "", icon: (info[id] || {}).icon || "" });
    let shardRows = [];
    const out = [];
    for (const s of styles || []) {
      const slots = s.slots || [];
      const regular = slots.filter((sl) => sl.type !== "kStatMod").map((sl) => sl.perks.map(rune));
      const stat = slots.filter((sl) => sl.type === "kStatMod").map((sl) => sl.perks.slice());
      if (stat.length && !shardRows.length) shardRows = stat;
      if (regular.length >= 4) out.push({ id: s.id, name: s.name, icon: s.iconPath || "", slots: regular });
    }
    const names = {};
    for (const row of shardRows) for (const id of row) names[id] = (info[id] || {}).name || String(id);
    return { styles: out, shards: { rows: shardRows, names }, icons: Object.fromEntries(Object.entries(info).map(([k, v]) => [k, v.icon])) };
  }

  // Regras de runas, iguais às de design/propostas/sexo2-v1/js/runes.js.
  function index(game) {
    const perks = {};
    const styles = {};
    for (const style of game.styles) {
      styles[style.id] = style;
      style.slots.forEach((slot, row) => {
        for (const r of slot) perks[r.id] = { ...r, style: style.id, row };
      });
    }
    return { perks, styles, shardRows: game.shards.rows, shardNames: game.shards.names };
  }
  function fromPerks(data, page) {
    const [keystone, a, b, c, s1, s2, f1, f2, f3] = page.perks;
    const secondary = [s1, s2].filter(Boolean).map((id) => ({ row: data.perks[id] ? data.perks[id].row : -1, id }));
    return { primary: page.primary, sub: page.sub, keystone, minor: [a, b, c], secondary, shards: [f1, f2, f3] };
  }
  function toPerks(p) {
    const sec = [...p.secondary].sort((x, y) => x.row - y.row).map((s) => s.id);
    return [p.keystone, ...p.minor, ...sec, ...p.shards];
  }
  function clone(p) {
    return { ...p, minor: [...p.minor], secondary: p.secondary.map((s) => ({ ...s })), shards: [...p.shards] };
  }
  function samePage(a, b) {
    return !!a && !!b && a.primary === b.primary && a.sub === b.sub && a.perks.join() === b.perks.join();
  }
  function validate(data, p) {
    const errors = [];
    const prim = data.styles[p.primary];
    const sub = data.styles[p.sub];
    if (!prim) errors.push("primary");
    if (!sub || p.sub === p.primary) errors.push("sub");
    if (prim) {
      if (!prim.slots[0].some((r) => r.id === p.keystone)) errors.push("keystone");
      for (let row = 1; row <= 3; row++) if (!prim.slots[row].some((r) => r.id === p.minor[row - 1])) errors.push("minor" + row);
    }
    if (sub) {
      const rows = new Set();
      for (const s of p.secondary) {
        if (s.row < 1 || s.row > 3 || !sub.slots[s.row].some((r) => r.id === s.id)) errors.push("secondary");
        rows.add(s.row);
      }
      if (p.secondary.length !== 2 || rows.size !== 2) errors.push("secondary-count");
    }
    data.shardRows.forEach((row, i) => {
      if (!row.includes(p.shards[i])) errors.push("shard" + (i + 1));
    });
    return errors;
  }
  const edit = {
    primaryStyle(data, p, styleId) {
      const n = clone(p);
      if (styleId === n.primary) return n;
      n.primary = styleId;
      n.keystone = null;
      n.minor = [null, null, null];
      if (n.sub === styleId) {
        n.sub = Object.keys(data.styles).map(Number).find((id) => id !== styleId);
        n.secondary = [];
      }
      return n;
    },
    subStyle(data, p, styleId) {
      const n = clone(p);
      if (styleId === n.primary || styleId === n.sub) return n;
      n.sub = styleId;
      n.secondary = [];
      return n;
    },
    primaryRune(data, p, row, id) {
      const n = clone(p);
      if (row === 0) n.keystone = id;
      else n.minor[row - 1] = id;
      return n;
    },
    secondaryRune(data, p, row, id) {
      const n = clone(p);
      const existing = n.secondary.findIndex((s) => s.row === row);
      if (existing >= 0) n.secondary.splice(existing, 1);
      n.secondary.push({ row, id });
      if (n.secondary.length > 2) n.secondary.shift();
      return n;
    },
    shard(data, p, row, id) {
      const n = clone(p);
      n.shards[row] = id;
      return n;
    },
  };

  // Mesma regra de ROSE-CustomWheel/index.js (computeAnchor).
  function computeAnchor(buttonRect, panelSize, viewport, gap = 8, margin = 8) {
    const room = Math.max(0, buttonRect.top - gap - margin);
    const height = Math.min(panelSize.height, room);
    let left = buttonRect.right - panelSize.width;
    left = Math.max(margin, Math.min(left, viewport.width - margin - panelSize.width));
    return { left: Math.round(left), top: Math.round(buttonRect.top - gap - height), maxHeight: Math.floor(room) };
  }

  // The client's lol-uikit-flat-button can measure 0x0 itself while its content is visible:
  // the first box with a size among the button, its children and its parent anchors the panel.
  function anchorRect(button) {
    if (!button) return null;
    const candidates = [button, ...Array.from(button.children || []), button.parentElement];
    for (const el of candidates) {
      if (!el || typeof el.getBoundingClientRect !== "function") continue;
      const r = el.getBoundingClientRect();
      if (r.width > 0 && r.height > 0) return r;
    }
    return null;
  }

  // Without a usable button the panel sits at the bottom right, where the button is.
  function fallbackAnchor(viewport, panelSize, margin = 16) {
    const height = Math.min(panelSize.height, viewport.height - 2 * margin);
    return {
      left: Math.max(margin, viewport.width - margin - panelSize.width),
      top: Math.max(margin, viewport.height - 80 - height),
      maxHeight: height,
    };
  }

  const RUNE_ERRORS = {
    cannot_edit: "A seleção terminou antes da confirmação.",
    no_free_page: "Sem espaço para a página do SEXO2. Apague uma página no cliente.",
  };
  function runeError(code) {
    if (!code) return "";
    return RUNE_ERRORS[code] || (/^(lcu_|not_confirmed)/.test(code) ? "O cliente recusou a página." : "Falha ao importar.");
  }
  function itemError(code, champion) {
    if (!code) return "";
    if (code === "no_builds" || code === "unsupported_mode" || code.startsWith("stats_")) return `Sem dados para ${champion}.`;
    return "O cliente recusou o conjunto.";
  }

  if (typeof window === "undefined" && typeof module !== "undefined" && module.exports) {
    module.exports = { gameFromClient, index, fromPerks, toPerks, validate, edit, samePage, computeAnchor, anchorRect, fallbackAnchor, runeError, itemError, LANES };
    return;
  }

  // -------------------------------------------------------------------- UI
  const nf1 = new Intl.NumberFormat("pt-BR", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
  const nf0 = new Intl.NumberFormat("pt-BR");
  const pct = (v) => nf1.format(v) + "%";
  const esc = (s) => String(s == null ? "" : s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);
  const PANEL_WIDTH = 452;
  const PANEL_HEIGHT = 492;

  const CSS = `
#sexo2-assistant{box-sizing:border-box;position:fixed;z-index:10001;width:${PANEL_WIDTH}px;height:${PANEL_HEIGHT}px;display:flex;flex-direction:column;background:var(--s2-surface);border:1px solid var(--s2-line);box-shadow:0 8px 30px rgba(0,0,0,.55);}
#sexo2-assistant[hidden]{display:none;}
#sexo2-assistant .asst-head{display:flex;align-items:center;gap:var(--sp-2);padding:var(--sp-2) var(--sp-3);}
#sexo2-assistant .asst-head .champ{width:32px;height:32px;border-radius:2px;}
#sexo2-assistant .asst-head .name{font:600 22px/1 var(--s2-font-display);text-transform:uppercase;letter-spacing:.01em;}
#sexo2-assistant .grow{flex:1;}
#sexo2-assistant .asst-body{flex:1;overflow-y:auto;padding:var(--sp-3);}
#sexo2-assistant .asst-foot{height:36px;border-top:1px solid var(--s2-line);display:flex;align-items:center;gap:var(--sp-2);padding:0 var(--sp-3);font-size:12px;color:var(--s2-fg-2);}
#sexo2-assistant .asst-foot .err{color:var(--s2-enemy);}
#sexo2-assistant .mini-page{display:inline-flex;align-items:center;gap:3px;}
#sexo2-assistant .rec-cards{display:grid;grid-template-columns:1fr 1fr;gap:var(--sp-2);}
#sexo2-assistant .rec-card{text-align:left;padding:var(--sp-2) var(--sp-3) var(--sp-3);border:1px solid var(--s2-line);background:var(--s2-surface-2);}
#sexo2-assistant .rec-card:hover{border-color:#3a3e44;background:var(--s2-hover);}
#sexo2-assistant .rec-card[aria-pressed="true"]{border-color:var(--s2-fg);}
#sexo2-assistant .rec-card .label{font-size:var(--t-small);color:var(--s2-fg-2);margin-bottom:var(--sp-1);}
#sexo2-assistant .rec-card .main{display:flex;align-items:center;justify-content:space-between;gap:var(--sp-2);}
#sexo2-assistant .rec-card .keystone{width:40px;height:40px;}
#sexo2-assistant .rec-card .sub{display:flex;align-items:center;gap:var(--sp-1);margin-top:var(--sp-2);}
#sexo2-assistant .rec-card .sub img{width:20px;height:20px;}
#sexo2-assistant .rec-card .games{margin-left:auto;font-size:var(--t-small);color:var(--s2-fg-2);font-variant-numeric:tabular-nums;}
#sexo2-assistant .section-head{display:flex;align-items:center;justify-content:space-between;margin:var(--sp-4) 0 var(--sp-1);gap:var(--sp-2);}
#sexo2-assistant .rec-row{display:flex;align-items:center;gap:var(--sp-2);width:100%;padding:6px var(--sp-1);border-bottom:1px solid #202327;text-align:left;}
#sexo2-assistant .rec-row:hover{background:var(--s2-hover);}
#sexo2-assistant .rec-row[aria-pressed="true"]{box-shadow:inset 2px 0 0 var(--s2-fg);}
#sexo2-assistant .rec-row .keystone{width:28px;height:28px;}
#sexo2-assistant .rec-row .minor{width:18px;height:18px;}
#sexo2-assistant .rec-row .lbl{font-size:var(--t-small);color:var(--s2-fg-3);margin-left:var(--sp-1);}
#sexo2-assistant .rec-row .wr{width:52px;text-align:right;}
#sexo2-assistant .rec-row .n{width:56px;text-align:right;font-size:var(--t-small);color:var(--s2-fg-3);font-variant-numeric:tabular-nums;}
#sexo2-assistant .tree-bar{display:flex;align-items:center;gap:var(--sp-2);margin-bottom:var(--sp-3);}
#sexo2-assistant .tree-bar .stat{display:flex;align-items:baseline;gap:6px;}
#sexo2-assistant .tree{display:grid;grid-template-columns:1fr 1fr;gap:var(--sp-4);}
#sexo2-assistant .tree-col{display:flex;flex-direction:column;gap:10px;}
#sexo2-assistant .styles{display:flex;gap:6px;padding-bottom:8px;border-bottom:1px solid var(--s2-line);}
#sexo2-assistant .styles button{width:26px;height:26px;border-radius:50%;opacity:.35;}
#sexo2-assistant .styles button img{width:26px;height:26px;}
#sexo2-assistant .styles button:hover{opacity:.7;}
#sexo2-assistant .styles button[aria-pressed="true"]{opacity:1;}
#sexo2-assistant .styles button:disabled{opacity:.1;cursor:default;}
#sexo2-assistant .tree-row{display:flex;justify-content:space-around;align-items:center;}
#sexo2-assistant .tree-row button{border-radius:50%;padding:2px;}
#sexo2-assistant .tree-row button img{width:30px;height:30px;border-radius:50%;filter:grayscale(1) brightness(.55);}
#sexo2-assistant .tree-row.keystones button img{width:38px;height:38px;}
#sexo2-assistant .tree-row button:hover img{filter:grayscale(.4) brightness(.85);}
#sexo2-assistant .tree-row button[aria-pressed="true"] img{filter:none;box-shadow:0 0 0 2px var(--s2-fg);}
#sexo2-assistant .tree-row.shards button img{width:20px;height:20px;}
#sexo2-assistant .tree-row.shards{padding:0 6px;}
#sexo2-assistant .tree-name{margin-top:-4px;}
#sexo2-assistant .ip-head{margin-bottom:var(--sp-2);}
#sexo2-assistant .ip-section{padding:5px 0 7px;border-bottom:1px solid #202327;}
#sexo2-assistant .ip-title{font-size:12px;color:var(--s2-fg-2);margin-bottom:4px;}
#sexo2-assistant .ip-items{display:flex;flex-wrap:wrap;gap:4px;}
#sexo2-assistant .ip-item{position:relative;display:inline-block;line-height:0;}
#sexo2-assistant .ip-count{position:absolute;right:1px;bottom:1px;font-size:10px;line-height:1;padding:1px 2px;background:rgba(0,0,0,.75);color:var(--s2-fg);}
#sexo2-assistant .state{display:flex;flex-direction:column;align-items:center;justify-content:center;gap:var(--sp-2);height:100%;color:var(--s2-fg-2);text-align:center;padding:var(--sp-4);}
#sexo2-assistant .skeleton{background:linear-gradient(90deg,#1b1d21 25%,#22252a 50%,#1b1d21 75%);background-size:200% 100%;animation:s2sk 1.2s infinite;}
@keyframes s2sk{to{background-position:-200% 0}}
`;

  function start() {
    if (!document.body || !document.head) {
      setTimeout(start, 100);
      return;
    }
    if (window.__sexo2Assistant) return;

    const style = document.createElement("style");
    style.textContent = CSS;
    document.head.appendChild(style);
    const panel = document.createElement("section");
    panel.id = "sexo2-assistant";
    panel.className = "s2";
    panel.hidden = true;
    panel.setAttribute("aria-label", "SEXO2");
    document.body.appendChild(panel);

    const S = { tab: "runes", screen: "home", draft: null, source: null, state: null, lanePending: null };
    let game = null;
    let data = null;
    const names = { champions: {}, items: {} };
    let button = null;
    let observer = null;
    let bridge = null;

    // Dados do cliente (uma vez por sessão do cliente).
    let loading = null;
    function loadClientData() {
      if (game || loading) return loading;
      const get = (path) => fetch(path).then((r) => (r.ok ? r.json() : null)).catch(() => null);
      loading = Promise.all([
        get("/lol-perks/v1/styles"),
        get("/lol-game-data/assets/v1/perks.json"),
        get("/lol-game-data/assets/v1/items.json"),
        get("/lol-game-data/assets/v1/champion-summary.json"),
      ]).then(([styles, perks, items, champions]) => {
        loading = null;
        if (Array.isArray(styles) && Array.isArray(perks)) {
          game = gameFromClient(styles, perks);
          data = index(game);
        }
        for (const i of items || []) names.items[i.id] = { name: i.name, icon: i.iconPath, gold: i.priceTotal };
        for (const c of champions || []) names.champions[c.id] = c.name;
        render();
      });
      return loading;
    }

    const runeIcon = (id) => (game && game.icons[id]) || "";
    const styleIcon = (id) => (data && data.styles[id] ? data.styles[id].icon : "");
    const perkName = (id) => (data && data.perks[id] ? data.perks[id].name : (data && data.shardNames[id]) || String(id));
    const champName = (id) => names.champions[id] || "";
    const send = (payload) => bridge && bridge.send(payload);

    // ----------------------------------------------------------- runas
    function dataState() {
      const st = S.state;
      if (!st || !data) {
        return `<div class="rec-cards"><div class="rec-card skeleton" style="height:94px"></div><div class="rec-card skeleton" style="height:94px"></div></div>
          <div class="skeleton" style="height:30px;margin-top:16px"></div><div class="skeleton" style="height:30px;margin-top:6px"></div>`;
      }
      if (st.error && st.error.startsWith("stats_") && st.error !== "stats_unknown_champion") {
        return `<div class="state"><div>Não foi possível carregar as estatísticas.</div><button class="s2-btn" data-act="retry">Tentar de novo</button></div>`;
      }
      if (st.error === "unsupported_mode" || st.error === "stats_unknown_champion" || !st.runes || !st.runes.general.length) {
        return `<div class="state">Sem dados para ${esc(champName(st.championId))}${st.lane && LANES[st.lane] ? ` no ${LANES[st.lane]}` : ""}.</div>`;
      }
      return null;
    }

    function recFor(selection, matchup) {
      const list = (S.state.runes || {})[matchup ? "matchup" : "general"] || [];
      return list.find((r) => r.selection === selection);
    }

    function runesTab() {
      const st0 = dataState();
      if (st0) return st0;
      if (S.screen === "tree" && S.draft) return runeTree();
      const st = S.state;
      const chosen = st.runes.chosen;
      const label = (sel) => (sel === "win" ? "Maior WR" : "Mais comum");
      const card = (rec) => {
        const p = fromPerks(data, rec.page);
        return `<button class="rec-card" data-act="rune-open" data-sel="${rec.selection}" aria-pressed="${samePage(chosen, rec.page)}">
          <div class="label">${label(rec.selection)}</div>
          <div class="main">
            <span class="t-stat-big" data-tip="${rec.keystoneWinRate == null ? "" : pct(rec.keystoneWinRate)} de vitórias|Win rate da runa-chave em ${nf0.format(rec.games || 0)} partidas (LoLalytics, patch ${esc(st.runes.patch || "")}).">${rec.keystoneWinRate == null ? "—" : pct(rec.keystoneWinRate)}</span>
            <img class="keystone s2-icon" src="${runeIcon(p.keystone)}" alt="${esc(perkName(p.keystone))}" data-tip="${esc(perkName(p.keystone))}|${esc((data.styles[p.primary] || {}).name)}">
          </div>
          <div class="sub">${p.secondary.map((s) => `<img class="s2-icon" src="${runeIcon(s.id)}" alt="${esc(perkName(s.id))}" data-tip="${esc(perkName(s.id))}|${esc((data.styles[p.sub] || {}).name)}">`).join("")}
            <span class="games">${nf0.format(rec.games || 0)} partidas</span></div>
        </button>`;
      };
      const opp = st.opponentId;
      const enemyOptions = (st.enemies || []).map((id) => `<option value="${id}" ${opp === id ? "selected" : ""}>${esc(champName(id))}</option>`).join("");
      const row = (rec) => {
        const p = fromPerks(data, rec.page);
        return `<button class="rec-row" data-act="rune-open" data-sel="${rec.selection}" data-matchup="1" aria-pressed="${samePage(chosen, rec.page)}">
          <img class="keystone s2-icon" src="${runeIcon(p.keystone)}" alt="" data-tip="${esc(perkName(p.keystone))}|${esc((data.styles[p.primary] || {}).name)}">
          ${p.secondary.map((s) => `<img class="minor s2-icon" src="${runeIcon(s.id)}" alt="" data-tip="${esc(perkName(s.id))}|${esc((data.styles[p.sub] || {}).name)}">`).join("")}
          <span class="lbl">${label(rec.selection)}</span><span class="grow"></span>
          <span class="wr t-stat" data-tip="Win rate da runa-chave|Contra ${esc(champName(opp))}, ${nf0.format(rec.games || 0)} partidas.">${rec.keystoneWinRate == null ? "—" : pct(rec.keystoneWinRate)}</span>
          <span class="n">${nf0.format(rec.games || 0)}</span>
        </button>`;
      };
      const vs = st.runes.matchup || [];
      return `<div class="rec-cards">${st.runes.general.map(card).join("")}</div>
        <div class="section-head">
          <span class="t-heading">${opp ? "Contra " + esc(champName(opp)) : "Contra"}</span>
          <select class="s2-select" data-act="opponent" aria-label="Adversário">${opp ? "" : `<option value="">Escolher</option>`}${enemyOptions}</select>
        </div>
        ${vs.length ? vs.map(row).join("") : `<div class="s2-empty">${opp ? `Sem dados suficientes contra ${esc(champName(opp))}.` : "Adversário de rota incerto."}</div>`}`;
    }

    function runeTree() {
      const p = S.draft;
      const src = S.source;
      const edited = !samePage({ primary: p.primary, sub: p.sub, perks: toPerks(p) }, src.page);
      const errors = validate(data, p);
      const styleIds = Object.keys(data.styles).map(Number);
      const styleBar = (active, act, disabledId) => `<div class="styles">${styleIds.map((id) => `<button data-act="${act}" data-style="${id}" aria-pressed="${id === active}" ${id === disabledId ? "disabled" : ""}
          data-tip="${esc(data.styles[id].name)}"><img src="${styleIcon(id)}" alt="${esc(data.styles[id].name)}"></button>`).join("")}</div>`;
      const runeBtn = (id, on, act, row) => `<button data-act="${act}" data-row="${row}" data-id="${id}" aria-pressed="${on}" data-tip="${esc(perkName(id))}|${esc(data.perks[id] ? data.perks[id].desc : "")}"><img src="${runeIcon(id)}" alt="${esc(perkName(id))}"></button>`;
      const prim = data.styles[p.primary];
      const sub = data.styles[p.sub];
      const primaryRows = prim ? prim.slots.map((slot, row) => `<div class="tree-row${row === 0 ? " keystones" : ""}">${slot.map((r) => runeBtn(r.id, row === 0 ? p.keystone === r.id : p.minor[row - 1] === r.id, "p-rune", row)).join("")}</div>`).join("") : "";
      const subRows = sub ? sub.slots.slice(1).map((slot, i) => `<div class="tree-row">${slot.map((r) => runeBtn(r.id, p.secondary.some((s) => s.id === r.id), "s-rune", i + 1)).join("")}</div>`).join("") : "";
      const shardRows = data.shardRows.map((row, i) => `<div class="tree-row shards">${row.map((id) => runeBtn(id, p.shards[i] === id, "shard", i)).join("")}</div>`).join("");
      const stat = edited
        ? `<span class="t-small">Personalizada</span>`
        : `<span class="t-stat" data-tip="Win rate da runa-chave|${nf0.format(src.games || 0)} partidas (LoLalytics, patch ${esc(S.state.runes.patch || "")}).">${src.keystoneWinRate == null ? "—" : pct(src.keystoneWinRate)}</span><span class="t-small num">${nf0.format(src.games || 0)} partidas</span>`;
      return `<div class="tree-bar">
          <button class="s2-btn ghost" data-act="tree-back">← Voltar</button>
          <span class="t-small">${esc(src.label)}</span>
          <span class="grow"></span><span class="stat">${stat}</span>
          <button class="s2-btn primary" data-act="tree-confirm" ${errors.length ? "disabled" : ""}>Confirmar</button>
        </div>
        <div class="tree">
          <div class="tree-col">${styleBar(p.primary, "p-style")}<div class="t-category tree-name">${esc(prim ? prim.name : "")}</div>${primaryRows}</div>
          <div class="tree-col">${styleBar(p.sub, "s-style", p.primary)}<div class="t-category tree-name">${esc(sub ? sub.name : "")}</div>${subRows}<div class="t-category">Fragmentos</div>${shardRows}</div>
        </div>`;
    }

    function miniPage(page) {
      const p = fromPerks(data, page);
      return `<span class="mini-page"><img class="s2-icon" width="18" height="18" src="${runeIcon(p.keystone)}" alt="">${p.secondary.map((s) => `<img class="s2-icon" width="14" height="14" src="${runeIcon(s.id)}" alt="">`).join("")}</span>`;
    }

    function runesFoot() {
      const r = (S.state && S.state.runes) || {};
      let left = "";
      if (r.pending) left = `<span class="s2-spinner"></span><span>Importando…</span>`;
      else if (r.error) left = `<span class="err">${esc(runeError(r.error))}</span>`;
      else if (S.screen === "tree" && S.draft && data && validate(data, S.draft).length) left = `<span>Página incompleta</span>`;
      const right = r.applied && data ? `<span class="t-small">Aplicada</span>${miniPage(r.applied)}` : `<span class="t-muted">Nenhuma página aplicada</span>`;
      return `<div class="asst-foot">${left}<span class="grow"></span>${right}</div>`;
    }

    // ----------------------------------------------------------- itens
    function itemsTab() {
      const st = S.state;
      if (!st) return dataState();
      const it = st.items || {};
      if (!it.blocks || !it.blocks.length) {
        if (it.pending) return `<div class="state"><span class="s2-spinner"></span></div>`;
        return `<div class="state">Sem dados para ${esc(champName(st.championId))}.</div>`;
      }
      const icon = (id, count) => {
        const item = names.items[id] || {};
        return `<span class="ip-item"><img class="s2-icon sq" width="34" height="34" src="${esc(item.icon || "")}" alt="${esc(item.name || id)}" data-tip="${esc(item.name || id)}|${nf0.format(item.gold || 0)} de ouro">${count > 1 ? `<span class="ip-count num">${count}</span>` : ""}</span>`;
      };
      return `<div class="ip-page"><div class="ip-head t-heading">${esc(it.title || "")}</div>
        ${it.blocks.map((b) => `<div class="ip-section"><div class="ip-title">${esc(b.type)}</div><div class="ip-items">${b.items.map((i) => icon(Number(i.id), i.count)).join("")}</div></div>`).join("")}</div>`;
    }

    function itemsFoot() {
      const it = (S.state && S.state.items) || {};
      let left = "";
      if (it.pending) left = `<span class="s2-spinner"></span><span>Importando…</span>`;
      else if (it.error) left = `<span class="err">${esc(itemError(it.error, champName(S.state.championId)))}</span>`;
      else if (it.confirmed) left = `<span>Conjunto importado</span>`;
      const retry = it.error ? `<button class="s2-btn primary" data-act="items-import">Importar conjunto</button>` : "";
      return `<div class="asst-foot">${left}<span class="grow"></span>${retry}</div>`;
    }

    // ----------------------------------------------------------- painel
    function render() {
      try {
        draw();
      } catch (error) {
        console.error("[SEXO2-Assistant] render failed", error);
      }
      place();
    }

    function draw() {
      if (panel.hidden) return;
      const st = S.state;
      const cid = st && st.championId;
      const tabs = [["runes", "Runas"], ["items", "Itens"], ["mods", "Mods"]];
      const lane = S.lanePending || (st && st.lane);
      const body = S.tab === "runes" ? runesTab() : itemsTab();
      const keep = panel.querySelector(".asst-body");
      const scroll = keep ? keep.scrollTop : 0;
      panel.innerHTML = `
        <div class="asst-head">
          ${cid ? `<img class="champ" src="/lol-game-data/assets/v1/champion-icons/${cid}.png" alt="">` : ""}
          <span class="name">${esc(champName(cid))}</span>
          ${lane && LANES[lane] ? `<select class="s2-select" data-act="lane" aria-label="Rota">${Object.entries(LANES).map(([k, v]) => `<option value="${k}" ${k === lane ? "selected" : ""}>${v}</option>`).join("")}</select>` : ""}
          <span class="grow"></span>
          <button class="s2-btn ghost" data-act="close" aria-label="Fechar">✕</button>
        </div>
        <div class="s2-tabs" role="tablist">${tabs.map(([k, v]) => `<button role="tab" data-act="tab" data-tab="${k}" aria-selected="${S.tab === k}">${v}</button>`).join("")}</div>
        <div class="asst-body">${body}</div>
        ${S.tab === "runes" ? runesFoot() : itemsFoot()}`;
      const fresh = panel.querySelector(".asst-body");
      if (fresh) fresh.scrollTop = scroll;
    }

    function place() {
      if (panel.hidden) return;
      const size = { width: PANEL_WIDTH, height: PANEL_HEIGHT };
      const viewport = { width: window.innerWidth, height: window.innerHeight };
      const r = button && button.isConnected ? anchorRect(button) : null;
      const pos = r ? computeAnchor(r, size, viewport) : fallbackAnchor(viewport, size);
      if (!r) console.log("[SEXO2-Assistant] button not measurable; panel at the bottom right");
      panel.style.left = pos.left + "px";
      panel.style.top = pos.top + "px";
      panel.style.height = Math.min(PANEL_HEIGHT, pos.maxHeight) + "px";
    }

    // The client can rebuild the page after plugins load, leaving this panel (and its
    // style) out of the document while an empty copy stays: put them back before showing.
    function reattach() {
      const other = document.getElementById("sexo2-assistant");
      if (other && other !== panel) other.remove();
      if (!style.isConnected) document.head.appendChild(style);
      if (!panel.isConnected) {
        document.body.appendChild(panel);
        console.log("[SEXO2-Assistant] panel reattached");
      }
    }

    function open(anchor) {
      button = anchor;
      reattach();
      panel.hidden = false;
      loadClientData();
      send({ type: "assistant-request" });
      render();
      if (typeof ResizeObserver !== "undefined") {
        observer = new ResizeObserver(place);
        observer.observe(button);
        observer.observe(document.documentElement);
      }
    }
    function close() {
      panel.hidden = true;
      if (observer) observer.disconnect();
      observer = null;
    }

    function act(name, el) {
      const st = S.state;
      switch (name) {
        case "close": close(); return;
        case "tab":
          if (el.dataset.tab === "mods") {
            // O painel de mods existente, com todas as categorias, abre no mesmo lugar.
            close();
            if (window.__sexo2Mods) window.__sexo2Mods.open();
            return;
          }
          S.tab = el.dataset.tab;
          break;
        case "retry": send({ type: "assistant-request" }); break;
        case "rune-open": {
          const matchup = el.dataset.matchup === "1";
          const rec = recFor(el.dataset.sel, matchup);
          if (!rec || !data) return;
          const label = (rec.selection === "win" ? "Maior WR" : "Mais comum") + (matchup ? ` contra ${champName(st.opponentId)}` : "");
          S.source = { ...rec, label };
          S.draft = fromPerks(data, rec.page);
          S.screen = "tree";
          send({ type: "assistant-runes-choose", selection: rec.selection, matchup }); // importação antecipada
          break;
        }
        case "tree-back": S.screen = "home"; send({ type: "assistant-runes-back" }); break;
        case "tree-confirm": S.screen = "home"; send({ type: "assistant-runes-confirm" }); break;
        case "p-style": S.draft = edit.primaryStyle(data, S.draft, +el.dataset.style); sendEdit(); break;
        case "s-style": S.draft = edit.subStyle(data, S.draft, +el.dataset.style); sendEdit(); break;
        case "p-rune": S.draft = edit.primaryRune(data, S.draft, +el.dataset.row, +el.dataset.id); sendEdit(); break;
        case "s-rune": S.draft = edit.secondaryRune(data, S.draft, +el.dataset.row, +el.dataset.id); sendEdit(); break;
        case "shard": S.draft = edit.shard(data, S.draft, +el.dataset.row, +el.dataset.id); sendEdit(); break;
        case "items-import": send({ type: "assistant-items-import" }); break;
        default: return;
      }
      render();
    }

    // Só edições válidas vão para o SEXO2, que agrupa e aplica a mais recente.
    function sendEdit() {
      if (validate(data, S.draft).length) return;
      send({ type: "assistant-runes-edit", page: { primary: S.draft.primary, sub: S.draft.sub, perks: toPerks(S.draft) } });
    }

    panel.addEventListener("click", (e) => {
      const el = e.target.closest("[data-act]");
      if (!el || el.disabled || el.tagName === "SELECT") return;
      e.stopPropagation();
      act(el.dataset.act, el);
    });
    panel.addEventListener("change", (e) => {
      const t = e.target;
      if (t.dataset.act === "opponent" && t.value) send({ type: "assistant-opponent", championId: Number(t.value) });
      if (t.dataset.act === "lane") {
        S.lanePending = t.value;
        send({ type: "assistant-lane", lane: t.value });
      }
    });
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && !panel.hidden) close();
    });

    function receive(state) {
      if (!state || state.type !== "assistant-state") return;
      const previous = S.state;
      if (previous && previous.championId !== state.championId) {
        S.screen = "home";
        S.draft = null;
      }
      S.lanePending = null;
      S.state = state;
      if (S.justOpened && state.supported === false && !panel.hidden) {
        S.justOpened = false;
        return openMods();
      }
      S.justOpened = false;
      render();
    }

    // In queues without statistics (Arena and others) the button opens the mods panel directly.
    function openMods() {
      close();
      if (window.__sexo2Mods) window.__sexo2Mods.open();
    }

    window.__sexo2Assistant = {
      toggle(anchor) {
        console.log("[SEXO2-Assistant] toggle", { open: !panel.hidden, supported: S.state ? S.state.supported : null });
        if (!panel.hidden) return close();
        if (S.state && S.state.supported === false) return openMods();
        S.justOpened = true;
        open(anchor);
      },
      close,
      isOpen: () => !panel.hidden,
    };
    console.log("[SEXO2-Assistant] ready");
    window.dispatchEvent(new Event("sexo2-assistant-ready"));

    const attach = setInterval(() => {
      const b = window.__roseBridge;
      if (!b) return;
      clearInterval(attach);
      bridge = b;
      bridge.subscribe("assistant-state", receive);
      bridge.subscribe("assistant-error", () => render());
      bridge.subscribe("champion-locked", () => !panel.hidden && send({ type: "assistant-request" }));
      bridge.subscribe("phase-change", (d) => {
        if (d && d.phase === "ChampSelect") send({ type: "assistant-request" }); // know the queue before a click
        else if (d && d.phase !== "FINALIZATION") close();
      });
    }, 250);
    setTimeout(() => clearInterval(attach), 30000);
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start, { once: true });
  else start();
})();
