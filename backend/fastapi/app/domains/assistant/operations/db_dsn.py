"""Assistant use cases: db dsn."""

from ..services import reasoning_support as port_compute_tenant_revenue_snapshot
from ....deps import AuthContext
from ..constants import APPLICATION_JSON
from ..constants import CRM_DEFAULT_OWNERSHIP
from ..constants import CRM_FEATURE_KEYS
from ..constants import EXPLICIT_APPROVAL_COMMAND_MARKERS
from ..constants import HUMAN_VALIDATION_COMMAND_MARKERS
from ..runtime import ContextRuntime
from ..schemas import IRAActionRequest
from ..schemas import IRATrainingPipelineRequest
from ..services.reasoning_support import _now_iso
from .ml_capabilities import helper_ml_capabilities
from datetime import datetime
from fastapi import HTTPException
from typing import Any
from typing import cast
import hmac
import httpx
import os
import psycopg


def helper_db_dsn() -> str:
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    db_name = os.getenv("POSTGRES_DB", "nuxtron")
    user = os.getenv("POSTGRES_USER", "nuxtron")
    password = os.getenv("POSTGRES_PASSWORD", "")
    return f"host={host} port={port} dbname={db_name} user={user} password={password} connect_timeout=2"


def helper_init_crm_governance_table(context_runtime: ContextRuntime) -> None:
    if context_runtime.crm_governance_table_ready:
        return
    with context_runtime.crm_governance_table_init_lock:
        if context_runtime.crm_governance_table_ready:
            return
        try:
            with psycopg.connect(helper_db_dsn()) as conn:
                conn.execute("SET lock_timeout = '2000ms'")
                conn.execute("SET statement_timeout = '5000ms'")
                with conn.cursor() as cur:
                    cur.execute(
                        "\n                            CREATE TABLE IF NOT EXISTS ira_crm_feature_governance (\n                                id BIGSERIAL PRIMARY KEY,\n                                tenant_id TEXT NOT NULL,\n                                feature_key TEXT NOT NULL,\n                                owner TEXT NOT NULL,\n                                duplicate_disabled BOOLEAN NOT NULL DEFAULT TRUE,\n                                notes TEXT NOT NULL DEFAULT '',\n                                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),\n                                UNIQUE (tenant_id, feature_key)\n                            )\n                            "
                    )
                conn.commit()
            context_runtime.crm_governance_table_ready = True
        except Exception:
            context_runtime.crm_governance_table_ready = False


def helper_default_crm_governance_map() -> dict[str, dict[str, Any]]:
    return {
        key: {
            "feature": key,
            "owner": owner,
            "duplicate_disabled": True,
            "secondary_disabled_for": "odoo" if owner == "corteza" else "corteza",
            "notes": "default ownership",
        }
        for key, owner in CRM_DEFAULT_OWNERSHIP.items()
    }


def helper_load_crm_governance(
    context_runtime: ContextRuntime, tenant_id: str, control: dict[str, Any]
) -> dict[str, dict[str, Any]]:
    governance = control.get("crm_feature_governance")
    if isinstance(governance, dict):
        cleaned: dict[str, dict[str, Any]] = {}
        governance_map = cast(dict[str, Any], governance)
        for key, value in governance_map.items():
            if not isinstance(value, dict):
                continue
            value_map = cast(dict[str, Any], value)
            cleaned[key] = {str(sub_key): sub_value for sub_key, sub_value in value_map.items()}
        return cleaned
    loaded = helper_default_crm_governance_map()
    helper_init_crm_governance_table(context_runtime)
    if context_runtime.crm_governance_table_ready:
        try:
            with psycopg.connect(helper_db_dsn()) as conn, conn.cursor() as cur:
                cur.execute(
                    "\n                            SELECT feature_key, owner, duplicate_disabled, notes, updated_at\n                            FROM ira_crm_feature_governance\n                            WHERE tenant_id = %s\n                            ",
                    (tenant_id,),
                )
                for feature_key, owner, duplicate_disabled, notes, updated_at in cur.fetchall():
                    feature = str(feature_key or "").strip()
                    if feature not in CRM_FEATURE_KEYS:
                        continue
                    owner_value = str(owner or "").strip().lower()
                    if owner_value not in {"corteza", "odoo"}:
                        continue
                    loaded[feature] = {
                        "feature": feature,
                        "owner": owner_value,
                        "duplicate_disabled": bool(duplicate_disabled),
                        "secondary_disabled_for": "odoo" if owner_value == "corteza" else "corteza",
                        "notes": str(notes or ""),
                        "updated_at": updated_at.isoformat() if isinstance(updated_at, datetime) else "",
                    }
        except Exception:
            pass
    control["crm_feature_governance"] = loaded
    return loaded


