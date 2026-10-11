"""Search automation composition with explicit provider-owned runtime state."""

from collections.abc import Callable
from typing import Any
from fastapi import APIRouter
from ...integrations.vendor_manager import get_vendor_manager
from .runtime import SearchRuntime
from .api import (
    cost_savings_calculator,
    airanklab_wiring_required_keys,
    semrush_list_projects,
    semrush_full_automation,
    ahrefs_full_automation,
    surfer_env_template,
    frase_provider_probes,
    sitebulb_create_schedule,
    botify_run_project,
    botify_env_template,
    seoai_run_project,
    seoai_env_template,
    neuronwriter_wiring_apply,
    neuronwriter_runs,
    clearscope_production_gate,
    hubspot_service_list_tickets,
    hubspot_commerce_list_documents,
    hubspot_content_list_landing_pages,
    hubspot_data_list_quality_rules,
    hubspot_provider_checklist,
    hubspot_list_runs,
    hubspot_env_template,
    hootsuite_features_automation,
    hootsuite_provider_checklist,
    hootsuite_get_run,
    hootsuite_completion_chart,
    yext_products_completion_chart,
    yext_create_project,
    yext_vendors,
    yext_assist_chat,
    brightedge_parity_audit,
    brightedge_list_runs,
    brightedge_env_template,
    writesonic_product_detail,
    writesonic_wiring_state,
    writesonic_create_schedule,
    writesonic_production_gate,
    geoptie_products_completion_chart,
    geoptie_create_project,
    geoptie_vendors,
    geoptie_assist_chat,
    promptwatch_parity_audit,
    promptwatch_list_runs,
    promptwatch_env_template,
    marketmuse_product_detail,
    marketmuse_wiring_apply,
    marketmuse_list_schedules,
    marketmuse_remediation_bundle,
    sitebulb_verification_report,
)


