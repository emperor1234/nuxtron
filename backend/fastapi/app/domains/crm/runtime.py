"""Crm explicit runtime dependencies."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass
class ContextRuntime:
    """Adapters and state owned by exactly one application instance."""

    activities_memory: list[dict[str, Any]]
    api_tokens_memory: list[dict[str, Any]]
    audit_log_memory: list[dict[str, Any]]
    automation_recipes_memory: list[dict[str, Any]]
    backup_snapshots_memory: list[dict[str, Any]]
    campaigns_memory: list[dict[str, Any]]
    companies_memory: list[dict[str, Any]]
    contacts_memory: list[dict[str, Any]]
    crm_invoices_memory: list[dict[str, Any]]
    custom_entity_records_memory: list[dict[str, Any]]
    custom_entity_types_memory: list[dict[str, Any]]
    deals_memory: list[dict[str, Any]]
    email_sequences_memory: list[dict[str, Any]]
    enforce_rate_limit: Callable[[str, int, int], None]
    leads_memory: list[dict[str, Any]]
    live_sync_state_memory: list[dict[str, Any]]
    lock: Any
    notes_memory: list[dict[str, Any]]
    projects_memory: list[dict[str, Any]]
    quotes_memory: list[dict[str, Any]]
    segments_memory: list[dict[str, Any]]
    sla_rules_memory: list[dict[str, Any]]
    tasks_memory: list[dict[str, Any]]
    tickets_memory: list[dict[str, Any]]
    vendor_manager: Any
    webhook_subscriptions_memory: list[dict[str, Any]]
    weekday_map: Any
    workflow_rules_memory: list[dict[str, Any]]
