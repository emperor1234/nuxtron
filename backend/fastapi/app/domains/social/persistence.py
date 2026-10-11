from __future__ import annotations
import sys

"Social Workspace state and durable profile persistence boundary."
import json
import os
import threading
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Callable
import psycopg
from fastapi import HTTPException


@dataclass
class _SocialWorkspaceState:
    """Runtime state passed to social route registrations.

    The lists are development/test adapters. Production startup requires the
    durable database path before this state can serve business traffic.
    """

    enforce_rate_limit: Callable[[str, int, int], None]
    audit_log: list[dict[str, Any]] = field(default_factory=list)
    social_accounts: list[dict[str, Any]] = field(default_factory=list)
    brand_profiles: list[dict[str, Any]] = field(default_factory=list)
    inbox_messages: list[dict[str, Any]] = field(default_factory=list)
    competitor_profiles: list[dict[str, Any]] = field(default_factory=list)
    competitor_snapshots: list[dict[str, Any]] = field(default_factory=list)
    notifications: list[dict[str, Any]] = field(default_factory=list)
    scheduled_posts: list[dict[str, Any]] = field(default_factory=list)
    viralpost_history: list[dict[str, Any]] = field(default_factory=list)
    db_ready_fn: Callable[[], bool] = field(default_factory=lambda: lambda: False)
    db_dsn_fn: Callable[[], str] = field(default_factory=lambda: lambda: "")
    lock: threading.Lock = field(default_factory=threading.Lock)
    db_init_lock: threading.Lock = field(default_factory=threading.Lock)
    db_initialized: bool = False
    oauth_states: dict[str, dict[str, Any]] = field(default_factory=dict)
    reviews: list[dict[str, Any]] = field(default_factory=list)
    review_cases: list[dict[str, Any]] = field(default_factory=list)
    influencer_profiles: list[dict[str, Any]] = field(default_factory=list)
    influencer_shortlists: dict[str, list[str]] = field(default_factory=dict)
    advocacy_assets: list[dict[str, Any]] = field(default_factory=list)
    automation_rules: list[dict[str, Any]] = field(default_factory=list)
    saved_replies: list[dict[str, Any]] = field(default_factory=list)
    pause_all_state: dict[str, dict[str, Any]] = field(default_factory=dict)
    approval_requests: list[dict[str, Any]] = field(default_factory=list)
    short_links: list[dict[str, Any]] = field(default_factory=list)
    integration_webhooks: list[dict[str, Any]] = field(default_factory=list)
    integration_events: list[dict[str, Any]] = field(default_factory=list)
    canva_import_jobs: list[dict[str, Any]] = field(default_factory=list)
    extension_captures: list[dict[str, Any]] = field(default_factory=list)
    mobile_devices: list[dict[str, Any]] = field(default_factory=list)
    mobile_sync_batches: list[dict[str, Any]] = field(default_factory=list)
    listening_keywords: list[dict[str, Any]] = field(default_factory=list)
    listening_mentions: list[dict[str, Any]] = field(default_factory=list)
    monitoring_streams: list[dict[str, Any]] = field(default_factory=list)
    social_ad_campaigns: list[dict[str, Any]] = field(default_factory=list)
    social_ad_boosts: list[dict[str, Any]] = field(default_factory=list)
    reports: list[dict[str, Any]] = field(default_factory=list)
    bulk_schedule_jobs: list[dict[str, Any]] = field(default_factory=list)
    ugc_assets: list[dict[str, Any]] = field(default_factory=list)
    automation_feeds: list[dict[str, Any]] = field(default_factory=list)
    content_ideas: list[dict[str, Any]] = field(default_factory=list)
    hashtag_groups: list[dict[str, Any]] = field(default_factory=list)
    community_comments: list[dict[str, Any]] = field(default_factory=list)
    post_first_comments: dict[str, str] = field(default_factory=dict)
    post_threads: dict[str, list[str]] = field(default_factory=dict)
    posting_schedules: list[dict[str, Any]] = field(default_factory=list)
    content_templates: list[dict[str, Any]] = field(default_factory=list)
    team_members: list[dict[str, Any]] = field(default_factory=list)
    start_pages: list[dict[str, Any]] = field(default_factory=list)
    comment_reply_log: list[dict[str, Any]] = field(default_factory=list)
    ai_agent_runs: list[dict[str, Any]] = field(default_factory=list)


def _sw_db_enabled(st: _SocialWorkspaceState) -> bool:
    try:
        return bool(st.db_dsn_fn().strip()) and st.db_ready_fn()
    except Exception:
        return False


