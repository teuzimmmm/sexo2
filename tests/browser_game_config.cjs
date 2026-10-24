// Run with PLAYWRIGHT_MODULE pointing at an installed Playwright package.
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || '../ui-test-runtime/node_modules/playwright');
const assert = require('node:assert/strict');
const path = require('node:path');

(async () => {
  const browser = await chromium.launch({ headless: true, channel: 'chromium' });
  try {
    const page = await browser.newPage({ viewport: { width: 820, height: 720 } });
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.setContent('<main class="s2" id="sexo2-hub"><div id="sexo2-hub-content"></div></main>');
    await page.addStyleTag({ path: path.resolve('design/tokens.css') });
    await page.addStyleTag({ content: `
      body { background:#0d0e10; margin:0; padding:24px; }
      #sexo2-hub { --s2-fg:#eee; --s2-fg-2:#ccc; --s2-fg-3:#999; --s2-line:#333; }
      button,input,select { font:inherit; color:#eee; background:#202124; border:1px solid #444; padding:6px 10px; }
      [hidden] { display:none!important; }
    ` });
    await page.evaluate(() => {
      window.sent = [];
      window.handlers = {};
      window.__sexo2Bridge = {
        ready: true,
        subscribe(type, callback) { window.handlers[type] = callback; },
        onReady(callback) { callback(); },
        send(payload) {
          window.sent.push(payload);
          if (payload.type === 'settings-request') {
            setTimeout(() => window.handlers['settings-data']({
              requestId: payload.requestId, threshold: .5, monitorAutoResumeTimeout: 60,
            }), 0);
          }
        },
      };
    });
    await page.addScriptTag({ path: path.resolve('Pengu Loader/plugins/SEXO2-Settings/index.js') });
    await page.waitForFunction(() => window.handlers['settings-game-imported']);
    await page.evaluate(() => window.dispatchEvent(new CustomEvent('sexo2-hub-settings', {
      detail: { target: document.getElementById('sexo2-hub-content') },
    })));
    const trigger = page.getByRole('button', { name: 'Importar configuração de jogo padrão', exact: true });
    const imports = () => page.evaluate(() => window.sent.filter(p => p.type === 'settings-import-game'));
    await trigger.click();
    assert.equal((await imports()).length, 0);
    await page.getByRole('button', { name: 'Cancelar', exact: true }).click();
    assert.equal((await imports()).length, 0);
    await trigger.click();
    await page.getByRole('button', { name: 'Confirmar', exact: true }).click();
    const sent = await imports();
    assert.equal(sent.length, 1);
    assert.equal(sent[0].confirmed, true);
    assert.equal(await trigger.isDisabled(), true);
    await page.evaluate(() => window.handlers['settings-game-imported']({ requestId: 'stale', success: true }));
    assert.equal(await trigger.isDisabled(), true);
    await page.evaluate(id => window.handlers['settings-game-imported']({
      requestId: id, success: false, error: 'Saia da partida antes de importar a configuração de jogo padrão.',
    }), sent[0].requestId);
    assert.equal(await trigger.isDisabled(), false);
    await page.getByText('Saia da partida antes de importar a configuração de jogo padrão.', { exact: true }).waitFor();
    await trigger.click();
    await page.getByRole('button', { name: 'Confirmar', exact: true }).click();
    const latest = (await imports()).at(-1);
    await page.evaluate(id => window.handlers['settings-game-imported']({ requestId: id, success: true }), latest.requestId);
    await page.getByText('Configuração importada. A cópia anterior foi salva. Confira os ajustes na próxima partida.', { exact: true }).waitFor();
    assert.equal(await trigger.isDisabled(), false);
    assert.deepEqual(errors, []);
    if (process.env.SEXO2_SCREENSHOT) await page.screenshot({ path: process.env.SEXO2_SCREENSHOT, fullPage: true });
    console.log('OK: confirmação, cancelamento, duplicação, resposta antiga, erro e sucesso.');
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
