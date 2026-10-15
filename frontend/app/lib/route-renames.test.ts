import { existsSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { MENUS } from "@/app/(dashboard)/_shell/nav";
import { ROUTE_INDEX } from "@/app/(dashboard)/_shell/route-index.generated";
import { SEO_MODULE_CATALOG } from "@/app/(dashboard)/seo/module-catalog";
import ROUTE_RENAMES from "./route-renames.json";

const ROUTES = new Set(ROUTE_INDEX.map((entry) => entry.route));
const SOURCES = new Set(ROUTE_RENAMES.redirects.map((r) => r.from));
const DASHBOARD_ROOT = join(__dirname, "..", "(dashboard)");
const APP_ROOT = join(__dirname, "..");

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

describe("renamed dashboard routes", () => {
  it("redirects every old URL to a page that exists", () => {
    const missing = ROUTE_RENAMES.redirects.filter((r) => !routeExists(r.to));
    expect(missing).toEqual([]);
  });

  it("leaves no page behind at an old URL", () => {
    // next.config redirects run before the filesystem, so a page left at the
    // old path would be unreachable dead code.
    expect([...SOURCES].filter((from) => ROUTES.has(from))).toEqual([]);
    expect([...SOURCES].filter((from) => pageFilesFor(from).some(existsSync))).toEqual([]);
  });

  it("redirects the retired competitor-monitor path to its neutral canonical route", () => {
    const destinations = new Map(ROUTE_RENAMES.redirects.map(({ from, to }) => [from, to]));
    expect(destinations.get("/seo/eyeon")).toBe("/seo/competitor-monitoring");
    expect(ROUTES.has("/seo/eyeon")).toBe(false);
    expect(ROUTES.has("/seo/competitor-monitoring")).toBe(true);
  });

  it("routes legacy keyword tools to Keyword Data Review rather than workflow planning", () => {
    const destinations = new Map(ROUTE_RENAMES.redirects.map(({ from, to }) => [from, to]));
    expect(destinations.get("/seo/keywords-explorer")).toBe("/seo/keywords");
    expect(destinations.get("/studio/keyword-research")).toBe("/seo/keywords");
    expect(ROUTES.has("/seo/keywords")).toBe(true);
    expect(destinations.get("/seo/keywords-explorer")).not.toBe("/seo/planner");
  });

  it("consolidates Studio Rank Tracker into the single Rank Position Review route", () => {
    const destinations = new Map(ROUTE_RENAMES.redirects.map(({ from, to }) => [from, to]));
    expect(destinations.get("/studio/rank-tracker")).toBe("/seo/rank-tracking");
    expect(ROUTES.has("/studio/rank-tracker")).toBe(false);
    expect(ROUTES.has("/seo/rank-tracking")).toBe(true);
    const rankReviewLinks = Object.values(MENUS).flatMap(
      (menu) => menu?.groups.flatMap((group) => group.items) ?? [],
    ).filter((item) => item.href === "/seo/rank-tracking");
    expect(rankReviewLinks.map((item) => item.label)).toEqual(["Rank Position Review"]);
  });

  it("retires unverified local ranking and heatmap routes to the SEO hub", () => {
    const destinations = new Map(ROUTE_RENAMES.redirects.map(({ from, to }) => [from, to]));
    for (const from of ["/seo/local", "/seo/local-seo", "/seo/map-rank-tracker", "/seo/local-heatmap", "/seo/gbp-monitor"]) {
      expect(destinations.get(from)).toBe("/seo");
      expect(ROUTES.has(from)).toBe(false);
    }
    const labels = Object.values(MENUS).flatMap(
      (menu) => menu?.groups.flatMap((group) => group.items.map((item) => item.label)) ?? [],
    );
    expect(labels.filter((label) => /Local SEO|Map Rank Tracker|Local Heatmap/i.test(label))).toEqual([]);
  });

  it("retires duplicate provider-dependent review pages to their product hubs", () => {
    const destinations = new Map(ROUTE_RENAMES.redirects.map(({ from, to }) => [from, to]));
    expect(destinations.get("/seo/reviews")).toBe("/seo");
    expect(destinations.get("/studio/social-studio/reviews")).toBe("/studio/social-studio");
    expect(destinations.get("/reviews")).toBe("/studio/social-studio");
    expect(destinations.get("/studio/social-reviews")).toBe("/studio/social-studio");
    expect(ROUTES.has("/seo/reviews")).toBe(false);
    expect(ROUTES.has("/studio/social-studio/reviews")).toBe(false);
  });

  it("retires the unsupported SEO Performance Audit route to the SEO hub", () => {
    const destinations = new Map(ROUTE_RENAMES.redirects.map(({ from, to }) => [from, to]));
    expect(destinations.get("/seo/performance")).toBe("/seo");
    expect(ROUTES.has("/seo/performance")).toBe(false);
  });

  it("retires unsupported Ads Orchestration module routes", () => {
    const destinations = new Map(ROUTE_RENAMES.redirects.map(({ from, to }) => [from, to]));
    const moduleKeys = [
      "retail-media-app-growth-hub",
      "ai-creative-keyword-lab",
      "attribution-conversion-intelligence",
      "budget-pacing-bid-engine",
      "cross-network-campaign-orchestrator",
      "unified-ads-control-tower",
    ];
    for (const moduleKey of moduleKeys) {
      for (const from of [`/seo/${moduleKey}`, `/seo/modules/${moduleKey}`]) {
        expect(destinations.get(from)).toBe("/seo");
        expect(ROUTES.has(from)).toBe(false);
      }
    }
    for (const slug of [
      "ads-connectors",
      "ads-campaigns",
      "ads-calendar",
      "ads-metrics",
      "ads-kpis",
      "ads-smart-schedule",
    ]) {
      const from = `/seo/${slug}`;
      expect(destinations.get(from)).toBe("/seo");
      expect(ROUTES.has(from)).toBe(false);
    }
    expect(SEO_MODULE_CATALOG.some((entry) => moduleKeys.includes(entry.moduleKey ?? ""))).toBe(false);
    const labels = Object.values(MENUS).flatMap(
      (menu) => menu?.groups.flatMap((group) => group.items.map((item) => item.label)) ?? [],
    );
    expect(labels).not.toContain("Campaign Autopilot");
    expect(labels).not.toContain("Smart Scheduler");
    expect(labels).not.toContain("Ads Calendar");
  });

  it("never chains one redirect into another", () => {
    expect(ROUTE_RENAMES.redirects.filter((r) => SOURCES.has(r.to))).toEqual([]);
  });

  it("keeps vendor names out of customer routes and menu labels", () => {
    const VENDOR = /lately|buffer|owly|kodee|promptwatch|seo-ai-assist|one2target|contentshake|content\s?shake|eyeon|semrush|ahrefs|gtmetrix|ocoya|manychat/i;
    const visible = ROUTE_INDEX.filter((entry) => !entry.internal);
    expect(visible.filter((entry) => VENDOR.test(entry.route) || VENDOR.test(entry.title)).map((e) => e.route)).toEqual(
      [],
    );
    const labels = Object.values(MENUS).flatMap(
      (menu) => menu?.groups.flatMap((group) => group.items.map((item) => item.label)) ?? [],
    );
    expect(labels.filter((label) => VENDOR.test(label))).toEqual([]);
  });

  it("keeps competitor-parity placeholder tools out of the customer SEO catalog", () => {
    const customerCatalogEntries = SEO_MODULE_CATALOG.filter((entry) =>
      /ahrefs|semrush|eyeon|one2target|contentshake|gtmetrix|ocoya|manychat|\bparity\b/i.test(
        `${entry.title} ${entry.summary} ${entry.category} ${entry.moduleKey ?? ""}`,
      ),
    );
    expect(customerCatalogEntries).toEqual([]);
  });

  it("redirects retired Social Studio operations pages to canonical customer workflows", () => {
    const destinations = new Map(ROUTE_RENAMES.redirects.map(({ from, to }) => [from, to]));
    expect(destinations.get("/studio/social-studio/mobile")).toBe("/studio/social-studio");
    expect(destinations.get("/studio/social-studio/manychat")).toBe("/studio/social-studio/automation");
    expect(destinations.get("/studio/social-studio/listening")).toBe("/social-listening");
  });

  it("retires UGC rights management until creator consent and publishing are verifiable", () => {
    const destinations = new Map(ROUTE_RENAMES.redirects.map(({ from, to }) => [from, to]));
    expect(destinations.get("/studio/social-studio/ugc")).toBe("/studio/social-studio");
    expect(destinations.get("/studio/social-ugc")).toBe("/studio/social-studio");
    expect(ROUTES.has("/studio/social-studio/ugc")).toBe(false);
    const labels = Object.values(MENUS).flatMap(
      (menu) => menu?.groups.flatMap((group) => group.items.map((item) => item.label)) ?? [],
    );
    expect(labels).not.toContain("UGC Management");
  });

  it("routes legacy analytics URLs to the matching manual analytics or history tool", () => {
    const destinations = new Map(ROUTE_RENAMES.redirects.map(({ from, to }) => [from, to]));
    expect(destinations.get("/seo/gsc-insights")).toBe("/seo/history");
    expect(destinations.get("/seo/web-analytics")).toBe("/seo/analytics");
  });

  it("retires the unsupported Client Portal and report-builder surface", () => {
    const destinations = new Map(ROUTE_RENAMES.redirects.map(({ from, to }) => [from, to]));
    expect(destinations.get("/seo/client-portal")).toBe("/seo");
    expect(destinations.get("/seo/report-builder")).toBe("/seo");
    expect(ROUTES.has("/seo/client-portal")).toBe(false);
    expect(SEO_MODULE_CATALOG.some((entry) => entry.routePath === "/seo/client-portal")).toBe(false);
    const labels = Object.values(MENUS).flatMap(
      (menu) => menu?.groups.flatMap((group) => group.items.map((item) => item.label)) ?? [],
    );
    expect(labels).not.toContain("Auto Reports");
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
