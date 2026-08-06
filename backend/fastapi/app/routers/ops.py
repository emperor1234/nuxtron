# pyright: reportUnusedFunction=false, reportMissingTypeArgument=false

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, Request
from pydantic import BaseModel, Field

from ..deps import AuthContext, require_auth
from ..middleware.admin_allowlist import require_privileged_ip

AuthDep = Annotated[AuthContext, Depends(require_auth)]
JsonObject = dict[str, object]


class PasswordHashRequest(BaseModel):
    password: str = Field(min_length=8, max_length=256)
    algorithm: str = Field(default='bcrypt', min_length=6, max_length=16)


class PasswordVerifyRequest(BaseModel):
    password: str = Field(min_length=8, max_length=256)
    stored_hash: str = Field(min_length=12, max_length=1024)


class SiemCaseCreateRequest(BaseModel):
    title: str = Field(min_length=4, max_length=240)
    severity: str = Field(default='medium', pattern=r'^(low|medium|high|critical)$')
    description: str = Field(default='', max_length=4000)
    evidence_ids: list[str] = Field(default_factory=list, max_length=50)


class SiemCaseUpdateRequest(BaseModel):
    status: str = Field(pattern=r'^(open|triaged|in_progress|resolved|closed)$')
    assignee: str = Field(default='', max_length=120)
    note: str = Field(default='', max_length=2000)


class SiemSoarRunRequest(BaseModel):
    playbook: str = Field(min_length=2, max_length=120)
    case_id: int | None = Field(default=None, ge=1)
    parameters: dict[str, object] = Field(default_factory=dict)


class SiemRetentionPolicyRequest(BaseModel):
    hot_days: int = Field(default=30, ge=1, le=3650)
    warm_days: int = Field(default=90, ge=1, le=3650)
    cold_days: int = Field(default=365, ge=1, le=3650)
    immutable_audit: bool = Field(default=True)


class SiemControlUpdateRequest(BaseModel):
    enabled: bool = True
    mode: str = Field(default='', max_length=60)
    action: str = Field(default='', max_length=60)
    threshold: int = Field(default=0, ge=0, le=100000)
    notes: str = Field(default='', max_length=500)


class SiemZapScanRequest(BaseModel):
    target_url: str = Field(min_length=8, max_length=600)
    scan_profile: str = Field(default='full-active', max_length=80)
    authenticated: bool = Field(default=False)


class SiemApplyUpdateRequest(BaseModel):
    strategy: str = Field(default='rolling', max_length=40)


class SiemAutoPentestRunRequest(BaseModel):
    profile: str = Field(default='deep', pattern=r'^(quick|deep|full)$')
    target_scope: str = Field(default='all-exposed', max_length=120)
    include_dependency_scan: bool = Field(default=True)
    include_api_fuzzing: bool = Field(default=True)


class SiemEndpointHardeningRequest(BaseModel):
    strict_mode: bool = Field(default=True)
    enforce_edr_policy: bool = Field(default=True)
    enforce_device_posture: bool = Field(default=True)
    apply_to_assets: list[str] = Field(default_factory=list, max_length=100)


class SiemDeadCodeScanRequest(BaseModel):
    scope: str = Field(default='backend/fastapi', max_length=240)
    include_frontend: bool = Field(default=True)
    include_backend: bool = Field(default=True)
    severity_floor: str = Field(default='medium', pattern=r'^(low|medium|high|critical)$')


def _invoke(fn: 'Callable[..., dict[str, Any]] | None', default: 'dict[str, Any]', /, *args: Any) -> 'dict[str, Any]':
    """Call *fn* with *args* when provided, otherwise return *default*."""
    if fn is not None:
        return fn(*args)
    return default


