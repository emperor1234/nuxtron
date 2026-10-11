import { describe, expect, it } from "vitest";
import { MENUS } from "@/app/(dashboard)/_shell/nav";
import { FEATURE_JOBS, FEATURE_TOOLS, filterTools } from "./features";

describe("feature directory", () => {
  it("has unique tool ids", () => {
    const ids = FEATURE_TOOLS.map((tool) => tool.id);
    expect(new Set(ids).size).toBe(ids.length);
  });

  it("puts every tool in a known job", () => {
    const jobs = new Set(FEATURE_JOBS.map((job) => job.id));
    expect(FEATURE_TOOLS.every((tool) => jobs.has(tool.job))).toBe(true);
  });

  it("product filter keeps tools shared by both products", () => {
    const seo = filterTools(FEATURE_TOOLS, "seo", "");
    expect(seo.some((tool) => tool.product === "marketing")).toBe(false);
    expect(seo.some((tool) => tool.product === "both")).toBe(true);
  });

  it("search matches name and description, case-insensitively", () => {
    expect(filterTools(FEATURE_TOOLS, "all", "INBOX").map((t) => t.id)).toContain("smart-inbox");
    expect(filterTools(FEATURE_TOOLS, "all", "crawl").map((t) => t.id)).toContain("site-audit");
  });

  it("returns nothing for a query that matches nothing", () => {
    expect(filterTools(FEATURE_TOOLS, "all", "zzzz-no-such-tool")).toEqual([]);
  });

  it("only lists tools that exist in the dashboard menus", () => {
    const labels = new Set(
      Object.values(MENUS).flatMap((menu) => menu?.groups.flatMap((group) => group.items.map((item) => item.label)) ?? []),
    );
    const missing = FEATURE_TOOLS.filter((tool) => !labels.has(tool.name)).map((tool) => tool.name);
    expect(missing).toEqual([]);
  });
});
