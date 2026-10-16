import type { ProductLine } from "@/app/lib/product-line";
import type { SectionIcon } from "./types";

/**
 * Public feature directory, organised by the job a tool does across both
 * products.
 *
 * Every tool here is a real page in the dashboard menus
 * (app/(dashboard)/_shell/nav.ts); names match the menu labels so a visitor
 * finds the same tool after signing in. Descriptions say only what the tool
 * is for — no performance claims.
 */

export type FeatureJob = "research" | "create" | "track" | "engage";

export type FeatureTool = {
  id: string;
  name: string;
  /** "both" when the tool sits in both products' menus. */
  product: ProductLine | "both";
  job: FeatureJob;
  icon: SectionIcon;
  description: string;
};

export const FEATURE_JOBS: readonly {
  id: FeatureJob;
  title: string;
  summary: string;
  icon: SectionIcon;
}[] = [
  {
    id: "research",
    title: "Research",
    summary:
      "Research the prompts people ask AI assistants and the angles worth covering.",
    icon: "search",
  },
  {
    id: "create",
    title: "Create & optimize",
    summary:
      "Turn findings into briefs, pages, copy and creative — and fix what holds them back.",
    icon: "sparkles",
  },
  {
    id: "track",
    title: "Track",
    summary:
      "See how crawlers reach your sites and how your content and campaigns perform.",
    icon: "chart",
  },
  {
    id: "engage",
    title: "Publish & engage",
    summary: "Schedule the work, keep listings right and answer every reply.",
    icon: "share",
  },
];

export const FEATURE_TOOLS: readonly FeatureTool[] = [
  // Research
  {
    id: "backlinks",
    name: "Backlink Intelligence",
    product: "seo",
    job: "research",
    icon: "link",
    description: "Plan link-earning strategy around the competitors you name.",
  },
  {
    id: "prompt-research",
    name: "Prompt Research",
    product: "seo",
    job: "research",
    icon: "sparkles",
    description:
      "Find the questions buyers ask AI assistants about your category.",
  },

  // Create & optimize
  {
    id: "log-file-analyzer",
    name: "Log File Analysis",
    product: "seo",
    job: "create",
    icon: "file-text",
    description: "See how search engine bots actually crawl your site.",
  },
  {
    id: "seo-writing-assistant",
    name: "AI Article Writer",
    product: "both",
    job: "create",
    icon: "file-text",
    description:
      "Write against the topics, terms and questions a page should cover.",
  },
  {
    id: "content-brief",
    name: "Content Brief",
    product: "both",
    job: "create",
    icon: "file-text",
    description:
      "Turn a keyword or prompt into a structured brief for writers.",
  },
  {
    id: "ai-content-generator",
    name: "Content Generator",
    product: "both",
    job: "create",
    icon: "sparkles",
    description: "Draft articles, posts and campaign copy with AI.",
  },
  {
    id: "ai-copywriter",
    name: "AI Copywriter",
    product: "marketing",
    job: "create",
    icon: "sparkles",
    description:
      "Write platform-ready captions for each network, scored before you post.",
  },
  {
    id: "ai-image-studio",
    name: "Image Studio",
    product: "marketing",
    job: "create",
    icon: "sparkles",
    description: "Create and edit images for campaigns and posts.",
  },
  {
    id: "brand-kit",
    name: "Brand Kit",
    product: "marketing",
    job: "create",
    icon: "shield",
    description: "Keep colours, fonts and logos consistent in every asset.",
  },
  {
    id: "brand-voice-dna",
    name: "Brand Voice",
    product: "marketing",
    job: "create",
    icon: "megaphone",
    description: "Capture your tone of voice so every draft sounds like you.",
  },

  // Track
  {
    id: "ai-visibility-overview",
    name: "AI Crawler Visibility",
    product: "seo",
    job: "track",
    icon: "sparkles",
    description: "See which AI crawlers reach your sites.",
  },
  {
    id: "industry-benchmarks",
    name: "Benchmarks",
    product: "seo",
    job: "track",
    icon: "chart",
    description: "Compare your numbers with your industry's.",
  },
  {
    id: "social-media-roi",
    name: "Social Media ROI",
    product: "marketing",
    job: "track",
    icon: "chart",
    description: "Connect social activity to the results it drove.",
  },
  {
    id: "agent-analytics",
    name: "Agent Analytics",
    product: "marketing",
    job: "track",
    icon: "bot",
    description:
      "See which AI crawlers and bots visit your site, and what they read.",
  },

  // Publish & engage
  {
    id: "content-calendar",
    name: "Content Calendar",
    product: "marketing",
    job: "engage",
    icon: "calendar",
    description: "Plan every channel on one calendar, with briefs attached.",
  },
  {
    id: "smart-inbox",
    name: "Social Inbox",
    product: "marketing",
    job: "engage",
    icon: "inbox",
    description:
      "Reply to comments and messages from every channel in one queue.",
  },
  {
    id: "comment-replies",
    name: "Comment Replies",
    product: "marketing",
    job: "engage",
    icon: "inbox",
    description: "Answer comments across networks with saved replies.",
  },
  {
    id: "content-approvals",
    name: "Content Approvals",
    product: "marketing",
    job: "engage",
    icon: "workflow",
    description: "Route work to the right reviewer before anything publishes.",
  },
];

export type ProductFilter = "all" | ProductLine;

/** Pure filter used by the explorer and its tests. */
export function filterTools(
  tools: readonly FeatureTool[],
  product: ProductFilter,
  query: string,
): FeatureTool[] {
  const q = query.trim().toLowerCase();
  return tools.filter((tool) => {
    if (
      product !== "all" &&
      tool.product !== product &&
      tool.product !== "both"
    )
      return false;
    if (!q) return true;
    return `${tool.name} ${tool.description}`.toLowerCase().includes(q);
  });
}