def create_search_everywhere_automation_router(
    *,
    enforce_rate_limit: Callable[[str, int, int], None],
    ace_sites_memory: list[dict[str, Any]],
    cms_connections_memory: list[dict[str, Any]],
) -> APIRouter:
    router = APIRouter(prefix="/search-everywhere", tags=["Search Everywhere Automation"])
    vendor_manager = get_vendor_manager()
    sitebulb_projects_memory: list[dict[str, Any]] = []
    sitebulb_runs_memory: list[dict[str, Any]] = []
    sitebulb_schedules_memory: list[dict[str, Any]] = []
    botify_projects_memory: list[dict[str, Any]] = []
    botify_runs_memory: list[dict[str, Any]] = []
    botify_schedules_memory: list[dict[str, Any]] = []
    semrush_projects_memory: list[dict[str, Any]] = []
    semrush_runs_memory: list[dict[str, Any]] = []
    seoai_projects_memory: list[dict[str, Any]] = []
    seoai_runs_memory: list[dict[str, Any]] = []
    seoai_schedules_memory: list[dict[str, Any]] = []
    neuronwriter_projects_memory: list[dict[str, Any]] = []
    neuronwriter_runs_memory: list[dict[str, Any]] = []
    seoai_wired_tenants: set[str] = set()
    yext_wired_tenants: set[str] = set()
    brightedge_wired_tenants: set[str] = set()
    writesonic_wired_tenants: set[str] = set()
    geoptie_wired_tenants: set[str] = set()
    promptwatch_wired_tenants: set[str] = set()
    marketmuse_wired_tenants: set[str] = set()
    neuronwriter_wired_tenants: set[str] = set()
    clearscope_wired_tenants: set[str] = set()
    hootsuite_wired_tenants: set[str] = set()
    hubspot_tickets_memory: dict[str, list[dict[str, Any]]] = {}
    hubspot_knowledge_base_memory: dict[str, list[dict[str, Any]]] = {}
    hubspot_surveys_memory: dict[str, list[dict[str, Any]]] = {}
    hubspot_products_memory: dict[str, list[dict[str, Any]]] = {}
    hubspot_documents_memory: dict[str, list[dict[str, Any]]] = {}
    hubspot_contacts_memory: dict[str, list[dict[str, Any]]] = {}
    hubspot_companies_memory: dict[str, list[dict[str, Any]]] = {}
    hubspot_deals_memory: dict[str, list[dict[str, Any]]] = {}
    hubspot_landing_pages_memory: dict[str, list[dict[str, Any]]] = {}
    hubspot_blog_posts_memory: dict[str, list[dict[str, Any]]] = {}
    hubspot_podcasts_memory: dict[str, list[dict[str, Any]]] = {}
    hubspot_data_sync_jobs_memory: dict[str, list[dict[str, Any]]] = {}
    hubspot_data_quality_rules_memory: dict[str, list[dict[str, Any]]] = {}
    runtime = SearchRuntime(
        ace_sites_memory=ace_sites_memory,
        botify_projects_memory=botify_projects_memory,
        botify_runs_memory=botify_runs_memory,
        botify_schedules_memory=botify_schedules_memory,
        brightedge_wired_tenants=brightedge_wired_tenants,
        clearscope_wired_tenants=clearscope_wired_tenants,
        cms_connections_memory=cms_connections_memory,
        enforce_rate_limit=enforce_rate_limit,
        geoptie_wired_tenants=geoptie_wired_tenants,
        hootsuite_wired_tenants=hootsuite_wired_tenants,
        hubspot_blog_posts_memory=hubspot_blog_posts_memory,
        hubspot_companies_memory=hubspot_companies_memory,
        hubspot_contacts_memory=hubspot_contacts_memory,
        hubspot_data_quality_rules_memory=hubspot_data_quality_rules_memory,
        hubspot_data_sync_jobs_memory=hubspot_data_sync_jobs_memory,
        hubspot_deals_memory=hubspot_deals_memory,
        hubspot_documents_memory=hubspot_documents_memory,
        hubspot_knowledge_base_memory=hubspot_knowledge_base_memory,
        hubspot_landing_pages_memory=hubspot_landing_pages_memory,
        hubspot_podcasts_memory=hubspot_podcasts_memory,
        hubspot_products_memory=hubspot_products_memory,
        hubspot_surveys_memory=hubspot_surveys_memory,
        hubspot_tickets_memory=hubspot_tickets_memory,
        marketmuse_wired_tenants=marketmuse_wired_tenants,
        neuronwriter_projects_memory=neuronwriter_projects_memory,
        neuronwriter_runs_memory=neuronwriter_runs_memory,
        neuronwriter_wired_tenants=neuronwriter_wired_tenants,
        promptwatch_wired_tenants=promptwatch_wired_tenants,
        router=router,
        semrush_projects_memory=semrush_projects_memory,
        semrush_runs_memory=semrush_runs_memory,
        seoai_projects_memory=seoai_projects_memory,
        seoai_runs_memory=seoai_runs_memory,
        seoai_schedules_memory=seoai_schedules_memory,
        seoai_wired_tenants=seoai_wired_tenants,
        sitebulb_projects_memory=sitebulb_projects_memory,
        sitebulb_runs_memory=sitebulb_runs_memory,
        sitebulb_schedules_memory=sitebulb_schedules_memory,
        vendor_manager=vendor_manager,
        writesonic_wired_tenants=writesonic_wired_tenants,
        yext_wired_tenants=yext_wired_tenants,
    )
    cost_savings_calculator.register(router, runtime)
    airanklab_wiring_required_keys.register(router, runtime)
    semrush_list_projects.register(router, runtime)
    semrush_full_automation.register(router, runtime)
    ahrefs_full_automation.register(router, runtime)
    surfer_env_template.register(router, runtime)
    frase_provider_probes.register(router, runtime)
    sitebulb_create_schedule.register(router, runtime)
    botify_run_project.register(router, runtime)
    botify_env_template.register(router, runtime)
    seoai_run_project.register(router, runtime)
    seoai_env_template.register(router, runtime)
    neuronwriter_wiring_apply.register(router, runtime)
    neuronwriter_runs.register(router, runtime)
    clearscope_production_gate.register(router, runtime)
    hubspot_service_list_tickets.register(router, runtime)
    hubspot_commerce_list_documents.register(router, runtime)
    hubspot_content_list_landing_pages.register(router, runtime)
    hubspot_data_list_quality_rules.register(router, runtime)
    hubspot_provider_checklist.register(router, runtime)
    hubspot_list_runs.register(router, runtime)
    hubspot_env_template.register(router, runtime)
    hootsuite_features_automation.register(router, runtime)
    hootsuite_provider_checklist.register(router, runtime)
    hootsuite_get_run.register(router, runtime)
    hootsuite_completion_chart.register(router, runtime)
    yext_products_completion_chart.register(router, runtime)
    yext_create_project.register(router, runtime)
    yext_vendors.register(router, runtime)
    yext_assist_chat.register(router, runtime)
    brightedge_parity_audit.register(router, runtime)
    brightedge_list_runs.register(router, runtime)
    brightedge_env_template.register(router, runtime)
    writesonic_product_detail.register(router, runtime)
    writesonic_wiring_state.register(router, runtime)
    writesonic_create_schedule.register(router, runtime)
    writesonic_production_gate.register(router, runtime)
    geoptie_products_completion_chart.register(router, runtime)
    geoptie_create_project.register(router, runtime)
    geoptie_vendors.register(router, runtime)
    geoptie_assist_chat.register(router, runtime)
    promptwatch_parity_audit.register(router, runtime)
    promptwatch_list_runs.register(router, runtime)
    promptwatch_env_template.register(router, runtime)
    marketmuse_product_detail.register(router, runtime)
    marketmuse_wiring_apply.register(router, runtime)
    marketmuse_list_schedules.register(router, runtime)
    marketmuse_remediation_bundle.register(router, runtime)
    sitebulb_verification_report.register(router, runtime)
    return router
