# pyright: reportUnusedFunction=false
"""
Live Editor — Alli AI visual in-place SEO editor parity.

Allows users to propose, review, approve, and publish SEO changes to live
pages directly from the dashboard without touching source code. Changes are
delivered to the page via an injected JS snippet (same mechanism as the AI
Crawler Enablement snippet).

Features
--------
  • Editing sessions per page URL
  • Change proposals: target CSS selector + field (title / meta / h1 / content / schema)
  • Multi-user approval workflow (propose → review → approve/reject → publish)
  • Bulk publish: publish all approved changes in a session
  • Version history per element / per page
  • Rollback: revert any published change to the previous version
  • Per-site snippet to receive and apply changes client-side
  • Preview API: return page HTML with proposed changes simulated

Endpoints
---------
POST   /live-editor/sessions                                     – Start a new editing session
GET    /live-editor/sessions                                     – List sessions
GET    /live-editor/sessions/{session_id}                        – Get session detail
DELETE /live-editor/sessions/{session_id}                        – Abandon a session

POST   /live-editor/sessions/{session_id}/changes               – Propose a change
GET    /live-editor/sessions/{session_id}/changes               – List pending changes
DELETE /live-editor/sessions/{session_id}/changes/{change_id}   – Remove a proposed change

POST   /live-editor/sessions/{session_id}/changes/{change_id}/approve – Approve a change
POST   /live-editor/sessions/{session_id}/changes/{change_id}/reject  – Reject a change

POST   /live-editor/sessions/{session_id}/preview               – Preview session (returns diff)
POST   /live-editor/sessions/{session_id}/publish               – Publish all approved changes

GET    /live-editor/history                                      – Published change history
POST   /live-editor/history/{change_id}/rollback                – Rollback a published change

GET    /live-editor/snippet                                      – Get the live-editor JS snippet
GET    /live-editor/snippet/payload/{site_key}                   – Snippet payload endpoint (pub)
"""

from __future__ import annotations

import hashlib
import threading
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from ..deps import AuthContext, require_auth

AuthDep = Annotated[AuthContext, Depends(require_auth)]

# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

ChangeField = Literal[
    "title",            # <title> tag
    "meta_description", # <meta name="description">
    "h1",               # First <h1> element
    "h2",               # First <h2> element matching selector
    "body_text",        # Inner text of matched element
    "inner_html",       # Inner HTML of matched element
    "attribute",        # Any HTML attribute
    "schema_json_ld",   # Inject/update <script type="application/ld+json">
    "og_title",         # <meta property="og:title">
    "og_description",   # <meta property="og:description">
    "canonical",        # <link rel="canonical">
    "hreflang",         # <link rel="alternate" hreflang="…">
    "css_class",        # Toggle / add / remove a CSS class
    "custom_element",   # Free-form target
]


class SessionCreateRequest(BaseModel):
    page_url: str = Field(min_length=10, max_length=2048)
    site_key: str | None = Field(default=None, max_length=80, description="Optional site key for snippet integration")
    session_name: str | None = Field(default=None, max_length=120)
    notes: str | None = Field(default=None, max_length=500)


class ChangeProposalRequest(BaseModel):
    field: ChangeField
    css_selector: str | None = Field(
        default=None,
        max_length=500,
        description="CSS selector identifying the target element. Optional for title/meta/canonical.",
    )
    attribute_name: str | None = Field(
        default=None,
        max_length=80,
        description="HTML attribute name for 'attribute' field type.",
    )
    current_value: str | None = Field(default=None, max_length=5000, description="Current (before) value for audit trail")
    proposed_value: str = Field(min_length=0, max_length=10000, description="New value to apply")
    reason: str | None = Field(default=None, max_length=500, description="Why this change is needed")
    priority: Literal["critical", "high", "medium", "low"] = "medium"


class ApprovalRequest(BaseModel):
    note: str | None = Field(default=None, max_length=500)


class PublishRequest(BaseModel):
    approved_only: bool = Field(default=True, description="Only publish changes with 'approved' status")
    note: str | None = Field(default=None, max_length=500)


class PreviewRequest(BaseModel):
    include_rejected: bool = False


class RollbackRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=500)


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def create_live_editor_router(
    *,
    enforce_rate_limit: Callable[[str, int, int], None],
    sessions_memory: list[dict[str, Any]],
    changes_memory: list[dict[str, Any]],
    history_memory: list[dict[str, Any]],
    audit_log_memory: list[dict[str, Any]],
) -> APIRouter:
    router = APIRouter(prefix="/live-editor", tags=["Live Editor"])
    _lock = threading.Lock()

    # ── helpers ──────────────────────────────────────────────────────────────

    def _now_iso() -> str:
        return datetime.now(UTC).isoformat()

    def _audit(tenant_id: str, action: str, detail: str = "") -> None:
        with _lock:
            audit_log_memory.append({
                "id": len(audit_log_memory) + 1,
                "tenant_id": tenant_id,
                "action": action,
                "detail": detail,
                "source": "live-editor",
                "created_at": _now_iso(),
            })

    def _get_session(tenant_id: str, session_id: str) -> dict[str, Any]:
        with _lock:
            sess = next(
                (s for s in sessions_memory if s["id"] == session_id and s["tenant_id"] == tenant_id),
                None,
            )
        if sess is None:
            raise HTTPException(status_code=404, detail="Editing session not found.")
        if sess.get("status") == "abandoned":
            raise HTTPException(status_code=410, detail="This editing session has been abandoned.")
        return sess

    def _get_change(tenant_id: str, session_id: str, change_id: str) -> dict[str, Any]:
        with _lock:
            change = next(
                (c for c in changes_memory
                 if c["id"] == change_id
                 and c["session_id"] == session_id
                 and c["tenant_id"] == tenant_id),
                None,
            )
        if change is None:
            raise HTTPException(status_code=404, detail="Change proposal not found.")
        return change

    def _session_changes(tenant_id: str, session_id: str) -> list[dict[str, Any]]:
        with _lock:
            return [
                c.copy() for c in changes_memory
                if c["session_id"] == session_id and c["tenant_id"] == tenant_id
            ]

    def _site_key_for_session(session: dict[str, Any]) -> str:
        """Derive a stable site key from the page URL for snippet delivery."""
        page_url = str(session.get("page_url", ""))
        return hashlib.sha256(f"{session['tenant_id']}:{page_url}".encode()).hexdigest()[:24]

    # ── Sessions ──────────────────────────────────────────────────────────────

    @router.post("/sessions", status_code=201)
    def create_session(payload: SessionCreateRequest, auth: AuthDep) -> dict[str, Any]:
        enforce_rate_limit(f"{auth.tenant_id}:live-editor:sessions:create", 60, 60)
        session_id = str(uuid.uuid4())
        now = _now_iso()
        session: dict[str, Any] = {
            "id": session_id,
            "tenant_id": auth.tenant_id,
            "page_url": payload.page_url,
            "site_key": payload.site_key or _site_key_for_session({"tenant_id": auth.tenant_id, "page_url": payload.page_url}),
            "session_name": payload.session_name or f"Edit session — {payload.page_url[:60]}",
            "notes": payload.notes or "",
            "status": "open",  # open | published | abandoned
            "changes_count": 0,
            "approved_count": 0,
            "published_count": 0,
            "created_at": now,
            "updated_at": now,
            "published_at": None,
        }
        with _lock:
            sessions_memory.append(session)
        _audit(auth.tenant_id, "session_created", payload.page_url[:120])
        return {"status": "ok", "session": session}

    @router.get("/sessions")
    def list_sessions(
        auth: AuthDep,
        status: str | None = Query(default=None),
        limit: int = Query(default=50, ge=1, le=500),
    ) -> dict[str, Any]:
        enforce_rate_limit(f"{auth.tenant_id}:live-editor:sessions:list", 120, 60)
        with _lock:
            all_sessions = [
                s.copy() for s in sessions_memory
                if s["tenant_id"] == auth.tenant_id
                and (not status or s.get("status") == status)
            ]
        return {"status": "ok", "count": len(all_sessions), "sessions": all_sessions[-limit:]}

    @router.get("/sessions/{session_id}")
    def get_session(session_id: str, auth: AuthDep) -> dict[str, Any]:
        enforce_rate_limit(f"{auth.tenant_id}:live-editor:sessions:get", 120, 60)
        sess = _get_session(auth.tenant_id, session_id)
        changes = _session_changes(auth.tenant_id, session_id)
        return {"status": "ok", "session": sess, "changes": changes}

    @router.delete("/sessions/{session_id}")
    def abandon_session(session_id: str, auth: AuthDep) -> dict[str, Any]:
        enforce_rate_limit(f"{auth.tenant_id}:live-editor:sessions:delete", 30, 60)
        with _lock:
            sess = next(
                (s for s in sessions_memory if s["id"] == session_id and s["tenant_id"] == auth.tenant_id),
                None,
            )
        if sess is None:
            raise HTTPException(status_code=404, detail="Editing session not found.")
        if sess.get("status") == "published":
            raise HTTPException(status_code=409, detail="Cannot abandon a published session. Use rollback instead.")
        sess["status"] = "abandoned"
        sess["updated_at"] = _now_iso()
        _audit(auth.tenant_id, "session_abandoned", session_id)
        return {"status": "ok", "session_id": session_id, "abandoned": True}

    # ── Change proposals ──────────────────────────────────────────────────────

    @router.post("/sessions/{session_id}/changes", status_code=201)
    def propose_change(session_id: str, payload: ChangeProposalRequest, auth: AuthDep) -> dict[str, Any]:
        enforce_rate_limit(f"{auth.tenant_id}:live-editor:changes:propose", 200, 60)
        sess = _get_session(auth.tenant_id, session_id)
        if sess["status"] != "open":
            raise HTTPException(status_code=409, detail="Session is not open for new changes.")

        change_id = str(uuid.uuid4())
        now = _now_iso()
        change: dict[str, Any] = {
            "id": change_id,
            "tenant_id": auth.tenant_id,
            "session_id": session_id,
            "page_url": sess["page_url"],
            "field": payload.field,
            "css_selector": payload.css_selector or "",
            "attribute_name": payload.attribute_name or "",
            "current_value": payload.current_value or "",
            "proposed_value": payload.proposed_value,
            "reason": payload.reason or "",
            "priority": payload.priority,
            "status": "pending",  # pending | approved | rejected | published | rolled_back
            "approved_by": None,
            "approval_note": None,
            "published_at": None,
            "created_at": now,
            "updated_at": now,
        }
        with _lock:
            changes_memory.append(change)
            # Update session counters
            for s in sessions_memory:
                if s["id"] == session_id:
                    s["changes_count"] = int(s.get("changes_count", 0)) + 1
                    s["updated_at"] = now

        return {"status": "ok", "change": change}

    @router.get("/sessions/{session_id}/changes")
    def list_changes(
        session_id: str,
        auth: AuthDep,
        status: str | None = Query(default=None),
    ) -> dict[str, Any]:
        enforce_rate_limit(f"{auth.tenant_id}:live-editor:changes:list", 120, 60)
        _get_session(auth.tenant_id, session_id)  # validate ownership
        with _lock:
            all_changes = [
                c.copy() for c in changes_memory
                if c["session_id"] == session_id
                and c["tenant_id"] == auth.tenant_id
                and (not status or c.get("status") == status)
            ]
        return {"status": "ok", "count": len(all_changes), "changes": all_changes}

    @router.delete("/sessions/{session_id}/changes/{change_id}")
    def remove_change(session_id: str, change_id: str, auth: AuthDep) -> dict[str, Any]:
        enforce_rate_limit(f"{auth.tenant_id}:live-editor:changes:delete", 60, 60)
        _get_session(auth.tenant_id, session_id)
        with _lock:
            before = len(changes_memory)
            changes_memory[:] = [
                c for c in changes_memory
                if not (c["id"] == change_id and c["session_id"] == session_id and c["tenant_id"] == auth.tenant_id)
            ]
        if len(changes_memory) == before:
            raise HTTPException(status_code=404, detail="Change proposal not found.")
        return {"status": "ok", "change_id": change_id, "removed": True}

    # ── Approval workflow ─────────────────────────────────────────────────────

    @router.post("/sessions/{session_id}/changes/{change_id}/approve")
    def approve_change(session_id: str, change_id: str, payload: ApprovalRequest, auth: AuthDep) -> dict[str, Any]:
        enforce_rate_limit(f"{auth.tenant_id}:live-editor:changes:approve", 120, 60)
        _get_session(auth.tenant_id, session_id)
        change = _get_change(auth.tenant_id, session_id, change_id)
        if change["status"] == "published":
            raise HTTPException(status_code=409, detail="Change is already published.")
        now = _now_iso()
        change.update({
            "status": "approved",
            "approved_by": auth.tenant_id,
            "approval_note": payload.note or "",
            "updated_at": now,
        })
        # Update session approved_count
        with _lock:
            for s in sessions_memory:
                if s["id"] == session_id:
                    approved_total = sum(
                        1 for c in changes_memory
                        if c["session_id"] == session_id and c.get("status") == "approved"
                    )
                    s["approved_count"] = approved_total
        return {"status": "ok", "change": change}

    @router.post("/sessions/{session_id}/changes/{change_id}/reject")
    def reject_change(session_id: str, change_id: str, payload: ApprovalRequest, auth: AuthDep) -> dict[str, Any]:
        enforce_rate_limit(f"{auth.tenant_id}:live-editor:changes:reject", 120, 60)
        _get_session(auth.tenant_id, session_id)
        change = _get_change(auth.tenant_id, session_id, change_id)
        if change["status"] == "published":
            raise HTTPException(status_code=409, detail="Cannot reject a published change.")
        change.update({
            "status": "rejected",
            "approval_note": payload.note or "",
            "updated_at": _now_iso(),
        })
        return {"status": "ok", "change": change}

    # ── Preview ───────────────────────────────────────────────────────────────

    @router.post("/sessions/{session_id}/preview")
    def preview_session(session_id: str, payload: PreviewRequest, auth: AuthDep) -> dict[str, Any]:
        enforce_rate_limit(f"{auth.tenant_id}:live-editor:preview", 60, 60)
        sess = _get_session(auth.tenant_id, session_id)
        statuses = {"pending", "approved"} | ({"rejected"} if payload.include_rejected else set())
        with _lock:
            pending_changes = [
                c.copy() for c in changes_memory
                if c["session_id"] == session_id
                and c["tenant_id"] == auth.tenant_id
                and c.get("status") in statuses
            ]

        diff: list[dict[str, Any]] = []
        for c in pending_changes:
            diff.append({
                "change_id": c["id"],
                "field": c["field"],
                "css_selector": c.get("css_selector", ""),
                "before": c.get("current_value", ""),
                "after": c["proposed_value"],
                "status": c["status"],
                "priority": c.get("priority", "medium"),
            })

        # Sort by priority
        priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        diff.sort(key=lambda x: priority_order.get(str(x.get("priority", "medium")), 2))

        return {
            "status": "ok",
            "session_id": session_id,
            "page_url": sess["page_url"],
            "pending_count": len([c for c in pending_changes if c["status"] == "pending"]),
            "approved_count": len([c for c in pending_changes if c["status"] == "approved"]),
            "diff": diff,
        }

    # ── Publish ───────────────────────────────────────────────────────────────

    @router.post("/sessions/{session_id}/publish")
    def publish_session(session_id: str, payload: PublishRequest, auth: AuthDep) -> dict[str, Any]:
        enforce_rate_limit(f"{auth.tenant_id}:live-editor:publish", 30, 60)
        _get_session(auth.tenant_id, session_id)
        now = _now_iso()
        target_statuses = {"approved"} if payload.approved_only else {"approved", "pending"}

        published: list[dict[str, Any]] = []
        with _lock:
            for c in changes_memory:
                if (c["session_id"] == session_id
                        and c["tenant_id"] == auth.tenant_id
                        and c.get("status") in target_statuses):
                    # Create history record
                    history_record: dict[str, Any] = {
                        "id": str(uuid.uuid4()),
                        "tenant_id": auth.tenant_id,
                        "session_id": session_id,
                        "change_id": c["id"],
                        "page_url": c["page_url"],
                        "field": c["field"],
                        "css_selector": c.get("css_selector", ""),
                        "value_before": c.get("current_value", ""),
                        "value_after": c["proposed_value"],
                        "published_by": auth.tenant_id,
                        "publish_note": payload.note or "",
                        "rolled_back": False,
                        "rolled_back_at": None,
                        "published_at": now,
                    }
                    history_memory.append(history_record)
                    if len(history_memory) > 20000:
                        del history_memory[:5000]

                    # Mark change as published
                    c["status"] = "published"
                    c["published_at"] = now
                    c["updated_at"] = now
                    published.append(c.copy())

            # Update session
            for s in sessions_memory:
                if s["id"] == session_id:
                    s["published_count"] = len(published)
                    s["published_at"] = now
                    s["status"] = "published"
                    s["updated_at"] = now

        _audit(auth.tenant_id, "session_published", f"session={session_id} changes={len(published)}")
        return {
            "status": "ok",
            "session_id": session_id,
            "published_count": len(published),
            "published_at": now,
            "changes": published,
        }

    # ── Change history & rollback ─────────────────────────────────────────────

    @router.get("/history")
    def get_history(
        auth: AuthDep,
        page_url: str | None = Query(default=None),
        field: str | None = Query(default=None),
        limit: int = Query(default=100, ge=1, le=1000),
    ) -> dict[str, Any]:
        enforce_rate_limit(f"{auth.tenant_id}:live-editor:history:list", 60, 60)
        with _lock:
            records = [
                h.copy() for h in history_memory
                if h["tenant_id"] == auth.tenant_id
                and (not page_url or h.get("page_url") == page_url)
                and (not field or h.get("field") == field)
            ]
        return {"status": "ok", "count": len(records), "history": records[-limit:]}

    @router.post("/history/{record_id}/rollback")
    def rollback_change(record_id: str, payload: RollbackRequest, auth: AuthDep) -> dict[str, Any]:
        enforce_rate_limit(f"{auth.tenant_id}:live-editor:rollback", 30, 60)
        now = _now_iso()
        with _lock:
            record = next(
                (h for h in history_memory if h["id"] == record_id and h["tenant_id"] == auth.tenant_id),
                None,
            )
        if record is None:
            raise HTTPException(status_code=404, detail="History record not found.")
        if record.get("rolled_back"):
            raise HTTPException(status_code=409, detail="This change has already been rolled back.")

        # Create a compensating history record (value_before ↔ value_after)
        rollback_record: dict[str, Any] = {
            "id": str(uuid.uuid4()),
            "tenant_id": auth.tenant_id,
            "session_id": record.get("session_id", ""),
            "change_id": record.get("change_id", ""),
            "page_url": record.get("page_url", ""),
            "field": record.get("field", ""),
            "css_selector": record.get("css_selector", ""),
            "value_before": record.get("value_after", ""),   # swapped
            "value_after": record.get("value_before", ""),   # swapped
            "published_by": auth.tenant_id,
            "publish_note": f"Rollback of {record_id}: {payload.reason or ''}",
            "rolled_back": False,
            "rolled_back_at": None,
            "is_rollback": True,
            "original_record_id": record_id,
            "published_at": now,
        }
        with _lock:
            record["rolled_back"] = True
            record["rolled_back_at"] = now
            history_memory.append(rollback_record)

        _audit(auth.tenant_id, "change_rolled_back", f"record={record_id}")
        return {"status": "ok", "rollback": rollback_record, "original_record_id": record_id}

    # ── Snippet delivery ──────────────────────────────────────────────────────

    @router.get("/snippet")
    def get_live_editor_snippet(auth: AuthDep, site_key: str | None = Query(default=None)) -> dict[str, Any]:
        enforce_rate_limit(f"{auth.tenant_id}:live-editor:snippet:get", 60, 60)
        cdn_base = "https://cdn.nuxtron.ai"
        key = site_key or hashlib.sha256(auth.tenant_id.encode()).hexdigest()[:24]
        snippet = f"""<!-- Nuxtron Live Editor Snippet -->
<script>
(function(w,d,s,k){{
  if(w.__NUXTRON_LE__)return;
  w.__NUXTRON_LE__=1;
  var t=d.createElement(s);t.async=1;
  t.src='{cdn_base}/live-editor.js?k='+k;
  d.head.appendChild(t);
}})(window,document,'script','{key}');
</script>"""
        return {"status": "ok", "site_key": key, "snippet": snippet}

    @router.get("/snippet/payload/{site_key}", include_in_schema=False)
    def snippet_payload(site_key: str, auth: AuthDep) -> dict[str, Any]:
        """
        Called by the live-editor.js snippet on page load.
        Returns published changes for the given site_key to apply client-side.
        """
        enforce_rate_limit(f"{auth.tenant_id}:live-editor:snippet:payload", 600, 60)
        with _lock:
            published = [
                {
                    "field": h["field"],
                    "css_selector": h.get("css_selector", ""),
                    "value": h["value_after"],
                }
                for h in history_memory
                if h["tenant_id"] == auth.tenant_id
                and not h.get("rolled_back")
                and h.get("published_at")
            ]
        return {"status": "ok", "site_key": site_key, "changes": published[-500:]}

    return router
