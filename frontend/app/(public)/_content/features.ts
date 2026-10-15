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
      "Review supplied keyword exports, manual competitor observations, prompts and market context.",
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
      "Review rank exports and other supplied results. Live position and performance monitoring are unavailable.",
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
    id: "domain-overview",
    name: "Domain Overview",
    product: "seo",
    job: "research",
    icon: "search",
    description:
      "A snapshot of any domain's search visibility and its closest competitors.",
  },
  {
    id: "organic-research",
    name: "Keyword Data Review",
    product: "seo",
    job: "research",
    icon: "search",
    description:
      "Review keyword rows and metrics from a CSV export you provide, locally in your browser.",
  },
  {
    id: "backlinks",
    name: "Backlink Intelligence",
    product: "seo",
    job: "research",
    icon: "link",
    description: "Inspect a domain's backlink profile and referring domains.",
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
  {
    id: "competitor-research",
    name: "Competitor Research",
    product: "seo",
    job: "research",
    icon: "users",
    description:
      "See which competitors AI assistants recommend, and for which questions.",
  },
  {
    id: "market-explorer",
    name: "Market Explorer",
    product: "seo",
    job: "research",
    icon: "chart",
    description: "Size a market and map the companies competing in it.",
  },
  {
    id: "traffic-analytics",
    name: "Traffic Analytics",
    product: "seo",
    job: "research",
    icon: "chart",
    description:
      "Compare search KPIs across two periods using values you provide.",
  },
  {
    id: "social-trends",
    name: "Social Trends",
    product: "marketing",
    job: "research",
    icon: "megaphone",
    description: "Spot topics gaining momentum across social channels.",
  },

  // Create & optimize
  {
    id: "log-file-analyzer",
    name: "Log File Analyzer",
    product: "seo",
    job: "create",
    icon: "file-text",
    description: "See how search engine bots actually crawl your site.",
  },
  {
    id: "seo-writing-assistant",
    name: "SEO Writing Assistant",
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
    id: "short-video-factory",
    name: "Short Video Factory",
    product: "marketing",
    job: "create",
    icon: "megaphone",
    description: "Produce short-form video from the content you already have.",
  },
  {
    id: "content-repurposer",
    name: "Repurpose Content",
    product: "marketing",
    job: "create",
    icon: "workflow",
    description: "Turn one piece into posts, emails and cuts for each channel.",
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
  {
    id: "template-system",
    name: "Template System",
    product: "marketing",
    job: "create",
    icon: "workflow",
    description: "Start campaigns and assets from reusable templates.",
  },

  // Track
  {
    id: "position-tracking",
    name: "Rank Position Review",
    product: "seo",
    job: "track",
    icon: "chart",
    description: "Review positions from a CSV you provide. Values stay in your browser; live monitoring and forecasts are unavailable.",
  },
  {
    id: "ai-visibility-overview",
    name: "AI Visibility",
    product: "seo",
    job: "track",
    icon: "sparkles",
    description: "Track how AI assistants mention and cite your brand.",
  },
  {
    id: "brand-performance",
    name: "Brand Performance",
    product: "seo",
    job: "track",
    icon: "chart",
    description: "Measure your share of AI answers against competitors.",
  },
  {
    id: "industry-benchmarks",
    name: "Industry Benchmarks",
    product: "seo",
    job: "track",
    icon: "chart",
    description: "Compare your numbers with your industry's.",
  },
  {
    id: "platform-analytics",
    name: "Social Analytics",
    product: "marketing",
    job: "track",
    icon: "chart",
    description: "Performance across your connected channels in one view.",
  },
  {
    id: "audience-insights",
    name: "Audience Insights",
    product: "marketing",
    job: "track",
    icon: "users",
    description: "See who your audience is and when they engage.",
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
    id: "post-scheduler",
    name: "Post Scheduler",
    product: "marketing",
    job: "engage",
    icon: "calendar",
    description: "Schedule posts across your connected channels.",
  },
  {
    id: "smart-inbox",
    name: "Smart Inbox",
    product: "marketing",
    job: "engage",
    icon: "inbox",
    description:
      "Reply to comments and messages from every channel in one queue.",
  },
  {
    id: "publishing-queue",
    name: "Publishing Queue",
    product: "marketing",
    job: "engage",
    icon: "calendar",
    description: "Order the queue and set posting times for each channel.",
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
    id: "link-in-bio",
    name: "Link in Bio",
    product: "marketing",
    job: "engage",
    icon: "link",
    description: "One link that sends your audience wherever you need them.",
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
