# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnknownParameterType=false, reportUnusedFunction=false

"""
Outcome Attribution — Flywheel Module 1.
DB-first (psycopg3) with in-memory fallback when Postgres unavailable.
"""

import json
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Annotated, Any

import psycopg
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..deps import AuthContext, require_auth

AuthDep = Annotated[AuthContext, Depends(require_auth)]

_QUALITY_BANDS: tuple[tuple[float, str], ...] = (
    (90.0, "excellent"),
    (75.0, "good"),
    (55.0, "fair"),
    (0.0,  "poor"),
)


@dataclass(frozen=True)
class OutcomeAttributionContext:
    enforce_rate_limit: Any
    actions_memory: list[dict[str, Any]]
    outcomes_memory: list[dict[str, Any]]
    quality_scores_memory: list[dict[str, Any]]
    audit_log_memory: list[dict[str, Any]]
    get_db_ready: Callable[[], bool] = field(default=lambda: False)
    db_dsn: Callable[[], str] = field(default=lambda: "")


class RecordActionRequest(BaseModel):
    action_type: str = Field(min_length=1, max_length=120)
    target: str = Field(min_length=1, max_length=255)
    command: str = Field(min_length=1, max_length=500)
    actor_role: str = Field(default="ira_autonomous", max_length=80)
    channel: str = Field(default="ira", max_length=80)
    payload: dict[str, Any] = Field(default_factory=dict)
    dry_run: bool = False


class RecordOutcomeRequest(BaseModel):
    action_id: str = Field(min_length=1, max_length=80)
    outcome_type: str = Field(min_length=1, max_length=80)
    revenue_impact_gbp: float = Field(default=0.0)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    notes: str = Field(default="", max_length=1000)


class DecisionQualityRequest(BaseModel):
    action_id: str = Field(min_length=1, max_length=80)
    accuracy: float = Field(ge=0.0, le=100.0)
    safety: float = Field(ge=0.0, le=100.0)
    speed_ms: int = Field(ge=0)
    revenue_impact_gbp: float = Field(default=0.0)
    human_override: bool = False
    override_reason: str = Field(default="", max_length=500)


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _quality_band(score: float) -> str:
    for threshold, label in _QUALITY_BANDS:
        if score >= threshold:
            return label
    return "poor"


def compute_decision_quality_score(
    *,
    accuracy: float,
    safety: float,
    speed_ms: int,
    revenue_impact_gbp: float,
    human_override: bool,
) -> float:
    speed_score = max(0.0, 100.0 - (speed_ms / 1000.0) * 2.0)
    revenue_bonus = min(10.0, max(-10.0, revenue_impact_gbp / 500.0))
    override_penalty = -20.0 if human_override else 0.0
    raw = (accuracy * 0.40) + (safety * 0.35) + (speed_score * 0.15) + revenue_bonus + override_penalty
    return round(max(0.0, min(100.0, raw)), 2)


def _row_to_action(r: Any) -> dict[str, Any]:
    return {
        "id": str(r[0]), "tenant_id": str(r[1]), "action_type": str(r[2]),
        "target": str(r[3]), "command": str(r[4]), "actor_role": str(r[5]),
        "channel": str(r[6]), "payload": r[7] or {}, "dry_run": bool(r[8]),
        "outcome_type": r[9], "quality_score": float(r[10]) if r[10] is not None else None,
        "created_at": r[11].isoformat() if hasattr(r[11], "isoformat") else str(r[11]),
    }


def _row_to_quality(r: Any) -> dict[str, Any]:
    return {
        "id": str(r[0]), "tenant_id": str(r[1]), "action_id": str(r[2]),
        "accuracy": float(r[3] or 0), "safety": float(r[4] or 0),
        "speed_ms": int(r[5] or 0), "revenue_impact_gbp": float(r[6] or 0),
        "human_override": bool(r[7]), "override_reason": str(r[8] or ""),
        "score": float(r[9] or 0), "band": str(r[10] or "poor"),
        "created_at": r[11].isoformat() if hasattr(r[11], "isoformat") else str(r[11]),
    }


