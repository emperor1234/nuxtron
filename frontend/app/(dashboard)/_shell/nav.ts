/**
 * Customer dashboard navigation — the single source of truth for what exists.
 *
 * Every entry below is a page that is wired to a working backend route. A page
 * whose backend capability is missing, unconfigured, or fabricated is removed,
 * not parked behind a "coming soon" screen. Section hubs, the sidebar, product
 * gating (app/lib/product-line.ts) and ⌘K search all derive from this model.
 */

import type { Route } from "next";
import type { ProductLine } from "@/app/lib/product-line";

export type RailKey = "dashboard" | "seo" | "social" | "studio" | "apps" | "settings";

export type FlyoutItem = { label: string; href: Route; description?: string };
export type FlyoutGroup = { label: string; items: FlyoutItem[] };
export type FlyoutMenu = { title: string; summary: string; groups: FlyoutGroup[] };

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
    matchPrefixes: ["/content-generation", "/ads-generation"],
    hasMenu: true,
  },
  {
    key: "apps",
    product: "shared",
    label: "Business",
    href: "/crm",
    matchPrefixes: ["/crm", "/workflows", "/smart-inbox", "/disputes", "/trust-center", "/affiliate", "/playbooks"],
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
const social = (slug: string) => `/studio/social-studio/${slug}` as Route;

export const MENUS: Partial<Record<RailKey, FlyoutMenu>> = {
  seo: {
    title: "SEO",
    summary: "AI-assisted optimization for the content and pages you provide, across classic search and AI answer engines.",
    groups: [
      {
        label: "Content & on-page",
        items: [
          { label: "On-Page Optimizer", href: seo("on-page"), description: "Score a page against a focus keyword and get prioritized fixes." },
          { label: "AI Article Writer", href: seo("writer"), description: "Draft an SEO article from a topic, keyword and outline." },
          { label: "Content Brief", href: seo("content-brief"), description: "Build a brief with headings, questions and entities for a keyword." },
          { label: "Content Planner", href: seo("content-creation-blogging"), description: "Plan pillar topics and a publishing strategy for a blog." },
          { label: "Landing Page Brief", href: seo("landing"), description: "Generate a conversion-focused landing page brief." },
          { label: "Topical Map", href: seo("topical-map"), description: "Cluster a topic into pillar and supporting pages." },
          { label: "Brand Voice Rewrite", href: seo("brand-voice"), description: "Rewrite copy so it matches your brand voice." },
          { label: "eCommerce SEO", href: seo("ecommerce"), description: "Optimize product and category page copy." },
          { label: "Video SEO", href: seo("video"), description: "Optimize video titles, descriptions and chapters." },
          { label: "Schema Generator", href: seo("schemas"), description: "Generate JSON-LD structured data for a page." },
          { label: "Internal Linking", href: seo("internal-linking"), description: "Suggest internal links between your pages." },
        ],
      },
      {
        label: "AI search visibility",
        items: [
          { label: "Answer Engine (AEO)", href: seo("aeo"), description: "Shape content so answer engines can quote it." },
          { label: "Generative Engine (GEO)", href: seo("geo"), description: "Optimize for citation in generative AI answers." },
          { label: "AI Overviews (AIO)", href: seo("aio"), description: "Score machine-readability for AI summaries." },
          { label: "LLM Optimization (LLMO)", href: seo("llmo"), description: "Check how language models represent your brand." },
          { label: "Google AI (GXO)", href: seo("gxo"), description: "Estimate readiness for AI Overview citations." },
          { label: "Search Intent (SAGEO)", href: seo("sageo"), description: "Map intent and generative-search readiness." },
          { label: "AI SEO Assistant", href: seo("seo-ai"), description: "Keyword opportunities and content guidance from a seed topic." },
          { label: "Entity SEO", href: seo("entity"), description: "Analyze entity coverage and relationships." },
          { label: "E-E-A-T", href: seo("eeat"), description: "Score experience, expertise, authority and trust signals." },
          { label: "Multi-surface (MSVO)", href: seo("msvo"), description: "Visibility across search surfaces." },
          { label: "Voice Search (VSO)", href: seo("vso"), description: "Optimize for spoken and assistant queries." },
          { label: "Decentralized (DAEO)", href: seo("daeo"), description: "Readiness for federated and decentralized search." },
          { label: "Predictive (PEAO)", href: seo("peao"), description: "Forecast volatility and ranking risk." },
          { label: "Conversational (CXAO)", href: seo("cxao"), description: "Optimize for conversational experiences." },
          { label: "Search Experience (SXO)", href: seo("sxo"), description: "Align page experience with search intent." },
          { label: "UX & Conversion", href: seo("ux"), description: "Audit above-the-fold experience and conversion paths." },
          { label: "News & Discover", href: seo("news-discover"), description: "Readiness for news and Discover surfaces." },
          { label: "Prompt Research", href: seo("prompt-research"), description: "Research the prompts people ask AI about your topic." },
          { label: "AI Crawler Visibility", href: "/ai-visibility-dashboard", description: "See which AI crawlers reach your sites." },
          { label: "AI Search Impact", href: "/ai-search-impact-calculator", description: "Estimate the traffic impact of AI search." },
        ],
      },
      {
        label: "Links",
        items: [
          { label: "Backlink Intelligence", href: seo("backlink-intelligence"), description: "Assess a backlink profile you provide." },
          { label: "Link Building", href: seo("linkbuilding"), description: "Plan outreach and link opportunities." },
        ],
      },
      {
        label: "Strategy & operations",
        items: [
          { label: "SEO Workflow Planner", href: seo("planner"), description: "Turn a goal into an ordered SEO plan." },
          { label: "Growth Playbooks", href: seo("growth-playbooks"), description: "Pick and sequence growth plays." },
          { label: "A/B Test Design", href: seo("seo-ab-testing"), description: "Design SEO experiments you can run." },
          { label: "Site Migration", href: seo("site-migration"), description: "Plan redirects and risk for a migration." },
          { label: "Log File Analysis", href: seo("log-file"), description: "Analyze server log lines you provide." },
          { label: "Multi-Channel Activation", href: seo("multi-channel-activation"), description: "Reuse SEO content across channels." },
          { label: "Autonomous Agent", href: seo("agent"), description: "Plan an SEO run and review the proposed steps." },
          { label: "Revenue Attribution", href: seo("revenue-attribution"), description: "Attribute revenue to organic channels." },
          { label: "Content Check", href: "/seo-analysis", description: "Quick SEO check of a page or draft." },
          { label: "Benchmarks", href: "/benchmarks", description: "Compare your results against benchmarks." },
          { label: "Competitive Benchmarking", href: "/competitive-benchmarking", description: "Record and compare competitor observations." },
          { label: "Analysis History", href: seo("history"), description: "Every analysis you have run." },
        ],
      },
    ],
  },
  social: {
    title: "Social",
    summary: "Plan, publish, engage and measure across your connected social accounts.",
    groups: [
      {
        label: "Publish",
        items: [
          { label: "Post Planner", href: social("posts"), description: "Plan posts and keep them in one list." },
          { label: "Content Calendar", href: social("calendar"), description: "See planned posts by day and move them." },
          { label: "Content Queue", href: social("queue"), description: "What is planned next, grouped by day." },
          { label: "Bulk Import", href: social("bulk-schedule"), description: "Plan many posts at once from a file." },
          { label: "Ideas & Drafts", href: social("ideas"), description: "Capture ideas and turn them into drafts." },
        ],
      },
      {
        label: "Engage",
        items: [
          { label: "Social Inbox", href: social("inbox"), description: "Messages and comments in one place." },
          { label: "Comment Replies", href: social("community"), description: "Reply to comments with saved responses." },
          { label: "Content Approvals", href: social("approvals"), description: "Route posts through reviewers before publishing." },
        ],
      },
      {
        label: "Listen & measure",
        items: [
          { label: "Social Listening", href: "/social-listening", description: "Track keywords and mentions." },
          { label: "Monitoring Streams", href: social("streams"), description: "Live feeds for accounts and topics." },
          { label: "Social Media ROI", href: "/social-media-roi", description: "Connect social activity to revenue." },
        ],
      },
      {
        label: "Setup",
        items: [
          { label: "Connected Accounts", href: social("accounts"), description: "Connect and manage social accounts." },
          { label: "Browser Capture", href: social("browser-capture"), description: "Capture content from the web into drafts." },
        ],
      },
    ],
  },
  studio: {
    title: "Studio",
    summary: "Create content, images and video, and manage the brand they follow.",
    groups: [
      {
        label: "Create",
        items: [
          { label: "Content Generator", href: "/content-generation", description: "Generate long-form and short-form copy." },
          { label: "AI Copywriter", href: studio("copywriter"), description: "Marketing copy in your brand voice." },
          { label: "Image Studio", href: studio("image-studio"), description: "Generate and edit images." },
          { label: "Paid Ad Creative", href: "/ads-generation", description: "Generate ad variations." },
        ],
      },
      {
        label: "Brand & content",
        items: [
          { label: "Brands", href: studio("brands"), description: "Manage brands and their assets." },
          { label: "Brand Kit", href: studio("brand-kit"), description: "Colors, fonts and logos." },
          { label: "Brand Voice", href: studio("content-hub/brand-voice"), description: "Define how your brand sounds." },
          { label: "Brand Hierarchy", href: studio("content-hub/brand-hierarchy"), description: "Organize parent and sub-brands." },
        ],
      },
      {
        label: "Operate & measure",
        items: [
          { label: "Brand Profile", href: studio("workspace"), description: "Business details, tone, keywords and colors." },
          { label: "Studio Analytics", href: studio("analytics"), description: "Output and performance." },
          { label: "Agent Analytics", href: studio("agent-analytics"), description: "AI crawler and agent activity." },
          { label: "Keyword Tracker", href: studio("content-hub/word-cloud"), description: "Track the keywords you care about." },
          { label: "Answer Engine Hub", href: studio("answer-engine"), description: "Answer-engine content readiness." },
          { label: "CDN Analytics", href: studio("cdn-analytics"), description: "Delivery performance." },
        ],
      },
    ],
  },
  apps: {
    title: "Business",
    summary: "Customer relationships, workflows and trust in one place.",
    groups: [
      {
        label: "Customer operations",
        items: [
          { label: "CRM", href: "/crm", description: "Contacts, companies and deals." },
          { label: "Workflows", href: "/workflows", description: "Automations across your tools." },
          { label: "Customer Inbox", href: "/smart-inbox", description: "Customer messages with suggested replies." },
          { label: "Disputes", href: "/disputes", description: "Open cases that need a human decision." },
          { label: "Integration Playbooks", href: "/playbooks", description: "Step-by-step integration guides." },
        ],
      },
      {
        label: "Partnerships",
        items: [
          { label: "Referral Program", href: "/affiliate", description: "Invite partners and track referrals." },
        ],
      },
      {
        label: "Trust",
        items: [{ label: "Trust Center", href: "/trust-center", description: "Policies, approvals and audit trail." }],
      },
    ],
  },
  settings: {
    title: "Account",
    summary: "Your profile, plan and billing.",
    groups: [
      {
        label: "Account",
        items: [
          { label: "Account Overview", href: "/account", description: "Plan and usage at a glance." },
          { label: "Profile", href: "/account/profile", description: "Your details." },
          { label: "Orders", href: "/account/orders", description: "Purchase history." },
          { label: "Billing & Plans", href: "/billing", description: "Plan, credits and invoices." },
        ],
      },
    ],
  },
};
