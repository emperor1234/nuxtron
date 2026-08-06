import { chromium, devices } from 'playwright';

const BASE = 'http://localhost:4173';
const DEFAULT_PATHS = [
  '/dashboard', '/finance-ops', '/crm', '/crm/abm', '/ai-analytics', '/ai-security',
  '/content-generation', '/platform/ai-agent', '/platform/backend', '/seo', '/seo/performance',
  '/seo/aeo', '/seo/geo', '/seo/llmo', '/seo/schemas', '/seo/programmatic', '/seo/ads-smart-schedule',
  '/seo/backlink-intelligence', '/seo/keywords', '/seo/competitor', '/seo/local-heatmap', '/seo/technical',
  '/seo/on-page', '/seo/sxo', '/seo/gxo', '/seo/ux', '/seo/client-portal', '/seo/semrush-command-center',
  '/studio/social-studio', '/studio/rank-tracker', '/studio/editor', '/studio/social-studio/calendar',
  '/studio/social-studio/analytics', '/studio/brand-kit', '/studio/lately', '/media-processing',
  '/benchmarks', '/hubspot-e2e', '/billing', '/buffer-create', '/buffer-analyze', '/vendor-inventory-report',
  '/outcome-graph', '/social-media-roi', '/siem', '/vse', '/workflows', '/reviews', '/disputes',
  '/api-governance', '/ira-monitor', '/smart-inbox', '/social-listening', '/playbooks', '/platform-ops',
];
const MOBILE_ONLY = process.argv.includes('--mobile');
const PATHS = DEFAULT_PATHS;

const MOBILE = { width: 390, height: 844 };
const DESKTOP = { width: 1280, height: 900 };

async function measure(page, path, viewport) {
  await page.setViewportSize(viewport);
  const res = await page.goto(`${BASE}${path}`, { waitUntil: 'domcontentloaded', timeout: 90000 }).catch((e) => { console.log('  goto err', path, e.message); return null; });
  await page.waitForTimeout(1200);
  const data = await page.evaluate(() => {
    const de = document.documentElement;
    const scrollW = de.scrollWidth;
    const clientW = de.clientWidth;
    const overflow = scrollW - clientW;
    // Find the widest offending elements
    let offenders = [];
    if (overflow > 1) {
      for (const el of document.querySelectorAll('main *')) {
        const r = el.getBoundingClientRect();
        if (r.right > clientW + 1 && r.width > 40) {
          offenders.push({
            tag: el.tagName.toLowerCase(),
            cls: (el.className && el.className.toString().slice(0, 40)) || '',
            right: Math.round(r.right),
            w: Math.round(r.width),
          });
        }
      }
      offenders = offenders.sort((a, b) => b.right - a.right).slice(0, 4);
    }
    return { scrollW, clientW, overflow, offenders };
  });
  return { status: res ? res.status() : 'ERR', ...data };
}

const browser = await chromium.launch();
const page = await browser.newPage();
let fails = 0;
for (const p of PATHS) {
  const m = await measure(page, p, MOBILE);
  const tag = m.overflow > 1 ? `OVERFLOW +${m.overflow}px` : 'ok';
  if (m.overflow > 1) fails++;
  console.log(`MOBILE  ${p.padEnd(30)} [${m.status}] ${tag}`);
  if (m.offenders?.length) {
    for (const o of m.offenders) console.log(`           ↳ <${o.tag}> .${o.cls} right=${o.right} w=${o.w}`);
  }
}
if (!MOBILE_ONLY) {
  console.log('---');
  for (const p of PATHS) {
    const d = await measure(page, p, DESKTOP);
    const tag = d.overflow > 1 ? `OVERFLOW +${d.overflow}px` : 'ok';
    if (d.overflow > 1) fails++;
    console.log(`DESKTOP ${p.padEnd(30)} [${d.status}] ${tag}`);
  }
}
await browser.close();
console.log(`\n${fails === 0 ? 'PASS — no horizontal overflow' : `FAIL — ${fails} pages overflow`}`);
process.exit(0);
