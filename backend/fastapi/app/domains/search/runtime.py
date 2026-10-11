"""Explicit application-owned provider adapters and development stores."""

from dataclasses import dataclass
from collections.abc import Callable
from typing import Any


@dataclass
class SearchRuntime:
    ace_sites_memory: list[dict[str, Any]]
    botify_projects_memory: list[dict[str, Any]]
    botify_runs_memory: list[dict[str, Any]]
    botify_schedules_memory: list[dict[str, Any]]
    brightedge_wired_tenants: set[str]
    clearscope_wired_tenants: set[str]
    cms_connections_memory: list[dict[str, Any]]
    enforce_rate_limit: Callable[[str, int, int], None]
    geoptie_wired_tenants: set[str]
    hootsuite_wired_tenants: set[str]
    hubspot_blog_posts_memory: dict[str, list[dict[str, Any]]]
    hubspot_companies_memory: dict[str, list[dict[str, Any]]]
    hubspot_contacts_memory: dict[str, list[dict[str, Any]]]
    hubspot_data_quality_rules_memory: dict[str, list[dict[str, Any]]]
    hubspot_data_sync_jobs_memory: dict[str, list[dict[str, Any]]]
    hubspot_deals_memory: dict[str, list[dict[str, Any]]]
    hubspot_documents_memory: dict[str, list[dict[str, Any]]]
    hubspot_knowledge_base_memory: dict[str, list[dict[str, Any]]]
    hubspot_landing_pages_memory: dict[str, list[dict[str, Any]]]
    hubspot_podcasts_memory: dict[str, list[dict[str, Any]]]
    hubspot_products_memory: dict[str, list[dict[str, Any]]]
    hubspot_surveys_memory: dict[str, list[dict[str, Any]]]
    hubspot_tickets_memory: dict[str, list[dict[str, Any]]]
    marketmuse_wired_tenants: set[str]
    neuronwriter_projects_memory: list[dict[str, Any]]
    neuronwriter_runs_memory: list[dict[str, Any]]
    neuronwriter_wired_tenants: set[str]
    promptwatch_wired_tenants: set[str]
    router: Any
    semrush_projects_memory: list[dict[str, Any]]
    semrush_runs_memory: list[dict[str, Any]]
    seoai_projects_memory: list[dict[str, Any]]
    seoai_runs_memory: list[dict[str, Any]]
    seoai_schedules_memory: list[dict[str, Any]]
    seoai_wired_tenants: set[str]
    sitebulb_projects_memory: list[dict[str, Any]]
    sitebulb_runs_memory: list[dict[str, Any]]
    sitebulb_schedules_memory: list[dict[str, Any]]
    vendor_manager: Any
    writesonic_wired_tenants: set[str]
    yext_wired_tenants: set[str]
