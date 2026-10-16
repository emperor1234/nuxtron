/**
 * One spec per SEO tool. Field names, limits and requirements mirror the
 * request models in backend/fastapi/app/domains/seo/platform/schemas.py, and
 * `endpoint` is the real FastAPI route. Vendor-stack switches (model names,
 * framework toggles) are deliberately not exposed: the backend owns them.
 */

export type FieldKind = "text" | "textarea" | "number" | "select" | "list" | "toggle";

export type FieldSpec = {
  name: string;
  label: string;
  kind: FieldKind;
  required?: boolean;
  placeholder?: string;
  hint?: string;
  max?: number;
  min?: number;
  rows?: number;
  options?: ReadonlyArray<{ value: string; label: string }>;
  initial?: string | number | boolean;
};

export type ToolSpec = {
  slug: string;
  title: string;
  summary: string;
  endpoint: string;
  fields: readonly FieldSpec[];
  /** At least one field in each group must be filled. */
  oneOf?: ReadonlyArray<readonly string[]>;
  /** Shown above the form when the tool needs context the user should know. */
  note?: string;
  submitLabel?: string;
};

const opts = (...values: string[]) => values.map((value) => ({ value, label: value.charAt(0).toUpperCase() + value.slice(1) }));

const content = (max: number, hint?: string): FieldSpec => ({
  name: "content",
  label: "Content",
  kind: "textarea",
  required: true,
  rows: 10,
  max,
  placeholder: "Paste the page copy or draft to analyze",
  hint: hint ?? `Up to ${max.toLocaleString()} characters.`,
});

const notes: FieldSpec = {
  name: "notes",
  label: "Notes",
  kind: "textarea",
  rows: 3,
  max: 1000,
  placeholder: "Anything the analysis should take into account (optional)",
};

const topic = (hint?: string): FieldSpec => ({
  name: "topic",
  label: "Topic",
  kind: "text",
  required: true,
  max: 300,
  placeholder: "e.g. trail running shoes for beginners",
  hint,
});

