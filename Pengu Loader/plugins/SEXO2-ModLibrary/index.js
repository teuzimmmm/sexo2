/** @name SEXO2-ModLibrary @description Biblioteca própria, integrada ao painel. */
(() => {
  'use strict';
  if (window.__sexo2ModLibrary) return;
  let root,
    bridge,
    status,
    list,
    incoming,
    summary,
    pages,
    pageLabel,
    search,
    category,
    lastData,
    activeEdit = null,
    pageIndex = 0;
  const editors = new Map();
  const categories = {
    all: 'Todas',
    skins: 'Skins',
    maps: 'Mapas',
    fonts: 'Fontes',
    announcers: 'Anunciadores',
    ui: 'Interface',
    voiceover: 'Vozes',
    loading_screen: 'Carregamento',
    vfx: 'Efeitos visuais',
    sfx: 'Sons',
    others: 'Outros',
  };
  function el(tag, text) {
    const node = document.createElement(tag);
    if (text) node.textContent = text;
    return node;
  }
  function button(text, fn) {
    const node = el('button', text);
    node.type = 'button';
    node.onclick = fn;
    return node;
  }
  function send(action, values = {}) {
    if (!bridge?.ready) {
      status.textContent = 'Conecte o SEXO2 para usar a biblioteca.';
      return;
    }
    bridge.send({ type: 'sexo2-library-request', action, ...values });
  }
  function options(select, items, value) {
    select.replaceChildren();
    for (const item of items) {
      const option = el('option', item.name);
      option.value = item.id;
      option.selected = String(item.id) === String(value);
      select.append(option);
    }
  }
  function build() {
    root = el('section');
    root.id = 'sexo2-mod-library';
    root.setAttribute('aria-label', 'Biblioteca de mods');
    const style = el('style');
    style.textContent = `#sexo2-mod-library{border-top:1px solid var(--s2-line);margin-top:16px;padding-top:12px}#sexo2-mod-library .s2-mod-row{border-bottom:1px solid var(--s2-line);padding:10px 0}#sexo2-mod-library .s2-mod-row strong{display:block;color:var(--s2-fg);font-weight:400;overflow-wrap:anywhere}#sexo2-mod-library small{display:block;color:var(--s2-fg-2);margin:5px 0}#sexo2-mod-library .s2-mod-actions{display:flex;gap:6px;flex-wrap:wrap;margin:6px 0}#sexo2-mod-library input{width:100%}#sexo2-mod-library select{max-width:100%}#sexo2-mod-library select[multiple]{width:100%;height:110px}#sexo2-mod-library .s2-mod-list{max-height:220px;overflow:auto}#sexo2-mod-library [role=status]{overflow-wrap:anywhere}`;
    root.append(
      style,
      button('← Configurações', () => {
        root.hidden = true;
        window.dispatchEvent(new CustomEvent('sexo2-mod-library-close'));
      }),
      el('h3', 'Biblioteca de mods'),
    );
    const help = el(
      'p',
      'Cole .fantome, .modpkg ou .zip na pasta de entrada. Casos não identificados ficam para revisão. Para restaurar a biblioteca, cole o ZIP exportado.',
    );
    help.className = 's2-help';
    root.append(help);
    const actions = el('div');
    actions.className = 's2-mod-actions';
    category = el('select');
    category.setAttribute('aria-label', 'Categoria da biblioteca');
    options(
      category,
      Object.entries(categories).map(([id, name]) => ({ id, name })),
      'all',
    );
    category.onchange = () => {
      pageIndex = 0;
      renderMods();
    };
    actions.append(
      category,
      button('Adicionar em lote', () =>
        send('inbox', { category: category.value === 'all' ? 'skins' : category.value }),
      ),
      button('Parar importação', () => send('stop')),
      button('Atualizar lista', () => send('list')),
    );
    root.append(actions);
    const exportActions = el('div');
    exportActions.className = 's2-mod-actions';
    exportActions.append(
      button('Exportar todos', () => send('export')),
      button('Pasta de exportações', () => send('exports')),
    );
    root.append(exportActions);
    status = el('p', 'Carregando biblioteca…');
    status.setAttribute('role', 'status');
    root.append(status);
    search = el('input');
    search.type = 'search';
    search.placeholder = 'Buscar mod ou campeão';
    search.setAttribute('aria-label', 'Buscar mod');
    search.oninput = () => {
      pageIndex = 0;
      renderMods();
    };
    root.append(search);
    pages = el('div');
    pages.className = 's2-mod-actions';
    pageLabel = el('small');
    pages.append(
      button('Anterior', () => {
        pageIndex = Math.max(0, pageIndex - 1);
        renderMods();
      }),
      pageLabel,
      button('Próxima', () => {
        pageIndex++;
        renderMods();
      }),
    );
    root.append(pages);
    list = el('div');
    list.className = 's2-mod-list';
    root.append(list, el('h3', 'Entrada e revisão'));
    summary = el('small');
    root.append(summary);
    incoming = el('div');
    incoming.className = 's2-mod-list';
    root.append(incoming);
  }
  function championName(cid) {
    return lastData?.champions?.find((c) => c.id === cid)?.name || '';
  }
  function renderMods() {
    if (!lastData) return;
    if (activeEdit) {
      editors.delete(activeEdit);
      activeEdit = null;
    }
    const pos = list.scrollTop;
    list.replaceChildren();
    const query = search.value.toLocaleLowerCase();
    const filtered = (lastData.mods || []).filter(
      (mod) =>
        (category.value === 'all' || mod.category === category.value) &&
        (!query || `${mod.name} ${championName(mod.championId)}`.toLocaleLowerCase().includes(query)),
    );
    pageIndex = Math.max(0, Math.min(pageIndex, Math.ceil(filtered.length / 50) - 1));
    pages.hidden = filtered.length <= 50;
    pageLabel.textContent = `${pageIndex * 50 + 1}–${Math.min(filtered.length, (pageIndex + 1) * 50)} de ${filtered.length}`;
    pages.firstChild.disabled = pageIndex === 0;
    pages.lastChild.disabled = (pageIndex + 1) * 50 >= filtered.length;
    for (const mod of filtered.slice(pageIndex * 50, (pageIndex + 1) * 50)) {
      const row = el('div');
      row.className = 's2-mod-row';
      row.append(
        el('strong', mod.name),
        el('small', [categories[mod.category], championName(mod.championId)].filter(Boolean).join(' · ')),
      );
      const actions = el('div');
      actions.className = 's2-mod-actions';
      actions.append(
        button('Editar', () => edit(mod, row)),
        button('Remover', () => {
          if (row.querySelector('.s2-mod-confirm')) return;
          const confirm = el('div');
          confirm.className = 's2-mod-confirm';
          confirm.append(
            el('small', 'Remover este mod da biblioteca?'),
            button('Confirmar remoção', () => send('delete', { id: mod.id })),
            button('Cancelar', () => confirm.remove()),
          );
          row.append(confirm);
        }),
      );
      row.append(actions);
      list.append(row);
    }
    if (!list.childElementCount) list.append(el('p', 'Nenhum mod nesta busca.'));
    list.scrollTop = pos;
  }
  function edit(mod, row) {
    if (row.querySelector('.s2-mod-editor')) return;
    const area = el('div');
    area.className = 's2-mod-editor';
    const name = el('input');
    name.value = mod.name;
    name.setAttribute('aria-label', 'Nome do mod');
    area.append(
      name,
      button('Salvar nome', () => send('rename', { id: mod.id, name: name.value })),
    );
    if (mod.category === 'skins') {
      const select = el('select');
      select.multiple = true;
      select.setAttribute('aria-label', 'Skins-base do mod');
      options(
        select,
        (mod.targets || []).map((id) => ({ id, name: id === mod.championId * 1000 ? 'Padrão' : 'Skin-base atual' })),
        mod.targets?.[0],
      );
      for (const option of select.options) option.selected = true;
      editors.set(mod.id, { select, mod });
      area.append(
        el('small', 'Aplicar nas skins-base selecionadas:'),
        select,
        button('Salvar skins-base', () =>
          send('targets', { id: mod.id, targets: [...select.selectedOptions].map((o) => Number(o.value)) }),
        ),
      );
      send('skins', { id: mod.id, championId: mod.championId });
    }
    area.append(
      button('Fechar edição', () => {
        area.remove();
        editors.delete(mod.id);
        activeEdit = null;
        renderMods();
      }),
    );
    row.append(area);
    activeEdit = mod.id;
  }
  function renderIncoming() {
    const pos = incoming.scrollTop;
    const entries = lastData.incoming || [],
      completed = entries.filter((item) => ['importado', 'duplicado', 'restaurado', 'preparado'].includes(item.status));
    summary.textContent = completed.length
      ? `${completed.length} arquivo(s) concluído(s). Originais preservados.`
      : 'Cole os arquivos na pasta de entrada para começar.';
    const live = new Set(entries.map((item) => item.id));
    for (const row of incoming.querySelectorAll('[data-entry]')) if (!live.has(row.dataset.entry)) row.remove();
    for (const item of completed) {
      incoming.querySelector(`[data-entry="${item.id}"]`)?.remove();
      editors.delete(item.id);
    }

    for (const item of entries.filter(
      (item) => !['importado', 'duplicado', 'restaurado', 'preparado'].includes(item.status),
    )) {
      let row = incoming.querySelector(`[data-entry="${item.id}"]`);
      if (!row) {
        row = el('div');
        row.className = 's2-mod-row';
        row.dataset.entry = item.id;
        row.append(el('strong', item.displayName || item.file), el('small'));
        incoming.append(row);
      }
      if (item.status === 'erro' && !row.querySelector('.s2-retry')) {
        const retry = button('Repetir', () => send('retry', { id: item.id }));
        retry.className = 's2-retry';
        row.append(retry);
      }
      row.querySelector('small').textContent =
        {
          importado: 'Importado',
          duplicado: 'Já existe na biblioteca',
          restaurado: 'Biblioteca restaurada',
          revisar: 'Confirme o campeão e a skin-base',
          aguardando: 'Aguardando sair da seleção ou partida',
          erro: item.error,
          analisando: 'Analisando…',
        }[item.status] || item.status;
      if (
        (item.status === 'revisar' || item.status === 'erro') &&
        !row.querySelector('select') &&
        item.category === 'skins'
      ) {
        const champ = el('select');
        champ.setAttribute('aria-label', 'Campeão do mod');
        options(champ, [{ id: '', name: 'Escolher campeão' }, ...lastData.champions], item.championId || '');
        const skin = el('select');
        skin.setAttribute('aria-label', 'Skin-base do mod');
        const setBase = () =>
          options(skin, [{ id: Number(champ.value) * 1000, name: 'Padrão' }], Number(champ.value) * 1000);
        champ.onchange = () => {
          setBase();
          editors.set(item.id, { select: skin, cid: Number(champ.value) });
          if (champ.value) send('skins', { id: item.id, championId: Number(champ.value) });
        };
        setBase();
        row.append(
          champ,
          skin,
          button('Importar', () => {
            if (champ.value)
              send('resolve', { id: item.id, championId: Number(champ.value), targets: [Number(skin.value)] });
          }),
        );
      }
      if (item.status === 'importado' || item.status === 'duplicado' || item.status === 'restaurado')
        for (const node of row.querySelectorAll('select,button')) node.remove();
    }
    if (!(lastData.incoming || []).length && !incoming.childElementCount)
      incoming.append(el('p', 'Nenhum arquivo novo.'));
    incoming.scrollTop = pos;
  }
  function receive(data) {
    lastData = data;
    status.textContent = data.message || '';
    if (activeEdit && !(data.mods || []).some((mod) => mod.id === activeEdit)) {
      editors.delete(activeEdit);
      activeEdit = null;
    }
    // Keep editing controls intact while background imports report progress.
    if (!activeEdit) renderMods();
    renderIncoming();
  }
  function skins(data) {
    const editor = editors.get(data.id);
    if (!editor || (editor.cid && editor.cid !== data.championId)) return;
    const selected = editor.mod?.targets || [Number(editor.select.value)];
    const values = data.skins?.length ? data.skins : [{ id: data.championId * 1000, name: 'Padrão' }];
    options(editor.select, values, selected[0]);
    if (editor.select.multiple)
      for (const option of editor.select.options) option.selected = selected.includes(Number(option.value));
  }
  window.__sexo2ModLibrary = {
    open(target, selected = 'all', add = false) {
      if (!root) build();
      target.append(root);
      root.hidden = false;
      category.value = selected;
      send('list');
      if (add) send('inbox', { category: selected === 'all' ? 'skins' : selected });
      root.scrollIntoView({ block: 'nearest' });
    },
  };
  window.addEventListener('sexo2-mod-library-open', (event) =>
    window.__sexo2ModLibrary.open(event.detail.target, event.detail.category, event.detail.add),
  );
  const timer = setInterval(() => {
    if (!bridge && window.__sexo2Bridge) {
      bridge = window.__sexo2Bridge;
      bridge.subscribe('sexo2-library-state', receive);
      bridge.subscribe('sexo2-library-skins', skins);
      bridge.onReady(() => {
        if (root) send('list');
      });
      clearInterval(timer);
    }
  }, 100);
})();