def create_ops_router(
    *,
    enforce_rate_limit: Callable[[str, int, int], None],
    hash_password: Callable[[str, str], str],
    verify_password: Callable[[str, str], bool],
    get_platform_status: Callable[[AuthContext], JsonObject],
    get_metrics_summary: Callable[[AuthContext], JsonObject],
    callbacks: '_OpsCallbacks | None' = None,
) -> APIRouter:
    cb = callbacks if callbacks is not None else _OpsCallbacks()
    router = APIRouter()
    _register_platform_routes(cb, enforce_rate_limit, hash_password, verify_password, get_platform_status, get_metrics_summary, router)

    # SIEM routes (case management, detections, compliance, endpoint hardening,
    # pentest/SOAR triggers, "apply update") were previously gated by AuthDep
    # only — any authenticated tenant caller, including a plain API-key holder
    # with no user identity, could read/administer the security operations
    # center. require_privileged_ip existed as a dependency but was never
    # actually wired onto any route; this is that wiring. A nested sub-router
    # is used (rather than adding the dependency to every handler) so the
    # non-SIEM platform routes registered above are unaffected.
    siem_router = APIRouter(dependencies=[Depends(require_privileged_ip)])
    _register_siem_core_routes(cb, siem_router)
    _register_siem_security_routes(cb, siem_router)
    _register_siem_advanced_routes(cb, siem_router)
    router.include_router(siem_router)
    return router


@dataclass
class _OpsCallbacks:
    get_anti_failure_status: Callable[[AuthContext], dict[str, Any]] | None = field(default=None)
    get_use_case_coverage: Callable[[AuthContext], dict[str, Any]] | None = field(default=None)
    get_api_usage_summary: Callable[[AuthContext, int], dict[str, Any]] | None = field(default=None)
    get_capabilities: Callable[[AuthContext], dict[str, Any]] | None = field(default=None)
    get_super_admin_dashboard: Callable[[AuthContext], dict[str, Any]] | None = field(default=None)
    get_siem_data_collection: Callable[[AuthContext, int], dict[str, Any]] | None = field(default=None)
    get_siem_detection: Callable[[AuthContext, int], dict[str, Any]] | None = field(default=None)
    get_siem_investigation: Callable[[AuthContext, str, int], dict[str, Any]] | None = field(default=None)
    get_siem_compliance: Callable[[AuthContext], dict[str, Any]] | None = field(default=None)
    set_siem_retention_policy: Callable[[AuthContext, int, int, int, bool], dict[str, Any]] | None = field(default=None)
    get_siem_architecture: Callable[[AuthContext], dict[str, Any]] | None = field(default=None)
    list_siem_cases: Callable[[AuthContext, str | None, int, int], dict[str, Any]] | None = field(default=None)
    create_siem_case: Callable[[AuthContext, str, str, str, list[str]], dict[str, Any]] | None = field(default=None)
    update_siem_case: Callable[[AuthContext, int, str, str, str], dict[str, Any]] | None = field(default=None)
    run_siem_soar_playbook: Callable[[AuthContext, str, int | None, dict[str, object]], dict[str, Any]] | None = field(default=None)
    get_siem_flow_map: Callable[[AuthContext, int, int], dict[str, Any]] | None = field(default=None)
    get_siem_security_controls: Callable[[AuthContext], dict[str, Any]] | None = field(default=None)
    update_siem_security_control: Callable[[AuthContext, str, int, bool, str, str, int, str], dict[str, Any]] | None = field(default=None)
    get_siem_vulnerabilities: Callable[[AuthContext, str, str, int], dict[str, Any]] | None = field(default=None)
    run_siem_zap_scan: Callable[[AuthContext, str, str, bool], dict[str, Any]] | None = field(default=None)
    get_siem_updates: Callable[[AuthContext], dict[str, Any]] | None = field(default=None)
    apply_siem_update: Callable[[AuthContext, int, str], dict[str, Any]] | None = field(default=None)
    run_siem_auto_pentest: Callable[[AuthContext, str, str, bool, bool], dict[str, Any]] | None = field(default=None)
    list_siem_auto_pentest_jobs: Callable[[AuthContext, int], dict[str, Any]] | None = field(default=None)
    get_siem_vault_encryption_health: Callable[[AuthContext], dict[str, Any]] | None = field(default=None)
    apply_siem_endpoint_hardening: Callable[[AuthContext, bool, bool, bool, list[str]], dict[str, Any]] | None = field(default=None)
    get_siem_endpoint_hardening_status: Callable[[AuthContext], dict[str, Any]] | None = field(default=None)
    get_siem_network_anomalies: Callable[[AuthContext, int], dict[str, Any]] | None = field(default=None)
    run_siem_dead_code_scan: Callable[[AuthContext, str, bool, bool, str], dict[str, Any]] | None = field(default=None)
    list_siem_dead_code_findings: Callable[[AuthContext, str, int], dict[str, Any]] | None = field(default=None)
    get_siem_advanced_threat_hunt: Callable[[AuthContext, int], dict[str, Any]] | None = field(default=None)
    get_hybrid_stacks: Callable[[AuthContext], dict[str, Any]] | None = field(default=None)
    get_module_registry: Callable[[AuthContext], dict[str, Any]] | None = field(default=None)
    require_super_admin_access: Callable[[Request, str | None], None] | None = field(default=None)


