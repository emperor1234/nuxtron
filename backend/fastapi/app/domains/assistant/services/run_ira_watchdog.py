"""Assistant service: run ira watchdog."""

from .reasoning_support import _activate_watchdog_protection
from .reasoning_support import _watchdog_activation_reason
from .reasoning_support import compute_tenant_revenue_snapshot
from .reasoning_support import compute_tenant_suspicious_signal
from typing import Any
import asyncio
import os


async def run_ira_watchdog(
    stop_event: asyncio.Event,
    *,
    ira_controls_memory: list[dict[str, Any]],
    ira_events_memory: list[dict[str, Any]],
    audit_log_memory: list[dict[str, Any]],
    invoices_memory: list[dict[str, Any]],
    credit_ledger_memory: list[dict[str, Any]],
    stripe_events_memory: list[dict[str, Any]],
    revenue_conversions_memory: list[dict[str, Any]],
    api_usage_audit_memory: list[dict[str, Any]],
    ai_security_usage_memory: list[dict[str, Any]],
) -> None:
    interval = max(10, int(os.getenv("IRA_WATCHDOG_INTERVAL_SECONDS", "60")))
    while not stop_event.is_set():
        for control in ira_controls_memory:
            tenant_id = str(control.get("tenant_id", "")).strip()
            if not tenant_id or not bool(control.get("autonomy_enabled", True)):
                continue
            snapshot = compute_tenant_revenue_snapshot(
                tenant_id=tenant_id, invoices_memory=invoices_memory, credit_ledger_memory=credit_ledger_memory
            )
            suspicious_signal = compute_tenant_suspicious_signal(
                tenant_id=tenant_id,
                stripe_events_memory=stripe_events_memory,
                revenue_conversions_memory=revenue_conversions_memory,
                api_usage_audit_memory=api_usage_audit_memory,
                ai_security_usage_memory=ai_security_usage_memory,
            )
            reason = _watchdog_activation_reason(control, snapshot, suspicious_signal)
            if reason is not None and (not bool(control.get("protection_mode", False))):
                _activate_watchdog_protection(
                    tenant_id=tenant_id,
                    control=control,
                    snapshot=snapshot,
                    suspicious_signal=suspicious_signal,
                    reason=reason,
                    ira_events_memory=ira_events_memory,
                    audit_log_memory=audit_log_memory,
                )
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=interval)
        except TimeoutError:
            continue
