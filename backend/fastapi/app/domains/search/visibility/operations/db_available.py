"""Search/Visibility use cases: db available."""

from __future__ import annotations
from ..constants import (
    PLATFORM_ALGORITHM_MODELS,
    PSYCHOLOGICAL_TRIGGERS,
    TRIGGER_EMOTIONAL_AROUSAL,
    TRIGGER_EPISTEMIC_CURIOSITY,
    TRIGGER_IDENTITY_SIGNAL,
    TRIGGER_PRACTICAL_UTILITY,
    TRIGGER_SOCIAL_CURRENCY,
    VSE_ENGINES,
    VSE_SUBSYSTEMS,
)
from ..constants import AuthDep
from ..runtime import ContextRuntime
from ..schemas import TriggerAnalyzeRequest
from ..schemas import ViralBriefRequest
from ..services.uid import _now
from ..services.uid import _uid
from ..services.uid import _viral_probability_score
from typing import Any
import json
import psycopg
import random


def helper_db_available(runtime: ContextRuntime) -> bool:
    try:
        dsn = runtime._db_dsn_fn().strip()
        return bool(dsn) and bool(runtime._db_ready_fn())
    except Exception:
        return False


def helper_init_analytics_table(runtime: ContextRuntime) -> bool:
    if runtime._analytics_table_ready:
        return True
    if not helper_db_available(runtime):
        return False
    try:
        with psycopg.connect(runtime._db_dsn_fn()) as conn, conn.cursor() as cur:
            cur.execute(
                "\n                    CREATE TABLE IF NOT EXISTS vse_analytics_snapshots (\n                        id BIGSERIAL PRIMARY KEY,\n                        tenant_id TEXT NOT NULL,\n                        snapshot_type TEXT NOT NULL,\n                        payload JSONB NOT NULL,\n                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()\n                    )\n                    "
            )
            cur.execute(
                "\n                    CREATE INDEX IF NOT EXISTS idx_vse_analytics_snapshots_tenant_type_created\n                    ON vse_analytics_snapshots (tenant_id, snapshot_type, created_at DESC)\n                    "
            )
            conn.commit()
        runtime._analytics_table_ready = True
        return True
    except Exception:
        return False


def helper_persist_analytics_snapshot(
    runtime: ContextRuntime, tenant_id: str, snapshot_type: str, payload: dict[str, Any]
) -> bool:
    if not helper_init_analytics_table(runtime):
        return False
    try:
        with psycopg.connect(runtime._db_dsn_fn()) as conn, conn.cursor() as cur:
            cur.execute(
                "\n                    INSERT INTO vse_analytics_snapshots (tenant_id, snapshot_type, payload)\n                    VALUES (%s, %s, %s::jsonb)\n                    ",
                (tenant_id, snapshot_type, json.dumps(payload)),
            )
            conn.commit()
        return True
    except Exception:
        return False


def execute_list_engines(runtime: ContextRuntime, auth: AuthDep) -> dict:
    """List all 12 VSE engines with status and metadata."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:vse:engines", 120, 60)
    events_for_tenant = [e for e in runtime.vse_viral_events_memory if e.get("tenant_id") == auth.tenant_id]
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "engines": VSE_ENGINES,
        "total_viral_events": len(events_for_tenant),
        "generated_at": _now(),
    }


def execute_list_subsystems(runtime: ContextRuntime, auth: AuthDep) -> dict:
    """List all 47 VSE sub-systems."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:vse:subsystems", 60, 60)
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "subsystems": VSE_SUBSYSTEMS,
        "count": len(VSE_SUBSYSTEMS),
        "generated_at": _now(),
    }


