import { chromium } from 'playwright';

const url = 'http://localhost:4173/dashboard';
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
await page.goto(url, { waitUntil: 'networkidle' });
await page.waitForTimeout(1200);
await page.screenshot({ path: '/tmp/dash-default.png', fullPage: false });

const seo = page.locator('button:has-text("SEO")').first();
await seo.click();
await page.waitForTimeout(500);
await page.screenshot({ path: '/tmp/dash-flyout.png', fullPage: false });

await browser.close();
console.log('screenshots saved');