def _register_platform_routes(
    cb: '_OpsCallbacks',
    enforce_rate_limit: Callable[[str, int, int], None],
    hash_password: Callable[[str, str], str],
    verify_password: Callable[[str, str], bool],
    get_platform_status: Callable[[AuthContext], JsonObject],
    get_metrics_summary: Callable[[AuthContext], JsonObject],
    router: APIRouter,
) -> None:
    @router.get('/ops/platform/status')
    def platform_ops_status(auth: AuthDep) -> JsonObject:
        return get_platform_status(auth)

    @router.get('/ops/platform/metrics-summary')
    def platform_metrics_summary(auth: AuthDep) -> JsonObject:
        return get_metrics_summary(auth)

    @router.get('/ops/platform/anti-failure-status')
    def platform_anti_failure_status(auth: AuthDep) -> dict[str, Any]:
        return _invoke(cb.get_anti_failure_status, {'status': 'ok', 'tenant_id': auth.tenant_id, 'defense_systems': [], 'summary': {'healthy_count': 0, 'degraded_count': 0}}, auth)

    @router.get('/ops/platform/use-case-coverage')
    def platform_use_case_coverage(auth: AuthDep) -> dict[str, Any]:
        return _invoke(cb.get_use_case_coverage, {'status': 'ok', 'tenant_id': auth.tenant_id, 'use_cases': {}, 'coverage_percent': 0}, auth)

    @router.get('/ops/platform/capabilities')
    def platform_capabilities(auth: AuthDep) -> dict[str, Any]:
        return _invoke(cb.get_capabilities, {'status': 'ok', 'tenant_id': auth.tenant_id, 'generated_at': '', 'categories': [], 'totals': {'features': 0, 'categories': 0}}, auth)

    @router.get('/ops/platform/hybrid-stacks')
    def platform_hybrid_stacks(auth: AuthDep) -> dict[str, Any]:
            # Return fallback minimal response if no callback is wired
        if cb.get_hybrid_stacks is None:
            return {
                'status': 'ok',
                'tenant_id': auth.tenant_id,
                'generated_at': '',
                'recommendation': {
                    'hybrid': 'OpenLens (Free) + Promptwatch (Paid)',
                    'score': '100/100 (100%)',
                    'benefits': [],
                    'positioning': '',
                },
                'stacks': [],
                'summary': [],
            }
        return cb.get_hybrid_stacks(auth)

    @router.get('/ops/platform/module-registry')
    def platform_module_registry(auth: AuthDep) -> dict[str, Any]:
        if cb.get_module_registry is not None:
            return cb.get_module_registry(auth)
        else:
            return {
                'status': 'ok',
                'tenant_id': auth.tenant_id,
                'generated_at': '',
                'source': 'fallback',
                'modules': [],
                'totals': {
                    'total_modules': 0,
                    'free_tools': 0,
                    'open_source_tools': 0,
                    'avg_hybrid_score': 0.0,
                },
            }

    @router.get('/ops/platform/super-admin/dashboard', responses={
        401: {'description': 'Invalid super admin key.'},
        403: {'description': 'Source IP is not allowlisted for super admin access.'},
        503: {'description': 'Super admin access policy is not configured.'},
    })
    def platform_super_admin_dashboard(
        request: Request,
        auth: AuthDep,
        x_super_admin_key: Annotated[str | None, Header(alias='X-Super-Admin-Key')] = None,
    ) -> dict[str, Any]:
        if cb.require_super_admin_access is not None:
            cb.require_super_admin_access(request, x_super_admin_key)
        if cb.get_super_admin_dashboard is not None:
            return cb.get_super_admin_dashboard(auth)
        return {
            'status': 'ok', 'tenant_id': auth.tenant_id, 'generated_at': '',
            'siem': {'total_logs': 0, 'critical_alerts': 0, 'security_events': 0, 'sources': []},
            'modules': [],
            'subscription': {'active_plan': 'free', 'available_plans': ['free', 'basic', 'pro', 'ultimate', 'enterprise']},
        }

    @router.get('/ops/security/api-usage')
    def platform_api_usage(auth: AuthDep, limit: int = 100) -> dict[str, Any]:
        bounded_limit = max(1, min(limit, 1000))
        return _invoke(cb.get_api_usage_summary, {'status': 'ok', 'tenant_id': auth.tenant_id, 'items': [], 'summary': {'total': 0, 'api_key_requests': 0, 'bearer_jwt_requests': 0}}, auth, bounded_limit)

    @router.post('/security/hash-password')
    def security_hash_password(payload: PasswordHashRequest, auth: AuthDep) -> JsonObject:
        enforce_rate_limit(f'{auth.tenant_id}:security:hash', 30, 60)
        hashed = hash_password(payload.password, payload.algorithm)
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'algorithm': payload.algorithm, 'hash': hashed}

    @router.post('/security/verify-password')
    def security_verify_password(payload: PasswordVerifyRequest, auth: AuthDep) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:security:verify', 60, 60)
        valid = verify_password(payload.password, payload.stored_hash)
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'valid': valid}


