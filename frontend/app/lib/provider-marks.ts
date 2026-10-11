/**
 * Factual provider/product mark registry.
 *
 * Third-party marks are rendered only as identifiers for coverage, integrations,
 * or measured provider activity. They are not Nuxtron marks and do not imply an
 * endorsement, partnership, or affiliation.
 */
export type ProviderMark = {
  key: string;
  label: string;
  src: string;
  aliases: readonly string[];
};

const MARKS: readonly ProviderMark[] = [
  {
    key: "chatgpt",
    label: "ChatGPT",
    src: "/brand/providers/chatgpt.ico",
    aliases: [
      "chatgpt",
      "openai",
      "gptbot",
      "oai searchbot",
      "chatgpt user",
      "openai crawler",
    ],
  },
  {
    key: "perplexity",
    label: "Perplexity",
    src: "/brand/providers/perplexity.svg",
    aliases: [
      "perplexity",
      "perplexity ai",
      "perplexitybot",
      "perplexity user",
    ],
  },
  {
    key: "gemini",
    label: "Gemini",
    src: "/brand/providers/gemini.svg",
    aliases: ["gemini", "google gemini", "geminibot", "gemini bot"],
  },
  {
    key: "claude",
    label: "Claude",
    src: "/brand/providers/claude.svg",
    aliases: ["claude", "anthropic", "claudebot", "anthropic ai"],
  },
  {
    key: "brave",
    label: "Brave",
    src: "/brand/providers/brave.svg",
    aliases: ["brave", "brave search", "brave search ai", "brave ai"],
  },
  {
    key: "google",
    label: "Google",
    src: "/brand/providers/google.svg",
    aliases: [
      "google",
      "google search console",
      "google business profile",
      "google reviews",
      "google ai overview",
      "google ai overviews",
      "googlebot",
      "google extended",
    ],
  },
  {
    key: "bing",
    label: "Bing",
    src: "/brand/providers/bing.png",
    aliases: ["bing", "bing webmaster", "bingbot"],
  },
  {
    key: "instagram",
    label: "Instagram",
    src: "/brand/providers/instagram.svg",
    aliases: ["instagram", "instagram reels"],
  },
  {
    key: "linkedin",
    label: "LinkedIn",
    src: "/brand/providers/linkedin.ico",
    aliases: ["linkedin", "linkedin video"],
  },
  {
    key: "facebook",
    label: "Facebook",
    src: "/brand/providers/facebook.svg",
    aliases: ["facebook"],
  },
  {
    key: "tiktok",
    label: "TikTok",
    src: "/brand/providers/tiktok.svg",
    aliases: ["tiktok", "tiktok reels"],
  },
  {
    key: "youtube",
    label: "YouTube",
    src: "/brand/providers/youtube.svg",
    aliases: ["youtube", "youtube shorts"],
  },
  {
    key: "x",
    label: "X",
    src: "/brand/providers/x.svg",
    aliases: ["x", "x twitter", "twitter"],
  },
  {
    key: "pinterest",
    label: "Pinterest",
    src: "/brand/providers/pinterest.svg",
    aliases: ["pinterest"],
  },
  {
    key: "threads",
    label: "Threads",
    src: "/brand/providers/threads.svg",
    aliases: ["threads"],
  },
  {
    key: "bluesky",
    label: "Bluesky",
    src: "/brand/providers/bluesky.svg",
    aliases: ["bluesky", "blue sky"],
  },
  {
    key: "hubspot",
    label: "HubSpot",
    src: "/brand/providers/hubspot.svg",
    aliases: ["hubspot"],
  },
  {
    key: "salesforce",
    label: "Salesforce",
    src: "/brand/providers/salesforce.ico",
    aliases: ["salesforce"],
  },
  {
    key: "stripe",
    label: "Stripe",
    src: "/brand/providers/stripe.svg",
    aliases: ["stripe"],
  },
  {
    key: "quickbooks",
    label: "QuickBooks",
    src: "/brand/providers/quickbooks.svg",
    aliases: ["quickbooks", "quick books"],
  },
  {
    key: "slack",
    label: "Slack",
    src: "/brand/providers/slack.png",
    aliases: ["slack"],
  },
  {
    key: "gmail",
    label: "Gmail",
    src: "/brand/providers/gmail.svg",
    aliases: ["gmail"],
  },
  {
    key: "twilio",
    label: "Twilio",
    src: "/brand/providers/twilio.svg",
    aliases: ["twilio"],
  },
  {
    key: "zendesk",
    label: "Zendesk",
    src: "/brand/providers/zendesk.svg",
    aliases: ["zendesk"],
  },
  {
    key: "trustpilot",
    label: "Trustpilot",
    src: "/brand/providers/trustpilot.svg",
    aliases: ["trustpilot"],
  },
  {
    key: "yelp",
    label: "Yelp",
    src: "/brand/providers/yelp.svg",
    aliases: ["yelp"],
  },
  { key: "g2", label: "G2", src: "/brand/providers/g2.svg", aliases: ["g2"] },
  {
    key: "googlecloud",
    label: "Google Cloud",
    src: "/brand/providers/googlecloud.svg",
    aliases: ["google cloud", "google cloud storage"],
  },
];

function normalize(value: string): string {
  return value
    .toLocaleLowerCase("en-US")
    .replace(/[^\p{L}\p{N}]+/gu, " ")
    .trim();
}

const NORMALIZED_MARKS = MARKS.flatMap((mark) =>
  mark.aliases.map((alias) => ({ mark, alias: normalize(alias) })),
).sort((a, b) => b.alias.length - a.alias.length);

/** Resolve a provider name/label to its unchanged, locally served mark. */
export function getProviderMark(name: string): ProviderMark | undefined {
  const normalized = normalize(name);
  if (!normalized) return undefined;
  return NORMALIZED_MARKS.find(
    ({ alias }) =>
      normalized === alias ||
      normalized.startsWith(`${alias} `) ||
      normalized.includes(` ${alias} `),
  )?.mark;
}

export const PROVIDER_MARKS: readonly ProviderMark[] = MARKS;
