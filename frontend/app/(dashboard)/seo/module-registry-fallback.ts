type SeoModule = {
  key: string;
  group: string;
  display_name: string;
  description: string;
  route_path: string;
  badge?: string | null;
  implemented: boolean;
  backend_ready: boolean;
  frontend_ready: boolean;
  database_ready: boolean;
  integrations: string[];
  supported_channels: string[];
  architecture_layers: string[];
  automation_features: string[];
  analytics_features: string[];
  enterprise_features: string[];
  ai_models: string[];
  delivery_constraints: string[];
};

type SeoModuleGroup = {
  group: string;
  items: SeoModule[];
};

type ModulesResponse = {
  total: number;
  implemented: number;
  groups: SeoModuleGroup[];
  modules: SeoModule[];
};

type FallbackSeed = {
  key: string;
  display_name: string;
  group: string;
  description: string;
  route_path: string;
  implemented?: boolean;
  backend_ready?: boolean;
  frontend_ready?: boolean;
  database_ready?: boolean;
  badge?: string;
  integrations?: string[];
  supported_channels?: string[];
  architecture_layers?: string[];
  automation_features?: string[];
  analytics_features?: string[];
  enterprise_features?: string[];
  ai_models?: string[];
  delivery_constraints?: string[];
};

const REGISTRY_SEED: FallbackSeed[] = [
  {
    key: 'seo-ai',
    display_name: 'SEO-AI',
    group: 'Search Intelligence',
    description: 'SEO workflow tools for content and technical review; keyword exports are reviewed locally and provider-backed discovery is unavailable.',
    route_path: '/seo/seo-ai',
    badge: 'Core',
  },
  {
    key: 'aeo',
    display_name: 'AEO: Answer Engine Optimization',
    group: 'Search Intelligence',
    description: 'Answer-engine visibility monitoring, browser validation, retrieval workflows, and structured-data improvements.',
    route_path: '/seo/aeo',
    badge: 'Core',
    integrations: ['AI visibility checks', 'browser validation', 'retrieval workflows', 'structured data'],
  },
  {
    key: 'geo',
    display_name: 'GEO: Generative Engine Optimization',
    group: 'Search Intelligence',
    description: 'Llama-3 + RAG over SERPs, AI answers, and site content for generative overviews.',
    route_path: '/seo/geo',
    badge: 'Core',
    integrations: ['llama3', 'rag', 'serp', 'ai_answers'],
  },
  {
    key: 'aio-2',
    display_name: 'AIO-2',
    group: 'Search Intelligence',
    description: 'Agentic intelligence optimization for content and search workflows.',
    route_path: '/seo/aio',
    badge: 'New',
  },
  {
    key: 'llmo',
    display_name: 'LLMO',
    group: 'Search Intelligence',
    description: 'LLM optimization for brand accuracy, retrieval, and answer quality.',
    route_path: '/seo/llmo',
    badge: 'New',
  },
  {
    key: 'sageo',
    display_name: 'SAGEO',
    group: 'Search Intelligence',
    description: 'Search-augmented generative SEO planning and synthesis.',
    route_path: '/seo/sageo',
  },
  {
    key: 'vso',
    display_name: 'VSO',
    group: 'Search Intelligence',
    description: 'Voice search optimization for question-answer and assistant-driven queries.',
    route_path: '/seo/vso',
  },
  {
    key: 'sxo',
    display_name: 'SXO',
    group: 'Search Intelligence',
    description: 'Search experience optimization spanning UX, engagement, and SERP behavior.',
    route_path: '/seo/sxo',
  },
  {
    key: 'gxo',
    display_name: 'GXO',
    group: 'Search Intelligence',
    description: 'Google AI Overview and generative experience optimization.',
    route_path: '/seo/gxo',
    badge: 'New',
  },
  {
    key: 'entity-first-seo',
    display_name: 'Entity-First SEO',
    group: 'Search Intelligence',
    description: 'Knowledge graph and entity-driven optimization workflows.',
    route_path: '/seo/entity',
  },
  {
    key: 'peao',
    display_name: 'PEAO',
    group: 'Search Intelligence',
    description: 'Predictive engine algorithm optimization using trend and anomaly forecasting.',
    route_path: '/seo/peao',
  },
  {
    key: 'msvo',
    display_name: 'MSVO',
    group: 'Search Intelligence',
    description: 'Multi-surface visibility optimization across search, AI, and owned channels.',
    route_path: '/seo/msvo',
  },
  {
    key: 'daeo',
    display_name: 'DAEO',
    group: 'Search Intelligence',
    description: 'Decentralized answer engine optimization for self-hosted and federated search.',
    route_path: '/seo/daeo',
  },
  {
    key: 'cxao',
    display_name: 'CXAO: Conversational Experience Answer Optimization',
    group: 'Experience Optimization',
    description: 'Llama-3 + RAG + Next.js chat flows + PostHog optimization for conversational outcomes.',
    route_path: '/seo/cxao',
    badge: 'AI',
    integrations: ['llama3', 'rag', 'nextjs', 'posthog'],
  },
  {
    key: 'eeat-suite',
    display_name: 'E-E-A-T Optimization Suite',
    group: 'Experience Optimization',
    description: 'Authority, trust, expertise, and provenance scoring.',
    route_path: '/seo/eeat',
  },
  {
    key: 'autonomous-agent-engine',
    display_name: 'Autonomous Agent Engine',
    group: 'Experience Optimization',
    description: 'Plan, execute, and evaluate SEO workflows with agentic loops.',
    route_path: '/seo/agent',
    badge: 'AI',
  },
  {
    key: 'programmatic-seo-engine',
    display_name: 'Programmatic SEO Draft Preview',
    group: 'Experience Optimization',
    description: 'Browser-local expansion of user-supplied templates is available; server generation, search metrics, persistence, and publishing are unavailable.',
    route_path: '/seo/programmatic',
    implemented: false,
    backend_ready: false,
    frontend_ready: true,
    database_ready: false,
  },
  {
    key: 'seo-ab-testing',
    display_name: 'SEO A/B Testing Framework',
    group: 'Experience Optimization',
    description: 'Next.js variants + feature flags + PostHog experiments + Llama-3 analysis.',
    route_path: '/seo/seo-ab-testing',
    badge: 'Experiment',
    integrations: ['nextjs', 'feature_flags', 'posthog_experiments', 'llama3'],
  },
  {
    key: 'ecommerce-seo-suite',
    display_name: 'eCommerce SEO Suite',
    group: 'Experience Optimization',
    description: 'Product, category, and merchandising-focused SEO workflows.',
    route_path: '/seo/ecommerce',
  },
  {
    key: 'revenue-attribution-intelligence',
    display_name: 'Revenue Attribution',
    group: 'Growth & Governance',
    description: 'Workspace-scoped report of recorded conversions and tracked touchpoints. Currency totals remain separate; no causal lift is estimated.',
    route_path: '/seo/revenue-attribution',
  },
  {
    key: 'growth-playbooks-automation',
    display_name: 'Growth Playbooks Automation',
    group: 'Growth & Governance',
    description: 'Automated growth playbook execution and measurement.',
    route_path: '/seo/growth-playbooks',
  },
  {
    key: 'trust-risk-governance',
    display_name: 'Trust & Risk Governance',
    group: 'Growth & Governance',
    description: 'Verified policy, control, incident, and audit evidence sources are not connected; posture scores and risk findings are unavailable.',
    route_path: '/seo/trust-risk-governance',
    implemented: false,
    backend_ready: false,
    frontend_ready: true,
  },
  {
    key: 'multi-channel-activation-loop',
    display_name: 'Multi-Channel Activation Loop',
    group: 'Growth & Governance',
    description: 'Activation and distribution across search, social, and lifecycle channels.',
    route_path: '/seo/multi-channel-activation',
  },
  {
    key: 'autonomous-link-building-system',
    display_name: 'Autonomous Link Building',
    group: 'Expansion Modules',
    description: 'Backlink discovery, prospecting, and workflow orchestration.',
    route_path: '/seo/linkbuilding',
  },
  {
    key: 'keyword-research-engine',
    display_name: 'Keyword Data Review',
    group: 'Research & visibility',
    description: 'Browser-local review of user-provided keyword exports; connected search data, generated metrics, and competitor gaps are unavailable.',
    route_path: '/seo/keywords',
    badge: 'Core',
    implemented: false,
    backend_ready: false,
    frontend_ready: true,
    database_ready: false,
  },
  {
    key: 'backlink-intelligence-engine',
    display_name: 'Backlink Intelligence Engine',
    group: 'Core Foundations',
    description: 'Advanced link graph analysis with Neo4j-ready topology and topical clustering.',
    route_path: '/seo/backlink-intelligence',
    badge: 'Core',
    integrations: ['neo4j', 'opensearch', 'scrapy'],
  },
  {
    key: 'advanced-rank-tracking-system',
    display_name: 'Rank Position Review',
    group: 'Core Foundations',
    description: 'Browser-local review of positions and context from a user-supplied CSV. Live tracking and forecasts are unavailable.',
    route_path: '/seo/rank-tracking',
    badge: 'Core',
    integrations: [],
  },
  {
    key: 'content-creation-blogging-suite',
    display_name: 'Content Creation & Blogging Suite',
    group: 'Core Foundations',
    description: 'AI-powered blogging strategy, content calendar, SEO briefs, and multimedia planning.',
    route_path: '/seo/content-creation-blogging',
    badge: 'Core',
    integrations: ['ollama', 'llama3', 'deepseek', 'claude'],
  },
  {
    key: 'international-multilingual-seo',
    display_name: 'Hreflang & Locale Review',
    group: 'International SEO',
    description: 'Browser-local syntax and user-supplied locale review only; live-page, reciprocal-link, and canonical verification are unavailable.',
    route_path: '/seo/international-multilingual',
    implemented: false,
    backend_ready: false,
    frontend_ready: true,
    database_ready: false,
  },
  {
    key: 'site-migration-seo-manager',
    display_name: 'Site Migration SEO Manager',
    group: 'Expansion Modules',
    description: 'SEO-safe migration planning, validation, and monitoring.',
    route_path: '/seo/site-migration',
  },
  {
    key: 'video-seo-module',
    display_name: 'Video SEO Module',
    group: 'Expansion Modules',
    description: 'Video metadata, transcript, and discovery optimization.',
    route_path: '/seo/video',
  },
  {
    key: 'news-seo-google-discover',
    display_name: 'News SEO & Google Discover',
    group: 'SaaS Platform',
    description: 'Freshness, Top Stories, and Discover optimization.',
    route_path: '/seo/news-discover',
  },
  {
    key: 'analytics-reporting-intelligence',
    display_name: 'SEO Analysis History',
    group: 'Analytics & history',
    description: 'Workspace-scoped archive of saved SEO analysis records with explicit persistence status and redacted details.',
    route_path: '/seo/history',
  },
  {
    key: 'agency-multi-tenant-platform',
    display_name: 'Agency Workspace Health',
    group: 'SaaS Platform',
    description: 'Workspace inventory, roles, policies, audit events, owners, and SLA evidence are not connected; health scores are unavailable.',
    route_path: '/seo/agency-platform',
    implemented: false,
    backend_ready: false,
    frontend_ready: true,
  },
  {
    key: 'integrations-automation-layer',
    display_name: 'Integrations & Automation Layer',
    group: 'SaaS Platform',
    description: 'Connector inventory and automation controls are not available in this customer experience yet.',
    route_path: '/seo/integrations-automation',
    implemented: false,
    backend_ready: false,
    frontend_ready: true,
  },
  {
    key: 'retail-media-app-growth-hub',
    display_name: 'Retail Media & App Growth Hub',
    group: 'Ads Orchestration & Retail Media',
    description:
      'Specialized command module for Amazon retail media, Apple Search Ads, app growth measurement, and marketplace-specific merchandising loops.',
    route_path: '/seo/retail-media-app-growth-hub',
    badge: 'New',
    integrations: ['amazon_ads', 'apple_search_ads', 'appsflyer', 'adjust', 'metabase'],
    supported_channels: [
      'Amazon Sponsored Products',
      'Amazon Sponsored Brands',
      'Apple Search Ads',
      'App install campaigns',
    ],
    architecture_layers: [
      'Retail catalog sync',
      'App growth cohort service',
      'Marketplace reporting adapters',
      'Budget split optimizer',
    ],
    automation_features: [
      'ASIN/product targeting sync',
      'Search term harvest loops',
      'App keyword bid automation',
      'Geo-aware budget allocation',
    ],
    analytics_features: [
      'Retail share-of-shelf',
      'App install to revenue cohort views',
      'Marketplace keyword profitability',
    ],
    enterprise_features: [
      'Brand vs marketplace budget segmentation',
      'Role-safe app portfolio access',
      'Operational alerting for feed failures',
    ],
    ai_models: ['llama-3.1-8b', 'deepseek-r1-distill'],
    delivery_constraints: [
      'Retail APIs expose different dimensions than search ads',
      'App attribution needs MMP alignment',
      'Some marketplaces offer limited realtime controls',
    ],
  },
  {
    key: 'realtime-search-ai-monitoring',
    display_name: 'Real-Time Search & AI Monitoring',
    group: 'Monitoring & Observability',
    description: 'Realtime engine volatility, visibility tracking, and alerting.',
    route_path: '/seo/realtime-monitoring',
  },
  {
    key: 'ai-technical-seo-engine',
    display_name: 'AI Technical SEO Engine',
    group: 'Monitoring & Observability',
    description: 'Autonomous technical SEO diagnosis and remediation.',
    route_path: '/seo/technical',
  },
  {
    key: 'content-quality-hallucination-auditor',
    display_name: 'Content Quality & Hallucination Auditor',
    group: 'Monitoring & Observability',
    description: 'Factuality, citation, and answer-quality auditing for AI-assisted content.',
    route_path: '/seo/content-auditor',
  },
  {
    key: 'knowledge-graph-management',
    display_name: 'Knowledge Graph Management',
    group: 'Monitoring & Observability',
    description: 'Entity graph construction, enrichment, and validation.',
    route_path: '/seo/knowledge-graph',
  },
  {
    key: 'ai-internal-linking-engine',
    display_name: 'AI Internal Linking Engine',
    group: 'Monitoring & Observability',
    description: 'Semantic link opportunity detection and internal authority flow design.',
    route_path: '/seo/internal-linking',
  },
  {
    key: 'crawl-budget-optimizer',
    display_name: 'Crawl Budget Optimizer',
    group: 'Monitoring & Observability',
    description: 'Log-based crawl efficiency and priority optimization.',
    route_path: '/seo/crawl-budget',
  },
  {
    key: 'ai-schema-engine',
    display_name: 'AI Schema Engine',
    group: 'Schema & Optimization',
    description: 'Automated schema generation, validation, and enhancement.',
    route_path: '/seo/schemas',
  },
  {
    key: 'ux-conversion-optimizer',
    display_name: 'UX & Conversion Optimizer',
    group: 'Schema & Optimization',
    description: 'Behavior, conversion, and UX optimization from search traffic.',
    route_path: '/seo/ux',
  },
  {
    key: 'rag-site-search-engine',
    display_name: 'Corpus Search Preview',
    group: 'Search Intelligence',
    description: 'Browser-local keyword matching over user-supplied text; no connected crawling, semantic index, or server search.',
    route_path: '/seo/rag-search',
    implemented: true,
    backend_ready: false,
    frontend_ready: true,
    database_ready: false,
  },
  {
    key: 'competitor-intelligence-engine',
    display_name: 'SEO Competitor Research',
    group: 'Search Intelligence',
    description: 'Verified SERP, keyword, traffic, backlink, and AI-answer evidence sources are not connected; competitor metrics are unavailable.',
    route_path: '/seo/competitor',
    implemented: false,
    backend_ready: false,
    frontend_ready: true,
  },
  {
    key: 'competitor-activity-monitor',
    display_name: 'Competitor Activity Monitor',
    group: 'Search Intelligence',
    description: 'Durable tenant-scoped storage, authorized data sources, and scheduled collection are not configured; no sample events or alerts are generated.',
    route_path: '/seo/competitor-monitoring',
    implemented: false,
    backend_ready: false,
    frontend_ready: true,
    database_ready: false,
  },
  {
    key: 'topical-map-silo-builder',
    display_name: 'Topical Map & Silo Builder',
    group: 'Content & Distribution',
    description: 'Topic clustering, hub-spoke architecture, and editorial map generation.',
    route_path: '/seo/topical-map',
  },
  {
    key: 'log-file-analysis-engine',
    display_name: 'Log File Analysis Engine',
    group: 'Content & Distribution',
    description: 'Crawl-log ingestion, anomaly detection, and bot behavior analysis.',
    route_path: '/seo/log-file',
  },
  {
    key: 'brand-voice-style-engine',
    display_name: 'Brand Voice & Style Engine',
    group: 'Content & Distribution',
    description: 'Brand-consistent rewriting and tone governance for SEO content.',
    route_path: '/seo/brand-voice',
  },
  {
    key: 'accessibility-optimizer',
    display_name: 'Accessibility Optimizer',
    group: 'Accessibility & Media',
    description: 'WCAG, readability, and assistive discoverability optimization.',
    route_path: '/seo/accessibility',
  },
  {
    key: 'image-media-seo-engine',
    display_name: 'Image & Media SEO Engine',
    group: 'Accessibility & Media',
    description: 'Alt text, metadata, compression, and media search optimization.',
    route_path: '/seo/media',
  },
  {
    key: 'social-seo-distribution',
    display_name: 'Social SEO & Distribution',
    group: 'Accessibility & Media',
    description: 'Search-aware social distribution and multi-surface promotion.',
    route_path: '/seo/social',
  },
  {
    key: 'landing-page-builder',
    display_name: 'Landing Page Builder',
    group: 'Accessibility & Media',
    description: 'Conversion-ready landing pages with schema and experimentation hooks.',
    route_path: '/seo/landing',
  },
  {
    key: 'security-seo-health-monitor',
    display_name: 'Security & SEO Health Monitor',
    group: 'Accessibility & Media',
    description: 'Security posture, spam, cloaking, and SEO integrity monitoring.',
    route_path: '/seo/security',
  },
];

