import { productAuthHref } from "@/app/lib/product-line";
import type { HomepageContent } from "./types";

const START = productAuthHref("/register", "seo");

/**
 * Nuxtron SEO homepage. Every capability below maps to a page in the SEO,
 * AI, Traffic or Local dashboard menus (app/(dashboard)/_shell/nav.ts).
 *
 * Engine coverage is limited to the engines Answer Engine Insights actually
 * queries for brand mentions (backend/fastapi/app/answer_engine/insights.py,
 * AISearchEngine). Google AI Overviews and Copilot are only scoring targets in
 * the GEO optimiser, so they are not claimed as tracked here.
 */
export const seoHomepage: HomepageContent = {
  product: "seo",

  hero: {
    eyebrow: "Search and AI answer-engine visibility",
    headlineLead: "Be the answer",
    headlineAccent: "your buyers find.",
    highlight: "answer",
    intro:
      "Nuxtron SEO reviews keyword and rank exports you provide, compares manually supplied search metrics, and helps teams plan the next step. It does not perform live rank or provider-backed local review monitoring.",
    primaryCta: { label: "Start with Nuxtron SEO", href: START },
    secondaryCta: { label: "See it working", href: "#demo" },
    explainer: "seo",
    coverageLabel: "AI engines in research scope",
    coverage: ["ChatGPT", "Perplexity", "Gemini", "Claude", "Brave Search AI"],
  },

  demo: {
    eyebrow: "Product tour",
    title: "A workspace for evidence, not guesses.",
    intro: "See how supplied exports and verified observations are reviewed. This preview contains no customer records or example performance metrics.",
    disclaimer: "Sample-free preview. No customer data, live account feeds, performance metrics, or competitor results are shown.",
    views: [
      {
        id: "overview",
        label: "Workspace",
        icon: "chart",
        heading: "Search workspace",
        subheading: "No connected account data",
        kpis: [
          { label: "Keyword export", value: "No file loaded" },
          { label: "Rank export", value: "No file loaded" },
          { label: "Traffic comparison", value: "Not entered" },
          { label: "Saved analyses", value: "Not loaded" },
        ],
        list: {
          label: "Data boundaries",
          rows: [
            { tag: "Input", text: "Review the sources your team provides." },
            { tag: "Scope", text: "Keyword and rank exports are processed locally in your browser." },
            { tag: "Status", text: "No live rank or review-provider results are displayed." },
          ],
        },
      },
      {
        id: "ai-visibility",
        label: "AI visibility",
        icon: "sparkles",
        heading: "AI visibility review",
        subheading: "No verified observations loaded",
        kpis: [
          { label: "Prompt source", value: "Not supplied" },
          { label: "Answer evidence", value: "Not loaded" },
          { label: "Citation metrics", value: "Not calculated" },
        ],
        list: {
          label: "Evidence status",
          rows: [
            { tag: "Source", text: "No verified AI-answer observations are connected." },
            { tag: "Claims", text: "No mention counts or citation results are fabricated." },
            { tag: "Compare", text: "No competitor results are shown without source evidence." },
          ],
        },
      },
      {
        id: "keywords",
        label: "Keyword Data Review",
        icon: "search",
        heading: "Review a keyword export",
        subheading: "Browser-local · no file loaded",
        kpis: [
          { label: "Source", value: "No CSV loaded" },
          { label: "Metrics", value: "Only as supplied" },
          { label: "Processing", value: "In this browser" },
        ],
        list: {
          label: "How it works",
          rows: [
            { tag: "Input", text: "Choose a keyword export you already have." },
            { tag: "Fields", text: "Only columns and metrics present in the file are shown." },
            { tag: "Privacy", text: "The file is not uploaded by this review tool." },
          ],
        },
      },
      {
        id: "rank-tracking",
        label: "Rank Position Review",
        icon: "chart",
        heading: "Review a rank export",
        subheading: "Browser-local · no file loaded",
        kpis: [
          { label: "Source", value: "No CSV loaded" },
          { label: "Positions", value: "Only as supplied" },
          { label: "Forecasts", value: "Not generated" },
        ],
        list: {
          label: "How it works",
          rows: [
            { tag: "Input", text: "Choose a rank export you already have." },
            { tag: "Scope", text: "Missing positions remain missing; no live tracking is performed." },
            { tag: "Privacy", text: "The file is processed locally in your browser." },
          ],
        },
      },
      {
        id: "traffic-analytics",
        label: "Traffic analytics",
        icon: "chart",
        heading: "Manual traffic comparison",
        subheading: "No metrics entered",
        kpis: [
          { label: "Clicks", value: "Not supplied" },
          { label: "Impressions", value: "Not supplied" },
          { label: "CTR", value: "Not supplied" },
        ],
        list: {
          label: "How it works",
          rows: [
            { tag: "Source", text: "Enter the source and two period labels." },
            { tag: "Metrics", text: "Compare values your team supplies." },
            { tag: "Scope", text: "No analytics provider is connected by this tool." },
          ],
        },
      },
    ],
  },

  // Only real, permissioned customer statements with a checkable source may
  // be added here. Until then the proof section renders nothing.
  proof: { eyebrow: "Customers", title: "Teams finding their way into the answer.", entries: [] },

  // Only awards with a public proof URL may be added. Swap in the issuer's
  // official embed once Nuxtron holds one. Until then the row renders nothing.
  trust: { title: "Recognised by", badges: [] },

  problemSolution: {
    eyebrow: "Why it matters now",
    title: "Ranking well is no longer the whole story.",
    problems: [
      {
        title: "Invisible in the answer",
        body: "Buyers ask AI assistants for recommendations. If the model never mentions you, a page-one ranking does not reach them.",
      },
      {
        title: "Blind to what AI says",
        body: "Rank trackers report positions. They cannot tell you whether an assistant cites you, ignores you or describes you wrongly.",
      },
      {
        title: "Insight with nowhere to go",
        body: "Audits, keyword lists and visibility reports live in separate tools, so the fix waits for someone to copy it across.",
      },
    ],
    solution: {
      title: "Search and AI visibility in one workspace, with the next step attached.",
      body: "Nuxtron SEO organizes the evidence your team provides and turns validated findings into reviewable briefs and plans.",
      cta: { label: "Start with Nuxtron SEO", href: START },
    },
  },

  useCases: {
    eyebrow: "How teams use it",
    title: "From a question to the page that answers it.",
    intro: "A typical week in Nuxtron SEO, from spotting a gap to shipping the page that closes it.",
    steps: [
      {
        id: "find",
        label: "Find the gap",
        icon: "search",
        title: "See where AI answers leave you out.",
        body: "Review question context and verified AI-answer evidence when it is available; this page does not supply unverified competitor results.",
        panel: {
          kind: "answer",
          caption: "Prompt research",
          items: [
            "Question supplied by your team.",
            "No verified AI answer has been loaded.",
            "Add a source before comparing brands or citations.",
          ],
        },
      },
      {
        id: "measure",
        label: "Review supplied data",
        icon: "chart",
        title: "Keep the source beside every keyword row.",
        body: "Keyword Data Review reads a CSV you provide in this browser and shows only fields present in that export; it does not estimate demand or competitor gaps.",
        panel: {
          kind: "rows",
          caption: "Fields shown when supplied",
          items: ["Keyword · as supplied", "Search volume · if present", "Difficulty · if present", "Export source and date"],
        },
      },
      {
        id: "brief",
        label: "Brief the content",
        icon: "file-text",
        title: "Turn reviewed evidence into a brief.",
        body: "Draft content from a user-provided brief, then verify every factual claim against its source before publication.",
        panel: {
          kind: "rows",
          caption: "Content brief",
          items: [
            "Answer the core question in the first 80 words",
            "Cover multi-state filing and registration steps",
            "Add a comparison table with clear criteria",
            "Cite primary sources for every statistic",
          ],
        },
      },
      {
        id: "fix",
        label: "Plan the next step",
        icon: "shield",
        title: "Review evidence before changing a page.",
        body: "Use supplied rank exports and manually entered traffic metrics to inform a plan. No live position monitoring or publishing is performed here.",
        panel: {
          kind: "rows",
          caption: "Review checklist",
          items: [
            "Confirm the source and date for each metric",
            "Check the target page and intended audience",
            "Record an owner and approval before changes",
            "Nothing is published automatically",
          ],
        },
      },
    ],
  },

  capabilities: {
    eyebrow: "What's inside",
    title: "Everything search and AI visibility needs.",
    intro: "Nine areas, one login. Open any of them to see what's included.",
    blocks: [
      {
        id: "ai-visibility",
        icon: "sparkles",
        title: "AI visibility",
        summary: "See how AI assistants mention, cite and describe your brand.",
        bullets: ["AI Visibility Overview", "Prompt Research", "Brand Performance", "Competitor Research"],
        link: { label: "See all features", href: "/features" },
      },
      {
        id: "rank-tracking",
        icon: "chart",
        title: "Rank position review",
        summary: "Review a rank export you already have; Nuxtron does not perform live position monitoring or forecasting.",
        bullets: ["Browser-local CSV review", "Top-10 and median from supplied positions", "Missing ranks are not estimated"],
        link: { label: "See all features", href: "/features" },
      },
      {
        id: "keyword-research",
        icon: "search",
        title: "Keyword data review",
        summary: "Review a keyword export you already have; no search metrics or competitor gaps are generated.",
        bullets: ["Browser-local CSV review", "Optional export source and market labels", "Provided metrics only"],
        link: { label: "See all features", href: "/features" },
      },
      {
        id: "traffic-analytics",
        icon: "chart",
        title: "Traffic Analytics",
        summary: "Compare manually supplied search metrics across two labeled periods.",
        bullets: ["Clicks and impressions", "Click-through-rate movement", "Average position difference"],
        link: { label: "See all features", href: "/features" },
      },
      {
        id: "backlinks",
        icon: "link",
        title: "Backlinks",
        summary: "Understand your link profile and find the next links worth earning.",
        bullets: ["Backlinks", "Link Building Tool", "Domain Overview"],
        link: { label: "See all features", href: "/features" },
      },
      {
        id: "content-optimisation",
        icon: "file-text",
        title: "Content optimisation",
        summary: "Brief, write and check content against what search and AI reward.",
        bullets: ["Content Brief", "SEO Writing Assistant", "AI SEO Analysis", "AI Content Generator"],
        link: { label: "See all features", href: "/features" },
      },
      {
        id: "market",
        icon: "users",
        title: "Market and traffic",
        summary: "Size the market and benchmark your traffic against competitors.",
        bullets: ["Market Explorer", "Traffic Analytics", "Industry Benchmarks", "Growth Quadrant"],
        link: { label: "See all features", href: "/features" },
      },
      {
        id: "reporting",
        icon: "inbox",
        title: "Analysis & history",
        summary: "Review saved analyses and compare traffic values you provide.",
        bullets: ["Analysis History", "Traffic Analytics"],
        link: { label: "See all features", href: "/features" },
      },
    ],
  },

  productHub: {
    eyebrow: "Nuxtron SEO",
    title: "Four workspaces, one view of visibility.",
    intro: "Each area of the dashboard has a clear job. Together they cover classic search and AI answers.",
    cards: [
      {
        id: "seo",
        icon: "search",
        name: "Search",
        tagline: "Keyword exports, manual traffic comparisons and saved SEO analyses.",
        features: ["Keyword Data Review", "Traffic Analytics", "Analysis History"],
        link: { label: "Start with Search", href: START },
      },
      {
        id: "ai",
        icon: "sparkles",
        name: "AI",
        tagline: "How AI assistants see and describe your brand.",
        features: ["AI Visibility Overview", "Prompt Research", "Brand Performance", "Answer Engine Optimization"],
        link: { label: "Start with AI visibility", href: START },
      },
      {
        id: "traffic",
        icon: "chart",
        name: "Traffic",
        tagline: "Market size and competitor traffic.",
        features: ["Market Explorer", "Traffic Analytics", "Industry Benchmarks", "Trending Now"],
        link: { label: "Start with Traffic", href: START },
      },
    ],
  },

  agents: {
    eyebrow: "AI agents",
    title: "Agents that turn findings into plans.",
    intro: "Give them a goal. They return a plan you can review before anything changes.",
    agents: [
      {
        id: "seo-agent",
        name: "SEO Agent",
        role: "Plans the work",
        body: "Takes an SEO goal and a domain and returns a phased plan: the tasks, the tool for each, priority, effort and the KPIs to watch.",
        actions: ["Break a goal into phases", "Estimate effort", "Pick the KPIs"],
        link: { label: "Try the SEO Agent", href: START },
      },
      {
        id: "ira",
        name: "IRA",
        role: "Answers and acts",
        body: "An assistant that routes questions to the AI provider you choose, grounds answers in your workspace, and hands off to the right tool.",
        actions: ["Answer from workspace data", "Choose the AI provider", "Open the right tool"],
        link: { label: "Meet IRA", href: START },
      },
      {
        id: "ai-seo-assistant",
        name: "Answer Engine Optimization",
        role: "Reviews the page",
        body: "Analyses a page against the topic it should rank for and suggests the changes most likely to improve search and AI visibility.",
        actions: ["Score a page", "Suggest fixes", "Draft improved passages"],
        link: { label: "Try Answer Engine Optimization", href: START },
      },
    ],
  },

  research: {
    eyebrow: "Research and guides",
    title: "What we're learning about AI search.",
    intro: "Notes from the team on how answer engines choose what to cite.",
    categories: ["SEO & AI visibility"],
    cta: { label: "Read the blog", href: "/blog" },
  },

  faq: [
    {
      q: "What does Nuxtron SEO track in AI answers?",
      a: "Answer Engine Insights checks how ChatGPT, Perplexity, Gemini, Claude and Brave Search AI mention your brand for the prompts you choose, and records which answers cite you. Each engine needs its provider credentials configured for your workspace.",
    },
    {
      q: "Does it replace my SEO platform?",
      a: "It brings together browser-local keyword-export review, manually entered traffic comparisons, saved analyses, and AI-visibility workflows. Provider-backed search metrics and competitor gaps are not currently available.",
    },
    {
      q: "What's the difference between Nuxtron SEO and Nuxtron Marketing?",
      a: "Nuxtron SEO is for search and AI visibility. Nuxtron Marketing is for content, social channels and customer work. You choose one when you sign in, and the dashboard shows that product's tools.",
    },
    {
      q: "How do I choose a plan?",
      a: "The pricing page lists the plans and the usage each includes. Review the limits there before activating a subscription.",
    },
  ],

  closing: {
    eyebrow: "Get started",
    titleLead: "See what the answers say.",
    titleAccent: "Then change them.",
    primaryCta: { label: "Start with Nuxtron SEO", href: START },
    secondaryCta: { label: "Talk to our team", href: "/contact" },
  },
};