def _register_siem_core_routes(cb: '_OpsCallbacks', router: APIRouter) -> None:
    @router.get('/ops/siem/data-collection')
    def siem_data_collection(auth: AuthDep, limit: int = 200) -> dict[str, Any]:
        bounded_limit = max(10, min(limit, 5000))
        return _invoke(cb.get_siem_data_collection, {'status': 'ok', 'tenant_id': auth.tenant_id, 'telemetry': {}, 'count': 0}, auth, bounded_limit)

    @router.get('/ops/siem/detection')
    def siem_detection(auth: AuthDep, limit: int = 200) -> dict[str, Any]:
        bounded_limit = max(10, min(limit, 5000))
        return _invoke(cb.get_siem_detection, {'status': 'ok', 'tenant_id': auth.tenant_id, 'detections': []}, auth, bounded_limit)

    @router.get('/ops/siem/investigation')
    def siem_investigation(auth: AuthDep, query: str = '', limit: int = 100) -> dict[str, Any]:
        bounded_limit = max(10, min(limit, 1000))
        return _invoke(cb.get_siem_investigation, {'status': 'ok', 'tenant_id': auth.tenant_id, 'results': [], 'query': query}, auth, query, bounded_limit)

    @router.get('/ops/siem/compliance')
    def siem_compliance(auth: AuthDep) -> dict[str, Any]:
        return _invoke(cb.get_siem_compliance, {'status': 'ok', 'tenant_id': auth.tenant_id, 'reports': []}, auth)

    @router.post('/ops/siem/compliance/retention')
    def siem_retention_policy(payload: SiemRetentionPolicyRequest, auth: AuthDep) -> dict[str, Any]:
        return _invoke(cb.set_siem_retention_policy, {'status': 'ok', 'tenant_id': auth.tenant_id, 'retention_policy': {'hot_days': payload.hot_days, 'warm_days': payload.warm_days, 'cold_days': payload.cold_days, 'immutable_audit': payload.immutable_audit}}, auth, payload.hot_days, payload.warm_days, payload.cold_days, payload.immutable_audit)

    @router.get('/ops/siem/architecture')
    def siem_architecture(auth: AuthDep) -> dict[str, Any]:
        return _invoke(cb.get_siem_architecture, {'status': 'ok', 'tenant_id': auth.tenant_id, 'architecture': {}}, auth)

    @router.get('/ops/siem/cases')
    def siem_cases(auth: AuthDep, status: str | None = None, limit: int = 100, offset: int = 0) -> dict[str, Any]:
        bounded_limit = max(1, min(limit, 500))
        bounded_offset = max(0, offset)
        return _invoke(cb.list_siem_cases, {'status': 'ok', 'tenant_id': auth.tenant_id, 'cases': [], 'count': 0}, auth, status, bounded_limit, bounded_offset)

    @router.post('/ops/siem/cases')
    def siem_create_case(payload: SiemCaseCreateRequest, auth: AuthDep) -> dict[str, Any]:
        return _invoke(cb.create_siem_case, {'status': 'ok', 'tenant_id': auth.tenant_id, 'case': payload.model_dump()}, auth, payload.title, payload.severity, payload.description, payload.evidence_ids)

    @router.patch('/ops/siem/cases/{case_id}')
    def siem_patch_case(case_id: int, payload: SiemCaseUpdateRequest, auth: AuthDep) -> dict[str, Any]:
        return _invoke(cb.update_siem_case, {'status': 'ok', 'tenant_id': auth.tenant_id, 'case_id': case_id, 'updated': payload.model_dump()}, auth, case_id, payload.status, payload.assignee, payload.note)

    @router.post('/ops/siem/soar/run')
    def siem_run_soar(payload: SiemSoarRunRequest, auth: AuthDep) -> dict[str, Any]:
        return _invoke(cb.run_siem_soar_playbook, {'status': 'ok', 'tenant_id': auth.tenant_id, 'playbook': payload.playbook, 'result': 'simulated'}, auth, payload.playbook, payload.case_id, payload.parameters)


