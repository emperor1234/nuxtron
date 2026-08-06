# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnknownParameterType=false, reportUnusedFunction=false

"""
Integration Playbooks — Flywheel Module 3.
10 built-in + custom tenant playbooks. DB-first with in-memory fallback.
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

_BUILTIN_PLAYBOOKS: list[dict[str, Any]] = [
    {"id": "pb-builtin-001", "name": "Welcome Email Sequence", "vertical": "all",
     "description": "Automated 5-touch onboarding sequence for new signups.", "built_in": True,
     "steps": ["Trigger on signup", "Send welcome email T+0", "Check engagement T+3", "Send tips T+7", "Send upgrade nudge T+14"],
     "integrations": ["email", "crm"], "roi_target": {"metric": "activation_rate_pct", "value": 35},
     "time_to_value_days": 1},
    {"id": "pb-builtin-002", "name": "Churn Rescue", "vertical": "saas",
     "description": "IRA detects disengagement signals and triggers save sequence.", "built_in": True,
     "steps": ["Monitor usage drop", "Score churn risk", "Send personalised save offer", "Log outcome"],
     "integrations": ["ira", "email", "crm"], "roi_target": {"metric": "churn_reduction_pct", "value": 30},
     "time_to_value_days": 3},
    {"id": "pb-builtin-003", "name": "Autonomous Dispute Resolution", "vertical": "ecommerce",
     "description": "Route disputes to IRA for instant resolution under policy threshold.", "built_in": True,
     "steps": ["Intake dispute", "IRA policy check", "Auto-resolve or escalate", "Notify customer", "Log to outcome graph"],
     "integrations": ["ira", "disputes", "crm"], "roi_target": {"metric": "dispute_auto_resolution_rate_pct", "value": 70},
     "time_to_value_days": 1},
    {"id": "pb-builtin-004", "name": "Full-Funnel Revenue Attribution", "vertical": "all",
     "description": "Tag every touchpoint with UTM and attribute revenue back to campaigns.", "built_in": True,
     "steps": ["Install UTM builder", "Tag all outbound links", "Capture conversion events", "Map to outcome graph", "Report in benchmarks"],
     "integrations": ["utm_builder", "outcome_attribution", "benchmarks"],
     "roi_target": {"metric": "attribution_coverage_pct", "value": 90}, "time_to_value_days": 2},
    {"id": "pb-builtin-005", "name": "Brand Reputation Alert", "vertical": "media",
     "description": "Monitor social mentions for brand risk and alert team instantly.", "built_in": True,
     "steps": ["Crawl mentions", "Score sentiment", "Alert on threshold breach", "Log to trust center"],
     "integrations": ["social_listening", "trust_center", "notifications"],
     "roi_target": {"metric": "response_time_minutes", "value": 5}, "time_to_value_days": 1},
    {"id": "pb-builtin-006", "name": "Influencer Pipeline", "vertical": "media",
     "description": "Discover, qualify and onboard influencers autonomously.", "built_in": True,
     "steps": ["Scan VSE network", "Score reach + alignment", "Send outreach via IRA", "Manage negotiation", "Onboard to platform"],
     "integrations": ["influencer", "ira", "crm"],
     "roi_target": {"metric": "outreach_conversion_pct", "value": 25}, "time_to_value_days": 7},
    {"id": "pb-builtin-007", "name": "AI Lead Qualification", "vertical": "saas",
     "description": "IRA qualifies inbound leads and routes hot leads to sales.", "built_in": True,
     "steps": ["Enrich lead data", "Score with IRA", "Route to CRM", "Trigger nurture sequence"],
     "integrations": ["ira", "crm", "email"],
     "roi_target": {"metric": "qualified_lead_rate_pct", "value": 40}, "time_to_value_days": 2},
    {"id": "pb-builtin-008", "name": "Content Performance Flywheel", "vertical": "media",
     "description": "Analyse what content works, generate variants, and measure uplift.", "built_in": True,
     "steps": ["Pull performance data", "Score content with VSE", "Generate high-signal variants", "Publish and track", "Feed benchmarks"],
     "integrations": ["viralpost", "benchmarks", "cms"],
     "roi_target": {"metric": "organic_reach_uplift_pct", "value": 50}, "time_to_value_days": 5},
    {"id": "pb-builtin-009", "name": "Trust Center Setup", "vertical": "all",
     "description": "Bootstrap governance: define policies, approval chains, and capture baseline posture.", "built_in": True,
     "steps": ["Record initial policies", "Create approval chains", "Capture posture snapshot", "Set up incident alerts"],
     "integrations": ["trust_center", "notifications"],
     "roi_target": {"metric": "avg_decision_quality_score", "value": 85}, "time_to_value_days": 1},
    {"id": "pb-builtin-010", "name": "Revenue Ops Flywheel", "vertical": "all",
     "description": "Connect all revenue signals — deals, disputes, subscriptions — to benchmarks.", "built_in": True,
     "steps": ["Wire billing events", "Wire dispute outcomes", "Map to outcome graph", "Submit to benchmarks", "Set quarterly targets"],
     "integrations": ["billing", "disputes", "outcome_attribution", "benchmarks"],
     "roi_target": {"metric": "net_revenue_retained_gbp", "value": 50000}, "time_to_value_days": 3},
]

_BUILTIN_IDS: frozenset[str] = frozenset(p["id"] for p in _BUILTIN_PLAYBOOKS)


@dataclass(frozen=True)
class PlaybooksContext:
    enforce_rate_limit: Any
    playbooks_memory: list[dict[str, Any]]
    playbook_runs_memory: list[dict[str, Any]]
    audit_log_memory: list[dict[str, Any]]
    get_db_ready: Callable[[], bool] = field(default=lambda: False)
    db_dsn: Callable[[], str] = field(default=lambda: "")


class CreatePlaybookRequest(BaseModel):
    name: str = Field(min_length=2, max_length=180)
    vertical: str = Field(default="all", max_length=80)
    description: str = Field(min_length=5, max_length=1000)
    steps: list[str] = Field(default_factory=list)
    integrations: list[str] = Field(default_factory=list)
    roi_metric: str = Field(default="activation_rate_pct", max_length=120)
    roi_target_value: float = Field(default=0.0)
    time_to_value_days: int = Field(default=1, ge=1, le=365)


class RunPlaybookRequest(BaseModel):
    playbook_id: str = Field(min_length=1, max_length=80)
    dry_run: bool = True
    config: dict[str, Any] = Field(default_factory=dict)


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _row_to_playbook(r: Any) -> dict[str, Any]:
    return {
        "id": str(r[0]), "tenant_id": str(r[1]), "name": str(r[2]),
        "vertical": str(r[3]), "description": str(r[4]),
        "steps": r[5] or [], "integrations": r[6] or [],
        "roi_target": r[7] or {}, "time_to_value_days": int(r[8] or 1),
        "built_in": bool(r[9]),
        "created_at": r[10].isoformat() if hasattr(r[10], "isoformat") else str(r[10]),
    }


def _find_playbook_in_db(ctx: PlaybooksContext, playbook_id: str, tenant_id: str) -> dict[str, Any] | None:
    with psycopg.connect(ctx.db_dsn()) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id,tenant_id,name,vertical,description,steps,integrations,roi_target,time_to_value_days,built_in,created_at FROM playbooks WHERE id=%s AND tenant_id=%s",
                (playbook_id, tenant_id),
            )
            r = cur.fetchone()
    return _row_to_playbook(r) if r else None


def _find_playbook(
    ctx: PlaybooksContext, playbook_id: str, tenant_id: str
) -> dict[str, Any] | None:
    for p in _BUILTIN_PLAYBOOKS:
        if p["id"] == playbook_id:
            return p
    if ctx.get_db_ready():
        try:
            return _find_playbook_in_db(ctx, playbook_id, tenant_id)
        except Exception:
            pass
    return next(
        (p for p in ctx.playbooks_memory if p.get("id") == playbook_id and p.get("tenant_id") == tenant_id),
        None,
    )


def _handle_list_playbooks(ctx: PlaybooksContext, auth: AuthContext) -> dict[str, Any]:
    ctx.enforce_rate_limit(f"{auth.tenant_id}:playbooks_list", 120, 60)
    custom: list[dict[str, Any]] = []
    if ctx.get_db_ready():
        try:
            with psycopg.connect(ctx.db_dsn()) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT id,tenant_id,name,vertical,description,steps,integrations,roi_target,time_to_value_days,built_in,created_at FROM playbooks WHERE tenant_id=%s ORDER BY created_at DESC",
                        (auth.tenant_id,),
                    )
                    rows = cur.fetchall()
            custom = [_row_to_playbook(r) for r in rows]
        except Exception:
            custom = [p for p in ctx.playbooks_memory if p.get("tenant_id") == auth.tenant_id]
    else:
        custom = [p for p in ctx.playbooks_memory if p.get("tenant_id") == auth.tenant_id]
    all_playbooks = [*_BUILTIN_PLAYBOOKS, *custom]
    return {"playbooks": all_playbooks, "total": len(all_playbooks), "built_in": len(_BUILTIN_PLAYBOOKS), "custom": len(custom)}


def _handle_get_playbook(ctx: PlaybooksContext, playbook_id: str, auth: AuthContext) -> dict[str, Any]:
    ctx.enforce_rate_limit(f"{auth.tenant_id}:playbooks_get", 120, 60)
    playbook = _find_playbook(ctx, playbook_id, auth.tenant_id)
    if playbook is None:
        raise HTTPException(status_code=404, detail="Playbook not found")
    return playbook


def _handle_create_playbook(ctx: PlaybooksContext, body: CreatePlaybookRequest, auth: AuthContext) -> dict[str, Any]:
    ctx.enforce_rate_limit(f"{auth.tenant_id}:playbooks_create", 120, 60)
    playbook_id = f"pb-custom-{uuid.uuid4().hex[:12]}"
    record: dict[str, Any] = {
        "id": playbook_id, "tenant_id": auth.tenant_id,
        "name": body.name, "vertical": body.vertical,
        "description": body.description, "steps": body.steps,
        "integrations": body.integrations,
        "roi_target": {"metric": body.roi_metric, "value": body.roi_target_value},
        "time_to_value_days": body.time_to_value_days,
        "built_in": False, "created_at": _now_iso(),
    }
    if ctx.get_db_ready():
        try:
            with psycopg.connect(ctx.db_dsn()) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO playbooks
                            (id,tenant_id,name,vertical,description,steps,integrations,roi_target,time_to_value_days,built_in,created_at)
                        VALUES (%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb,%s::jsonb,%s,%s,%s)
                        ON CONFLICT (id) DO NOTHING
                        """,
                        (playbook_id, auth.tenant_id, body.name, body.vertical,
                         body.description, json.dumps(body.steps),
                         json.dumps(body.integrations),
                         json.dumps({"metric": body.roi_metric, "value": body.roi_target_value}),
                         body.time_to_value_days, False, record["created_at"]),
                    )
                conn.commit()
        except Exception:
            ctx.playbooks_memory.append(record)
    else:
        ctx.playbooks_memory.append(record)
    return {"playbook_id": playbook_id, "status": "created"}


