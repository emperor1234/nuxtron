"""Search HTTP operations beginning with hubspot env template."""

from ..constants import AuthDep
from ..operations.hootsuite_features import operation_hootsuite_features
from ..operations.hubspot_product_catalog import operation_hubspot_remediation_bundle
from ..operations.hubspot_product_catalog import operation_hubspot_remediation_bundle_export
from ..operations.hubspot_route_coverage_chart import operation_hubspot_env_template
from ..operations.hubspot_wiring_required_keys import operation_hubspot_completion_chart
from ..operations.hubspot_wiring_required_keys import operation_hubspot_full_e2e_audit
from ..operations.hubspot_wiring_required_keys import operation_hubspot_production_gate
from ..operations.hubspot_wiring_required_keys import operation_hubspot_verification_report
from ..runtime import SearchRuntime
from ..schemas import SitebulbEnvTemplateRequest
from ..schemas import SitebulbRemediationBundleRequest
from fastapi import APIRouter
from fastapi import Query
from typing import Annotated
from typing import Any


def register(router: APIRouter, runtime: SearchRuntime):

    @router.post("/hubspot/env-template")
    def hubspot_env_template(payload: SitebulbEnvTemplateRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_hubspot_env_template(runtime, payload, auth)

    @router.get("/hubspot/completion-chart")
    def hubspot_completion_chart(auth: AuthDep) -> dict[str, Any]:
        return operation_hubspot_completion_chart(runtime, auth)

    @router.get("/hubspot/production-gate")
    def hubspot_production_gate(auth: AuthDep) -> dict[str, Any]:
        return operation_hubspot_production_gate(runtime, auth)

    @router.post("/hubspot/remediation-bundle")
    def hubspot_remediation_bundle(payload: SitebulbRemediationBundleRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_hubspot_remediation_bundle(runtime, payload, auth)

    @router.get("/hubspot/remediation-bundle/export")
    def hubspot_remediation_bundle_export(
        auth: AuthDep,
        format: Annotated[str, Query(pattern="^(json|csv)$")] = "json",
        top_steps: int = Query(default=12, ge=1, le=100),
        include_optional: bool = Query(default=False),
        include_configured: bool = Query(default=False),
    ) -> dict[str, Any]:
        return operation_hubspot_remediation_bundle_export(
            runtime, auth, format, top_steps, include_optional, include_configured
        )

    @router.get("/hubspot/verification-report")
    def hubspot_verification_report(auth: AuthDep) -> dict[str, Any]:
        return operation_hubspot_verification_report(runtime, auth)

    @router.get("/hubspot/full-e2e-audit")
    def hubspot_full_e2e_audit(auth: AuthDep) -> dict[str, Any]:
        return operation_hubspot_full_e2e_audit(runtime, auth)

    @router.get("/hootsuite/features")
    def hootsuite_features(auth: AuthDep) -> dict[str, Any]:
        return operation_hootsuite_features(runtime, auth)
