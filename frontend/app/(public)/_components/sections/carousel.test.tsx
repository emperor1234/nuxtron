import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import type { AgentContent, ProofContent, ProofEntry, TrustBadge, TrustContent } from "../../_content/types";
import { AgentCarouselSection } from "./agent-carousel-section";
import { Carousel } from "./carousel";
import { ProofCarouselSection, verifiedProofEntries } from "./proof-carousel-section";
import { TrustBadgesSection, verifiedTrustBadges } from "./trust-badges-section";

/** Test fixtures only — never rendered on a real page. */
const verifiedEntry: ProofEntry = {
  id: "fixture-1",
  quote: "Fixture quote",
  person: "Fixture Person",
  role: "Fixture Role",
  company: "Fixture Co",
  metric: { value: "1x", label: "fixture metric" },
  verified: true,
  source: "https://example.com/story",
};

const unverifiedEntry = { ...verifiedEntry, id: "fixture-2", verified: false } as unknown as ProofEntry;
const sourcelessEntry: ProofEntry = { ...verifiedEntry, id: "fixture-3", source: "  " };

const verifiedBadge: TrustBadge = {
  id: "badge-1",
  name: "Fixture Award",
  issuer: "Fixture Issuer",
  season: "Fall 2026",
  url: "https://example.com/award",
  verified: true,
};

describe("Carousel", () => {
  it("exposes the carousel and slide ARIA pattern", () => {
    const html = renderToStaticMarkup(
      <Carousel label="Fixture slides">
        <p>One</p>
        <p>Two</p>
        <p>Three</p>
      </Carousel>,
    );
    expect(html).toContain('role="region"');
    expect(html).toContain('aria-roledescription="carousel"');
    expect(html).toContain('aria-label="Fixture slides"');
    expect(html).toContain('aria-roledescription="slide"');
    expect(html).toContain('aria-label="2 of 3"');
    expect(html).toContain('aria-label="Previous slide"');
    expect(html).toContain('aria-label="Next slide"');
  });

  it("starts with the previous button disabled", () => {
    const html = renderToStaticMarkup(
      <Carousel label="Fixture slides">
        <p>One</p>
        <p>Two</p>
      </Carousel>,
    );
    expect(html).toMatch(/<button[^>]*disabled=""[^>]*aria-label="Previous slide"|<button[^>]*aria-label="Previous slide"[^>]*disabled=""/);
  });

  it("omits controls for a single slide", () => {
    const html = renderToStaticMarkup(
      <Carousel label="Fixture slides">
        <p>Only</p>
      </Carousel>,
    );
    expect(html).not.toContain("Next slide");
  });
});

describe("ProofCarouselSection", () => {
  const content = (entries: readonly ProofEntry[]): ProofContent => ({
    eyebrow: "Proof",
    title: "Fixture proof",
    entries,
  });

  it("renders nothing without verified entries", () => {
    expect(renderToStaticMarkup(<ProofCarouselSection content={content([])} />)).toBe("");
    expect(
      renderToStaticMarkup(
        <ProofCarouselSection content={content([unverifiedEntry, sourcelessEntry])} />,
      ),
    ).toBe("");
  });

  it("keeps only verified entries with a source", () => {
    expect(verifiedProofEntries([verifiedEntry, unverifiedEntry, sourcelessEntry])).toEqual([
      verifiedEntry,
    ]);
  });

  it("renders the quote, attribution and source link", () => {
    const html = renderToStaticMarkup(<ProofCarouselSection content={content([verifiedEntry])} />);
    expect(html).toContain("Fixture quote");
    expect(html).toContain("Fixture Person · Fixture Role · Fixture Co");
    expect(html).toContain('href="https://example.com/story"');
    expect(html).toContain('aria-labelledby="home-proof-title"');
  });
});

describe("TrustBadgesSection", () => {
  const content = (badges: readonly TrustBadge[]): TrustContent => ({ title: "Fixture trust", badges });

  it("drops unverified and non-https badges", () => {
    const insecure: TrustBadge = { ...verifiedBadge, id: "badge-2", url: "http://example.com" };
    const scripted: TrustBadge = { ...verifiedBadge, id: "badge-3", url: "javascript:alert(1)" };
    const unverified = { ...verifiedBadge, id: "badge-4", verified: false } as unknown as TrustBadge;
    expect(verifiedTrustBadges([verifiedBadge, insecure, scripted, unverified])).toEqual([verifiedBadge]);
  });

  it("renders nothing without verified badges", () => {
    expect(renderToStaticMarkup(<TrustBadgesSection content={content([])} />)).toBe("");
  });

  it("renders text tiles linking to the award page", () => {
    const html = renderToStaticMarkup(<TrustBadgesSection content={content([verifiedBadge])} />);
    expect(html).toContain("Fixture Award");
    expect(html).toContain('href="https://example.com/award"');
    expect(html).not.toContain("<img");
  });
});

describe("AgentCarouselSection", () => {
  it("renders each agent with its actions and link", () => {
    const content: AgentContent = {
      eyebrow: "Agents",
      title: "Fixture agents",
      intro: "Fixture intro",
      agents: [
        {
          id: "agent-1",
          name: "Fixture Agent",
          role: "Fixture role",
          body: "Fixture body",
          actions: ["Does one thing"],
          link: { label: "Open", href: "/features" },
        },
      ],
    };
    const html = renderToStaticMarkup(<AgentCarouselSection content={content} />);
    expect(html).toContain("Fixture Agent");
    expect(html).toContain("Does one thing");
    expect(html).toContain('href="/features"');
    expect(html).toContain('aria-labelledby="home-agents-title"');
  });
});