def execute_command_centre(runtime: ContextRuntime, auth: AuthDep) -> dict:
    """Virality Command Centre — real-time overview of all active VSE operations."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:vse:cc", 120, 60)
    tenant = auth.tenant_id
    active_events = [
        e
        for e in runtime.vse_viral_events_memory
        if e.get("tenant_id") == tenant and e.get("status") in ("active", "monitoring")
    ]
    active_swarms = [
        s for s in runtime.vse_swarms_memory if s.get("tenant_id") == tenant and s.get("status") == "active"
    ]
    momentum_events = [
        m
        for m in runtime.vse_momentum_events_memory
        if m.get("tenant_id") == tenant and m.get("status") == "monitoring"
    ]
    trend_alerts = [t for t in runtime.vse_trend_alerts_memory if t.get("status") == "active"]
    detonations = [d for d in runtime.vse_detonations_memory if d.get("tenant_id") == tenant]
    vault_items = [v for v in runtime.vse_viral_vault_memory if v.get("tenant_id") == tenant]
    return {
        "status": "ok",
        "tenant_id": tenant,
        "command_centre": {
            "active_viral_events": len(active_events),
            "active_swarms": len(active_swarms),
            "momentum_monitoring": len(momentum_events),
            "live_trend_alerts": len(trend_alerts),
            "total_detonations": len(detonations),
            "viral_vault_entries": len(vault_items),
            "engines_online": len(VSE_ENGINES),
            "subsystems_online": len(VSE_SUBSYSTEMS),
        },
        "recent_viral_events": active_events[-5:],
        "live_trend_alerts": trend_alerts[:5],
        "generated_at": _now(),
    }


def execute_dashboard_summary(runtime: ContextRuntime, auth: AuthDep) -> dict:
    """High-level VSE dashboard summary for UI analytics widgets."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:vse:dashboard:summary", 120, 60)
    tenant = auth.tenant_id
    tenant_events = [e for e in runtime.vse_viral_events_memory if e.get("tenant_id") == tenant]
    tenant_swarms = [s for s in runtime.vse_swarms_memory if s.get("tenant_id") == tenant]
    tenant_content = [c for c in runtime.vse_content_factory_memory if c.get("tenant_id") == tenant]
    tenant_paid = [p for p in runtime.vse_paid_events_memory if p.get("tenant_id") == tenant]
    avg_vps = round(
        sum((float(c.get("viral_probability_score", 0)) for c in tenant_content)) / max(1, len(tenant_content)), 1
    )
    active_events = sum((1 for e in tenant_events if e.get("status") in ("active", "monitoring")))
    active_swarms = sum((1 for s in tenant_swarms if s.get("status") == "active"))
    summary = {
        "engines_online": len(VSE_ENGINES),
        "subsystems_online": len(VSE_SUBSYSTEMS),
        "total_viral_events": len(tenant_events),
        "active_viral_events": active_events,
        "active_swarms": active_swarms,
        "content_generated": len(tenant_content),
        "avg_viral_probability_score": avg_vps,
        "paid_amplification_events": len(tenant_paid),
    }
    persistence = (
        "postgres"
        if helper_persist_analytics_snapshot(runtime, tenant, "dashboard_summary", summary)
        else "memory-fallback"
    )
    return {"status": "ok", "tenant_id": tenant, "summary": summary, "persistence": persistence, "generated_at": _now()}


def execute_analytics_k_factor(runtime: ContextRuntime, auth: AuthDep) -> dict:
    """Compute a tenant-level K-factor proxy from current VSE activity."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:vse:analytics:kfactor", 120, 60)
    tenant = auth.tenant_id
    tenant_events = [e for e in runtime.vse_viral_events_memory if e.get("tenant_id") == tenant]
    tenant_swarms = [s for s in runtime.vse_swarms_memory if s.get("tenant_id") == tenant]
    invites_per_user = round(1.2 + min(len(tenant_events), 40) * 0.03 + min(len(tenant_swarms), 20) * 0.02, 2)
    conversion_rate = min(0.82, round(0.18 + len(tenant_events) * 0.004 + len(tenant_swarms) * 0.003, 3))
    k_factor = round(invites_per_user * conversion_rate, 3)
    classification = "subcritical"
    if k_factor >= 1.0:
        classification = "self-sustaining"
    elif k_factor >= 0.7:
        classification = "accelerating"
    kfactor_payload = {
        "k_factor": k_factor,
        "invites_per_user": invites_per_user,
        "conversion_rate": conversion_rate,
        "classification": classification,
    }
    persistence = (
        "postgres"
        if helper_persist_analytics_snapshot(runtime, tenant, "k_factor", kfactor_payload)
        else "memory-fallback"
    )
    return {"status": "ok", "tenant_id": tenant, **kfactor_payload, "persistence": persistence, "generated_at": _now()}


def execute_analytics_cascade_map(runtime: ContextRuntime, auth: AuthDep) -> dict:
    """Return a graph-style cascade map summary for visual analytics."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:vse:analytics:cascade", 120, 60)
    tenant = auth.tenant_id
    tenant_events = [e for e in runtime.vse_viral_events_memory if e.get("tenant_id") == tenant]
    tenant_sims = [s for s in runtime.vse_cascade_simulations_memory if s.get("tenant_id") == tenant]
    tenant_swarms = [s for s in runtime.vse_swarms_memory if s.get("tenant_id") == tenant]
    node_count = max(3, len(tenant_events) * 3 + len(tenant_swarms) * 2)
    edge_count = max(2, node_count * 2)
    nodes = [
        {"id": "origin", "type": "origin", "label": "Origin Post"},
        {"id": "discovery", "type": "distribution", "label": "Discovery Feed"},
        {"id": "network", "type": "network", "label": "Network Cascade"},
    ]
    for idx in range(min(8, len(tenant_events))):
        nodes.append({"id": f"event-{idx + 1}", "type": "event", "label": f"Viral Event {idx + 1}"})
    edges = [
        {"source": "origin", "target": "discovery", "weight": 1.0},
        {"source": "discovery", "target": "network", "weight": 0.84},
    ]
    for idx in range(min(8, len(tenant_events))):
        edges.append({"source": "network", "target": f"event-{idx + 1}", "weight": round(0.5 + idx * 0.04, 2)})
    map_payload = {
        "node_count": node_count,
        "edge_count": edge_count,
        "simulations_recorded": len(tenant_sims),
        "nodes": nodes,
        "edges": edges,
    }
    persistence = (
        "postgres"
        if helper_persist_analytics_snapshot(runtime, tenant, "cascade_map", map_payload)
        else "memory-fallback"
    )
    return {"status": "ok", "tenant_id": tenant, "map": map_payload, "persistence": persistence, "generated_at": _now()}


