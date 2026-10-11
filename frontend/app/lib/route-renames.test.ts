import { describe, expect, it } from "vitest";
import { MENUS } from "@/app/(dashboard)/_shell/nav";
import { ROUTE_INDEX } from "@/app/(dashboard)/_shell/route-index.generated";
import ROUTE_RENAMES from "./route-renames.json";

const ROUTES = new Set(ROUTE_INDEX.map((entry) => entry.route));
const SOURCES = new Set(ROUTE_RENAMES.redirects.map((r) => r.from));

describe("renamed dashboard routes", () => {
  it("redirects every old URL to a page that exists", () => {
    const missing = ROUTE_RENAMES.redirects.filter((r) => !ROUTES.has(r.to));
    expect(missing).toEqual([]);
  });

  it("leaves no page behind at an old URL", () => {
    // next.config redirects run before the filesystem, so a page left at the
    // old path would be unreachable dead code.
    expect([...SOURCES].filter((from) => ROUTES.has(from))).toEqual([]);
  });

  it("never chains one redirect into another", () => {
    expect(ROUTE_RENAMES.redirects.filter((r) => SOURCES.has(r.to))).toEqual([]);
  });

  it("keeps vendor names out of customer routes and menu labels", () => {
    const VENDOR = /lately|buffer|owly|kodee|promptwatch|seo-ai-assist|one2target/i;
    const visible = ROUTE_INDEX.filter((entry) => !entry.internal);
    expect(visible.filter((entry) => VENDOR.test(entry.route) || VENDOR.test(entry.title)).map((e) => e.route)).toEqual(
      [],
    );
    const labels = Object.values(MENUS).flatMap(
      (menu) => menu?.groups.flatMap((group) => group.items.map((item) => item.label)) ?? [],
    );
    expect(labels.filter((label) => VENDOR.test(label))).toEqual([]);
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
