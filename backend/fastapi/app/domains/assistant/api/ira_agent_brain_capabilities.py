"""Assistant HTTP adapters beginning with ira agent brain capabilities."""

from ..constants import AuthDep
from ..operations.ira_copilot_plan import execute_ira_agent_brain_capabilities
from ..operations.ira_copilot_plan import execute_ira_agent_brain_reason
from ..operations.ira_copilot_plan import execute_ira_agent_preferences_update
from ..operations.ira_copilot_plan import execute_ira_agent_run
from ..operations.ira_copilot_plan import execute_ira_ml_upsert_knowledge
from ..operations.ira_ml_retrieval_query import execute_ira_ml_create_fine_tuning_job
from ..operations.ira_ml_retrieval_query import execute_ira_ml_create_pipeline
from ..operations.ira_ml_retrieval_query import execute_ira_ml_retrieval_query
from ..runtime import ContextRuntime
from ..schemas import IRAAgentBrainReasonRequest
from ..schemas import IRAAgentPreferenceUpdateRequest
from ..schemas import IRAAgentRunRequest
from ..schemas import IRAFineTuningJobRequest
from ..schemas import IRAKnowledgeDocumentRequest
from ..schemas import IRARetrievalQueryRequest
from ..schemas import IRATrainingPipelineRequest
from fastapi import APIRouter
from fastapi import Header
from typing import Annotated
from typing import Any


def register(router: APIRouter, context_runtime: ContextRuntime):

    @router.get("/agent/brain/capabilities")
    def ira_agent_brain_capabilities(auth: AuthDep) -> dict[str, Any]:
        return execute_ira_agent_brain_capabilities(context_runtime, auth)

    @router.post("/agent/brain/reason")
    def ira_agent_brain_reason(payload: IRAAgentBrainReasonRequest, auth: AuthDep) -> dict[str, Any]:
        return execute_ira_agent_brain_reason(context_runtime, payload, auth)

    @router.post("/agent/preferences", responses={403: {"description": "Super admin required"}})
    def ira_agent_preferences_update(
        payload: IRAAgentPreferenceUpdateRequest,
        auth: AuthDep,
        x_super_admin_key: Annotated[str | None, Header(alias="X-Super-Admin-Key")] = None,
    ) -> dict[str, Any]:
        return execute_ira_agent_preferences_update(context_runtime, payload, auth, x_super_admin_key)

    @router.post(
        "/agent/run",
        responses={403: {"description": "Super admin required"}, 422: {"description": "IRA autonomy disabled"}},
    )
    def ira_agent_run(
        payload: IRAAgentRunRequest,
        auth: AuthDep,
        x_super_admin_key: Annotated[str | None, Header(alias="X-Super-Admin-Key")] = None,
    ) -> dict[str, Any]:
        return execute_ira_agent_run(context_runtime, payload, auth, x_super_admin_key)

    @router.post("/ml/knowledge/upsert")
    def ira_ml_upsert_knowledge(payload: IRAKnowledgeDocumentRequest, auth: AuthDep) -> dict[str, Any]:
        return execute_ira_ml_upsert_knowledge(context_runtime, payload, auth)

    @router.post("/ml/retrieval/query")
    def ira_ml_retrieval_query(payload: IRARetrievalQueryRequest, auth: AuthDep) -> dict[str, Any]:
        return execute_ira_ml_retrieval_query(context_runtime, payload, auth)

    @router.post(
        "/ml/fine-tuning/jobs",
        responses={
            403: {"description": "Super admin required"},
            422: {"description": "Provider configuration missing"},
        },
    )
    def ira_ml_create_fine_tuning_job(
        payload: IRAFineTuningJobRequest,
        auth: AuthDep,
        x_super_admin_key: Annotated[str | None, Header(alias="X-Super-Admin-Key")] = None,
    ) -> dict[str, Any]:
        return execute_ira_ml_create_fine_tuning_job(context_runtime, payload, auth, x_super_admin_key)

    @router.post("/ml/pipelines", responses={403: {"description": "Super admin required"}})
    def ira_ml_create_pipeline(
        payload: IRATrainingPipelineRequest,
        auth: AuthDep,
        x_super_admin_key: Annotated[str | None, Header(alias="X-Super-Admin-Key")] = None,
    ) -> dict[str, Any]:
        return execute_ira_ml_create_pipeline(context_runtime, payload, auth, x_super_admin_key)