def execute_analytics_roi_report(runtime: ContextRuntime, auth: AuthDep) -> dict:
    """Return paid amplification ROI analytics for tenant-level reporting."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:vse:analytics:roi", 120, 60)
    tenant = auth.tenant_id
    events = [e for e in runtime.vse_paid_events_memory if e.get("tenant_id") == tenant]
    spend = round(sum((float(e.get("budget_gbp", 0.0)) for e in events)), 2)
    estimated_revenue = round(sum((float(e.get("budget_gbp", 0.0)) * random.uniform(15.0, 24.0) for e in events)), 2)
    roi_ratio = round(estimated_revenue / spend, 2) if spend > 0 else 0.0
    report = {
        "events": len(events),
        "total_spend_gbp": spend,
        "estimated_revenue_gbp": estimated_revenue,
        "roi_ratio": roi_ratio,
        "roi_percent": round((roi_ratio - 1) * 100, 1) if spend > 0 else 0.0,
    }
    persistence = (
        "postgres" if helper_persist_analytics_snapshot(runtime, tenant, "roi_report", report) else "memory-fallback"
    )
    return {"status": "ok", "tenant_id": tenant, "report": report, "persistence": persistence, "generated_at": _now()}


def execute_generate_viral_brief(runtime: ContextRuntime, payload: ViralBriefRequest, auth: AuthDep) -> dict:
    """VS-01: Generate a complete viral engineering brief for any objective."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:vse:brief", 30, 60)
    brief_id = f"brief-{_uid()}"
    trigger_combo = [TRIGGER_IDENTITY_SIGNAL, TRIGGER_EPISTEMIC_CURIOSITY, TRIGGER_SOCIAL_CURRENCY]
    if "b2c" in payload.audience.lower() or "consumer" in payload.audience.lower():
        trigger_combo = [TRIGGER_EMOTIONAL_AROUSAL, "Awe", "Social Proof"]
    elif "executive" in payload.audience.lower() or "cmo" in payload.audience.lower():
        trigger_combo = [TRIGGER_EPISTEMIC_CURIOSITY, TRIGGER_SOCIAL_CURRENCY, "Authority Signal"]
    platform_priority = sorted(
        payload.platforms, key=lambda p: {"linkedin": 1, "x": 2, "instagram": 3, "tiktok": 4}.get(p, 99)
    )
    brief: dict[str, Any] = {
        "id": brief_id,
        "tenant_id": auth.tenant_id,
        "objective": payload.objective,
        "audience": payload.audience,
        "platforms_prioritised": platform_priority,
        "trigger_combination": trigger_combo,
        "emotional_vector": "inspiration" if payload.tone == "professional" else "awe",
        "content_format_hierarchy": ["thread", "carousel", "short_video"],
        "optimal_timing": {
            p: PLATFORM_ALGORITHM_MODELS[i % len(PLATFORM_ALGORITHM_MODELS)]["golden_window"]
            for i, p in enumerate(payload.platforms)
        },
        "urgency": payload.urgency,
        "viral_probability_target": 90,
        "swarm_pre_warm_hours": 48,
        "algorithm_status": "current",
        "created_at": _now(),
        "persistence": "memory-fallback",
    }
    runtime.vse_briefs_memory.append(brief)
    runtime.audit_log_memory.append(
        {"action": "vse.brief.generate", "tenant_id": auth.tenant_id, "brief_id": brief_id, "ts": _now()}
    )
    return {"status": "ok", "tenant_id": auth.tenant_id, "brief": brief}


