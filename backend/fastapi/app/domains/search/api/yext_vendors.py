"""Search HTTP operations beginning with yext vendors."""

from ..constants import AuthDep
from ..operations.yext_product_catalog import operation_yext_completion_chart
from ..operations.yext_product_catalog import operation_yext_gate_progress
from ..operations.yext_product_catalog import operation_yext_preflight
from ..operations.yext_product_catalog import operation_yext_production_gate
from ..operations.yext_product_catalog import operation_yext_remediation_bundle
from ..operations.yext_product_catalog import operation_yext_remediation_bundle_export
from ..operations.yext_vendor_inventory import operation_yext_env_template
from ..operations.yext_vendor_inventory import operation_yext_vendors
from ..runtime import SearchRuntime
from ..schemas import SitebulbEnvTemplateRequest
from ..schemas import SitebulbRemediationBundleRequest
from fastapi import APIRouter
from fastapi import Query
from typing import Annotated
from typing import Any


def register(router: APIRouter, runtime: SearchRuntime):

    @router.get("/yext/vendors")
    def yext_vendors(auth: AuthDep) -> dict[str, Any]:
        return operation_yext_vendors(runtime, auth)

    @router.get("/yext/preflight")
    def yext_preflight(auth: AuthDep) -> dict[str, Any]:
        return operation_yext_preflight(runtime, auth)

    @router.get("/yext/gate-progress")
    def yext_gate_progress(auth: AuthDep) -> dict[str, Any]:
        return operation_yext_gate_progress(runtime, auth)

    @router.post("/yext/env-template")
    def yext_env_template(payload: SitebulbEnvTemplateRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_yext_env_template(runtime, payload, auth)

    @router.get("/yext/completion-chart")
    def yext_completion_chart(auth: AuthDep) -> dict[str, Any]:
        return operation_yext_completion_chart(runtime, auth)

    @router.get("/yext/production-gate")
    def yext_production_gate(auth: AuthDep) -> dict[str, Any]:
        return operation_yext_production_gate(runtime, auth)

    @router.post("/yext/remediation-bundle")
    def yext_remediation_bundle(payload: SitebulbRemediationBundleRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_yext_remediation_bundle(runtime, payload, auth)

    @router.get("/yext/remediation-bundle/export")
    def yext_remediation_bundle_export(
        auth: AuthDep,
        format: Annotated[str, Query(pattern="^(json|csv)$")] = "json",
        top_steps: int = Query(default=12, ge=1, le=100),
        include_optional: bool = Query(default=False),
        include_configured: bool = Query(default=False),
    ) -> dict[str, Any]:
        return operation_yext_remediation_bundle_export(
            runtime, auth, format, top_steps, include_optional, include_configured
        )
