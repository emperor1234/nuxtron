import { chromium } from 'playwright';
const BASE = 'http://localhost:4173';
const shots = [
  ['/ira-monitor', 'desktop', 1280, 900],
  ['/platform/ai-agent', 'desktop', 1280, 900],
  ['/seo/ux', 'desktop', 1280, 900],
  ['/seo/client-portal', 'desktop', 1280, 900],
  ['/ira-monitor', 'mobile', 390, 844],
  ['/platform/ai-agent', 'mobile', 390, 844],
];
const browser = await chromium.launch();
const page = await browser.newPage();
for (const [path, mode, w, h] of shots) {
  await page.setViewportSize({ width: w, height: h });
  await page.goto(`${BASE}${path}`, { waitUntil: 'domcontentloaded', timeout: 90000 }).catch(() => {});
  await page.waitForTimeout(1600);
  const name = `/tmp/shot_${mode}_${path.replace(/\//g, '_')}.png`;
  await page.screenshot({ path: name, fullPage: false });
  console.log('saved', name);
}
await browser.close();
