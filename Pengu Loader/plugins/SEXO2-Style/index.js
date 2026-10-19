/**
 * @name SEXO2-Style
 * @description Fontes, cores e componentes aprovados (D-007, D-014, D-017), compartilhados pelos plugins SEXO2.
 *
 * Mesmos valores de design/propostas/sexo2-v1/css/styles.css. As fontes vêm da pasta assets do
 * SEXO2 pela ponte local (/asset/fonts/...), nunca de serviço externo.
 */
(function () {
  "use strict";

  function fontFaces(port) {
    const base = `http://127.0.0.1:${port}/asset/fonts`;
    return `
@font-face{font-family:"Oswald";font-style:normal;font-display:swap;font-weight:200 700;src:url("${base}/oswald-latin-wght-normal.woff2") format("woff2-variations")}
@font-face{font-family:"Inter";font-style:normal;font-display:swap;font-weight:100 900;src:url("${base}/inter-latin-wght-normal.woff2") format("woff2-variations")}`;
  }

  const CSS = `
:root{
  --s2-font-display:"Oswald","Segoe UI",sans-serif;--s2-font-text:"Inter","Segoe UI",sans-serif;--s2-numeric-stats:tabular-nums;
  --s2-bg:#0d0e10;--s2-surface:#15171a;--s2-surface-2:#1b1d21;--s2-hover:#22252a;--s2-line:#2a2d32;
  --s2-fg:#ececec;--s2-fg-2:#a4a9b0;--s2-fg-3:#6e747b;--s2-ally:#4f8cff;--s2-enemy:#e5484d;--s2-focus:#ececec;
  --t-display:34px;--t-heading:18px;--t-category:12px;--t-body:14px;--t-small:12px;--t-stat:14px;--t-stat-big:30px;
  --sp-1:4px;--sp-2:8px;--sp-3:12px;--sp-4:16px;
}
.s2{font:400 var(--t-body)/1.4 var(--s2-font-text);color:var(--s2-fg);}
.s2 *{box-sizing:border-box;}
.s2 button{font:inherit;color:inherit;background:none;border:0;cursor:pointer;padding:0;}
.s2 input,.s2 select{font:inherit;color:inherit;}
.s2 img{display:block;}
.s2 .num{font-variant-numeric:var(--s2-numeric-stats);}
.s2 .t-heading{font:500 var(--t-heading)/1.15 var(--s2-font-display);text-transform:uppercase;letter-spacing:.02em;}
.s2 .t-category{font:500 var(--t-category)/1.2 var(--s2-font-display);text-transform:uppercase;letter-spacing:.06em;color:var(--s2-fg-2);}
.s2 .t-small{font-size:var(--t-small);color:var(--s2-fg-2);}
.s2 .t-muted{color:var(--s2-fg-3);}
.s2 .t-stat{font-size:var(--t-stat);font-weight:600;font-variant-numeric:var(--s2-numeric-stats);}
.s2 .t-stat-big{font:500 var(--t-stat-big)/1 var(--s2-font-display);font-variant-numeric:var(--s2-numeric-stats);}
.s2-panel{background:var(--s2-surface);border:1px solid var(--s2-line);}
.s2 .s2-btn{height:28px;padding:0 var(--sp-3);border:1px solid var(--s2-line);background:var(--s2-surface-2);font-size:13px;font-weight:600;white-space:nowrap;}
.s2 .s2-btn:hover{background:var(--s2-hover);}
.s2 .s2-btn.primary{background:var(--s2-fg);color:#111;border-color:var(--s2-fg);}
.s2 .s2-btn.primary:hover{background:#fff;}
.s2 .s2-btn.ghost{background:transparent;border-color:transparent;color:var(--s2-fg-2);}
.s2 .s2-btn.ghost:hover{color:var(--s2-fg);background:var(--s2-hover);}
.s2 .s2-btn:disabled{opacity:.45;cursor:default;}
.s2 .s2-tabs{display:flex;border-bottom:1px solid var(--s2-line);}
.s2 .s2-tabs button{padding:7px var(--sp-3) 6px;font:500 13px var(--s2-font-display);letter-spacing:.05em;text-transform:uppercase;color:var(--s2-fg-3);}
.s2 .s2-tabs button:hover{color:var(--s2-fg-2);}
.s2 .s2-tabs button[aria-selected="true"]{color:var(--s2-fg);box-shadow:inset 0 -2px 0 var(--s2-fg);}
.s2 .s2-select{height:28px;background:var(--s2-surface-2);border:1px solid var(--s2-line);padding:0 var(--sp-2);font-size:13px;}
.s2 .s2-input{height:28px;background:var(--s2-bg);border:1px solid var(--s2-line);padding:0 var(--sp-2);font-size:13px;width:100%;}
.s2 .s2-icon{border-radius:50%;background:#000;flex:none;}
.s2 .s2-icon.sq{border-radius:2px;}
.s2 .s2-spinner{width:12px;height:12px;border:2px solid var(--s2-line);border-top-color:var(--s2-fg);border-radius:50%;animation:s2spin .8s linear infinite;flex:none;}
@keyframes s2spin{to{transform:rotate(360deg)}}
.s2 .s2-empty{padding:var(--sp-4) var(--sp-3);color:var(--s2-fg-3);font-size:13px;}
.s2-tip{position:fixed;z-index:20000;pointer-events:none;max-width:260px;padding:6px 8px;background:#0b0c0d;border:1px solid #2a2d32;color:#ddd;font:12px/1.4 var(--s2-font-text);}
.s2-tip b{display:block;font-weight:600;margin-bottom:2px;}
.s2-tip[hidden]{display:none;}
`;

  // Tooltips "Título|Texto" em qualquer elemento com data-tip dentro de .s2 (como no protótipo).
  function installTips() {
    const tip = document.createElement("div");
    tip.className = "s2-tip";
    tip.hidden = true;
    document.body.appendChild(tip);
    document.addEventListener("mouseover", (e) => {
      const el = e.target.closest && e.target.closest(".s2 [data-tip]");
      if (!el) {
        tip.hidden = true;
        return;
      }
      const [title, text] = el.dataset.tip.split("|");
      tip.replaceChildren();
      const b = document.createElement("b");
      b.textContent = title;
      tip.append(b);
      if (text) tip.append(text);
      const r = el.getBoundingClientRect();
      tip.hidden = false;
      const x = Math.min(r.left, window.innerWidth - tip.offsetWidth - 8);
      const y = r.top - tip.offsetHeight - 6 < 0 ? r.bottom + 6 : r.top - tip.offsetHeight - 6;
      tip.style.left = Math.max(8, x) + "px";
      tip.style.top = y + "px";
    });
  }

  if (typeof window === "undefined" && typeof module !== "undefined" && module.exports) {
    module.exports = { CSS, fontFaces };
    return;
  }

  function start() {
    if (!document.body || !document.head) {
      setTimeout(start, 100);
      return;
    }
    if (window.__sexo2Style) return;
    window.__sexo2Style = true;
    const style = document.createElement("style");
    style.id = "sexo2-style";
    style.textContent = CSS;
    document.head.appendChild(style);
    const fonts = document.createElement("style");
    fonts.id = "sexo2-fonts";
    document.head.appendChild(fonts);
    const setFonts = () => {
      const bridge = window.__sexo2Bridge;
      fonts.textContent = fontFaces(bridge ? bridge.port : 50000);
      return !!bridge;
    };
    if (!setFonts()) {
      // A ponte expõe a porta pouco depois do carregamento; tenta de novo só até encontrá-la.
      const retry = setInterval(() => setFonts() && clearInterval(retry), 500);
      setTimeout(() => clearInterval(retry), 20000);
    }
    installTips();
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start, { once: true });
  else start();
})();
