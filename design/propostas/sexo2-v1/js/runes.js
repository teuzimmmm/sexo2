/*
 * Lógica das runas do protótipo, sem DOM: modelo da página, regras de validade,
 * edição e o controlador de importação simulado (mesmo comportamento do serviço real).
 */
(function (root) {
  "use strict";

  function index(game) {
    const perks = {};
    const styles = {};
    for (const style of game.styles) {
      styles[style.id] = style;
      style.slots.forEach((slot, row) => {
        for (const rune of slot) perks[rune.id] = { ...rune, style: style.id, row };
      });
    }
    return { perks, styles, shardRows: game.shards.rows, shardNames: game.shards.names };
  }

  // Página: { primary, sub, keystone, minor: [3], secondary: [{row, id}, ...] (até 2), shards: [3] }
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

  function same(a, b) {
    if (!a || !b) return false;
    return a.primary === b.primary && a.sub === b.sub && toPerks(a).join() === toPerks(b).join();
  }

  // Regras de montagem: as mesmas que o serviço aplica com /lol-perks/v1/styles do cliente.
  function validate(data, p) {
    const errors = [];
    const prim = data.styles[p.primary];
    const sub = data.styles[p.sub];
    if (!prim) errors.push("primary");
    if (!sub || p.sub === p.primary) errors.push("sub");
    if (prim) {
      if (!prim.slots[0].some((r) => r.id === p.keystone)) errors.push("keystone");
      for (let row = 1; row <= 3; row++) {
        if (!prim.slots[row].some((r) => r.id === p.minor[row - 1])) errors.push("minor" + row);
      }
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

  // Edição, como no cliente: trocar de árvore limpa as escolhas daquela árvore.
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
    // Duas runas de linhas diferentes; a terceira escolha substitui a mais antiga.
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

  /*
   * Controlador de importação (simulação do serviço do SEXO2).
   * - displayed: recomendação exibida (não importa nada);
   * - chosen: escolha do usuário (card ou edição);
   * - applied: última página que o cliente confirmou.
   * Edições válidas são agrupadas (debounce) e enviadas uma de cada vez; a mais recente vence.
   * Respostas de outra sessão ou geração antiga são descartadas. Sem edição permitida, nada é enviado.
   */
  function createImporter(opts) {
    const st = {
      session: 1,
      generation: 0,
      chosen: null,
      applied: null,
      inflight: null,
      resend: false,
      timer: null,
      error: null,
    };

    function log(msg) { opts.log && opts.log(msg); }
    function changed() { opts.onChange && opts.onChange(snapshot()); }

    function snapshot() {
      return {
        chosen: st.chosen,
        applied: st.applied,
        pending: !!st.inflight || !!st.timer,
        error: st.error,
        incomplete: !!st.chosen && validate(opts.data, st.chosen.page).length > 0,
      };
    }

    function send() {
      if (st.timer) { clearTimeout(st.timer); st.timer = null; }
      const choice = st.chosen;
      if (!choice) return;
      if (validate(opts.data, choice.page).length) { changed(); return; }
      if (st.applied && same(st.applied.page, choice.page)) { st.error = null; changed(); return; }
      if (!opts.canEdit()) { log("Nada enviado: a seleção não permite alterações."); changed(); return; }
      if (st.inflight) { st.resend = true; log("Edição guardada; envio após a resposta atual."); changed(); return; }
      const gen = ++st.generation;
      const session = st.session;
      const page = { ...choice, page: clone(choice.page) };
      st.inflight = { gen, session, page };
      st.error = null;
      log(`#${gen} enviada (${choice.label}).`);
      changed();
      opts.transport(page, (result) => complete(gen, session, page, result));
    }

    function complete(gen, session, page, result) {
      if (session !== st.session) {
        log(`#${gen} descartada: era de outra seleção.`);
        return;
      }
      if (!st.inflight || st.inflight.gen !== gen) {
        log(`#${gen} descartada: resposta antiga.`);
        return;
      }
      st.inflight = null;
      if (result.ok) {
        st.applied = page;
        st.error = null;
        log(`#${gen} confirmada pelo cliente.`);
      } else {
        st.error = result.error;
        log(`#${gen} falhou (${result.error}). Mantida a última página confirmada.`);
      }
      const newer = st.resend;
      st.resend = false;
      changed();
      if (newer) send();
    }

    return {
      snapshot,
      choose(label, page) {
        st.chosen = { label, page: clone(page), edited: false };
        st.error = null;
        send();
      },
      edit(page) {
        if (!st.chosen) return;
        st.chosen = { label: "Personalizada", page: clone(page), edited: true };
        if (st.timer) clearTimeout(st.timer);
        if (validate(opts.data, page).length) { changed(); return; }
        st.timer = setTimeout(() => { st.timer = null; send(); }, opts.debounceMs);
        changed();
      },
      confirm() { send(); },
      retry() { send(); },
      // Troca de campeão, nova seleção, desconexão: nada pendente pode chegar à sessão nova.
      reset(reason) {
        if (st.timer) clearTimeout(st.timer);
        st.session += 1;
        st.timer = null;
        st.inflight = null;
        st.resend = false;
        st.chosen = null;
        st.applied = null;
        st.error = null;
        log(`Nova sessão (${reason}). Operações anteriores invalidadas.`);
        changed();
      },
      // Fim da seleção: cancela o que não foi enviado; preserva a última página confirmada.
      close() {
        if (st.timer) { clearTimeout(st.timer); st.timer = null; log("Edição pendente não enviada: a seleção terminou."); }
        changed();
      },
    };
  }

  root.S2Runes = { index, fromPerks, toPerks, clone, same, validate, edit, createImporter };
})(typeof window !== "undefined" ? window : globalThis);
