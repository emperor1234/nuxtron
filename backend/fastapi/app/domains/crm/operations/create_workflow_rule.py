"""Crm use cases: create workflow rule."""

from ..constants import AUTOMATION_RECIPE_NOT_FOUND
from ..constants import AuthDep
from ..constants import ENTITY_TYPE_NOT_FOUND
from ..constants import PROJECT_NOT_FOUND
from ..constants import WORKFLOW_NOT_FOUND
from ..runtime import ContextRuntime
from ..schemas import AutomationRecipeCreateRequest
from ..schemas import CustomEntityRecordUpsertRequest
from ..schemas import CustomEntityTypeCreateRequest
from ..schemas import ProjectCreateRequest
from ..schemas import ProjectUpdateRequest
from ..schemas import WorkflowRuleCreateRequest
from .contact_to_dict import helper_create_db_workflow_rule
from .contact_to_dict import helper_list_db_workflow_rules
from .contact_to_dict import helper_trigger_db_workflow_rule
from .task_to_dict import helper_audit
from datetime import UTC
from datetime import datetime
from fastapi import HTTPException
from fastapi import Query
from typing import Annotated
from typing import Any


def execute_create_workflow_rule(
    runtime: ContextRuntime, payload: WorkflowRuleCreateRequest, auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:crm:workflows:create", 40, 60)
    try:
        workflow_rule, duplicate = helper_create_db_workflow_rule(auth.tenant_id, payload)
    except Exception:
        now = datetime.now(UTC).isoformat()
        duplicate_rule: dict[str, Any] | None = None
        created_rule: dict[str, Any] | None = None
        with runtime.lock:
            existing = next(
                (
                    r
                    for r in runtime.workflow_rules_memory
                    if r.get("tenant_id") == auth.tenant_id
                    and str(r.get("name", "")).strip().lower() == payload.name.strip().lower()
                    and (str(r.get("trigger", "")).strip().lower() == payload.trigger.strip().lower())
                    and (str(r.get("action", "")).strip().lower() == payload.action.strip().lower())
                ),
                None,
            )
            if existing is not None:
                duplicate_rule = existing.copy()
            else:
                rule: dict[str, Any] = {
                    "id": len(runtime.workflow_rules_memory) + 1,
                    "tenant_id": auth.tenant_id,
                    "name": payload.name,
                    "trigger": payload.trigger,
                    "conditions": payload.conditions,
                    "action": payload.action,
                    "action_params": payload.action_params,
                    "enabled": payload.enabled,
                    "run_count": 0,
                    "last_triggered_at": None,
                    "created_at": now,
                    "updated_at": now,
                }
                runtime.workflow_rules_memory.append(rule)
                created_rule = rule
        if duplicate_rule is not None:
            helper_audit(runtime, auth.tenant_id, "crm_workflow_rule_reused", int(duplicate_rule.get("id", 0)))
            return {
                "status": "ok",
                "tenant_id": auth.tenant_id,
                "workflow_rule": duplicate_rule,
                "duplicate": True,
                "created": False,
            }
        if created_rule is None:
            raise HTTPException(status_code=500, detail="Failed to create workflow rule.")
        helper_audit(runtime, auth.tenant_id, "crm_workflow_rule_created", int(created_rule["id"]))
        return {
            "status": "ok",
            "tenant_id": auth.tenant_id,
            "workflow_rule": created_rule,
            "duplicate": False,
            "created": True,
        }
    if duplicate:
        helper_audit(runtime, auth.tenant_id, "crm_workflow_rule_reused", int(workflow_rule.get("id", 0)))
        return {
            "status": "ok",
            "tenant_id": auth.tenant_id,
            "workflow_rule": workflow_rule,
            "duplicate": True,
            "created": False,
        }
    helper_audit(runtime, auth.tenant_id, "crm_workflow_rule_created", int(workflow_rule["id"]))
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "workflow_rule": workflow_rule,
        "duplicate": False,
        "created": True,
    }


