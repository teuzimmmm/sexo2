// Run: node --test tests/test_prototype_runes.cjs. Rules and import controller of the v1 prototype.
const assert = require('node:assert/strict');
const path = require('node:path');
const { test, mock } = require('node:test');
const dir = path.join(__dirname, '../design/propostas/sexo2-v1/js');
global.window = global;
require(path.join(dir, 'game-data.js'));
require(path.join(dir, 'demo-data.js'));
require(path.join(dir, 'runes.js'));
const R = global.S2Runes;
const data = R.index(global.S2_GAME);
const win = R.fromPerks(data, global.S2_DEMO.runes.Ahri.win.page);
const pick = R.fromPerks(data, global.S2_DEMO.runes.Ahri.pick.page);

function setup({ canEdit = () => true } = {}) {
  const sent = [];
  const importer = R.createImporter({
    data, debounceMs: 350, canEdit,
    transport: (choice, done) => sent.push({ choice, done }),
  });
  return { importer, sent };
}

test('every demo page follows the rune rules', () => {
  for (const champ of Object.values(global.S2_DEMO.runes)) {
    for (const rec of [champ.win, champ.pick, ...Object.values(champ.vs).flatMap((v) => [v.win, v.pick])]) {
      assert.deepEqual(R.validate(data, R.fromPerks(data, rec.page)), []);
    }
  }
});

test('invalid combinations are rejected', () => {
  const noSecondary = R.clone(win); noSecondary.secondary = [];
  assert.ok(R.validate(data, noSecondary).includes('secondary-count'));
  const sameRow = R.edit.secondaryRune(data, R.edit.secondaryRune(data, win, 1, 8224), 1, 8275);
  assert.equal(sameRow.secondary.filter((s) => s.row === 1).length, 1);
  const switched = R.edit.primaryStyle(data, win, 8000);
  assert.ok(R.validate(data, switched).includes('keystone'));
});

test('choosing a recommendation imports it at once; only the confirmed page is applied', () => {
  const { importer, sent } = setup();
  importer.choose('Maior WR', win);
  assert.equal(sent.length, 1);
  assert.equal(importer.snapshot().applied, null);
  sent[0].done({ ok: true });
  assert.ok(R.same(importer.snapshot().applied.page, win));
});

test('quick edits are coalesced into one import of the latest page', () => {
  mock.timers.enable({ apis: ['setTimeout'] });
  try {
    const { importer, sent } = setup();
    importer.choose('Maior WR', win);
    sent[0].done({ ok: true });
    importer.edit(R.edit.primaryRune(data, win, 0, 8128));
    importer.edit(R.edit.shard(data, R.edit.primaryRune(data, win, 0, 8128), 0, 5005));
    mock.timers.tick(349);
    assert.equal(sent.length, 1);
    mock.timers.tick(1);
    assert.equal(sent.length, 2);
    assert.equal(sent[1].choice.page.keystone, 8128);
    assert.equal(sent[1].choice.page.shards[0], 5005);
  } finally { mock.timers.reset(); }
});

test('an incomplete edit is never sent', () => {
  mock.timers.enable({ apis: ['setTimeout'] });
  try {
    const { importer, sent } = setup();
    importer.choose('Maior WR', win);
    sent[0].done({ ok: true });
    importer.edit(R.edit.subStyle(data, win, 8000));
    mock.timers.tick(1000);
    assert.equal(sent.length, 1);
    assert.ok(importer.snapshot().incomplete);
  } finally { mock.timers.reset(); }
});

test('a failed import keeps the last confirmed page', () => {
  const { importer, sent } = setup();
  importer.choose('Maior WR', win);
  sent[0].done({ ok: true });
  importer.choose('Mais comum', pick);
  sent[1].done({ ok: false, error: 'client' });
  assert.ok(R.same(importer.snapshot().applied.page, win));
  assert.equal(importer.snapshot().error, 'client');
});

test('an edit made while an import is in flight is sent after it, and only the latest', () => {
  const { importer, sent } = setup();
  importer.choose('Maior WR', win);
  importer.choose('Mais comum', pick);
  assert.equal(sent.length, 1);
  sent[0].done({ ok: true });
  assert.equal(sent.length, 2);
  assert.ok(R.same(sent[1].choice.page, pick));
});

test('a response from a previous session is discarded', () => {
  const { importer, sent } = setup();
  importer.choose('Maior WR', win);
  importer.reset('champion changed');
  sent[0].done({ ok: true });
  assert.equal(importer.snapshot().applied, null);
});

test('when the selection no longer allows changes nothing is sent and the applied page stays', () => {
  let open = true;
  const { importer, sent } = setup({ canEdit: () => open });
  importer.choose('Maior WR', win);
  sent[0].done({ ok: true });
  open = false;
  importer.choose('Mais comum', pick);
  importer.confirm();
  assert.equal(sent.length, 1);
  assert.ok(R.same(importer.snapshot().applied.page, win));
});
