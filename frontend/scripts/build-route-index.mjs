/**
 * Generates `app/(dashboard)/_shell/route-index.generated.ts` from the route
 * tree on disk.
 *
 * The command palette used to index the hand-written nav model, which listed
 * 57 of the app's ~242 real routes — so most of the product was reachable only
 * by typing the URL. Deriving the index from the filesystem means a new page is
 * searchable the moment it exists, and the two can never drift apart.
 *
 * Run via `npm run build:routes` (also wired into `prebuild`).
 */

import { readdirSync, readFileSync, statSync, writeFileSync } from 'node:fs';
import { dirname, join, relative, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = dirname(fileURLToPath(import.meta.url));
const APP_ROOT = resolve(HERE, '..', 'app');
const DASHBOARD_ROOT = join(APP_ROOT, '(dashboard)');
const OUTPUT = join(DASHBOARD_ROOT, '_shell', 'route-index.generated.ts');

/** Path prefix -> rail section. Longest prefix wins. */
const SECTION_BY_PREFIX = [
  ['/studio/social-studio', 'social'],
  ['/studio', 'studio'],
  ['/seo', 'seo'],
  ['/platform', 'apps'],
  ['/account', 'settings'],
  ['/billing', 'settings'],
  ['/ira', 'ai'],
  ['/dashboard', 'dashboard'],
];

const WORD_OVERRIDES = new Map(
  Object.entries({
    ai: 'AI',
    aeo: 'AEO',
    geo: 'GEO',
    aio: 'AIO',
    llmo: 'LLMO',
    sxo: 'SXO',
    gxo: 'GXO',
    vso: 'VSO',
    peao: 'PEAO',
    daeo: 'DAEO',
    cxao: 'CXAO',
    msvo: 'MSVO',
    sageo: 'SAGEO',
    seo: 'SEO',
    ux: 'UX',
    ui: 'UI',
    roi: 'ROI',
    kpi: 'KPI',
    kpis: 'KPIs',
    crm: 'CRM',
    cdn: 'CDN',
    siem: 'SIEM',
    ira: 'IRA',
    ugc: 'UGC',
    api: 'API',
    ab: 'A/B',
    eeat: 'E-E-A-T',
    gbp: 'GBP',
    vse: 'VSE',
    sso: 'SSO',
  })
);

function titleize(slug) {
  return slug
    .split('-')
    .filter(Boolean)
    .map((word) => WORD_OVERRIDES.get(word.toLowerCase()) ?? word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

function walk(dir, out = []) {
  for (const entry of readdirSync(dir)) {
    const full = join(dir, entry);
    if (statSync(full).isDirectory()) {
      walk(full, out);
    } else if (entry === 'page.tsx') {
      out.push(full);
    }
  }
  return out;
}

/** Filesystem path -> URL route, dropping route groups like `(dashboard)`. */
function toRoute(file) {
  const rel = relative(APP_ROOT, dirname(file)).split(/[\\/]/);
  const segments = rel.filter((segment) => !(segment.startsWith('(') && segment.endsWith(')')));
  return `/${segments.join('/')}`;
}

function sectionFor(route) {
  for (const [prefix, section] of SECTION_BY_PREFIX) {
    if (route === prefix || route.startsWith(`${prefix}/`)) return section;
  }
  return 'apps';
}

/**
 * Alias routes are excluded from search: they re-export or redirect to a
 * canonical page, so indexing both would show the same tool twice under
 * different names.
 */
function aliasTarget(source) {
  const reexport = source.match(/^\s*export\s*\{\s*default\s*\}\s*from\s*['"]([^'"]+)['"]/m);
  if (reexport) return reexport[1];
  const redirect = source.match(/redirect\(\s*['"]([^'"]+)['"]\s*\)/);
  if (redirect) return redirect[1];
  return null;
}

/**
 * A heading is only usable as a nav title if it names the tool. Error copy
 * ("Brand Kit unavailable") and marketing sentences ("Run your AI social media
 * manager from one place.") both render as `<h1>` here, so they are rejected in
 * favour of the slug.
 */
function isUsableTitle(text) {
  if (!text) return false;
  const trimmed = text.trim();
  if (trimmed.length < 2 || trimmed.length > 48) return false;
  if (/[.!?]$/.test(trimmed)) return false;
  if (/\b(unavailable|not found|error|failed|loading|coming soon)\b/i.test(trimmed)) return false;
  return trimmed.split(/\s+/).length <= 6;
}

/** Best-effort human title from the page source, before falling back to the slug. */
function titleFromSource(source) {
  const pageHeader = source.match(/<PageHeader[^>]*\btitle=(?:"([^"]+)"|\{'([^']+)'\})/);
  const headerTitle = pageHeader?.[1] || pageHeader?.[2];
  if (isUsableTitle(headerTitle)) return headerTitle.trim();
  const h1 = source.match(/<h1[^>]*>\s*([^<{][^<]*?)\s*<\/h1>/);
  if (isUsableTitle(h1?.[1])) return h1[1].trim();
  return null;
}

function loadSeoCatalog() {
  const file = join(DASHBOARD_ROOT, 'seo', 'module-catalog.ts');
  const source = readFileSync(file, 'utf8');
  const byRoute = new Map();
  const entry = /\{\s*title:\s*'((?:[^'\\]|\\.)*)',[\s\S]*?category:\s*'((?:[^'\\]|\\.)*)',\s*routePath:\s*'([^']+)'/g;
  let match;
  while ((match = entry.exec(source))) {
    byRoute.set(match[3], { title: match[1].replace(/\\'/g, "'"), category: match[2] });
  }
  return byRoute;
}

/** Nav labels become search aliases, so old menu wording still finds the page. */
function loadNavLabels() {
  const source = readFileSync(join(DASHBOARD_ROOT, '_shell', 'nav.ts'), 'utf8');
  const byRoute = new Map();
  const item = /\{\s*label:\s*'((?:[^'\\]|\\.)*)',\s*href:\s*(?:seo\('([^']+)'\)|'([^']+)')\s*\}/g;
  let match;
  while ((match = item.exec(source))) {
    const route = match[2] ? `/seo/${match[2]}` : match[3];
    const label = match[1].replace(/\\'/g, "'");
    if (!byRoute.has(route)) byRoute.set(route, new Set());
    byRoute.get(route).add(label);
  }
  return byRoute;
}

const seoCatalog = loadSeoCatalog();
const navLabels = loadNavLabels();

const pages = [];
const aliases = [];

for (const file of walk(DASHBOARD_ROOT).sort()) {
  const route = toRoute(file);
  if (route.includes('[')) continue; // dynamic segments have no static title

  const source = readFileSync(file, 'utf8');
  const alias = aliasTarget(source);
  if (alias) {
    aliases.push({ route, alias });
    continue;
  }

  const slug = route.split('/').filter(Boolean).at(-1) ?? 'dashboard';
  const catalog = seoCatalog.get(route);
  const title = catalog?.title ?? titleFromSource(source) ?? titleize(slug);
  const group = catalog?.category ?? titleize(route.split('/').filter(Boolean).at(-2) ?? 'General');

  const keywords = new Set(navLabels.get(route) ?? []);
  keywords.delete(title);

  const entry = { route, title, section: sectionFor(route), group, keywords: [...keywords].sort() };
  // Vendor-parity consoles report *Nuxtron's own* integration build status —
  // "Production Gate: FAILED", implementation percentages, rollout blockers.
  // That is internal engineering telemetry, so it is kept out of customer
  // search and navigation rather than advertised alongside real tools.
  //
  // Matched on the build-status vocabulary rather than the `/search-everywhere/`
  // base path: the lead-gen calculators call the same API but show the customer
  // their own numbers, so they must stay discoverable.
  if (/production-gate|Production Gate|implementation_pct|parity_pct|parity-audit/.test(source)) {
    entry.internal = true;
  }
  pages.push(entry);
}

pages.sort((a, b) => a.route.localeCompare(b.route));

const banner = `// AUTO-GENERATED by scripts/build-route-index.mjs — do not edit by hand.
// Regenerate with \`npm run build:routes\`.
`;

const body = `${banner}
export type RouteIndexEntry = {
  route: string;
  title: string;
  section: string;
  group: string;
  /** Alternate wording (mostly legacy nav labels) that should still match. */
  keywords: readonly string[];
  /** Internal engineering telemetry — excluded from customer search and nav. */
  internal?: boolean;
};

export const ROUTE_INDEX: readonly RouteIndexEntry[] = ${JSON.stringify(pages, null, 2)};

/** Routes that only re-export or redirect to a canonical page. */
export const ROUTE_ALIASES: Readonly<Record<string, string>> = ${JSON.stringify(
  Object.fromEntries(aliases.map((a) => [a.route, a.alias])),
  null,
  2
)};
`;

writeFileSync(OUTPUT, body);
console.log(`route-index: ${pages.length} pages, ${aliases.length} aliases -> ${relative(process.cwd(), OUTPUT)}`);
