// Renderiza cada opção em cada tamanho do .ico, com fundo transparente.
const {chromium} = require(process.env.PW || '/opt/node-tools/node_modules/playwright');
const fs = require('node:fs'), path = require('node:path');
const here = __dirname, sizes = [16, 20, 24, 32, 40, 48, 64, 128, 256];
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();
  fs.mkdirSync(path.join(here, 'png'), {recursive: true});
  for (const file of fs.readdirSync(path.join(here, 'svg')).filter(f => /^[a-z]\.svg$/.test(f))) {
    const key = file[0];
    for (const size of sizes) {
      const source = fs.readFileSync(path.join(here, 'svg', `${key}.svg`), 'utf8');
      await page.setViewportSize({width: size, height: size});
      await page.setContent(`<html><body style="margin:0;background:transparent">${source.replace('width="256" height="256"', `width="${size}" height="${size}"`)}</body></html>`);
      await page.screenshot({path: path.join(here, 'png', `${key}-${size}.png`), omitBackground: true});
    }
  }
  await browser.close();
})();
