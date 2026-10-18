// Run: node tests/test_party_ui.cjs. No League client or network needed.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { test } = require('node:test');
const source = fs.readFileSync(path.join(__dirname, '../Pengu Loader/plugins/ROSE-PartyMode/index.js'), 'utf8');

function client() {
  const sent = [], timers = new Map();
  let timerId = 0;
  const sandbox = {
    console: { log() {}, error() {} },
    document: { getElementById: () => null, querySelector: () => null },
    window: { addEventListener() {}, removeEventListener() {} },
    WebSocket: { OPEN: 1 },
    setTimeout(fn) { timers.set(++timerId, fn); return timerId; },
    clearTimeout(id) { timers.delete(id); },
    setInterval() { return ++timerId; }, clearInterval() {},
    sent, capture: text => sent.push(JSON.parse(text)),
  };
  // Expose the real private handlers in this test copy only; omit DOM startup.
  const marker = '  // Start when DOM is ready';
  assert.ok(source.includes(marker), 'plugin startup marker changed');
  vm.runInNewContext(source.slice(0, source.indexOf(marker)) + `
    bridgeReady = true;
    bridgeSocket = {readyState: 1, send: capture};
    globalThis.api = {
      receive: handleBridgeMessage,
      health: getChampSelectPartyHealth,
      reconnect: handleReconnect,
      offline: () => { bridgeReady = false; },
    };
  })();`, sandbox);
  return { ...sandbox.api, sent, tick() {
    const pending = [...timers.values()]; timers.clear(); pending.forEach(fn => fn());
  }};
}

test('disabled state automatically enables fixed room only once while pending', () => {
  const c = client();
  c.receive({type: 'party-state', enabled: false}); c.tick();
  c.receive({type: 'party-state', enabled: false}); c.tick();
  assert.deepEqual(c.sent, [{type: 'party-enable'}]);
});
test('failed enable is retried', () => {
  const c = client();
  c.receive({type: 'party-enabled', success: false}); c.tick();
  assert.equal(c.sent.at(-1).type, 'party-enable');
});
test('reconnect button does not create invitation or switch rooms', () => {
  const c = client(); c.receive({type: 'party-state', enabled: true, relay_connected: true});
  c.reconnect(); assert.deepEqual(c.sent, [{type: 'party-reconnect'}]);
});
test('bridge offline is not shown as connected', () => {
  const c = client(); c.offline(); assert.equal(c.health().status, 'SEXO2 SEM RESPOSTA');
});
test('relay offline/reconnecting statuses are explicit', () => {
  const c = client(); c.receive({type: 'party-state', enabled: true});
  assert.equal(c.health().status, 'SEM SERVIDOR');
  c.receive({type: 'party-state', enabled: true, relay_reconnecting: true});
  assert.equal(c.health().status, 'RECONECTANDO');
});
test('connected friends in other lobbies do not mark match ready', () => {
  const c = client(); c.receive({type: 'party-state', enabled: true, relay_connected: true,
    peers: [{connected: true, in_lobby: false}]});
  assert.equal(c.health().status, 'CONECTADA');
});
test('champ select confirms received skins, not injection success', () => {
  const c = client(); c.receive({type: 'party-state', enabled: true, relay_connected: true,
    peers: [{connected: true, in_lobby: true, skin_selection: {champion_id: 11, skin_id: 11001}}]});
  assert.equal(c.health().status, 'PARTY PRONTA');
});
