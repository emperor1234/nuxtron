import { existsSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { MENUS } from "@/app/(dashboard)/_shell/nav";
import { ROUTE_INDEX } from "@/app/(dashboard)/_shell/route-index.generated";
import ROUTE_RENAMES from "./route-renames.json";

const ROUTES = new Set(ROUTE_INDEX.map((entry) => entry.route));
const SOURCES = new Set(ROUTE_RENAMES.redirects.map((r) => r.from));
const DASHBOARD_ROOT = join(__dirname, "..", "(dashboard)");
const APP_ROOT = join(__dirname, "..");
const DESTINATIONS = new Map(ROUTE_RENAMES.redirects.map(({ from, to }) => [from, to]));
const LABELS = Object.values(MENUS).flatMap(
  (menu) => menu?.groups.flatMap((group) => group.items.map((item) => item.label)) ?? [],
);

function pageFilesFor(route: string): string[] {
  const segments = route.split("/").filter(Boolean);
  return [
    join(DASHBOARD_ROOT, ...segments, "page.tsx"),
    join(APP_ROOT, "(public)", ...segments, "page.tsx"),
  ];
}

function routeExists(route: string): boolean {
  return ROUTES.has(route) || pageFilesFor(route).some(existsSync);
}

describe("renamed and retired dashboard routes", () => {
  it("redirects every old URL to a page that exists", () => {
    expect(ROUTE_RENAMES.redirects.filter((r) => !routeExists(r.to))).toEqual([]);
  });

  it("leaves no page behind at an old URL", () => {
    // next.config redirects run before the filesystem, so a page left at the
    // old path would be unreachable dead code.
    expect([...SOURCES].filter((from) => ROUTES.has(from))).toEqual([]);
    expect([...SOURCES].filter((from) => pageFilesFor(from).some(existsSync))).toEqual([]);
  });

  it("never chains one redirect into another", () => {
    expect(ROUTE_RENAMES.redirects.filter((r) => SOURCES.has(r.to))).toEqual([]);
  });

  it("sends pages retired for lacking a working backend to their section hub", () => {
    const retired = [
      "/seo/keywords",
      "/seo/rank-tracking",
      "/seo/competitor",
      "/seo/technical",
      "/seo/domain-overview",
      "/seo/market-explorer",
      "/seo/pla-research",
      "/seo/content-auditor",
      "/seo/programmatic",
      "/media-processing",
      "/studio/backlink-intelligence",
    ];
    for (const from of retired) {
      expect(ROUTES.has(from), from).toBe(false);
      expect(DESTINATIONS.get(from), from).toMatch(/^\/(seo|studio|dashboard)$/);
    }
    expect(DESTINATIONS.get("/studio/social-studio/audience")).toBe("/studio/social-studio");
    expect(DESTINATIONS.get("/studio/social-studio/best-time")).toBe("/studio/social-studio");
  });

  it("does not advertise retired capabilities in any menu", () => {
    for (const label of [
      "Keyword Data Review",
      "Rank Position Review",
      "Competitor Research",
      "Technical SEO Audit",
      "Domain Overview",
      "Market Explorer",
      "Media Processing",
      "Audience Insights",
      "Best Time to Post",
    ]) {
      expect(LABELS).not.toContain(label);
    }
  });

  it("keeps vendor names out of customer routes and menu labels", () => {
    const VENDOR = /lately|buffer|owly|kodee|promptwatch|seo-ai-assist|one2target|contentshake|content\s?shake|eyeon|semrush|ahrefs|gtmetrix|ocoya|manychat/i;
    const visible = ROUTE_INDEX.filter((entry) => !entry.internal);
    expect(visible.filter((entry) => VENDOR.test(entry.route) || VENDOR.test(entry.title)).map((e) => e.route)).toEqual([]);
    expect(LABELS.filter((label) => VENDOR.test(label))).toEqual([]);
  });

  it("gives each destination one name across all menus", () => {
    const names = new Map<string, Set<string>>();
    for (const menu of Object.values(MENUS)) {
      for (const item of menu?.groups.flatMap((group) => group.items) ?? []) {
        const set = names.get(item.href) ?? new Set();
        set.add(item.label);
        names.set(item.href, set);
      }
    }
    const conflicting = [...names].filter(([, labels]) => labels.size > 1).map(([href, labels]) => [href, [...labels]]);
    expect(conflicting).toEqual([]);
  });
});