def execute_list_workflow_rules(runtime: ContextRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:crm:workflows:list", 180, 60)
    try:
        items = helper_list_db_workflow_rules(auth.tenant_id)
    except Exception:
        with runtime.lock:
            items = [r.copy() for r in runtime.workflow_rules_memory if r.get("tenant_id") == auth.tenant_id]
    return {"status": "ok", "tenant_id": auth.tenant_id, "count": len(items), "workflow_rules": items}


def execute_trigger_workflow_rule(runtime: ContextRuntime, rule_id: int, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:crm:workflows:trigger", 60, 60)
    now = datetime.now(UTC).isoformat()
    try:
        snapshot = helper_trigger_db_workflow_rule(rule_id, auth.tenant_id, now)
        if snapshot is None:
            raise HTTPException(status_code=404, detail=WORKFLOW_NOT_FOUND)
    except HTTPException:
        raise
    except Exception:
        with runtime.lock:
            rule = next(
                (
                    r
                    for r in runtime.workflow_rules_memory
                    if r.get("id") == rule_id and r.get("tenant_id") == auth.tenant_id
                ),
                None,
            )
            if rule is None:
                raise HTTPException(status_code=404, detail=WORKFLOW_NOT_FOUND)
            rule["run_count"] = int(rule.get("run_count", 0)) + 1
            rule["last_triggered_at"] = now
            rule["updated_at"] = now
            snapshot = rule.copy()
    helper_audit(runtime, auth.tenant_id, "crm_workflow_triggered", rule_id)
    return {"status": "ok", "tenant_id": auth.tenant_id, "workflow_rule": snapshot, "triggered_at": now}


def execute_create_project(runtime: ContextRuntime, payload: ProjectCreateRequest, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:crm:projects:create", 80, 60)
    now = datetime.now(UTC).isoformat()
    duplicate_project: dict[str, Any] | None = None
    created_project: dict[str, Any] | None = None
    with runtime.lock:
        existing = next(
            (
                p
                for p in runtime.projects_memory
                if p.get("tenant_id") == auth.tenant_id
                and str(p.get("name", "")).strip().lower() == payload.name.strip().lower()
                and (str(p.get("owner", "")).strip().lower() == payload.owner.strip().lower())
            ),
            None,
        )
        if existing is not None:
            duplicate_project = existing.copy()
        else:
            project: dict[str, Any] = {
                "id": len(runtime.projects_memory) + 1,
                "tenant_id": auth.tenant_id,
                "name": payload.name,
                "description": payload.description,
                "owner": payload.owner,
                "status": payload.status,
                "due_date": payload.due_date,
                "created_at": now,
                "updated_at": now,
            }
            runtime.projects_memory.append(project)
            created_project = project
    if duplicate_project is not None:
        helper_audit(runtime, auth.tenant_id, "crm_project_reused", int(duplicate_project.get("id", 0)))
        return {
            "status": "ok",
            "tenant_id": auth.tenant_id,
            "project": duplicate_project,
            "duplicate": True,
            "created": False,
        }
    if created_project is None:
        raise HTTPException(status_code=500, detail="Failed to create project.")
    helper_audit(runtime, auth.tenant_id, "crm_project_created", int(created_project["id"]))
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "project": created_project,
        "duplicate": False,
        "created": True,
    }


def execute_list_projects(
    runtime: ContextRuntime,
    auth: AuthDep,
    status: Annotated[str | None, Query(max_length=40)] = None,
    owner: Annotated[str | None, Query(max_length=120)] = None,
    limit: Annotated[int, Query(ge=1, le=250)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:crm:projects:list", 240, 60)
    with runtime.lock:
        items = [p.copy() for p in runtime.projects_memory if p.get("tenant_id") == auth.tenant_id]
    if (status or "").strip():
        items = [p for p in items if str(p.get("status", "")).lower() == str(status).strip().lower()]
    if (owner or "").strip():
        items = [p for p in items if str(p.get("owner", "")).lower() == str(owner).strip().lower()]
    items.sort(key=lambda p: str(p.get("created_at", "")), reverse=True)
    total = len(items)
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "count": len(items[offset : offset + limit]),
        "total": total,
        "projects": items[offset : offset + limit],
    }


def execute_update_project(
    runtime: ContextRuntime, project_id: int, payload: ProjectUpdateRequest, auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:crm:projects:update", 120, 60)
    with runtime.lock:
        item = next(
            (
                p
                for p in runtime.projects_memory
                if p.get("tenant_id") == auth.tenant_id and int(p.get("id", 0)) == project_id
            ),
            None,
        )
        if item is None:
            raise HTTPException(status_code=404, detail=PROJECT_NOT_FOUND)
        if payload.name is not None:
            item["name"] = payload.name
        if payload.description is not None:
            item["description"] = payload.description
        if payload.owner is not None:
            item["owner"] = payload.owner
        if payload.status is not None:
            item["status"] = payload.status
        if payload.due_date is not None:
            item["due_date"] = payload.due_date
        item["updated_at"] = datetime.now(UTC).isoformat()
        snapshot = item.copy()
    helper_audit(runtime, auth.tenant_id, "crm_project_updated", project_id)
    return {"status": "ok", "tenant_id": auth.tenant_id, "project": snapshot}


def execute_projects_board(runtime: ContextRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:crm:projects:board", 180, 60)
    with runtime.lock:
        items = [p.copy() for p in runtime.projects_memory if p.get("tenant_id") == auth.tenant_id]
    columns: dict[str, list[dict[str, Any]]] = {"planning": [], "active": [], "blocked": [], "done": []}
    for item in items:
        key = str(item.get("status", "planning")).lower().replace(" ", "_")
        if key not in columns:
            columns[key] = []
        columns[key].append(item)
    return {"status": "ok", "tenant_id": auth.tenant_id, "board": columns}


def execute_create_custom_entity_type(
    runtime: ContextRuntime, payload: CustomEntityTypeCreateRequest, auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:crm:entities:types:create", 40, 60)
    now = datetime.now(UTC).isoformat()
    with runtime.lock:
        existing = next(
            (
                e
                for e in runtime.custom_entity_types_memory
                if e.get("tenant_id") == auth.tenant_id and str(e.get("key", "")).lower() == payload.key.lower()
            ),
            None,
        )
        if existing is not None:
            return {"status": "ok", "tenant_id": auth.tenant_id, "entity_type": existing, "duplicate": True}
        entity_type: dict[str, Any] = {
            "id": len(runtime.custom_entity_types_memory) + 1,
            "tenant_id": auth.tenant_id,
            "key": payload.key,
            "name": payload.name,
            "description": payload.description,
            "fields": payload.fields,
            "created_at": now,
            "updated_at": now,
        }
        runtime.custom_entity_types_memory.append(entity_type)
    helper_audit(runtime, auth.tenant_id, "crm_custom_entity_type_created", int(entity_type["id"]))
    return {"status": "ok", "tenant_id": auth.tenant_id, "entity_type": entity_type}


def execute_list_custom_entity_types(runtime: ContextRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:crm:entities:types:list", 120, 60)
    with runtime.lock:
        items = [e.copy() for e in runtime.custom_entity_types_memory if e.get("tenant_id") == auth.tenant_id]
    items.sort(key=lambda e: str(e.get("created_at", "")), reverse=True)
    return {"status": "ok", "tenant_id": auth.tenant_id, "count": len(items), "entity_types": items}


def execute_upsert_custom_entity_record(
    runtime: ContextRuntime, entity_key: str, payload: CustomEntityRecordUpsertRequest, auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:crm:entities:records:upsert", 120, 60)
    now = datetime.now(UTC).isoformat()
    with runtime.lock:
        entity_type = next(
            (
                e
                for e in runtime.custom_entity_types_memory
                if e.get("tenant_id") == auth.tenant_id and str(e.get("key", "")) == entity_key
            ),
            None,
        )
        if entity_type is None:
            raise HTTPException(status_code=404, detail=ENTITY_TYPE_NOT_FOUND)
        record: dict[str, Any] = {
            "id": len(runtime.custom_entity_records_memory) + 1,
            "tenant_id": auth.tenant_id,
            "entity_key": entity_key,
            "values": payload.values,
            "created_at": now,
            "updated_at": now,
        }
        runtime.custom_entity_records_memory.append(record)
    helper_audit(runtime, auth.tenant_id, "crm_custom_entity_record_created", int(record["id"]))
    return {"status": "ok", "tenant_id": auth.tenant_id, "record": record}


def execute_list_custom_entity_records(
    runtime: ContextRuntime,
    entity_key: str,
    auth: AuthDep,
    limit: Annotated[int, Query(ge=1, le=250)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:crm:entities:records:list", 180, 60)
    with runtime.lock:
        entity_type = next(
            (
                e
                for e in runtime.custom_entity_types_memory
                if e.get("tenant_id") == auth.tenant_id and str(e.get("key", "")) == entity_key
            ),
            None,
        )
        if entity_type is None:
            raise HTTPException(status_code=404, detail=ENTITY_TYPE_NOT_FOUND)
        items = [
            r.copy()
            for r in runtime.custom_entity_records_memory
            if r.get("tenant_id") == auth.tenant_id and str(r.get("entity_key", "")) == entity_key
        ]
    items.sort(key=lambda r: str(r.get("created_at", "")), reverse=True)
    total = len(items)
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "entity_key": entity_key,
        "count": len(items[offset : offset + limit]),
        "total": total,
        "records": items[offset : offset + limit],
    }


def execute_create_automation_recipe(
    runtime: ContextRuntime, payload: AutomationRecipeCreateRequest, auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:crm:automation:create", 60, 60)
    now = datetime.now(UTC).isoformat()
    duplicate_recipe: dict[str, Any] | None = None
    created_recipe: dict[str, Any] | None = None
    with runtime.lock:
        existing = next(
            (
                r
                for r in runtime.automation_recipes_memory
                if r.get("tenant_id") == auth.tenant_id
                and str(r.get("name", "")).strip().lower() == payload.name.strip().lower()
                and (str(r.get("trigger", "")).strip().lower() == payload.trigger.strip().lower())
                and (str(r.get("action", "")).strip().lower() == payload.action.strip().lower())
            ),
            None,
        )
        if existing is not None:
            duplicate_recipe = existing.copy()
        else:
            recipe: dict[str, Any] = {
                "id": len(runtime.automation_recipes_memory) + 1,
                "tenant_id": auth.tenant_id,
                "name": payload.name,
                "trigger": payload.trigger,
                "action": payload.action,
                "config": payload.config,
                "enabled": payload.enabled,
                "run_count": 0,
                "last_run_at": None,
                "created_at": now,
                "updated_at": now,
            }
            runtime.automation_recipes_memory.append(recipe)
            created_recipe = recipe
    if duplicate_recipe is not None:
        helper_audit(runtime, auth.tenant_id, "crm_automation_recipe_reused", int(duplicate_recipe.get("id", 0)))
        return {
            "status": "ok",
            "tenant_id": auth.tenant_id,
            "recipe": duplicate_recipe,
            "duplicate": True,
            "created": False,
        }
    if created_recipe is None:
        raise HTTPException(status_code=500, detail="Failed to create automation recipe.")
    helper_audit(runtime, auth.tenant_id, "crm_automation_recipe_created", int(created_recipe["id"]))
    return {"status": "ok", "tenant_id": auth.tenant_id, "recipe": created_recipe, "duplicate": False, "created": True}


def execute_list_automation_recipes(runtime: ContextRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:crm:automation:list", 180, 60)
    with runtime.lock:
        items = [r.copy() for r in runtime.automation_recipes_memory if r.get("tenant_id") == auth.tenant_id]
    items.sort(key=lambda r: str(r.get("created_at", "")), reverse=True)
    return {"status": "ok", "tenant_id": auth.tenant_id, "count": len(items), "recipes": items}


def execute_run_automation_recipe(runtime: ContextRuntime, recipe_id: int, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:crm:automation:run", 60, 60)
    now = datetime.now(UTC).isoformat()
    with runtime.lock:
        item = next(
            (
                r
                for r in runtime.automation_recipes_memory
                if r.get("tenant_id") == auth.tenant_id and int(r.get("id", 0)) == recipe_id
            ),
            None,
        )
        if item is None:
            raise HTTPException(status_code=404, detail=AUTOMATION_RECIPE_NOT_FOUND)
        item["run_count"] = int(item.get("run_count", 0)) + 1
        item["last_run_at"] = now
        item["updated_at"] = now
        snapshot = item.copy()
    helper_audit(runtime, auth.tenant_id, "crm_automation_recipe_ran", recipe_id)
    return {"status": "ok", "tenant_id": auth.tenant_id, "recipe": snapshot, "run_at": now}
