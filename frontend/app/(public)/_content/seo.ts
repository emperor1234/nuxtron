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
      "Nuxtron SEO gives teams AI-assisted tools for on-page optimization, content briefs and answer-engine visibility. You provide the content and context; every result is labelled as AI guidance, never as search-engine data.",
    primaryCta: { label: "Start with Nuxtron SEO", href: START },
    secondaryCta: { label: "See it working", href: "#demo" },
    explainer: "seo",
    coverageLabel: "AI engines in research scope",
    coverage: ["ChatGPT", "Perplexity", "Gemini", "Claude", "Brave Search AI"],
  },

  demo: {
    eyebrow: "Product tour",
    title: "A workspace for evidence, not guesses.",
    intro: "See how an analysis is set up and reviewed. This preview contains no customer records or example performance metrics.",
    disclaimer: "Sample-free preview. No customer data, live account feeds, performance metrics, or competitor results are shown.",
    views: [
      {
        id: "overview",
        label: "Workspace",
        icon: "chart",
        heading: "Search workspace",
        subheading: "No connected account data",
        kpis: [
          { label: "Content analysed", value: "Not supplied" },
          { label: "Briefs", value: "None yet" },
          { label: "Answer-engine checks", value: "None yet" },
          { label: "Saved analyses", value: "Not loaded" },
        ],
        list: {
          label: "Data boundaries",
          rows: [
            { tag: "Input", text: "Paste the content and context you want analysed." },
            { tag: "Scope", text: "Results are guidance from your input, not search-engine measurements." },
            { tag: "Status", text: "Every analysis is labelled with how it was produced." },
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
        id: "on-page",
        label: "On-Page Optimizer",
        icon: "search",
        heading: "Optimize a page",
        subheading: "No page analysed yet",
        kpis: [
          { label: "Page", value: "Not supplied" },
          { label: "Focus keyword", value: "Not set" },
          { label: "Measurements", value: "From your text" },
        ],
        list: {
          label: "How it works",
          rows: [
            { tag: "Input", text: "Paste the page copy and a focus keyword." },
            { tag: "Output", text: "Keyword use, word count, readability and prioritized fixes." },
            { tag: "Scope", text: "Computed from the text you paste; nothing is crawled." },
          ],
        },
      },
      {
        id: "content-brief",
        label: "Content Brief",
        icon: "file-text",
        heading: "Brief the content",
        subheading: "No brief created yet",
        kpis: [
          { label: "Topic", value: "Not supplied" },
          { label: "Keywords", value: "Not supplied" },
          { label: "Outline", value: "Not generated" },
        ],
        list: {
          label: "How it works",
          rows: [
            { tag: "Input", text: "Give a topic, keywords and audience." },
            { tag: "Output", text: "A writer-ready outline with questions to answer." },
            { tag: "Review", text: "Verify every factual claim before publishing." },
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
        label: "Optimize the page",
        icon: "chart",
        title: "Fix what holds the page back.",
        body: "The On-Page Optimizer measures keyword use, word count and readability in the copy you paste, then lists the fixes in priority order.",
        panel: {
          kind: "rows",
          caption: "What you get",
          items: ["Keyword density and word count", "Readability", "Title and meta guidance", "Quick wins in priority order"],
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
        title: "Review the plan before changing a page.",
        body: "Turn a goal into a phased plan with the Workflow Planner. Nothing is published or changed on your site automatically.",
        panel: {
          kind: "rows",
          caption: "Review checklist",
          items: [
            "Check the target page and intended audience",
            "Confirm each claim against your own data",
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
        title: "AI answer engines",
        summary: "Shape content so answer engines can read, extract and cite it.",
        bullets: ["Answer Engine (AEO)", "Generative Engine (GEO)", "AI Overviews (AIO)", "Prompt Research"],
        link: { label: "See all features", href: "/features" },
      },
      {
        id: "on-page",
        icon: "search",
        title: "On-page optimization",
        summary: "Measure keyword use, readability and structure in the copy you paste.",
        bullets: ["On-Page Optimizer", "Schema Generator", "Internal Linking", "E-E-A-T"],
        link: { label: "See all features", href: "/features" },
      },
      {
        id: "content-optimisation",
        icon: "file-text",
        title: "Content",
        summary: "Brief, plan and draft content, then check it before it goes live.",
        bullets: ["Content Brief", "AI Article Writer", "Content Planner", "Topical Map"],
        link: { label: "See all features", href: "/features" },
      },
      {
        id: "backlinks",
        icon: "link",
        title: "Links and strategy",
        summary: "Plan link-earning and sequence the work that moves results.",
        bullets: ["Backlink Intelligence", "Link Building", "Growth Playbooks", "Workflow Planner"],
        link: { label: "See all features", href: "/features" },
      },
      {
        id: "ops",
        icon: "chart",
        title: "Operations",
        summary: "Understand crawler activity and design experiments you can run.",
        bullets: ["Log File Analysis", "A/B Test Design", "Site Migration", "AI Crawler Visibility"],
        link: { label: "See all features", href: "/features" },
      },
      {
        id: "reporting",
        icon: "inbox",
        title: "Analysis history",
        summary: "Every analysis you run is saved so you can return to it.",
        bullets: ["Analysis History", "Benchmarks"],
        link: { label: "See all features", href: "/features" },
      },
    ],
  },

  productHub: {
    eyebrow: "Nuxtron SEO",
    title: "Three workspaces, one view of visibility.",
    intro: "Each area of the dashboard has a clear job. Together they cover classic search and AI answers.",
    cards: [
      {
        id: "seo",
        icon: "search",
        name: "Optimize",
        tagline: "Pages, content and structure, analysed from what you provide.",
        features: ["On-Page Optimizer", "Content Brief", "Schema Generator"],
        link: { label: "Start optimizing", href: START },
      },
      {
        id: "ai",
        icon: "sparkles",
        name: "AI answers",
        tagline: "How answer engines can read and cite your content.",
        features: ["Answer Engine (AEO)", "Generative Engine (GEO)", "Prompt Research"],
        link: { label: "Start with AI answers", href: START },
      },
      {
        id: "traffic",
        icon: "chart",
        name: "Strategy",
        tagline: "Plans, playbooks and experiments you can act on.",
        features: ["Workflow Planner", "Growth Playbooks", "A/B Test Design"],
        link: { label: "Start planning", href: START },
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
