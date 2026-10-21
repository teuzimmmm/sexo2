// Numeric model of the SEXO2 opening (pure part of SEXO2-Startup/index.js). No browser needed.
// Reference measurements and expectations: HANDOFF.md 4.3 and 9 (1280x720, Oswald 600).
const test = require('node:test');
const assert = require('node:assert/strict');
const m = require('../Pengu Loader/plugins/SEXO2-Startup/index.js');

const FS = (184 * 0.68) / 0.81;
const M = {
  U: 1, VW: 1280, VH: 720,
  adv: [78.04, 67.73, 78.47, 88.96, 80],
  ink: [{ l: 5.3, r: 73.3 }, { l: 8.6, r: 63.6 }, { l: 0.2, r: 77.2 }, { l: 7.1, r: 81.1 }, { l: 5.5, r: 73.5 }],
  capA: 125.2, baseOff: 0, lsPx: 0.14 * FS,
};
const near = (a, b, tol, what) => assert.ok(Math.abs(a - b) <= tol, `${what}: ${a} vs ${b}`);

test('pchip hits its key points and is monotone, zero velocity only at the ends', () => {
  for (const [x, y] of m.GAPK) near(m.gapFn(x), y, 1e-9, `gap@${x}`);
  let prev = m.gapFn(0);
  for (let t = 0.01; t <= 2.55; t += 0.01) { const v = m.gapFn(t); assert.ok(v <= prev + 1e-12, `monotone @${t}`); prev = v; }
  const slope = (a, b) => Math.abs(m.gapFn(b) - m.gapFn(a)) / (b - a);
  assert.ok(slope(0, 0.01) < 0.2 * slope(0.2, 0.21), 'starts at rest');
  assert.ok(slope(2.54, 2.55) < 0.2 * slope(1.2, 1.21), 'ends at rest');
  assert.equal(m.gapFn(9), 0.145);
});

test('bez matches the CSS cubic-bezier endpoints and symmetry of the window curve', () => {
  assert.equal(m.winEase(0), 0);
  near(m.winEase(1), 1, 1e-9, 'end');
  near(m.winEase(0.5), 0.5, 1e-3, 'symmetric midpoint');
  near(m.bez(0.25, 0.1, 0.25, 1)(0.5), 0.8024, 2e-3, 'CSS ease@0.5');
});

test('initial frame (t = 0)', () => {
  const f = m.frame(0, M);
  near(f.iconL, 200.93, 0.5, 'icon x');
  [605.73, 705.4, 794.76, 894.86, 1005.45].forEach((x, i) => {
    near(f.glyphs[i].x, x, 0.5, `x[${i}]`);
    near(f.glyphs[i].sc, 1, 0.02, `sc[${i}]`);
    near(f.glyphs[i].op, 1, 0.02, `op[${i}]`);
  });
});

test('final frame (t = 2.55): composition centred, 32 px gap', () => {
  const f = m.frame(2.55, M);
  near(f.iconL, 497.85, 0.5, 'icon x');
  near(f.glyphs[4].x, 708.53, 0.5, '2 x');
  for (let i = 0; i < 4; i++) { near(f.glyphs[i].sc, 0.5, 0.02, `sc[${i}]`); near(f.glyphs[i].op, 0, 0.02, `op[${i}]`); }
  near(f.iconT, 268, 0.5, 'icon y');
  const right = f.glyphs[4].x + M.ink[4].r;
  near(right, 782.15, 0.5, 'right');
  near((f.iconL + right) / 2, 640, 0.5, 'centre');
  near(f.glyphs[4].x + M.ink[4].l - (f.iconL + 184), 32, 0.5, 'gap');
  near(m.frame(2.45, M).iconL, 497.64, 0.5, 'icon x @2.45');
});

test('absorption instants and distances', () => {
  const want = [[1.01, 37], [1.34, 37], [1.74, 26], [2.25, 30]];
  want.forEach(([ts, dist], i) => {
    let t = 0;
    while (m.frame(t, M).glyphs[i].op > 0.0005 && t < 2.6) t += 0.0005;
    near(t, ts, 0.03, `instant[${i}]`);
    const f = m.frame(t, M), g = f.glyphs[i];
    // the reference table is rounded and measured in another Chromium: E and O differ by up to 2.2 px (see docs/ABERTURA-QA.md)
    near(g.x + M.ink[i].l * g.sc - (f.iconL + 184), dist, 2.5, `distance[${i}]`);
  });
});

test('no letter touches or overlaps the icon edge at any instant while visible', () => {
  for (let t = 0; t <= 2.55; t += 0.005) {
    const f = m.frame(t, M);
    f.glyphs.forEach((g, i) => { if (g.op > 0.001) assert.ok(g.x + M.ink[i].l * g.sc - (f.iconL + 184) >= 20, `letter ${i} @${t}`); });
  }
});

test('the frame is a function of t alone (no hidden state)', () => {
  const a = JSON.stringify(m.frame(1.32, M));
  m.frame(0.4, M); m.frame(2.55, M);
  assert.equal(JSON.stringify(m.frame(1.32, M)), a);
});
