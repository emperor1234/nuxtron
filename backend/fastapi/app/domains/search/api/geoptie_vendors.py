"""Search HTTP operations beginning with geoptie vendors."""

from ..constants import AuthDep
from ..operations.geoptie_product_catalog import operation_geoptie_completion_chart
from ..operations.geoptie_product_catalog import operation_geoptie_gate_progress
from ..operations.geoptie_product_catalog import operation_geoptie_preflight
from ..operations.geoptie_product_catalog import operation_geoptie_production_gate
from ..operations.geoptie_product_catalog import operation_geoptie_remediation_bundle
from ..operations.geoptie_product_catalog import operation_geoptie_remediation_bundle_export
from ..operations.geoptie_vendor_inventory import operation_geoptie_env_template
from ..operations.geoptie_vendor_inventory import operation_geoptie_vendors
from ..runtime import SearchRuntime
from ..schemas import SitebulbEnvTemplateRequest
from ..schemas import SitebulbRemediationBundleRequest
from fastapi import APIRouter
from fastapi import Query
from typing import Annotated
from typing import Any


def register(router: APIRouter, runtime: SearchRuntime):

    @router.get("/geoptie/vendors")
    def geoptie_vendors(auth: AuthDep) -> dict[str, Any]:
        return operation_geoptie_vendors(runtime, auth)

    @router.get("/geoptie/preflight")
    def geoptie_preflight(auth: AuthDep) -> dict[str, Any]:
        return operation_geoptie_preflight(runtime, auth)

    @router.get("/geoptie/gate-progress")
    def geoptie_gate_progress(auth: AuthDep) -> dict[str, Any]:
        return operation_geoptie_gate_progress(runtime, auth)

    @router.post("/geoptie/env-template")
    def geoptie_env_template(payload: SitebulbEnvTemplateRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_geoptie_env_template(runtime, payload, auth)

    @router.get("/geoptie/completion-chart")
    def geoptie_completion_chart(auth: AuthDep) -> dict[str, Any]:
        return operation_geoptie_completion_chart(runtime, auth)

    @router.get("/geoptie/production-gate")
    def geoptie_production_gate(auth: AuthDep) -> dict[str, Any]:
        return operation_geoptie_production_gate(runtime, auth)

    @router.post("/geoptie/remediation-bundle")
    def geoptie_remediation_bundle(payload: SitebulbRemediationBundleRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_geoptie_remediation_bundle(runtime, payload, auth)

    @router.get("/geoptie/remediation-bundle/export")
    def geoptie_remediation_bundle_export(
        auth: AuthDep,
        format: Annotated[str, Query(pattern="^(json|csv)$")] = "json",
        top_steps: int = Query(default=12, ge=1, le=100),
        include_optional: bool = Query(default=False),
        include_configured: bool = Query(default=False),
    ) -> dict[str, Any]:
        return operation_geoptie_remediation_bundle_export(
            runtime, auth, format, top_steps, include_optional, include_configured
        )
