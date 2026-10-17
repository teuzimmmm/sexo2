/* SEXO2 1.0 — protótipo navegável. Interface em proposta; dados demonstrativos. */
(function () {
  "use strict";

  const G = window.S2_GAME;
  const D = window.S2_DEMO;
  const R = window.S2Runes;
  const RD = R.index(G);
  const $ = (sel, el = document) => el.querySelector(sel);
  const nf1 = new Intl.NumberFormat("pt-BR", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
  const nf0 = new Intl.NumberFormat("pt-BR");
  const pct = (v) => nf1.format(v) + "%";
  const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);

  const img = {
    rune: (id) => `assets/runes/${id}.png`,
    style: (id) => `assets/runes/style-${id}.png`,
    item: (id) => `assets/items/${id}.png`,
    champ: (key) => `assets/champions/${key}.png`,
  };
  const champName = (key) => (G.champions[key] ? G.champions[key].name : key);
  const perkName = (id) => (RD.perks[id] ? RD.perks[id].name : RD.shardNames[id] || String(id));
  const itemName = (id) => (G.items[id] ? G.items[id].name : String(id));

  // ---------------------------------------------------------------- estado
  const S = {
    view: "champ",
    sim: { open: true, timer: 30, running: true, latency: 700, fail: false, noPage: false, data: "ok", log: [] },
    cs: { phase: "pick", hover: "Ahri", champion: null, lane: "middle", opponent: null },
    asst: { open: true, tab: "runes", screen: "home", draft: null, source: null },
    items: { pick: { win: true, pick: false, vs: false }, pending: false, done: null, error: null },
    mod: null,
    game: { minute: 22, tab: true },
    hub: { open: true, section: "skins", category: "skins", auto: "favorite", profile: "Padrão", room: "connected", toast: null },
    dialog: null,
    toast: null,
  };

  function log(msg) {
    const t = new Date().toLocaleTimeString("pt-BR");
    S.sim.log.unshift(`${t}  ${msg}`);
    S.sim.log = S.sim.log.slice(0, 60);
    renderSim();
  }

  function toast(msg) {
    S.toast = msg;
    render();
    clearTimeout(toast.t);
    toast.t = setTimeout(() => { S.toast = null; render(); }, 1800);
  }

  // ------------------------------------------------- controlador de runas
  const canEdit = () => S.cs.phase !== "ended";
  const importer = R.createImporter({
    data: RD,
    debounceMs: 350,
    canEdit,
    log,
    onChange: () => render(),
    // Cliente simulado: responde após a latência; recusa se a seleção acabou ou se configurado para falhar.
    transport(choice, done) {
      setTimeout(() => {
        if (!canEdit()) return done({ ok: false, error: "closed" });
        if (S.sim.fail) return done({ ok: false, error: "client" });
        if (S.sim.noPage) return done({ ok: false, error: "no-page" });
        done({ ok: true });
      }, S.sim.latency);
    },
  });

  const ERR = {
    client: "O cliente recusou a página.",
    "no-page": "Sem espaço para a página do SEXO2. Apague uma página no cliente.",
    closed: "A seleção terminou antes da confirmação.",
  };

  // ------------------------------------------------- cronômetro da seleção
  setInterval(() => {
    if (S.view !== "champ" || !S.sim.running || S.cs.phase === "ended") return;
    S.sim.timer -= 1;
    if (S.sim.timer <= 0) {
      endPhase();
      render();
      return;
    }
    // Só o relógio muda: não redesenha a tela (seletores abertos continuam abertos).
    const clock = $(".cs-top .clock");
    if (clock) clock.textContent = S.sim.timer;
    const simTimer = $("#sim .timer");
    if (simTimer) simTimer.textContent = S.sim.timer + " s";
  }, 1000);

  function endPhase() {
    if (S.cs.phase === "pick" && S.cs.champion == null) {
      S.cs.champion = S.cs.hover;
      log(`Tempo esgotado: ${champName(S.cs.hover)} confirmado automaticamente.`);
    }
    if (S.cs.phase === "pick") { S.cs.phase = "final"; S.sim.timer = 30; log("Fase final da seleção."); return; }
    S.cs.phase = "ended";
    S.sim.timer = 0;
    importer.close();
    log("Seleção encerrada. Nenhuma importação nova.");
  }

  function currentChampion() { return S.cs.champion || S.cs.hover; }

  function switchChampion(key, reason) {
    if (key === currentChampion()) return;
    if (S.cs.champion) S.cs.champion = key;
    else S.cs.hover = key;
    S.asst.screen = "home";
    S.asst.draft = null;
    S.items.done = null;
    S.mod = null;
    importer.reset(reason || `campeão: ${champName(key)}`);
  }

  // ---------------------------------------------------------------- tooltips
  document.addEventListener("mouseover", (e) => {
    const el = e.target.closest("[data-tip]");
    const tip = $("#tip");
    if (!el) { tip.hidden = true; return; }
    const [title, body] = el.dataset.tip.split("|");
    tip.innerHTML = `<b>${esc(title)}</b>${body ? esc(body) : ""}`;
    tip.hidden = false;
    const r = el.getBoundingClientRect();
    tip.style.left = Math.min(r.left, innerWidth - 280) + "px";
    tip.style.top = r.bottom + 6 + "px";
  });

  // ---------------------------------------------------------------- render
  function render() {
    document.querySelectorAll("#views button").forEach((b) => b.setAttribute("aria-current", String(b.dataset.view === S.view)));
    const client = $("#client");
    client.innerHTML = S.view === "champ" ? champSelect() : S.view === "game" ? game() : home();
    if (S.dialog) client.insertAdjacentHTML("beforeend", dialog());
    if (S.toast) client.insertAdjacentHTML("beforeend", `<div class="s2-toast s2">${esc(S.toast)}</div>`);
    renderSim();
  }

  // --------------------------------------------- seleção de campeões
  function champSelect() {
    const phaseText = { pick: "Escolha seu campeão", final: "Organize sua equipe", ended: "A partida está começando" }[S.cs.phase];
    const mm = Math.max(0, S.sim.timer);
    const me = currentChampion();
    const allies = D.allies.map((a) => {
      const champ = a.me ? me : a.champion;
      const locked = a.me ? !!S.cs.champion : true;
      return `<div class="cs-slot${a.me ? " me" : ""}"><img src="${img.champ(champ)}" alt="" style="${locked ? "" : "opacity:.6"}">
        <div><div class="who">${esc(a.player)}</div><div class="what">${esc(champName(champ))} · ${D.lanes[a.lane]}</div></div></div>`;
    }).join("");
    const enemies = D.enemies.map((e) => `<div class="cs-slot"><img src="${img.champ(e.champion)}" alt="">
        <div><div class="who">${esc(champName(e.champion))}</div><div class="what">Adversário</div></div></div>`).join("");
    const center = S.cs.champion
      ? `<div class="cs-locked"><img src="${img.champ(S.cs.champion)}" alt=""></div>`
      : `<div class="cs-grid-area"><div class="cs-filter"><span>Todos os campeões</span><span>Buscar</span></div>
          <div class="cs-grid">${D.pool.map((k) => `<button data-act="hover" data-champ="${k}" class="${k === S.cs.hover ? "sel" : ""}"
            ${D.allies.concat(D.enemies).some((x) => !x.me && x.champion === k) ? "disabled" : ""}><img src="${img.champ(k)}" alt="">${esc(champName(k))}</button>`).join("")}</div></div>`;
    return `<div class="cs">
      <div class="cs-top"><div class="phase">${phaseText}</div><div class="clock">${mm}</div></div>
      <div class="cs-team ally">${allies}</div>
      <div class="cs-team enemy">${enemies}</div>
      ${center}
      <div class="cs-bottom">
        <div class="cs-spells"><span></span><span></span> Feitiços</div>
        <button class="cs-lock" data-act="lock" ${S.cs.champion || S.cs.phase !== "pick" ? "disabled" : ""}>Confirmar</button>
        <div class="cs-right-buttons">
          <button class="cs-btn">Runas</button>
          <button class="cs-btn s2-entry" data-act="asst-toggle" aria-expanded="${S.asst.open}">SEXO2</button>
        </div>
      </div>
      ${S.asst.open ? assistant() : ""}
    </div>`;
  }

  function assistant() {
    const me = currentChampion();
    const tabs = [["runes", "Runas"], ["items", "Itens"], ["mods", "Mods"]];
    const body = S.asst.tab === "runes" ? runesTab(me) : S.asst.tab === "items" ? itemsTab(me) : modsTab(me);
    return `<section class="asst s2" aria-label="SEXO2">
      <div class="asst-head">
        <img class="champ" src="${img.champ(me)}" alt="">
        <span class="name">${esc(champName(me))}</span>
        <select class="s2-select" data-act="lane" aria-label="Rota">${Object.entries(D.lanes).map(([k, v]) => `<option value="${k}" ${k === S.cs.lane ? "selected" : ""}>${v}</option>`).join("")}</select>
        <span class="grow"></span>
        <button class="s2-btn ghost" data-act="asst-toggle" aria-label="Fechar">✕</button>
      </div>
      <div class="s2-tabs" role="tablist">${tabs.map(([k, v]) => `<button role="tab" data-act="tab" data-tab="${k}" aria-selected="${S.asst.tab === k}">${v}</button>`).join("")}</div>
      <div class="asst-body">${body}</div>
      ${S.asst.tab === "runes" ? runesFoot() : S.asst.tab === "items" ? itemsFoot() : `<div class="asst-foot"><span class="grow"></span><button class="s2-btn ghost" data-act="open-library">Biblioteca de mods</button></div>`}
    </section>`;
  }

  // Adversário de rota: escolha manual, senão o mais provável na mesma rota.
  function laneOpponent() {
    if (S.cs.opponent) return { key: S.cs.opponent, manual: true, p: null };
    let best = null;
    for (const e of D.enemies) {
      const p = e.lanes[S.cs.lane] || 0;
      if (!best || p > best.p) best = { key: e.champion, manual: false, p };
    }
    return best && best.p >= 0.5 ? best : null;
  }

  function dataState() {
    if (S.sim.data === "loading") return `<div class="rec-cards"><div class="rec-card skeleton" style="height:94px"></div><div class="rec-card skeleton" style="height:94px"></div></div>
      <div class="skeleton" style="height:30px;margin-top:16px"></div><div class="skeleton" style="height:30px;margin-top:6px"></div>`;
    if (S.sim.data === "error") return `<div class="state"><div>Não foi possível carregar as estatísticas.</div><button class="s2-btn" data-act="data-retry">Tentar de novo</button></div>`;
    if (S.sim.data === "empty") return `<div class="state">Sem dados para ${esc(champName(currentChampion()))} no ${D.lanes[S.cs.lane]}.</div>`;
    return null;
  }

  // ------------------------------------------------------------ runas
  function runesTab(me) {
    const st = dataState();
    if (st) return st;
    const recs = D.runes[me];
    if (!recs) return `<div class="state">Sem dados para ${esc(champName(me))}.</div>`;
    if (S.asst.screen === "tree") return runeTree();
    const snap = importer.snapshot();
    const chosenLabel = snap.chosen ? snap.chosen.label : null;
    const card = (kind, label, rec) => {
      const p = R.fromPerks(RD, rec.page);
      return `<button class="rec-card" data-act="rune-open" data-kind="${kind}" aria-pressed="${chosenLabel === label}">
        <div class="label">${label}</div>
        <div class="main">
          <span class="t-stat-big" data-tip="${pct(rec.wr)} de vitórias|Win rate da runa-chave em ${nf0.format(rec.games)} partidas (LoLalytics, patch ${D.patch}).">${pct(rec.wr)}</span>
          <img class="keystone s2-icon" src="${img.rune(p.keystone)}" alt="${esc(perkName(p.keystone))}" data-tip="${esc(perkName(p.keystone))}|${esc(RD.styles[p.primary].name)}">
        </div>
        <div class="sub">${p.secondary.map((s) => `<img class="s2-icon" src="${img.rune(s.id)}" alt="${esc(perkName(s.id))}" data-tip="${esc(perkName(s.id))}|${esc(RD.styles[p.sub].name)}">`).join("")}
          <span class="games">${nf0.format(rec.games)} partidas</span></div>
      </button>`;
    };
    const opp = laneOpponent();
    const vs = opp && recs.vs[opp.key];
    const enemyOptions = D.enemies.map((e) => `<option value="${e.champion}" ${opp && opp.key === e.champion ? "selected" : ""}>${esc(champName(e.champion))}</option>`).join("");
    const row = (kind, label, rec) => {
      const p = R.fromPerks(RD, rec.page);
      const lbl = `${label} contra ${champName(opp.key)}`;
      return `<button class="rec-row" data-act="rune-open" data-kind="${kind}" aria-pressed="${chosenLabel === lbl}">
        <img class="keystone s2-icon" src="${img.rune(p.keystone)}" alt="" data-tip="${esc(perkName(p.keystone))}|${esc(RD.styles[p.primary].name)}">
        ${p.secondary.map((s) => `<img class="minor s2-icon" src="${img.rune(s.id)}" alt="" data-tip="${esc(perkName(s.id))}|${esc(RD.styles[p.sub].name)}">`).join("")}
        <span class="lbl">${label}</span><span class="grow"></span>
        <span class="wr t-stat" data-tip="Win rate da runa-chave|Contra ${esc(champName(opp.key))}, ${nf0.format(rec.games)} partidas.">${pct(rec.wr)}</span>
        <span class="n">${nf0.format(rec.games)}</span>
      </button>`;
    };
    return `<div class="rec-cards">${card("win", "Maior WR", recs.win)}${card("pick", "Mais comum", recs.pick)}</div>
      <div class="section-head">
        <span class="t-heading">${opp ? "Contra " + esc(champName(opp.key)) : "Contra"}</span>
        <span class="vs-pick">${opp && !opp.manual ? `<span class="t-small" data-tip="Rota estimada|${esc(champName(opp.key))} joga no ${D.lanes[S.cs.lane]} em ${Math.round(opp.p * 100)}% das partidas.">${Math.round(opp.p * 100)}%</span>` : ""}
          <select class="s2-select" data-act="opponent" aria-label="Adversário">${opp ? "" : `<option value="">Escolher</option>`}${enemyOptions}</select></span>
      </div>
      ${vs ? row("vs-win", "Maior WR", vs.win) + row("vs-pick", "Mais comum", vs.pick)
        : `<div class="s2-empty">${opp ? `Sem dados suficientes contra ${esc(champName(opp.key))}.` : "Adversário de rota incerto."}</div>`}`;
  }

  function sourceFor(kind) {
    const recs = D.runes[currentChampion()];
    const opp = laneOpponent();
    if (kind === "win") return { label: "Maior WR", rec: recs.win };
    if (kind === "pick") return { label: "Mais comum", rec: recs.pick };
    const vs = recs.vs[opp.key];
    return kind === "vs-win"
      ? { label: `Maior WR contra ${champName(opp.key)}`, rec: vs.win }
      : { label: `Mais comum contra ${champName(opp.key)}`, rec: vs.pick };
  }

  function runeTree() {
    const p = S.asst.draft;
    const src = S.asst.source;
    const edited = !R.same(p, R.fromPerks(RD, src.rec.page));
    const errors = R.validate(RD, p);
    const styleIds = Object.keys(RD.styles).map(Number);
    const styleBar = (active, act, disabledId) => `<div class="styles">${styleIds.map((id) => `<button data-act="${act}" data-style="${id}" aria-pressed="${id === active}" ${id === disabledId ? "disabled" : ""}
        data-tip="${esc(RD.styles[id].name)}"><img src="${img.style(id)}" alt="${esc(RD.styles[id].name)}"></button>`).join("")}</div>`;
    const runeBtn = (id, on, act, row) => `<button data-act="${act}" data-row="${row}" data-id="${id}" aria-pressed="${on}" data-tip="${esc(perkName(id))}|${esc(RD.perks[id] ? RD.perks[id].desc : RD.shardNames[id] || "")}"><img src="${img.rune(id)}" alt="${esc(perkName(id))}"></button>`;
    const prim = RD.styles[p.primary];
    const sub = RD.styles[p.sub];
    const primaryRows = prim.slots.map((slot, row) => `<div class="tree-row${row === 0 ? " keystones" : ""}">${slot.map((r) => runeBtn(r.id, row === 0 ? p.keystone === r.id : p.minor[row - 1] === r.id, "p-rune", row)).join("")}</div>`).join("");
    const subRows = sub.slots.slice(1).map((slot, i) => `<div class="tree-row">${slot.map((r) => runeBtn(r.id, p.secondary.some((s) => s.id === r.id), "s-rune", i + 1)).join("")}</div>`).join("");
    const shardRows = RD.shardRows.map((row, i) => `<div class="tree-row shards">${row.map((id) => runeBtn(id, p.shards[i] === id, "shard", i)).join("")}</div>`).join("");
    const stat = edited
      ? `<span class="t-small">Personalizada</span>`
      : `<span class="t-stat" data-tip="Win rate da runa-chave|${nf0.format(src.rec.games)} partidas (LoLalytics, patch ${D.patch}).">${pct(src.rec.wr)}</span><span class="t-small num">${nf0.format(src.rec.games)} partidas</span>`;
    return `<div class="tree-bar">
        <button class="s2-btn ghost" data-act="tree-back">← Voltar</button>
        <span class="t-small">${esc(src.label)}</span>
        <span class="grow"></span><span class="stat">${stat}</span>
        <button class="s2-btn primary" data-act="tree-confirm" ${errors.length || !canEdit() ? "disabled" : ""}>Confirmar</button>
      </div>
      <div class="tree">
        <div class="tree-col">${styleBar(p.primary, "p-style")}<div class="t-category tree-name">${esc(prim.name)}</div>${primaryRows}</div>
        <div class="tree-col">${styleBar(p.sub, "s-style", p.primary)}<div class="t-category tree-name">${esc(sub.name)}</div>${subRows}<div class="t-category">Fragmentos</div>${shardRows}</div>
      </div>`;
  }

  function miniPage(page) {
    return `<span class="mini-page"><img class="s2-icon" width="18" height="18" src="${img.rune(page.keystone)}" alt="">${page.secondary.map((s) => `<img class="s2-icon" width="14" height="14" src="${img.rune(s.id)}" alt="">`).join("")}</span>`;
  }

  // Rodapé discreto: só a página aplicada e o que está acontecendo agora.
  function runesFoot() {
    const s = importer.snapshot();
    let left = "";
    if (s.pending) left = `<span class="s2-spinner"></span><span>Importando…</span>`;
    else if (s.error) left = `<span class="err">${ERR[s.error] || "Falha ao importar."}</span>${canEdit() && s.error !== "closed" ? `<button class="s2-btn ghost" data-act="rune-retry">Tentar de novo</button>` : ""}`;
    else if (s.incomplete) left = `<span>Página incompleta</span>`;
    else if (S.cs.phase === "ended" && s.applied) left = `<span>Seleção encerrada</span>`;
    const right = s.applied
      ? `<span class="t-small" data-tip="Página no cliente|${esc(s.applied.label)}">Aplicada</span>${miniPage(s.applied.page)}`
      : `<span class="t-muted">Nenhuma página aplicada</span>`;
    return `<div class="asst-foot">${left}<span class="grow"></span>${right}</div>`;
  }

  // ------------------------------------------------------------ itens
  function itemsTab(me) {
    const st = dataState();
    if (st) return st;
    const it = D.items[me];
    if (!it) return `<div class="state">Sem dados para ${esc(champName(me))}.</div>`;
    const icon = (id, size) => `<img class="s2-icon sq" width="${size}" height="${size}" src="${img.item(id)}" alt="${esc(itemName(id))}" data-tip="${esc(itemName(id))}|${nf0.format(G.items[id] ? G.items[id].gold : 0)} de ouro">`;
    const card = (kind, label, b) => `<button class="rec-card items" data-act="item-pick" data-kind="${kind}" aria-pressed="${S.items.pick[kind]}">
        <div class="label">${label}</div>
        <div class="main"><span class="t-stat-big" data-tip="Win rate dos três itens|Partidas com os três itens juntos: ${nf0.format(b.games)}.">${pct(b.wr)}</span>
          <span class="core">${b.core.map((id) => icon(id, 30)).join("")}</span></div>
        <div class="sub"><span class="games">${nf0.format(b.games)} partidas</span></div>
      </button>`;
    const opt = (o) => `<span class="slot-opt">${icon(o.id, 26)}<span><span class="num t-stat">${pct(o.wr)}</span><br><span class="n num">${nf0.format(o.games)}</span></span></span>`;
    const combo = (o) => `<span class="slot-opt combo">${o.items.map((id) => icon(id, 22)).join("")}<span><span class="num t-stat">${pct(o.wr)}</span><br><span class="n num">${nf0.format(o.games)}</span></span></span>`;
    const opp = laneOpponent();
    const vs = opp && it.vs[opp.key];
    const slotRow = (label, opts, fn) => `<div class="slot-row"><span class="t-category">${label}</span><span class="opts">${opts.length ? opts.map(fn).join("") : `<span class="t-muted t-small">Sem dados</span>`}</span></div>`;
    return `<div class="rec-cards">${card("win", "Maior WR", it.win)}${card("pick", "Mais comum", it.pick)}</div>
      <div style="margin-top:10px">
        ${slotRow("Iniciais", it.start, combo)}
        ${slotRow("Botas", it.boots, opt)}
        ${it.slots.map((s, i) => slotRow(`${i + 4}º item`, s, opt)).join("")}
      </div>
      <div class="section-head"><span class="t-heading">${opp ? "Contra " + esc(champName(opp.key)) : "Contra"}</span></div>
      ${vs ? `<button class="rec-row" data-act="item-pick" data-kind="vs" aria-pressed="${S.items.pick.vs}">
          <span class="core" style="display:flex;gap:3px">${vs.core.map((id) => icon(id, 26)).join("")}</span><span class="grow"></span>
          <span class="wr t-stat">${pct(vs.wr)}</span><span class="n">${nf0.format(vs.games)}</span></button>`
        : `<div class="s2-empty">${opp ? `Sem dados suficientes contra ${esc(champName(opp.key))}.` : "Adversário de rota incerto."}</div>`}`;
  }

  function itemsFoot() {
    const n = Object.values(S.items.pick).filter(Boolean).length;
    let left = "";
    if (S.items.pending) left = `<span class="s2-spinner"></span><span>Importando…</span>`;
    else if (S.items.error) left = `<span class="err">${S.items.error}</span>`;
    else if (S.items.done) left = `<span>${S.items.done}</span>`;
    return `<div class="asst-foot">${left}<span class="grow"></span>
      <button class="s2-btn primary" data-act="items-import" ${!n || S.items.pending || !canEdit() ? "disabled" : ""}>Importar ${n === 1 ? "conjunto" : n + " conjuntos"}</button></div>`;
  }

  // ------------------------------------------------------------- mods
  function modsTab(me) {
    const mods = D.mods[me] || [];
    const row = (name, value) => `<button class="mod-row" role="radio" data-act="mod" data-mod="${esc(value)}" aria-checked="${S.mod === value}"><span class="dot"></span>${esc(name)}</button>`;
    return `${row("Nenhum", "")}${mods.map((m) => row(m.name, m.file)).join("")}
      ${mods.length ? "" : `<div class="s2-empty">Nenhum mod para ${esc(champName(me))} na biblioteca.</div>`}`;
  }

  // ----------------------------------------------------- partida (overlay)
  function game() {
    const m = D.match;
    const inv = m.inventories[S.game.minute];
    const value = (items) => items.reduce((sum, id) => sum + (G.items[id] ? G.items[id].gold : 0), 0);
    const order = inv.order.map(value);
    const chaos = inv.chaos.map(value);
    const tot = (a) => a.reduce((x, y) => x + y, 0);
    const kda = m.kda[S.game.minute];
    const itemsHtml = (items) => `<span class="tb-items">${Array.from({ length: 6 }, (_, i) => (items[i] ? `<img src="${img.item(items[i])}" alt="" data-tip="${esc(itemName(items[i]))}|${nf0.format(G.items[items[i]].gold)}">` : "<span></span>")).join("")}</span>`;
    const rows = m.order.map((ally, i) => `<div class="tb-row">
        <div class="tb-side"><img class="champ" src="${img.champ(ally)}" alt=""><span class="kda">${kda[i]}</span>${itemsHtml(inv.order[i])}</div>
        <div class="tb-mid"></div>
        <div class="tb-side chaos"><img class="champ" src="${img.champ(m.chaos[i])}" alt=""><span class="kda">${kda[i + 5]}</span>${itemsHtml(inv.chaos[i])}</div>
      </div>`).join("");
    const cell = (diff, top) => {
      const side = diff > 0 ? "o" : diff < 0 ? "c" : "eq";
      return `<div class="gold-cell" style="left:50%;top:${top}px">${side === "eq" ? "" : `<span class="arrow ${side}"></span>`}<span class="d ${side}">${nf0.format(Math.abs(diff))}</span></div>`;
    };
    const total = tot(order) - tot(chaos);
    const layer = S.game.tab ? `<div class="gold-layer">
        <div class="gold-total" style="top:${90 + 14}px"><span class="v o">${nf0.format(tot(order))}</span>${cell(total, 0).replace('style="left:50%;top:0px"', 'style="position:static;margin:0"')}<span class="v c">${nf0.format(tot(chaos))}</span></div>
        ${order.map((v, i) => cell(v - chaos[i], 90 + 57 + i * 62 + 14)).join("")}
      </div>` : "";
    return `<div class="game">
      ${S.game.tab ? `<div class="tabboard"><div class="tb-head"><span class="b">Equipe azul</span><span class="r">Equipe vermelha</span></div>${rows}</div>` : ""}
      ${layer}
      <div class="hint">${S.game.tab ? "Placar aberto (Tab)." : "Segure Tab para ver o placar."} Minuto ${S.game.minute}.</div>
    </div>`;
  }

  // ------------------------------------------- cliente: início e painel
  function home() {
    const sections = [["skins", "Skins"], ["mods", "Mods"], ["room", "Sala"], ["settings", "Configurações"], ["diag", "Diagnóstico"]];
    const titles = { skins: "Skins", mods: "Mods", room: "Sala", settings: "Configurações", diag: "Diagnóstico" };
    const h = S.hub;
    const body = { skins: hubSkins, mods: hubMods, room: hubRoom, settings: hubSettings, diag: hubDiag }[h.section]();
    return `<div class="home">
      <div class="home-nav"><span class="play">Jogar</span><span>Início</span><span>Coleção</span><span>Loja</span><span class="grow"></span>
        <button class="s2-hud" data-act="hub-toggle" aria-expanded="${h.open}">SEXO2</button></div>
      <section class="hub s2 s2-panel" ${h.open ? "" : "hidden"}>
        <nav class="hub-side"><div class="brand">SEXO2</div>
          ${sections.map(([k, v]) => `<button data-act="hub-section" data-section="${k}" aria-current="${h.section === k}">${v}</button>`).join("")}
          <span class="grow"></span><span class="ver">Versão ${D.diagnostics.version}</span></nav>
        <div class="hub-main">
          <div class="hub-head"><span class="t-heading">${titles[h.section]}</span><span class="grow"></span>${hubActions()}
            <button class="s2-btn ghost" data-act="hub-toggle" aria-label="Fechar">✕</button></div>
          <div class="hub-body">${body}</div>
        </div>
      </section>
    </div>`;
  }

  function hubActions() {
    const s = S.hub.section;
    if (s === "mods") return `<button class="s2-btn" data-act="lib-export">Exportar biblioteca</button><button class="s2-btn primary" data-act="lib-import">Importar arquivos</button>`;
    if (s === "settings") return `<button class="s2-btn primary" data-act="settings-save">Salvar</button>`;
    if (s === "diag") return `<button class="s2-btn" data-act="toast" data-msg="Pasta de logs aberta.">Abrir logs</button><button class="s2-btn primary" data-act="toast" data-msg="Arquivo de diagnóstico salvo em Downloads.">Gerar arquivo</button>`;
    return "";
  }

  function hubSkins() {
    const modes = [["off", "Desligada"], ["favorite", "Favorita"], ["random", "Aleatória"], ["favorites", "Entre favoritas"]];
    const champs = Object.keys(D.favorites);
    return `<div class="field"><span>Seleção automática</span><span class="ctl"><span class="s2-seg">${modes.map(([k, v]) => `<button data-act="auto" data-mode="${k}" aria-pressed="${S.hub.auto === k}">${v}</button>`).join("")}</span></span></div>
      <div class="field"><span>Perfil</span><span class="ctl"><select class="s2-select" data-act="profile">${D.profiles.map((p) => `<option ${p === S.hub.profile ? "selected" : ""}>${p}</option>`).join("")}</select>
        <button class="s2-btn ghost" data-act="toast" data-msg="Perfil duplicado.">Duplicar</button></span></div>
      <div class="section-head"><span class="t-category">Favoritas</span><span class="t-small">${champs.length} campeões</span></div>
      <div class="fav-grid">${champs.map((c) => `<button class="fav" data-act="fav" data-champ="${c}"><img src="${img.champ(c)}" alt=""><span><span>${esc(champName(c))}</span><span class="t-small">${esc(D.favorites[c])}</span></span></button>`).join("")}</div>`;
  }

  function hubMods() {
    const cats = [["skins", "Skins"], ["maps", "Mapas"], ["fonts", "Fontes"], ["announcers", "Narradores"], ["others", "Outros"]];
    const rows = D.library.filter((m) => m.category === S.hub.category);
    return `<div class="s2-tabs" style="margin-bottom:8px">${cats.map(([k, v]) => `<button data-act="cat" data-cat="${k}" aria-selected="${S.hub.category === k}">${v}</button>`).join("")}</div>
      ${rows.length ? `<table class="s2-table"><thead><tr><th>Nome</th><th>Campeão</th><th class="num">Tamanho</th><th></th></tr></thead><tbody>
        ${rows.map((m) => `<tr><td>${esc(m.name)}</td><td>${m.champion ? esc(champName(m.champion)) : "—"}</td><td class="num">${m.size}</td>
          <td style="text-align:right"><button class="s2-btn ghost" data-act="mod-rename" data-name="${esc(m.name)}">Renomear</button><button class="s2-btn ghost danger" data-act="mod-delete" data-name="${esc(m.name)}">Excluir</button></td></tr>`).join("")}
      </tbody></table>` : `<div class="s2-empty">Nenhum arquivo nesta categoria.</div>`}`;
  }

  function hubRoom() {
    const r = S.hub.room;
    const status = { connected: "Conectada", hosting: "Criando sala…", off: "Sem sala", error: "Não foi possível conectar" }[r];
    return `<div class="kv"><span class="k">Situação</span><span ${r === "error" ? 'style="color:var(--s2-enemy)"' : ""}>${status}</span></div>
      ${r === "connected" ? `<div class="kv"><span class="k">Endereço</span><span class="ctl" style="display:flex;gap:8px;align-items:center"><span class="t-small">${esc(D.room.link)}</span>
          <button class="s2-btn ghost" data-act="toast" data-msg="Endereço copiado.">Copiar</button></span></div>
        <div class="section-head"><span class="t-category">Membros</span><span class="t-small">${D.room.members.length}</span></div>
        ${D.room.members.map((m) => `<div class="member"><span>${esc(m.name)}</span><span class="grow"></span><span class="t-small">${m.status}</span><span class="t-small num" style="width:70px;text-align:right">${m.skins ? m.skins + " skin" : "—"}</span></div>`).join("")}
        <div style="margin-top:12px;display:flex;gap:8px"><button class="s2-btn" data-act="room" data-room="reconnect">Reconectar</button><button class="s2-btn danger" data-act="room" data-room="off">Sair da sala</button></div>`
      : r === "hosting" ? `<div class="state" style="height:120px"><span class="s2-spinner"></span></div>`
      : `<div class="field"><span>Entrar com endereço</span><span class="ctl"><input class="s2-input" placeholder="https://…trycloudflare.com/#…"><button class="s2-btn" data-act="room" data-room="join">Entrar</button></span></div>
        <div class="field"><span>Hospedar</span><span class="ctl"><button class="s2-btn primary" data-act="room" data-room="host">Criar sala</button></span></div>`}`;
  }

  function hubSettings() {
    const sw = (key, on) => `<button class="s2-switch" role="switch" data-act="switch" data-key="${key}" aria-checked="${on}"></button>`;
    const s = (S.hub.settings ||= { threshold: 0.5, resume: 60, autostart: true, hideEmpty: false, gold: true, itemsAuto: false });
    return `<div class="section-head" style="margin-top:0"><span class="t-category">Injeção</span></div>
      <div class="field"><span>Momento da injeção</span><span class="ctl"><input type="range" min="0.3" max="2" step="0.1" value="${s.threshold}" data-act="range" data-key="threshold"><span class="num">${nf1.format(s.threshold)} s antes do fim</span></span></div>
      <div class="field"><span>Retomar o jogo após</span><span class="ctl"><input type="range" min="20" max="180" step="5" value="${s.resume}" data-act="range" data-key="resume"><span class="num">${s.resume} s</span></span></div>
      <div class="field"><span>Pasta do jogo</span><span class="ctl"><input class="s2-input" value="C:\\Riot Games\\League of Legends"><button class="s2-btn" data-act="toast" data-msg="Pasta válida.">Verificar</button></span></div>
      <div class="section-head"><span class="t-category">Assistente</span></div>
      <div class="field"><span>Importar itens ao confirmar o campeão</span><span class="ctl">${sw("itemsAuto", s.itemsAuto)}</span></div>
      <div class="field"><span>Valor dos itens no placar</span><span class="ctl">${sw("gold", s.gold)}</span></div>
      <div class="section-head"><span class="t-category">Geral</span></div>
      <div class="field"><span>Iniciar com o Windows</span><span class="ctl">${sw("autostart", s.autostart)}</span></div>
      <div class="field"><span>Ocultar categorias vazias</span><span class="ctl">${sw("hideEmpty", s.hideEmpty)}</span></div>`;
  }

  function hubDiag() {
    const d = D.diagnostics;
    const issues = S.hub.cleared ? [] : d.issues;
    return `<div class="kv"><span class="k">Versão</span><span>SEXO2 ${d.version}</span></div>
      ${d.checks.map(([k, v]) => `<div class="kv"><span class="k">${k}</span><span>${v}</span></div>`).join("")}
      <div class="section-head"><span class="t-category">Ocorrências</span>${issues.length ? `<button class="s2-btn ghost" data-act="diag-clear">Limpar</button>` : ""}</div>
      ${issues.length ? issues.map((i) => `<div class="kv"><span class="k">${i.when}</span><span>${esc(i.text)}</span></div>`).join("") : `<div class="s2-empty">Nenhuma ocorrência.</div>`}
      <div class="section-head"><span class="t-category">Créditos</span></div>
      <div class="t-small" style="line-height:1.6">Baseado no Rose (licença no arquivo LICENSE). Pengu Loader, LTK e cslol mantêm suas licenças. BORK é da Riot Games; o escudo do Galo é do Clube Atlético Mineiro. Estatísticas: LoLalytics.</div>`;
  }

  function dialog() {
    const d = S.dialog;
    if (d.kind === "delete") return `<div class="s2-dialog-backdrop s2"><div class="s2-dialog"><div class="t-heading">Excluir mod</div><p>${esc(d.name)} será removido da biblioteca.</p>
      <div class="actions"><button class="s2-btn ghost" data-act="dialog-close">Cancelar</button><button class="s2-btn primary" data-act="dialog-ok">Excluir</button></div></div></div>`;
    if (d.kind === "rename") return `<div class="s2-dialog-backdrop s2"><div class="s2-dialog"><div class="t-heading">Renomear</div><p><input class="s2-input" id="rename-input" value="${esc(d.name)}"></p>
      <div class="actions"><button class="s2-btn ghost" data-act="dialog-close">Cancelar</button><button class="s2-btn primary" data-act="dialog-ok">Salvar</button></div></div></div>`;
    if (d.kind === "fav") return `<div class="s2-dialog-backdrop s2"><div class="s2-dialog"><div class="t-heading">${esc(champName(d.champ))}</div><p>Favorita usada na seleção automática.</p>
      ${[D.favorites[d.champ], "Skin padrão", "Edição de colecionador"].map((n) => `<button class="mod-row" data-act="fav-set" data-name="${esc(n)}" aria-checked="${D.favorites[d.champ] === n}"><span class="dot"></span>${esc(n)}</button>`).join("")}
      <div class="actions" style="margin-top:12px"><button class="s2-btn ghost" data-act="dialog-close">Fechar</button></div></div></div>`;
    return "";
  }

  // ------------------------------------------------------------ simulação
  function renderSim() {
    const el = $("#sim");
    el.hidden = !S.sim.open;
    $("#stage").classList.toggle("with-sim", S.sim.open);
    if (!S.sim.open) return;
    const champSim = `
      <h3>Seleção</h3>
      <div class="row"><span class="timer">${Math.max(0, S.sim.timer)} s</span><span>${{ pick: "escolha", final: "fase final", ended: "encerrada" }[S.cs.phase]}</span></div>
      <div class="row"><button data-sim="pause">${S.sim.running ? "Pausar" : "Retomar"}</button><button data-sim="minus">−10 s</button><button data-sim="end">Encerrar fase</button><button data-sim="restart">Nova seleção</button></div>
      <div class="row"><label>Campeão <select data-sim="champ">${Object.keys(D.runes).map((k) => `<option ${k === currentChampion() ? "selected" : ""} value="${k}">${champName(k)}</option>`).join("")}</select></label></div>
      <h3>Cliente</h3>
      <div class="row"><label style="flex:1">Resposta <input type="range" min="100" max="3000" step="100" value="${S.sim.latency}" data-sim="latency"></label><span>${S.sim.latency} ms</span></div>
      <label><input type="checkbox" data-sim="fail" ${S.sim.fail ? "checked" : ""}> Recusar importações</label>
      <label><input type="checkbox" data-sim="nopage" ${S.sim.noPage ? "checked" : ""}> Sem espaço para página nova</label>
      <h3>Estatísticas</h3>
      <div class="row">${["ok", "loading", "error", "empty"].map((k) => `<button data-sim="data" data-v="${k}" style="${S.sim.data === k ? "border-color:#ddd" : ""}">${{ ok: "Normal", loading: "Carregando", error: "Erro", empty: "Sem dados" }[k]}</button>`).join("")}</div>
      <h3>Registro</h3>
      <div class="log">${S.sim.log.map((l, i) => `<div class="${i > 8 ? "old" : ""}">${esc(l)}</div>`).join("") || "—"}</div>`;
    const gameSim = `
      <h3>Partida</h3>
      <label><input type="checkbox" data-sim="tab" ${S.game.tab ? "checked" : ""}> Placar aberto (Tab)</label>
      <div class="row">${Object.keys(D.match.inventories).map((m) => `<button data-sim="minute" data-v="${m}" style="${String(S.game.minute) === m ? "border-color:#ddd" : ""}">${m} min</button>`).join("")}</div>
      <p style="margin-top:10px;line-height:1.5">Valor = soma do preço total dos itens no inventário (preços do patch ${G.patch}). Inventários simulados.</p>`;
    const homeSim = `
      <h3>Sala</h3>
      <div class="row">${["connected", "off", "error"].map((k) => `<button data-sim="roomstate" data-v="${k}">${{ connected: "Conectada", off: "Sem sala", error: "Erro" }[k]}</button>`).join("")}</div>`;
    el.innerHTML = S.view === "champ" ? champSim : S.view === "game" ? gameSim : homeSim;
  }

  // ---------------------------------------------------------------- eventos
  document.addEventListener("click", (e) => {
    const v = e.target.closest("[data-view]");
    if (v) { S.view = v.dataset.view; render(); return; }
    if (e.target.closest("#sim-toggle")) { S.sim.open = !S.sim.open; fit(); render(); return; }
    const s = e.target.closest("[data-sim]");
    if (s && s.tagName === "BUTTON") return simClick(s);
    const a = e.target.closest("[data-act]");
    if (!a || a.disabled) return;
    act(a.dataset.act, a, e);
  });

  document.addEventListener("change", (e) => {
    const t = e.target;
    if (t.dataset.sim) {
      const k = t.dataset.sim;
      if (k === "latency") S.sim.latency = +t.value;
      if (k === "fail") S.sim.fail = t.checked;
      if (k === "nopage") S.sim.noPage = t.checked;
      if (k === "tab") S.game.tab = t.checked;
      if (k === "champ") switchChampion(t.value, "campeão trocado");
      render();
      return;
    }
    if (t.dataset.act === "lane") { S.cs.lane = t.value; S.cs.opponent = null; render(); }
    if (t.dataset.act === "opponent") { S.cs.opponent = t.value || null; render(); }
    if (t.dataset.act === "profile") { S.hub.profile = t.value; toast("Perfil ativado."); }
    if (t.dataset.act === "range") { S.hub.settings[t.dataset.key] = +t.value; render(); }
  });

  document.addEventListener("keydown", (e) => {
    if (S.view === "game" && e.key === "Tab") { e.preventDefault(); S.game.tab = true; render(); }
  });
  document.addEventListener("keyup", (e) => {
    if (S.view === "game" && e.key === "Tab") { S.game.tab = false; render(); }
  });

  function simClick(s) {
    const k = s.dataset.sim;
    if (k === "pause") S.sim.running = !S.sim.running;
    if (k === "minus") { S.sim.timer = Math.max(0, S.sim.timer - 10); if (S.sim.timer === 0) endPhase(); }
    if (k === "end") endPhase();
    if (k === "restart") {
      S.cs = { phase: "pick", hover: "Ahri", champion: null, lane: "middle", opponent: null };
      S.sim.timer = 30;
      S.asst.screen = "home";
      S.items.done = null;
      importer.reset("nova seleção");
    }
    if (k === "data") S.sim.data = s.dataset.v;
    if (k === "minute") S.game.minute = +s.dataset.v;
    if (k === "roomstate") S.hub.room = s.dataset.v;
    render();
  }

  function act(name, el) {
    const p = S.asst.draft;
    switch (name) {
      case "hover": switchChampion(el.dataset.champ, `campeão em foco: ${champName(el.dataset.champ)}`); break;
      case "lock": S.cs.champion = S.cs.hover; S.cs.phase = "final"; S.sim.timer = 30; log(`${champName(S.cs.champion)} confirmado.`); break;
      case "asst-toggle": S.asst.open = !S.asst.open; break;
      case "tab": S.asst.tab = el.dataset.tab; break;
      case "rune-open": {
        const src = sourceFor(el.dataset.kind);
        S.asst.source = src;
        S.asst.draft = R.fromPerks(RD, src.rec.page);
        S.asst.screen = "tree";
        importer.choose(src.label, S.asst.draft); // importação antecipada da página original
        break;
      }
      case "tree-back": S.asst.screen = "home"; break;
      case "tree-confirm": importer.confirm(); S.asst.screen = "home"; break;
      case "rune-retry": importer.retry(); break;
      case "p-style": S.asst.draft = R.edit.primaryStyle(RD, p, +el.dataset.style); importer.edit(S.asst.draft); break;
      case "s-style": S.asst.draft = R.edit.subStyle(RD, p, +el.dataset.style); importer.edit(S.asst.draft); break;
      case "p-rune": S.asst.draft = R.edit.primaryRune(RD, p, +el.dataset.row, +el.dataset.id); importer.edit(S.asst.draft); break;
      case "s-rune": S.asst.draft = R.edit.secondaryRune(RD, p, +el.dataset.row, +el.dataset.id); importer.edit(S.asst.draft); break;
      case "shard": S.asst.draft = R.edit.shard(RD, p, +el.dataset.row, +el.dataset.id); importer.edit(S.asst.draft); break;
      case "data-retry": S.sim.data = "loading"; render(); setTimeout(() => { S.sim.data = "ok"; render(); }, 900); return;
      case "item-pick": S.items.pick[el.dataset.kind] = !S.items.pick[el.dataset.kind]; S.items.done = null; break;
      case "items-import": {
        const n = Object.values(S.items.pick).filter(Boolean).length;
        S.items.pending = true; S.items.error = null;
        setTimeout(() => {
          S.items.pending = false;
          if (!canEdit()) S.items.error = "A seleção terminou.";
          else if (S.sim.fail) S.items.error = "O cliente recusou os conjuntos.";
          else { S.items.done = n === 1 ? "Conjunto importado" : `${n} conjuntos importados`; log(`${n} conjunto(s) de itens gravados; conjuntos pessoais mantidos.`); }
          render();
        }, S.sim.latency);
        break;
      }
      case "mod": S.mod = el.dataset.mod; toast(S.mod ? "Mod selecionado." : "Sem mod."); return;
      case "open-library": S.view = "home"; S.hub.open = true; S.hub.section = "mods"; break;
      case "hub-toggle": S.hub.open = !S.hub.open; break;
      case "hub-section": S.hub.section = el.dataset.section; break;
      case "cat": S.hub.category = el.dataset.cat; break;
      case "auto": S.hub.auto = el.dataset.mode; break;
      case "fav": S.dialog = { kind: "fav", champ: el.dataset.champ }; break;
      case "fav-set": D.favorites[S.dialog.champ] = el.dataset.name; S.dialog = null; toast("Favorita salva."); return;
      case "mod-delete": S.dialog = { kind: "delete", name: el.dataset.name }; break;
      case "mod-rename": S.dialog = { kind: "rename", name: el.dataset.name }; break;
      case "dialog-close": S.dialog = null; break;
      case "dialog-ok": {
        const d = S.dialog;
        const item = D.library.find((m) => m.name === d.name);
        if (d.kind === "delete") D.library.splice(D.library.indexOf(item), 1);
        if (d.kind === "rename") item.name = $("#rename-input").value.trim() || item.name;
        S.dialog = null;
        toast(d.kind === "delete" ? "Mod excluído." : "Nome salvo.");
        return;
      }
      case "lib-import": toast("Arquivos importados: 2 (simulação)."); return;
      case "lib-export": toast("Biblioteca exportada para a pasta Exportações."); return;
      case "room": {
        const r = el.dataset.room;
        if (r === "host") { S.hub.room = "hosting"; setTimeout(() => { S.hub.room = "connected"; render(); }, 1500); }
        if (r === "join" || r === "reconnect") { S.hub.room = "hosting"; setTimeout(() => { S.hub.room = "connected"; render(); }, 900); }
        if (r === "off") S.hub.room = "off";
        break;
      }
      case "switch": S.hub.settings[el.dataset.key] = !S.hub.settings[el.dataset.key]; break;
      case "settings-save": toast("Configurações salvas."); return;
      case "diag-clear": S.hub.cleared = true; break;
      case "toast": toast(el.dataset.msg); return;
    }
    render();
  }

  // ------------------------------------------------------------- escala
  function fit() {
    const w = innerWidth - (S.sim.open ? 300 : 0) - 24;
    const h = innerHeight - 40 - 24;
    document.documentElement.style.setProperty("--scale", Math.min(w / 1280, h / 720, 1.25).toFixed(3));
  }
  addEventListener("resize", fit);
  fit();
  log("Protótipo carregado. Dados simulados.");
  render();
})();
