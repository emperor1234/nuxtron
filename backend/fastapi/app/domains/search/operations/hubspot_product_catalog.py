"""Search use cases: hubspot product catalog."""

from ..constants import AuthDep
from ..runtime import SearchRuntime
from ..schemas import SemrushFullAutomationRequest
from ..schemas import SitebulbProjectRunRequest
from ..schemas import SitebulbRemediationBundleRequest
from ..schemas import SitebulbScheduleExecuteRequest
from .platform_now_iso import helper_now_iso
from .semrush_list_projects import operation_semrush_full_automation
from .sitebulb_completion_chart import helper_sitebulb_completion_chart
from .sitebulb_completion_chart import helper_sitebulb_gate_progress
from .sitebulb_completion_chart import helper_sitebulb_gate_state
from .sitebulb_completion_chart import helper_sitebulb_remediation_bundle
from .sitebulb_completion_chart import operation_sitebulb_execute_schedules
from .sitebulb_completion_chart import operation_sitebulb_run_project
from .sitebulb_project_lookup import helper_sitebulb_vendor_inventory
from .sitebulb_remediation_bundle_export import helper_sitebulb_remediation_bundle_export
from fastapi import Query
from typing import Annotated
from typing import Any


def helper_hubspot_product_catalog() -> list[dict[str, Any]]:
    return [
        {
            "key": "marketing-hub",
            "name": "Marketing Hub",
            "description": "AI-powered marketing software that helps generate leads and automate marketing.",
            "premium_features": [
                "AI-powered lead generation tools",
                "SEO",
                "Omni-channel marketing automation",
                "Breeze social post agent (Beta)",
                "Campaign management",
                "Custom reporting and advanced analytics",
            ],
            "vendors": ["Google Search Console", "Google Ads", "Meta", "LinkedIn", "HubSpot"],
        },
        {
            "key": "sales-hub",
            "name": "Sales Hub",
            "description": "Easy-to-adopt sales software that leverages AI to build pipelines and close deals.",
            "premium_features": [
                "AI-powered Smart CRM",
                "Sales workspace",
                "Breeze prospecting agent",
                "Sales sequences and automation",
                "Custom objects",
                "Forecasting",
                "Predictive lead scoring",
                "Playbooks",
            ],
            "vendors": ["HubSpot", "LinkedIn", "Gmail", "Outlook", "ZoomInfo"],
        },
        {
            "key": "service-hub",
            "name": "Service Hub",
            "description": "Customer service software powered by AI to scale support and drive retention.",
            "premium_features": [
                "Help desk workspace",
                "Customer success workspace",
                "Customer feedback management",
                "Knowledge base",
                "Capacity and skill-based routing",
                "Custom support form fields",
                "Multiple ticket pipelines",
            ],
            "vendors": ["HubSpot", "Slack", "Twilio", "Intercom", "Zendesk"],
        },
        {
            "key": "content-hub",
            "name": "Content Hub",
            "description": "All-in-one AI-powered content marketing software to create and manage content.",
            "premium_features": [
                "Landing pages",
                "Content remix (Beta)",
                "Brand voice (Beta)",
                "Blog software",
                "Podcasts",
                "Website builder",
                "Custom portals and gated content",
            ],
            "vendors": ["HubSpot", "WordPress", "YouTube", "Spotify", "Cloudflare"],
        },
        {
            "key": "data-hub",
            "name": "Data Hub",
            "description": "Data management software that combines data and enhances data quality with AI.",
            "premium_features": [
                "Programmable automation",
                "Data quality automation",
                "Data studio",
                "Data share",
                "Scheduled workflow triggers",
                "AI-powered data quality automation",
            ],
            "vendors": ["HubSpot", "Snowflake", "BigQuery", "Databricks", "Fivetran"],
        },
        {
            "key": "commerce-hub",
            "name": "Commerce Hub",
            "description": "B2B commerce software for collecting payments and automating billing.",
            "premium_features": [
                "HubSpot payments",
                "E-signature",
                "Custom billing automation",
                "Simple revenue reporting",
                "Custom revenue reporting",
                "QuickBooks integration",
            ],
            "vendors": ["HubSpot", "Stripe", "PayPal", "QuickBooks", "DocuSign"],
        },
        {
            "key": "smart-crm",
            "name": "Smart CRM",
            "description": "Central source of customer intelligence connecting data, teams, and tools.",
            "premium_features": [
                "Custom data model",
                "Data enrichment",
                "Data agent (Beta)",
                "Sensitive data",
                "Custom reporting",
                "Team governance",
                "Automatic duplicate detection",
                "Data sync",
                "CRM interface configuration",
            ],
            "vendors": ["HubSpot", "Clearbit", "Apollo", "Salesforce", "Microsoft Dynamics"],
        },
        {
            "key": "breeze",
            "name": "Breeze",
            "description": "AI agents, assistants, and embedded features across the customer platform.",
            "premium_features": [
                "Breeze marketplace",
                "Breeze studio",
                "Customer agent",
                "Prospecting agent",
                "Data agent",
                "Closing agent",
                "Custom assistants",
            ],
            "vendors": ["HubSpot", "OpenAI", "Anthropic", "Ollama", "Azure OpenAI"],
        },
        {
            "key": "small-business-bundle",
            "name": "Small Business Bundle",
            "description": "Starter edition bundle for startups and small businesses.",
            "premium_features": [
                "Website pages",
                "AI content writer",
                "Email automation",
                "Contact management",
                "Deal pipelines",
                "Commerce tools",
                "Chatbots",
                "Ticketing",
                "Analytics",
            ],
            "vendors": ["HubSpot", "Stripe", "Google Analytics", "Meta", "WhatsApp"],
        },
        {
            "key": "free-tools",
            "name": "Free Tools",
            "description": "Entry-level tools available across HubSpot products.",
            "premium_features": [
                "Forms",
                "Email marketing",
                "Live chat",
                "Contact management",
                "Deal tracking",
                "Ad tracking",
                "Landing pages",
                "Ticketing",
                "Meeting scheduling",
                "Basic analytics",
            ],
            "vendors": ["HubSpot", "Google", "Meta", "LinkedIn", "Cloudflare"],
        },
    ]


