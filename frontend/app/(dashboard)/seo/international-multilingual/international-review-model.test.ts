import { describe, expect, it } from "vitest";

import { reviewHreflangMarkup } from "./international-review-model";

const links = [
  '<link rel="alternate" hreflang="en-US" href="https://example.com/en/">',
  '<link rel="alternate" hreflang="fr-FR" href="https://example.com/fr/">',
].join("\n");

const emptyFields = {
  currentPageLocale: "",
  expectedLocales: "",
  canonicalUrl: "",
};

describe("reviewHreflangMarkup", () => {
  it("normalizes language tags and confirms only the supplied locale coverage", () => {
    const result = reviewHreflangMarkup({
      ...emptyFields,
      currentPageLocale: "en-us",
      expectedLocales: "en-US\nfr-fr",
      canonicalUrl: "https://example.com/en/",
      markup: links,
    });

    expect(result.entries.map((entry) => [entry.locale, entry.href, entry.status])).toEqual([
      ["en-US", "https://example.com/en/", "valid"],
      ["fr-FR", "https://example.com/fr/", "valid"],
    ]);
    expect(result.missingLocales).toEqual([]);
    expect(result.currentPageLocale).toBe("en-US");
    expect(result.canonicalUrlStatus).toBe("valid");
    expect(result.findings.map((finding) => finding.code)).toContain("canonical-url-format-only");
  });

  it("reports duplicate targets and expected locales absent from the pasted markup", () => {
    const result = reviewHreflangMarkup({
      ...emptyFields,
      expectedLocales: "en, fr, de",
      markup: [
        '<link rel="alternate" hreflang="en" href="https://example.com/en/">',
        '<link rel="alternate" hreflang="en" href="https://example.com/english/">',
        '<link rel="alternate" hreflang="es" href="https://example.com/es/">',
      ].join("\n"),
    });

    expect(result.duplicateLocales).toEqual(["en"]);
    expect(result.missingLocales).toEqual(["fr", "de"]);
    expect(result.entries.map((entry) => entry.status)).toEqual([
      "duplicate",
      "duplicate",
      "unexpected",
    ]);
    expect(result.findings.map((finding) => finding.code)).toContain("duplicate-hreflang-en");
  });

  it("hides target query strings and fragments from the displayed preview", () => {
    const result = reviewHreflangMarkup({
      ...emptyFields,
      markup: '<link rel="alternate" hreflang="en" href="https://example.com/en/?access_token=secret#session">',
    });

    expect(result.entries[0]?.hrefPreview).toBe('https://example.com/en/?[query omitted]#[fragment omitted]');
    expect(result.entries[0]?.hrefPreview).not.toContain('secret');
  });

  it("rejects malformed locale values, relative or unsafe URLs, and missing attributes", () => {
    const result = reviewHreflangMarkup({
      ...emptyFields,
      markup: [
        '<link rel="alternate" hreflang="en_US" href="https://example.com/en/">',
        '<link rel="alternate" hreflang="fr" href="/fr/">',
        '<link rel="alternate" hreflang="de" href="javascript:alert(1)">',
        '<link rel="alternate" hreflang="es">',
      ].join("\n"),
    });

    expect(result.invalidEntryCount).toBe(4);
    expect(result.entries.every((entry) => entry.status === "invalid")).toBe(true);
    expect(result.entries.map((entry) => entry.href)).toEqual([
      "https://example.com/en/",
      null,
      null,
      null,
    ]);
    expect(result.findings.filter((finding) => finding.severity === "error")).toHaveLength(4);
  });

  it("does not mistake canonical or stylesheet links for hreflang alternates", () => {
    const result = reviewHreflangMarkup({
      ...emptyFields,
      markup: [
        '<link rel="canonical" href="https://example.com/">',
        '<link rel="stylesheet" href="https://example.com/site.css">',
      ].join("\n"),
    });

    expect(result.entries).toEqual([]);
    expect(result.alternateTagsFound).toBe(0);
    expect(result.findings[0]?.code).toBe("no-alternate-links-found");
  });

  it("accepts x-default as a special hreflang value but does not require it", () => {
    const result = reviewHreflangMarkup({
      ...emptyFields,
      markup: '<link rel="alternate" hreflang="x-default" href="https://example.com/">',
    });

    expect(result.entries[0]).toMatchObject({ locale: "x-default", status: "valid" });
    expect(result.findings).toEqual([]);
  });

  it("reports invalid supplied locale lists and canonical syntax without claiming page verification", () => {
    const result = reviewHreflangMarkup({
      currentPageLocale: "english_US",
      expectedLocales: "en, not_a_locale, en",
      canonicalUrl: "javascript:alert(1)",
      markup: links,
    });

    expect(result.currentPageLocale).toBeNull();
    expect(result.canonicalUrlStatus).toBe("invalid");
    expect(result.findings.map((finding) => finding.code)).toEqual(
      expect.arrayContaining([
        "invalid-current-page-locale",
        "invalid-expected-locale-2",
        "duplicate-expected-locale-en",
        "invalid-canonical-url",
      ]),
    );
  });
});
