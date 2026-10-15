export type ModuleTier = 'Core' | 'AI' | 'New' | 'Experiment' | 'SaaS';

export type ModuleCatalogEntry = {
  title: string;
  tier?: ModuleTier;
  summary: string;
  category: string;
  routePath: string;
  moduleKey?: string;
};

export const SEO_MODULE_CATALOG: ModuleCatalogEntry[] = [
  {
    title: 'SEO-AI',
    tier: 'Core',
    summary: 'SEO-AI planning and content review. Keyword-export inspection is browser-local; provider-backed search metrics are unavailable.',
    category: 'Search Intelligence',
    routePath: '/seo/seo-ai',
    moduleKey: 'seo-ai',
  },
  {
    title: 'Keyword Data Review',
    tier: 'Core',
    summary: 'Review a keyword export you provide in this browser. Connected search data, generated metrics, and competitor gaps are unavailable.',
    category: 'Research & visibility',
    routePath: '/seo/keywords',
    moduleKey: 'keyword-research-engine',
  },
  {
    title: 'AEO: Answer Engine Optimization',
    tier: 'Core',
    summary: 'OpenLens + Playwright + LlamaIndex + JSON-LD optimization for answer engines.',
    category: 'Search Intelligence',
    routePath: '/seo/aeo',
    moduleKey: 'aeo',
  },
  {
    title: 'GEO: Generative Engine Optimization',
    tier: 'Core',
    summary: 'Llama-3 + RAG over SERPs, AI answers, and site content for generative overviews.',
    category: 'Search Intelligence',
    routePath: '/seo/geo',
    moduleKey: 'geo',
  },
  {
    title: 'AIO-2',
    tier: 'New',
    summary: 'Agentic intelligence optimization for content and search workflows.',
    category: 'Search Intelligence',
    routePath: '/seo/aio',
    moduleKey: 'aio',
  },
  {
    title: 'LLMO',
    tier: 'New',
    summary: 'LLM optimization for brand accuracy, retrieval, and answer quality.',
    category: 'Search Intelligence',
    routePath: '/seo/llmo',
    moduleKey: 'llmo',
  },
  {
    title: 'SAGEO',
    summary: 'Search-augmented generative SEO planning and synthesis.',
    category: 'Search Intelligence',
    routePath: '/seo/sageo',
    moduleKey: 'sageo',
  },
  {
    title: 'VSO',
    summary: 'Voice search optimization for question-answer and assistant-driven queries.',
    category: 'Search Intelligence',
    routePath: '/seo/vso',
    moduleKey: 'vso',
  },
  {
    title: 'SXO',
    summary: 'Search experience optimization spanning UX, engagement, and SERP behavior.',
    category: 'Search Intelligence',
    routePath: '/seo/sxo',
    moduleKey: 'sxo',
  },
  {
    title: 'GXO',
    tier: 'New',
    summary: 'Google AI Overview and generative experience optimization.',
    category: 'Search Intelligence',
    routePath: '/seo/gxo',
    moduleKey: 'gxo',
  },
  {
    title: 'Entity-First SEO',
    summary: 'Knowledge graph and entity-driven optimization workflows.',
    category: 'Search Intelligence',
    routePath: '/seo/entity',
    moduleKey: 'entity',
  },
  {
    title: 'PEAO',
    summary: 'Predictive engine algorithm optimization using trend and anomaly forecasting.',
    category: 'Search Intelligence',
    routePath: '/seo/peao',
    moduleKey: 'peao',
  },
  {
    title: 'MSVO',
    summary: 'Multi-surface visibility optimization across search, AI, and owned channels.',
    category: 'Search Intelligence',
    routePath: '/seo/msvo',
    moduleKey: 'msvo',
  },
  {
    title: 'NSVO (MSVO Alias)',
    summary: 'Compatibility alias for multi-surface visibility optimization naming.',
    category: 'Search Intelligence',
    routePath: '/seo/nsvo',
    moduleKey: 'nsvo',
  },
  {
    title: 'DAEO',
    summary: 'Decentralized answer engine optimization for self-hosted and federated search.',
    category: 'Search Intelligence',
    routePath: '/seo/daeo',
    moduleKey: 'daeo',
  },

  {
    title: 'CXAO: Conversational Experience Answer Optimization',
    tier: 'AI',
    summary: 'Llama-3 + RAG + Next.js chat flows + PostHog optimization for conversational outcomes.',
    category: 'Experience Optimization',
    routePath: '/seo/cxao',
    moduleKey: 'cxao',
  },
  {
    title: 'E-E-A-T Optimization Suite',
    summary: 'Authority, trust, expertise, and provenance scoring.',
    category: 'Experience Optimization',
    routePath: '/seo/eeat',
    moduleKey: 'eeat',
  },
  {
    title: 'Autonomous Agent Engine',
    tier: 'AI',
    summary: 'Plan, execute, and evaluate SEO workflows with agentic loops.',
    category: 'Experience Optimization',
    routePath: '/seo/agent',
    moduleKey: 'agent',
  },
  {
    title: 'Programmatic SEO Draft Preview',
    summary: 'Expand user-supplied templates locally into a capped draft set; no server generation, search metrics, storage, or publishing.',
    category: 'Experience Optimization',
    routePath: '/seo/programmatic',
    moduleKey: 'programmatic-seo-engine',
  },
  {
    title: 'SEO A/B Testing Framework',
    tier: 'Experiment',
    summary: 'Next.js variants + feature flags + PostHog experiments + Llama-3 analysis.',
    category: 'Experience Optimization',
    routePath: '/seo/seo-ab-testing',
    moduleKey: 'seo-ab-testing-framework',
  },
  {
    title: 'eCommerce SEO Suite',
    summary: 'Product, category, and merchandising-focused SEO workflows.',
    category: 'Experience Optimization',
    routePath: '/seo/ecommerce',
    moduleKey: 'ecommerce-seo-suite',
  },

  {
    title: 'Revenue Attribution',
    summary: 'Workspace-scoped report of recorded conversions and tracked touchpoints. Currency totals remain separate; no causal lift is estimated.',
    category: 'Growth & Governance',
    routePath: '/seo/revenue-attribution',
    moduleKey: 'revenue-attribution-intelligence',
  },
  {
    title: 'Growth Playbooks Automation',
    summary: 'Automated growth playbook execution and measurement.',
    category: 'Growth & Governance',
    routePath: '/seo/growth-playbooks',
    moduleKey: 'growth-playbooks-automation',
  },
  {
    title: 'Trust & Risk Governance',
    summary: 'Evidence-based governance assessments are unavailable until verified policy, control, incident, and audit sources are connected.',
    category: 'Growth & Governance',
    routePath: '/seo/trust-risk-governance',
    moduleKey: 'trust-risk-governance',
  },
  {
    title: 'Multi-Channel Activation Loop',
    summary: 'Activation and distribution across search, social, and lifecycle channels.',
    category: 'Growth & Governance',
    routePath: '/seo/multi-channel-activation',
    moduleKey: 'multi-channel-activation-loop',
  },

  {
    title: 'Autonomous Link Building',
    summary: 'Backlink discovery, prospecting, and workflow orchestration.',
    category: 'Expansion Modules',
    routePath: '/seo/linkbuilding',
    moduleKey: 'autonomous-link-building',
  },
  {
    title: 'Hreflang & Locale Review',
    summary: 'Browser-local syntax and locale-list checks for markup you provide; no crawl, reciprocal-link, canonical, or translation verification.',
    category: 'International SEO',
    routePath: '/seo/international-multilingual',
    moduleKey: 'international-multilingual-seo',
  },
  {
    title: 'Site Migration SEO Manager',
    summary: 'SEO-safe migration planning, validation, and monitoring.',
    category: 'Expansion Modules',
    routePath: '/seo/site-migration',
    moduleKey: 'site-migration-seo-manager',
  },
  {
    title: 'Video SEO Module',
    summary: 'Video metadata, transcript, and discovery optimization.',
    category: 'Expansion Modules',
    routePath: '/seo/video',
    moduleKey: 'video-seo-module',
  },
  {
    title: 'Backlink Intelligence Engine',
    tier: 'Core',
    summary: 'Advanced link graph analysis with Neo4j-ready topology and topical clustering.',
    category: 'Core Foundations',
    routePath: '/seo/backlink-intelligence',
    moduleKey: 'backlink-intelligence-engine',
  },
  {
    title: 'Rank Position Review',
    tier: 'Core',
    summary: 'Review positions from a supplied CSV locally. Live monitoring, competitor tracking, and forecasts are unavailable.',
    category: 'Core Foundations',
    routePath: '/seo/rank-tracking',
    moduleKey: 'advanced-rank-tracking',
  },
  {
    title: 'Content Creation & Blogging Suite',
    tier: 'Core',
    summary: 'AI-powered blogging strategy, content calendar, SEO briefs, and multimedia planning.',
    category: 'Core Foundations',
    routePath: '/seo/content-creation-blogging',
    moduleKey: 'content-creation-blogging-suite',
  },

  {
    title: 'News SEO & Google Discover',
    summary: 'Freshness, Top Stories, and Discover optimization.',
    category: 'SaaS Platform',
    routePath: '/seo/news-discover',
    moduleKey: 'news-seo-google-discover',
  },
  {
    title: 'Traffic Analytics',
    summary: 'Compare search KPIs from two periods using values supplied by the workspace; no analytics provider is connected.',
    category: 'Analytics & history',
    routePath: '/seo/analytics',
  },
  {
    title: 'SEO Analysis History',
    summary: 'Workspace-scoped archive of saved SEO analysis records with explicit persistence status and redacted details.',
    category: 'Analytics & history',
    routePath: '/seo/history',
    moduleKey: 'analytics-reporting-intelligence',
  },
  {
    title: 'Agency Workspace Health',
    summary: 'Workspace inventory, roles, policies, audit events, owners, and SLA evidence are not connected; health scores are unavailable.',
    category: 'SaaS Platform',
    routePath: '/seo/agency-platform',
    moduleKey: 'agency-multi-tenant-platform',
  },
  {
    title: 'Integrations & Automation Layer',
    summary: 'Connector inventory and automation controls are not available in this customer experience yet.',
    category: 'SaaS Platform',
    routePath: '/seo/integrations-automation',
    moduleKey: 'integrations-automation-layer',
  },

  {
    title: 'Search Observation Log',
    summary: 'Record and export manually verified search observations; no live provider or persistent monitor is connected.',
    category: 'Monitoring & Observability',
    routePath: '/seo/realtime-monitoring',
    moduleKey: 'real-time-search-ai-monitoring',
  },
  {
    title: 'Technical SEO Audit',
    summary: 'Unavailable until a verified crawler and Core Web Vitals source can provide measured page-level findings.',
    category: 'Monitoring & Observability',
    routePath: '/seo/technical',
    moduleKey: 'ai-technical-seo-engine',
  },
  {
    title: 'Content Review',
    summary: 'Unavailable until findings can be verified against retrieved, traceable source evidence.',
    category: 'Monitoring & Observability',
    routePath: '/seo/content-auditor',
    moduleKey: 'content-quality-hallucination-auditor',
  },
  {
    title: 'Entity Graph Planner',
    summary: 'Draft an entity and relationship outline from inputs you provide; live knowledge-graph analysis is not connected.',
    category: 'Monitoring & Observability',
    routePath: '/seo/knowledge-graph',
    moduleKey: 'knowledge-graph-management',
  },
  {
    title: 'AI Internal Linking Engine',
    summary: 'Semantic link opportunity detection and internal authority flow design.',
    category: 'Monitoring & Observability',
    routePath: '/seo/internal-linking',
    moduleKey: 'ai-internal-linking-engine',
  },
  {
    title: 'Crawl Budget Review',
    summary: 'Review user-supplied URL and access-log samples locally; sitewide crawl metrics are not connected.',
    category: 'Monitoring & Observability',
    routePath: '/seo/crawl-budget',
    moduleKey: 'crawl-budget-optimizer',
  },

  {
    title: 'AI Schema Engine',
    summary: 'Automated schema generation, validation, and enhancement.',
    category: 'Schema & Optimization',
    routePath: '/seo/schemas',
    moduleKey: 'ai-schema-engine',
  },
  {
    title: 'UX & Conversion Optimizer',
    summary: 'Behavior, conversion, and UX optimization from search traffic.',
    category: 'Schema & Optimization',
    routePath: '/seo/ux',
    moduleKey: 'ux-conversion-optimizer',
  },
  {
    title: 'Corpus Search Preview',
    summary: 'Browser-local keyword matching over text you provide; no crawling, semantic index, generated answers, or saved sources.',
    category: 'Search Intelligence',
    routePath: '/seo/rag-search',
    moduleKey: 'rag-site-search-engine',
  },
  {
    title: 'SEO Competitor Research',
    summary: 'Verified SERP, keyword, traffic, backlink, and AI-answer evidence sources are not connected; competitor metrics are unavailable.',
    category: 'Search Intelligence',
    routePath: '/seo/competitor',
    moduleKey: 'competitor-intelligence-engine',
  },
  {
    title: 'Competitor Activity Monitor',
    summary: 'Durable tenant-scoped storage, authorized data sources, and scheduled collection are not configured; no sample events or alerts are generated.',
    category: 'Search Intelligence',
    routePath: '/seo/competitor-monitoring',
    moduleKey: 'competitor-activity-monitor',
  },

  {
    title: 'Topical Map & Silo Builder',
    summary: 'Topic clustering, hub-spoke architecture, and editorial map generation.',
    category: 'Content & Distribution',
    routePath: '/seo/topical-map',
    moduleKey: 'topical-map-silo-builder',
  },
  {
    title: 'Log File Analysis Engine',
    summary: 'Crawl-log ingestion, anomaly detection, and bot behavior analysis.',
    category: 'Content & Distribution',
    routePath: '/seo/log-file',
    moduleKey: 'log-file-analysis-engine',
  },
  {
    title: 'Brand Voice & Style Engine',
    summary: 'Brand-consistent rewriting and tone governance for SEO content.',
    category: 'Content & Distribution',
    routePath: '/seo/brand-voice',
    moduleKey: 'brand-voice-style-engine',
  },

  {
    title: 'Accessibility Audit',
    summary: 'Unavailable until a rendered-page WCAG scanner can return reproducible, page-specific evidence.',
    category: 'Accessibility & Media',
    routePath: '/seo/accessibility',
    moduleKey: 'accessibility-optimizer',
  },
  {
    title: 'Media Markup Review',
    summary: 'Review image and video attributes from pasted HTML locally; no website crawl, compression estimate, or live change.',
    category: 'Accessibility & Media',
    routePath: '/seo/media',
    moduleKey: 'image-media-seo-engine',
  },
  {
    title: 'Social Share Preview',
    summary: 'Build text-only channel previews from user-entered metadata locally; no page crawl or third-party rendering check is performed.',
    category: 'Content & Distribution',
    routePath: '/seo/social',
    moduleKey: 'social-seo-distribution',
  },
  {
    title: 'Landing Page Brief',
    summary: 'Generate a reviewable landing-page outline with copy, metadata, FAQ, and schema drafts; publishing is not connected.',
    category: 'Content & Distribution',
    routePath: '/seo/landing',
    moduleKey: 'landing-page-builder',
  },
  {
    title: 'Security Header Review',
    summary: 'Inspect exact header values from a pasted sample locally; no security scan or compliance assessment is performed.',
    category: 'Accessibility & Media',
    routePath: '/seo/security',
    moduleKey: 'security-seo-health-monitor',
  },

];

export function getCatalogByRoutePath(routePath: string | undefined): ModuleCatalogEntry | null {
  if (!routePath) return null;
  return SEO_MODULE_CATALOG.find((item) => item.routePath === routePath) ?? null;
}

export function getCatalogByModuleKey(moduleKey: string | undefined): ModuleCatalogEntry | null {
  if (!moduleKey) return null;
  return SEO_MODULE_CATALOG.find((item) => item.moduleKey === moduleKey) ?? null;
}

export function getCatalogBySlug(slug: string | undefined): ModuleCatalogEntry | null {
  if (!slug) return null;
  return SEO_MODULE_CATALOG.find((item) => item.moduleKey === slug || item.routePath.endsWith(`/${slug}`)) ?? null;
}
