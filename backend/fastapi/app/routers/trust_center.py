# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnknownParameterType=false, reportUnusedFunction=false

"""
Trust Center — Flywheel Module 2.
Governance posture, policy history, approval chains, incidents.
DB-first (psycopg3) with in-memory fallback.
"""

import json
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Annotated, Any, Literal

import psycopg
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..deps import AuthContext, require_auth

AuthDep = Annotated[AuthContext, Depends(require_auth)]


@dataclass(frozen=True)
class TrustCenterContext:
    enforce_rate_limit: Any
    policy_history_memory: list[dict[str, Any]]
    approval_chains_memory: list[dict[str, Any]]
    incidents_memory: list[dict[str, Any]]
    governance_snapshots_memory: list[dict[str, Any]]
    audit_log_memory: list[dict[str, Any]]
    get_db_ready: Callable[[], bool] = field(default=lambda: False)
    db_dsn: Callable[[], str] = field(default=lambda: "")


class PolicyChangeRequest(BaseModel):
    policy_key: str = Field(min_length=1, max_length=120)
    old_value: dict[str, Any] | None = None
    new_value: dict[str, Any] = Field(default_factory=dict)
    change_reason: str = Field(min_length=1, max_length=500)
    actor_role: str = Field(default="admin", max_length=80)
    requires_human_validation: bool = False
    approved_by: str = Field(default="", max_length=180)


class ApprovalChainRequest(BaseModel):
    chain_name: str = Field(min_length=1, max_length=120)
    action_type: str = Field(min_length=1, max_length=120)
    steps: list[dict[str, Any]] = Field(default_factory=list)
    require_all: bool = True


class IncidentRequest(BaseModel):
    title: str = Field(min_length=3, max_length=255)
    description: str = Field(min_length=5, max_length=2000)
    severity: Literal["critical", "high", "medium", "low"] = "medium"
    affected_module: str = Field(default="ira", max_length=120)
    resolved: bool = False
    resolution_notes: str = Field(default="", max_length=2000)


class GovernanceSnapshotRequest(BaseModel):
    autonomy_enabled: bool = True
    allow_high_impact_actions: bool = False
    strict_policy_lock: bool = True
    policy_change_human_validation: bool = False
    notes: str = Field(default="", max_length=1000)


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _posture_rating(score: float) -> str:
    if score < 40:
        return "critical"
    if score < 70:
        return "warning"
    return "healthy"


def _db_count_open_incidents(db_dsn: Callable[[], str], tenant_id: str) -> tuple[int, int]:
    """Returns (total_open, critical_open)."""
    with psycopg.connect(db_dsn()) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*), COUNT(*) FILTER (WHERE severity='critical') FROM trust_incidents WHERE tenant_id=%s AND resolved=FALSE",
                (tenant_id,),
            )
            row = cur.fetchone()
    return (int(row[0] or 0), int(row[1] or 0)) if row else (0, 0)


def _db_count_active_chains(db_dsn: Callable[[], str], tenant_id: str) -> int:
    with psycopg.connect(db_dsn()) as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) FROM trust_approval_chains WHERE tenant_id=%s AND active=TRUE",
            (tenant_id,),
        )
        row = cur.fetchone()
    return int(row[0] or 0) if row else 0


def _mem_count_open_incidents(incidents: list[dict[str, Any]], tenant_id: str) -> tuple[int, int]:
    open_inc = sum(1 for i in incidents if i.get("tenant_id") == tenant_id and not i.get("resolved"))
    crit_inc = sum(1 for i in incidents if i.get("tenant_id") == tenant_id and not i.get("resolved") and i.get("severity") == "critical")
    return open_inc, crit_inc


def _mem_count_active_chains(chains: list[dict[str, Any]], tenant_id: str) -> int:
    return sum(1 for c in chains if c.get("tenant_id") == tenant_id and c.get("active"))


