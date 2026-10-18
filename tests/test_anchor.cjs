const test = require('node:test');
const assert = require('node:assert/strict');
const plugin = require('../Pengu Loader/plugins/ROSE-CustomWheel/index.js');
const proto = require('../design/propostas/sexo2-v1/js/anchor.js');

const view = { width: 1280, height: 720 };
const button = { left: 1150, right: 1256, top: 660, bottom: 694 };
const panel = { width: 452, height: 492 };

test('right edges aligned and 8 px above the button', () => {
  const a = plugin.computeAnchor(button, panel, view);
  assert.equal(a.left + panel.width, button.right);
  assert.equal(a.top + panel.height, button.top - 8);
  assert.equal(a.shrunk, false);
  assert.equal(a.shifted, false);
});

test('panel never covers the button: shrinks when it does not fit above', () => {
  const low = { width: 1024, height: 576 };
  const b = { left: 900, right: 1004, top: 300, bottom: 330 };
  const a = plugin.computeAnchor(b, panel, low);
  assert.equal(a.top, 8);
  assert.equal(a.maxHeight, 300 - 8 - 8);
  assert.equal(a.shrunk, true);
  assert.ok(a.top + a.maxHeight <= b.top - 8);
});

test('kept inside the window horizontally', () => {
  const left = plugin.computeAnchor({ left: 10, right: 100, top: 660, bottom: 694 }, panel, view);
  assert.equal(left.left, 8);
  assert.equal(left.shifted, true);
  const right = plugin.computeAnchor({ left: 1250, right: 1300, top: 660, bottom: 694 }, panel, view);
  assert.equal(right.left + panel.width, view.width - 8);
});

test('scaled client (CSS px from getBoundingClientRect) keeps the same rule', () => {
  const s = 1.5;
  const scaled = (r) => ({ left: r.left * s, right: r.right * s, top: r.top * s, bottom: r.bottom * s });
  const a = plugin.computeAnchor(scaled(button), { width: panel.width * s, height: panel.height * s }, { width: view.width * s, height: view.height * s });
  assert.equal(a.left + panel.width * s, button.right * s);
  assert.equal(a.top + panel.height * s, button.top * s - 8);
});

test('prototype and plugin use the same rule', () => {
  const cases = [
    [button, panel, view],
    [{ left: 900, right: 1004, top: 300, bottom: 330 }, panel, { width: 1024, height: 576 }],
    [{ left: 10, right: 100, top: 660, bottom: 694 }, panel, view],
  ];
  for (const [b, p, v] of cases) assert.deepEqual(proto.computeAnchor(b, p, v), plugin.computeAnchor(b, p, v));
});