def helper_hubspot_product_route_contract() -> dict[str, list[str]]:
    return {
        "marketing-hub": [
            "/search-everywhere/hubspot/full-automation",
            "/search-everywhere/hubspot/projects",
            "/search-everywhere/hubspot/projects/{project_id}/run",
        ],
        "sales-hub": [
            "/search-everywhere/hubspot/products/{product_key}/run",
            "/search-everywhere/hubspot/crm/contacts",
            "/search-everywhere/hubspot/crm/deals",
        ],
        "service-hub": [
            "/search-everywhere/hubspot/service/tickets",
            "/search-everywhere/hubspot/service/knowledge-base/articles",
            "/search-everywhere/hubspot/service/surveys",
        ],
        "content-hub": [
            "/search-everywhere/hubspot/content/landing-pages",
            "/search-everywhere/hubspot/content/blog-posts",
            "/search-everywhere/hubspot/content/podcasts",
        ],
        "data-hub": [
            "/search-everywhere/hubspot/data/sync-jobs",
            "/search-everywhere/hubspot/data/quality-rules",
            "/search-everywhere/hubspot/wiring/apply",
        ],
        "commerce-hub": [
            "/search-everywhere/hubspot/commerce/products",
            "/search-everywhere/hubspot/commerce/documents",
            "/search-everywhere/hubspot/products/{product_key}/run",
        ],
        "smart-crm": [
            "/search-everywhere/hubspot/crm/contacts",
            "/search-everywhere/hubspot/crm/companies",
            "/search-everywhere/hubspot/crm/deals",
        ],
        "breeze": [
            "/search-everywhere/hubspot/products/{product_key}/run",
            "/search-everywhere/hubspot/full-automation",
        ],
        "small-business-bundle": [
            "/search-everywhere/hubspot/products/{product_key}/run",
            "/search-everywhere/hubspot/schedules",
            "/search-everywhere/hubspot/schedules/execute",
        ],
        "free-tools": [
            "/search-everywhere/hubspot/products/{product_key}/run",
            "/search-everywhere/hubspot/completion-chart",
        ],
    }


def helper_hubspot_route_registry(runtime: SearchRuntime) -> set[str]:
    return {str(route.path) for route in runtime.router.routes}


