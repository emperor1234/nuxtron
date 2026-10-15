from __future__ import annotations

from typing import Any

_BASE_AUTOMATION_FEATURES = [
    "Autonomous planning loop",
    "Self-healing retries with rollback",
    "Scheduled execution workflows",
    "Human override controls",
]

_BASE_ANALYTICS_FEATURES = [
    "Realtime KPI telemetry",
    "Anomaly and drift detection",
    "Forecast versus actual tracking",
    "Executive-ready reporting",
]

_BASE_ENTERPRISE_FEATURES = [
    "Tenant isolation boundaries",
    "RBAC + audit log coverage",
    "Policy and compliance guardrails",
    "SLA and incident visibility",
]

_BASE_ARCHITECTURE_LAYERS = [
    "Next.js operator interface",
    "FastAPI orchestration API",
    "Async worker execution fabric",
    "PostgreSQL analytical store",
]

_BASE_SUPPORTED_CHANNELS = [
    "Web search",
    "AI answer engines",
    "Owned content channels",
]

_BASE_AI_MODELS = [
    "deepseek-r1",
    "llama-3.1",
]

_BASE_DELIVERY_CONSTRAINTS = [
    "Human approval required for high-risk actions",
    "External API rate limits apply",
]


def _merge_unique(primary: list[str] | None, fallback: list[str]) -> list[str]:
    merged: list[str] = []
    for source in [primary or [], fallback]:
        for item in source:
            text = str(item).strip()
            if text and text not in merged:
                merged.append(text)
    return merged


def _enrich_module_for_production(module: dict[str, Any]) -> dict[str, Any]:
    """
    Apply a non-destructive production baseline to all modules.
    Existing module-specific values are preserved and de-duplicated.
    """
    enriched = dict(module)

    enriched["integrations"] = _merge_unique(
        enriched.get("integrations"),
        ["postgres", "redis", "opentelemetry", "prometheus"],
    )
    enriched["supported_channels"] = _merge_unique(
        enriched.get("supported_channels"),
        _BASE_SUPPORTED_CHANNELS,
    )
    enriched["architecture_layers"] = _merge_unique(
        enriched.get("architecture_layers"),
        _BASE_ARCHITECTURE_LAYERS,
    )
    enriched["automation_features"] = _merge_unique(
        enriched.get("automation_features"),
        _BASE_AUTOMATION_FEATURES,
    )
    enriched["analytics_features"] = _merge_unique(
        enriched.get("analytics_features"),
        _BASE_ANALYTICS_FEATURES,
    )
    enriched["enterprise_features"] = _merge_unique(
        enriched.get("enterprise_features"),
        _BASE_ENTERPRISE_FEATURES,
    )
    enriched["ai_models"] = _merge_unique(
        enriched.get("ai_models"),
        _BASE_AI_MODELS,
    )
    enriched["delivery_constraints"] = _merge_unique(
        enriched.get("delivery_constraints"),
        _BASE_DELIVERY_CONSTRAINTS,
    )

    return enriched


def _module_readiness_score(module: dict[str, Any]) -> float:
    checks = [
        bool(module.get("implemented")),
        bool(module.get("backend_ready")),
        bool(module.get("frontend_ready")),
        bool(module.get("database_ready")),
        bool(module.get("integrations")),
        bool(module.get("supported_channels")),
        bool(module.get("architecture_layers")),
        bool(module.get("automation_features")),
        bool(module.get("analytics_features")),
        bool(module.get("enterprise_features")),
        bool(module.get("ai_models")),
        bool(module.get("delivery_constraints")),
    ]
    return round((sum(1 for check in checks if check) / len(checks)) * 100.0, 2)


