import { chromium } from 'playwright';
const BASE = 'http://localhost:4173';
const path = process.argv[2] || '/studio/rank-tracker';
const browser = await chromium.launch();
const page = await browser.newPage();
await page.setViewportSize({ width: 390, height: 844 });
await page.goto(`${BASE}${path}`, { waitUntil: 'domcontentloaded', timeout: 90000 });
await page.waitForTimeout(1500);
const report = await page.evaluate(() => {
  const clientW = document.documentElement.clientWidth;
  // widest element overall
  let widest = null, max = 0;
  for (const el of document.querySelectorAll('body *')) {
    const r = el.getBoundingClientRect();
    if (r.width > max && r.right > clientW + 1) { max = r.width; widest = el; }
  }
  const chain = [];
  let el = widest;
  while (el && el !== document.documentElement) {
    const r = el.getBoundingClientRect();
    const cs = getComputedStyle(el);
    chain.push({
      tag: el.tagName.toLowerCase(),
      cls: (el.className?.toString?.() || '').slice(0, 46),
      w: Math.round(r.width),
      right: Math.round(r.right),
      ovx: cs.overflowX,
      disp: cs.display,
      minW: cs.minWidth,
      ws: cs.whiteSpace,
      inlineStyle: (el.getAttribute('style') || '').slice(0, 90),
    });
    el = el.parentElement;
  }
  return { clientW, chain };
});
console.log('clientW', report.clientW, 'path', path);
for (const c of report.chain) {
  console.log(`<${c.tag}> w=${c.w} right=${c.right} ovx=${c.ovx} disp=${c.disp} minW=${c.minW} ws=${c.ws}`);
  console.log(`    cls="${c.cls}" style="${c.inlineStyle}"`);
}
await browser.close();