def operation_hubspot_run_project(
    runtime: SearchRuntime, project_id: str, payload: dict[str, Any], auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:hubspot:runs:create", 30, 60)
    competitor_domains = payload.get("competitor_domains")
    competitors = [str(item) for item in competitor_domains] if isinstance(competitor_domains, list) else None
    return operation_sitebulb_run_project(
        runtime,
        project_id,
        SitebulbProjectRunRequest(
            seed_keyword=str(payload.get("seed_keyword")) if payload.get("seed_keyword") else None,
            competitor_domains=competitors,
            max_results=int(payload.get("max_results") or 20),
            require_live_providers=bool(payload.get("require_live_providers", False)),
        ),
        auth,
    )


def operation_hubspot_gate_progress(runtime: SearchRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:hubspot:gate-progress", 60, 60)
    return helper_sitebulb_gate_progress(runtime, auth)


def operation_hubspot_full_automation(
    runtime: SearchRuntime, payload: SemrushFullAutomationRequest, auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:hubspot:full-automation", 30, 60)
    base_result = operation_semrush_full_automation(runtime, payload, auth)
    completion = helper_sitebulb_completion_chart(runtime, auth)
    gate_state = helper_sitebulb_gate_state(runtime, auth)
    vendor_inventory = helper_sitebulb_vendor_inventory(runtime, auth)
    vendor_inventory.append(
        {
            "domain": "go-to-market",
            "vendor": "HubSpot",
            "capability": "CRM, automation, and campaign orchestration layer",
            "configured": True,
            "evidence": "search_everywhere hubspot full automation mapping",
        }
    )
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "run_mode": base_result.get("run_mode"),
        "results": {
            "search_demand_and_intent": base_result.get("results", {}).get("keyword_discovery", {}),
            "content_strategy_and_gaps": base_result.get("results", {}).get("content_gap", {}),
            "authority_backlink_and_competitor_context": base_result.get("results", {}).get("backlink_audit", {}),
            "prioritized_growth_actions": base_result.get("results", {}).get("backlink_gap", {}),
            "parity_summary": base_result.get("results", {}).get("parity_summary", {}),
        },
        "hubspot_modules": {
            "attract": ["topic and keyword discovery", "SERP and competitor monitoring", "content opportunity scoring"],
            "engage": [
                "campaign brief generation",
                "landing page and conversion flow recommendations",
                "persona-driven optimization",
            ],
            "delight": ["retention play triggers", "CRM handoff suggestions", "pipeline-impact visibility"],
            "content": ["landing pages", "blog posts", "podcast episodes", "content calendar execution"],
            "data": ["sync job orchestration", "data quality rules", "automation governance"],
            "operations": ["provider checklist", "gate progress", "remediation bundle", "verification report"],
        },
        "completion_summary": completion.get("summary", {}),
        "production_gate": gate_state.get("gate", {}),
        "third_parties_and_vendors": vendor_inventory,
        "how_it_works": [
            "Intent and SERP intelligence prioritizes the highest-value acquisition opportunities.",
            "Content and conversion recommendations align acquisition with CRM lifecycle outcomes.",
            "Authority and competitor signals shape campaign sequencing and channel emphasis.",
            "Provider checklist, strict-live probe, and production gate enforce release readiness.",
        ],
        "generated_at": helper_now_iso(),
    }


def operation_hubspot_execute_schedules(
    runtime: SearchRuntime, payload: SitebulbScheduleExecuteRequest, auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:hubspot:schedules:execute", 20, 60)
    return operation_sitebulb_execute_schedules(runtime, payload, auth)


def operation_hubspot_remediation_bundle(
    runtime: SearchRuntime, payload: SitebulbRemediationBundleRequest, auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:hubspot:remediation-bundle", 30, 60)
    return helper_sitebulb_remediation_bundle(runtime, payload, auth)


def operation_hubspot_remediation_bundle_export(
    runtime: SearchRuntime,
    auth: AuthDep,
    format: Annotated[str, Query(pattern="^(json|csv)$")] = "json",
    top_steps: int = Query(default=12, ge=1, le=100),
    include_optional: bool = Query(default=False),
    include_configured: bool = Query(default=False),
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:hubspot:remediation-bundle:export", 30, 60)
    payload = SitebulbRemediationBundleRequest(
        top_steps=top_steps, include_optional=include_optional, include_configured=include_configured
    )
    return helper_sitebulb_remediation_bundle_export(runtime, payload, auth, format)