def _find_action_db(db_dsn: Callable[[], str], action_id: str, tenant_id: str) -> bool:
    with psycopg.connect(db_dsn()) as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT 1 FROM outcome_actions WHERE id = %s AND tenant_id = %s",
            (action_id, tenant_id),
        )
        return cur.fetchone() is not None


def _action_exists(ctx: OutcomeAttributionContext, action_id: str, tenant_id: str) -> bool:
    if ctx.get_db_ready():
        try:
            return _find_action_db(ctx.db_dsn, action_id, tenant_id)
        except Exception:
            pass
    return any(
        a.get("id") == action_id and a.get("tenant_id") == tenant_id
        for a in ctx.actions_memory
    )


# ── Route handler helpers ─────────────────────────────────────────────────────

def _handle_record_action(ctx: OutcomeAttributionContext, body: RecordActionRequest, auth: AuthContext) -> dict[str, Any]:
    ctx.enforce_rate_limit(f'{auth.tenant_id}:outcome:record-action', 120, 60)
    action_id = str(uuid.uuid4())
    record: dict[str, Any] = {
        "id": action_id, "tenant_id": auth.tenant_id,
        "action_type": body.action_type, "target": body.target,
        "command": body.command, "actor_role": body.actor_role,
        "channel": body.channel, "payload": body.payload,
        "dry_run": body.dry_run, "outcome_type": None,
        "quality_score": None, "created_at": _now_iso(),
    }
    if ctx.get_db_ready():
        try:
            with psycopg.connect(ctx.db_dsn()) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO outcome_actions
                            (id,tenant_id,action_type,target,command,actor_role,channel,payload,dry_run,created_at)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s,%s)
                        ON CONFLICT (id) DO NOTHING
                        """,
                        (action_id, auth.tenant_id, body.action_type, body.target,
                         body.command, body.actor_role, body.channel,
                         json.dumps(body.payload), body.dry_run, record["created_at"]),
                    )
                conn.commit()
        except Exception:
            ctx.actions_memory.append(record)
    else:
        ctx.actions_memory.append(record)
    ctx.audit_log_memory.append({
        "id": str(uuid.uuid4()), "tenant_id": auth.tenant_id,
        "event": "outcome.action_recorded", "action_id": action_id, "created_at": _now_iso(),
    })
    return {"action_id": action_id, "status": "recorded"}


def _handle_record_outcome(ctx: OutcomeAttributionContext, body: RecordOutcomeRequest, auth: AuthContext) -> dict[str, Any]:
    ctx.enforce_rate_limit(f'{auth.tenant_id}:outcome:record-outcome', 120, 60)
    if not _action_exists(ctx, body.action_id, auth.tenant_id):
        raise HTTPException(status_code=404, detail="Action not found")
    outcome_id = str(uuid.uuid4())
    rec: dict[str, Any] = {
        "id": outcome_id, "tenant_id": auth.tenant_id,
        "action_id": body.action_id, "outcome_type": body.outcome_type,
        "revenue_impact_gbp": body.revenue_impact_gbp,
        "confidence": body.confidence, "notes": body.notes, "created_at": _now_iso(),
    }
    if ctx.get_db_ready():
        try:
            with psycopg.connect(ctx.db_dsn()) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO outcome_outcomes
                            (id,tenant_id,action_id,outcome_type,revenue_impact_gbp,confidence,notes,created_at)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (id) DO NOTHING
                        """,
                        (outcome_id, auth.tenant_id, body.action_id, body.outcome_type,
                         body.revenue_impact_gbp, body.confidence, body.notes, rec["created_at"]),
                    )
                    cur.execute(
                        "UPDATE outcome_actions SET outcome_type=%s WHERE id=%s",
                        (body.outcome_type, body.action_id),
                    )
                conn.commit()
        except Exception:
            ctx.outcomes_memory.append(rec)
    else:
        ctx.outcomes_memory.append(rec)
    ctx.audit_log_memory.append({
        "id": str(uuid.uuid4()), "tenant_id": auth.tenant_id,
        "event": "outcome.outcome_recorded", "action_id": body.action_id, "created_at": _now_iso(),
    })
    return {"outcome_id": outcome_id, "status": "recorded"}