def _register_siem_security_routes(cb: '_OpsCallbacks', router: APIRouter) -> None:
    @router.get('/ops/siem/flows')
    def siem_flows(auth: AuthDep, minutes: int = 60, limit: int = 500) -> dict[str, Any]:
        bounded_minutes = max(5, min(minutes, 1440))
        bounded_limit = max(10, min(limit, 5000))
        return _invoke(cb.get_siem_flow_map, {'status': 'ok', 'tenant_id': auth.tenant_id, 'graph': {'nodes': [], 'edges': []}, 'flow_count': 0}, auth, bounded_minutes, bounded_limit)

    @router.get('/ops/siem/controls')
    def siem_controls(auth: AuthDep) -> dict[str, Any]:
        return _invoke(cb.get_siem_security_controls, {'status': 'ok', 'tenant_id': auth.tenant_id, 'summary': {'controls_total': 0}}, auth)

    @router.patch('/ops/siem/controls/{control_type}/{control_id}')
    def siem_update_control(control_type: str, control_id: int, payload: SiemControlUpdateRequest, auth: AuthDep) -> dict[str, Any]:
        return _invoke(cb.update_siem_security_control, {'status': 'ok', 'tenant_id': auth.tenant_id, 'control_type': control_type, 'control_id': control_id}, auth, control_type, control_id, payload.enabled, payload.mode, payload.action, payload.threshold, payload.notes)

    @router.get('/ops/siem/vulnerabilities')
    def siem_vulnerabilities(auth: AuthDep, severity: str = '', status: str = '', limit: int = 200) -> dict[str, Any]:
        bounded_limit = max(1, min(limit, 5000))
        return _invoke(cb.get_siem_vulnerabilities, {'status': 'ok', 'tenant_id': auth.tenant_id, 'items': [], 'count': 0}, auth, severity, status, bounded_limit)

    @router.post('/ops/siem/zap/scan')
    def siem_zap_scan(payload: SiemZapScanRequest, auth: AuthDep) -> dict[str, Any]:
        return _invoke(cb.run_siem_zap_scan, {'status': 'ok', 'tenant_id': auth.tenant_id, 'scan': {'status': 'simulated'}}, auth, payload.target_url, payload.scan_profile, payload.authenticated)

    @router.get('/ops/siem/updates')
    def siem_updates(auth: AuthDep) -> dict[str, Any]:
        return _invoke(cb.get_siem_updates, {'status': 'ok', 'tenant_id': auth.tenant_id, 'items': [], 'count': 0}, auth)

    @router.post('/ops/siem/updates/{update_id}/apply')
    def siem_apply_update(update_id: int, payload: SiemApplyUpdateRequest, auth: AuthDep) -> dict[str, Any]:
        return _invoke(cb.apply_siem_update, {'status': 'ok', 'tenant_id': auth.tenant_id, 'update_id': update_id, 'strategy': payload.strategy}, auth, update_id, payload.strategy)

    @router.post('/ops/siem/auto-pentest/run')
    def siem_auto_pentest_run(payload: SiemAutoPentestRunRequest, auth: AuthDep) -> dict[str, Any]:
        return _invoke(cb.run_siem_auto_pentest, {'status': 'ok', 'tenant_id': auth.tenant_id, 'job': {'status': 'simulated'}}, auth, payload.profile, payload.target_scope, payload.include_dependency_scan, payload.include_api_fuzzing)

    @router.get('/ops/siem/auto-pentest/jobs')
    def siem_auto_pentest_jobs(auth: AuthDep, limit: int = 50) -> dict[str, Any]:
        bounded_limit = max(1, min(limit, 500))
        return _invoke(cb.list_siem_auto_pentest_jobs, {'status': 'ok', 'tenant_id': auth.tenant_id, 'count': 0, 'jobs': []}, auth, bounded_limit)

    @router.get('/ops/siem/vault-encryption-health')
    def siem_vault_encryption_health(auth: AuthDep) -> dict[str, Any]:
        return _invoke(cb.get_siem_vault_encryption_health, {'status': 'ok', 'tenant_id': auth.tenant_id, 'health': {'overall': 'unknown'}}, auth)


