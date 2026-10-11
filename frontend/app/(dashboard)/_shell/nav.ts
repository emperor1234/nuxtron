/**
 * Dashboard navigation model — mirrors the approved reference.
 * The icon rail lists top-level sections; each section (except Home) opens a
 * flyout whose items are grouped *by function*. Rail sections link to a valid
 * base route; flyout groups organise the tools within that section.
 */

import type { Route } from "next";
import type { ProductLine } from "@/app/lib/product-line";

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

export type FlyoutItem = { label: string; href: Route };
export type FlyoutGroup = { label: string; items: FlyoutItem[] };
export type FlyoutMenu = { title: string; groups: FlyoutGroup[] };

export type RailItem = {
  key: RailKey;
  label: string;
  href: Route;
  /** Additional route families owned by this rail section. */
  matchPrefixes?: readonly string[];
  /** Whether clicking opens a function-grouped flyout. */
  hasMenu: boolean;
  /**
   * Which product line owns this section. A user signed in to one product
   * only sees its sections plus the "shared" ones; proxy.ts enforces the same
   * split server-side so a deep link cannot reach the other product's pages.
   */
  product: ProductLine | "shared";
};

export const RAIL_ITEMS: readonly RailItem[] = [
  { key: "dashboard", product: "shared", label: "Home", href: "/dashboard", hasMenu: false },
  { key: "seo", product: "seo", label: "SEO", href: "/seo", hasMenu: true },
  { key: "ai", product: "seo", label: "AI", href: "/seo/seo-ai", hasMenu: true },
  { key: "traffic", product: "seo", label: "Traffic", href: "/seo/analytics", hasMenu: true },
  { key: "local", product: "seo", label: "Local", href: "/seo/local-seo", hasMenu: true },
  {
    key: "content", product: "marketing",
    label: "Content",
    href: "/content-generation",
    hasMenu: true,
  },
  // Social points at the Studio suite (25 pages) rather than /seo/social (1).
  {
    key: "social", product: "marketing",
    label: "Social",
    href: "/studio/social-studio",
    hasMenu: true,
  },
  // Studio had no rail entry at all, stranding 34 pages with no way in.
  {
    key: "studio", product: "marketing",
    label: "Studio",
    href: "/studio",
    matchPrefixes: ["/vse"],
    hasMenu: true,
  },
  {
    key: "apps", product: "shared",
    label: "Operations",
    href: "/crm",
    matchPrefixes: [
      "/crm",
      "/workflows",
      "/smart-inbox",
      "/disputes",
      "/finance-ops",
      "/outcome-graph",
      "/vendor-inventory-report",
      "/siem",
      "/trust-center",
      "/ai-security",
      "/platform-ops",
      "/platform",
      "/api-governance",
    ],
    hasMenu: true,
  },
];

export const SETTINGS_ITEM: RailItem = {
  key: "settings", product: "shared",
  label: "Settings",
  href: "/account/settings",
  matchPrefixes: ["/account", "/billing", "/white-label"],
  hasMenu: true,
};

