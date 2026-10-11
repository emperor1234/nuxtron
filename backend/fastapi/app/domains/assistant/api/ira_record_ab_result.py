"""Assistant HTTP adapters beginning with ira record ab result."""

from ..constants import AuthDep
from ..operations.ira_copilot_plan import execute_ira_finance_health
from ..operations.ira_copilot_plan import execute_list_ira_connectors
from ..operations.ira_execute_action import execute_ira_record_ab_result
from ..operations.ira_list_ab_tests import execute_ira_ingest_finance_sample
from ..operations.ira_list_ab_tests import execute_ira_list_ab_tests
from ..operations.ira_list_ab_tests import execute_update_ira_control
from ..operations.ira_list_ab_tests import execute_upsert_ira_connector
from ..operations.ira_ml_retrieval_query import execute_ira_risk_score
from ..runtime import ContextRuntime
from ..schemas import IRAAbTestRecordRequest
from ..schemas import IRAAutonomyUpdateRequest
from ..schemas import IRAConnectorUpsertRequest
from ..schemas import IRAFinanceSampleRequest
from fastapi import APIRouter
from fastapi import Header
from typing import Annotated
from typing import Any


def register(router: APIRouter, context_runtime: ContextRuntime):

    @router.post(
        "/ab-tests/record",
        responses={404: {"description": "Test not found"}, 422: {"description": "Unknown variant or test not running"}},
    )
    def ira_record_ab_result(payload: IRAAbTestRecordRequest, auth: AuthDep) -> dict[str, Any]:
        return execute_ira_record_ab_result(context_runtime, payload, auth)

    @router.get("/ab-tests")
    def ira_list_ab_tests(auth: AuthDep) -> dict[str, Any]:
        return execute_ira_list_ab_tests(context_runtime, auth)

    @router.post(
        "/control/config",
        responses={403: {"description": "Super admin required"}, 422: {"description": "Policy validation failed"}},
    )
    def update_ira_control(
        payload: IRAAutonomyUpdateRequest,
        auth: AuthDep,
        x_super_admin_key: Annotated[str | None, Header(alias="X-Super-Admin-Key")] = None,
    ) -> dict[str, Any]:
        return execute_update_ira_control(context_runtime, payload, auth, x_super_admin_key)

    @router.get("/connectors")
    def list_ira_connectors(auth: AuthDep) -> dict[str, Any]:
        return execute_list_ira_connectors(context_runtime, auth)

    @router.post("/connectors/upsert", responses={403: {"description": "Super admin required"}})
    def upsert_ira_connector(
        payload: IRAConnectorUpsertRequest,
        auth: AuthDep,
        x_super_admin_key: Annotated[str | None, Header(alias="X-Super-Admin-Key")] = None,
    ) -> dict[str, Any]:
        return execute_upsert_ira_connector(context_runtime, payload, auth, x_super_admin_key)

    @router.get("/finance/health")
    def ira_finance_health(auth: AuthDep) -> dict[str, Any]:
        return execute_ira_finance_health(context_runtime, auth)

    @router.get("/risk/score")
    def ira_risk_score(auth: AuthDep) -> dict[str, Any]:
        return execute_ira_risk_score(context_runtime, auth)

    @router.post("/finance/ingest")
    def ira_ingest_finance_sample(payload: IRAFinanceSampleRequest, auth: AuthDep) -> dict[str, Any]:
        return execute_ira_ingest_finance_sample(context_runtime, payload, auth)