def _register_siem_advanced_routes(cb: '_OpsCallbacks', router: APIRouter) -> None:
    @router.post('/ops/siem/endpoint-hardening/baseline')
    def siem_apply_endpoint_hardening(payload: SiemEndpointHardeningRequest, auth: AuthDep) -> dict[str, Any]:
        return _invoke(cb.apply_siem_endpoint_hardening, {'status': 'ok', 'tenant_id': auth.tenant_id, 'baseline': payload.model_dump()}, auth, payload.strict_mode, payload.enforce_edr_policy, payload.enforce_device_posture, payload.apply_to_assets)

    @router.get('/ops/siem/endpoint-hardening/status')
    def siem_endpoint_hardening_status(auth: AuthDep) -> dict[str, Any]:
        return _invoke(cb.get_siem_endpoint_hardening_status, {'status': 'ok', 'tenant_id': auth.tenant_id, 'assets': []}, auth)

    @router.get('/ops/siem/network-anomalies')
    def siem_network_anomalies(auth: AuthDep, minutes: int = 180) -> dict[str, Any]:
        bounded_minutes = max(5, min(minutes, 1440))
        return _invoke(cb.get_siem_network_anomalies, {'status': 'ok', 'tenant_id': auth.tenant_id, 'inbound_unknown': [], 'outbound_unknown': []}, auth, bounded_minutes)

    @router.post('/ops/siem/dead-code/scan')
    def siem_dead_code_scan(payload: SiemDeadCodeScanRequest, auth: AuthDep) -> dict[str, Any]:
        return _invoke(cb.run_siem_dead_code_scan, {'status': 'ok', 'tenant_id': auth.tenant_id, 'scan': {'status': 'simulated'}}, auth, payload.scope, payload.include_frontend, payload.include_backend, payload.severity_floor)

    @router.get('/ops/siem/dead-code/findings')
    def siem_dead_code_findings(auth: AuthDep, severity: str = '', limit: int = 200) -> dict[str, Any]:
        bounded_limit = max(1, min(limit, 2000))
        return _invoke(cb.list_siem_dead_code_findings, {'status': 'ok', 'tenant_id': auth.tenant_id, 'count': 0, 'items': []}, auth, severity, bounded_limit)

    @router.get('/ops/siem/threat-hunting/advanced')
    def siem_advanced_threat_hunting(auth: AuthDep, minutes: int = 360) -> dict[str, Any]:
        bounded_minutes = max(10, min(minutes, 1440))
        return _invoke(cb.get_siem_advanced_threat_hunt, {'status': 'ok', 'tenant_id': auth.tenant_id, 'apt_indicators': []}, auth, bounded_minutes)