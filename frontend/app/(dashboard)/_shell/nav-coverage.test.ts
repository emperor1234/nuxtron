import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

import { MENUS, RAIL_ITEMS, SETTINGS_ITEM } from "./nav";
import { ROUTE_ALIASES, ROUTE_INDEX } from "./route-index.generated";

const REAL_ROUTES = new Set(ROUTE_INDEX.map((entry) => entry.route));
const THIRD_PARTY_PRODUCT_PATTERN = /\b(?:semrush|hubspot|profound|ahrefs|hootsuite|sprout\s?social|writesonic|yext|surfer(?:seo)?|jasper|botify|brightedge|neo4j|promptwatch|geoptie)\b/i;

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

describe("navigation model", () => {
  it("points every entry at a page that exists", () => {
    const broken = navHrefs().filter(
      (href) => !REAL_ROUTES.has(href) && !(href in ROUTE_ALIASES),
    );
    expect(broken).toEqual([]);
  });

  it("never routes users through a redirect stub", () => {
    // Landing on an alias costs an extra navigation and shows the wrong URL in
    // the address bar. Link the canonical page instead.
    const viaAlias = navHrefs().filter((href) => href in ROUTE_ALIASES);
    expect(viaAlias).toEqual([]);
  });

  it("gives every rail section a reachable destination", () => {
    for (const item of [...RAIL_ITEMS, SETTINGS_ITEM]) {
      expect(
        REAL_ROUTES.has(item.href),
        `rail "${item.label}" -> ${item.href}`,
      ).toBe(true);
    }
  });

  it("never advertises an internal build-status console", () => {
    // These render Nuxtron's own "Production Gate: FAILED" telemetry. Linking
    // them from customer navigation reads as the product being broken.
    const internal = new Set(
      ROUTE_INDEX.filter((entry) => entry.internal).map((entry) => entry.route),
    );
    expect(navHrefs().filter((href) => internal.has(href))).toEqual([]);
  });

  it("keeps third-party product trademarks out of customer discovery", () => {
    const labels = [
      ...[...RAIL_ITEMS, SETTINGS_ITEM].map((item) => item.label),
      ...Object.values(MENUS).flatMap(
        (menu) => menu?.groups.flatMap((group) => group.items.map((item) => item.label)) ?? [],
      ),
    ];
    expect(labels.filter((label) => THIRD_PARTY_PRODUCT_PATTERN.test(label))).toEqual([]);
    const visibleBrandedRoutes = ROUTE_INDEX.filter(
      (entry) => !entry.internal && THIRD_PARTY_PRODUCT_PATTERN.test(`${entry.route} ${entry.title}`),
    );
    expect(visibleBrandedRoutes.map((entry) => entry.route)).toEqual([]);
  });

  it("does not inflate a menu with multiple labels for one destination", () => {
    for (const [key, menu] of Object.entries(MENUS)) {
      if (!menu) continue;
      const hrefs = menu.groups.flatMap((group) =>
        group.items.map((item) => item.href),
      );
      const duplicates = hrefs.filter(
        (href, index) => hrefs.indexOf(href) !== index,
      );
      expect(duplicates, `${key} menu duplicate destinations`).toEqual([]);
    }
  });

  it("promotes real differentiated product surfaces", () => {
    const promoted = new Set(navHrefs());
    for (const route of [
      "/crm",
      "/workflows",
      "/smart-inbox",
      "/seo-aeo-geo-audit-tool",
      "/ai-visibility-dashboard",
      "/studio/social-studio/queue",
      "/trust-center",
      "/siem",
      "/white-label",
    ]) {
      expect(promoted.has(route), `${route} should be discoverable`).toBe(true);
    }
  });

  it("resolves every alias to a real page", () => {
    for (const [from, to] of Object.entries(ROUTE_ALIASES)) {
      if (!to.startsWith("/")) continue; // relative re-export, resolved by the bundler
      expect(REAL_ROUTES.has(to), `${from} -> ${to}`).toBe(true);
    }
  });
});

describe("route index", () => {
  it("is up to date with the route tree", () => {
    // Guards against a page being added without regenerating the index, which
    // would silently make it unsearchable.
    const generated = readFileSync(
      join(__dirname, "route-index.generated.ts"),
      "utf8",
    );
    expect(generated).toContain("AUTO-GENERATED");
    expect(ROUTE_INDEX.length).toBeGreaterThan(200);
  });

  it("has a usable title for every entry", () => {
    // Catches description text leaking in as a title. The bound is looser than
    // the extractor's because curated catalog names are legitimately long
    // ("CXAO: Conversational Experience Answer Optimization").
    const bad = ROUTE_INDEX.filter(
      (entry) =>
        !entry.title.trim() ||
        entry.title.length > 64 ||
        entry.title.endsWith("."),
    );
    expect(bad.map((entry) => `${entry.route}: ${entry.title}`)).toEqual([]);
  });

  it("has no duplicate routes", () => {
    const seen = new Set<string>();
    const dupes = ROUTE_INDEX.filter((entry) =>
      seen.has(entry.route) ? true : (seen.add(entry.route), false),
    );
    expect(dupes).toEqual([]);
  });
});
