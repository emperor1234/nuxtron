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
      "Nuxtron SEO tracks how your brand ranks in search and how AI assistants describe it — then shows you what to fix, write and build next.",
    primaryCta: { label: "Start with Nuxtron SEO", href: START },
    secondaryCta: { label: "See it working", href: "#demo" },
    explainer: "seo",
    coverageLabel: "Brand mentions tracked in",
    coverage: ["ChatGPT", "Perplexity", "Gemini", "Claude", "Brave Search AI"],
  },

  demo: {
    eyebrow: "Product tour",
    title: "One view of search and AI visibility.",
    intro: "Follow the short tour, pause at any time, or select a view. Each panel is a real Nuxtron SEO screen.",
    views: [
      {
        id: "overview",
        label: "Overview",
        icon: "chart",
        heading: "Visibility overview",
        subheading: "customer.com · last 28 days",
        kpis: [
          { label: "AI answer share", value: "18%", delta: "+2.1 pts" },
          { label: "Tracked keywords", value: "1,240", delta: "+86" },
          { label: "Site health", value: "87", delta: "+4" },
          { label: "Referring domains", value: "932", delta: "-3" },
        ],
        chart: {
          label: "Brand mentions by engine",
          bars: [
            { label: "ChatGPT", value: 64 },
            { label: "Perplexity", value: 48 },
            { label: "Gemini", value: 37 },
            { label: "Claude", value: 29 },
            { label: "Brave AI", value: 18 },
          ],
        },
      },
      {
        id: "ai-visibility",
        label: "AI visibility",
        icon: "sparkles",
        heading: "AI visibility",
        subheading: "Prompts where your brand appears, and where a competitor does instead",
        kpis: [
          { label: "Prompts monitored", value: "312" },
          { label: "Cited as a source", value: "41", delta: "+7" },
          { label: "Competitor-only answers", value: "58", delta: "-5" },
        ],
        list: {
          label: "Prompts to win next",
          rows: [
            { tag: "Gap", text: "best payroll software for small teams" },
            { tag: "Gap", text: "payroll vs PEO for a 20-person company" },
            { tag: "Cited", text: "how to run payroll in two states" },
            { tag: "Gap", text: "payroll software with time tracking" },
          ],
        },
      },
      {
        id: "keywords",
        label: "Keywords",
        icon: "search",
        heading: "Position tracking",
        subheading: "Desktop · United States",
        kpis: [
          { label: "Top 3 positions", value: "142", delta: "+12" },
          { label: "Average position", value: "11.4", delta: "-0.8" },
          { label: "Estimated traffic", value: "38.2k" },
        ],
        chart: {
          label: "Keywords by position range",
          bars: [
            { label: "1–3", value: 142 },
            { label: "4–10", value: 318 },
            { label: "11–20", value: 274 },
            { label: "21–50", value: 336 },
            { label: "51–100", value: 170 },
          ],
        },
      },
      {
        id: "site-audit",
        label: "Site audit",
        icon: "shield",
        heading: "Site audit",
        subheading: "Last crawl: 4,812 pages",
        kpis: [
          { label: "Health score", value: "87" },
          { label: "Errors", value: "23", delta: "-9" },
          { label: "Warnings", value: "214" },
        ],
        list: {
          label: "Fix first",
          rows: [
            { tag: "Error", text: "17 pages return 4xx from internal links" },
            { tag: "Error", text: "6 pages missing a canonical tag" },
            { tag: "Warning", text: "48 pages with duplicate title tags" },
            { tag: "Notice", text: "Structured data missing on 12 product pages" },
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
      body: "Nuxtron SEO puts rankings, site health and AI answer coverage side by side, and turns each gap into a brief, a fix or a task.",
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
        body: "Prompt Research and Brand Performance show the questions your buyers ask and which brands the assistants recommend instead.",
        panel: {
          kind: "answer",
          caption: "Prompt research",
          items: [
            "What's the best payroll software for a 20-person company?",
            "Gusto and Rippling come up most for small teams. [Perplexity]",
            "Several reviews also mention ease of multi-state filing. [ChatGPT]",
            "Your brand is not mentioned in this answer.",
          ],
        },
      },
      {
        id: "measure",
        label: "Size the opportunity",
        icon: "chart",
        title: "Know which gaps are worth closing.",
        body: "Keyword Gap and Organic Research weigh each topic by search demand and how often it already shows up in AI answers.",
        panel: {
          kind: "bars",
          caption: "Opportunity by topic",
          items: ["Multi-state payroll:82", "Payroll for startups:64", "Payroll vs PEO:51", "Time tracking:38"],
        },
      },
      {
        id: "brief",
        label: "Brief the content",
        icon: "file-text",
        title: "Turn the gap into a brief.",
        body: "Content Brief and the SEO Writing Assistant draft around the entities, questions and sources the answer engines lean on.",
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
        label: "Fix and track",
        icon: "shield",
        title: "Ship it clean, then watch it land.",
        body: "Site Audit catches the technical blockers before launch, and Position Tracking plus AI visibility show whether the page starts to earn its place.",
        panel: {
          kind: "rows",
          caption: "Before launch",
          items: [
            "Canonical tag set on the new page",
            "Internal links added from 6 related pages",
            "FAQ structured data validated",
            "Prompt added to AI visibility monitoring",
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
        title: "Rank tracking",
        summary: "Daily positions for the keywords that matter, by device and location.",
        bullets: ["Position Tracking", "Map Rank Tracker for local results", "Trend Predictor"],
        link: { label: "See all features", href: "/features" },
      },
      {
        id: "keyword-research",
        icon: "search",
        title: "Keyword research",
        summary: "Find the topics worth targeting and the gaps your competitors already own.",
        bullets: ["Organic Research", "Keyword Gap", "Keyword Strategy Builder", "Top Pages"],
        link: { label: "See all features", href: "/features" },
      },
      {
        id: "site-audit",
        icon: "shield",
        title: "Technical SEO",
        summary: "Crawl the site, rank the issues and confirm the fixes.",
        bullets: ["Site Audit", "Log File Analyzer", "Site Performance and Core Web Vitals"],
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
        id: "local",
        icon: "map-pin",
        title: "Local SEO",
        summary: "Keep listings accurate and see how you rank street by street.",
        bullets: ["Listing Management", "Map Rank Tracker", "Local Heatmap", "Review Management"],
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
        title: "Reporting",
        summary: "Send the numbers on a schedule instead of assembling them by hand.",
        bullets: ["Auto Reports", "Smart Scheduler", "Citation analytics"],
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
        tagline: "Rankings, keywords, links and site health.",
        features: ["Site Audit", "Position Tracking", "Keyword Gap", "Backlinks"],
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
      {
        id: "local",
        icon: "map-pin",
        name: "Local",
        tagline: "Listings, reviews and map rankings.",
        features: ["Listing Management", "Map Rank Tracker", "Local Heatmap", "Review Management"],
        link: { label: "Start with Local", href: START },
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
      a: "It covers the core of one — site audits, position tracking, keyword and backlink research, local SEO and reporting — alongside AI visibility, so most teams run them from one place.",
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
