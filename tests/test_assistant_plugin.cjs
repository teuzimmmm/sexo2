const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const A = require('../Pengu Loader/plugins/SEXO2-Assistant/index.js');
const wheel = require('../Pengu Loader/plugins/SEXO2-CustomWheel/index.js');

const styles = JSON.parse(fs.readFileSync(path.join(__dirname, 'fixtures/lcu/perks-styles-representative.json'), 'utf8')).styles;
const perks = [{ id: 8112, name: 'Eletrocutar', iconPath: '/i/8112.png', shortDesc: 'x' }, { id: 5008, name: 'Força Adaptativa', iconPath: '/i/5008.png' }];
const game = A.gameFromClient(styles, perks);
const data = A.index(game);

function firstValid() {
  const prim = game.styles[0];
  const sub = game.styles[1];
  return {
    primary: prim.id, sub: sub.id, keystone: prim.slots[0][0].id,
    minor: [1, 2, 3].map((r) => prim.slots[r][0].id),
    secondary: [{ row: 1, id: sub.slots[1][0].id }, { row: 2, id: sub.slots[2][0].id }],
    shards: game.shards.rows.map((r) => r[0]),
  };
}

test('client styles become four rows per tree plus three shard rows', () => {
  assert.ok(game.styles.length >= 5);
  for (const s of game.styles) assert.equal(s.slots.length, 4);
  assert.equal(game.shards.rows.length, 3);
  assert.equal(data.perks[8112].name, 'Eletrocutar');
  assert.equal(game.icons[8112], '/i/8112.png');
  assert.equal(game.shards.names[5008], 'Força Adaptativa');
});

test('a page round-trips through the editor model and validates', () => {
  const p = firstValid();
  const perksList = A.toPerks(p);
  assert.equal(perksList.length, 9);
  const back = A.fromPerks(data, { primary: p.primary, sub: p.sub, perks: perksList });
  assert.deepEqual(A.toPerks(back), perksList);
  assert.deepEqual(A.validate(data, p), []);
});

test('changing the primary tree leaves the page incomplete until runes are chosen', () => {
  const p = firstValid();
  const other = game.styles[2].id;
  const n = A.edit.primaryStyle(data, p, other);
  assert.ok(A.validate(data, n).includes('keystone'));
  assert.deepEqual(A.validate(data, p), []); // the original is not mutated
});

test('a third secondary rune replaces the oldest, one per row', () => {
  const p = firstValid();
  const sub = data.styles[p.sub];
  const n = A.edit.secondaryRune(data, p, 3, sub.slots[3][0].id);
  assert.deepEqual(n.secondary.map((s) => s.row), [2, 3]);
});

test('same anchor rule as the CustomWheel button', () => {
  const b = { left: 1150, right: 1256, top: 660, bottom: 694 };
  const size = { width: 452, height: 492 };
  const view = { width: 1280, height: 720 };
  const a = A.computeAnchor(b, size, view);
  const w = wheel.computeAnchor(b, size, view);
  assert.deepEqual([a.left, a.top, a.maxHeight], [w.left, w.top, w.maxHeight]);
});

test('error codes become the approved texts', () => {
  assert.equal(A.runeError('no_free_page'), 'Sem espaço para a página do SEXO2. Apague uma página no cliente.');
  assert.equal(A.runeError('lcu_rejected'), 'O cliente recusou a página.');
  assert.equal(A.itemError('no_builds', 'Ahri'), 'Sem dados para Ahri.');
  assert.equal(A.itemError('concurrent_edit', 'Ahri'), 'O cliente recusou o conjunto.');
});

test('a button that measures 0x0 anchors by its content, else the panel stays on screen', () => {
  const box = (width, height) => ({ getBoundingClientRect: () => ({ left: 1150, right: 1150 + width, top: 660, bottom: 660 + height, width, height }) });
  const inner = box(106, 34);
  const button = { ...box(0, 0), children: [inner], parentElement: box(300, 40) };
  assert.equal(A.anchorRect(button).width, 106);
  assert.equal(A.anchorRect({ ...box(0, 0), children: [], parentElement: box(0, 0) }), null);
  const pos = A.fallbackAnchor({ width: 1280, height: 720 }, { width: 452, height: 492 });
  assert.ok(pos.left >= 0 && pos.left + 452 <= 1280);
  assert.ok(pos.top >= 0 && pos.top + pos.maxHeight <= 720);
});

test('other builds are filtered by item name, ignoring accents and case', () => {
  const names = { 3118: 'Chama Sombria', 3020: 'Sapatos do Feiticeiro', 6653: 'Tormento de Liandry' };
  const builds = [{ items: [3118, 3020, 6653] }, { items: [6653, 3020, 3157] }];
  const name = (id) => names[id] || '';
  assert.equal(A.filterBuilds(builds, '', name).length, 2);
  assert.deepEqual(A.filterBuilds(builds, 'chama', name), [builds[0]]);
  assert.deepEqual(A.filterBuilds(builds, 'FEITICEIRO', name).length, 2);
  assert.deepEqual(A.filterBuilds(builds, 'liándry', name).length, 2);
  assert.deepEqual(A.filterBuilds(builds, 'zzz', name), []);
});

test('the default build shows only the first group as Inicial, Essenciais and Situacionais', () => {
  const block = (type, ...ids) => ({ type, items: ids.map((id) => ({ id: String(id), count: 1 })) });
  const blocks = [
    block('56,3% — 1.200 partidas', 1, 2, 3),
    block('Itens iniciais', 4),
    block('Alternativas', 5),
    block('54,0% — 3.000 partidas', 6),
    block('Itens iniciais', 7),
  ];
  const build = A.defaultBuild(blocks);
  assert.equal(build.essenciais.type, '56,3% — 1.200 partidas');
  assert.equal(build.inicial.items[0].id, '4');
  assert.equal(build.situacionais.items[0].id, '5');
  assert.deepEqual(A.defaultBuild([]), { inicial: null, essenciais: null, situacionais: null });
  assert.equal(A.defaultBuild([block('Itens iniciais', 4)]).inicial, null);
});

test('sem estatísticas só Mods e Todas as configurações aparecem', () => {
  const keys = (noStats) => A.visibleTabs(noStats).map(([k]) => k);
  assert.deepEqual(keys(false), ['runes', 'items', 'mods', 'settings']);
  assert.deepEqual(keys(true), ['mods', 'settings']);
  assert.ok(!keys(false).includes('prefs'));
});