def _handle_submit_quality(ctx: OutcomeAttributionContext, body: DecisionQualityRequest, auth: AuthContext) -> dict[str, Any]:
    ctx.enforce_rate_limit(f'{auth.tenant_id}:outcome:submit-quality', 120, 60)
    if not _action_exists(ctx, body.action_id, auth.tenant_id):
        raise HTTPException(status_code=404, detail="Action not found")
    score = compute_decision_quality_score(
        accuracy=body.accuracy, safety=body.safety, speed_ms=body.speed_ms,
        revenue_impact_gbp=body.revenue_impact_gbp, human_override=body.human_override,
    )
    band = _quality_band(score)
    quality_id = str(uuid.uuid4())
    qrec: dict[str, Any] = {
        "id": quality_id, "tenant_id": auth.tenant_id, "action_id": body.action_id,
        "accuracy": body.accuracy, "safety": body.safety, "speed_ms": body.speed_ms,
        "revenue_impact_gbp": body.revenue_impact_gbp, "human_override": body.human_override,
        "override_reason": body.override_reason, "score": score, "band": band,
        "created_at": _now_iso(),
    }
    if ctx.get_db_ready():
        try:
            with psycopg.connect(ctx.db_dsn()) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO outcome_quality_scores
                            (id,tenant_id,action_id,accuracy,safety,speed_ms,
                             revenue_impact_gbp,human_override,override_reason,score,band,created_at)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (id) DO NOTHING
                        """,
                        (quality_id, auth.tenant_id, body.action_id,
                         body.accuracy, body.safety, body.speed_ms,
                         body.revenue_impact_gbp, body.human_override,
                         body.override_reason, score, band, qrec["created_at"]),
                    )
                    cur.execute(
                        "UPDATE outcome_actions SET quality_score=%s WHERE id=%s",
                        (score, body.action_id),
                    )
                conn.commit()
        except Exception:
            ctx.quality_scores_memory.append(qrec)
    else:
        ctx.quality_scores_memory.append(qrec)
    ctx.audit_log_memory.append({
        "id": str(uuid.uuid4()), "tenant_id": auth.tenant_id,
        "event": "outcome.quality_scored", "score": score, "created_at": _now_iso(),
    })
    return {"quality_id": quality_id, "score": score, "band": band, "status": "recorded"}


def _handle_get_outcome_graph(ctx: OutcomeAttributionContext, auth: AuthContext) -> dict[str, Any]:
    ctx.enforce_rate_limit(f'{auth.tenant_id}:outcome:graph', 240, 60)
    actions: list[dict[str, Any]] = []
    if ctx.get_db_ready():
        try:
            with psycopg.connect(ctx.db_dsn()) as conn, conn.cursor() as cur:
                cur.execute(
                    """
                        SELECT id,tenant_id,action_type,target,command,actor_role,channel,
                               payload,dry_run,outcome_type,quality_score,created_at
                        FROM outcome_actions WHERE tenant_id=%s ORDER BY created_at DESC LIMIT 500
                        """,
                    (auth.tenant_id,),
                )
                actions = [_row_to_action(r) for r in cur.fetchall()]
        except Exception:
            actions = [a for a in ctx.actions_memory if a.get("tenant_id") == auth.tenant_id]
    else:
        actions = [a for a in ctx.actions_memory if a.get("tenant_id") == auth.tenant_id]
    total = len(actions)
    attributed = sum(1 for a in actions if a.get("outcome_type"))
    distribution: dict[str, int] = {}
    for a in actions:
        ot = str(a.get("outcome_type") or "pending")
        distribution[ot] = distribution.get(ot, 0) + 1
    return {
        "tenant_id": auth.tenant_id, "total_actions": total,
        "attributed_actions": attributed,
        "attribution_rate_pct": round((attributed / total * 100) if total else 0.0, 1),
        "outcome_distribution": distribution,
        "retrieved_at": _now_iso(),
    }


def _handle_list_quality(ctx: OutcomeAttributionContext, auth: AuthContext) -> dict[str, Any]:
    ctx.enforce_rate_limit(f'{auth.tenant_id}:outcome:list-quality', 240, 60)
    scores: list[dict[str, Any]] = []
    if ctx.get_db_ready():
        try:
            with psycopg.connect(ctx.db_dsn()) as conn, conn.cursor() as cur:
                cur.execute(
                    """
                        SELECT id,tenant_id,action_id,accuracy,safety,speed_ms,
                               revenue_impact_gbp,human_override,override_reason,score,band,created_at
                        FROM outcome_quality_scores WHERE tenant_id=%s ORDER BY created_at DESC LIMIT 200
                        """,
                    (auth.tenant_id,),
                )
                scores = [_row_to_quality(r) for r in cur.fetchall()]
        except Exception:
            scores = [q for q in ctx.quality_scores_memory if q.get("tenant_id") == auth.tenant_id]
    else:
        scores = [q for q in ctx.quality_scores_memory if q.get("tenant_id") == auth.tenant_id]
    band_dist: dict[str, int] = {}
    avg_score = round(sum(float(q.get("score", 0) or 0) for q in scores) / len(scores), 2) if scores else 0.0
    for q in scores:
        b = str(q.get("band", "poor"))
        band_dist[b] = band_dist.get(b, 0) + 1
    return {
        "tenant_id": auth.tenant_id, "scores": scores[:100], "total": len(scores),
        "avg_score": avg_score, "band_distribution": band_dist, "retrieved_at": _now_iso(),
    }


def _handle_list_pending(ctx: OutcomeAttributionContext, auth: AuthContext) -> dict[str, Any]:
    ctx.enforce_rate_limit(f'{auth.tenant_id}:outcome:pending-actions', 240, 60)
    pending: list[dict[str, Any]] = []
    if ctx.get_db_ready():
        try:
            with psycopg.connect(ctx.db_dsn()) as conn, conn.cursor() as cur:
                cur.execute(
                    """
                        SELECT id,action_type,target,created_at
                        FROM outcome_actions
                        WHERE tenant_id=%s AND outcome_type IS NULL
                        ORDER BY created_at DESC LIMIT 100
                        """,
                    (auth.tenant_id,),
                )
                pending = [
                    {"id": str(r[0]), "action_type": str(r[1]), "target": str(r[2]),
                     "created_at": r[3].isoformat() if hasattr(r[3], "isoformat") else str(r[3])}
                    for r in cur.fetchall()
                ]
        except Exception:
            pending = [
                a for a in ctx.actions_memory
                if a.get("tenant_id") == auth.tenant_id and a.get("outcome_type") is None
            ]
    else:
        pending = [
            a for a in ctx.actions_memory
            if a.get("tenant_id") == auth.tenant_id and a.get("outcome_type") is None
        ]
    return {"tenant_id": auth.tenant_id, "pending": pending, "total": len(pending)}


# ── Router factory (thin wrappers only) ───────────────────────────────────────

def create_outcome_attribution_router(ctx: OutcomeAttributionContext) -> APIRouter:
    router = APIRouter(prefix="/outcome", tags=["Outcome Attribution"])

    @router.post("/actions", status_code=201)
    def record_action(body: RecordActionRequest, auth: AuthDep) -> dict[str, Any]:
        return _handle_record_action(ctx, body, auth)

    @router.post("/outcomes", status_code=201, responses={404: {"description": "Action not found"}})
    def record_outcome(body: RecordOutcomeRequest, auth: AuthDep) -> dict[str, Any]:
        return _handle_record_outcome(ctx, body, auth)

    @router.post("/quality", status_code=201, responses={404: {"description": "Action not found"}})
    def submit_quality(body: DecisionQualityRequest, auth: AuthDep) -> dict[str, Any]:
        return _handle_submit_quality(ctx, body, auth)

    @router.get("/graph")
    def get_outcome_graph(auth: AuthDep) -> dict[str, Any]:
        return _handle_get_outcome_graph(ctx, auth)

    @router.get("/quality")
    def list_quality_scores(auth: AuthDep) -> dict[str, Any]:
        return _handle_list_quality(ctx, auth)

    @router.get("/actions/pending")
    def list_pending_actions(auth: AuthDep) -> dict[str, Any]:
        return _handle_list_pending(ctx, auth)

    return router