const seo = (slug: string) => `/seo/${slug}` as Route;
const studio = (slug: string) => `/studio/${slug}` as Route;

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
        label: "AEO & AI search",
        items: [
          {
            label: "SEO / AEO / GEO Audit",
            href: "/seo-aeo-geo-audit-tool",
          },
          { label: "AI SEO Analysis", href: "/seo-analysis" },
        ],
      },
      {
        label: "Competitive Analysis",
        items: [
          { label: "Domain Overview", href: seo("domain-overview") },
          { label: "Organic Research", href: seo("keywords") },
          { label: "Top Pages", href: seo("performance") },
          { label: "Keyword Gap", href: seo("planner") },
          { label: "Keyword Strategy Builder", href: seo("growth-playbooks") },
        ],
      },
      {
        label: "Link Building",
        items: [
          { label: "Backlinks", href: seo("backlink-intelligence") },
          { label: "Link Building Tool", href: seo("linkbuilding") },
        ],
      },
      {
        label: "Content",
        items: [
          { label: "SEO Writing Assistant", href: seo("writer") },
          { label: "Content Brief", href: seo("content-brief") },
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
          {
            label: "AI Visibility Dashboard",
            href: "/ai-visibility-dashboard",
          },
          {
            label: "AI Search Impact",
            href: "/ai-search-impact-calculator",
          },
          { label: "Competitor Research", href: seo("competitor") },
          { label: "Prompt Research", href: seo("prompt-research") },
          { label: "Brand Performance", href: seo("brand-voice") },
        ],
      },
      {
        label: "Create",
        items: [
          { label: "AI Content Generator", href: "/content-generation" },
          { label: "Image Studio", href: "/media-processing" },
        ],
      },
      {
        label: "Optimize",
        items: [
          { label: "Answer Engine Optimization", href: seo("aeo") },
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
          { label: "Audience Intelligence", href: seo("audience-intelligence") },
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
        items: [{ label: "Local Heatmap", href: seo("local-heatmap") }],
      },
    ],
  },
  content: {
    title: "Content",
    groups: [
      {
        label: "Plan",
        items: [{ label: "Content Brief", href: seo("content-brief") }],
      },
      {
        label: "Create",
        items: [
          { label: "SEO Writing Assistant", href: seo("writer") },
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
        ],
      },
      {
        label: "Distribute",
        items: [
          { label: "Social Poster", href: seo("social") },
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
          { label: "Content Calendar", href: studio("social-studio/calendar") },
          { label: "Publishing Queue", href: studio("social-studio/queue") },
          { label: "Bulk Scheduler", href: studio("social-studio/bulk-schedule") },
          { label: "Best Time to Post", href: studio("social-studio/best-time") },
          { label: "Ideas & Drafts", href: studio("social-studio/ideas") },
        ],
      },
      {
        label: "Engage",
        items: [
          { label: "Smart Inbox", href: studio("social-studio/inbox") },
          { label: "Comment Replies", href: studio("social-studio/community") },
          { label: "Content Approvals", href: studio("social-studio/approvals") },
          { label: "Review Management", href: studio("social-studio/reviews") },
          { label: "UGC Management", href: studio("social-studio/ugc") },
        ],
      },
      {
        label: "Analyze",
        items: [
          { label: "Analytics & KPIs", href: studio("social-studio/analytics") },
          { label: "Audience Insights", href: studio("social-studio/audience") },
          { label: "Social Media ROI", href: "/social-media-roi" },
          { label: "Social Listening", href: studio("social-studio/listening") },
          { label: "Monitoring Streams", href: studio("social-studio/streams") },
          { label: "Social Trends", href: studio("social-studio/trends") },
        ],
      },
      {
        label: "Advertise & Grow",
        items: [
          { label: "Paid Social Ads", href: studio("social-studio/ads") },
          { label: "Ads Calendar", href: seo("ads-calendar") },
          { label: "Influencer CRM", href: studio("social-studio/influencers") },
          { label: "Link In Bio", href: studio("social-studio/link-in-bio") },
          { label: "Employee Advocacy", href: studio("social-studio/advocacy") },
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
          { label: "AI Copywriter", href: studio("copywriter") },
        ],
      },
      {
        label: "Brand",
        items: [
          { label: "Brand Hub", href: studio("brands") },
          { label: "Brand Kit", href: studio("brand-kit") },
          { label: "Brand Voice DNA", href: studio("content-hub/brand-voice") },
          { label: "Template System", href: studio("template-system") },
        ],
      },
      {
        label: "Growth",
        items: [
          { label: "AI Content Hub", href: studio("content-hub") },
          { label: "AI Growth Suite", href: studio("growth-suite") },
          { label: "Viral Content Engine", href: "/vse" },
          { label: "Rank Tracker", href: studio("rank-tracker") },
          {
            label: "Backlink Intelligence",
            href: studio("backlink-intelligence"),
          },
          { label: "Answer Engine Hub", href: studio("answer-engine") },
          { label: "Content Repurposer", href: studio("content-hub/repurpose") },
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
          { label: "Team & Roles", href: studio("team") },
        ],
      },
      {
        label: "Measure",
        items: [
          { label: "Platform Analytics", href: studio("analytics") },
          { label: "Agent Analytics", href: studio("agent-analytics") },
          { label: "A/B Testing Engine", href: studio("content-hub/ab-testing") },
          { label: "ROI Forecaster", href: studio("content-hub/roi-forecast") },
        ],
      },
    ],
  },
  apps: {
    title: "Operations",
    groups: [
      {
        label: "Customer operations",
        items: [
          { label: "CRM", href: "/crm" },
          { label: "Workflows", href: "/workflows" },
          { label: "Customer Inbox", href: "/smart-inbox" },
        ],
      },
      {
        label: "Finance & governance",
        items: [
          { label: "Finance Ops", href: "/finance-ops" },
          { label: "Disputes", href: "/disputes" },
          { label: "Outcome Graph", href: "/outcome-graph" },
          { label: "Vendor Inventory", href: "/vendor-inventory-report" },
        ],
      },
      {
        label: "Trust & security",
        items: [
          { label: "Trust Center", href: "/trust-center" },
          { label: "SIEM", href: "/siem" },
          { label: "AI Security", href: "/ai-security" },
          { label: "Platform Operations", href: "/platform-ops" },
        ],
      },
      {
        label: "Platform",
        items: [
          { label: "App Center", href: "/platform" },
          { label: "Integrations", href: seo("integrations-automation") },
          { label: "API Access", href: "/api-governance" },
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
          { label: "White label", href: "/white-label" },
        ],
      },
    ],
  },
};
