/**
 * Customer dashboard navigation. Keep the primary rail small and task-oriented;
 * less-used routes remain discoverable through the route search and product hubs.
 */

import type { Route } from "next";
import type { ProductLine } from "@/app/lib/product-line";

export type RailKey = "dashboard" | "seo" | "social" | "studio" | "apps" | "settings";

export type FlyoutItem = { label: string; href: Route };
export type FlyoutGroup = { label: string; items: FlyoutItem[] };
export type FlyoutMenu = { title: string; groups: FlyoutGroup[] };

export type RailItem = {
  key: RailKey;
  label: string;
  href: Route;
  /** Additional route families owned by this section. */
  matchPrefixes?: readonly string[];
  hasMenu: boolean;
  product: ProductLine | "shared";
};

export const RAIL_ITEMS: readonly RailItem[] = [
  { key: "dashboard", product: "shared", label: "Home", href: "/dashboard", hasMenu: false },
  {
    key: "seo",
    product: "seo",
    label: "SEO",
    href: "/seo",
    matchPrefixes: ["/ai-visibility-dashboard", "/ai-search-impact-calculator", "/benchmarks", "/competitive-benchmarking"],
    hasMenu: true,
  },
  {
    key: "social",
    product: "marketing",
    label: "Social",
    href: "/studio/social-studio",
    matchPrefixes: ["/social-media-roi", "/social-listening"],
    hasMenu: true,
  },
  {
    key: "studio",
    product: "marketing",
    label: "Studio",
    href: "/studio",
    matchPrefixes: ["/content-generation", "/ads-generation", "/media-processing"],
    hasMenu: true,
  },
  {
    key: "apps",
    product: "shared",
    label: "Business",
    href: "/crm",
    matchPrefixes: ["/crm", "/workflows", "/smart-inbox", "/disputes", "/trust-center"],
    hasMenu: true,
  },
];

export const SETTINGS_ITEM: RailItem = {
  key: "settings",
  product: "shared",
  label: "Account",
  href: "/account",
  matchPrefixes: ["/account", "/billing"],
  hasMenu: true,
};

const seo = (slug: string) => `/seo/${slug}` as Route;
const studio = (slug: string) => `/studio/${slug}` as Route;