export const SEO_TOOLS: Record<string, ToolSpec> = {
  "on-page": {
    slug: "on-page",
    title: "On-Page Optimizer",
    summary: "Measure keyword use, word count and readability in your page copy and get prioritized fixes.",
    endpoint: "/seo-platform/on-page/analyze",
    fields: [
      { name: "url", label: "Page URL", kind: "text", required: true, max: 500, placeholder: "https://example.com/page" },
      { name: "focus_keyword", label: "Focus keyword", kind: "text", required: true, max: 200, placeholder: "trail running shoes" },
      { name: "content", label: "Page content", kind: "textarea", rows: 10, max: 10000, placeholder: "Paste the page copy", hint: "Measurements are computed from the text you paste." },
    ],
  },
  writer: {
    slug: "writer",
    title: "AI Article Writer",
    summary: "Draft an SEO article from a topic, keywords and an optional brief.",
    endpoint: "/seo-platform/content/write",
    fields: [
      topic(),
      { name: "keywords", label: "Keywords", kind: "list", placeholder: "One per line", hint: "Primary keyword first." },
      { name: "word_count", label: "Target length (words)", kind: "number", min: 300, max: 3000, initial: 1200 },
      { name: "tone", label: "Tone", kind: "select", options: opts("professional", "friendly", "authoritative", "conversational"), initial: "professional" },
      { name: "brief", label: "Brief", kind: "textarea", rows: 4, placeholder: "Audience, angle, must-cover points (optional)" },
    ],
    submitLabel: "Write article",
  },
  "content-brief": {
    slug: "content-brief",
    title: "Content Brief",
    summary: "Build a writer-ready brief with outline, questions and linking guidance for a keyword.",
    endpoint: "/seo-platform/content/brief",
    fields: [
      topic(),
      { name: "keywords", label: "Keywords", kind: "list", placeholder: "One per line" },
      { name: "word_count", label: "Target length (words)", kind: "number", min: 300, max: 5000, initial: 1500 },
      { name: "audience", label: "Audience", kind: "text", placeholder: "e.g. first-time trail runners" },
    ],
    submitLabel: "Build brief",
  },
  "content-creation-blogging": {
    slug: "content-creation-blogging",
    title: "Content Planner",
    summary: "Plan pillar topics, a publishing calendar and promotion for a blog.",
    endpoint: "/seo-platform/content-creation-blogging/plan",
    fields: [
      topic(),
      { name: "content_pillars", label: "Content pillars", kind: "list", placeholder: "One per line" },
      { name: "target_keywords", label: "Target keywords", kind: "list", placeholder: "One per line" },
      { name: "word_count_target", label: "Target length (words)", kind: "number", min: 300, max: 5000, initial: 2000 },
      { name: "publication_frequency", label: "Publishing cadence", kind: "select", options: opts("daily", "weekly", "biweekly", "monthly"), initial: "weekly" },
      { name: "include_multimedia_plan", label: "Include a multimedia plan", kind: "toggle", initial: true },
      { name: "seo_brief", label: "SEO brief", kind: "textarea", rows: 3, max: 3000 },
      notes,
    ],
    submitLabel: "Build plan",
  },
  landing: {
    slug: "landing",
    title: "Landing Page Brief",
    summary: "Generate a conversion-focused landing page brief with hero copy, sections and FAQ.",
    endpoint: "/seo-platform/landing/generate",
    fields: [
      { name: "product_name", label: "Product or offer", kind: "text", required: true, max: 200 },
      { name: "target_keyword", label: "Target keyword", kind: "text", required: true, max: 200 },
      { name: "audience", label: "Audience", kind: "text", max: 200, placeholder: "e.g. small business owners" },
      notes,
    ],
    submitLabel: "Generate brief",
  },
  "topical-map": {
    slug: "topical-map",
    title: "Topical Map",
    summary: "Cluster a seed topic into pillar and supporting pages.",
    endpoint: "/seo-platform/topical-map/build",
    fields: [
      { name: "seed_topic", label: "Seed topic", kind: "text", required: true, max: 300, placeholder: "e.g. trail running" },
      { name: "domain", label: "Domain", kind: "text", max: 300, placeholder: "example.com" },
      { name: "depth", label: "Depth (levels)", kind: "number", min: 1, max: 4, initial: 2 },
      notes,
    ],
    submitLabel: "Build map",
  },
  "brand-voice": {
    slug: "brand-voice",
    title: "Brand Voice Rewrite",
    summary: "Rewrite copy so it reads in your brand voice while keeping the SEO signals.",
    endpoint: "/seo-platform/brand-voice/rewrite",
    fields: [
      content(5000),
      { name: "brand_name", label: "Brand name", kind: "text", max: 300 },
      { name: "tone", label: "Tone", kind: "select", options: opts("professional", "friendly", "authoritative", "playful", "technical"), initial: "professional" },
      { name: "target_audience", label: "Audience", kind: "text", max: 300 },
      notes,
    ],
    submitLabel: "Rewrite",
  },
  ecommerce: {
    slug: "ecommerce",
    title: "eCommerce SEO",
    summary: "Optimize a product title, description and structured data.",
    endpoint: "/seo-platform/ecommerce/optimize",
    fields: [
      { name: "product_name", label: "Product name", kind: "text", required: true, max: 300 },
      { name: "category", label: "Category", kind: "text" },
      { name: "description", label: "Current description", kind: "textarea", rows: 6, max: 3000 },
      { name: "keywords", label: "Keywords", kind: "list", placeholder: "One per line" },
    ],
    submitLabel: "Optimize product",
  },
  video: {
    slug: "video",
    title: "Video SEO",
    summary: "Optimize a video's title, description, tags and chapters.",
    endpoint: "/seo-platform/video/optimize",
    fields: [
      { name: "title", label: "Video title", kind: "text", required: true, max: 300 },
      { name: "platform", label: "Platform", kind: "select", options: opts("youtube", "tiktok", "vimeo", "instagram"), initial: "youtube" },
      { name: "description", label: "Description", kind: "textarea", rows: 5, max: 5000 },
      { name: "transcript", label: "Transcript", kind: "textarea", rows: 8, max: 10000, hint: "Used to propose chapters and tags." },
      { name: "keywords", label: "Keywords", kind: "list", placeholder: "One per line" },
    ],
    submitLabel: "Optimize video",
  },
  schemas: {
    slug: "schemas",
    title: "Schema Generator",
    summary: "Generate JSON-LD structured data for a page.",
    endpoint: "/seo-platform/schemas/generate",
    fields: [
      {
        name: "schema_type",
        label: "Schema type",
        kind: "select",
        options: ["Article", "FAQPage", "HowTo", "Product", "LocalBusiness", "Organization", "Person", "VideoObject"].map((value) => ({ value, label: value })),
        initial: "Article",
      },
      { name: "page_url", label: "Page URL", kind: "text", placeholder: "https://example.com/page" },
      { name: "content", label: "Page content", kind: "textarea", rows: 8, max: 5000 },
    ],
    oneOf: [["content", "page_url"]],
    submitLabel: "Generate schema",
  },
  "internal-linking": {
    slug: "internal-linking",
    title: "Internal Linking",
    summary: "Suggest internal links between your pages.",
    endpoint: "/seo-platform/internal-linking/suggest",
    fields: [
      { name: "page_url", label: "Page URL", kind: "text", max: 500, placeholder: "https://example.com/page" },
      { name: "site_url", label: "Site URL", kind: "text", max: 500, placeholder: "https://example.com" },
      { name: "page_content", label: "Page content", kind: "textarea", rows: 8, max: 5000 },
      { name: "target_urls", label: "Pages to link to", kind: "list", placeholder: "One URL per line" },
      notes,
    ],
    oneOf: [["page_url", "site_url"]],
    submitLabel: "Suggest links",
  },
  aeo: {
    slug: "aeo",
    title: "Answer Engine Optimization",
    summary: "Shape content so answer engines can quote it, and find featured-snippet opportunities.",
    endpoint: "/seo-platform/aeo/optimize",
    fields: [
      content(8000),
      topic(),
      { name: "target_questions", label: "Target questions", kind: "list", placeholder: "One per line" },
      { name: "entity_targets", label: "Entities to cover", kind: "list", placeholder: "One per line" },
      { name: "schema_types", label: "Schema types", kind: "list", placeholder: "FAQPage, HowTo…" },
    ],
  },
  geo: {
    slug: "geo",
    title: "Generative Engine Optimization",
    summary: "Improve how likely generative answers are to cite your content.",
    endpoint: "/seo-platform/geo/optimize",
    fields: [
      content(8000),
      topic(),
      { name: "target_engines", label: "Answer engines", kind: "list", placeholder: "ChatGPT\nPerplexity\nGemini" },
      { name: "serp_context", label: "SERP context", kind: "textarea", rows: 3, max: 3000, hint: "Paste what currently ranks, if you have it." },
      { name: "site_content_context", label: "Site context", kind: "textarea", rows: 3, max: 3000 },
    ],
  },
  aio: {
    slug: "aio",
    title: "AI Overviews (AIO)",
    summary: "Score how easily AI summaries can read and extract your content.",
    endpoint: "/seo-platform/aio/score",
    fields: [content(8000), { name: "topic", label: "Topic", kind: "text", max: 300 }],
  },
  llmo: {
    slug: "llmo",
    title: "LLM Optimization (LLMO)",
    summary: "Assess how language models are likely to represent your brand and where facts are at risk.",
    endpoint: "/seo-platform/llmo/analyze",
    fields: [
      { name: "brand", label: "Brand", kind: "text", required: true, max: 200 },
      { name: "domain", label: "Domain", kind: "text", placeholder: "example.com" },
      { name: "key_claims", label: "Key claims", kind: "list", placeholder: "Facts models should repeat correctly" },
      { name: "competitors", label: "Competitors", kind: "list", placeholder: "One per line" },
    ],
    note: "This needs the AI model. If none is connected you will see that instead of a guess.",
  },
  gxo: {
    slug: "gxo",
    title: "Google AI (GXO)",
    summary: "Estimate readiness for AI Overview citations and what to fix first.",
    endpoint: "/seo-platform/gxo/optimize",
    fields: [content(8000), topic(), { name: "url", label: "Page URL", kind: "text", placeholder: "https://example.com/page" }],
  },
  sageo: {
    slug: "sageo",
    title: "Search Intent (SAGEO)",
    summary: "Map search intent and plan how generative search should retrieve and answer.",
    endpoint: "/seo-platform/sageo/analyze",
    fields: [
      { name: "topic", label: "Topic", kind: "text", required: true, max: 300 },
      { name: "search_intent", label: "Primary intent", kind: "select", options: opts("informational", "commercial", "transactional", "navigational"), initial: "informational" },
      { name: "source_material", label: "Source material", kind: "textarea", rows: 6, max: 4000 },
      { name: "target_engines", label: "Answer engines", kind: "list", placeholder: "One per line" },
      notes,
    ],
  },
  "seo-ai": {
    slug: "seo-ai",
    title: "AI SEO Assistant",
    summary: "Keyword opportunities and content guidance for a domain and primary keyword.",
    endpoint: "/seo-platform/seo-ai/analyze",
    fields: [
      { name: "domain", label: "Domain", kind: "text", required: true, max: 300, placeholder: "example.com" },
      { name: "primary_keyword", label: "Primary keyword", kind: "text", required: true, max: 200 },
      { name: "business_goal", label: "Business goal", kind: "text", max: 200, placeholder: "e.g. grow trial signups" },
      { name: "content_excerpt", label: "Content excerpt", kind: "textarea", rows: 6, max: 4000 },
      notes,
    ],
  },
  entity: {
    slug: "entity",
    title: "Entity SEO",
    summary: "Find the entities in your content, how they relate, and what is missing.",
    endpoint: "/seo-platform/entity/analyze",
    fields: [content(8000), { name: "topic", label: "Topic", kind: "text", max: 300 }],
  },
  eeat: {
    slug: "eeat",
    title: "E-E-A-T",
    summary: "Score experience, expertise, authority and trust signals in your content.",
    endpoint: "/seo-platform/eeat/score",
    fields: [
      content(8000),
      { name: "author_bio", label: "Author bio", kind: "textarea", rows: 3 },
      { name: "domain", label: "Domain", kind: "text", placeholder: "example.com" },
      { name: "niche", label: "Niche", kind: "text" },
    ],
  },
  msvo: {
    slug: "msvo",
    title: "Multi-surface (MSVO)",
    summary: "Plan visibility across search, social, video and AI surfaces.",
    endpoint: "/seo-platform/msvo/analyze",
    fields: [
      { name: "brand", label: "Brand", kind: "text", required: true, max: 200 },
      { name: "topic", label: "Topic", kind: "text", required: true, max: 300 },
      { name: "target_surfaces", label: "Target surfaces", kind: "list", placeholder: "Google\nYouTube\nTikTok" },
      { name: "owned_channels", label: "Owned channels", kind: "list", placeholder: "One per line" },
      notes,
    ],
  },
  vso: {
    slug: "vso",
    title: "Voice Search (VSO)",
    summary: "Optimize for spoken and assistant queries.",
    endpoint: "/seo-platform/vso/optimize",
    fields: [content(8000), topic(), { name: "local_area", label: "Local area", kind: "text", placeholder: "e.g. Austin, TX" }],
  },
  daeo: {
    slug: "daeo",
    title: "Decentralized (DAEO)",
    summary: "Readiness for federated and decentralized search and knowledge protocols.",
    endpoint: "/seo-platform/daeo/analyze",
    fields: [
      { name: "domain", label: "Domain", kind: "text", required: true, max: 300 },
      { name: "protocol_targets", label: "Protocols", kind: "list", placeholder: "One per line" },
      { name: "canonical_facts", label: "Canonical facts", kind: "list", placeholder: "Facts about your brand, one per line" },
      { name: "federation_notes", label: "Federation notes", kind: "textarea", rows: 3, max: 3000 },
      notes,
    ],
  },
  peao: {
    slug: "peao",
    title: "Predictive (PEAO)",
    summary: "Scenario planning for ranking volatility from the signals you provide.",
    endpoint: "/seo-platform/peao/analyze",
    fields: [
      { name: "domain", label: "Domain", kind: "text", required: true, max: 300 },
      { name: "primary_keyword", label: "Primary keyword", kind: "text", required: true, max: 200 },
      { name: "recent_signals", label: "Recent signals", kind: "textarea", rows: 5, max: 3000, hint: "Ranking moves, algorithm updates, traffic changes you have observed." },
      { name: "forecast_horizon_days", label: "Horizon (days)", kind: "number", min: 7, max: 365, initial: 30 },
      notes,
    ],
  },
  cxao: {
    slug: "cxao",
    title: "Conversational (CXAO)",
    summary: "Improve how an assistant answers a conversation, and where users get stuck.",
    endpoint: "/seo-platform/cxao/analyze",
    fields: [
      { name: "assistant_surface", label: "Assistant surface", kind: "text", max: 120, initial: "chat_assistant" },
      { name: "primary_intent", label: "Primary intent", kind: "text", required: true, max: 300 },
      { name: "conversation_context", label: "Conversation", kind: "textarea", required: true, rows: 8, max: 4000, placeholder: "Paste a representative conversation" },
      { name: "success_criteria", label: "Success criteria", kind: "list", placeholder: "One per line" },
    ],
  },
  sxo: {
    slug: "sxo",
    title: "Search Experience (SXO)",
    summary: "Align page experience with the intent that brings people to it.",
    endpoint: "/seo-platform/sxo/analyze",
    fields: [
      { name: "url", label: "Page URL", kind: "text", required: true, max: 500 },
      { name: "content", label: "Page content", kind: "textarea", rows: 8, max: 8000 },
      { name: "keywords", label: "Keywords", kind: "list", placeholder: "One per line" },
    ],
  },
  ux: {
    slug: "ux",
    title: "UX & Conversion",
    summary: "Review above-the-fold experience and conversion friction.",
    endpoint: "/seo-platform/ux/audit",
    fields: [
      { name: "url", label: "Page URL", kind: "text", required: true, max: 500 },
      { name: "page_type", label: "Page type", kind: "select", options: opts("landing", "product", "blog", "pricing", "checkout", "homepage"), initial: "landing" },
      { name: "traffic_source", label: "Main traffic source", kind: "select", options: opts("organic", "paid", "social", "email", "direct"), initial: "organic" },
      notes,
    ],
  },
  "news-discover": {
    slug: "news-discover",
    title: "News & Discover",
    summary: "Headline and freshness guidance for news and Discover surfaces.",
    endpoint: "/seo-platform/news-discover/analyze",
    fields: [
      { name: "domain", label: "Domain", kind: "text", required: true, max: 300 },
      { name: "recent_headlines", label: "Recent headlines", kind: "list", placeholder: "One per line" },
      { name: "focus_topics", label: "Focus topics", kind: "list", placeholder: "One per line" },
      notes,
    ],
  },
  "backlink-intelligence": {
    slug: "backlink-intelligence",
    title: "Backlink Intelligence",
    summary: "Strategy for earning links, based on the competitors you name.",
    endpoint: "/seo-platform/backlink-intelligence/analyze",
    fields: [
      { name: "domain", label: "Your domain", kind: "text", required: true, max: 300 },
      { name: "competitor_domains", label: "Competitor domains", kind: "list", placeholder: "One per line" },
      { name: "link_analysis_depth", label: "Depth", kind: "select", options: opts("quick", "standard", "deep"), initial: "standard" },
      notes,
    ],
    note: "This is strategy guidance, not a crawl of your backlink index.",
  },
  linkbuilding: {
    slug: "linkbuilding",
    title: "Link Building",
    summary: "Plan outreach angles and the kinds of sites worth approaching.",
    endpoint: "/seo-platform/linkbuilding/analyze",
    fields: [
      { name: "domain", label: "Your domain", kind: "text", required: true, max: 200 },
      { name: "competitors", label: "Competitors", kind: "list", placeholder: "One per line" },
      { name: "niche", label: "Niche", kind: "text" },
      { name: "target_keywords", label: "Target keywords", kind: "list", placeholder: "One per line" },
      { name: "opportunity_types", label: "Opportunity types", kind: "list", placeholder: "guest posts, digital PR…" },
    ],
    note: "This is strategy guidance, not a crawl of your backlink index.",
  },
  "growth-playbooks": {
    slug: "growth-playbooks",
    title: "Growth Playbooks",
    summary: "Pick and sequence growth plays that fit your capacity.",
    endpoint: "/seo-platform/growth-playbooks/analyze",
    fields: [
      { name: "objective", label: "Objective", kind: "text", required: true, max: 300 },
      { name: "domain", label: "Domain", kind: "text", max: 300 },
      { name: "target_channels", label: "Channels", kind: "list", placeholder: "One per line" },
      { name: "weekly_capacity_hours", label: "Weekly capacity (hours)", kind: "number", min: 1, max: 168, initial: 20 },
      notes,
    ],
  },
  "seo-ab-testing": {
    slug: "seo-ab-testing",
    title: "A/B Test Design",
    summary: "Design an SEO experiment you can run and measure.",
    endpoint: "/seo-platform/seo-ab-testing/analyze",
    fields: [
      { name: "url", label: "Page URL", kind: "text", required: true, max: 500 },
      { name: "hypothesis", label: "Hypothesis", kind: "text", required: true, max: 500, placeholder: "A shorter title will lift click-through rate" },
      { name: "primary_metric", label: "Primary metric", kind: "select", options: [{ value: "conversion_rate", label: "Conversion rate" }, { value: "ctr", label: "Click-through rate" }, { value: "organic_sessions", label: "Organic sessions" }, { value: "position", label: "Average position" }], initial: "conversion_rate" },
      { name: "variant_a", label: "Variant A (control)", kind: "textarea", required: true, rows: 4, max: 2000 },
      { name: "variant_b", label: "Variant B", kind: "textarea", required: true, rows: 4, max: 2000 },
      { name: "test_duration_days", label: "Duration (days)", kind: "number", min: 7, max: 120, initial: 21 },
      notes,
    ],
  },
  "site-migration": {
    slug: "site-migration",
    title: "Site Migration",
    summary: "Plan redirects and monitoring for a domain or structure change.",
    endpoint: "/seo-platform/site-migration/analyze",
    fields: [
      { name: "source_domain", label: "Current domain", kind: "text", required: true, max: 300 },
      { name: "target_domain", label: "New domain", kind: "text", required: true, max: 300 },
      { name: "sample_urls", label: "Sample URLs", kind: "list", placeholder: "Important URLs, one per line" },
      { name: "launch_window", label: "Launch window", kind: "text", max: 120, placeholder: "e.g. first week of November" },
      notes,
    ],
  },
  "log-file": {
    slug: "log-file",
    title: "Log File Analysis",
    summary: "Break down crawler activity, response codes and wasted crawls from your server logs.",
    endpoint: "/seo-platform/log-file/analyze",
    fields: [
      { name: "log_snippet", label: "Log lines", kind: "textarea", required: true, rows: 12, max: 5000, placeholder: "Paste access-log lines", hint: "Results are computed from the lines you paste (up to 5,000 characters)." },
      { name: "domain", label: "Domain", kind: "text", max: 300 },
      notes,
    ],
  },
  "multi-channel-activation": {
    slug: "multi-channel-activation",
    title: "Multi-Channel Activation",
    summary: "Reuse SEO content across channels with a consistent message.",
    endpoint: "/seo-platform/multi-channel-activation/analyze",
    fields: [
      { name: "campaign_name", label: "Campaign", kind: "text", required: true, max: 300 },
      { name: "primary_offer", label: "Primary offer", kind: "text", max: 300 },
      { name: "channels", label: "Channels", kind: "list", placeholder: "One per line" },
      { name: "audience_segments", label: "Audience segments", kind: "list", placeholder: "One per line" },
      notes,
    ],
  },
  agent: {
    slug: "agent",
    title: "Autonomous Agent",
    summary: "Turn a goal into a phased SEO plan with owners, effort and success metrics.",
    endpoint: "/seo-platform/agent/run",
    fields: [
      { name: "goal", label: "Goal", kind: "textarea", required: true, rows: 4, max: 1000, placeholder: "e.g. Increase organic signups for our trail shoes category by 20% in a quarter", hint: "At least 5 characters." },
      { name: "domain", label: "Domain", kind: "text", placeholder: "example.com" },
    ],
    submitLabel: "Plan",
    note: "The agent proposes a plan for you to review. It does not make changes to your site.",
  },
};
