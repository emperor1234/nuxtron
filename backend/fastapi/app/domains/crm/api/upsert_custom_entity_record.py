"""Crm HTTP adapters beginning with upsert custom entity record."""

from ..constants import AUTOMATION_RECIPE_NOT_FOUND
from ..constants import AuthDep
from ..constants import ENTITY_TYPE_NOT_FOUND
from ..operations.create_api_token import execute_create_api_token
from ..operations.create_api_token import execute_get_forecast
from ..operations.create_api_token import execute_list_api_tokens
from ..operations.create_workflow_rule import execute_create_automation_recipe
from ..operations.create_workflow_rule import execute_list_automation_recipes
from ..operations.create_workflow_rule import execute_list_custom_entity_records
from ..operations.create_workflow_rule import execute_run_automation_recipe
from ..operations.create_workflow_rule import execute_upsert_custom_entity_record
from ..runtime import ContextRuntime
from ..schemas import APITokenCreateRequest
from ..schemas import AutomationRecipeCreateRequest
from ..schemas import CustomEntityRecordUpsertRequest
from fastapi import APIRouter
from fastapi import Query
from typing import Annotated
from typing import Any


def register(router: APIRouter, runtime: ContextRuntime):

    @router.post("/crm/custom-entities/{entity_key}/records", responses={404: {"description": ENTITY_TYPE_NOT_FOUND}})
    def upsert_custom_entity_record(
        entity_key: str, payload: CustomEntityRecordUpsertRequest, auth: AuthDep
    ) -> dict[str, Any]:
        return execute_upsert_custom_entity_record(runtime, entity_key, payload, auth)

    @router.get("/crm/custom-entities/{entity_key}/records", responses={404: {"description": ENTITY_TYPE_NOT_FOUND}})
    def list_custom_entity_records(
        entity_key: str,
        auth: AuthDep,
        limit: Annotated[int, Query(ge=1, le=250)] = 100,
        offset: Annotated[int, Query(ge=0)] = 0,
    ) -> dict[str, Any]:
        return execute_list_custom_entity_records(runtime, entity_key, auth, limit, offset)

    @router.post("/crm/automation/recipes")
    def create_automation_recipe(payload: AutomationRecipeCreateRequest, auth: AuthDep) -> dict[str, Any]:
        return execute_create_automation_recipe(runtime, payload, auth)

    @router.get("/crm/automation/recipes")
    def list_automation_recipes(auth: AuthDep) -> dict[str, Any]:
        return execute_list_automation_recipes(runtime, auth)

    @router.post(
        "/crm/automation/recipes/{recipe_id}/run", responses={404: {"description": AUTOMATION_RECIPE_NOT_FOUND}}
    )
    def run_automation_recipe(recipe_id: int, auth: AuthDep) -> dict[str, Any]:
        return execute_run_automation_recipe(runtime, recipe_id, auth)

    @router.post("/crm/api-tokens")
    def create_api_token(payload: APITokenCreateRequest, auth: AuthDep) -> dict[str, Any]:
        return execute_create_api_token(runtime, payload, auth)

    @router.get("/crm/api-tokens")
    def list_api_tokens(auth: AuthDep) -> dict[str, Any]:
        return execute_list_api_tokens(runtime, auth)

    @router.get("/crm/reports/forecast")
    def get_forecast(auth: AuthDep, days: Annotated[int, Query(ge=7, le=365)] = 30) -> dict[str, Any]:
        return execute_get_forecast(runtime, auth, days)