def _get_posture_counts(ctx: TrustCenterContext, tenant_id: str) -> tuple[int, int, int]:
    """Returns (open_incidents, critical_incidents, active_chains)."""
    if ctx.get_db_ready():
        try:
            open_inc, crit_inc = _db_count_open_incidents(ctx.db_dsn, tenant_id)
            active_chains = _db_count_active_chains(ctx.db_dsn, tenant_id)
            return open_inc, crit_inc, active_chains
        except Exception:
            pass
    open_inc, crit_inc = _mem_count_open_incidents(ctx.incidents_memory, tenant_id)
    active_chains = _mem_count_active_chains(ctx.approval_chains_memory, tenant_id)
    return open_inc, crit_inc, active_chains


# ── Route handler helpers ─────────────────────────────────────────────────────

def _handle_record_policy(ctx: TrustCenterContext, body: PolicyChangeRequest, auth: AuthContext) -> dict[str, Any]:
    ctx.enforce_rate_limit(f"{auth.tenant_id}:trust_record_policy", 120, 60)
    policy_id = str(uuid.uuid4())
    record: dict[str, Any] = {
        "id": policy_id, "tenant_id": auth.tenant_id,
        "policy_key": body.policy_key, "old_value": body.old_value,
        "new_value": body.new_value, "change_reason": body.change_reason,
        "actor_role": body.actor_role,
        "requires_human_validation": body.requires_human_validation,
        "approved_by": body.approved_by, "created_at": _now_iso(),
    }
    if ctx.get_db_ready():
        try:
            with psycopg.connect(ctx.db_dsn()) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO trust_policy_history
                            (id,tenant_id,policy_key,old_value,new_value,change_reason,
                             actor_role,requires_human_validation,approved_by,created_at)
                        VALUES (%s,%s,%s,%s::jsonb,%s::jsonb,%s,%s,%s,%s,%s)
                        ON CONFLICT (id) DO NOTHING
                        """,
                        (policy_id, auth.tenant_id, body.policy_key,
                         json.dumps(body.old_value), json.dumps(body.new_value),
                         body.change_reason, body.actor_role,
                         body.requires_human_validation, body.approved_by, record["created_at"]),
                    )
                conn.commit()
        except Exception:
            ctx.policy_history_memory.append(record)
    else:
        ctx.policy_history_memory.append(record)
    ctx.audit_log_memory.append({
        "id": str(uuid.uuid4()), "tenant_id": auth.tenant_id,
        "event": "trust.policy_changed", "policy_key": body.policy_key, "created_at": _now_iso(),
    })
    return {"policy_id": policy_id, "status": "recorded"}


def _handle_list_policies(ctx: TrustCenterContext, auth: AuthContext) -> dict[str, Any]:
    ctx.enforce_rate_limit(f"{auth.tenant_id}:trust_list_policies", 120, 60)
    if ctx.get_db_ready():
        try:
            with psycopg.connect(ctx.db_dsn()) as conn, conn.cursor() as cur:
                cur.execute(
                    """
                        SELECT id,tenant_id,policy_key,old_value,new_value,change_reason,
                               actor_role,requires_human_validation,approved_by,created_at
                        FROM trust_policy_history WHERE tenant_id=%s ORDER BY created_at DESC LIMIT 200
                        """,
                    (auth.tenant_id,),
                )
                rows = cur.fetchall()
            policies = [
                {"id": str(r[0]), "tenant_id": str(r[1]), "policy_key": str(r[2]),
                 "old_value": r[3], "new_value": r[4], "change_reason": str(r[5]),
                 "actor_role": str(r[6]), "requires_human_validation": bool(r[7]),
                 "approved_by": str(r[8] or ""),
                 "created_at": r[9].isoformat() if hasattr(r[9], "isoformat") else str(r[9])}
                for r in rows
            ]
            return {"policies": policies, "total": len(policies)}
        except Exception:
            pass
    policies = [p for p in ctx.policy_history_memory if p.get("tenant_id") == auth.tenant_id]
    return {"policies": policies, "total": len(policies)}


def _handle_create_chain(ctx: TrustCenterContext, body: ApprovalChainRequest, auth: AuthContext) -> dict[str, Any]:
    ctx.enforce_rate_limit(f"{auth.tenant_id}:trust_create_chain", 120, 60)
    chain_id = str(uuid.uuid4())
    record: dict[str, Any] = {
        "id": chain_id, "tenant_id": auth.tenant_id,
        "chain_name": body.chain_name, "action_type": body.action_type,
        "steps": body.steps, "require_all": body.require_all,
        "active": True, "created_at": _now_iso(),
    }
    if ctx.get_db_ready():
        try:
            with psycopg.connect(ctx.db_dsn()) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO trust_approval_chains
                            (id,tenant_id,chain_name,action_type,steps,require_all,active,created_at)
                        VALUES (%s,%s,%s,%s,%s::jsonb,%s,%s,%s) ON CONFLICT (id) DO NOTHING
                        """,
                        (chain_id, auth.tenant_id, body.chain_name, body.action_type,
                         json.dumps(body.steps), body.require_all, True, record["created_at"]),
                    )
                conn.commit()
        except Exception:
            ctx.approval_chains_memory.append(record)
    else:
        ctx.approval_chains_memory.append(record)
    return {"chain_id": chain_id, "status": "created"}


