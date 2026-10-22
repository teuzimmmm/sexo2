// Stress test of the Equipe tab's pure parts (D-153): whatever junk the service or the client sends,
// no row may throw or show "undefined", "NaN" or "null", and a row never grows past what fits.
const test = require('node:test');
const assert = require('node:assert/strict');
const A = require('../Pengu Loader/plugins/SEXO2-Assistant/index.js');

let seed = 20261022;
const rnd = () => ((seed = (seed * 1664525 + 1013904223) >>> 0) / 2 ** 32);
const pick = (xs) => xs[Math.floor(rnd() * xs.length)];
const junk = () => pick([undefined, null, NaN, Infinity, -1, 0, 1, 7, 1e9, 3.5, '', 'x', '12', true, false, [], {}, [1, 2], { a: 1 }, () => 1]);
const maybe = (good) => (rnd() < 0.55 ? good() : junk());
const names = { 86: 'Garen', 22: 'Ashe', 202: 'Jhin' };
const champ = (id) => names[id] || '';

const elo = () => ({
  queue: pick(['RANKED_SOLO_5x5', 'RANKED_FLEX_SR', junk()]),
  tier: maybe(() => pick(['IRON', 'GOLD', 'PLATINUM', 'MASTER', 'CHALLENGER', 'UNRANKED', 'NONE', 'gold'])),
  division: maybe(() => pick(['I', 'II', 'III', 'IV', 'NA', ''])),
  leaguePoints: maybe(() => Math.floor(rnd() * 100)),
  wins: maybe(() => Math.floor(rnd() * 400)),
  losses: maybe(() => Math.floor(rnd() * 400)),
});
const form = () => ({
  games: maybe(() => Math.floor(rnd() * 21)),
  wins: maybe(() => Math.floor(rnd() * 21)),
  recent: maybe(() => Array.from({ length: Math.floor(rnd() * 9) }, () => pick([true, false, junk()]))),
  role: maybe(() => pick(['top', 'jungle', 'middle', 'bottom', 'support', 'ninja'])),
  top: maybe(() => Array.from({ length: Math.floor(rnd() * 5) }, () => ({ id: pick([86, 22, 202, 999, junk()]), games: maybe(() => Math.floor(rnd() * 30)) }))),
  withChampion: maybe(() => ({ games: maybe(() => Math.floor(rnd() * 20)), wins: maybe(() => Math.floor(rnd() * 20)) })),
});
const player = () => ({
  cellId: maybe(() => Math.floor(rnd() * 10)),
  position: pick(['top', 'jungle', 'middle', 'bottom', 'support', '', junk()]),
  name: maybe(() => pick(['Fulano', 'A'.repeat(200), 'Ünïcödé 日本語', '<img src=x onerror=1>', '"quote\'s"', ''])),
  championId: maybe(() => pick([0, 86, 22, 202, 999])),
  elo: rnd() < 0.2 ? null : maybe(elo),
  form: rnd() < 0.3 ? null : maybe(form),
  canOpen: maybe(() => rnd() < 0.5),
});

const bad = /undefined|NaN|\bnull\b|\[object|Infinity/;
const texts = (v) => [v.name, v.champion, v.elo && v.elo.tier, v.elo && v.elo.points, ...v.facts, v.tip];

test('a thousand random rows never throw and never show a broken value', () => {
  for (let i = 0; i < 1000; i++) {
    const p = player();
    const v = A.rowParts(p, champ);
    for (const t of texts(v)) {
      if (typeof t === 'string') assert.doesNotMatch(t, bad, JSON.stringify(p));
    }
    assert.ok(v.facts.length <= 3, JSON.stringify(p));
    assert.ok(v.recent.length <= 5, JSON.stringify(p));
    assert.ok(Number.isInteger(v.cell));
    assert.equal(typeof v.canOpen, 'boolean');
    for (const f of v.facts) {
      const m = /(\d+)% em/.exec(f);
      if (m) assert.ok(Number(m[1]) >= 0 && Number(m[1]) <= 100, f);
    }
    assert.equal(typeof A.rowLabel(v.champion, v.name), 'string');
  }
});

test('random states never throw in the tab rules', () => {
  for (let i = 0; i < 1000; i++) {
    const st = rnd() < 0.1 ? junk() : { ranked: maybe(() => ({ available: junk(), team: maybe(() => Array.from({ length: 8 }, player)), enemies: junk() })) };
    const has = A.hasTeamRows(st);
    assert.equal(typeof has, 'boolean');
    for (const noStats of [true, false, junk()]) {
      const keys = A.visibleTabs(noStats, has).map(([k]) => k);
      assert.ok(keys.includes('mods') && keys.includes('settings'));
      assert.equal(keys.includes('team'), has);
    }
  }
});

test('elo text and parts accept anything', () => {
  for (let i = 0; i < 1000; i++) {
    const e = rnd() < 0.2 ? junk() : elo();
    const text = A.eloText(e);
    assert.equal(typeof text, 'string');
    assert.doesNotMatch(text, bad);
    const parts = A.eloParts(e);
    assert.ok(parts === null || (typeof parts.tier === 'string' && typeof parts.points === 'string'));
  }
});