def helper_persist_crm_governance_row(context_runtime: ContextRuntime, tenant_id: str, row: dict[str, Any]) -> None:
    helper_init_crm_governance_table(context_runtime)
    if not context_runtime.crm_governance_table_ready:
        return
    try:
        with psycopg.connect(helper_db_dsn()) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "\n                        INSERT INTO ira_crm_feature_governance (tenant_id, feature_key, owner, duplicate_disabled, notes, updated_at)\n                        VALUES (%s, %s, %s, %s, %s, NOW())\n                        ON CONFLICT (tenant_id, feature_key)\n                        DO UPDATE SET\n                            owner = EXCLUDED.owner,\n                            duplicate_disabled = EXCLUDED.duplicate_disabled,\n                            notes = EXCLUDED.notes,\n                            updated_at = NOW()\n                        ",
                    (
                        tenant_id,
                        str(row.get("feature", "")),
                        str(row.get("owner", "corteza")),
                        bool(row.get("duplicate_disabled", True)),
                        str(row.get("notes", "")),
                    ),
                )
            conn.commit()
    except Exception:
        pass


def helper_probe_crm_connectors() -> dict[str, Any]:
    timeout = httpx.Timeout(connect=0.8, read=1.2, write=1.2, pool=0.8)
    probe_enabled = os.getenv("IRA_CONNECTOR_HEALTH_PROBE_ENABLED", "false").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    result: dict[str, Any] = {
        "corteza": {"configured": False, "healthy": False, "detail": "not configured"},
        "odoo": {"configured": False, "healthy": False, "detail": "not configured"},
    }
    corteza_base = os.getenv("CORTEZA_API_BASE_URL", "").strip().rstrip("/")
    corteza_token = os.getenv("CORTEZA_API_TOKEN", "").strip()
    if corteza_base:
        headers = {"Accept": APPLICATION_JSON}
        if corteza_token:
            headers["Authorization"] = f"Bearer {corteza_token}"
        result["corteza"]["configured"] = True
        if not probe_enabled:
            result["corteza"]["detail"] = "probe disabled"
        else:
            try:
                response = httpx.get(f"{corteza_base}/healthcheck", headers=headers, timeout=timeout)
                result["corteza"]["healthy"] = response.is_success
                result["corteza"]["detail"] = f"status={response.status_code}"
            except Exception as ex:
                result["corteza"]["detail"] = str(ex)
    odoo_base = os.getenv("ODOO_API_BASE_URL", "").strip().rstrip("/")
    odoo_api_key = os.getenv("ODOO_API_KEY", "").strip()
    if odoo_base:
        headers = {"Accept": APPLICATION_JSON}
        if odoo_api_key:
            headers["X-API-Key"] = odoo_api_key
        result["odoo"]["configured"] = True
        if not probe_enabled:
            result["odoo"]["detail"] = "probe disabled"
        else:
            try:
                response = httpx.get(f"{odoo_base}/web/health", headers=headers, timeout=timeout)
                result["odoo"]["healthy"] = response.is_success
                result["odoo"]["detail"] = f"status={response.status_code}"
            except Exception as ex:
                result["odoo"]["detail"] = str(ex)
    return result


