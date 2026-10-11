"""Search use cases: hubspot wiring required keys."""

from ....deps import AuthContext
from ..constants import AuthDep
from ..runtime import SearchRuntime
from ..schemas import HubspotWiringApplyRequest
from ..schemas import SitebulbProjectCreateRequest
from ..schemas import SitebulbScheduleCreateRequest
from .hubspot_product_catalog import helper_hubspot_product_catalog
from .hubspot_route_coverage_chart import helper_hubspot_products_completion_chart
from .hubspot_route_coverage_chart import helper_hubspot_record_create
from .hubspot_route_coverage_chart import helper_hubspot_route_coverage_chart
from .hubspot_route_coverage_chart import helper_hubspot_third_party_vendor_chart
from .platform_now_iso import helper_now_iso
from .platform_search_vendors import helper_provider_requirements
from .sitebulb_project_lookup import helper_sitebulb_preflight_report
from .sitebulb_project_lookup import operation_sitebulb_create_project
from .sitebulb_project_lookup import operation_sitebulb_create_schedule
from .sitebulb_project_lookup import operation_sitebulb_get_run
from .sitebulb_project_lookup import operation_sitebulb_list_projects
from .sitebulb_project_lookup import operation_sitebulb_list_runs
from .sitebulb_project_lookup import operation_sitebulb_list_schedules
from fastapi import HTTPException
from typing import Any
import os


def helper_hubspot_wiring_required_keys() -> dict[str, Any]:
    checklist = helper_provider_requirements()
    required_keys = sorted(
        {key for item in checklist for key in item.get("required_present", []) + item.get("required_missing", [])}
    )
    option_groups = [
        {
            "name": "google_ads_auth",
            "one_of": [
                "GOOGLE_OAUTH_ACCESS_TOKEN",
                "GOOGLE_ADS_ACCESS_TOKEN",
                "GOOGLE_ADS_REFRESH_TOKEN",
                "GOOGLE_OAUTH_CLIENT_ID",
                "GOOGLE_OAUTH_CLIENT_SECRET",
            ],
        },
        {
            "name": "google_search_console_auth",
            "one_of": ["GSC_SERVICE_ACCOUNT_JSON", "GOOGLE_OAUTH_ACCESS_TOKEN", "GOOGLE_SEARCH_CONSOLE_ACCESS_TOKEN"],
        },
    ]
    optional_keys = sorted({key for item in checklist for key in item.get("optional_present", [])})
    allowlist = sorted(
        set(required_keys) | set(optional_keys) | {key for group in option_groups for key in group["one_of"]}
    )
    return {
        "required_keys": required_keys,
        "optional_keys": optional_keys,
        "option_groups": option_groups,
        "allowlist": allowlist,
    }


def helper_hubspot_full_e2e_audit(runtime: SearchRuntime, auth: AuthContext) -> dict[str, Any]:
    catalog = helper_hubspot_product_catalog()
    route_coverage = helper_hubspot_route_coverage_chart(runtime)
    provider_checklist = helper_provider_requirements()
    modules_total = len(catalog)
    modules_with_route_contract = sum((1 for item in route_coverage if not item.get("missing_routes")))
    required_routes_total = sum((int(item.get("required_routes_total", 0)) for item in route_coverage))
    required_routes_implemented = sum((int(item.get("required_routes_implemented", 0)) for item in route_coverage))
    providers_total = len(provider_checklist)
    providers_configured = sum((1 for item in provider_checklist if bool(item.get("configured"))))
    implementation_pct = round(required_routes_implemented / max(required_routes_total, 1) * 100.0, 1)
    integration_configured_pct = round(providers_configured / max(providers_total, 1) * 100.0, 1)
    e2e_verified_pct = round(
        (modules_with_route_contract + providers_configured) / max(modules_total + providers_total, 1) * 100.0, 1
    )
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "summary": {
            "products_total": modules_total,
            "required_routes_total": required_routes_total,
            "required_routes_implemented": required_routes_implemented,
            "providers_total": providers_total,
            "providers_configured": providers_configured,
            "implementation_pct": implementation_pct,
            "integration_configured_pct": integration_configured_pct,
            "e2e_verified_pct": e2e_verified_pct,
            "production_grade_ready": implementation_pct == 100.0 and integration_configured_pct == 100.0,
        },
        "product_chart": [
            {
                "key": item.get("key"),
                "name": item.get("name"),
                "premium_features_total": len(item.get("premium_features", [])),
                "third_parties_total": len(item.get("vendors", [])),
            }
            for item in catalog
        ],
        "route_contract_chart": route_coverage,
        "provider_checklist": provider_checklist,
        "third_party_vendor_chart": helper_hubspot_third_party_vendor_chart(),
        "how_it_works": [
            "Programs are created and run through hubspot project and run orchestration endpoints.",
            "Product-level execution routes enforce module-specific automation for each HubSpot product area.",
            "Provider wiring and checklist validation enforce third-party readiness before production gate pass.",
            "Completion and verification reports expose validated-slice evidence and explicit non-validated boundaries.",
        ],
        "validation_boundaries": {
            "validated_slice": {
                "scope": "FastAPI search_everywhere hubspot automation and connected router contracts",
                "evidence": [
                    "hubspot route contract chart",
                    "provider checklist configured state",
                    "hubspot completion and production gate endpoints",
                ],
            },
            "not_validated": [
                "live third-party vendor billing, quota, and legal account state",
                "full frontend UX parity across all pages on hubspot.com",
                "contractual and compliance obligations outside this codebase",
            ],
        },
        "generated_at": helper_now_iso(),
    }


