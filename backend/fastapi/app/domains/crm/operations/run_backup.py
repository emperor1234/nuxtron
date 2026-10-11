"""Crm use cases: run backup."""

from ..constants import AuthDep
from ..runtime import ContextRuntime
from .get_live_sync_state import helper_get_live_sync_state
from .task_to_dict import helper_audit
from .task_to_dict import helper_get_backup_config
from datetime import UTC
from datetime import datetime
from fastapi import Query
from typing import Annotated
from typing import Any
import hashlib


def execute_run_backup(
    runtime: ContextRuntime,
    auth: AuthDep,
    mode: Annotated[str, Query(pattern="^(incremental|full)$")] = "incremental",
    source: Annotated[str, Query(max_length=80)] = "manual",
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:crm:ops:backup:run", 30, 60)
    now = datetime.now(UTC)
    with runtime.lock:
        helper_get_backup_config(runtime, auth.tenant_id)
        tenant_contacts = [c for c in runtime.contacts_memory if c.get("tenant_id") == auth.tenant_id]
        tenant_companies = [c for c in runtime.companies_memory if c.get("tenant_id") == auth.tenant_id]
        tenant_deals = [d for d in runtime.deals_memory if d.get("tenant_id") == auth.tenant_id]
        tenant_tickets = [t for t in runtime.tickets_memory if t.get("tenant_id") == auth.tenant_id]
        counts = {
            "contacts": len(tenant_contacts),
            "companies": len(tenant_companies),
            "deals": len(tenant_deals),
            "tickets": len(tenant_tickets),
        }
        digest_seed = f"{auth.tenant_id}:{mode}:{counts['contacts']}:{counts['companies']}:{counts['deals']}:{counts['tickets']}:{now.isoformat()}"
        snapshot = {
            "id": len(runtime.backup_snapshots_memory) + 1,
            "tenant_id": auth.tenant_id,
            "type": "snapshot",
            "mode": mode,
            "source": source,
            "started_at": now.isoformat(),
            "completed_at": now.isoformat(),
            "status": "completed",
            "checksum": hashlib.sha256(digest_seed.encode("utf-8")).hexdigest()[:24],
            "entity_counts": counts,
        }
        runtime.backup_snapshots_memory.append(snapshot)
    snapshot_id = snapshot.get("id")
    helper_audit(runtime, auth.tenant_id, "crm_backup_run", snapshot_id if isinstance(snapshot_id, int) else None)
    return {"status": "ok", "tenant_id": auth.tenant_id, "backup": snapshot}


def execute_run_live_sync(runtime: ContextRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:crm:ops:sync:run", 60, 60)
    now_iso = datetime.now(UTC).isoformat()
    with runtime.lock:
        state = helper_get_live_sync_state(runtime, auth.tenant_id)
        state["last_sync_at"] = now_iso
        state["last_success_at"] = now_iso
        state["lag_seconds"] = 0
        state["events_processed_24h"] = int(state.get("events_processed_24h", 0)) + 125
        state["conflict_queue"] = 0
        state["updated_at"] = now_iso
        snapshot = state.copy()
    helper_audit(runtime, auth.tenant_id, "crm_live_sync_ran", int(snapshot.get("id", 0)))
    return {"status": "ok", "tenant_id": auth.tenant_id, "sync": snapshot}
