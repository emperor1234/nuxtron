"""Marketing/Ads use cases: ads health."""

from __future__ import annotations
from ..constants import AuthDep
from ..runtime import ContextRuntime
from ..services.now_iso import _now_iso
from .append_notification import helper_tenant_campaigns
from .append_notification import helper_tenant_connectors
from datetime import UTC
from datetime import datetime
from datetime import timedelta


async def execute_ads_health(runtime: ContextRuntime, auth: AuthDep):
    connectors = helper_tenant_connectors(runtime, auth.tenant_id)
    campaigns = helper_tenant_campaigns(runtime, auth.tenant_id)
    connected = sum((1 for item in connectors if bool(item.get("connected"))))
    overdue = [
        item
        for item in campaigns
        if str(item.get("status")) == "active"
        and datetime.fromisoformat(str(item.get("updated_at", _now_iso())).replace("Z", "+00:00"))
        < datetime.now(UTC) - timedelta(days=2)
    ]
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "connectors_total": len(connectors),
        "connectors_connected": connected,
        "campaigns_total": len(campaigns),
        "campaigns_overdue_sync": len(overdue),
        "scheduler_jobs_total": len([item for item in runtime._scheduler if item.get("tenant_id") == auth.tenant_id]),
        "forecast_runs_total": len([item for item in runtime._forecasts if item.get("tenant_id") == auth.tenant_id]),
    }
