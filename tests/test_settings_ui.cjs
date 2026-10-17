const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const source = fs.readFileSync(path.join(__dirname, '../Pengu Loader/plugins/SEXO2-Settings/index.js'), 'utf8');

class Node {
  constructor(tag, text = '') {
    this.tagName = tag.toUpperCase(); this.children = []; this.textContent = text;
    this.dataset = {}; this.attributes = {}; this.listeners = {}; this.disabled = false;
    this.classList = { add: value => { this.className = `${this.className || ''} ${value}`.trim(); } };
    this.value = ''; this.checked = false; this.type = ''; this.hidden = false;
  }
  append(...nodes) { for (const node of nodes) { this.children.push(node); node.parentElement = this; } }
  get lastChild() { return this.children.at(-1); }
  setAttribute(name, value) { this.attributes[name] = value; }
  removeAttribute(name) { delete this.attributes[name]; }
  toggleAttribute(name, force) { if (force) this.attributes[name] = ''; else delete this.attributes[name]; }
  addEventListener(name, fn) { (this.listeners[name] ||= []).push(fn); }
  emit(name, event = {}) { for (const fn of this.listeners[name] || []) fn({ target: this, preventDefault() {}, ...event }); }
  reportValidity() { return true; }
  querySelectorAll(selector) {
    const tags = selector.split(',').map(value => value.trim().toUpperCase());
    return this.children.flatMap(child => [ ...(tags.includes(child.tagName) ? [child] : []), ...child.querySelectorAll(selector) ]);
  }
  closest() { return null; }
}

test('LoLalytics selector loads persisted value, preserves dirty choice during polling, and saves with lock and ack', () => {
  // Capture the root mounted by the settings event through its target host.
  const handlers = {}; const sent = []; const intervals = [];
  const document = { createElement: tag => new Node(tag), querySelectorAll: () => [] };
  const bridge = {
    ready: true,
    subscribe(type, callback) { (handlers[type] ||= []).push(callback); },
    onReady(callback) { callback(); },
    send(payload) { sent.push(payload); },
  };
  const window = { __roseBridge: bridge,
    addEventListener(type, callback) { (handlers[`window:${type}`] ||= []).push(callback); },
    dispatchEvent(event) { for (const fn of handlers[`window:${event.type}`] || []) fn(event); } };
  const context = { window, document, Date, Math, console,
    CustomEvent: class { constructor(type, init = {}) { this.type = type; this.detail = init.detail; } },
    setInterval(fn) { intervals.push(fn); return intervals.length; }, clearInterval() {} };
  vm.runInNewContext(source, context);
  intervals[0]();
  const host = new Node('div');
  window.dispatchEvent(new context.CustomEvent('rose-hub-settings', { detail: { target: host } }));
  const find = name => host.querySelectorAll('select').find(node => node.name === name);
  const risk = find('lolalyticsRiskLevel');
  const request = sent.find(message => message.type === 'settings-request');
  const emit = (type, data) => { for (const fn of handlers[type] || []) fn(data); };
  emit('settings-data', { requestId: request.requestId, threshold: .5, monitorAutoResumeTimeout: 60,
    autostart: false, hideEmptyCategories: false, gamePath: '', lolalyticsRiskLevel: 'high', version:'2.0.0.7 (teste)' });
  assert.equal(risk.value, 'high');
  assert.ok(host.querySelectorAll('p').some(node=>node.textContent==='SEXO2 · 2.0.0.7 (teste)'));
  const overlay = host.querySelectorAll('input').find(node => node.name === 'buildOverlayEnabled');
  assert.equal(overlay.checked, true);
  host.querySelectorAll('button').find(node => node.textContent === 'Testar janela (20 s)').onclick();
  assert.equal(sent.at(-1).type, 'sexo2-overlay-preview');
  emit('sexo2-overlay-state', { accepted: true, status: { message: 'Prévia temporária.', window: { message: 'Janela exibida.' } } });
  assert.ok(host.querySelectorAll('p').some(node => node.textContent.includes('Janela exibida.')));
  assert.deepEqual(risk.children.map(option => option.textContent), ['Muito baixo', 'Baixo', 'Médio', 'Alto', 'Muito alto']);

  risk.value = 'very-high'; risk.emit('change');
  overlay.checked = false; overlay.emit('change');
  window.dispatchEvent(new context.CustomEvent('rose-hub-settings', { detail: { target: host } }));
  const poll = sent.filter(message => message.type === 'settings-request').at(-1);
  emit('settings-data', { requestId: poll.requestId, threshold: .5, monitorAutoResumeTimeout: 60,
    autostart: false, hideEmptyCategories: false, gamePath: '', lolalyticsRiskLevel: 'low' });
  assert.equal(risk.value, 'very-high', 'polling must not overwrite an unsaved selection');

  const saveButton = host.querySelectorAll('button').find(node => node.id === 'sexo2-settings-save');
  saveButton.onclick();
  const save = sent.findLast(message => message.type === 'settings-save');
  assert.equal(save.lolalyticsRiskLevel, 'very-high');
  assert.equal(save.buildOverlayEnabled, false);
  assert.equal(risk.disabled, true);
  emit('settings-saved', { requestId: save.requestId, success: true,
    settings: { threshold: .5, monitorAutoResumeTimeout: 60, autostart: false,
      hideEmptyCategories: false, gamePath: '', lolalyticsRiskLevel: 'very-high', buildOverlayEnabled: false } });
  assert.equal(risk.disabled, false);
  assert.equal(risk.value, 'very-high');
  assert.equal(overlay.checked, false);
});

test('missing risk field from an older backend populates the medium default', () => {
  const handlers = {}; const sent = []; const intervals = [];
  const document = { createElement: tag => new Node(tag), querySelectorAll: () => [] };
  const bridge = { ready: true, subscribe(type, callback) { (handlers[type] ||= []).push(callback); },
    onReady(callback) { callback(); }, send(payload) { sent.push(payload); } };
  const window = { __roseBridge: bridge, addEventListener(type, callback) { (handlers[`window:${type}`] ||= []).push(callback); },
    dispatchEvent(event) { for (const fn of handlers[`window:${event.type}`] || []) fn(event); } };
  const context = { window, document, Date, Math, console,
    CustomEvent: class { constructor(type, init = {}) { this.type = type; this.detail = init.detail; } },
    setInterval(fn) { intervals.push(fn); return intervals.length; }, clearInterval() {} };
  vm.runInNewContext(source, context); intervals[0]();
  const host = new Node('div'); window.dispatchEvent(new context.CustomEvent('rose-hub-settings', { detail: { target: host } }));
  const request = sent.find(message => message.type === 'settings-request');
  for (const fn of handlers['settings-data']) fn({ requestId: request.requestId, threshold: .5,
    monitorAutoResumeTimeout: 60, autostart: false, hideEmptyCategories: false, gamePath: '' });
  assert.equal(host.querySelectorAll('select').find(node => node.name === 'lolalyticsRiskLevel').value, 'medium');
});
