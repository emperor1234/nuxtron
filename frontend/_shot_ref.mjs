import { chromium } from 'playwright';

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
const errors = [];
page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()); });
page.on('pageerror', (e) => errors.push('PAGEERROR: ' + e.message));

const url = 'http://localhost:8899/Nuxtron%20Homepage.html';
await page.goto(url, { waitUntil: 'networkidle' });
await page.waitForTimeout(3000);
await page.screenshot({ path: '/tmp/ref-hero.png' });

const h = await page.evaluate(() => document.body.scrollHeight);
console.log('ref scrollHeight:', h);

const ys = [1500, 3500, 5200, 6300, 7400, 8600, 9800, 11200, 12800, 14200, 15600];
for (const y of ys) {
  await page.evaluate((v) => window.scrollTo(0, v), y);
  await page.waitForTimeout(700);
  await page.screenshot({ path: `/tmp/ref-y${y}.png` });
}
await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
await page.waitForTimeout(1000);
await page.screenshot({ path: '/tmp/ref-bottom.png' });

console.log('ERRORS:', errors.length ? errors.slice(0, 20) : 'none');
await browser.close();