def helper_audit(
    context_runtime: ContextRuntime, tenant_id: str, action: str, metadata: dict[str, Any] | None = None
) -> None:
    context_runtime.audit_log_memory.append(
        {
            "id": len(context_runtime.audit_log_memory) + 1,
            "tenant_id": tenant_id,
            "action": action,
            "source": "ira-router",
            "metadata": metadata or {},
            "created_at": _now_iso(),
        }
    )


def helper_append_ira_event(
    context_runtime: ContextRuntime, tenant_id: str, event_type: str, payload: dict[str, Any]
) -> dict[str, Any]:
    event: dict[str, Any] = {
        "id": len(context_runtime.ira_events_memory) + 1,
        "tenant_id": tenant_id,
        "event_type": event_type,
        "payload": payload,
        "created_at": _now_iso(),
    }
    context_runtime.ira_events_memory.append(event)
    return event


def helper_get_or_create_control(context_runtime: ContextRuntime, tenant_id: str) -> dict[str, Any]:
    existing = next((item for item in context_runtime.ira_controls_memory if item.get("tenant_id") == tenant_id), None)
    if existing is not None:
        return existing
    created: dict[str, Any] = {
        "id": len(context_runtime.ira_controls_memory) + 1,
        "tenant_id": tenant_id,
        "autonomy_enabled": True,
        "allow_high_impact_actions": False,
        "min_profit_margin_pct": 70.0,
        "suspicious_signal_threshold": 0.75,
        "require_super_admin": True,
        "max_dispute_auto_resolution_gbp": 50.0,
        "strict_policy_lock": True,
        "protection_mode": False,
        "blocked_actions": [],
        "updated_at": _now_iso(),
    }
    context_runtime.ira_controls_memory.append(created)
    return created


def helper_is_super_admin(key: str | None) -> bool:
    expected = os.getenv("SUPER_ADMIN_API_KEY", "").strip()
    supplied = (key or "").strip()
    if not expected:
        return False
    return hmac.compare_digest(expected, supplied)


def helper_require_super_admin_for_control(
    *, control: dict[str, Any], x_super_admin_key: str | None, detail: str
) -> None:
    if bool(control.get("require_super_admin", True)) and (not helper_is_super_admin(x_super_admin_key)):
        raise HTTPException(status_code=403, detail=detail)


def helper_requires_human_validation(payload: IRAActionRequest) -> bool:
    command = payload.command.strip().lower()
    if any((marker in command for marker in HUMAN_VALIDATION_COMMAND_MARKERS)):
        return True
    if bool(payload.payload.get("is_compliance_operation", False)):
        return True
    if bool(payload.payload.get("bulk", False)):
        return True
    if int(payload.payload.get("recipient_count", 1) or 1) > 1:
        return True
    return payload.target in {"email", "customer_support"}


def helper_requires_explicit_approval(payload: IRAActionRequest) -> bool:
    command = payload.command.strip().lower()
    return any((marker in command for marker in EXPLICIT_APPROVAL_COMMAND_MARKERS))


def helper_effective_actor_role(
    context_runtime: ContextRuntime, auth: AuthContext, *, verified_super_admin: bool
) -> str:
    """Derive the caller's IRA role from verified, server-side signals ONLY.

    `payload.actor_role` on IRAActionRequest is client-supplied and must
    never be trusted for authorization — it existed only as the input to
    this function, which is exactly the vulnerability being fixed.

    Two verified signals are honored, in order:
    1. `verified_super_admin` — the caller presented a valid
       `X-Super-Admin-Key` (checked via `_is_super_admin`, a real
       `hmac`-comparable server secret) before this function ever runs, on
       routes that require it. Possession of that secret is itself the
       privileged credential this router already defers to, so it maps to
       `super_admin` regardless of JWT roles (API-key auth carries none).
    2. `auth.roles` — populated server-side in deps.py from the bearer
       JWT's `roles` claim (empty for API-key auth otherwise).

    Returns the highest-precedence role actually present, defaulting to
    the least privileged ('customer') if neither signal grants one.
    """
    if verified_super_admin:
        return "super_admin"
    caller_roles = set(auth.roles)
    for role in context_runtime._ROLE_PRECEDENCE:
        if role in caller_roles:
            return role
    return "customer"