def _handle_list_chains(ctx: TrustCenterContext, auth: AuthContext) -> dict[str, Any]:
    ctx.enforce_rate_limit(f"{auth.tenant_id}:trust_list_chains", 120, 60)
    if ctx.get_db_ready():
        try:
            with psycopg.connect(ctx.db_dsn()) as conn, conn.cursor() as cur:
                cur.execute(
                    """
                        SELECT id,tenant_id,chain_name,action_type,steps,require_all,active,created_at
                        FROM trust_approval_chains WHERE tenant_id=%s AND active=TRUE ORDER BY created_at DESC
                        """,
                    (auth.tenant_id,),
                )
                rows = cur.fetchall()
            chains = [
                {"id": str(r[0]), "tenant_id": str(r[1]), "chain_name": str(r[2]),
                 "action_type": str(r[3]), "steps": r[4] or [], "require_all": bool(r[5]),
                 "active": bool(r[6]),
                 "created_at": r[7].isoformat() if hasattr(r[7], "isoformat") else str(r[7])}
                for r in rows
            ]
            return {"chains": chains, "total": len(chains)}
        except Exception:
            pass
    chains = [
        c for c in ctx.approval_chains_memory
        if c.get("tenant_id") == auth.tenant_id and c.get("active")
    ]
    return {"chains": chains, "total": len(chains)}


def _handle_deactivate_chain(ctx: TrustCenterContext, chain_id: str, auth: AuthContext) -> dict[str, Any]:
    ctx.enforce_rate_limit(f"{auth.tenant_id}:trust_delete_chain", 120, 60)
    if ctx.get_db_ready():
        try:
            with psycopg.connect(ctx.db_dsn()) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE trust_approval_chains SET active=FALSE WHERE id=%s AND tenant_id=%s RETURNING id",
                        (chain_id, auth.tenant_id),
                    )
                    row = cur.fetchone()
                conn.commit()
            if row is None:
                raise HTTPException(status_code=404, detail="Approval chain not found")
            return {"chain_id": chain_id, "status": "deactivated"}
        except HTTPException:
            raise
        except Exception:
            pass
    chain = next(
        (c for c in ctx.approval_chains_memory
         if c.get("id") == chain_id and c.get("tenant_id") == auth.tenant_id),
        None,
    )
    if chain is None:
        raise HTTPException(status_code=404, detail="Approval chain not found")
    chain["active"] = False
    return {"chain_id": chain_id, "status": "deactivated"}


