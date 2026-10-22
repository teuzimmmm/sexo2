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

test('ranked entries from the client become the Equipe line', () => {
  const ranked = JSON.parse(fs.readFileSync(path.join(__dirname, 'fixtures/lcu/ranked-stats-representative.json'), 'utf8'));
  const solo = ranked.queueMap.RANKED_SOLO_5x5;
  const flex = ranked.queueMap.RANKED_FLEX_SR;
  assert.equal(A.eloText({ queue: solo.queueType, tier: solo.tier, division: solo.division, leaguePoints: solo.leaguePoints }), 'Platina IV · 77 PDL');
  assert.equal(A.eloText({ queue: flex.queueType, tier: flex.tier, division: flex.division, leaguePoints: flex.leaguePoints }), 'Flex · Ouro II · 45 PDL');
  assert.equal(A.eloText({ queue: 'RANKED_SOLO_5x5', tier: 'MASTER', division: null, leaguePoints: 312 }), 'Mestre · 312 PDL');
  assert.equal(A.eloText({ queue: 'RANKED_SOLO_5x5', tier: 'MASTER', division: 'I', leaguePoints: 312 }), 'Mestre · 312 PDL');
});

test('a player without ranked, or an unknown tier, is a dash', () => {
  assert.equal(A.eloText(null), '—');
  assert.equal(A.eloText({ queue: 'RANKED_SOLO_5x5', tier: '', division: 'NA', leaguePoints: 0 }), '—');
  assert.equal(A.eloText({ queue: 'RANKED_SOLO_5x5', tier: 'NOT_A_TIER', division: 'I', leaguePoints: 1 }), '—');
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

test('a tela do Swiftplay mostra só Runas e Itens e conhece os erros do espaço do lobby', () => {
  assert.deepEqual(A.visibleTabs(false, false, true).map(([k]) => k), ['runes', 'items']);
  assert.deepEqual(A.visibleTabs(false, true, true).map(([k]) => k), ['runes', 'items']);
  assert.equal(A.runeError('invalid_page'), 'Página incompleta ou inválida.');
  assert.equal(A.runeError('no_swiftplay_slot'), 'Esse campeão não está mais no lobby.');
  assert.equal(A.runeError('slot_refused'), 'O cliente recusou a página.');
  assert.equal(A.runeError('slot_format'), 'O cliente recusou a página.');
});

test('Campeão · Jogador: o campeão quando escolhido, depois o jogador', () => {
  assert.equal(A.rowLabel('Draven', 'Fulano'), 'Draven · Fulano');
  assert.equal(A.rowLabel('', 'Fulano'), 'Fulano');
  assert.equal(A.rowLabel('Draven', ''), 'Draven');
  assert.equal(A.rowLabel('', ''), '—');
});

const names = { 86: 'Garen', 22: 'Ashe', 202: 'Jhin' };
const champ = (id) => names[id] || '';

test('linha da Equipe: tudo o que o cliente der aparece, nada além', () => {
  const full = A.rowParts(
    {
      name: 'Fulano', championId: 86,
      elo: { queue: 'RANKED_SOLO_5x5', tier: 'PLATINUM', division: 'IV', leaguePoints: 77, wins: 86, losses: 56 },
      form: { games: 20, wins: 13, recent: [true, true, false, true, true], role: 'top', top: [{ id: 22, games: 9 }, { id: 86, games: 3 }], withChampion: { games: 6, wins: 4 } },
      met: true,
    },
    champ,
  );
  assert.equal(full.name, 'Fulano');
  assert.equal(full.champion, 'Garen');
  assert.deepEqual(full.elo, { queue: '', tier: 'Platina IV', points: '77 PDL' });
  assert.deepEqual(full.facts, ['Topo', '61% em 142', 'Garen 67% em 6']);
  assert.deepEqual(full.recent, [true, true, false, true, true]);
  assert.equal(full.met, true);
  assert.equal(full.tip, 'Fulano|Mais jogados: Ashe 9, Garen 3. 13 vitórias e 7 derrotas nas últimas 20.');
});

test('linha da Equipe: cada dado ausente some, sem estragar os outros', () => {
  const none = A.rowParts({ name: '', championId: 0, elo: null, form: null, met: false }, champ);
  assert.deepEqual(none, { name: '', champion: '', icon: 0, elo: null, facts: [], recent: [], met: false, tip: '' });
  // ainda não escolheu o campeão: nada de "com o campeão"
  const unpicked = A.rowParts({ name: 'X', championId: 0, form: { games: 5, wins: 1, recent: [false], role: null, top: [], withChampion: null } }, champ);
  assert.deepEqual(unpicked.facts, []);
  assert.equal(unpicked.champion, '');
  // escolheu, mas nunca jogou com ele: sem o dado do campeão
  const first = A.rowParts({ name: 'X', championId: 86, form: { games: 5, wins: 1, recent: [false], role: 'jungle', top: [], withChampion: null } }, champ);
  assert.deepEqual(first.facts, ['Selva']);
  // nome do campeão ainda não carregado: o dado do campeão não aparece
  const unknown = A.rowParts({ name: 'X', championId: 999, form: { games: 2, wins: 2, recent: [true, true], role: null, top: [], withChampion: { games: 2, wins: 2 } } }, champ);
  assert.deepEqual(unknown.facts, []);
  // sem vitórias nem derrotas da fila (não ranqueado ou falha): sem taxa
  assert.deepEqual(A.rowParts({ elo: { queue: 'RANKED_SOLO_5x5', tier: 'GOLD', division: 'I', leaguePoints: 0, wins: 0, losses: 0 } }, champ).facts, []);
  assert.deepEqual(A.rowParts({ elo: { queue: 'RANKED_SOLO_5x5', tier: 'GOLD', division: 'I', leaguePoints: 0, wins: null, losses: null } }, champ).facts, []);
  // dados de forma malformados não quebram a linha
  assert.deepEqual(A.rowParts({ form: { recent: 'x', role: 'ninja', withChampion: { games: 'a' } } }, champ).recent, []);
  assert.equal(A.rowParts({ form: { games: 0 } }, champ).tip, '');
});

test('elo em partes: Flex, divisão só onde existe, pontos só se vierem', () => {
  assert.deepEqual(A.eloParts({ queue: 'RANKED_FLEX_SR', tier: 'GOLD', division: 'II', leaguePoints: 45 }), { queue: 'Flex', tier: 'Ouro II', points: '45 PDL' });
  assert.deepEqual(A.eloParts({ queue: 'RANKED_SOLO_5x5', tier: 'MASTER', division: 'I', leaguePoints: 312 }), { queue: '', tier: 'Mestre', points: '312 PDL' });
  assert.deepEqual(A.eloParts({ queue: 'RANKED_SOLO_5x5', tier: 'IRON', division: 'IV' }), { queue: '', tier: 'Ferro IV', points: '' });
  assert.equal(A.eloParts({ tier: 'UNRANKED' }), null);
  assert.equal(A.eloParts(null), null);
  assert.equal(A.eloText(null), '—');
});

test('dica da linha: singular e plural, e só com partidas', () => {
  const tip = (wins, games) => A.rowTip({ name: 'Y', form: { games, wins, top: [] } }, champ);
  assert.equal(tip(1, 2), 'Y|1 vitória e 1 derrota nas últimas 2.');
  assert.equal(tip(2, 3), 'Y|2 vitórias e 1 derrota nas últimas 3.');
  assert.equal(A.rowTip({ name: 'Y', form: null }, champ), '');
});

test('sem estatísticas só Equipe, Mods e Todas as configurações aparecem; Equipe só com elenco', () => {
  const keys = (noStats, hasTeam) => A.visibleTabs(noStats, hasTeam).map(([k]) => k);
  // Summoner's Rift (ranqueadas, normais): tudo
  assert.deepEqual(keys(false, true), ['runes', 'items', 'team', 'mods', 'settings']);
  // ARAM tem estatísticas e elenco
  assert.deepEqual(keys(false, true), ['runes', 'items', 'team', 'mods', 'settings']);
  // Arena (sem estatísticas): Equipe, Mods e configurações
  assert.deepEqual(keys(true, true), ['team', 'mods', 'settings']);
  // Swiftplay (sem seleção de campeões com elenco): nada de Equipe
  assert.deepEqual(keys(false, false), ['runes', 'items', 'mods', 'settings']);
  assert.deepEqual(keys(true, false), ['mods', 'settings']);
  assert.ok(!keys(false, true).includes('prefs'));
  assert.equal(A.hasTeamRows(null), false);
  assert.equal(A.hasTeamRows({ ranked: { available: true, team: [], enemies: [] } }), false);
  assert.equal(A.hasTeamRows({ ranked: { available: true, team: [{ position: 'top' }], enemies: [] } }), true);
  // the service decides by queue: Solo/Duo, Arena and Swiftplay never show the tab
  assert.equal(A.hasTeamRows({ ranked: { available: false, team: [{ position: 'top' }], enemies: [] } }), false);
  // the enemies alone never open it (the client hides them)
  assert.equal(A.hasTeamRows({ ranked: { available: true, team: [], enemies: [{ position: 'top' }] } }), false);
});

test('build favorita: o trio do topo do conjunto e a comparação com o fixado', () => {
  const blocks = [
    { type: '56,8% — 7.505 partidas', items: [{ id: '2503' }, { id: '3158' }, { id: '3100' }, { id: '3089' }] },
    { type: 'Itens iniciais', items: [{ id: '1056' }] },
  ];
  assert.deepEqual(A.topTrio(blocks), [2503, 3158, 3100]);
  assert.deepEqual(A.topTrio([]), []);
  assert.equal(A.sameIds([2503, 3158, 3100], A.topTrio(blocks)), true);
  assert.equal(A.sameIds(null, A.topTrio(blocks)), false);
  assert.equal(A.sameIds([2503, 3158], A.topTrio(blocks)), false);
});
