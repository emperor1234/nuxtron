import { describe, expect, it } from "vitest";
import { AI_CRAWLER_TARGETS, checkCrawler, parseRobotsTxt } from "./robots";

function target(id: string) {
  const found = AI_CRAWLER_TARGETS.find((item) => item.id === id);
  if (!found) throw new Error(`Unknown crawler target: ${id}`);
  return found;
}

describe("robots.txt checker", () => {
  it("parses grouped agents, directives, comments, and sitemap records", () => {
    const document = parseRobotsTxt(
      `Sitemap: https://example.com/sitemap.xml\n\nUser-agent: GPTBot # training\nUser-agent: OAI-SearchBot\nDisallow: /private/\nAllow: /private/public/`,
    );
    expect(document.sitemaps).toEqual(["https://example.com/sitemap.xml"]);
    expect(document.groups).toEqual([
      {
        agents: ["gptbot", "oai-searchbot"],
        rules: [
          { type: "disallow", path: "/private/" },
          { type: "allow", path: "/private/public/" },
        ],
      },
    ]);
  });

  it("uses exact agent groups instead of combining them with the wildcard group", () => {
    const document = parseRobotsTxt(
      `User-agent: *\nDisallow: /\nUser-agent: GPTBot\nAllow: /about\nDisallow: /`,
    );
    const result = checkCrawler(document, target("gptbot"));
    expect(result.source).toBe("specific");
    expect(
      result.pathChecks.find((item) => item.path === "/about")?.allowed,
    ).toBe(true);
    expect(result.pathChecks.find((item) => item.path === "/")?.allowed).toBe(
      false,
    );
  });

  it("falls back to wildcard rules for a crawler without an exact group", () => {
    const document = parseRobotsTxt("User-agent: *\nDisallow: /private/");
    const result = checkCrawler(document, target("perplexitybot"));
    expect(result.source).toBe("wildcard");
    expect(
      result.pathChecks.find((item) => item.path === "/private/report")
        ?.allowed,
    ).toBe(false);
    expect(
      result.pathChecks.find((item) => item.path === "/about")?.allowed,
    ).toBe(true);
  });

  it("defaults to allow when no specific or wildcard group matches", () => {
    const result = checkCrawler(
      parseRobotsTxt("User-agent: OtherBot\nDisallow: /"),
      target("claudebot"),
    );
    expect(result.source).toBe("none");
    expect(result.blockedCount).toBe(0);
    expect(result.headline).toContain("default allow");
  });

  it("reports Google-Extended as its own product token, not an inferred HTTP crawler", () => {
    const result = checkCrawler(
      parseRobotsTxt("User-agent: Google-Extended\nDisallow: /training/"),
      target("google-extended"),
    );
    expect(result.source).toBe("specific");
    expect(result.target.note).toContain("not a separate HTTP crawler");
  });
});
