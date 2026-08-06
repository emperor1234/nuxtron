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
    description: 'AI-enhanced traditional SEO workflows spanning keyword research, content, and technical signals.',
    route_path: '/seo/seo-ai',
    badge: 'Core',
  },
  {
    key: 'aeo',
    display_name: 'AEO: Answer Engine Optimization',
    group: 'Search Intelligence',
    description: 'OpenLens + Playwright + LlamaIndex + JSON-LD optimization for answer engines.',
    route_path: '/seo/aeo',
    badge: 'Core',
    integrations: ['openlens', 'playwright', 'llamaindex', 'json-ld'],
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
    display_name: 'Programmatic SEO Engine',
    group: 'Experience Optimization',
    description: 'Programmatic landing page and template-driven SEO at scale.',
    route_path: '/seo/programmatic',
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
    display_name: 'Revenue Attribution Intelligence',
    group: 'Growth & Governance',
    description: 'Attribution from search and AI channels through to revenue outcomes.',
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
    description: 'Policy, governance, and risk controls for SEO and AI execution.',
    route_path: '/seo/trust-risk-governance',
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
    display_name: 'Keyword Research',
    group: 'Core Foundations',
    description: 'Intent, clustering, SERP features, and keyword opportunity scoring.',
    route_path: '/seo/keywords',
    badge: 'Core',
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
    display_name: 'Advanced Rank Tracking',
    group: 'Core Foundations',
    description: 'Time-series ranking data, volatility detection, competitor tracking, and SERP forecasting.',
    route_path: '/seo/rank-tracking',
    badge: 'Core',
    integrations: ['opensearch', 'grafana', 'time_series_db'],
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
    display_name: 'International & Multilingual SEO',
    group: 'Expansion Modules',
    description: 'Regionalization, hreflang, and multilingual search optimization.',
    route_path: '/seo/international-multilingual',
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
    key: 'local-seo-suite',
    display_name: 'Local SEO Suite',
    group: 'Expansion Modules',
    description: 'Local intent, map visibility, location pages, and review signals.',
    route_path: '/seo/local',
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
    display_name: 'Analytics, Reporting & Intelligence',
    group: 'SaaS Platform',
    description: 'Central analytics and reporting across the SEO estate.',
    route_path: '/seo/analytics',
  },
  {
    key: 'agency-multi-tenant-platform',
    display_name: 'Agency & Multi-Tenant Platform',
    group: 'SaaS Platform',
    description: 'Tenant-aware SEO operations, workspaces, and governance.',
    route_path: '/seo/agency-platform',
  },
  {
    key: 'integrations-automation-layer',
    display_name: 'Integrations & Automation Layer',
    group: 'SaaS Platform',
    description: 'Third-party integrations, connectors, and automation plumbing.',
    route_path: '/seo/integrations-automation',
  },
  {
    key: 'unified-ads-control-tower',
    display_name: 'Unified Ads Control Tower',
    group: 'Ads Orchestration & Retail Media',
    description:
      'Production-grade command center for orchestrating Google, Microsoft, Amazon, Apple Search Ads, and YouTube campaigns from one operating plane.',
    route_path: '/seo/unified-ads-control-tower',
    badge: 'Core',
    integrations: [
      'google_ads_api',
      'microsoft_ads',
      'amazon_ads',
      'apple_search_ads',
      'youtube_ads',
      'supabase',
      'redis',
    ],
    supported_channels: [
      'Google Ads',
      'Microsoft Advertising',
      'Amazon Advertising',
      'Apple Search Ads',
      'YouTube Ads',
    ],
    architecture_layers: [
      'Next.js control tower UI',
      'FastAPI orchestration layer',
      'Django admin and billing spine',
      'PostgreSQL + Supabase control plane',
      'Redis + Celery execution fabric',
    ],
    automation_features: [
      'Cross-network campaign launch',
      'Shared budget guardrails',
      'Creative approval routing',
      'Realtime anomaly and pacing alerts',
    ],
    analytics_features: [
      'Unified ROAS scorecards',
      'Network-normalized KPI schema',
      'Cross-channel spend rollups',
      'Realtime delivery health snapshots',
    ],
    enterprise_features: [
      'Multi-tenant workspaces',
      'RBAC and audit logs',
      'API gateway + rate limiting',
      'GDPR-aware consent boundaries',
    ],
    ai_models: ['llama-3.1-70b', 'deepseek-r1', 'qwen2.5-72b', 'bge-m3'],
    delivery_constraints: [
      'Requires advertiser API approvals',
      'Cannot replace underlying ad exchanges',
      'Each network has different reporting latency and policy rules',
    ],
  },
  {
    key: 'cross-network-campaign-orchestrator',
    display_name: 'Cross-Network Campaign Orchestrator',
    group: 'Ads Orchestration & Retail Media',
    description:
      'Advanced workflow engine for cloning, localizing, and synchronizing campaigns, ad groups, audiences, and creative packages across major ad networks.',
    route_path: '/seo/cross-network-campaign-orchestrator',
    badge: 'AI',
    integrations: ['google_ads_api', 'microsoft_ads', 'amazon_ads', 'apple_search_ads', 'celery', 'airflow'],
    supported_channels: ['Search', 'Shopping', 'Retail media', 'App acquisition', 'Video'],
    architecture_layers: [
      'Campaign template service',
      'Connector abstraction layer',
      'Async execution queues',
      'Approval + rollback workflow service',
    ],
    automation_features: [
      'Campaign cloning by market',
      'Audience and keyword sync',
      'Landing-page mapping automation',
      'Failure-safe retries with rollback',
    ],
    analytics_features: ['Execution audit timeline', 'Platform drift detection', 'Template performance benchmarking'],
    enterprise_features: [
      'Approval checkpoints',
      'Tenant-safe connector isolation',
      'Change history and operator attribution',
    ],
    ai_models: ['qwen2.5-coder', 'deepseek-v3'],
    delivery_constraints: [
      'Platform object models differ by network',
      'Bulk mutation limits must be throttled',
      'Creative policy violations can block sync jobs',
    ],
  },
  {
    key: 'budget-pacing-bid-engine',
    display_name: 'Budget Pacing & Bid Engine',
    group: 'Ads Orchestration & Retail Media',
    description:
      'Rule-driven and model-assisted bid engine that monitors CTR, CPA, CPC, ROAS, and spend pacing to keep campaigns on target throughout the day.',
    route_path: '/seo/budget-pacing-bid-engine',
    badge: 'AI',
    integrations: ['redis', 'celery', 'prometheus', 'grafana', 'postgres'],
    supported_channels: ['Search', 'Retail media', 'App store search', 'Video performance'],
    architecture_layers: [
      'Realtime metrics ingest',
      'Rules engine',
      'Bid recommendation service',
      'Task workers for pacing adjustments',
    ],
    automation_features: [
      'If CTR drops then pause/repair',
      'If CPA spikes then lower bid',
      'Budget pacing by hour',
      'Seasonality and daypart bid multipliers',
    ],
    analytics_features: [
      'Pacing variance dashboards',
      'Bid-change impact attribution',
      'Spend anomaly detection',
      'Forecast vs actual delivery',
    ],
    enterprise_features: [
      'Per-tenant guardrails',
      'Manual override controls',
      'Threshold-based approvals for high-spend changes',
    ],
    ai_models: ['xgboost-ctr', 'lightgbm-cpa', 'llama-3.1-8b-instruct'],
    delivery_constraints: [
      'Requires sufficient conversion volume',
      'Model quality varies by channel maturity',
      'Realtime bidding is limited by API refresh windows',
    ],
  },
  {
    key: 'attribution-conversion-intelligence',
    display_name: 'Attribution & Conversion Intelligence',
    group: 'Ads Orchestration & Retail Media',
    description:
      'Server-side tracking and attribution fabric that unifies ad clicks, conversions, revenue events, and offline outcomes into decision-grade reporting.',
    route_path: '/seo/attribution-conversion-intelligence',
    badge: 'Core',
    integrations: ['posthog', 'snowplow', 'supabase', 'postgres', 'google_conversion_api'],
    supported_channels: ['Paid search', 'Retail media', 'Organic assist', 'CRM/offline revenue'],
    architecture_layers: [
      'Event ingestion API',
      'Identity resolution layer',
      'Attribution model service',
      'Warehouse-ready reporting marts',
    ],
    automation_features: [
      'Server-side event capture',
      'Conversion deduplication',
      'Assisted conversion stitching',
      'Multi-touch model refresh jobs',
    ],
    analytics_features: [
      'Path-to-conversion analysis',
      'LTV by acquisition source',
      'Incrementality-ready reporting',
      'ROAS by campaign and keyword cluster',
    ],
    enterprise_features: [
      'Consent-aware event governance',
      'Data retention policy hooks',
      'Auditability for metric definitions',
    ],
    ai_models: ['bge-large', 'e5-large-v2'],
    delivery_constraints: [
      'Attribution is probabilistic, not absolute',
      'Cross-device identity remains imperfect',
      'Privacy policies differ by geography',
    ],
  },
  {
    key: 'ai-creative-keyword-lab',
    display_name: 'AI Creative & Keyword Lab',
    group: 'Ads Orchestration & Retail Media',
    description:
      'Advanced AI workspace for generating ad copy, keyword clusters, negative keywords, landing-page angles, and channel-specific test matrices.',
    route_path: '/seo/ai-creative-keyword-lab',
    badge: 'AI',
    integrations: ['ollama', 'llama3', 'deepseek', 'qwen', 'openai_embeddings', 'serp_data'],
    supported_channels: ['Search ads', 'Retail media search', 'YouTube and video scripts', 'App store copy variants'],
    architecture_layers: [
      'Prompt/version registry',
      'Embedding clustering service',
      'Approval workspace',
      'Experiment publishing hooks',
    ],
    automation_features: [
      'Keyword expansion',
      'Negative keyword mining',
      'Ad copy variant generation',
      'Creative fatigue detection',
    ],
    analytics_features: ['Prompt-to-performance lineage', 'Keyword cluster scoring', 'Creative win-rate analysis'],
    enterprise_features: ['Human approval queues', 'Brand safety constraints', 'Prompt audit log'],
    ai_models: ['llama-3.1-70b', 'deepseek-v3', 'qwen2.5-72b', 'mistral-nemo', 'bge-m3'],
    delivery_constraints: [
      'Generated copy still requires policy review',
      'Keyword suggestions depend on source quality',
      'Platform editorial rules vary by locale',
    ],
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
    display_name: 'RAG Site Search Engine',
    group: 'Schema & Optimization',
    description: 'Semantic site search powered by retrieval and reasoning.',
    route_path: '/seo/rag-search',
  },
  {
    key: 'competitor-intelligence-engine',
    display_name: 'Competitor Intelligence Engine',
    group: 'Schema & Optimization',
    description: 'Competitive search, AI visibility, and content gap intelligence.',
    route_path: '/seo/competitor',
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
    key: 'review-reputation-engine',
    display_name: 'Review & Reputation Engine',
    group: 'Content & Distribution',
    description: 'Review mining, sentiment analysis, and reputation response workflows.',
    route_path: '/seo/reviews',
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
  {
    key: 'performance-audit',
    display_name: 'GTmetrix-Style Performance Audit',
    group: 'Performance & Audits',
    description: 'Lighthouse, CDP waterfall, Web Vitals, filmstrip, history, and alert-driven performance auditing.',
    route_path: '/seo/performance',
    badge: 'New',
    integrations: ['lighthouse', 'playwright_cdp', 'web_vitals', 'opensearch', 'prometheus', 'grafana', 'metabase'],
  },
  {
    key: 'platform-intelligence',
    display_name: 'Platform Matrix Score',
    group: 'Performance & Audits',
    description:
      'Cross-module health score, SLA compliance, latency matrix, AI governance, anomaly detection, and ranked action items.',
    route_path: '/seo/platform-intelligence',
    badge: 'Core',
    integrations: ['prometheus', 'grafana', 'opensearch', 'dbt', 'deepseek', 'llm_pool', 'mlflow_patterns'],
  },
];

function toSeoModule(item: FallbackSeed): SeoModule {
  return {
    ...item,
    implemented: true,
    backend_ready: true,
    frontend_ready: true,
    database_ready: true,
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
  const groupsByName: Record<string, SeoModule[]> = {};
  for (const module of modules) {
    groupsByName[module.group] = groupsByName[module.group] ?? [];
    groupsByName[module.group].push(module);
  }

  const groups: SeoModuleGroup[] = Object.entries(groupsByName).map(([group, items]) => ({ group, items }));

  return {
    total: modules.length,
    implemented: modules.length,
    groups,
    modules,
  };
}