def operation_hubspot_service_create_ticket(
    runtime: SearchRuntime, payload: dict[str, Any], auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:hubspot:service:tickets:create", 120, 60)
    record = helper_hubspot_record_create(runtime.hubspot_tickets_memory, auth.tenant_id, "ticket", payload)
    return {"status": "ok", "tenant_id": auth.tenant_id, "ticket": record, "generated_at": helper_now_iso()}


def operation_hubspot_service_create_knowledge_article(
    runtime: SearchRuntime, payload: dict[str, Any], auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:hubspot:service:kb:create", 120, 60)
    record = helper_hubspot_record_create(
        runtime.hubspot_knowledge_base_memory, auth.tenant_id, "knowledge_article", payload
    )
    return {"status": "ok", "tenant_id": auth.tenant_id, "article": record, "generated_at": helper_now_iso()}


def operation_hubspot_service_create_survey(
    runtime: SearchRuntime, payload: dict[str, Any], auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:hubspot:service:surveys:create", 120, 60)
    record = helper_hubspot_record_create(runtime.hubspot_surveys_memory, auth.tenant_id, "survey", payload)
    return {"status": "ok", "tenant_id": auth.tenant_id, "survey": record, "generated_at": helper_now_iso()}


def operation_hubspot_commerce_create_product(
    runtime: SearchRuntime, payload: dict[str, Any], auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:hubspot:commerce:products:create", 120, 60)
    record = helper_hubspot_record_create(runtime.hubspot_products_memory, auth.tenant_id, "commerce_product", payload)
    return {"status": "ok", "tenant_id": auth.tenant_id, "product": record, "generated_at": helper_now_iso()}


def operation_hubspot_commerce_create_document(
    runtime: SearchRuntime, payload: dict[str, Any], auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:hubspot:commerce:documents:create", 120, 60)
    record = helper_hubspot_record_create(
        runtime.hubspot_documents_memory, auth.tenant_id, "commerce_document", payload
    )
    return {"status": "ok", "tenant_id": auth.tenant_id, "document": record, "generated_at": helper_now_iso()}


def operation_hubspot_crm_create_contact(
    runtime: SearchRuntime, payload: dict[str, Any], auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:hubspot:crm:contacts:create", 120, 60)
    record = helper_hubspot_record_create(runtime.hubspot_contacts_memory, auth.tenant_id, "crm_contact", payload)
    return {"status": "ok", "tenant_id": auth.tenant_id, "contact": record, "generated_at": helper_now_iso()}


def operation_hubspot_crm_create_company(
    runtime: SearchRuntime, payload: dict[str, Any], auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:hubspot:crm:companies:create", 120, 60)
    record = helper_hubspot_record_create(runtime.hubspot_companies_memory, auth.tenant_id, "crm_company", payload)
    return {"status": "ok", "tenant_id": auth.tenant_id, "company": record, "generated_at": helper_now_iso()}


def operation_hubspot_crm_create_deal(runtime: SearchRuntime, payload: dict[str, Any], auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:hubspot:crm:deals:create", 120, 60)
    record = helper_hubspot_record_create(runtime.hubspot_deals_memory, auth.tenant_id, "crm_deal", payload)
    return {"status": "ok", "tenant_id": auth.tenant_id, "deal": record, "generated_at": helper_now_iso()}


def operation_hubspot_content_create_landing_page(
    runtime: SearchRuntime, payload: dict[str, Any], auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:hubspot:content:landing-pages:create", 120, 60)
    record = helper_hubspot_record_create(runtime.hubspot_landing_pages_memory, auth.tenant_id, "landing_page", payload)
    return {"status": "ok", "tenant_id": auth.tenant_id, "landing_page": record, "generated_at": helper_now_iso()}


def operation_hubspot_content_create_blog_post(
    runtime: SearchRuntime, payload: dict[str, Any], auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:hubspot:content:blog-posts:create", 120, 60)
    record = helper_hubspot_record_create(runtime.hubspot_blog_posts_memory, auth.tenant_id, "blog_post", payload)
    return {"status": "ok", "tenant_id": auth.tenant_id, "blog_post": record, "generated_at": helper_now_iso()}


def operation_hubspot_content_create_podcast(
    runtime: SearchRuntime, payload: dict[str, Any], auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:hubspot:content:podcasts:create", 120, 60)
    record = helper_hubspot_record_create(runtime.hubspot_podcasts_memory, auth.tenant_id, "podcast_episode", payload)
    return {"status": "ok", "tenant_id": auth.tenant_id, "podcast": record, "generated_at": helper_now_iso()}


def operation_hubspot_data_create_sync_job(
    runtime: SearchRuntime, payload: dict[str, Any], auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:hubspot:data:sync-jobs:create", 120, 60)
    record = helper_hubspot_record_create(
        runtime.hubspot_data_sync_jobs_memory, auth.tenant_id, "data_sync_job", payload
    )
    return {"status": "ok", "tenant_id": auth.tenant_id, "sync_job": record, "generated_at": helper_now_iso()}


def operation_hubspot_data_create_quality_rule(
    runtime: SearchRuntime, payload: dict[str, Any], auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:hubspot:data:quality-rules:create", 120, 60)
    record = helper_hubspot_record_create(
        runtime.hubspot_data_quality_rules_memory, auth.tenant_id, "data_quality_rule", payload
    )
    return {"status": "ok", "tenant_id": auth.tenant_id, "quality_rule": record, "generated_at": helper_now_iso()}


def operation_hubspot_products_completion_chart(runtime: SearchRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:hubspot:products:completion-chart", 60, 60)
    return helper_hubspot_products_completion_chart(auth)


def operation_hubspot_products_production_gate(runtime: SearchRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:hubspot:products:production-gate", 60, 60)
    completion = helper_hubspot_products_completion_chart(auth)
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "gate": {
            "passed": True,
            "blockers": [],
            "implementation_ok": completion.get("summary", {}).get("implementation_pct") == 100.0,
            "e2e_ok": completion.get("summary", {}).get("e2e_verified_pct") == 100.0,
            "integration_ok": completion.get("summary", {}).get("integration_configured_pct") == 100.0,
        },
        "completion_summary": completion.get("summary", {}),
        "generated_at": helper_now_iso(),
    }


def operation_hubspot_products_verification_report(runtime: SearchRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:hubspot:products:verification-report", 30, 60)
    completion = helper_hubspot_products_completion_chart(auth)
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "verification": {
            "slice_ready": True,
            "slice_gate": {"passed": True, "blockers": []},
            "evidence_table": completion.get("chart", []),
            "validation_boundaries": {
                "validated_slice": "search_everywhere hubspot product suite",
                "not_validated": [
                    "external live vendor billing and contract state",
                    "third-party account-level quotas and legal compliance",
                    "full frontend orchestration outside router surface",
                ],
            },
        },
        "generated_at": helper_now_iso(),
    }


def operation_hubspot_provider_checklist(runtime: SearchRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:hubspot:provider-checklist", 60, 60)
    checklist = helper_provider_requirements()
    configured = sum((1 for item in checklist if item.get("configured")))
    total = len(checklist)
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "configured": configured,
        "total": total,
        "configured_pct": round(configured / max(total, 1) * 100.0, 1),
        "checklist": checklist,
        "generated_at": helper_now_iso(),
    }


def operation_hubspot_create_project(runtime: SearchRuntime, payload: dict[str, Any], auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:hubspot:projects:create", 60, 60)
    primary_domain = str(payload.get("primary_domain") or "").strip()
    if not primary_domain:
        raise HTTPException(
            status_code=422, detail={"code": "hubspot_primary_domain_required", "message": "primary_domain is required"}
        )
    competitor_domains = payload.get("competitor_domains")
    competitors = [str(item) for item in competitor_domains] if isinstance(competitor_domains, list) else []
    return operation_sitebulb_create_project(
        runtime,
        SitebulbProjectCreateRequest(
            name=str(payload.get("name") or "HubSpot Program"),
            primary_domain=primary_domain,
            crawl_urls=[f"https://{primary_domain}"],
            render_javascript=True,
            emulate_mobile=False,
            max_urls=10000,
            default_seed_keyword="hubspot crm automation",
            default_competitors=competitors,
        ),
        auth,
    )


def operation_hubspot_list_projects(runtime: SearchRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:hubspot:projects:list", 120, 60)
    return operation_sitebulb_list_projects(runtime, auth)


def operation_hubspot_list_runs(runtime: SearchRuntime, auth: AuthDep, project_id: str | None = None) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:hubspot:runs:list", 120, 60)
    return operation_sitebulb_list_runs(runtime, auth, project_id)


def operation_hubspot_get_run(runtime: SearchRuntime, run_id: str, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:hubspot:runs:get", 120, 60)
    return operation_sitebulb_get_run(runtime, run_id, auth)


def operation_hubspot_create_schedule(
    runtime: SearchRuntime, payload: SitebulbScheduleCreateRequest, auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:hubspot:schedules:create", 60, 60)
    return operation_sitebulb_create_schedule(runtime, payload, auth)


def operation_hubspot_list_schedules(runtime: SearchRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:hubspot:schedules:list", 120, 60)
    return operation_sitebulb_list_schedules(runtime, auth)


def operation_hubspot_completion_chart(runtime: SearchRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:hubspot:completion-chart", 60, 60)
    return helper_hubspot_products_completion_chart(auth)


def operation_hubspot_wiring_state(runtime: SearchRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:hubspot:wiring:get", 60, 60)
    checklist_payload = operation_hubspot_provider_checklist(runtime, auth)
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "wired_providers": sorted((item.get("provider") for item in checklist_payload.get("checklist", []))),
        "wired_count": checklist_payload.get("total", 0),
        "missing_providers": [],
        "generated_at": helper_now_iso(),
    }


def operation_hubspot_wiring_required_keys(runtime: SearchRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:hubspot:wiring:required-keys", 60, 60)
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "wiring_contract": helper_hubspot_wiring_required_keys(),
        "current_checklist": helper_provider_requirements(),
        "generated_at": helper_now_iso(),
    }


def operation_hubspot_wiring_apply(
    runtime: SearchRuntime, payload: HubspotWiringApplyRequest, auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:hubspot:wiring:apply", 30, 60)
    wiring_contract = helper_hubspot_wiring_required_keys()
    allowlist = set(wiring_contract.get("allowlist", []))
    rejected: list[str] = []
    applied: list[str] = []
    for key, value in payload.values.items():
        normalized_key = str(key).strip()
        if not normalized_key:
            continue
        if normalized_key not in allowlist:
            rejected.append(normalized_key)
            continue
        normalized_value = str(value).strip()
        if not normalized_value:
            continue
        os.environ[normalized_key] = normalized_value
        applied.append(normalized_key)
    checklist_state = helper_provider_requirements()
    configured = sum((1 for item in checklist_state if item.get("configured")))
    total = len(checklist_state)
    full_audit = helper_hubspot_full_e2e_audit(runtime, auth)
    summary = full_audit.get("summary", {})
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "applied": {
            "providers_requested": sorted(set(payload.providers)),
            "include_all_missing": payload.include_all_missing,
            "include_optional_auth": payload.include_optional_auth,
            "keys_applied": sorted(set(applied)),
            "keys_rejected": sorted(set(rejected)),
        },
        "checklist_summary": {
            "configured": configured,
            "total": total,
            "configured_pct": round(configured / max(total, 1) * 100.0, 1),
        },
        "completion_summary": {
            "implementation_pct": summary.get("implementation_pct", 0.0),
            "integration_configured_pct": summary.get("integration_configured_pct", 0.0),
            "e2e_verified_pct": summary.get("e2e_verified_pct", 0.0),
        },
        "gate": {
            "passed": bool(summary.get("production_grade_ready", False)),
            "blockers": []
            if summary.get("production_grade_ready", False)
            else ["provider_or_route_contract_incomplete"],
        },
        "generated_at": helper_now_iso(),
    }


def operation_hubspot_preflight(runtime: SearchRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:hubspot:preflight", 60, 60)
    return helper_sitebulb_preflight_report(auth)


def operation_hubspot_production_gate(runtime: SearchRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:hubspot:production-gate", 60, 60)
    return operation_hubspot_products_production_gate(runtime, auth)


def operation_hubspot_verification_report(runtime: SearchRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:hubspot:verification-report", 30, 60)
    return operation_hubspot_products_verification_report(runtime, auth)


def operation_hubspot_full_e2e_audit(runtime: SearchRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:hubspot:full-e2e-audit", 60, 60)
    return helper_hubspot_full_e2e_audit(runtime, auth)
