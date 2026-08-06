-- SEO platform module registry schema and seed data.
-- Mirrors the runtime registry used by the SEO hub and backend module endpoints.

BEGIN;

CREATE TABLE IF NOT EXISTS seo_platform_modules (
    key TEXT PRIMARY KEY,
    group_name TEXT NOT NULL,
    display_name TEXT NOT NULL,
    description TEXT NOT NULL,
    route_path TEXT NOT NULL,
    badge TEXT,
    implemented BOOLEAN NOT NULL DEFAULT FALSE,
    backend_ready BOOLEAN NOT NULL DEFAULT FALSE,
    frontend_ready BOOLEAN NOT NULL DEFAULT FALSE,
    database_ready BOOLEAN NOT NULL DEFAULT TRUE,
    integrations JSONB NOT NULL DEFAULT '[]'::jsonb,
    sort_order INT NOT NULL DEFAULT 100,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_seo_platform_modules_group_order
ON seo_platform_modules (group_name, sort_order, key);

INSERT INTO seo_platform_modules (
    key,
    group_name,
    display_name,
    description,
    route_path,
    badge,
    implemented,
    backend_ready,
    frontend_ready,
    database_ready,
    integrations,
    sort_order,
    updated_at
)
VALUES
    ('seo-ai', 'Search Intelligence', 'SEO-AI', 'AI-enhanced traditional SEO workflows spanning keyword research, content, and technical signals.', '/seo/seo-ai', 'Core', TRUE, TRUE, TRUE, TRUE, '[]'::jsonb, 1, NOW()),
    ('geo', 'Search Intelligence', 'GEO', 'Generative engine optimization across AI answer surfaces.', '/seo/geo', 'New', TRUE, TRUE, TRUE, TRUE, '[]'::jsonb, 2, NOW()),
    ('aio-2', 'Search Intelligence', 'AIO-2', 'Agentic intelligence optimization for content and search workflows.', '/seo/aio', 'New', TRUE, TRUE, TRUE, TRUE, '[]'::jsonb, 3, NOW()),
    ('llmo', 'Search Intelligence', 'LLMO', 'LLM optimization for brand accuracy, retrieval, and answer quality.', '/seo/llmo', 'New', TRUE, TRUE, TRUE, TRUE, '[]'::jsonb, 4, NOW()),
    ('sageo', 'Search Intelligence', 'SAGEO', 'Search-augmented generative SEO planning and synthesis.', '/seo/sageo', NULL, TRUE, TRUE, TRUE, TRUE, '[]'::jsonb, 5, NOW()),
    ('vso', 'Search Intelligence', 'VSO', 'Voice search optimization for question-answer and assistant-driven queries.', '/seo/vso', NULL, TRUE, TRUE, TRUE, TRUE, '[]'::jsonb, 6, NOW()),
    ('sxo', 'Search Intelligence', 'SXO', 'Search experience optimization spanning UX, engagement, and SERP behavior.', '/seo/sxo', NULL, TRUE, TRUE, TRUE, TRUE, '[]'::jsonb, 7, NOW()),
    ('gxo', 'Search Intelligence', 'GXO', 'Google AI Overview and generative experience optimization.', '/seo/gxo', 'New', TRUE, TRUE, TRUE, TRUE, '[]'::jsonb, 8, NOW()),
    ('entity-first-seo', 'Search Intelligence', 'Entity-First SEO', 'Knowledge graph and entity-driven optimization workflows.', '/seo/entity', NULL, TRUE, TRUE, TRUE, TRUE, '[]'::jsonb, 9, NOW()),
    ('peao', 'Search Intelligence', 'PEAO', 'Predictive engine algorithm optimization using trend and anomaly forecasting.', '/seo/peao', NULL, TRUE, TRUE, TRUE, TRUE, '[]'::jsonb, 10, NOW()),
    ('msvo', 'Search Intelligence', 'MSVO', 'Multi-surface visibility optimization across search, AI, and owned channels.', '/seo/msvo', NULL, TRUE, TRUE, TRUE, TRUE, '[]'::jsonb, 11, NOW()),
    ('daeo', 'Search Intelligence', 'DAEO', 'Decentralized answer engine optimization for self-hosted and federated search.', '/seo/daeo', NULL, TRUE, TRUE, TRUE, TRUE, '[]'::jsonb, 12, NOW()),
    ('cxao', 'Experience Optimization', 'Experience Optimization', 'Conversational experience answer optimization for assistants and chat.', '/seo/modules/cxao', NULL, FALSE, FALSE, FALSE, TRUE, '[]'::jsonb, 13, NOW()),
    ('eeat-suite', 'Experience Optimization', 'E-E-A-T Optimization Suite', 'Authority, trust, expertise, and provenance scoring.', '/seo/eeat', NULL, TRUE, TRUE, TRUE, TRUE, '[]'::jsonb, 14, NOW()),
    ('autonomous-agent-engine', 'Experience Optimization', 'Autonomous Agent Engine', 'Plan, execute, and evaluate SEO workflows with agentic loops.', '/seo/agent', 'AI', TRUE, TRUE, TRUE, TRUE, '[]'::jsonb, 15, NOW()),
    ('programmatic-seo-engine', 'Experience Optimization', 'Programmatic SEO Engine', 'Programmatic landing page and template-driven SEO at scale.', '/seo/programmatic', NULL, TRUE, TRUE, TRUE, TRUE, '[]'::jsonb, 16, NOW()),
    ('seo-ab-testing', 'Experience Optimization', 'Experience Optimization', 'Statistical testing of SEO and UX variants.', '/seo/modules/seo-ab-testing', NULL, FALSE, FALSE, FALSE, TRUE, '[]'::jsonb, 17, NOW()),
    ('ecommerce-seo-suite', 'Experience Optimization', 'eCommerce SEO Suite', 'Product, category, and merchandising-focused SEO workflows.', '/seo/ecommerce', NULL, TRUE, TRUE, TRUE, TRUE, '[]'::jsonb, 18, NOW()),
    ('revenue-attribution-intelligence', 'Growth & Governance', 'Revenue Attribution Intelligence', 'Attribution from search and AI channels through to revenue outcomes.', '/seo/modules/revenue-attribution-intelligence', NULL, FALSE, FALSE, FALSE, TRUE, '[]'::jsonb, 19, NOW()),
    ('growth-playbooks-automation', 'Growth & Governance', 'Growth Playbooks Automation', 'Automated growth playbook execution and measurement.', '/seo/modules/growth-playbooks-automation', NULL, FALSE, FALSE, FALSE, TRUE, '[]'::jsonb, 20, NOW()),
    ('trust-risk-governance', 'Growth & Governance', 'Trust & Risk Governance', 'Policy, governance, and risk controls for SEO and AI execution.', '/seo/modules/trust-risk-governance', NULL, FALSE, FALSE, FALSE, TRUE, '[]'::jsonb, 21, NOW()),
    ('multi-channel-activation-loop', 'Growth & Governance', 'Multi-Channel Activation Loop', 'Activation and distribution across search, social, and lifecycle channels.', '/seo/modules/multi-channel-activation-loop', NULL, FALSE, FALSE, FALSE, TRUE, '[]'::jsonb, 22, NOW()),
    ('autonomous-link-building-system', 'Expansion Modules', 'Autonomous Link Building', 'Backlink discovery, prospecting, and workflow orchestration.', '/seo/linkbuilding', NULL, TRUE, TRUE, TRUE, TRUE, '[]'::jsonb, 23, NOW()),
    ('international-multilingual-seo', 'Expansion Modules', 'International & Multilingual SEO', 'Regionalization, hreflang, and multilingual search optimization.', '/seo/modules/international-multilingual-seo', NULL, FALSE, FALSE, FALSE, TRUE, '[]'::jsonb, 24, NOW()),
    ('site-migration-seo-manager', 'Expansion Modules', 'Site Migration SEO Manager', 'SEO-safe migration planning, validation, and monitoring.', '/seo/modules/site-migration-seo-manager', NULL, FALSE, FALSE, FALSE, TRUE, '[]'::jsonb, 25, NOW()),
    ('video-seo-module', 'Expansion Modules', 'Video SEO Module', 'Video metadata, transcript, and discovery optimization.', '/seo/video', NULL, TRUE, TRUE, TRUE, TRUE, '[]'::jsonb, 26, NOW()),
    ('local-seo-suite', 'Expansion Modules', 'Local SEO Suite', 'Local intent, map visibility, location pages, and review signals.', '/seo/local', NULL, TRUE, TRUE, TRUE, TRUE, '[]'::jsonb, 27, NOW()),
    ('news-seo-google-discover', 'SaaS Platform', 'News SEO & Google Discover', 'Freshness, Top Stories, and Discover optimization.', '/seo/modules/news-seo-google-discover', NULL, FALSE, FALSE, FALSE, TRUE, '[]'::jsonb, 28, NOW()),
    ('analytics-reporting-intelligence', 'SaaS Platform', 'Analytics, Reporting & Intelligence', 'Central analytics and reporting across the SEO estate.', '/seo/history', NULL, TRUE, TRUE, TRUE, TRUE, '[]'::jsonb, 29, NOW()),
    ('agency-multi-tenant-platform', 'SaaS Platform', 'Agency & Multi-Tenant Platform', 'Tenant-aware SEO operations, workspaces, and governance.', '/seo/modules/agency-multi-tenant-platform', NULL, FALSE, FALSE, FALSE, TRUE, '[]'::jsonb, 30, NOW()),
    ('integrations-automation-layer', 'SaaS Platform', 'Integrations & Automation Layer', 'Third-party integrations, connectors, and automation plumbing.', '/seo/modules/integrations-automation-layer', NULL, FALSE, FALSE, FALSE, TRUE, '[]'::jsonb, 31, NOW()),
    ('realtime-search-ai-monitoring', 'Monitoring & Observability', 'Real-Time Search & AI Monitoring', 'Realtime engine volatility, visibility tracking, and alerting.', '/seo/modules/realtime-search-ai-monitoring', NULL, FALSE, FALSE, FALSE, TRUE, '[]'::jsonb, 32, NOW()),
    ('ai-technical-seo-engine', 'Monitoring & Observability', 'AI Technical SEO Engine', 'Autonomous technical SEO diagnosis and remediation.', '/seo/technical', NULL, TRUE, TRUE, TRUE, TRUE, '[]'::jsonb, 33, NOW()),
    ('content-quality-hallucination-auditor', 'Monitoring & Observability', 'Content Quality & Hallucination Auditor', 'Factuality, citation, and answer-quality auditing for AI-assisted content.', '/seo/modules/content-quality-hallucination-auditor', NULL, FALSE, FALSE, FALSE, TRUE, '[]'::jsonb, 34, NOW()),
    ('knowledge-graph-management', 'Monitoring & Observability', 'Knowledge Graph Management', 'Entity graph construction, enrichment, and validation.', '/seo/modules/knowledge-graph-management', NULL, FALSE, FALSE, FALSE, TRUE, '[]'::jsonb, 35, NOW()),
    ('ai-internal-linking-engine', 'Monitoring & Observability', 'AI Internal Linking Engine', 'Semantic link opportunity detection and internal authority flow design.', '/seo/modules/ai-internal-linking-engine', NULL, FALSE, FALSE, FALSE, TRUE, '[]'::jsonb, 36, NOW()),
    ('crawl-budget-optimizer', 'Monitoring & Observability', 'Crawl Budget Optimizer', 'Log-based crawl efficiency and priority optimization.', '/seo/modules/crawl-budget-optimizer', NULL, FALSE, FALSE, FALSE, TRUE, '[]'::jsonb, 37, NOW()),
    ('ai-schema-engine', 'Schema & Optimization', 'AI Schema Engine', 'Automated schema generation, validation, and enhancement.', '/seo/schemas', NULL, TRUE, TRUE, TRUE, TRUE, '[]'::jsonb, 38, NOW()),
    ('ux-conversion-optimizer', 'Schema & Optimization', 'UX & Conversion Optimizer', 'Behavior, conversion, and UX optimization from search traffic.', '/seo/modules/ux-conversion-optimizer', NULL, FALSE, FALSE, FALSE, TRUE, '[]'::jsonb, 39, NOW()),
    ('rag-site-search-engine', 'Schema & Optimization', 'RAG Site Search Engine', 'Semantic site search powered by retrieval and reasoning.', '/seo/modules/rag-site-search-engine', NULL, FALSE, FALSE, FALSE, TRUE, '[]'::jsonb, 40, NOW()),
    ('competitor-intelligence-engine', 'Schema & Optimization', 'Competitor Intelligence Engine', 'Competitive search, AI visibility, and content gap intelligence.', '/seo/modules/competitor-intelligence-engine', NULL, FALSE, FALSE, FALSE, TRUE, '[]'::jsonb, 41, NOW()),
    ('topical-map-silo-builder', 'Content & Distribution', 'Topical Map & Silo Builder', 'Topic clustering, hub-spoke architecture, and editorial map generation.', '/seo/modules/topical-map-silo-builder', NULL, FALSE, FALSE, FALSE, TRUE, '[]'::jsonb, 42, NOW()),
    ('log-file-analysis-engine', 'Content & Distribution', 'Log File Analysis Engine', 'Crawl-log ingestion, anomaly detection, and bot behavior analysis.', '/seo/modules/log-file-analysis-engine', NULL, FALSE, FALSE, FALSE, TRUE, '[]'::jsonb, 43, NOW()),
    ('review-reputation-engine', 'Content & Distribution', 'Review & Reputation Engine', 'Review mining, sentiment analysis, and reputation response workflows.', '/seo/modules/review-reputation-engine', NULL, FALSE, FALSE, FALSE, TRUE, '[]'::jsonb, 44, NOW()),
    ('brand-voice-style-engine', 'Content & Distribution', 'Brand Voice & Style Engine', 'Brand-consistent rewriting and tone governance for SEO content.', '/seo/modules/brand-voice-style-engine', NULL, FALSE, FALSE, FALSE, TRUE, '[]'::jsonb, 45, NOW()),
    ('accessibility-optimizer', 'Accessibility & Media', 'Accessibility Optimizer', 'WCAG, readability, and assistive discoverability optimization.', '/seo/modules/accessibility-optimizer', NULL, FALSE, FALSE, FALSE, TRUE, '[]'::jsonb, 46, NOW()),
    ('image-media-seo-engine', 'Accessibility & Media', 'Image & Media SEO Engine', 'Alt text, metadata, compression, and media search optimization.', '/seo/modules/image-media-seo-engine', NULL, FALSE, FALSE, FALSE, TRUE, '[]'::jsonb, 47, NOW()),
    ('social-seo-distribution', 'Accessibility & Media', 'Social SEO & Distribution', 'Search-aware social distribution and multi-surface promotion.', '/seo/modules/social-seo-distribution', NULL, FALSE, FALSE, FALSE, TRUE, '[]'::jsonb, 48, NOW()),
    ('landing-page-builder', 'Accessibility & Media', 'Landing Page Builder', 'Conversion-ready landing pages with schema and experimentation hooks.', '/seo/modules/landing-page-builder', NULL, FALSE, FALSE, FALSE, TRUE, '[]'::jsonb, 49, NOW()),
    ('security-seo-health-monitor', 'Accessibility & Media', 'Security & SEO Health Monitor', 'Security posture, spam, cloaking, and SEO integrity monitoring.', '/seo/modules/security-seo-health-monitor', NULL, FALSE, FALSE, FALSE, TRUE, '[]'::jsonb, 50, NOW()),
    ('performance-audit', 'Performance & Audits', 'GTmetrix-Style Performance Audit', 'Lighthouse, CDP waterfall, Web Vitals, filmstrip, history, and alert-driven performance auditing.', '/seo/performance', 'New', TRUE, TRUE, TRUE, TRUE, '["lighthouse", "playwright_cdp", "web_vitals", "opensearch", "prometheus", "grafana", "metabase"]'::jsonb, 51, NOW())
ON CONFLICT (key) DO UPDATE SET
    group_name = EXCLUDED.group_name,
    display_name = EXCLUDED.display_name,
    description = EXCLUDED.description,
    route_path = EXCLUDED.route_path,
    badge = EXCLUDED.badge,
    implemented = EXCLUDED.implemented,
    backend_ready = EXCLUDED.backend_ready,
    frontend_ready = EXCLUDED.frontend_ready,
    database_ready = EXCLUDED.database_ready,
    integrations = EXCLUDED.integrations,
    sort_order = EXCLUDED.sort_order,
    updated_at = NOW();

COMMIT;