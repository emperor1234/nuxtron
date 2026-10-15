import { describe, expect, it } from "vitest";
import { MENUS } from "@/app/(dashboard)/_shell/nav";
import { FEATURE_JOBS, FEATURE_TOOLS, filterTools } from "./features";
import { marketingHomepage } from "./marketing";
import { seoHomepage } from "./seo";

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
    expect(filterTools(FEATURE_TOOLS, "all", "crawl").map((t) => t.id)).toContain("log-file-analyzer");
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

  it("does not market unsupported automated report delivery", () => {
    const publicCopy = JSON.stringify({ tools: FEATURE_TOOLS, homepage: seoHomepage }).toLowerCase();
    expect(publicCopy).not.toContain("auto reports");
    expect(publicCopy).not.toContain("client-portal");
    expect(publicCopy).not.toContain("send the numbers on a schedule");
  });

  it("describes keyword tooling as local review of user-provided exports", () => {
    const keywordTool = FEATURE_TOOLS.find((tool) => tool.id === "organic-research");
    expect(keywordTool).toMatchObject({ name: "Keyword Data Review" });
    expect(keywordTool?.description).toMatch(/CSV export you provide, locally in your browser/i);
    const publicCopy = JSON.stringify({ jobs: FEATURE_JOBS, tools: FEATURE_TOOLS, homepage: seoHomepage }).toLowerCase();
    expect(publicCopy).not.toContain("organic research");
    expect(publicCopy).not.toContain("keyword gap");
  });

  it("describes rank and performance tracking as supplied review, not live measurement", () => {
    const trackingSummary = FEATURE_JOBS.find((job) => job.id === "track")?.summary ?? "";
    expect(trackingSummary).toMatch(/review rank exports/i);
    expect(trackingSummary).toMatch(/monitoring are unavailable/i);
    expect(trackingSummary).not.toMatch(/measured over time/i);
  });

  it("does not market unconnected provider-backed review management", () => {
    const publicCopy = JSON.stringify({ jobs: FEATURE_JOBS, tools: FEATURE_TOOLS, homepage: seoHomepage }).toLowerCase();
    expect(publicCopy).not.toContain("review management");
    expect(publicCopy).not.toContain("review feeds");
    expect(FEATURE_TOOLS.some((tool) => tool.id === "review-management")).toBe(false);
  });

  it("does not market UGC rights or republishing before creator consent is verifiable", () => {
    const publicCopy = JSON.stringify({ tools: FEATURE_TOOLS, homepage: marketingHomepage }).toLowerCase();
    expect(publicCopy).not.toContain("ugc management");
    expect(FEATURE_TOOLS.some((tool) => tool.id === "ugc-management")).toBe(false);
  });

  it("keeps public product tours free of fabricated customer metrics and competitor examples", () => {
    const demos = JSON.stringify([seoHomepage.demo, marketingHomepage.demo]).toLowerCase();
    for (const example of ["gusto", "rippling", "customer.com", "1,240", "38.2k", "3,918", "4.2%", "24 scheduled"]) {
      expect(demos).not.toContain(example);
    }
    expect(demos).toContain("sample-free");
  });
});