def _handle_create_incident(ctx: TrustCenterContext, body: IncidentRequest, auth: AuthContext) -> dict[str, Any]:
    ctx.enforce_rate_limit(f"{auth.tenant_id}:trust_create_incident", 120, 60)
    incident_id = str(uuid.uuid4())
    record: dict[str, Any] = {
        "id": incident_id, "tenant_id": auth.tenant_id,
        "title": body.title, "description": body.description,
        "severity": body.severity, "affected_module": body.affected_module,
        "resolved": body.resolved, "resolution_notes": body.resolution_notes,
        "created_at": _now_iso(),
        "resolved_at": _now_iso() if body.resolved else None,
    }
    if ctx.get_db_ready():
        try:
            with psycopg.connect(ctx.db_dsn()) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO trust_incidents
                            (id,tenant_id,title,description,severity,affected_module,
                             resolved,resolution_notes,resolved_at,created_at)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (id) DO NOTHING
                        """,
                        (incident_id, auth.tenant_id, body.title, body.description,
                         body.severity, body.affected_module, body.resolved,
                         body.resolution_notes, record["resolved_at"], record["created_at"]),
                    )
                conn.commit()
        except Exception:
            ctx.incidents_memory.append(record)
    else:
        ctx.incidents_memory.append(record)
    ctx.audit_log_memory.append({
        "id": str(uuid.uuid4()), "tenant_id": auth.tenant_id,
        "event": "trust.incident_created", "incident_id": incident_id,
        "severity": body.severity, "created_at": _now_iso(),
    })
    return {"incident_id": incident_id, "status": "created"}


def _handle_resolve_incident(ctx: TrustCenterContext, incident_id: str, body: dict[str, Any], auth: AuthContext) -> dict[str, Any]:
    ctx.enforce_rate_limit(f"{auth.tenant_id}:trust_resolve_incident", 120, 60)
    notes = str(body.get("resolution_notes", ""))[:1000]
    if ctx.get_db_ready():
        try:
            with psycopg.connect(ctx.db_dsn()) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        UPDATE trust_incidents
                        SET resolved=TRUE, resolution_notes=%s, resolved_at=NOW()
                        WHERE id=%s AND tenant_id=%s RETURNING id
                        """,
                        (notes, incident_id, auth.tenant_id),
                    )
                    row = cur.fetchone()
                conn.commit()
            if row is None:
                raise HTTPException(status_code=404, detail="Incident not found")
            return {"incident_id": incident_id, "status": "resolved"}
        except HTTPException:
            raise
        except Exception:
            pass
    incident = next(
        (i for i in ctx.incidents_memory
         if i.get("id") == incident_id and i.get("tenant_id") == auth.tenant_id),
        None,
    )
    if incident is None:
        raise HTTPException(status_code=404, detail="Incident not found")
    incident["resolved"] = True
    incident["resolution_notes"] = notes
    incident["resolved_at"] = _now_iso()
    return {"incident_id": incident_id, "status": "resolved"}


def _handle_list_incidents(ctx: TrustCenterContext, auth: AuthContext) -> dict[str, Any]:
    ctx.enforce_rate_limit(f"{auth.tenant_id}:trust_list_incidents", 120, 60)
    if ctx.get_db_ready():
        try:
            with psycopg.connect(ctx.db_dsn()) as conn, conn.cursor() as cur:
                cur.execute(
                    """
                        SELECT id,tenant_id,title,description,severity,affected_module,
                               resolved,resolution_notes,resolved_at,created_at
                        FROM trust_incidents WHERE tenant_id=%s ORDER BY created_at DESC LIMIT 200
                        """,
                    (auth.tenant_id,),
                )
                rows = cur.fetchall()
            incidents = [
                {"id": str(r[0]), "tenant_id": str(r[1]), "title": str(r[2]),
                 "description": str(r[3]), "severity": str(r[4]),
                 "affected_module": str(r[5]), "resolved": bool(r[6]),
                 "resolution_notes": str(r[7] or ""),
                 "resolved_at": r[8].isoformat() if r[8] and hasattr(r[8], "isoformat") else None,
                 "created_at": r[9].isoformat() if hasattr(r[9], "isoformat") else str(r[9])}
                for r in rows
            ]
            return {"incidents": incidents, "total": len(incidents)}
        except Exception:
            pass
    incidents = [i for i in ctx.incidents_memory if i.get("tenant_id") == auth.tenant_id]
    return {"incidents": incidents, "total": len(incidents)}