def _is_real_production_environment() -> bool:
    return os.getenv("ENVIRONMENT", "development").strip().lower() == "production" and (
        not (os.getenv("PYTEST_CURRENT_TEST") and "pytest" in sys.modules)
    )


def _production_persistence() -> bool:
    return os.getenv("ENVIRONMENT", "development").strip().lower() == "production"


def _persistence_failure(exc: Exception | None = None) -> None:
    raise HTTPException(status_code=503, detail="Social profile persistence unavailable.") from exc


def _sw_ensure_brand_profile_table(st: _SocialWorkspaceState) -> None:
    if not _sw_db_enabled(st):
        if _production_persistence():
            _persistence_failure()
        return
    if st.db_initialized:
        return
    with st.db_init_lock:
        if st.db_initialized:
            return
        if not _production_persistence():
            with psycopg.connect(st.db_dsn_fn()) as conn, conn.cursor() as cur:
                cur.execute(
                    "\n                    CREATE TABLE IF NOT EXISTS social_brand_profiles_store (\n                        tenant_id TEXT PRIMARY KEY,\n                        profile JSONB NOT NULL,\n                        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()\n                    )\n                "
                )
        st.db_initialized = True


def _sw_load_profile_from_db(st: _SocialWorkspaceState, tenant_id: str) -> dict[str, Any] | None:
    if not tenant_id.strip():
        raise ValueError("An organization is required for profile reads.")
    if not _sw_db_enabled(st):
        if _production_persistence():
            _persistence_failure()
        return None
    try:
        _sw_ensure_brand_profile_table(st)
        with psycopg.connect(st.db_dsn_fn()) as conn, conn.cursor() as cur:
            cur.execute("SELECT set_config('app.current_tenant_id', %s, true)", (tenant_id,))
            cur.execute("SELECT profile FROM social_brand_profiles_store WHERE tenant_id = %s", (tenant_id,))
            row = cur.fetchone()
        if not row:
            return None
        payload = json.loads(row[0]) if isinstance(row[0], str) else row[0]
        if not isinstance(payload, dict):
            _persistence_failure()
        if payload.get("tenant_id", tenant_id) != tenant_id:
            _persistence_failure()
        return {**payload, "tenant_id": tenant_id}
    except HTTPException:
        raise
    except Exception as exc:
        if _production_persistence():
            _persistence_failure(exc)
        return None


def _sw_save_profile_to_db(st: _SocialWorkspaceState, profile: dict[str, Any]) -> None:
    tenant_id = str(profile.get("tenant_id") or "").strip()
    if not tenant_id:
        raise ValueError("An organization is required for profile writes.")
    if not _sw_db_enabled(st):
        if _production_persistence():
            _persistence_failure()
        return
    try:
        _sw_ensure_brand_profile_table(st)
        with psycopg.connect(st.db_dsn_fn()) as conn, conn.cursor() as cur:
            cur.execute("SELECT set_config('app.current_tenant_id', %s, true)", (tenant_id,))
            cur.execute(
                "\n                INSERT INTO social_brand_profiles_store (tenant_id, profile, updated_at)\n                VALUES (%s, %s::jsonb, NOW())\n                ON CONFLICT (tenant_id)\n                DO UPDATE SET profile = EXCLUDED.profile, updated_at = NOW()\n            ",
                (tenant_id, json.dumps(profile)),
            )
    except HTTPException:
        raise
    except Exception as exc:
        if _production_persistence():
            _persistence_failure(exc)


def _sw_audit(st: _SocialWorkspaceState, tenant_id: str, action: str, ref_id: int | None = None) -> None:
    if _production_persistence():
        from ..identity.security_audit import record_security_event

        record_security_event(
            tenant_id=tenant_id,
            event_type=action,
            principal_id="social-system",
            auth_mode="internal",
            method="",
            path="/social",
            request_id="",
            client_ip="",
            user_agent="",
            metadata={"ref_id": ref_id, "source": "social-workspace-domain"},
        )
        return
    with st.lock:
        st.audit_log.append(
            {
                "id": len(st.audit_log) + 1,
                "tenant_id": tenant_id,
                "action": action,
                "ref_id": ref_id,
                "created_at": datetime.now(UTC).isoformat(),
                "source": "social-workspace-domain",
            }
        )


def _sw_get_account(st: _SocialWorkspaceState, tenant_id: str, account_id: int) -> dict[str, Any] | None:
    with st.lock:
        return next(
            (
                account
                for account in st.social_accounts
                if account.get("tenant_id") == tenant_id and account.get("id") == account_id
            ),
            None,
        )
