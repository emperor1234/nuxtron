import { describe, expect, it } from "vitest";
import { MENUS, RAIL_ITEMS, SETTINGS_ITEM } from "@/app/(dashboard)/_shell/nav";
import { ROUTE_INDEX } from "@/app/(dashboard)/_shell/route-index.generated";
import INTERNAL_CONSOLES from "./internal-consoles.json";

const NAV_HREFS = new Set<string>([
  ...[...RAIL_ITEMS, SETTINGS_ITEM].map((item) => item.href as string),
  ...Object.values(MENUS).flatMap(
    (menu) => menu?.groups.flatMap((group) => group.items.map((item) => item.href as string)) ?? [],
  ),
]);

describe("internal vendor consoles", () => {
  it("lists only pages that exist", () => {
    const routes = new Set(ROUTE_INDEX.map((entry) => entry.route));
    expect(INTERNAL_CONSOLES.paths.filter((path) => !routes.has(path))).toEqual([]);
  });

  it("never gates a page the customer navigation links to", () => {
    expect(INTERNAL_CONSOLES.paths.filter((path) => NAV_HREFS.has(path))).toEqual([]);
  });

  it("keeps every console out of customer search", () => {
    const visible = ROUTE_INDEX.filter((entry) => INTERNAL_CONSOLES.paths.includes(entry.route) && !entry.internal);
    expect(visible.map((entry) => entry.route)).toEqual([]);
  });

  it("has no duplicates", () => {
    expect(new Set(INTERNAL_CONSOLES.paths).size).toBe(INTERNAL_CONSOLES.paths.length);
  });
});
