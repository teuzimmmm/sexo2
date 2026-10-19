/** @name ROSE-Hub @description Single native navigation entry for all Rose tools. */
(function () {
  'use strict';
  function start() {
    if (!document.body || !document.head) {
      setTimeout(start, 100);
      return;
    }
    if (window.__roseHub) return;
    const css = document.createElement('style');
    css.textContent = `
  #rose-amigos-launch,#rose-party-button,#rose-party-lobby-button,#rose-party-champ-status,.rsp-launch{display:none!important}
  #rose-hub{position:fixed;z-index:11000;width:min(820px,calc(100vw - 24px));height:min(560px,calc(100vh - 100px));display:grid;grid-template-columns:172px 1fr;color:var(--s2-fg);background:var(--s2-surface);border:1px solid var(--s2-line);font:13px/1.4 var(--s2-font-text);box-shadow:0 8px 30px rgba(0,0,0,.55)}
  #rose-hub[hidden],#rose-hub [hidden]{display:none!important}#rose-hub *{box-sizing:border-box}
  .menu_item_Golden.Rose[data-sexo2-update] .menu-item-icon-wrapper::after{content:'';position:absolute;width:5px;height:5px;background:var(--s2-fg);border-radius:50%;right:0;top:0}
  #rose-hub>nav{display:flex;flex-direction:column;border-right:1px solid var(--s2-line);padding:12px 0}
  #rose-hub>nav .brand{font:600 20px var(--s2-font-display);letter-spacing:.06em;padding:0 16px 12px}
  #rose-hub>nav button{text-align:left;padding:8px 16px;color:var(--s2-fg-2);font-size:14px;background:transparent;border:0;cursor:pointer}
  #rose-hub>nav button:hover{color:var(--s2-fg);background:var(--s2-hover)}
  #rose-hub>nav button.active{color:var(--s2-fg);box-shadow:inset 2px 0 0 var(--s2-fg);background:var(--s2-surface-2)}
  #rose-hub .hub-main{display:flex;flex-direction:column;min-width:0;min-height:0}
  #rose-hub .hub-head{height:52px;flex:none;display:flex;align-items:center;gap:12px;padding:0 16px;border-bottom:1px solid var(--s2-line)}
  #rose-hub .hub-head .title{flex:1;font:500 18px/1.15 var(--s2-font-display);text-transform:uppercase;letter-spacing:.02em}
  #rose-hub .hub-head .hub-close{background:transparent;border:0;color:var(--s2-fg-2);cursor:pointer;font-size:14px;padding:4px 8px}
  #rose-hub button,#rose-hub select,#rose-hub input{font:inherit;color:var(--s2-fg);background:var(--s2-surface-2);border:1px solid var(--s2-line);border-radius:0;padding:5px 10px;max-width:100%}
  #rose-hub button{cursor:pointer;font-weight:600}#rose-hub button:disabled{opacity:.45;cursor:default}#rose-hub button:hover{background:var(--s2-hover)}
  #rose-hub-content{flex:1;overflow:auto;padding:12px 16px}
  #rose-hub-content .hub-subnav{display:flex;margin-bottom:12px;border-bottom:1px solid var(--s2-line)}
  #rose-hub-content .hub-subnav button{border:0!important;background:transparent!important;padding:7px 12px 6px;font:500 13px var(--s2-font-display)!important;letter-spacing:.05em;text-transform:uppercase;color:var(--s2-fg-3)!important}
  #rose-hub-content .hub-subnav button.active{color:var(--s2-fg)!important;box-shadow:inset 0 -2px 0 var(--s2-fg)}
  #rose-hub-content h2,#rose-hub-content h3,#rose-hub-content .rsp-title{font:500 13px/1.2 var(--s2-font-display)!important;text-transform:uppercase;letter-spacing:.06em;color:var(--s2-fg-2)!important;margin:14px 0 8px!important}
  #rose-hub-content .ra-muted,#rose-hub-content small,#rose-hub-content .s2-help{color:var(--s2-fg-3)!important}
  #rose-hub-content .ra-card,#rose-hub-content .s2-mod-row,#rose-hub-content footer{border-color:var(--s2-line)!important}
  #rose-hub-content .ra-notice{border-left-color:var(--s2-fg)!important;color:var(--s2-fg)!important}
  #rose-hub-content .ra-active{border-color:var(--s2-fg)!important;background:var(--s2-hover)!important}
  #rose-hub-content [data-hub-section="Mods"] #sexo2-mod-library{border-top:0;margin-top:0;padding-top:0}
  #rose-hub-content [data-hub-section="Mods"] #sexo2-mod-library>button:first-of-type{display:none}
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
  #rose-hub-content button,#rose-hub-content input,#rose-hub-content select{border-radius:0!important;background:var(--s2-surface-2)!important;color:var(--s2-fg)!important;border-color:var(--s2-line)!important;font-family:var(--s2-font-text)!important}
  #rose-hub-content #rose-settings-flyout{font:13px var(--s2-font-text)!important;color:var(--s2-fg)!important}
  #rose-hub #rose-settings-flyout{min-width:0!important;align-items:stretch!important}
  #rose-hub #rose-settings-flyout .sexo2-settings-content{display:block!important;width:100%!important;min-width:0!important;max-width:100%!important;background:transparent!important;border:0!important;padding:0!important;box-shadow:none!important}
  #rose-hub #rose-settings-flyout .sexo2-settings-content>div{min-width:0;max-width:100%;overflow-wrap:anywhere}
  #rose-hub-content #rose-settings-flyout .settings-section{width:100%!important;padding:8px 0!important;margin:0!important;border-bottom:1px solid var(--s2-line)}
  #rose-hub-content #rose-settings-flyout details{width:100%;font-size:11px;color:var(--s2-fg-3);margin-top:12px}
  #rose-hub input[type=checkbox]{appearance:auto!important;-webkit-appearance:checkbox!important;accent-color:var(--s2-fg);width:16px!important;height:16px!important;padding:0!important;flex:none;cursor:pointer}
  `;
    document.head.append(css);
    const panel = document.createElement('section');
    panel.id = 'rose-hub';
    panel.className = 's2';
    panel.hidden = true;
    panel.setAttribute('role', 'dialog');
    panel.setAttribute('aria-label', 'SEXO2');
    const nav = document.createElement('nav'),
      main = document.createElement('div'),
      head = document.createElement('div'),
      title = document.createElement('span'),
      content = document.createElement('div');
    main.className = 'hub-main';
    head.className = 'hub-head';
    title.className = 'title';
    content.id = 'rose-hub-content';
    head.append(title);
    main.append(head, content);
    panel.append(nav, main);
    document.body.append(panel);
    let current = 'Sala',
      anchor = null,
      phase = null,
      swift = false;
    const containers = {};
    function dispatch(type, detail) {
      window.dispatchEvent(new CustomEvent(type, { detail }));
    }
    function hide() {
      panel.hidden = true;
    }
    function position() {
      const rect = anchor?.getBoundingClientRect();
      if (!rect) return;
      panel.style.top = Math.min(rect.bottom + 8, window.innerHeight - 120) + 'px';
      panel.style.left =
        Math.max(12, Math.min(rect.right - panel.offsetWidth, window.innerWidth - panel.offsetWidth - 12)) + 'px';
    }
    function createButton(text, fn) {
      const b = document.createElement('button');
      b.textContent = text;
      b.type = 'button';
      b.onclick = fn;
      return b;
    }
    function subnav(target, items, active) {
      let menu = target.querySelector(':scope>.hub-subnav');
      if (!menu) {
        menu = document.createElement('div');
        menu.className = 'hub-subnav';
        target.prepend(menu);
      }
      menu.hidden = false;
      menu.replaceChildren(
        ...items.map(([label, fn]) => {
          const b = createButton(label, fn);
          if (label === active) b.className = 'active';
          return b;
        }),
      );
    }
    // Menus do painel SEXO2 (D-115); Swiftplay só aparece quando o jogo é Swiftplay.
    const sections = () => ['Sala', 'Favoritas', 'Configurações', 'Suporte', ...(swift ? ['Swiftplay'] : [])];
    function mount() {
      nav.replaceChildren();
      const brand = document.createElement('div');
      brand.className = 'brand';
      brand.textContent = 'SEXO2';
      nav.append(brand);
      for (const label of sections()) {
        const b = createButton(label, () => {
          current = label;
          mount();
        });
        if (current === label) b.className = 'active';
        nav.append(b);
      }
      title.textContent = current;
      const x = createButton('✕', hide);
      x.className = 'hub-close';
      x.setAttribute('aria-label', 'Fechar painel');
      head.querySelector('.hub-close')?.remove();
      head.append(x);
      for (const node of Object.values(containers)) node.hidden = true;
      if (!containers[current]) {
        containers[current] = document.createElement('div');
        containers[current].dataset.hubSection = current;
        content.append(containers[current]);
      }
      const target = containers[current];
      target.hidden = false;
      if (current === 'Sala') {
        dispatch('rose-hub-friends', { target, tab: 'Sala' });
        const legacyParty = document.getElementById('rose-party-panel');
        if (legacyParty) legacyParty.hidden = true;
      } else if (current === 'Favoritas') {
        dispatch('rose-hub-friends', { target, tab: 'Favoritas' });
      } else if (current === 'Swiftplay') {
        dispatch('rose-hub-swiftplay', { target });
      } else if (current === 'Suporte') {
        dispatch('rose-hub-settings-close');
        dispatch('rose-hub-friends', { target, tab: 'Preparo' });
      } else {
        showSettings(target);
      }
      position();
    }
    function showSettings(target) {
      const friends = document.getElementById('rose-amigos-panel');
      if (friends && target.contains(friends)) friends.hidden = true;
      dispatch('rose-hub-settings', { target, anchor });
    }
    window.__roseHub = {
      open(navItem) {
        anchor = navItem;
        if (phase === 'InProgress') return;
        panel.hidden = !panel.hidden;
        if (!panel.hidden) {
          current = 'Sala';
          mount();
        }
      },
      show(label) {
        anchor = anchor || document.querySelector('lol-uikit-navigation-item.menu_item_Golden.Rose');
        if (phase === 'InProgress') return;
        current = label;
        panel.hidden = false;
        mount();
      },
      close: hide,
      refreshSettings() {
        if (current === 'Configurações') showSettings(containers[current]);
      },
    };
    window.addEventListener(
      'rose-open-settings',
      (e) => {
        e.stopImmediatePropagation();
        window.__roseHub.open(
          e.detail?.navItem || document.querySelector('lol-uikit-navigation-item.menu_item_Golden.Rose'),
        );
      },
      true,
    );
    window.addEventListener('rose-swiftplay-state', (e) => {
      const active = e.detail?.active === true;
      if (active === swift) return;
      swift = active;
      if (!swift && current === 'Swiftplay') current = 'Sala';
      if (!panel.hidden) mount();
    });
    window.addEventListener('resize', position);
    document.addEventListener('pointerdown', (e) => {
      if (
        !panel.hidden &&
        !panel.contains(e.target) &&
        !anchor?.contains(e.target) &&
        !e.target.closest('lol-uikit-dialog,.chroma-view,[id$="-flyout"],[id$="-dialog"]')
      )
        hide();
    });
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') hide();
    });
    document.addEventListener(
      'click',
      (e) => {
        if (e.target.closest('.skin-selection-item') && !e.target.closest('.lu-random-dice-button,.chroma-button'))
          window.__roseBridge?.send({ type: 'manual-skin-choice' });
      },
      true,
    );
    let attached = false;
    setInterval(() => {
      if (!panel.isConnected) document.body.append(panel);
      const bridge = window.__roseBridge;
      if (bridge && !attached) {
        attached = true;
        bridge.subscribe('phase-change', (data) => {
          phase = data.phase;
          if (phase === 'InProgress') hide();
        });
      }
      if (!panel.hidden) position();
    }, 1000);
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start, { once: true });
  else start();
})();
