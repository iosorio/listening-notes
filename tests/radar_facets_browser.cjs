/* Run with PLAYWRIGHT_MODULE pointing to an installed Playwright module. */
const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const http = require('node:http');
const path = require('node:path');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');

const root = path.resolve(__dirname, '..');
const signalId = require('../radar/signals.json').signals.find(record => record.replaced_on === null).event_id;
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
    response.end('Not found');
  }
});
const button = (page, key, value) => page.locator(`#filters button[data-key="${key}"][data-value="${value}"]`);
const checked = async (locator, expected) => assert.equal(await locator.getAttribute('aria-pressed'), String(expected));

async function exercise(page, locale, origin) {
  const spanish = locale === 'es';
  await page.goto(`${origin}/radar/${spanish ? 'es/' : ''}`);
  await page.locator('#filters button').first().waitFor();
  const initial = await page.locator('#count').innerText();
  const initialTotal = Number(initial.match(/^\d+/)?.[0]);
  const areaValues = await page.locator('#filters button[data-key="radar_area"]:not([data-value=""])').evaluateAll(buttons => buttons.map(button => button.dataset.value));
  assert.deepEqual(areaValues, ['dmv', 'baltimore', 'philadelphia', 'newark', 'new_york', 'tokyo', 'kanagawa', 'saitama', 'new_jersey', 'unassigned'].filter(value => areaValues.includes(value)));
  assert.deepEqual(await page.locator('#filters [role="group"]').evaluateAll(groups => groups.map(group => group.getAttribute('aria-label'))),
    spanish ? ['Escenas y zonas', 'Recintos', 'Prioridades'] : ['Scenes and areas', 'Venues', 'Priorities']);
  let partitionTotal = 0;
  for (const value of areaValues) {
    await button(page, 'radar_area', value).click();
    const count = Number((await page.locator('#count').innerText()).match(/^\d+/)?.[0]);
    const ids = await page.locator('#radar .event').evaluateAll(cards => cards.map(card => card.dataset.eventId));
    assert.equal(ids.length, new Set(ids).size, `no duplicated events in ${value}`);
    assert.equal(ids.length, count, `no lost events in ${value}`);
    partitionTotal += count;
  }
  assert.equal(partitionTotal, initialTotal, 'each upcoming event belongs to exactly one scene, including the Signal');
  const dmv = button(page, 'radar_area', 'dmv');
  const blue = button(page, 'venue', 'blue-note-jazz-club-new-york');
  const blues = button(page, 'venue', 'blues-alley-washington-dc');
  await dmv.click();
  await checked(dmv, true);
  assert.equal(await blue.count(), 0, 'zero-match venue is absent from the DOM');
  const accessibility = await page.context().newCDPSession(page);
  const { nodes } = await accessibility.send('Accessibility.getFullAXTree');
  const blueAccessible = nodes.find(node => node.role?.value === 'button' && node.name?.value?.includes('Blue Note Jazz Club'));
  assert.equal(blueAccessible, undefined, 'zero-match venue is absent from the accessibility tree');
  await accessibility.detach();
  assert.equal(await blues.isEnabled(), true);
  const dmvCount = await page.locator('#count').innerText();
  assert.equal(await page.locator('#count').innerText(), dmvCount);
  await blues.press('Enter');
  await checked(blues, true);
  await checked(dmv, true);
  assert.equal(await page.evaluate(() => document.activeElement.dataset.value), 'blues-alley-washington-dc');
  assert.deepEqual(await page.locator('#filters button[data-key="radar_area"]:not([data-value=""])').evaluateAll(buttons => buttons.map(button => button.dataset.value)), areaValues, 'scene navigation keeps its order after filtering');
  assert.equal(await button(page, 'priority', 'A').isEnabled(), true);
  assert.equal(await button(page, 'priority', 'A+').isEnabled(), true);
  assert.equal(await button(page, 'priority', 'S').count(), 0);
  assert.equal(await button(page, 'priority', 'S+').count(), 0);
  await checked(button(page, 'priority', ''), true);
  await button(page, 'priority', 'A').click();
  await checked(button(page, 'priority', 'A'), true);
  assert.equal(await button(page, 'priority', 'S').count(), 0);
  assert.equal(await button(page, 'priority', 'A+').isEnabled(), true, 'changing tier replaces A');
  await button(page, 'priority', 'A+').press('Space');
  await checked(button(page, 'priority', 'A+'), true);
  assert.equal(await page.evaluate(() => document.activeElement.dataset.value), 'A+', 'focus survives the priority render');
  await button(page, 'priority', '').click();
  await button(page, 'venue', '').click();
  await checked(dmv, true);
  await checked(button(page, 'venue', ''), true);
  await button(page, 'radar_area', '').click();
  await checked(button(page, 'radar_area', ''), true);
  await blues.click();
  await checked(dmv, true);
  await checked(blues, true);
  await button(page, 'radar_area', 'new_york').click();
  await checked(button(page, 'radar_area', 'new_york'), true);
  await checked(button(page, 'venue', ''), true);
  assert.equal(await blue.isEnabled(), true);
  await blue.click();
  await checked(blue, true);
  await checked(button(page, 'radar_area', 'new_york'), true);
  await button(page, 'radar_area', '').click();
  await checked(button(page, 'venue', ''), true);
  await page.setViewportSize({ width: 320, height: 740 });
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true, '320 px has no horizontal overflow');
  assert.equal(await page.locator('#filters button').first().evaluate(element => element.getBoundingClientRect().height >= 44), true);
  await dmv.focus();
  await page.keyboard.press('Tab');
  assert.equal(await page.evaluate(() => document.activeElement?.disabled), false, 'Tab reaches an enabled control');
  await page.locator('#views button[data-value="archive"]').click();
  await checked(page.locator('#views button[data-value="archive"]'), true);
  await checked(button(page, 'radar_area', ''), true);
  await checked(button(page, 'venue', ''), true);
  await checked(button(page, 'priority', ''), true);
  assert.equal(await page.evaluate(() => document.activeElement.dataset.value), 'archive');
  assert.notEqual(await page.locator('#count').innerText(), initial);
  const archiveTotal = Number((await page.locator('#count').innerText()).match(/^\d+/)?.[0]);
  let archivePartitionTotal = 0;
  const archiveAreas = await page.locator('#filters button[data-key="radar_area"]:not([data-value=""])').evaluateAll(buttons => buttons.map(button => button.dataset.value));
  for (const value of archiveAreas) {
    await button(page, 'radar_area', value).click();
    const count = Number((await page.locator('#count').innerText()).match(/^\d+/)?.[0]);
    const ids = await page.locator('#radar .event').evaluateAll(cards => cards.map(card => card.dataset.eventId));
    assert.equal(ids.length, new Set(ids).size, `no duplicated archived events in ${value}`);
    assert.equal(ids.length, count, `no lost archived events in ${value}`);
    archivePartitionTotal += count;
  }
  assert.equal(archivePartitionTotal, archiveTotal, 'each archived event belongs to exactly one scene');
  await button(page, 'radar_area', 'dmv').click();
  assert.equal(await blue.count(), 0);
  await page.locator('#views button[data-value="upcoming"]').click();
  await checked(button(page, 'radar_area', ''), true);
  return initial;
}

