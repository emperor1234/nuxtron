import { describe, expect, it } from "vitest";
import type { BlogPost } from "../../blog/posts";
import { selectResearchPosts } from "./research-grid-section";

function post(slug: string, category: string, date: string): BlogPost {
  return { slug, title: slug, description: "", date, author: "", readMinutes: 1, category, paragraphs: [] };
}

const POSTS = [
  post("old-seo", "SEO", "2026-01-01"),
  post("new-company", "Company", "2026-06-01"),
  post("mid-ops", "Ops", "2026-03-01"),
  post("newest-seo", "SEO", "2026-07-01"),
];

describe("selectResearchPosts", () => {
  it("returns the newest posts when no categories are given", () => {
    expect(selectResearchPosts(POSTS, undefined, 2).map((p) => p.slug)).toEqual(["newest-seo", "new-company"]);
  });

  it("puts matching posts first, newest first", () => {
    expect(selectResearchPosts(POSTS, ["SEO"], 2).map((p) => p.slug)).toEqual(["newest-seo", "old-seo"]);
  });

  it("fills the grid with other posts when too few match", () => {
    expect(selectResearchPosts(POSTS, ["SEO"], 4).map((p) => p.slug)).toEqual([
      "newest-seo",
      "old-seo",
      "new-company",
      "mid-ops",
    ]);
  });

  it("falls back to the newest posts when nothing matches", () => {
    expect(selectResearchPosts(POSTS, ["Missing"], 1).map((p) => p.slug)).toEqual(["newest-seo"]);
  });

  it("never returns more posts than exist", () => {
    expect(selectResearchPosts(POSTS, ["SEO"], 10)).toHaveLength(4);
  });
});
