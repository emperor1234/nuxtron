/**
 * Dashboard navigation model — mirrors the approved reference.
 * The icon rail lists top-level sections; each section (except Home) opens a
 * flyout whose items are grouped *by function*. Rail sections link to a valid
 * base route; flyout groups organise the tools within that section.
 */

export type RailKey =
  | "dashboard"
  | "seo"
  | "ai"
  | "traffic"
  | "local"
  | "content"
  | "social"
  | "studio"
  | "apps"
  | "settings";

export type FlyoutItem = { label: string; href: string };
export type FlyoutGroup = { label: string; items: FlyoutItem[] };
export type FlyoutMenu = { title: string; groups: FlyoutGroup[] };

export type RailItem = {
  key: RailKey;
  label: string;
  href: string;
  /** Whether clicking opens a function-grouped flyout. */
  hasMenu: boolean;
};

export const RAIL_ITEMS: readonly RailItem[] = [
  { key: "dashboard", label: "Home", href: "/dashboard", hasMenu: false },
  { key: "seo", label: "SEO", href: "/seo", hasMenu: true },
  { key: "ai", label: "AI", href: "/seo/seo-ai", hasMenu: true },
  { key: "traffic", label: "Traffic", href: "/seo/analytics", hasMenu: true },
  { key: "local", label: "Local", href: "/seo/local-seo", hasMenu: true },
  {
    key: "content",
    label: "Content",
    href: "/content-generation",
    hasMenu: true,
  },
  // Social points at the Studio suite (25 pages) rather than /seo/social (1).
  {
    key: "social",
    label: "Social",
    href: "/studio/social-studio",
    hasMenu: true,
  },
  // Studio had no rail entry at all, stranding 34 pages with no way in.
  { key: "studio", label: "Studio", href: "/studio", hasMenu: true },
  { key: "apps", label: "Apps", href: "/platform", hasMenu: true },
];

export const SETTINGS_ITEM: RailItem = {
  key: "settings",
  label: "Settings",
  href: "/account/settings",
  hasMenu: true,
};

const seo = (slug: string) => `/seo/${slug}`;
const studio = (slug: string) => `/studio/${slug}`;

