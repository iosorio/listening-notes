/* Optional integration check: PLAYWRIGHT_MODULE may point to an installed module. */
const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const http = require('node:http');
const path = require('node:path');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');

const root = path.resolve(__dirname, '..');
const desired = require('../radar/discovery/status.json');
const mime = { '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css', '.json': 'application/json' };
const server = http.createServer(async (request, response) => {
  try {
    let target = path.resolve(root, `.${decodeURIComponent(new URL(request.url, 'http://localhost').pathname)}`);
    if (!target.startsWith(`${root}${path.sep}`)) throw new Error('Outside site root');
    if ((await fs.stat(target)).isDirectory()) target = path.join(target, 'index.html');
    response.setHeader('Content-Type', mime[path.extname(target)] || 'application/octet-stream');
    response.end(await fs.readFile(target));
  } catch {
    response.writeHead(404);
    response.end();
  }
});

const run = (id, started, completed, status = 'success') => ({
  run_id: id, started_at: started, completed_at: completed, status, trigger: 'scheduled',
  executor: 'browser-test', threads_checked: ['tokyo_kanto', 'us_corridor'],
  sources_checked: 4, candidates_reviewed: 0, events_admitted: 0, events_published: 0, material_updates: 0,
  error_summary: status === 'success' ? null : 'Test source failure.'
});

async function main() {
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  const base = `http://127.0.0.1:${server.address().port}`;
  const browser = await chromium.launch({headless: true});
  try {
    for (const language of ['en', 'es']) {
      const page = await browser.newPage({viewport: {width: 1280, height: 900}});
      const errors = [];
      page.on('pageerror', error => errors.push(error.message));
      await page.clock.install({time: new Date('2026-09-30T12:00:00Z')});
      let status = structuredClone(desired);
      let runs = {schema_version: 1, runs: []};
      let failEvents = false;
      let failTelemetry = false;
      await page.route('**/discovery/status.json', route => route.fulfill({json: status}));
      await page.route('**/discovery/runs.json', route => failTelemetry ? route.abort() : route.fulfill({json: runs}));
      await page.route('**/events.json', route => failEvents ? route.abort() : route.continue());
      const visit = async state => {
        await page.goto(`${base}/radar/${language === 'es' ? 'es/' : ''}`);
        await page.waitForFunction(expected => document.querySelector('.radar-status-title')?.classList.contains(`radar-status--${expected}`), state);
      };
      await visit('unknown');
      assert.equal(await page.locator('.radar-status-title').innerText(), language === 'en' ? 'RADAR — UNKNOWN' : 'RADAR — DESCONOCIDO');
      assert.match(await page.locator('#radar-status').innerText(), language === 'en' ? /Requested state: ON/ : /Estado solicitado: ENCENDIDO/);
      assert.equal(await page.locator('#radar-status a').first().innerText(), language === 'en' ? 'Edit requested state' : 'Editar estado solicitado');
      if (process.env.RADAR_SCREENSHOT_DIR) {
        await fs.mkdir(process.env.RADAR_SCREENSHOT_DIR, {recursive: true});
        await page.locator('#radar-status').screenshot({path: path.join(process.env.RADAR_SCREENSHOT_DIR, `radar-status-${language}.png`)});
      }
      failEvents = true;
      await visit('unknown');
      await page.locator('#radar .empty').waitFor();
      failEvents = false;
      runs = {schema_version: 1, runs: [null]};
      await visit('unknown');
      await page.locator('#filters button').first().waitFor();
      failTelemetry = true;
      await visit('unknown');
      status.enabled = false;
      await visit('off');
      failTelemetry = false;
      status.enabled = true;
      const success = run('success', '2026-09-30T10:00:00Z', '2026-09-30T10:10:00Z');
      runs.runs = [success];
      await visit('healthy');
      runs.runs.push(run('failed', '2026-09-30T11:00:00Z', '2026-09-30T11:10:00Z', 'error'));
      runs.runs.push(run('partial', '2026-09-30T11:20:00Z', '2026-09-30T11:30:00Z', 'partial'));
      await visit('error');
      assert.match(await page.locator('#radar-status').innerText(), /Test source failure/);
      runs.runs = [success];
      status.enabled = false;
      await visit('off');
      assert.doesNotMatch(await page.locator('#radar-status').innerText(), /Next expected scan|Próximo escaneo esperado/);
      status.enabled = true;
      runs.runs = [run('almost-stale', '2026-09-29T23:50:00Z', '2026-09-30T00:00:30Z')];
      await visit('healthy');
      await page.clock.fastForward(61_000);
      await page.waitForSelector('.radar-status--stale');
      // A heartbeat published after initial load is picked up without navigation.
      runs.runs.push(run('new', '2026-09-30T11:50:00Z', '2026-09-30T12:00:00Z'));
      await page.clock.fastForward(60_000);
      await page.waitForSelector('.radar-status--healthy');
      await page.setViewportSize({width: 320, height: 740});
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
      assert.deepEqual(errors, []);
      await page.close();
      console.log(`${language}: requested/observed state, failures, recovery, refresh, and mobile layout passed`);
    }
  } finally {
    await browser.close();
    await new Promise(resolve => server.close(resolve));
  }
}
main().catch(error => { console.error(error); server.close(); process.exitCode = 1; });
