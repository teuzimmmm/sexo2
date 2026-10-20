/**
 * @name SEXO2-Startup
 * @description SEXO2 opening: [icon] SEXO 2 -> [icon] 2 over the client loading screen. Independent of the Python bridge and network.
 */
(() => {
  "use strict";

  // ---- model: pure functions of t (spec: skins/identidade/animacao-abertura/HANDOFF.md, 4.1-4.4) ----
  var clamp = function (v, a, b) {
    return v < a ? a : v > b ? b : v;
  };
  var st = function (a, b, x) {
    var t = clamp((x - a) / (b - a), 0, 1);
    return t * t * (3 - 2 * t);
  };
  function bez(x1, y1, x2, y2) {
    var cx = 3 * x1, bx = 3 * (x2 - x1) - cx, ax = 1 - cx - bx;
    var cy = 3 * y1, by = 3 * (y2 - y1) - cy, ay = 1 - cy - by;
    var fx = function (t) { return ((ax * t + bx) * t + cx) * t; };
    var fy = function (t) { return ((ay * t + by) * t + cy) * t; };
    var dfx = function (t) { return (3 * ax * t + 2 * bx) * t + cx; };
    return function (x) {
      var t = clamp(x, 0, 1), i, e, d;
      for (i = 0; i < 7; i++) {
        e = fx(t) - x;
        if (e < 1e-5 && e > -1e-5) break;
        d = dfx(t);
        if (d < 1e-6 && d > -1e-6) break;
        t = clamp(t - e / d, 0, 1);
      }
      return fy(t);
    };
  }
  // monotone PCHIP through key points: zero velocity only at the ends
  function pchip(xs, ys) {
    var n = xs.length, h = [], s = [], d = [], i, w1, w2;
    for (i = 0; i < n - 1; i++) { h[i] = xs[i + 1] - xs[i]; s[i] = (ys[i + 1] - ys[i]) / h[i]; }
    d[0] = 0; d[n - 1] = 0;
    for (i = 1; i < n - 1; i++) {
      if (s[i - 1] * s[i] <= 0) d[i] = 0;
      else {
        w1 = 2 * h[i] + h[i - 1]; w2 = h[i] + 2 * h[i - 1];
        d[i] = (w1 + w2) / (w1 / s[i - 1] + w2 / s[i]);
      }
    }
    return function (x) {
      if (x <= xs[0]) return ys[0];
      if (x >= xs[n - 1]) return ys[n - 1];
      var k = 0; while (x > xs[k + 1]) k++;
      var t = (x - xs[k]) / h[k], t2 = t * t, t3 = t2 * t;
      return (2 * t3 - 3 * t2 + 1) * ys[k]
        + (t3 - 2 * t2 + t) * h[k] * d[k]
        + (-2 * t3 + 3 * t2) * ys[k + 1]
        + (t3 - t2) * h[k] * d[k + 1];
    };
  }

  var G = { dur: 2.55, icon: 184, cap: 0.68, ls: 0.14, k: 0.5, ke: 1.2, fade: [0.25, 0.72], drift: 0.06, tight: 0.26, rise: 10 };
  var WIN = [[0.78, 1.14], [1.08, 1.5], [1.44, 1.92], [1.86, 2.48]]; // S, E, X, O consumption windows (s)
  var WINE = [0.45, 0, 0.55, 1];
  var GAPK = [[0, 1.2], [0.36, 0.55], [0.9, 0.21], [2.5, 0.145]]; // icon-to-first-live-letter gap, in icon sides
  var GAP0 = GAPK[0][1], GAP1 = GAPK[GAPK.length - 1][1];
  var gapFn = pchip(GAPK.map(function (k) { return k[0]; }), GAPK.map(function (k) { return k[1]; }));
  var winEase = bez(WINE[0], WINE[1], WINE[2], WINE[3]);

  /**
   * One frame as numbers. M = { U, VW, VH, adv[5], ink[5]{r}, capA, baseOff, lsPx }.
   * Returns { iconL, iconT, y, glyphs: [{x, sc, op}] x5 }; y is the shared letter top.
   */
  function frame(t, M) {
    var tt = clamp(t, 0, G.dur), U = M.U, adv = M.adv;
    var gapV = gapFn(tt);
    var gp = (GAP0 - gapV) / (GAP0 - GAP1); // 0 = widest, 1 = final
    var gap = gapV * G.icon * U;
    var lsn = M.lsPx * (1 - G.tight * gp);
    var sc = [1, 1, 1, 1, 1], op = [1, 1, 1, 1, 1], dr = [0, 0, 0, 0, 0], col = [1, 1, 1, 1, 1], i, c;
    for (i = 0; i < 4; i++) {
      c = winEase(clamp((tt - WIN[i][0]) / (WIN[i][1] - WIN[i][0]), 0, 1));
      sc[i] = 1 - G.k * Math.pow(c, G.ke);
      op[i] = 1 - st(G.fade[0], G.fade[1], c);
      col[i] = 1 - c;
      dr[i] = -G.drift * adv[i] * c;
    }
    var pen = [], x = 0;
    for (i = 0; i < 5; i++) { pen.push(x); x += (adv[i] + lsn) * col[i]; }
    var tw = G.icon * U + gap + pen[4] + M.ink[4].r;
    var iconL = (M.VW - tw) / 2;
    var iconT = (M.VH - G.icon * U) / 2 + G.rise * U * (1 - gp);
    var B = iconL + G.icon * U + gap;
    var baseY = iconT + (G.icon * U) / 2 + M.capA / 2;
    var gl = [];
    for (i = 0; i < 5; i++) gl.push({ x: B + pen[i] + dr[i], sc: sc[i], op: op[i] });
    return { iconL: iconL, iconT: iconT, y: baseY - M.baseOff, glyphs: gl };
  }

  if (typeof window === "undefined") {
    if (typeof module !== "undefined" && module.exports) {
      module.exports = { G, WIN, WINE, GAPK, clamp, st, bez, pchip, gapFn, winEase, frame };
    }
    return;
  }

  // ---- client integration ----
  var BASE = "https://plugins/SEXO2-Startup/";
  var STYLE_ID = "sexo2-startup-style";
  var ROOT_ID = "sexo2-abertura";
  var LOADING = 'div[id^="index_loading_div"]';

  // The client's own loading content is replaced; its background yields to the opening identity (#0d0e10).
  var CSS = [
    LOADING + "{background-color:#0d0e10!important}",
    LOADING + ">img{display:none!important}",
    LOADING + "::before," + LOADING + "::after{content:none!important;display:none!important}",
    '@font-face{font-family:Oswald;src:url("' + BASE + 'oswald.woff2") format("woff2");font-weight:200 700;font-style:normal;font-display:block}',
    '@font-face{font-family:Inter;src:url("' + BASE + 'inter.woff2") format("woff2");font-weight:100 900;font-style:normal;font-display:block}',
    // The browser itself hides the opening 8 s after it appears, without any script: the client
    // can replace the element with a copy that the script no longer holds
    "#" + ROOT_ID + "{position:fixed;inset:0;z-index:2147483000;overflow:hidden;background:#0d0e10;opacity:0;pointer-events:none;animation:sexo2-abertura-fim .3s linear 8s forwards}",
    "@keyframes sexo2-abertura-fim{to{opacity:0;visibility:hidden}}",
    "#" + ROOT_ID + ".on{opacity:1}",
    "#" + ROOT_ID + " .g{position:absolute;left:0;top:0;display:block;white-space:pre;line-height:1;font-family:Oswald,system-ui,sans-serif;font-weight:600;letter-spacing:0;color:#ececec;transform-origin:0 0;will-change:transform,opacity}",
    "#" + ROOT_ID + " .ic{position:absolute;left:0;top:0;line-height:0;transform-origin:0 0;will-change:transform}",
    "#" + ROOT_ID + " .ic img{display:block;width:100%;height:100%}",
    "#" + ROOT_ID + " .pr{position:absolute;left:-9999px;top:0;visibility:hidden;line-height:1;white-space:pre;font-family:Oswald,system-ui,sans-serif;font-weight:600}",
    "#" + ROOT_ID + " .pr i{display:inline-block;width:0;height:0;vertical-align:baseline}",
  ].join("\n");

  function injectStyle() {
    if (document.getElementById(STYLE_ID)) return;
    var style = document.createElement("style");
    style.id = STYLE_ID;
    style.textContent = CSS;
    (document.head || document.documentElement).appendChild(style);
  }

  // measured state shared by layout/measure/render
  var root, scene, iconEl, glyphs, probe, canvas, loadingDiv;
  var M = { U: 1, VW: 0, VH: 0, adv: [0, 0, 0, 0, 0], ink: [], capA: 0, baseOff: 0, lsPx: 0 };
  var capEm = 0.73;

  function measure(u) {
    M.U = u;
    var FS = (G.icon * u * G.cap) / capEm;
    // measure WITHOUT transform: getBoundingClientRect includes scaleX
    glyphs.forEach(function (el) { el.style.transform = "none"; el.style.fontSize = FS + "px"; });
    probe.style.fontSize = FS + "px";
    for (var i = 0; i < 5; i++) M.adv[i] = glyphs[i].getBoundingClientRect().width;
    M.baseOff = probe.firstElementChild.getBoundingClientRect().bottom - probe.getBoundingClientRect().top;
    var c = canvas.getContext("2d");
    c.font = "600 " + FS + "px Oswald";
    M.ink = ["S", "E", "X", "O", "2"].map(function (ch) {
      var m = c.measureText(ch);
      if (m.actualBoundingBoxRight === undefined || !m.actualBoundingBoxRight) return { l: 0, r: m.width, a: FS * capEm, d: 0 };
      return { l: -m.actualBoundingBoxLeft, r: m.actualBoundingBoxRight, a: m.actualBoundingBoxAscent, d: m.actualBoundingBoxDescent };
    });
    M.capA = M.ink[1].a;
    M.lsPx = G.ls * FS;
    iconEl.style.width = iconEl.style.height = G.icon * u + "px";
  }

  function layout() {
    var r = scene.getBoundingClientRect();
    M.VW = r.width; M.VH = r.height;
    var u = clamp(Math.min(M.VW / 1280, M.VH / 720), 0.4, 1.8), k, w, tw, f, i;
    for (k = 0; k < 3; k++) {
      measure(u);
      w = 0; for (i = 0; i < 4; i++) w += M.adv[i] + M.lsPx;
      w += M.ink[4].r;
      tw = G.icon * (1 + GAP0) * u + w;
      f = Math.min(1, (0.94 * M.VW) / tw, (0.64 * M.VH) / (G.icon * u));
      if (f > 0.999) break;
      u *= f;
    }
  }

  // The client can put a copy of the opening in its place: always animate the one on screen
  function rebind() {
    var shown = document.getElementById(ROOT_ID);
    if (!shown || shown === root) return;
    root = shown;
    scene = root.firstElementChild;
    iconEl = scene.querySelector(".ic");
    glyphs = Array.prototype.slice.call(scene.querySelectorAll(".g"));
    probe = root.querySelector(".pr");
  }

  function render(t) {
    rebind();
    var f = frame(t, M), y = f.y.toFixed(2) + "px", i;
    iconEl.style.transform = "translate3d(" + f.iconL.toFixed(2) + "px," + f.iconT.toFixed(2) + "px,0)";
    for (i = 0; i < 5; i++) {
      glyphs[i].style.transform = "translate3d(" + f.glyphs[i].x.toFixed(2) + "px," + y + ",0) scaleX(" + f.glyphs[i].sc.toFixed(4) + ")";
      glyphs[i].style.opacity = f.glyphs[i].op.toFixed(3);
    }
  }

  // ---- clock: one timeline, one rAF ----
  var el = 0, playing = false, raf = 0, last = 0, ended = false, loadingGone = false, booted = false, resizeTimer = 0;
  var holdTimer = 0, loadingObs = null, killTimer = 0;
  // Longest the final frame waits for the client after the animation, whatever the client does
  var MAX_HOLD_MS = 3000;
  // Longest the opening stays at all, by the plain timer clock: even if animation frames never
  // run or stall in the client's browser, the client is never left covered
  var MAX_ON_SCREEN_MS = 8000;

  function unmount() {
    cancelAnimationFrame(raf); raf = 0; playing = false;
    clearTimeout(resizeTimer);
    clearTimeout(holdTimer);
    clearTimeout(killTimer);
    if (loadingObs) { loadingObs.disconnect(); loadingObs = null; }
    window.removeEventListener("resize", onResize);
    if (root && root.parentNode) root.parentNode.removeChild(root);
    root = null;
    // and any copy of it the client put in its place
    document.querySelectorAll("#" + ROOT_ID).forEach(function (node) { node.remove(); });
  }

  // The client may hide its loading screen, or remove an ancestor of it, instead of removing it
  function loadingShown() {
    if (!loadingDiv.isConnected || !loadingDiv.getClientRects().length) return false;
    var cs = getComputedStyle(loadingDiv);
    return cs.visibility !== "hidden" && parseFloat(cs.opacity) > 0;
  }

  // The final frame stays while the client still shows its loading screen, at most MAX_HOLD_MS;
  // the overlay goes only after the animation ended.
  function finish() {
    ended = true;
    if (loadingGone || !loadingShown()) unmount();
    else if (!holdTimer) holdTimer = setTimeout(unmount, MAX_HOLD_MS);
  }

  // The time comes from performance.now(), not the frame timestamp: in the client's off-screen
  // browser the two clocks can differ, and the animation then never left its first frame.
  function tick() {
    if (!playing) return;
    var now = performance.now();
    var dt = clamp((now - last) / 1000, 0, 0.06);
    last = now; el += dt;
    try {
      if (el >= G.dur) { el = G.dur; render(G.dur); playing = false; raf = 0; finish(); return; }
      render(el);
    } catch (e) {
      playing = false; raf = 0; finish(); return;
    }
    raf = requestAnimationFrame(tick);
  }

  function play() {
    cancelAnimationFrame(raf); raf = 0;
    if (window.matchMedia && matchMedia("(prefers-reduced-motion: reduce)").matches) {
      playing = false; el = G.dur; render(G.dur); finish(); return;
    }
    el = 0; render(0); last = performance.now(); playing = true; raf = requestAnimationFrame(tick);
  }

  function onResize() {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(function () { if (booted && root) { layout(); render(el); } }, 90);
  }

  function boot() {
    if (booted || !root) return;
    booted = true;
    rebind();
    try {
      var c = canvas.getContext("2d");
      c.font = "600 200px Oswald";
      var m = c.measureText("E");
      capEm = m.actualBoundingBoxAscent ? m.actualBoundingBoxAscent / 200 : 0.73;
      layout();
      root.classList.add("on");
      play();
    } catch (e) {
      // never an empty scene: fall back to the static final frame
      try { layout(); render(G.dur); root.classList.add("on"); } catch (e2) { /* keep the client loading screen */ }
      finish();
    }
  }

  function mountOverlay() {
    root = document.createElement("div");
    root.id = ROOT_ID;
    root.setAttribute("aria-hidden", "true");
    scene = document.createElement("div");
    scene.style.cssText = "position:absolute;inset:0";
    iconEl = document.createElement("div");
    iconEl.className = "ic";
    var img = document.createElement("img");
    img.src = BASE + "icone-final.svg";
    img.alt = ""; img.draggable = false;
    iconEl.appendChild(img);
    scene.appendChild(iconEl);
    glyphs = ["S", "E", "X", "O", "2"].map(function (ch) {
      var s = document.createElement("span");
      s.className = "g"; s.textContent = ch;
      scene.appendChild(s);
      return s;
    });
    probe = document.createElement("div");
    probe.className = "pr";
    probe.appendChild(document.createElement("i"));
    canvas = document.createElement("canvas");
    root.appendChild(scene);
    root.appendChild(probe);
    document.body.appendChild(root);
    killTimer = setTimeout(unmount, MAX_ON_SCREEN_MS);
    window.addEventListener("resize", onResize);

    // measure only after Oswald is loaded; a late font re-measures, a missing one never blocks
    var fl = document.fonts && document.fonts.load ? document.fonts.load("600 100px Oswald") : Promise.resolve();
    var timer = setTimeout(boot, 1600);
    fl.then(
      function () {
        clearTimeout(timer);
        if (!booted) boot();
        else if (root) { layout(); render(el); }
      },
      function () { clearTimeout(timer); boot(); }
    );
  }

  var started = false;
  function watch() {
    var div = document.querySelector(LOADING);
    if (!div) return false;
    if (started) return true;
    started = true;
    loadingDiv = div;
    mountOverlay();
    // Disconnected by unmount; lives only while the opening is on screen
    loadingObs = new MutationObserver(function () {
      if (loadingShown()) return;
      loadingGone = true;
      // Once on screen the opening plays to its end, even when the client is ready sooner
      if (ended) unmount();
    });
    loadingObs.observe(document.body, { childList: true, subtree: true });
    loadingObs.observe(div, { attributes: true, attributeFilter: ["style", "class", "hidden"] });
    return true;
  }

  function start() {
    if (watch()) return;
    // loading div not there yet: observe until it shows up, then stop
    var seek = new MutationObserver(function () {
      if (watch()) seek.disconnect();
    });
    seek.observe(document.documentElement, { childList: true, subtree: true });
  }

  injectStyle();
  if (document.body) start();
  else document.addEventListener("DOMContentLoaded", start, { once: true });
})();
