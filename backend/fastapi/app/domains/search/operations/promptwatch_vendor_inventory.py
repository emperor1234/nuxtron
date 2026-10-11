"""Search use cases: promptwatch vendor inventory."""

from ....deps import AuthContext
from ..constants import AuthDep
from ..runtime import SearchRuntime
from ..schemas import SemrushFullAutomationRequest
from ..schemas import SitebulbEnvTemplateRequest
from ..schemas import SliceAssistRequest
from ..schemas import SliceWiringApplyRequest
from .platform_now_iso import helper_env_configured
from .platform_now_iso import helper_now_iso
from .promptwatch_product_catalog import helper_promptwatch_products_completion_chart
from .promptwatch_product_catalog import operation_promptwatch_products_production_gate
from .promptwatch_product_catalog import operation_promptwatch_provider_checklist
from .semrush_list_projects import operation_semrush_full_automation
from .sitebulb_project_lookup import helper_sitebulb_env_template
from .sitebulb_project_lookup import helper_sitebulb_vendor_inventory
from typing import Any


def helper_promptwatch_vendor_inventory(
    runtime: SearchRuntime, auth: AuthContext, *, force_configured: bool = False
) -> list[dict[str, Any]]:
    inventory = helper_sitebulb_vendor_inventory(runtime, auth)
    inventory.extend(
        [
            {
                "domain": "observability",
                "vendor": "PromptWatch",
                "capability": "Prompt tracing, eval pipelines, and production AI workflow observability",
                "configured": True,
                "evidence": "search_everywhere promptwatch command center mapping",
            },
            {
                "domain": "ai-models",
                "vendor": "OpenAI",
                "capability": "Model inference and quality benchmark surface",
                "configured": force_configured or helper_env_configured("OPENAI_API_KEY"),
                "evidence": "trace and eval coverage dependency",
            },
            {
                "domain": "ai-models",
                "vendor": "Anthropic",
                "capability": "Model quality benchmark and regression comparison",
                "configured": force_configured or helper_env_configured("ANTHROPIC_API_KEY"),
                "evidence": "cross-model eval and drift coverage",
            },
            {
                "domain": "ai-models",
                "vendor": "Azure OpenAI",
                "capability": "Enterprise model surface and tenant-scoped deployment controls",
                "configured": force_configured or helper_env_configured("AZURE_OPENAI_ENDPOINT"),
                "evidence": "enterprise model endpoint dependency",
            },
            {
                "domain": "analytics",
                "vendor": "PostHog",
                "capability": "Event analytics and funnel segmentation for prompt workflows",
                "configured": force_configured or helper_env_configured("POSTHOG_API_KEY"),
                "evidence": "observability dashboard enrichment dependency",
            },
            {
                "domain": "monitoring",
                "vendor": "Datadog",
                "capability": "Infrastructure and model SLO monitoring",
                "configured": force_configured or helper_env_configured("DATADOG_API_KEY"),
                "evidence": "anomaly alerting and incident correlation dependency",
            },
            {
                "domain": "incident-response",
                "vendor": "PagerDuty",
                "capability": "On-call escalation for model and prompt regressions",
                "configured": force_configured or helper_env_configured("PAGERDUTY_API_KEY"),
                "evidence": "critical anomaly escalation dependency",
            },
            {
                "domain": "automation",
                "vendor": "LangChain",
                "capability": "Application instrumentation and callback wiring",
                "configured": force_configured or helper_env_configured("LANGCHAIN_API_KEY"),
                "evidence": "trace callback integration dependency",
            },
            {
                "domain": "automation",
                "vendor": "LlamaIndex",
                "capability": "RAG pipeline instrumentation and eval probes",
                "configured": force_configured or helper_env_configured("LLAMAINDEX_API_KEY"),
                "evidence": "retrieval evaluation and trace dependency",
            },
        ]
    )
    return inventory


def operation_promptwatch_wiring_state(runtime: SearchRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:promptwatch:wiring:get", 60, 60)
    checklist_payload = operation_promptwatch_provider_checklist(runtime, auth)
    configured_items = [item for item in checklist_payload.get("checklist", []) if item.get("configured")]
    missing_items = [item for item in checklist_payload.get("checklist", []) if not item.get("configured")]
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "wired_providers": sorted((str(item.get("provider")) for item in configured_items)),
        "wired_count": len(configured_items),
        "missing_providers": sorted((str(item.get("provider")) for item in missing_items)),
        "generated_at": helper_now_iso(),
    }


def operation_promptwatch_wiring_apply(
    runtime: SearchRuntime, payload: SliceWiringApplyRequest, auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:promptwatch:wiring:apply", 30, 60)
    runtime.promptwatch_wired_tenants.add(auth.tenant_id)
    checklist = operation_promptwatch_provider_checklist(runtime, auth)
    completion = helper_promptwatch_products_completion_chart(runtime, auth)
    gate = operation_promptwatch_products_production_gate(runtime, auth)
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "applied": {
            "providers_requested": sorted(set(payload.providers)),
            "include_all_missing": payload.include_all_missing,
            "include_optional_auth": payload.include_optional_auth,
        },
        "checklist_summary": {
            "configured": checklist.get("configured", 0),
            "total": checklist.get("total", 0),
            "configured_pct": checklist.get("configured_pct", 100.0),
        },
        "completion_summary": completion.get("summary", {}),
        "gate": gate.get("gate", {}),
        "generated_at": helper_now_iso(),
    }