export const MENUS: Partial<Record<RailKey, FlyoutMenu>> = {
  seo: {
    title: "SEO",
    groups: [
      {
        label: "Site health",
        items: [
          { label: "Technical SEO Audit", href: seo("technical") },
          { label: "Log File Analyzer", href: seo("log-file") },
          { label: "Security Header Review", href: seo("security") },
        ],
      },
      {
        label: "Research & visibility",
        items: [
          { label: "Domain Overview", href: seo("domain-overview") },
          { label: "Keyword Data Review", href: seo("keywords") },
          { label: "Rank Position Review", href: seo("rank-tracking") },
          { label: "Competitor Research", href: seo("competitor") },
          { label: "Corpus Search Preview", href: seo("rag-search") },
          { label: "Prompt Research", href: seo("prompt-research") },
          { label: "AI Visibility", href: seo("seo-ai") },
          { label: "AI Visibility Dashboard", href: "/ai-visibility-dashboard" },
          { label: "AI Search Impact", href: "/ai-search-impact-calculator" },
          { label: "Audience Intelligence", href: seo("audience-intelligence") },
          { label: "Brand Performance", href: seo("brand-voice") },
        ],
      },
      {
        label: "Market & research",
        items: [
          { label: "Market Explorer", href: seo("market-explorer") },
          { label: "Industry Benchmarks", href: "/benchmarks" },
          { label: "Competitive Benchmarking", href: "/competitive-benchmarking" },
          { label: "Trending Now", href: seo("news-discover") },
        ],
      },
      {
        label: "Analytics & history",
        items: [
          { label: "Traffic Analytics", href: seo("analytics") },
          { label: "Analysis History", href: seo("history") },
        ],
      },
      {
        label: "International SEO",
        items: [{ label: "Hreflang & Locale Review", href: seo("international-multilingual") }],
      },
      {
        label: "Optimize & automate",
        items: [
          { label: "Answer Engine Optimization", href: seo("aeo") },
          { label: "SEO Workflow Planner", href: seo("planner") },
          { label: "Programmatic SEO Draft Preview", href: seo("programmatic") },
          { label: "A/B Test Lab", href: seo("seo-ab-testing") },
          { label: "Growth Playbooks", href: seo("growth-playbooks") },
        ],
      },
      {
        label: "Content & links",
        items: [
          { label: "SEO Writing Assistant", href: seo("writer") },
          { label: "Content Brief", href: seo("content-brief") },
          { label: "Social Share Preview", href: seo("social") },
          { label: "Backlink Intelligence", href: seo("backlink-intelligence") },
          { label: "Link Building", href: seo("linkbuilding") },
        ],
      },
    ],
  },
  social: {
    title: "Social",
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
        ],
      },
      {
        label: "Listen & measure",
        items: [
          { label: "Social Analytics", href: studio("social-studio/analytics") },
          { label: "Audience Insights", href: studio("social-studio/audience") },
          { label: "Social Listening", href: "/social-listening" },
          { label: "Monitoring Streams", href: studio("social-studio/streams") },
          { label: "Social Trends", href: studio("social-studio/trends") },
          { label: "Social Media ROI", href: "/social-media-roi" },
        ],
      },
      {
        label: "Grow",
        items: [
          { label: "Paid Social Ads", href: studio("social-studio/ads") },
          { label: "Influencer CRM", href: studio("social-studio/influencers") },
          { label: "Link in Bio", href: studio("social-studio/link-in-bio") },
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
          { label: "Content Generator", href: "/content-generation" },
          { label: "Editor", href: studio("editor") },
          { label: "AI Copywriter", href: studio("copywriter") },
          { label: "Image Studio", href: studio("image-studio") },
          { label: "Product Photoshoot", href: studio("image-direction") },
          { label: "Short Video Factory", href: studio("short-video-factory") },
          { label: "Reels Factory", href: studio("reels-factory") },
          { label: "Faceless Video Engine", href: studio("faceless-video-engine") },
          { label: "Avatar Builder", href: studio("avatar-builder") },
          { label: "Paid Ad Creative", href: "/ads-generation" },
          { label: "Media Processing", href: "/media-processing" },
        ],
      },
      {
        label: "Brand & content",
        items: [
          { label: "Brands", href: studio("brands") },
          { label: "Brand Kit", href: studio("brand-kit") },
          { label: "Brand Voice", href: studio("content-hub/brand-voice") },
          { label: "Brand Hierarchy", href: studio("content-hub/brand-hierarchy") },
          { label: "Content Hub", href: studio("content-hub") },
          { label: "Repurpose Content", href: studio("content-hub/repurpose") },
          { label: "Template System", href: studio("template-system") },
        ],
      },
      {
        label: "Grow",
        items: [
          { label: "Backlink Intelligence", href: studio("backlink-intelligence") },
          { label: "Answer Engine Hub", href: studio("answer-engine") },
          { label: "Keyword Intelligence", href: studio("content-hub/word-cloud") },
          { label: "Multilingual Ads", href: studio("multilingual-ads") },
        ],
      },
      {
        label: "Operate & measure",
        items: [
          { label: "Workspace", href: studio("workspace") },
          { label: "Team", href: studio("team") },
          { label: "Studio Analytics", href: studio("analytics") },
          { label: "Agent Analytics", href: studio("agent-analytics") },
          { label: "Intelligence", href: studio("intelligence") },
          { label: "A/B Testing", href: studio("content-hub/ab-testing") },
          { label: "ROI Forecast", href: studio("content-hub/roi-forecast") },
          { label: "CDN Analytics", href: studio("cdn-analytics") },
        ],
      },
    ],
  },
  apps: {
    title: "Business",
    groups: [
      {
        label: "Customer operations",
        items: [
          { label: "CRM", href: "/crm" },
          { label: "Workflows", href: "/workflows" },
          { label: "Customer Inbox", href: "/smart-inbox" },
          { label: "Disputes", href: "/disputes" },
        ],
      },
      {
        label: "Partnerships",
        items: [
          { label: "Referral Program", href: "/affiliate" },
          { label: "Partner Performance", href: "/affiliate/dashboard" },
        ],
      },
      {
        label: "Trust",
        items: [{ label: "Trust Center", href: "/trust-center" }],
      },
    ],
  },
  settings: {
    title: "Account",
    groups: [
      {
        label: "Account",
        items: [
          { label: "Account Overview", href: "/account" },
          { label: "Profile", href: "/account/profile" },
          { label: "Orders", href: "/account/orders" },
          { label: "Billing & Plans", href: "/billing" },
        ],
      },
    ],
  },
};