def _handle_capture_snapshot(ctx: TrustCenterContext, body: GovernanceSnapshotRequest, auth: AuthContext) -> dict[str, Any]:
    ctx.enforce_rate_limit(f"{auth.tenant_id}:trust_capture_snapshot", 120, 60)
    snapshot_id = str(uuid.uuid4())
    open_inc, _, active_chains = _get_posture_counts(ctx, auth.tenant_id)
    snap: dict[str, Any] = {
        "id": snapshot_id, "tenant_id": auth.tenant_id,
        "autonomy_enabled": body.autonomy_enabled,
        "allow_high_impact_actions": body.allow_high_impact_actions,
        "strict_policy_lock": body.strict_policy_lock,
        "policy_change_human_validation": body.policy_change_human_validation,
        "active_approval_chains": active_chains,
        "open_incidents": open_inc, "notes": body.notes, "created_at": _now_iso(),
    }
    if ctx.get_db_ready():
        try:
            with psycopg.connect(ctx.db_dsn()) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO trust_governance_snapshots
                            (id,tenant_id,autonomy_enabled,allow_high_impact_actions,
                             strict_policy_lock,policy_change_human_validation,
                             active_approval_chains,open_incidents,notes,created_at)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (id) DO NOTHING
                        """,
                        (snapshot_id, auth.tenant_id, body.autonomy_enabled,
                         body.allow_high_impact_actions, body.strict_policy_lock,
                         body.policy_change_human_validation, active_chains,
                         open_inc, body.notes, snap["created_at"]),
                    )
                conn.commit()
        except Exception:
            ctx.governance_snapshots_memory.append(snap)
    else:
        ctx.governance_snapshots_memory.append(snap)
    return {"snapshot_id": snapshot_id, "status": "captured"}


def _handle_get_posture(ctx: TrustCenterContext, auth: AuthContext) -> dict[str, Any]:
    ctx.enforce_rate_limit(f"{auth.tenant_id}:trust_posture", 120, 60)
    open_inc, crit_inc, active_chains = _get_posture_counts(ctx, auth.tenant_id)
    posture_score = max(0, 100 - (crit_inc * 25) - (open_inc * 5))
    return {
        "tenant_id": auth.tenant_id, "posture_score": posture_score,
        "open_incidents": open_inc, "critical_open_incidents": crit_inc,
        "active_approval_chains": active_chains,
        "rating": _posture_rating(posture_score),
        "retrieved_at": _now_iso(),
    }


# ── Router factory (thin wrappers only) ───────────────────────────────────────

def create_trust_center_router(ctx: TrustCenterContext) -> APIRouter:
    router = APIRouter(prefix="/trust-center", tags=["Trust Center"])

    @router.post("/policies", status_code=201)
    def record_policy_change(body: PolicyChangeRequest, auth: AuthDep) -> dict[str, Any]:
        return _handle_record_policy(ctx, body, auth)

    @router.get("/policies")
    def list_policies(auth: AuthDep) -> dict[str, Any]:
        return _handle_list_policies(ctx, auth)

    @router.post("/approval-chains", status_code=201)
    def create_approval_chain(body: ApprovalChainRequest, auth: AuthDep) -> dict[str, Any]:
        return _handle_create_chain(ctx, body, auth)

    @router.get("/approval-chains")
    def list_approval_chains(auth: AuthDep) -> dict[str, Any]:
        return _handle_list_chains(ctx, auth)

    @router.delete("/approval-chains/{chain_id}", status_code=200, responses={404: {"description": "Approval chain not found"}})
    def deactivate_approval_chain(chain_id: str, auth: AuthDep) -> dict[str, Any]:
        return _handle_deactivate_chain(ctx, chain_id, auth)

    @router.post("/incidents", status_code=201)
    def create_incident(body: IncidentRequest, auth: AuthDep) -> dict[str, Any]:
        return _handle_create_incident(ctx, body, auth)

    @router.patch("/incidents/{incident_id}/resolve", status_code=200, responses={404: {"description": "Incident not found"}})
    def resolve_incident(incident_id: str, body: dict[str, Any], auth: AuthDep) -> dict[str, Any]:
        return _handle_resolve_incident(ctx, incident_id, body, auth)

    @router.get("/incidents")
    def list_incidents(auth: AuthDep) -> dict[str, Any]:
        return _handle_list_incidents(ctx, auth)

    @router.post("/snapshots", status_code=201)
    def capture_snapshot(body: GovernanceSnapshotRequest, auth: AuthDep) -> dict[str, Any]:
        return _handle_capture_snapshot(ctx, body, auth)

    @router.get("/posture")
    def get_posture(auth: AuthDep) -> dict[str, Any]:
        return _handle_get_posture(ctx, auth)

    return router
