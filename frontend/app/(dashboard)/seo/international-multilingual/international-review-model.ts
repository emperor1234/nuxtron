export type HreflangSeverity = "error" | "warning" | "note";
export type HreflangEntryStatus = "valid" | "duplicate" | "unexpected" | "invalid";

export type HreflangFinding = {
  code: string;
  severity: HreflangSeverity;
  title: string;
  detail: string;
};

export type HreflangEntry = {
  index: number;
  rawLocale: string;
  locale: string | null;
  hrefPreview: string;
  href: string | null;
  status: HreflangEntryStatus;
  details: string[];
};

export type HreflangReviewInput = {
  currentPageLocale: string;
  expectedLocales: string;
  canonicalUrl: string;
  markup: string;
};

export type HreflangReview = {
  entries: HreflangEntry[];
  findings: HreflangFinding[];
  expectedLocales: string[];
  missingLocales: string[];
  duplicateLocales: string[];
  currentPageLocale: string | null;
  canonicalUrlStatus: "not-provided" | "valid" | "invalid";
  canonicalUrl: string | null;
  alternateTagsFound: number;
  invalidEntryCount: number;
};

function normalizeLocale(value: string): string | null {
  const trimmed = value.trim();
  if (!trimmed) return null;
  if (trimmed.toLowerCase() === "x-default") return "x-default";
  try {
    return Intl.getCanonicalLocales(trimmed)[0] ?? null;
  } catch {
    return null;
  }
}

function attributeValue(tag: string, name: string): string | null {
  const match = tag.match(
    new RegExp(`(?:^|\\s)${name}\\s*=\\s*(?:"([^"]*)"|'([^']*)'|([^\\s>]+))`, "i"),
  );
  if (!match) return null;
  return (match[1] ?? match[2] ?? match[3] ?? "").trim();
}

function parseAbsoluteHttpUrl(value: string): string | null {
  try {
    const url = new URL(value.trim());
    if ((url.protocol !== "http:" && url.protocol !== "https:") || url.username || url.password) {
      return null;
    }
    return url.href;
  } catch {
    return null;
  }
}

function preview(value: string): string {
  const trimmed = value.trim();
  return trimmed.length > 180 ? `${trimmed.slice(0, 177)}…` : trimmed;
}