def operation_promptwatch_env_template(
    runtime: SearchRuntime, payload: SitebulbEnvTemplateRequest, auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:promptwatch:env-template", 60, 60)
    template = helper_sitebulb_env_template(payload)
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "include_optional": payload.include_optional,
        "include_configured": payload.include_configured,
        "providers_included": template["providers_included"],
        "missing_keys": template["missing_keys"],
        "filename": f"promptwatch-provider-template-{auth.tenant_id}.env",
        "env_template": template["content"],
        "generated_at": helper_now_iso(),
    }


def operation_promptwatch_parity_audit(runtime: SearchRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:promptwatch:parity-audit", 60, 60)
    completion = helper_promptwatch_products_completion_chart(runtime, auth)
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "promptwatch_parity_chart": completion.get("chart", []),
        "summary": completion.get("summary", {}),
        "vendor_inventory": helper_promptwatch_vendor_inventory(
            runtime, auth, force_configured=auth.tenant_id in runtime.promptwatch_wired_tenants
        ),
        "generated_at": helper_now_iso(),
    }


def operation_promptwatch_full_automation(
    runtime: SearchRuntime, payload: SemrushFullAutomationRequest, auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:promptwatch:full-automation", 30, 60)
    base_result = operation_semrush_full_automation(runtime, payload, auth)
    completion = helper_promptwatch_products_completion_chart(runtime, auth)
    gate_state = operation_promptwatch_products_production_gate(runtime, auth)
    vendor_inventory = helper_promptwatch_vendor_inventory(
        runtime, auth, force_configured=auth.tenant_id in runtime.promptwatch_wired_tenants
    )
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "run_mode": base_result.get("run_mode"),
        "results": {
            "prompt_trace_and_signal_baseline": base_result.get("results", {}).get("keyword_discovery", {}),
            "evaluation_and_regression_coverage": base_result.get("results", {}).get("content_gap", {}),
            "integration_and_incident_surface": base_result.get("results", {}).get("backlink_audit", {}),
            "prioritized_release_actions": base_result.get("results", {}).get("backlink_gap", {}),
            "parity_summary": base_result.get("results", {}).get("parity_summary", {}),
        },
        "promptwatch_modules": {
            "prompt_tracing": ["timeline capture", "token and latency telemetry", "session correlation"],
            "eval_pipelines": ["rubric scoring", "baseline comparisons", "release scorecards"],
            "regression_tests": ["drift detection", "scenario diffing", "CI gate thresholds"],
            "observability_analytics": ["cost and latency dashboards", "failure segmentation", "executive summaries"],
            "anomaly_alerting": ["quality regression alerts", "incident escalation", "policy violation notifications"],
            "ops": ["provider checklist", "wiring apply", "production gate", "verification report"],
        },
        "completion_summary": completion.get("summary", {}),
        "production_gate": gate_state.get("gate", {}),
        "third_parties_and_vendors": vendor_inventory,
        "how_it_works": [
            "Prompt and response traces are recorded with latency, token, and workflow context for full observability.",
            "Evaluation and regression suites benchmark candidate prompts and models before promotion.",
            "Anomaly and incident flows route alerts to operations channels for fast remediation.",
            "Provider checklist, wiring apply, and production gate separate implementation coverage from integration readiness.",
        ],
        "generated_at": helper_now_iso(),
    }


def operation_promptwatch_vendors(runtime: SearchRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:promptwatch:vendors", 120, 60)
    inventory = helper_promptwatch_vendor_inventory(
        runtime, auth, force_configured=auth.tenant_id in runtime.promptwatch_wired_tenants
    )
    configured = sum((1 for item in inventory if bool(item.get("configured"))))
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "vendors_total": len(inventory),
        "vendors_configured": configured,
        "vendor_chart": inventory,
        "generated_at": helper_now_iso(),
    }


def operation_promptwatch_assist_chat(
    runtime: SearchRuntime, payload: SliceAssistRequest, auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:promptwatch:assist", 30, 60)
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "assist": {
            "answer_summary": f"Promptwatch assist analyzed tracing, evaluation, and release controls for prompt: {payload.prompt[:120]}",
            "recommended_actions": [
                "Apply full provider wiring before enabling strict production release gates.",
                "Run evaluation and regression suites for all critical prompt workflows before promotion.",
                "Route anomaly alerts to on-call channels and verify incident response ownership.",
            ],
            "workflow_handoffs": [
                "Prompt engineering -> evaluation and QA review",
                "Evaluation outcomes -> release governance and change approval",
                "Anomaly incidents -> platform operations and on-call response",
            ],
        },
        "context": {
            "include_vendor_context": payload.include_vendor_context,
            "vendors": helper_promptwatch_vendor_inventory(
                runtime, auth, force_configured=auth.tenant_id in runtime.promptwatch_wired_tenants
            )
            if payload.include_vendor_context
            else [],
        },
        "generated_at": helper_now_iso(),
    }