(async () => {
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  const origin = `http://127.0.0.1:${server.address().port}`;
  let browser;
  try {
    browser = await chromium.launch({ channel: 'chrome', headless: true });
    for (const locale of ['en', 'es']) {
      const page = await browser.newPage();
      await page.addInitScript(() => {
        const RealDate = Date;
        globalThis.Date = class extends RealDate {
          constructor(...args) { super(...(args.length ? args : ['2026-09-15T12:00:00'])); }
          static now() { return new RealDate('2026-09-15T12:00:00').getTime(); }
        };
      });
      await exercise(page, locale, origin);
      await page.close();
      const signalPage = await browser.newPage();
      await signalPage.addInitScript(() => {
        const RealDate = Date;
        globalThis.Date = class extends RealDate {
          constructor(...args) { super(...(args.length ? args : ['2026-08-25T12:00:00'])); }
          static now() { return new RealDate('2026-08-25T12:00:00').getTime(); }
        };
      });
      await signalPage.goto(`${origin}/radar/${locale === 'es' ? 'es/' : ''}`);
      await signalPage.locator('#filters button').first().waitFor();
      assert.equal(await signalPage.locator('#signal').isVisible(), true);
      const kanagawa = button(signalPage, 'radar_area', 'kanagawa');
      assert.equal(await kanagawa.isEnabled(), true);
      await kanagawa.click();
      assert.equal(await signalPage.locator('#signal').isVisible(), false);
      assert.equal(await signalPage.locator(`#radar .event[data-event-id="${signalId}"]`).count(), 1);
      await signalPage.close();
    }
    console.log('RADAR browser facets: English, Spanish, keyboard, focus, mobile, both views, Signal passed');
  } finally {
    await browser?.close();
    server.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