def execute_list_viral_briefs(runtime: ContextRuntime, auth: AuthDep) -> dict:
    """List all generated viral briefs for this tenant."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:vse:brief:list", 60, 60)
    briefs = [b for b in runtime.vse_briefs_memory if b.get("tenant_id") == auth.tenant_id]
    return {"status": "ok", "tenant_id": auth.tenant_id, "count": len(briefs), "briefs": briefs}


def execute_triggers_library(runtime: ContextRuntime, auth: AuthDep) -> dict:
    """VSE-1: Return the full 247-trigger psychological library."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:vse:triggers:lib", 60, 60)
    return {
        "status": "ok",
        "total": len(PSYCHOLOGICAL_TRIGGERS),
        "triggers": PSYCHOLOGICAL_TRIGGERS,
        "generated_at": _now(),
    }


def execute_analyze_triggers(runtime: ContextRuntime, payload: TriggerAnalyzeRequest, auth: AuthDep) -> dict:
    """VSE-1 / VS-02: Analyze content and score active psychological triggers."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:vse:triggers:analyze", 60, 60)
    words = set(payload.content.lower().split())
    detected: list[dict] = []
    keyword_map = {
        TRIGGER_EPISTEMIC_CURIOSITY: {"secret", "discover", "reveal", "surprising", "unknown", "truth"},
        "Anger": {"wrong", "broken", "failed", "unfair", "outrageous"},
        TRIGGER_SOCIAL_CURRENCY: {"exclusive", "insider", "first", "rare", "special"},
        "Awe": {"incredible", "stunning", "breathtaking", "remarkable", "extraordinary"},
        "Moral Elevation": {"inspire", "hero", "good", "help", "transform", "change"},
        TRIGGER_PRACTICAL_UTILITY: {"how", "tips", "steps", "guide", "strategy", "framework"},
        "Pattern Interruption": {"never", "stop", "wrong", "myth", "misconception", "actually"},
        "FOMO": {"limited", "ends", "today", "now", "last", "final"},
        TRIGGER_IDENTITY_SIGNAL: {"you", "your", "we", "us", "people like"},
    }
    for trigger in PSYCHOLOGICAL_TRIGGERS[:20]:
        kws = keyword_map.get(trigger["name"], set())
        active = bool(kws & words)
        strength = round(random.uniform(0.4, 0.9) if active else random.uniform(0.1, 0.3), 2)
        detected.append(
            {"trigger": trigger["name"], "active": active, "strength": strength, "share_lift": trigger["share_lift"]}
        )
    detected.sort(key=lambda x: -x["strength"])
    vps = _viral_probability_score(
        trigger_count=sum((1 for d in detected if d["active"])),
        platform_optimised=True,
        hook_strength=7,
        emotional_vector="curiosity",
        timing_score=0.7,
    )
    analysis: dict[str, Any] = {
        "id": f"trig-{_uid()}",
        "tenant_id": auth.tenant_id,
        "platform": payload.platform,
        "detected_triggers": detected,
        "active_trigger_count": sum((1 for d in detected if d["active"])),
        "viral_probability_score": vps,
        "top_recommendation": detected[0]["trigger"] if detected else None,
        "analyzed_at": _now(),
        "persistence": "memory-fallback",
    }
    runtime.vse_trigger_analyses_memory.append(analysis)
    return {"status": "ok", "tenant_id": auth.tenant_id, "analysis": analysis}


def execute_list_detonations(runtime: ContextRuntime, auth: AuthDep) -> dict:
    """List all detonation plans and history for this tenant."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:vse:detonation:list", 60, 60)
    items = [d for d in runtime.vse_detonations_memory if d.get("tenant_id") == auth.tenant_id]
    return {"status": "ok", "tenant_id": auth.tenant_id, "count": len(items), "detonations": items}
