// Run with NODE_PATH pointing to a local Playwright installation.
const { chromium, firefox, webkit } = require('playwright');
const assert = require('node:assert/strict');

async function smoke(name, type) {
  const browser = await type.launch({ headless: !process.env.FOGO_HEADED, args: name === 'chromium' ? ['--enable-unsafe-swiftshader'] : [],
    firefoxUserPrefs: { 'webgl.force-enabled': true } });
  try {
    const mobile = process.env.FOGO_MOBILE === '1';
    const viewport = mobile ? { width: 390, height: 844 } : { width: 540, height: 860 };
    const page = await browser.newPage({ viewport, hasTouch: true, isMobile: mobile });
    const scale = viewport.width / 540;
    const tapMenu = y => {
      const targetY = viewport.height / 2 + (y - 430) * scale;
      return mobile ? page.touchscreen.tap(viewport.width / 2, targetY) :
        page.mouse.click(viewport.width / 2, targetY);
    };
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    page.on('console', line => {
      if (/SCRIPT ERROR|ERROR: Failed/.test(line.text())) errors.push(line.text());
    });
    await page.goto(process.env.FOGO_URL || 'http://127.0.0.1:8765');
    await page.getByRole('button', { name: 'Iniciar jogo' }).click();
    await page.waitForFunction(() => document.documentElement.dataset.gameReady === 'true' ||
      document.querySelector('#status').textContent.startsWith('Falha'), null, { timeout: 45000 });
    assert.equal(await page.evaluate(() => document.documentElement.dataset.gameReady), 'true',
      await page.locator('#status').textContent());
    await page.locator('#welcome').waitFor({ state: 'hidden' });
    async function screen(name) {
      await page.waitForFunction(value => document.documentElement.dataset.gameScreen === value, name, { timeout: name === 'Resultado' ? 60000 : 8000 });
    }
    for (const [y, expected] of [[324, 'Instrumento'], [410, 'Música'],
      [410, 'Dificuldade'], [399, 'Ensaio'], [519, 'Partida']]) {
      await tapMenu(y);
      await screen(expected);
    }
    const rhythm = page.locator('#rhythm-status');
    assert.equal(await rhythm.textContent(), 'Cortejo A');
    await page.waitForFunction(() => document.documentElement.dataset.gamePhase === 'playing');
    if (mobile) await page.touchscreen.tap(100, 48);
    else await page.keyboard.press('Escape');
    await screen('Pausa');
    await tapMenu(403);
    await screen('Partida');
    if (!mobile) await page.keyboard.press('f');
    await page.touchscreen.tap(viewport.width * .70, viewport.height * .86);
    await page.waitForFunction(() => document.querySelector('#rhythm-status').textContent === 'Cortejo B', null, { timeout: 45000 });
    await screen('Resultado');
    assert.deepEqual(errors, []);
    console.log(name + ': carregamento, partida, pausa, retomada, mudança de ritmo e resultado');
  } finally {
    await browser.close();
  }
}
(async () => {
  const browsers = process.env.FOGO_BROWSER === 'webkit' ? { webkit } : { chromium, firefox };
  for (const [name, type] of Object.entries(browsers)) {
    if (process.env.FOGO_BROWSER && process.env.FOGO_BROWSER !== name) continue;
    await smoke(name, type);
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
