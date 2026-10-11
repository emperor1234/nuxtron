"""Assistant HTTP adapters beginning with disable protection mode."""

from ..constants import AuthDep
from ..operations.get_ira_recommendations import execute_get_ira_recommendations
from ..operations.ira_list_ab_tests import execute_collect_ira_feedback
from ..operations.ira_list_ab_tests import execute_disable_protection_mode
from ..operations.ira_list_ab_tests import execute_ira_crm_hybrid_recommendation
from ..operations.ira_list_ab_tests import execute_ira_disputes_dashboard
from ..operations.ira_list_ab_tests import execute_update_crm_feature_governance
from ..operations.ira_response import execute_ira_crm_connectors_status
from ..runtime import ContextRuntime
from ..schemas import IRAAdviceRequest
from ..schemas import IRACrmGovernanceUpdateRequest
from ..schemas import IRAFeedbackRequest
from fastapi import APIRouter
from fastapi import Header
from typing import Annotated
from typing import Any


def register(router: APIRouter, context_runtime: ContextRuntime):

    @router.post("/control/disable-protection", responses={403: {"description": "Super admin required"}})
    def disable_protection_mode(
        auth: AuthDep, x_super_admin_key: Annotated[str | None, Header(alias="X-Super-Admin-Key")] = None
    ) -> dict[str, Any]:
        return execute_disable_protection_mode(context_runtime, auth, x_super_admin_key)

    @router.post("/learning/feedback")
    def collect_ira_feedback(payload: IRAFeedbackRequest, auth: AuthDep) -> dict[str, Any]:
        return execute_collect_ira_feedback(context_runtime, payload, auth)

    @router.get("/disputes/dashboard")
    def ira_disputes_dashboard(auth: AuthDep) -> dict[str, Any]:
        return execute_ira_disputes_dashboard(context_runtime, auth)

    @router.get("/crm/hybrid-recommendation")
    def ira_crm_hybrid_recommendation(auth: AuthDep) -> dict[str, Any]:
        return execute_ira_crm_hybrid_recommendation(context_runtime, auth)

    @router.get("/crm/connectors/status")
    def ira_crm_connectors_status(auth: AuthDep) -> dict[str, Any]:
        return execute_ira_crm_connectors_status(context_runtime, auth)

    @router.post(
        "/crm/feature-governance",
        responses={403: {"description": "Super admin required"}, 422: {"description": "Policy validation failed"}},
    )
    def update_crm_feature_governance(
        payload: IRACrmGovernanceUpdateRequest,
        auth: AuthDep,
        x_super_admin_key: Annotated[str | None, Header(alias="X-Super-Admin-Key")] = None,
    ) -> dict[str, Any]:
        return execute_update_crm_feature_governance(context_runtime, payload, auth, x_super_admin_key)

    @router.post("/advisor/recommendations", responses={403: {"description": "Super admin required"}})
    def get_ira_recommendations(
        payload: IRAAdviceRequest,
        auth: AuthDep,
        x_super_admin_key: Annotated[str | None, Header(alias="X-Super-Admin-Key")] = None,
    ) -> dict[str, Any]:
        return execute_get_ira_recommendations(context_runtime, payload, auth, x_super_admin_key)