def helper_validate_rbac_abac(
    context_runtime: ContextRuntime, *, payload: IRAActionRequest, auth: AuthContext, verified_super_admin: bool = False
) -> None:
    effective_role = helper_effective_actor_role(context_runtime, auth, verified_super_admin=verified_super_admin)
    allowed = context_runtime._ROLE_ALLOWED_TARGETS.get(effective_role, set())
    if payload.target not in allowed:
        raise HTTPException(status_code=403, detail="RBAC policy denied this IRA action for the authenticated role.")
    if payload.dashboard_scope != "super_admin_dashboard":
        raise HTTPException(status_code=403, detail="ABAC policy requires super_admin_dashboard scope for IRA actions.")
    actor_tenant = str(payload.actor_attributes.get("tenant_id", "")).strip()
    if actor_tenant and actor_tenant != auth.tenant_id:
        raise HTTPException(status_code=403, detail="ABAC policy denied tenant mismatch for IRA action.")


def helper_get_or_create_connector(context_runtime: ContextRuntime, tenant_id: str, channel: str) -> dict[str, Any]:
    existing = next(
        (
            item
            for item in context_runtime.ira_connectors_memory
            if item.get("tenant_id") == tenant_id and item.get("channel") == channel
        ),
        None,
    )
    if existing is not None:
        return existing
    created: dict[str, Any] = {
        "id": len(context_runtime.ira_connectors_memory) + 1,
        "tenant_id": tenant_id,
        "channel": channel,
        "enabled": True,
        "provider": "internal",
        "config": {},
        "updated_at": _now_iso(),
    }
    context_runtime.ira_connectors_memory.append(created)
    return created


def helper_connector_enabled(context_runtime: ContextRuntime, tenant_id: str, channel: str) -> bool:
    return bool(helper_get_or_create_connector(context_runtime, tenant_id, channel).get("enabled", True))


def helper_free_tier_readiness(count: int) -> str:
    if count >= 3:
        return "full"
    if count > 0:
        return "partial"
    return "none"


def helper_validate_env_target_filename(value: str) -> tuple[bool, str]:
    candidate = value.strip()
    if not candidate:
        return (False, "target_file must not be empty.")
    if "/" in candidate or "\\" in candidate or ".." in candidate:
        return (False, "target_file must be a plain filename without path traversal.")
    if not candidate.startswith(".env"):
        return (False, "target_file must start with .env")
    return (True, candidate)


def helper_split_env_assignment(line: str) -> tuple[str, str] | None:
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return None
    if "=" not in stripped:
        return None
    key, value = stripped.split("=", 1)
    env_key = key.strip()
    if not env_key:
        return None
    return (env_key, value)


def helper_choose_pipeline_framework(payload: IRATrainingPipelineRequest) -> tuple[str, bool, str]:
    capabilities = helper_ml_capabilities()["frameworks"]
    if payload.framework != "auto":
        is_available = bool(capabilities.get(payload.framework, False))
        reason = "requested framework is installed" if is_available else "requested runtime is not installed yet"
        return (payload.framework, is_available, reason)
    if payload.pipeline_type == "rag" and bool(capabilities.get("sentence_transformers", False)):
        return ("sentence_transformers", True, "best local retrieval stack available")
    if bool(capabilities.get("pytorch", False)):
        return ("pytorch", True, "best available general-purpose training runtime")
    if bool(capabilities.get("tensorflow", False)):
        return ("tensorflow", True, "tensorflow runtime available")
    return (
        "sentence_transformers" if payload.pipeline_type == "rag" else "pytorch",
        False,
        "managed orchestration only until local runtime is installed",
    )


def helper_tenant_revenue_snapshot(context_runtime: ContextRuntime, tenant_id: str) -> dict[str, float]:
    return port_compute_tenant_revenue_snapshot.compute_tenant_revenue_snapshot(
        tenant_id=tenant_id,
        invoices_memory=context_runtime.invoices_memory,
        credit_ledger_memory=context_runtime.credit_ledger_memory,
    )
