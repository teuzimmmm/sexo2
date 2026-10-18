/* Posição do painel do assistente acima do botão SEXO2.
 * Mesma regra de computeAnchor em Pengu Loader/plugins/ROSE-CustomWheel/index.js
 * (tests/test_anchor.cjs confere que as duas dão o mesmo resultado). */
(function (root) {
  "use strict";
  // button: {left, top, right, bottom}; panel: {width, height}; viewport: {width, height}.
  // Borda direita do painel alinhada à do botão, `gap` px acima dele, sempre dentro da área.
  // Se não couber acima, o painel encolhe (maxHeight) em vez de cobrir o botão.
  function computeAnchor(button, panel, viewport, gap, margin) {
    gap = gap == null ? 8 : gap;
    margin = margin == null ? 8 : margin;
    const room = Math.max(0, button.top - gap - margin);
    const height = Math.min(panel.height, room);
    let left = button.right - panel.width;
    left = Math.max(margin, Math.min(left, viewport.width - margin - panel.width));
    return {
      left: Math.round(left),
      top: Math.round(button.top - gap - height),
      maxHeight: Math.floor(room),
      shrunk: height < panel.height,
      shifted: Math.round(left) !== Math.round(button.right - panel.width),
    };
  }
  const api = { computeAnchor };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.S2Anchor = api;
})(this);