function toSeoModule(item: FallbackSeed): SeoModule {
  return {
    ...item,
    implemented: item.implemented ?? true,
    backend_ready: item.backend_ready ?? true,
    frontend_ready: item.frontend_ready ?? true,
    database_ready: item.database_ready ?? true,
    badge: item.badge ?? null,
    integrations: item.integrations ?? [],
    supported_channels: item.supported_channels ?? [],
    architecture_layers: item.architecture_layers ?? [],
    automation_features: item.automation_features ?? [],
    analytics_features: item.analytics_features ?? [],
    enterprise_features: item.enterprise_features ?? [],
    ai_models: item.ai_models ?? [],
    delivery_constraints: item.delivery_constraints ?? [],
  };
}

export function getFallbackModulesResponse(): ModulesResponse {
  const modules = REGISTRY_SEED.map(toSeoModule);
  const implemented = modules.filter((module) => module.implemented).length;
  const groupsByName: Record<string, SeoModule[]> = {};
  for (const module of modules) {
    groupsByName[module.group] = groupsByName[module.group] ?? [];
    groupsByName[module.group].push(module);
  }

  const groups: SeoModuleGroup[] = Object.entries(groupsByName).map(([group, items]) => ({ group, items }));

  return {
    total: modules.length,
    implemented,
    groups,
    modules,
  };
}