function safeHrefPreview(rawHref: string, href: string | null): string {
  if (href) {
    const url = new URL(href);
    return preview(
      `${url.origin}${url.pathname}${url.search ? '?[query omitted]' : ''}${url.hash ? '#[fragment omitted]' : ''}`,
    );
  }

  const withoutCredentials = rawHref.trim().replace(/(https?:\/\/)[^/\s@]+@/i, '$1[credentials omitted]@');
  const detailsStart = withoutCredentials.search(/[?#]/);
  const safeValue = detailsStart < 0
    ? withoutCredentials
    : `${withoutCredentials.slice(0, detailsStart)}${withoutCredentials[detailsStart]}[details omitted]`;
  return preview(safeValue || 'Not provided');
}

export function reviewHreflangMarkup(input: HreflangReviewInput): HreflangReview {
  const findings: HreflangFinding[] = [];
  const addFinding = (
    code: string,
    severity: HreflangSeverity,
    title: string,
    detail: string,
  ) => findings.push({ code, severity, title, detail });

  const expectedLocales: string[] = [];
  const expectedSeen = new Set<string>();
  for (const [index, raw] of input.expectedLocales.split(/[\n,]/).entries()) {
    const value = raw.trim();
    if (!value) continue;
    const locale = normalizeLocale(value);
    if (!locale) {
      addFinding(
        `invalid-expected-locale-${index + 1}`,
        "error",
        "Expected locale is not recognized",
        `“${preview(value)}” is not a valid language tag. Check its BCP 47 spelling.`,
      );
      continue;
    }
    if (expectedSeen.has(locale)) {
      addFinding(
        `duplicate-expected-locale-${locale}`,
        "warning",
        "Expected locale is listed more than once",
        `“${locale}” appears multiple times in the expected locale list.`,
      );
      continue;
    }
    expectedSeen.add(locale);
    expectedLocales.push(locale);
  }

  const currentPageLocaleInput = input.currentPageLocale.trim();
  const currentPageLocale = currentPageLocaleInput
    ? normalizeLocale(currentPageLocaleInput)
    : null;
  if (currentPageLocaleInput && !currentPageLocale) {
    addFinding(
      "invalid-current-page-locale",
      "error",
      "Current page locale is not recognized",
      `“${preview(currentPageLocaleInput)}” is not a valid language tag.`,
    );
  }

  const canonicalInput = input.canonicalUrl.trim();
  const canonicalUrl = canonicalInput ? parseAbsoluteHttpUrl(canonicalInput) : null;
  const canonicalUrlStatus = !canonicalInput
    ? "not-provided"
    : canonicalUrl
      ? "valid"
      : "invalid";
  if (canonicalInput && !canonicalUrl) {
    addFinding(
      "invalid-canonical-url",
      "error",
      "Canonical URL is not a valid absolute HTTP(S) URL",
      "Only the URL syntax is checked here; this tool does not request the page or compare its canonical element.",
    );
  } else if (canonicalUrl) {
    addFinding(
      "canonical-url-format-only",
      "note",
      "Canonical URL format looks valid",
      "The page is not fetched, so canonical target content or alignment cannot be confirmed.",
    );
  }

  const linkTags = Array.from(input.markup.matchAll(/<link\b[^>]*>/gi), (match) => match[0]);
  const alternateTags = linkTags.filter((tag) =>
    (attributeValue(tag, "rel") ?? "").toLowerCase().split(/\s+/).includes("alternate"),
  );
  if (alternateTags.length === 0) {
    addFinding(
      "no-alternate-links-found",
      "warning",
      "No alternate link tags found in the supplied text",
      "This result describes only the text pasted above; it does not mean the live page has no hreflang tags.",
    );
  }

  const entries: HreflangEntry[] = alternateTags.map((tag, index) => {
    const rawLocale = attributeValue(tag, "hreflang") ?? "";
    const rawHref = attributeValue(tag, "href") ?? "";
    const locale = normalizeLocale(rawLocale);
    const href = rawHref ? parseAbsoluteHttpUrl(rawHref) : null;
    const details: string[] = [];
    let invalid = false;

    if (!rawLocale) {
      details.push("Missing hreflang attribute.");
      invalid = true;
    } else if (!locale) {
      details.push("The hreflang value is not a recognized language tag.");
      invalid = true;
    }
    if (!rawHref) {
      details.push("Missing href attribute.");
      invalid = true;
    } else if (!href) {
      details.push("The href must be an absolute HTTP or HTTPS URL without embedded credentials.");
      invalid = true;
    }

    return {
      index: index + 1,
      rawLocale: preview(rawLocale || "Not provided"),
      locale,
      hrefPreview: safeHrefPreview(rawHref, href),
      href,
      status: invalid ? "invalid" : "valid",
      details,
    };
  });

  for (const entry of entries) {
    if (entry.status === "invalid") {
      addFinding(
        `invalid-alternate-${entry.index}`,
        "error",
        `Alternate link ${entry.index} needs correction`,
        entry.details.join(" "),
      );
    }
  }

  const localeCounts = new Map<string, number>();
  for (const entry of entries) {
    if (entry.status === "invalid" || !entry.locale) continue;
    localeCounts.set(entry.locale, (localeCounts.get(entry.locale) ?? 0) + 1);
  }
  const duplicateLocales = [...localeCounts]
    .filter(([, count]) => count > 1)
    .map(([locale]) => locale);
  for (const locale of duplicateLocales) {
    addFinding(
      `duplicate-hreflang-${locale}`,
      "error",
      `More than one alternate is declared for ${locale}`,
      "Review the target URLs and keep one intentional alternate for this language or language-region tag.",
    );
  }
  for (const entry of entries) {
    if (entry.locale && duplicateLocales.includes(entry.locale) && entry.status !== "invalid") {
      entry.status = "duplicate";
      entry.details.push("This locale appears in more than one supplied alternate link.");
    }
  }

  const missingLocales = expectedLocales.filter((locale) => !localeCounts.has(locale));
  for (const locale of missingLocales) {
    addFinding(
      `missing-expected-locale-${locale}`,
      "warning",
      `No supplied alternate matches ${locale}`,
      "Check whether a corresponding localized page exists and whether its alternate link belongs in this page's markup.",
    );
  }

  if (expectedLocales.length > 0) {
    for (const entry of entries) {
      if (
        entry.locale &&
        entry.status === "valid" &&
        !expectedSeen.has(entry.locale)
      ) {
        entry.status = "unexpected";
        entry.details.push("This locale was not included in the expected-locale list you supplied.");
      }
    }
  }

  if (currentPageLocale && !localeCounts.has(currentPageLocale)) {
    addFinding(
      "current-page-locale-not-listed",
      "warning",
      `No supplied alternate matches the current page locale ${currentPageLocale}`,
      "Confirm whether the current page should be included in the alternate set. This check uses only the locale and markup you entered.",
    );
  }

  return {
    entries,
    findings,
    expectedLocales,
    missingLocales,
    duplicateLocales,
    currentPageLocale,
    canonicalUrlStatus,
    canonicalUrl,
    alternateTagsFound: alternateTags.length,
    invalidEntryCount: entries.filter((entry) => entry.status === "invalid").length,
  };
}
