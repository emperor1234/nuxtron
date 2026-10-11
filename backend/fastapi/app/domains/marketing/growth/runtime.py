"""Marketing/Growth explicit runtime dependencies."""

from __future__ import annotations
from dataclasses import dataclass
from typing import Any


@dataclass
class ContextRuntime:
    """Adapters and state owned by exactly one application instance."""

    analytics_reports_memory: Any
    chatbot_leads_memory: Any
    chatbots_memory: Any
    crm_contacts_memory: Any
    crm_deals_memory: Any
    db_dsn_fn: Any
    db_init_lock: Any
    db_initialized: Any
    db_ready_fn: Any
    email_campaigns_memory: Any
    enforce_rate_limit: Any
    growth_suite_memory: Any
    linkinbio_links_memory: Any
    linkinbio_pages_memory: Any
    lock: Any
    revenue_conversions_memory: Any
    revenue_touchpoints_memory: Any
    scheduled_posts_memory: Any