def audit_seo_module_registry(modules: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """
    Triple-audit pass:
      1) structural validity (keys, routes, duplicates)
      2) production readiness metadata completeness
      3) autonomous/analytics/enterprise capability coverage
    """
    items = modules or SEO_MODULE_REGISTRY
    key_seen: set[str] = set()
    route_seen: set[str] = set()
    duplicate_keys: list[str] = []
    duplicate_routes: list[str] = []
    missing_required: list[dict[str, str]] = []
    missing_advanced: list[dict[str, Any]] = []
    low_readiness: list[dict[str, Any]] = []

    required_fields = ["key", "display_name", "group", "description", "route_path"]
    advanced_fields = [
        "integrations",
        "supported_channels",
        "architecture_layers",
        "automation_features",
        "analytics_features",
        "enterprise_features",
        "ai_models",
        "delivery_constraints",
    ]

    for module in items:
        key = str(module.get("key", "")).strip()
        route = str(module.get("route_path", "")).strip()

        if key in key_seen:
            duplicate_keys.append(key)
        key_seen.add(key)

        if route in route_seen:
            duplicate_routes.append(route)
        route_seen.add(route)

        for field in required_fields:
            value = module.get(field)
            if value is None or str(value).strip() == "":
                missing_required.append({"key": key or "unknown", "field": field})

        missing = [field for field in advanced_fields if not module.get(field)]
        if missing:
            missing_advanced.append({"key": key or "unknown", "missing": missing})

        readiness = _module_readiness_score(module)
        if readiness < 95.0:
            low_readiness.append({"key": key or "unknown", "score": readiness})

    return {
        "total_modules": len(items),
        "duplicate_keys": sorted(set(duplicate_keys)),
        "duplicate_routes": sorted(set(duplicate_routes)),
        "missing_required": missing_required,
        "missing_advanced": missing_advanced,
        "low_readiness": sorted(low_readiness, key=lambda x: float(x.get("score", 0))),
        "summary": {
            "triple_audit_passed": not duplicate_keys
            and not duplicate_routes
            and not missing_required
            and not missing_advanced,
            "average_readiness": round(
                sum(_module_readiness_score(module) for module in items) / len(items),
                2,
            )
            if items
            else 0.0,
            "production_grade_modules": sum(1 for module in items if _module_readiness_score(module) >= 95.0),
        },
    }


def _module(
    key: str,
    display_name: str,
    group: str,
    description: str,
    route_path: str,
    *,
    badge: str | None = None,
    implemented: bool = False,
    backend_ready: bool | None = None,
    frontend_ready: bool | None = None,
    database_ready: bool = True,
    integrations: list[str] | None = None,
    supported_channels: list[str] | None = None,
    architecture_layers: list[str] | None = None,
    automation_features: list[str] | None = None,
    analytics_features: list[str] | None = None,
    enterprise_features: list[str] | None = None,
    ai_models: list[str] | None = None,
    delivery_constraints: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "key": key,
        "display_name": display_name,
        "group": group,
        "description": description,
        "route_path": route_path,
        "badge": badge,
        "implemented": implemented,
        "backend_ready": implemented if backend_ready is None else backend_ready,
        "frontend_ready": implemented if frontend_ready is None else frontend_ready,
        "database_ready": database_ready,
        "integrations": integrations or [],
        "supported_channels": supported_channels or [],
        "architecture_layers": architecture_layers or [],
        "automation_features": automation_features or [],
        "analytics_features": analytics_features or [],
        "enterprise_features": enterprise_features or [],
        "ai_models": ai_models or [],
        "delivery_constraints": delivery_constraints or [],
    }


_SEO_MODULE_REGISTRY_RAW: list[dict[str, Any]] = [
    _module(
        "seo-ai",
        "SEO-AI",
        "Search Intelligence",
        "AI-enhanced traditional SEO workflows spanning keyword research, content, and technical signals.",
        "/seo/seo-ai",
        badge="Core",
        implemented=True,
    ),
    _module(
        "keyword-research-engine",
        "Keyword Data Review",
        "Research & visibility",
        "Browser-local review of user-provided keyword exports; connected search data, generated metrics, and competitor gaps are unavailable.",
        "/seo/keywords",
        badge="Core",
        implemented=False,
        backend_ready=False,
        frontend_ready=True,
        database_ready=False,
    ),
    _module(
        "aeo",
        "AEO: Answer Engine Optimization",
        "Search Intelligence",
        "OpenLens + Playwright + LlamaIndex + JSON-LD optimization for answer engines.",
        "/seo/aeo",
        badge="Core",
        implemented=True,
        integrations=["openlens", "playwright", "llamaindex", "json-ld"],
    ),
    _module(
        "geo",
        "GEO: Generative Engine Optimization",
        "Search Intelligence",
        "Llama-3 + RAG over SERPs, AI answers, and site content for generative overviews.",
        "/seo/geo",
        badge="Core",
        implemented=True,
        integrations=["llama3", "rag", "serp", "ai_answers"],
    ),
    _module(
        "aio-2",
        "AIO-2",
        "Search Intelligence",
        "Agentic intelligence optimization for content and search workflows.",
        "/seo/aio",
        badge="New",
        implemented=True,
    ),
    _module(
        "llmo",
        "LLMO",
        "Search Intelligence",
        "LLM optimization for brand accuracy, retrieval, and answer quality.",
        "/seo/llmo",
        badge="New",
        implemented=True,
    ),
    _module(
        "sageo",
        "SAGEO",
        "Search Intelligence",
        "Search-augmented generative SEO planning and synthesis.",
        "/seo/sageo",
        implemented=True,
    ),
    _module(
        "vso",
        "VSO",
        "Search Intelligence",
        "Voice search optimization for question-answer and assistant-driven queries.",
        "/seo/vso",
        implemented=True,
    ),
    _module(
        "sxo",
        "SXO",
        "Search Intelligence",
        "Search experience optimization spanning UX, engagement, and SERP behavior.",
        "/seo/sxo",
        implemented=True,
    ),
    _module(
        "gxo",
        "GXO",
        "Search Intelligence",
        "Google AI Overview and generative experience optimization.",
        "/seo/gxo",
        badge="New",
        implemented=True,
    ),
    _module(
        "entity-first-seo",
        "Entity-First SEO",
        "Search Intelligence",
        "Knowledge graph and entity-driven optimization workflows.",
        "/seo/entity",
        implemented=True,
    ),
    _module(
        "peao",
        "PEAO",
        "Search Intelligence",
        "Predictive engine algorithm optimization using trend and anomaly forecasting.",
        "/seo/peao",
        implemented=True,
    ),
    _module(
        "msvo",
        "MSVO",
        "Search Intelligence",
        "Multi-surface visibility optimization across search, AI, and owned channels.",
        "/seo/msvo",
        implemented=True,
    ),
    _module(
        "daeo",
        "DAEO",
        "Search Intelligence",
        "Decentralized answer engine optimization for self-hosted and federated search.",
        "/seo/daeo",
        implemented=True,
    ),
    _module(
        "cxao",
        "CXAO: Conversational Experience Answer Optimization",
        "Experience Optimization",
        "Llama-3 + RAG + Next.js chat flows + PostHog optimization for conversational outcomes.",
        "/seo/cxao",
        badge="AI",
        implemented=True,
        integrations=["llama3", "rag", "nextjs", "posthog"],
    ),
    _module(
        "eeat-suite",
        "E-E-A-T Optimization Suite",
        "Experience Optimization",
        "Authority, trust, expertise, and provenance scoring.",
        "/seo/eeat",
        implemented=True,
    ),
    _module(
        "autonomous-agent-engine",
        "Autonomous Agent Engine",
        "Experience Optimization",
        "Plan, execute, and evaluate SEO workflows with agentic loops.",
        "/seo/agent",
        badge="AI",
        implemented=True,
    ),
    _module(
        "programmatic-seo-engine",
        "Programmatic SEO Draft Preview",
        "Experience Optimization",
        "Browser-local expansion of user-supplied templates is available; server generation, search metrics, persistence, and publishing are unavailable.",
        "/seo/programmatic",
        implemented=False,
        backend_ready=False,
        frontend_ready=True,
        database_ready=False,
    ),
    _module(
        "seo-ab-testing",
        "SEO A/B Testing Framework",
        "Experience Optimization",
        "Next.js variants + feature flags + PostHog experiments + Llama-3 analysis.",
        "/seo/seo-ab-testing",
        badge="Experiment",
        implemented=True,
        integrations=["nextjs", "feature_flags", "posthog_experiments", "llama3"],
    ),
    _module(
        "ecommerce-seo-suite",
        "eCommerce SEO Suite",
        "Experience Optimization",
        "Product, category, and merchandising-focused SEO workflows.",
        "/seo/ecommerce",
        implemented=True,
    ),
    _module(
        "revenue-attribution-intelligence",
        "Revenue Attribution",
        "Growth & Governance",
        "Workspace-scoped report of recorded conversions and tracked touchpoints. Currency totals remain separate; no causal lift is estimated.",
        "/seo/revenue-attribution",
        implemented=True,
    ),
    _module(
        "growth-playbooks-automation",
        "Growth Playbooks Automation",
        "Growth & Governance",
        "Automated growth playbook execution and measurement.",
        "/seo/growth-playbooks",
        implemented=True,
    ),
    _module(
        "trust-risk-governance",
        "Trust & Risk Governance",
        "Growth & Governance",
        "Verified policy, control, incident, and audit evidence sources are not connected; posture scores and risk findings are unavailable.",
        "/seo/trust-risk-governance",
        implemented=False,
        backend_ready=False,
        frontend_ready=True,
    ),
    _module(
        "multi-channel-activation-loop",
        "Multi-Channel Activation Loop",
        "Growth & Governance",
        "Activation and distribution across search, social, and lifecycle channels.",
        "/seo/multi-channel-activation",
        implemented=True,
    ),
    _module(
        "autonomous-link-building-system",
        "Autonomous Link Building",
        "Expansion Modules",
        "Backlink discovery, prospecting, and workflow orchestration.",
        "/seo/linkbuilding",
        implemented=True,
    ),
    _module(
        "backlink-intelligence-engine",
        "Backlink Intelligence Engine",
        "Core Foundations",
        "Advanced link graph analysis with Neo4j-ready topology and topical clustering.",
        "/seo/backlink-intelligence",
        badge="Core",
        implemented=True,
        integrations=["neo4j", "opensearch", "scrapy"],
    ),
    _module(
        "advanced-rank-tracking-system",
        "Rank Position Review",
        "Core Foundations",
        "Browser-local review of positions and context from a user-supplied CSV; server-side live tracking and forecasts are unavailable.",
        "/seo/rank-tracking",
        badge="Core",
        implemented=False,
        integrations=[],
    ),
    _module(
        "content-creation-blogging-suite",
        "Content Creation & Blogging Suite",
        "Core Foundations",
        "AI-powered blogging strategy, content calendar, SEO briefs, and multimedia planning.",
        "/seo/content-creation-blogging",
        badge="Core",
        implemented=True,
        integrations=["ollama", "llama3", "deepseek", "claude"],
    ),
    _module(
        "international-multilingual-seo",
        "Hreflang & Locale Review",
        "International SEO",
        "Browser-local syntax and user-supplied locale review only; live-page, reciprocal-link, and canonical verification are unavailable.",
        "/seo/international-multilingual",
        implemented=False,
        backend_ready=False,
        frontend_ready=True,
        database_ready=False,
    ),
    _module(
        "site-migration-seo-manager",
        "Site Migration SEO Manager",
        "Expansion Modules",
        "SEO-safe migration planning, validation, and monitoring.",
        "/seo/site-migration",
        implemented=True,
    ),
    _module(
        "video-seo-module",
        "Video SEO Module",
        "Expansion Modules",
        "Video metadata, transcript, and discovery optimization.",
        "/seo/video",
        implemented=True,
    ),
    _module(
        "local-seo-suite",
        "Local SEO Suite",
        "Expansion Modules",
        "Provider-verified business-profile, citation, review, and local-demand sources are unavailable; no local scores or search volumes are generated.",
        "/seo/local",
        implemented=False,
        backend_ready=False,
        frontend_ready=False,
        database_ready=False,
    ),
    _module(
        "news-seo-google-discover",
        "News SEO & Google Discover",
        "SaaS Platform",
        "Freshness, Top Stories, and Discover optimization.",
        "/seo/news-discover",
        implemented=True,
    ),
    _module(
        "analytics-reporting-intelligence",
        "SEO Analysis History",
        "Analytics & history",
        "Workspace-scoped archive of saved SEO analysis records with explicit persistence status and redacted details.",
        "/seo/history",
        implemented=True,
    ),
    _module(
        "agency-multi-tenant-platform",
        "Agency Workspace Health",
        "SaaS Platform",
        "Workspace inventory, role, policy, audit, owner, and SLA evidence are not connected; workspace-health scores are unavailable.",
        "/seo/agency-platform",
        implemented=False,
        backend_ready=False,
        frontend_ready=True,
    ),
    _module(
        "integrations-automation-layer",
        "Integrations & Automation Layer",
        "SaaS Platform",
        "Connector inventory and automation controls are not available in this customer experience yet.",
        "/seo/integrations-automation",
        implemented=False,
        backend_ready=False,
        frontend_ready=True,
    ),
    _module(
        "unified-ads-control-tower",
        "Unified Ads Control Tower",
        "Ads Orchestration & Retail Media",
        "Unavailable: provider OAuth exchange, tenant-scoped durable campaign storage, and verified provider reporting are not implemented.",
        "/seo",
        implemented=False,
        backend_ready=False,
        frontend_ready=False,
        database_ready=False,
        integrations=[],
        delivery_constraints=["No verified provider results or durable campaign records are available."],
    ),
    _module(
        "cross-network-campaign-orchestrator",
        "Cross-Network Campaign Orchestrator",
        "Ads Orchestration & Retail Media",
        "Unavailable: verified provider integrations, durable evidence, and production campaign controls are not implemented.",
        "/seo",
        implemented=False,
        backend_ready=False,
        frontend_ready=False,
        database_ready=False,
        integrations=[],
        delivery_constraints=["No verified provider results or durable campaign records are available."],
    ),
    _module(
        "budget-pacing-bid-engine",
        "Budget Pacing & Bid Engine",
        "Ads Orchestration & Retail Media",
        "Unavailable: verified provider integrations, durable evidence, and production campaign controls are not implemented.",
        "/seo",
        implemented=False,
        backend_ready=False,
        frontend_ready=False,
        database_ready=False,
        integrations=[],
        delivery_constraints=["No verified provider results or durable campaign records are available."],
    ),
    _module(
        "attribution-conversion-intelligence",
        "Attribution & Conversion Intelligence",
        "Ads Orchestration & Retail Media",
        "Unavailable: verified provider integrations, durable evidence, and production campaign controls are not implemented.",
        "/seo",
        implemented=False,
        backend_ready=False,
        frontend_ready=False,
        database_ready=False,
        integrations=[],
        delivery_constraints=["No verified provider results or durable campaign records are available."],
    ),
    _module(
        "ai-creative-keyword-lab",
        "AI Creative & Keyword Lab",
        "Ads Orchestration & Retail Media",
        "Unavailable: verified provider integrations, durable evidence, and production campaign controls are not implemented.",
        "/seo",
        implemented=False,
        backend_ready=False,
        frontend_ready=False,
        database_ready=False,
        integrations=[],
        delivery_constraints=["No verified provider results or durable campaign records are available."],
    ),
    _module(
        "retail-media-app-growth-hub",
        "Retail Media & App Growth Hub",
        "Ads Orchestration & Retail Media",
        "Retail-media and app-growth execution is unavailable; no verified provider connection, durable attribution, or campaign control is implemented.",
        "/seo",
        implemented=False,
        backend_ready=False,
        frontend_ready=False,
        database_ready=False,
        integrations=[],
        supported_channels=[],
        architecture_layers=[],
        automation_features=[],
        analytics_features=[],
        enterprise_features=[],
        ai_models=[],
        delivery_constraints=[
            "Provider adapters, tenant-scoped persistence, and measured campaign outcomes are not available",
        ],
    ),
    _module(
        "domain-overview",
        "Domain Overview",
        "Search Intelligence",
        "Comprehensive domain summary with organic, paid, backlink, traffic trend, and competitor snapshots.",
        "/seo/domain-overview",
        badge="Core",
        implemented=True,
        backend_ready=True,
        frontend_ready=True,
        database_ready=True,
        integrations=["dataforseo"],
    ),
    _module(
        "market-explorer",
        "Market Explorer",
        "Market Intelligence",
        "Market landscape analysis with category sizing, top players, market share, and growth quadrants.",
        "/seo/market-explorer",
        badge="Core",
        implemented=True,
        backend_ready=True,
        frontend_ready=True,
        database_ready=True,
        integrations=["similarweb"],
    ),
    _module(
        "one2target",
        "Audience Intelligence",
        "Audience Intelligence",
        "Audience research and segmentation using connected, verified evidence sources.",
        "/seo/one2target",
        badge="Core",
        implemented=True,
        backend_ready=True,
        frontend_ready=True,
        database_ready=True,
        integrations=["similarweb"],
    ),
    _module(
        "competitor-activity-monitor",
        "Competitor Activity Monitor",
        "Search Intelligence",
        "Durable tenant-scoped storage, authorized competitor-data sources, and scheduled collection are not configured; monitoring is unavailable.",
        "/seo/competitor-monitoring",
        implemented=False,
        backend_ready=False,
        frontend_ready=True,
        database_ready=False,
    ),
    _module(
        "pla-research",
        "PLA Research",
        "Paid Search Intelligence",
        "Google Shopping/PLA competitor intelligence including ad copies, positions, and pricing insights.",
        "/seo/pla-research",
        badge="New",
        implemented=True,
        backend_ready=True,
        frontend_ready=True,
        database_ready=True,
        integrations=["dataforseo_shopping"],
    ),
    _module(
        "map-rank-tracker",
        "Map Rank Tracker",
        "Local Search",
        "Verified local-pack observations and durable location history are unavailable; no map scans are generated.",
        "/seo/map-rank-tracker",
        badge="New",
        implemented=False,
        backend_ready=False,
        frontend_ready=False,
        database_ready=False,
        integrations=[],
    ),
    _module(
        "local-heatmap",
        "Local Heatmap",
        "Local Search",
        "Verified local rank-grid observations and durable scan history are unavailable; no heatmaps are generated.",
        "/seo/local-heatmap",
        badge="New",
        implemented=False,
        backend_ready=False,
        frontend_ready=False,
        database_ready=False,
        integrations=[],
    ),
    _module(
        "contentshake",
        "AI Content Generation",
        "Content & Distribution",
        "AI-assisted content drafting and editing from a user-provided brief.",
        "/seo/contentshake",
        badge="Core",
        implemented=True,
        backend_ready=True,
        frontend_ready=True,
        database_ready=True,
        integrations=["ollama", "openai", "dataforseo"],
    ),
    _module(
        "client-portal",
        "Client Portal",
        "Client Operations",
        "Client reports are unavailable until durable workspace storage, verified analytics sources, scheduled delivery, and production share-link configuration exist.",
        "/seo",
        implemented=False,
        backend_ready=False,
        frontend_ready=False,
        database_ready=False,
        integrations=[],
    ),
    _module(
        "realtime-search-ai-monitoring",
        "Real-Time Search & AI Monitoring",
        "Monitoring & Observability",
        "Realtime engine volatility, visibility tracking, and alerting.",
        "/seo/realtime-monitoring",
        implemented=True,
    ),
    _module(
        "ai-technical-seo-engine",
        "AI Technical SEO Engine",
        "Monitoring & Observability",
        "Autonomous technical SEO diagnosis and remediation.",
        "/seo/technical",
        implemented=True,
    ),
    _module(
        "content-quality-hallucination-auditor",
        "Content Quality & Hallucination Auditor",
        "Monitoring & Observability",
        "Factuality, citation, and answer-quality auditing for AI-assisted content.",
        "/seo/content-auditor",
        implemented=True,
    ),
    _module(
        "knowledge-graph-management",
        "Knowledge Graph Management",
        "Monitoring & Observability",
        "Entity graph construction, enrichment, and validation.",
        "/seo/knowledge-graph",
        implemented=True,
    ),
    _module(
        "ai-internal-linking-engine",
        "AI Internal Linking Engine",
        "Monitoring & Observability",
        "Semantic link opportunity detection and internal authority flow design.",
        "/seo/internal-linking",
        implemented=True,
    ),
    _module(
        "crawl-budget-optimizer",
        "Crawl Budget Optimizer",
        "Monitoring & Observability",
        "Log-based crawl efficiency and priority optimization.",
        "/seo/crawl-budget",
        implemented=True,
    ),
    _module(
        "ai-schema-engine",
        "AI Schema Engine",
        "Schema & Optimization",
        "Automated schema generation, validation, and enhancement.",
        "/seo/schemas",
        implemented=True,
    ),
    _module(
        "ux-conversion-optimizer",
        "UX & Conversion Optimizer",
        "Schema & Optimization",
        "Behavior, conversion, and UX optimization from search traffic.",
        "/seo/ux",
        implemented=True,
    ),
    _module(
        "rag-site-search-engine",
        "Corpus Search Preview",
        "Search Intelligence",
        "Browser-local lexical matching over user-supplied text; connected crawling, semantic indexing, and server search are unavailable.",
        "/seo/rag-search",
        implemented=True,
        backend_ready=False,
        frontend_ready=True,
        database_ready=False,
    ),
    _module(
        "competitor-intelligence-engine",
        "SEO Competitor Research",
        "Search Intelligence",
        "Verified SERP, keyword, traffic, backlink, and AI-answer evidence sources are not connected; competitor metrics are unavailable.",
        "/seo/competitor",
        implemented=False,
        backend_ready=False,
        frontend_ready=True,
    ),
    _module(
        "topical-map-silo-builder",
        "Topical Map & Silo Builder",
        "Content & Distribution",
        "Topic clustering, hub-spoke architecture, and editorial map generation.",
        "/seo/topical-map",
        implemented=True,
    ),
    _module(
        "log-file-analysis-engine",
        "Log File Analysis Engine",
        "Content & Distribution",
        "Crawl-log ingestion, anomaly detection, and bot behavior analysis.",
        "/seo/log-file",
        implemented=True,
    ),
    _module(
        "review-reputation-engine",
        "Review & Reputation Engine",
        "Content & Distribution",
        "Connected review-provider data and durable reputation history are unavailable; no counts, ratings, or themes are generated.",
        "/seo/reviews",
        implemented=False,
        backend_ready=False,
        frontend_ready=False,
        database_ready=False,
    ),
    _module(
        "brand-voice-style-engine",
        "Brand Voice & Style Engine",
        "Content & Distribution",
        "Brand-consistent rewriting and tone governance for SEO content.",
        "/seo/brand-voice",
        implemented=True,
    ),
    _module(
        "accessibility-optimizer",
        "Accessibility Optimizer",
        "Accessibility & Media",
        "WCAG, readability, and assistive discoverability optimization.",
        "/seo/accessibility",
        implemented=True,
    ),
    _module(
        "image-media-seo-engine",
        "Image & Media SEO Engine",
        "Accessibility & Media",
        "Alt text, metadata, compression, and media search optimization.",
        "/seo/media",
        implemented=True,
    ),
    _module(
        "social-seo-distribution",
        "Social SEO & Distribution",
        "Accessibility & Media",
        "Search-aware social distribution and multi-surface promotion.",
        "/seo/social",
        implemented=True,
    ),
    _module(
        "landing-page-builder",
        "Landing Page Builder",
        "Accessibility & Media",
        "Conversion-ready landing pages with schema and experimentation hooks.",
        "/seo/landing",
        implemented=True,
    ),
    _module(
        "security-seo-health-monitor",
        "Security & SEO Health Monitor",
        "Accessibility & Media",
        "Security posture, spam, cloaking, and SEO integrity monitoring.",
        "/seo/security",
        implemented=True,
    ),
    _module(
        "performance-audit",
        "Performance Audit",
        "Performance & Audits",
        "Performance measurements, RUM, history, monitoring, and auto-fix are unavailable until verified providers and tenant-scoped storage are configured.",
        "/seo/performance",
        implemented=False,
    ),
    _module(
        "platform-intelligence",
        "Platform Matrix Score",
        "Performance & Audits",
        "Cross-module health score, SLA compliance, latency matrix, AI governance, anomaly detection, and ranked action items.",
        "/seo/platform-intelligence",
        badge="Core",
        implemented=True,
        integrations=["prometheus", "grafana", "opensearch", "dbt", "deepseek", "llm_pool", "mlflow_patterns"],
    ),
    _module(
        "ahrefs-brand-radar",
        "Ahrefs Parity: Brand Radar",
        "Ahrefs Core Tools",
        "AI-answer-engine visibility, citations, and sentiment intelligence parity.",
        "/seo/brand-radar",
        badge="Parity",
        implemented=True,
        integrations=["answer_engine", "posthog", "openai_embeddings"],
    ),
    _module(
        "ahrefs-custom-prompts",
        "Ahrefs Parity: Custom Prompts",
        "Ahrefs Core Tools",
        "Prompt intelligence and custom query tracking parity.",
        "/seo/custom-prompts",
        badge="Parity",
        implemented=True,
        integrations=["prompt_volumes", "postgres", "redis"],
    ),
    _module(
        "ahrefs-dashboard",
        "Ahrefs Parity: Dashboard",
        "Ahrefs Core Tools",
        "Executive KPI dashboard and multi-module aggregation parity.",
        "/seo/dashboard",
        badge="Parity",
        implemented=True,
        integrations=["analytics_dashboard", "platform_intelligence", "metabase"],
    ),
    _module(
        "ahrefs-site-explorer",
        "Ahrefs Parity: Site Explorer",
        "Ahrefs Core Tools",
        "Domain intelligence parity for organic, paid, backlink, and competitor snapshots.",
        "/seo/site-explorer",
        badge="Parity",
        implemented=True,
        integrations=["domain_overview", "backlink_intelligence", "competitor_analysis"],
    ),
    _module(
        "ahrefs-keywords-explorer",
        "Ahrefs Parity: Keywords Explorer",
        "Ahrefs Core Tools",
        "Keyword research, clustering, and opportunity scoring parity.",
        "/seo/keywords-explorer",
        badge="Parity",
        implemented=True,
        integrations=["seo_platform", "dataforseo", "planner"],
    ),
    _module(
        "ahrefs-site-audit",
        "Ahrefs Parity: Site Audit",
        "Ahrefs Core Tools",
        "Technical crawl and issue remediation parity.",
        "/seo/site-audit",
        badge="Parity",
        implemented=True,
        integrations=["seo_platform", "lighthouse", "playwright_cdp"],
    ),
    _module(
        "ahrefs-rank-tracker",
        "Ahrefs Parity: Rank Tracker",
        "Ahrefs Core Tools",
        "SERP rank movement, volatility, and forecast parity.",
        "/seo/rank-tracker",
        badge="Parity",
        implemented=True,
        integrations=["rank_tracker", "time_series_db", "grafana"],
    ),
    _module(
        "ahrefs-gsc-insights",
        "Ahrefs Parity: GSC Insights",
        "Ahrefs Core Tools",
        "Search-console-style insight rollups and anomaly detection parity.",
        "/seo/gsc-insights",
        badge="Parity",
        implemented=True,
        integrations=["analytics_dashboard", "reporting", "postgres"],
    ),
    _module(
        "ahrefs-content-explorer",
        "Ahrefs Parity: Content Explorer",
        "Ahrefs Core Tools",
        "Content discovery and topic gap analysis parity.",
        "/seo/content-explorer",
        badge="Parity",
        implemented=True,
        integrations=["contentshake", "content_analytics", "dataforseo"],
    ),
    _module(
        "ahrefs-web-analytics",
        "Ahrefs Parity: Web Analytics",
        "Ahrefs Core Tools",
        "Realtime traffic analytics and trend reporting parity.",
        "/seo/analytics",
        badge="Parity",
        implemented=True,
        integrations=["analytics_dashboard", "cdn_analytics", "posthog"],
    ),
    _module(
        "ahrefs-bot-analytics",
        "Ahrefs Parity: Bot Analytics",
        "Ahrefs Core Tools",
        "Crawler and bot behavior observability parity.",
        "/seo/bot-analytics",
        badge="Parity",
        implemented=True,
        integrations=["ai_crawler_enablement", "cdn_analytics", "prometheus"],
    ),
    _module(
        "ahrefs-gbp-monitor",
        "Ahrefs Parity: GBP Monitor",
        "Ahrefs Core Tools",
        "Local business profile and map-rank monitoring parity.",
        "/seo/gbp-monitor",
        badge="Parity",
        implemented=True,
        integrations=["map_rank_tracker", "local_heatmap", "google_places"],
    ),
    _module(
        "ahrefs-social-media-manager",
        "Ahrefs Parity: Social Media Manager",
        "Ahrefs Core Tools",
        "Cross-network social planning, publishing, and analytics parity.",
        "/seo/social-media-manager",
        badge="Parity",
        implemented=True,
        integrations=["social_workspace", "social_posting", "analytics_dashboard"],
    ),
    _module(
        "ahrefs-portfolios",
        "Ahrefs Parity: Portfolios",
        "Ahrefs Core Tools",
        "Multi-site portfolio monitoring and unified KPI portfolio parity.",
        "/seo/portfolios",
        badge="Parity",
        implemented=True,
        integrations=["site_portfolio_manager", "analytics_dashboard", "postgres"],
    ),
    _module(
        "ahrefs-report-builder",
        "Ahrefs Parity: Report Builder",
        "Ahrefs Core Tools",
        "Custom report creation and sharing workflow parity.",
        "/seo/report-builder",
        badge="Parity",
        implemented=True,
        integrations=["client_portal", "analytics_dashboard", "share_links"],
    ),
    _module(
        "ahrefs-ai-content-helper",
        "Ahrefs Parity: AI Content Helper",
        "Ahrefs Core Tools",
        "Keyword-guided content planning and drafting parity.",
        "/seo/ai-content-helper",
        badge="Parity",
        implemented=True,
        integrations=["content-creation-blogging-suite", "ollama", "openai", "dataforseo"],
    ),
    _module(
        "ahrefs-ai-content-grader",
        "Ahrefs Parity: AI Content Grader",
        "Ahrefs Core Tools",
        "Content scoring, factuality review, and rewrite guidance parity.",
        "/seo/ai-content-grader",
        badge="Parity",
        implemented=True,
        integrations=["content-quality-hallucination-auditor", "openai", "posthog", "llama3"],
    ),
    _module(
        "ahrefs-patches",
        "Ahrefs Parity: Patches",
        "Ahrefs Core Tools",
        "Technical fixes and page-level remediation parity.",
        "/seo/patches",
        badge="Parity",
        implemented=True,
        integrations=["ai-technical-seo-engine", "lighthouse", "playwright_cdp", "openlens"],
    ),
    _module(
        "ahrefs-ai-localization",
        "Ahrefs Parity: AI Localization",
        "Ahrefs Core Tools",
        "Translation workflow and locale planning parity.",
        "/seo/ai-localization",
        badge="Parity",
        implemented=True,
        integrations=["international-multilingual-seo", "deepl", "openai", "ollama"],
    ),
]

# These parity entries had no shipped frontend routes or production adapters.
# Keep their catalog metadata visible, but do not present them as implemented.
for _module_record in _SEO_MODULE_REGISTRY_RAW:
    if str(_module_record["key"]).startswith("ahrefs-"):
        _module_record.update(
            implemented=False,
            backend_ready=False,
            frontend_ready=False,
            database_ready=False,
        )


# Apply production-grade enrichment once at import time for all modules.
SEO_MODULE_REGISTRY: list[dict[str, Any]] = [_enrich_module_for_production(item) for item in _SEO_MODULE_REGISTRY_RAW]
SEO_MODULE_MAP: dict[str, dict[str, Any]] = {item["key"]: item for item in SEO_MODULE_REGISTRY}


_AHREFS_CORE_TOOL_MAP: list[dict[str, Any]] = [
    {
        "tool_key": "brand-radar",
        "tool_name": "Brand Radar",
        "parity_module_key": "ahrefs-brand-radar",
        "counterpart_module_key": "realtime-search-ai-monitoring",
        "route_path": "/seo/brand-radar",
    },
    {
        "tool_key": "custom-prompts",
        "tool_name": "Custom Prompts",
        "parity_module_key": "ahrefs-custom-prompts",
        "counterpart_module_key": "analytics-reporting-intelligence",
        "route_path": "/seo/custom-prompts",
    },
    {
        "tool_key": "dashboard",
        "tool_name": "Dashboard",
        "parity_module_key": "ahrefs-dashboard",
        "counterpart_module_key": "platform-intelligence",
        "route_path": "/seo/dashboard",
    },
    {
        "tool_key": "site-explorer",
        "tool_name": "Site Explorer",
        "parity_module_key": "ahrefs-site-explorer",
        "counterpart_module_key": "domain-overview",
        "route_path": "/seo/site-explorer",
    },
    {
        "tool_key": "keywords-explorer",
        "tool_name": "Keywords Explorer",
        "parity_module_key": "ahrefs-keywords-explorer",
        "counterpart_module_key": "seo-ai",
        "route_path": "/seo/keywords-explorer",
    },
    {
        "tool_key": "site-audit",
        "tool_name": "Site Audit",
        "parity_module_key": "ahrefs-site-audit",
        "counterpart_module_key": "ai-technical-seo-engine",
        "route_path": "/seo/site-audit",
    },
    {
        "tool_key": "rank-tracker",
        "tool_name": "Rank Tracker",
        "parity_module_key": "ahrefs-rank-tracker",
        "counterpart_module_key": "advanced-rank-tracking-system",
        "route_path": "/seo/rank-tracker",
    },
    {
        "tool_key": "gsc-insights",
        "tool_name": "GSC Insights",
        "parity_module_key": "ahrefs-gsc-insights",
        "counterpart_module_key": "analytics-reporting-intelligence",
        "route_path": "/seo/gsc-insights",
    },
    {
        "tool_key": "content-explorer",
        "tool_name": "Content Explorer",
        "parity_module_key": "ahrefs-content-explorer",
        "counterpart_module_key": "content-creation-blogging-suite",
        "route_path": "/seo/content-explorer",
    },
    {
        "tool_key": "web-analytics",
        "tool_name": "Web Analytics",
        "parity_module_key": "ahrefs-web-analytics",
        "counterpart_module_key": "analytics-reporting-intelligence",
        "route_path": "/seo/analytics",
    },
    {
        "tool_key": "bot-analytics",
        "tool_name": "Bot Analytics",
        "parity_module_key": "ahrefs-bot-analytics",
        "counterpart_module_key": "realtime-search-ai-monitoring",
        "route_path": "/seo/bot-analytics",
    },
    {
        "tool_key": "gbp-monitor",
        "tool_name": "GBP Monitor",
        "parity_module_key": "ahrefs-gbp-monitor",
        "counterpart_module_key": "map-rank-tracker",
        "route_path": "/seo/gbp-monitor",
    },
    {
        "tool_key": "social-media-manager",
        "tool_name": "Social Media Manager",
        "parity_module_key": "ahrefs-social-media-manager",
        "counterpart_module_key": "social-seo-distribution",
        "route_path": "/seo/social-media-manager",
    },
    {
        "tool_key": "portfolios",
        "tool_name": "Portfolios",
        "parity_module_key": "ahrefs-portfolios",
        "counterpart_module_key": "agency-multi-tenant-platform",
        "route_path": "/seo/portfolios",
    },
    {
        "tool_key": "report-builder",
        "tool_name": "Report Builder",
        "parity_module_key": "ahrefs-report-builder",
        "counterpart_module_key": "client-portal",
        "route_path": "/seo/report-builder",
    },
    {
        "tool_key": "ai-content-helper",
        "tool_name": "AI Content Helper",
        "parity_module_key": "ahrefs-ai-content-helper",
        "counterpart_module_key": "content-creation-blogging-suite",
        "route_path": "/seo/ai-content-helper",
    },
    {
        "tool_key": "ai-content-grader",
        "tool_name": "AI Content Grader",
        "parity_module_key": "ahrefs-ai-content-grader",
        "counterpart_module_key": "content-quality-hallucination-auditor",
        "route_path": "/seo/ai-content-grader",
    },
    {
        "tool_key": "patches",
        "tool_name": "Patches",
        "parity_module_key": "ahrefs-patches",
        "counterpart_module_key": "ai-technical-seo-engine",
        "route_path": "/seo/patches",
    },
    {
        "tool_key": "ai-localization",
        "tool_name": "AI Localization",
        "parity_module_key": "ahrefs-ai-localization",
        "counterpart_module_key": "international-multilingual-seo",
        "route_path": "/seo/ai-localization",
    },
]


def get_ahrefs_core_tool_parity() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in _AHREFS_CORE_TOOL_MAP:
        parity_module = SEO_MODULE_MAP.get(str(item["parity_module_key"]))
        counterpart_module = SEO_MODULE_MAP.get(str(item["counterpart_module_key"]))
        vendors = _merge_unique(
            list(parity_module.get("integrations", [])) if isinstance(parity_module, dict) else [],
            list(counterpart_module.get("integrations", [])) if isinstance(counterpart_module, dict) else [],
        )
        implementation_ready = bool(
            parity_module
            and parity_module.get("implemented")
            and parity_module.get("backend_ready")
            and parity_module.get("frontend_ready")
            and parity_module.get("database_ready")
        )
        coverage_pct = (
            100.0
            if implementation_ready and bool(counterpart_module) and bool(vendors) and bool(item.get("route_path"))
            else 0.0
        )
        rows.append(
            {
                "tool_key": item["tool_key"],
                "tool_name": item["tool_name"],
                "route_path": item["route_path"],
                "parity_module_key": item["parity_module_key"],
                "counterpart_module_key": item["counterpart_module_key"],
                "parity_module_present": bool(parity_module),
                "parity_module_implemented": implementation_ready,
                "implementation_status": "available" if coverage_pct == 100.0 else "unavailable",
                "counterpart_module_present": bool(counterpart_module),
                "vendors": vendors,
                "coverage_pct": coverage_pct,
            }
        )
    return rows


def audit_ahrefs_core_tool_parity() -> dict[str, Any]:
    rows = get_ahrefs_core_tool_parity()
    missing_parity_modules = [row["parity_module_key"] for row in rows if not bool(row.get("parity_module_present"))]
    missing_counterparts = [
        row["counterpart_module_key"] for row in rows if not bool(row.get("counterpart_module_present"))
    ]
    unavailable_parity_modules = [
        row["parity_module_key"] for row in rows if row.get("implementation_status") != "available"
    ]
    average_coverage = (
        round(
            sum(float(row.get("coverage_pct", 0.0)) for row in rows) / len(rows),
            2,
        )
        if rows
        else 0.0
    )
    return {
        "total_tools": len(rows),
        "missing_parity_modules": sorted(set(missing_parity_modules)),
        "missing_counterparts": sorted(set(missing_counterparts)),
        "unavailable_parity_modules": sorted(set(unavailable_parity_modules)),
        "average_coverage_pct": average_coverage,
        "fully_covered_tools": sum(1 for row in rows if float(row.get("coverage_pct", 0.0)) >= 100.0),
        "rows": rows,
    }


def grouped_seo_modules(modules: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = {}
    source = SEO_MODULE_REGISTRY if modules is None else modules
    for item in source:
        groups.setdefault(str(item["group"]), []).append(item)

    return [{"group": group, "items": items} for group, items in groups.items()]
