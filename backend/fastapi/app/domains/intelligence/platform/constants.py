"""Intelligence/Platform constants and configuration vocabulary."""

from __future__ import annotations
from .... import memory_stores
from ....deps import AuthContext
from ....deps import require_auth
from collections import defaultdict
from fastapi import Depends
from typing import Annotated
from typing import Any
import time

AuthDep = Annotated[AuthContext, Depends(require_auth)]

_prompt_versions = memory_stores.platform_prompt_versions

_lineage_events = memory_stores.platform_lineage_events

_recovery_queue = memory_stores.platform_recovery_queue

_retry_counts: dict[str, int] = defaultdict(int)

_PLATFORM_START_TS = time.time()

_DEFAULT_AGENT_TOOLS: list[dict[str, Any]] = [
    {
        "key": "run_site_audit",
        "display_name": "Run Site Audit",
        "group_name": "SEO Tools",
        "fn_signature": "run_site_audit(site_id)",
        "risk_level": "low",
        "requires_confirmation": False,
        "is_active": True,
        "backend_endpoint": "/seo-platform/technical/audit",
    },
    {
        "key": "generate_blog_post",
        "display_name": "Generate Blog Post",
        "group_name": "SEO Tools",
        "fn_signature": "generate_blog_post(site_id, topic)",
        "risk_level": "low",
        "requires_confirmation": False,
        "is_active": True,
        "backend_endpoint": "/seo-platform/content/write",
    },
    {
        "key": "optimize_page",
        "display_name": "Optimize Page",
        "group_name": "SEO Tools",
        "fn_signature": "optimize_page(url_id)",
        "risk_level": "medium",
        "requires_confirmation": False,
        "is_active": True,
        "backend_endpoint": "/seo-platform/on-page/analyze",
    },
    {
        "key": "create_internal_links",
        "display_name": "Create Internal Links",
        "group_name": "SEO Tools",
        "fn_signature": "create_internal_links(site_id, src, tgts)",
        "risk_level": "medium",
        "requires_confirmation": False,
        "is_active": True,
        "backend_endpoint": "/seo-platform/internal-linking/suggest",
    },
    {
        "key": "create_project",
        "display_name": "Create Project",
        "group_name": "Platform Tools",
        "fn_signature": "create_project(client_id, name)",
        "risk_level": "medium",
        "requires_confirmation": False,
        "is_active": True,
        "backend_endpoint": "/crm/projects",
    },
    {
        "key": "add_domain",
        "display_name": "Add Domain",
        "group_name": "Platform Tools",
        "fn_signature": "add_domain(client_id, domain)",
        "risk_level": "medium",
        "requires_confirmation": False,
        "is_active": True,
        "backend_endpoint": "/platform/domains",
    },
    {
        "key": "trigger_migration",
        "display_name": "Trigger Migration",
        "group_name": "Platform Tools",
        "fn_signature": "trigger_migration(site_id)",
        "risk_level": "high",
        "requires_confirmation": True,
        "is_active": True,
        "backend_endpoint": "/seo-platform/site-migration/analyze",
    },
    {
        "key": "run_lighthouse_audit",
        "display_name": "Lighthouse Audit",
        "group_name": "Platform Tools",
        "fn_signature": "run_lighthouse_audit(url_id)",
        "risk_level": "low",
        "requires_confirmation": False,
        "is_active": True,
        "backend_endpoint": "/seo-platform/performance/audit",
    },
    {
        "key": "create_brief",
        "display_name": "Create Content Brief",
        "group_name": "Content Tools",
        "fn_signature": "create_brief(keyword)",
        "risk_level": "low",
        "requires_confirmation": False,
        "is_active": True,
        "backend_endpoint": "/seo-platform/content/brief",
    },
    {
        "key": "rewrite_paragraph",
        "display_name": "Rewrite Paragraph",
        "group_name": "Content Tools",
        "fn_signature": "rewrite_paragraph(page_id, block_id)",
        "risk_level": "medium",
        "requires_confirmation": False,
        "is_active": True,
        "backend_endpoint": "/seo-platform/brand-voice/rewrite",
    },
]

_agent_sessions = memory_stores.platform_agent_sessions

_agent_tool_calls = memory_stores.platform_agent_tool_calls

_agent_config: dict[str, Any] = {
    "current_phase": "phase1",
    "enabled_models": ["deepseek-r1:8b", "llama3:8b"],
    "enabled_agent_roles": ["planner", "executor", "critic", "supervisor"],
    "tool_count_limit": 10,
    "max_auto_actions": 0,
    "allow_high_risk_tools": False,
    "mcp_endpoint": None,
}