def _handle_run_playbook(ctx: PlaybooksContext, body: RunPlaybookRequest, auth: AuthContext) -> dict[str, Any]:
    ctx.enforce_rate_limit(f"{auth.tenant_id}:playbooks_run", 120, 60)
    playbook = _find_playbook(ctx, body.playbook_id, auth.tenant_id)
    if playbook is None:
        raise HTTPException(status_code=404, detail="Playbook not found")
    run_id = str(uuid.uuid4())
    run: dict[str, Any] = {
        "id": run_id, "tenant_id": auth.tenant_id,
        "playbook_id": body.playbook_id, "playbook_name": playbook.get("name"),
        "config": body.config, "dry_run": body.dry_run,
        "status": "dry_run_preview" if body.dry_run else "scheduled",
        "steps_total": len(list(playbook.get("steps", []))),
        "steps_completed": 0, "created_at": _now_iso(),
    }
    if ctx.get_db_ready():
        try:
            with psycopg.connect(ctx.db_dsn()) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO playbook_runs
                            (id,tenant_id,playbook_id,playbook_name,config,dry_run,status,steps_total,steps_completed,created_at)
                        VALUES (%s,%s,%s,%s,%s::jsonb,%s,%s,%s,%s,%s) ON CONFLICT (id) DO NOTHING
                        """,
                        (run_id, auth.tenant_id, body.playbook_id,
                         str(playbook.get("name", "")), json.dumps(body.config),
                         body.dry_run, run["status"],
                         run["steps_total"], 0, run["created_at"]),
                    )
                conn.commit()
        except Exception:
            ctx.playbook_runs_memory.append(run)
    else:
        ctx.playbook_runs_memory.append(run)
    ctx.audit_log_memory.append({
        "id": str(uuid.uuid4()), "tenant_id": auth.tenant_id,
        "event": "playbook.run_started", "run_id": run_id,
        "playbook_id": body.playbook_id, "created_at": _now_iso(),
    })
    return {"run_id": run_id, "status": run["status"], "steps_total": run["steps_total"]}


def _handle_list_runs(ctx: PlaybooksContext, auth: AuthContext) -> dict[str, Any]:
    ctx.enforce_rate_limit(f"{auth.tenant_id}:playbooks_list_runs", 120, 60)
    if ctx.get_db_ready():
        try:
            with psycopg.connect(ctx.db_dsn()) as conn, conn.cursor() as cur:
                cur.execute(
                    """
                        SELECT id,tenant_id,playbook_id,playbook_name,dry_run,status,
                               steps_total,steps_completed,created_at
                        FROM playbook_runs WHERE tenant_id=%s ORDER BY created_at DESC LIMIT 100
                        """,
                    (auth.tenant_id,),
                )
                rows = cur.fetchall()
            runs = [
                {"id": str(r[0]), "tenant_id": str(r[1]), "playbook_id": str(r[2]),
                 "playbook_name": str(r[3] or ""), "dry_run": bool(r[4]), "status": str(r[5]),
                 "steps_total": int(r[6] or 0), "steps_completed": int(r[7] or 0),
                 "created_at": r[8].isoformat() if hasattr(r[8], "isoformat") else str(r[8])}
                for r in rows
            ]
            return {"runs": runs, "total": len(runs)}
        except Exception:
            pass
    runs = [r for r in ctx.playbook_runs_memory if r.get("tenant_id") == auth.tenant_id]
    return {"runs": runs, "total": len(runs)}


# ── Router factory (thin wrappers only) ───────────────────────────────────────

def create_playbooks_router(ctx: PlaybooksContext) -> APIRouter:
    router = APIRouter(prefix="/playbooks", tags=["Integration Playbooks"])

    @router.get("")
    def list_playbooks(auth: AuthDep) -> dict[str, Any]:
        return _handle_list_playbooks(ctx, auth)

    @router.get("/{playbook_id}", responses={404: {"description": "Playbook not found"}})
    def get_playbook(playbook_id: str, auth: AuthDep) -> dict[str, Any]:
        return _handle_get_playbook(ctx, playbook_id, auth)

    @router.post("", status_code=201)
    def create_playbook(body: CreatePlaybookRequest, auth: AuthDep) -> dict[str, Any]:
        return _handle_create_playbook(ctx, body, auth)

    @router.post("/run", status_code=201, responses={404: {"description": "Playbook not found"}})
    def run_playbook(body: RunPlaybookRequest, auth: AuthDep) -> dict[str, Any]:
        return _handle_run_playbook(ctx, body, auth)

    @router.get("/runs/list")
    def list_runs(auth: AuthDep) -> dict[str, Any]:
        return _handle_list_runs(ctx, auth)

    return router

