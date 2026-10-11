export type RobotsRule = {
  type: "allow" | "disallow";
  path: string;
};

export type RobotsGroup = {
  agents: string[];
  rules: RobotsRule[];
};

export type RobotsDocument = {
  groups: RobotsGroup[];
  sitemaps: string[];
};

export type AiCrawlerTarget = {
  id: string;
  name: string;
  product: string;
  token: string;
  purpose: string;
  note?: string;
};

export const AI_CRAWLER_TARGETS: readonly AiCrawlerTarget[] = [
  {
    id: "google-extended",
    name: "Google-Extended",
    product: "Google",
    token: "Google-Extended",
    purpose: "Controls eligible uses of crawled content for some AI products.",
    note: "A robots.txt control token, not a separate HTTP crawler. It does not control Google Search indexing.",
  },
  {
    id: "googlebot",
    name: "Googlebot",
    product: "Google",
    token: "Googlebot",
    purpose: "Google Search crawling and indexing.",
    note: "Shown as a search-crawl reference; it is distinct from Google's AI content-use token.",
  },
  {
    id: "oai-searchbot",
    name: "OAI-SearchBot",
    product: "OpenAI",
    token: "OAI-SearchBot",
    purpose: "Automatic discovery for ChatGPT search results.",
  },
  {
    id: "gptbot",
    name: "GPTBot",
    product: "OpenAI",
    token: "GPTBot",
    purpose: "Automatic crawling for potential model training use.",
  },
  {
    id: "chatgpt-user",
    name: "ChatGPT-User",
    product: "OpenAI",
    token: "ChatGPT-User",
    purpose: "User-directed page fetching, not automatic web crawling.",
    note: "OpenAI notes that user-triggered requests may not be governed by robots.txt in the same way as automatic crawling.",
  },
  {
    id: "claude-searchbot",
    name: "Claude-SearchBot",
    product: "Anthropic",
    token: "Claude-SearchBot",
    purpose: "Search-related crawling.",
  },
  {
    id: "claudebot",
    name: "ClaudeBot",
    product: "Anthropic",
    token: "ClaudeBot",
    purpose: "Crawling that may contribute to model training.",
  },
  {
    id: "claude-user",
    name: "Claude-User",
    product: "Anthropic",
    token: "Claude-User",
    purpose: "Page retrieval initiated by a Claude user.",
  },
  {
    id: "perplexitybot",
    name: "PerplexityBot",
    product: "Perplexity",
    token: "PerplexityBot",
    purpose: "Automatic search-result discovery and indexing.",
  },
  {
    id: "perplexity-user",
    name: "Perplexity-User",
    product: "Perplexity",
    token: "Perplexity-User",
    purpose: "User-directed page fetching rather than automatic crawling.",
    note: "Perplexity says this user-requested fetcher generally ignores robots.txt rules.",
  },
];

export const SAMPLE_PATHS = [
  "/",
  "/about",
  "/blog/article",
  "/products",
  "/private/report",
] as const;

export type PathCheck = {
  path: string;
  allowed: boolean;
  matchedRule: RobotsRule | null;
};

export type CrawlerCheck = {
  target: AiCrawlerTarget;
  source: "specific" | "wildcard" | "none";
  headline: string;
  blockedCount: number;
  pathChecks: PathCheck[];
};

export function parseRobotsTxt(source: string): RobotsDocument {
  const groups: RobotsGroup[] = [];
  const sitemaps: string[] = [];
  let agents: string[] = [];
  let rules: RobotsRule[] = [];
  let hasRuleLine = false;

  const flushGroup = () => {
    if (agents.length > 0) {
      groups.push({ agents, rules });
    }
    agents = [];
    rules = [];
    hasRuleLine = false;
  };

  for (const rawLine of source.slice(0, 500_000).split(/\r\n|\n|\r/)) {
    const line = rawLine.replace(/#.*$/, "").trim();
    if (!line) continue;

    const separator = line.indexOf(":");
    if (separator < 0) continue;
    const field = line.slice(0, separator).trim().toLowerCase();
    const value = line.slice(separator + 1).trim();

    if (field === "user-agent") {
      if (hasRuleLine) flushGroup();
      if (value) agents.push(value.toLowerCase());
      continue;
    }

    if (field === "allow" || field === "disallow") {
      if (agents.length > 0) {
        hasRuleLine = true;
        if (value.startsWith("/")) {
          rules.push({ type: field, path: value });
        }
      }
      continue;
    }

    if (field === "sitemap" && value) {
      sitemaps.push(value);
    }
  }

  flushGroup();
  return { groups, sitemaps };
}

function patternMatches(pattern: string, path: string): boolean {
  const isEndAnchored = pattern.endsWith("$");
  const body = isEndAnchored ? pattern.slice(0, -1) : pattern;
  const escaped = body
    .replace(/[|\\{}()[\]^$+?.]/g, "\\$&")
    .replace(/\*/g, ".*");
  const expression = new RegExp(`^${escaped}${isEndAnchored ? "$" : ""}`);
  return expression.test(path);
}

function ruleForPath(
  rules: readonly RobotsRule[],
  path: string,
): RobotsRule | null {
  if (path === "/robots.txt") return { type: "allow", path: "/robots.txt" };
  const matching = rules
    .filter((rule) => patternMatches(rule.path, path))
    .sort(
      (a, b) =>
        b.path.length - a.path.length ||
        Number(b.type === "allow") - Number(a.type === "allow"),
    );
  return matching[0] ?? null;
}

export function checkCrawler(
  document: RobotsDocument,
  target: AiCrawlerTarget,
): CrawlerCheck {
  const exactGroups = document.groups.filter((group) =>
    group.agents.includes(target.token.toLowerCase()),
  );
  const wildcardGroups = document.groups.filter((group) =>
    group.agents.includes("*"),
  );
  const source =
    exactGroups.length > 0
      ? "specific"
      : wildcardGroups.length > 0
        ? "wildcard"
        : "none";
  const applicableGroups =
    exactGroups.length > 0 ? exactGroups : wildcardGroups;
  const rules = applicableGroups.flatMap((group) => group.rules);
  const pathChecks = SAMPLE_PATHS.map((path) => {
    const matchedRule = ruleForPath(rules, path);
    return { path, allowed: matchedRule?.type !== "disallow", matchedRule };
  });
  const blockedCount = pathChecks.filter((item) => !item.allowed).length;
  const headline =
    source === "none"
      ? "No matching group — default allow"
      : blockedCount === 0
        ? "No tested path is disallowed"
        : blockedCount === pathChecks.length
          ? "Every tested path is disallowed"
          : `${blockedCount} of ${pathChecks.length} tested paths are disallowed`;

  return { target, source, headline, blockedCount, pathChecks };
}