export const MENUS: Partial<Record<RailKey, FlyoutMenu>> = {
  seo: {
    title: "SEO",
    groups: [
      {
        label: "Site Performance",
        items: [
          { label: "Site Audit", href: seo("technical") },
          { label: "Position Tracking", href: seo("rank-tracking") },
          { label: "Log File Analyzer", href: seo("log-file") },
        ],
      },
      {
        label: "Competitive Analysis",
        items: [
          { label: "Domain Overview", href: seo("domain-overview") },
          { label: "Organic Research", href: seo("keywords") },
          { label: "Top Pages", href: seo("performance") },
          { label: "Keyword Gap", href: seo("planner") },
          { label: "Backlink Gap", href: seo("backlink-intelligence") },
        ],
      },
      {
        label: "Keyword Research",
        items: [
          { label: "Keyword Overview", href: seo("keywords") },
          { label: "Keyword Magic Tool", href: seo("planner") },
          { label: "Keyword Strategy Builder", href: seo("growth-playbooks") },
        ],
      },
      {
        label: "Link Building",
        items: [
          { label: "Backlinks", href: seo("backlink-intelligence") },
          { label: "Referring Domains", href: seo("backlink-intelligence") },
          { label: "Backlink Audit", href: seo("backlink-intelligence") },
          { label: "Link Building Tool", href: seo("linkbuilding") },
        ],
      },
      {
        label: "Content",
        items: [
          { label: "SEO Writing Assistant", href: seo("writer") },
          { label: "Topic Research", href: seo("content-brief") },
          { label: "SEO Content Template", href: seo("content-brief") },
        ],
      },
    ],
  },
  ai: {
    title: "AI Visibility",
    groups: [
      {
        label: "Research & optimize",
        items: [
          { label: "AI Visibility Overview", href: seo("seo-ai") },
          { label: "Competitor Research", href: seo("competitor") },
          { label: "Prompt Research", href: seo("promptwatch-assist") },
          { label: "Brand Performance", href: seo("brand-voice") },
          { label: "Site Audit", href: seo("technical") },
        ],
      },
      {
        label: "Create",
        items: [
          { label: "AI Content Generator", href: "/content-generation" },
          { label: "AI Copywriter", href: seo("writer") },
          { label: "Image Studio", href: "/media-processing" },
          { label: "Brand Voice", href: seo("brand-voice") },
        ],
      },
      {
        label: "Optimize",
        items: [
          { label: "AI SEO Assistant", href: seo("seo-ai-assist") },
          { label: "A/B Test Lab", href: seo("seo-ab-testing") },
        ],
      },
      {
        label: "Automate",
        items: [
          {
            label: "Campaign Autopilot",
            href: seo("cross-network-campaign-orchestrator"),
          },
          { label: "Smart Scheduler", href: seo("ads-smart-schedule") },
          { label: "Auto Reports", href: seo("client-portal") },
        ],
      },
      {
        label: "Insights",
        items: [
          { label: "Trend Predictor", href: "/ai-analytics" },
          { label: "Audience Intelligence", href: seo("one2target") },
        ],
      },
    ],
  },
  traffic: {
    title: "Traffic & Market",
    groups: [
      {
        label: "Market Analysis",
        items: [
          { label: "Market Explorer", href: seo("market-explorer") },
          { label: "Traffic Analytics", href: seo("analytics") },
          { label: "One2Target", href: seo("one2target") },
        ],
      },
      {
        label: "Benchmarking",
        items: [
          { label: "Industry Benchmarks", href: "/benchmarks" },
          { label: "Growth Quadrant", href: "/competitive-benchmarking" },
          { label: "Trending Now", href: seo("news-discover") },
        ],
      },
      {
        label: "Audience",
        items: [
          { label: "Demographics", href: seo("one2target") },
          { label: "Audience Overlap", href: seo("market-explorer") },
        ],
      },
    ],
  },
  local: {
    title: "Local",
    groups: [
      {
        label: "Local SEO",
        items: [
          { label: "Listing Management", href: seo("local-seo") },
          { label: "Map Rank Tracker", href: seo("map-rank-tracker") },
          { label: "Review Management", href: seo("reviews") },
        ],
      },
      {
        label: "Business Profile",
        items: [
          { label: "GBP Optimization", href: seo("map-rank-tracker") },
          { label: "Local Heatmap", href: seo("local-heatmap") },
        ],
      },
    ],
  },
  content: {
    title: "Content",
    groups: [
      {
        label: "Plan",
        items: [
          { label: "Content Calendar", href: seo("ads-calendar") },
          { label: "Topic Research", href: seo("content-brief") },
          { label: "Brief Generator", href: seo("content-brief") },
        ],
      },
      {
        label: "Create",
        items: [
          { label: "AI Writer", href: seo("writer") },
          {
            label: "Content Templates",
            href: seo("content-creation-blogging"),
          },
        ],
      },
      {
        label: "Optimize",
        items: [
          { label: "On-Page Checker", href: seo("on-page") },
          { label: "Readability Score", href: seo("content-auditor") },
          { label: "SEO Writing Assistant", href: seo("writer") },
        ],
      },
      {
        label: "Distribute",
        items: [
          { label: "Social Poster", href: seo("social") },
          { label: "Newsletter Builder", href: "/content-generation" },
        ],
      },
    ],
  },
  social: {
    title: "Social Media",
    groups: [
      {
        label: "Publish",
        items: [
          { label: "Post Scheduler", href: studio("social-studio/posts") },
          {
            label: "Campaign Calendar",
            href: studio("social-studio/calendar"),
          },
          {
            label: "Bulk Scheduler",
            href: studio("social-studio/bulk-schedule"),
          },
          {
            label: "Best Time to Post",
            href: studio("social-studio/best-time"),
          },
        ],
      },
      {
        label: "Engage",
        items: [
          { label: "Smart Inbox", href: studio("social-studio/inbox") },
          {
            label: "Content Approvals",
            href: studio("social-studio/approvals"),
          },
          { label: "Review Management", href: studio("social-studio/reviews") },
          { label: "UGC Management", href: studio("social-studio/ugc") },
        ],
      },
      {
        label: "Analyze",
        items: [
          {
            label: "Analytics & KPIs",
            href: studio("social-studio/analytics"),
          },
          {
            label: "Social Listening",
            href: studio("social-studio/listening"),
          },
          {
            label: "Monitoring Streams",
            href: studio("social-studio/streams"),
          },
          { label: "Social Trends", href: studio("social-studio/trends") },
        ],
      },
      {
        label: "Advertise & Grow",
        items: [
          { label: "Paid Social Ads", href: studio("social-studio/ads") },
          {
            label: "Influencer CRM",
            href: studio("social-studio/influencers"),
          },
          { label: "Link In Bio", href: studio("social-studio/link-in-bio") },
          {
            label: "Employee Advocacy",
            href: studio("social-studio/advocacy"),
          },
        ],
      },
    ],
  },
  studio: {
    title: "Studio",
    groups: [
      {
        label: "Create",
        items: [
          { label: "Editor", href: studio("editor") },
          { label: "AI Image Studio", href: studio("image-studio") },
          { label: "Short Video Factory", href: studio("short-video-factory") },
          { label: "Reels Factory", href: studio("reels-factory") },
          { label: "Avatar Builder", href: studio("avatar-builder") },
        ],
      },
      {
        label: "Brand",
        items: [
          { label: "Brand Hub", href: studio("brands") },
          { label: "Brand Kit", href: studio("brand-kit") },
          { label: "Brand Voice DNA", href: studio("lately/brand-voice") },
          { label: "Template System", href: studio("template-system") },
        ],
      },
      {
        label: "Growth",
        items: [
          { label: "AI Growth Suite", href: studio("growth-suite") },
          { label: "Rank Tracker", href: studio("rank-tracker") },
          {
            label: "Backlink Intelligence",
            href: studio("backlink-intelligence"),
          },
          { label: "Answer Engine Hub", href: studio("answer-engine") },
          { label: "Content Repurposer", href: studio("lately/repurpose") },
        ],
      },
      {
        label: "Operate",
        items: [
          { label: "Workspace", href: studio("workspace") },
          {
            label: "Workflow Orchestrator",
            href: studio("workflow-orchestrator"),
          },
          { label: "Team & Approvals", href: studio("team") },
          { label: "Scheduler", href: studio("scheduler") },
        ],
      },
      {
        label: "Measure",
        items: [
          { label: "Platform Analytics", href: studio("analytics") },
          { label: "Agent Analytics", href: studio("agent-analytics") },
          { label: "A/B Testing Engine", href: studio("lately/ab-testing") },
          { label: "ROI Forecaster", href: studio("lately/roi-forecast") },
        ],
      },
    ],
  },
  apps: {
    title: "Apps & More",
    groups: [
      {
        label: "Marketplace",
        items: [
          { label: "App Center", href: "/platform" },
          { label: "Integrations", href: seo("integrations-automation") },
          { label: "API Access", href: "/api-governance" },
        ],
      },
      {
        label: "Resources",
        items: [
          { label: "Agency Kit", href: seo("agency-platform") },
          { label: "Academy", href: "/playbooks" },
          {
            label: "Templates Gallery",
            href: seo("content-creation-blogging"),
          },
        ],
      },
    ],
  },
  settings: {
    title: "Settings",
    groups: [
      {
        label: "Account",
        items: [
          { label: "Profile", href: "/account/profile" },
          { label: "Billing & Plans", href: "/billing" },
          { label: "Team Members", href: "/account" },
        ],
      },
      {
        label: "Preferences",
        items: [
          { label: "Notifications", href: "/account/settings" },
          { label: "Connected Apps", href: seo("integrations-automation") },
          { label: "API Keys", href: "/api-governance" },
        ],
      },
    ],
  },
};
