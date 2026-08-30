import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';

import { MENUS, RAIL_ITEMS, SETTINGS_ITEM } from './nav';
import { ROUTE_ALIASES, ROUTE_INDEX } from './route-index.generated';

const REAL_ROUTES = new Set(ROUTE_INDEX.map((entry) => entry.route));

function navHrefs(): string[] {
  const hrefs = [...RAIL_ITEMS, SETTINGS_ITEM].map((item) => item.href);
  for (const menu of Object.values(MENUS)) {
    if (!menu) continue;
    for (const group of menu.groups) {
      for (const item of group.items) hrefs.push(item.href);
    }
  }
  return hrefs;
}

describe('navigation model', () => {
  it('points every entry at a page that exists', () => {
    const broken = navHrefs().filter((href) => !REAL_ROUTES.has(href) && !(href in ROUTE_ALIASES));
    expect(broken).toEqual([]);
  });

  it('never routes users through a redirect stub', () => {
    // Landing on an alias costs an extra navigation and shows the wrong URL in
    // the address bar. Link the canonical page instead.
    const viaAlias = navHrefs().filter((href) => href in ROUTE_ALIASES);
    expect(viaAlias).toEqual([]);
  });

  it('gives every rail section a reachable destination', () => {
    for (const item of [...RAIL_ITEMS, SETTINGS_ITEM]) {
      expect(REAL_ROUTES.has(item.href), `rail "${item.label}" -> ${item.href}`).toBe(true);
    }
  });

  it('never advertises an internal build-status console', () => {
    // These render Nuxtron's own "Production Gate: FAILED" telemetry. Linking
    // them from customer navigation reads as the product being broken.
    const internal = new Set(ROUTE_INDEX.filter((entry) => entry.internal).map((entry) => entry.route));
    expect(navHrefs().filter((href) => internal.has(href))).toEqual([]);
  });

  it('resolves every alias to a real page', () => {
    for (const [from, to] of Object.entries(ROUTE_ALIASES)) {
      if (!to.startsWith('/')) continue; // relative re-export, resolved by the bundler
      expect(REAL_ROUTES.has(to), `${from} -> ${to}`).toBe(true);
    }
  });
});

describe('route index', () => {
  it('is up to date with the route tree', () => {
    // Guards against a page being added without regenerating the index, which
    // would silently make it unsearchable.
    const generated = readFileSync(join(__dirname, 'route-index.generated.ts'), 'utf8');
    expect(generated).toContain('AUTO-GENERATED');
    expect(ROUTE_INDEX.length).toBeGreaterThan(200);
  });

  it('has a usable title for every entry', () => {
    // Catches description text leaking in as a title. The bound is looser than
    // the extractor's because curated catalog names are legitimately long
    // ("CXAO: Conversational Experience Answer Optimization").
    const bad = ROUTE_INDEX.filter(
      (entry) => !entry.title.trim() || entry.title.length > 64 || entry.title.endsWith('.')
    );
    expect(bad.map((entry) => `${entry.route}: ${entry.title}`)).toEqual([]);
  });

  it('has no duplicate routes', () => {
    const seen = new Set<string>();
    const dupes = ROUTE_INDEX.filter((entry) => (seen.has(entry.route) ? true : (seen.add(entry.route), false)));
    expect(dupes).toEqual([]);
  });
});
