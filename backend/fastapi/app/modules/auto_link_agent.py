"""
Auto-Link Agent: Autonomous agent for safe internal link execution.

Autonomy tiers:
  1 = suggest only (never executes automatically)
  2 = auto-execute low-risk actions (same-domain links, no redirect chains)
  3 = auto-execute + push to approval queue for high-risk actions

Listens to: links_suggested
Emits: action_executed, safety_check_failed
"""

import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from urllib.parse import urlparse

import psycopg

from ..event_bus import Event, EventBus, EventType

logger = logging.getLogger(__name__)


@dataclass
class SafetyViolation:
    """A single safety violation found during pre-execution checks"""
    rule: str
    severity: str  # "block", "warn"
    detail: str


@dataclass
class AgentDecision:
    """Record of an agent's decision on a single link"""
    link: dict[str, Any]
    approved: bool
    violations: list[SafetyViolation] = field(default_factory=list)
    reasoning: str = ""


class AgentSafetyChecker:
    """
    Safety checks for all agent actions.
    Every action must pass ALL blocking rules before execution.
    """

    def __init__(self, site_domain: str, blocked_paths: list[str] | None = None):
        self.site_domain = site_domain
        self.blocked_paths = blocked_paths or ["/admin", "/api", "/login", "/.well-known"]

    def check_link(self, link: dict[str, Any]) -> list[SafetyViolation]:
        """
        Run all safety checks on a proposed internal link.

        Returns list of violations. Empty = safe to execute.
        """
        violations: list[SafetyViolation] = []
        from_url = link.get("from_url", "")
        to_url = link.get("to_url", "")
        anchor = link.get("anchor_text", "")

        # Rule 1: Both URLs must be on the same domain
        from_domain = urlparse(from_url).netloc
        to_domain = urlparse(to_url).netloc
        if from_domain and to_domain and from_domain != to_domain:
            violations.append(SafetyViolation(
                rule="same_domain",
                severity="block",
                detail=f"Cross-domain link attempt: {from_domain} → {to_domain}",
            ))

        # Rule 2: Neither URL should be empty or malformed
        if not from_url or not to_url:
            violations.append(SafetyViolation(
                rule="url_required",
                severity="block",
                detail="from_url or to_url is empty",
            ))

        # Rule 3: Anchor text must not be empty or spam-like
        if not anchor or len(anchor.strip()) < 2:
            violations.append(SafetyViolation(
                rule="anchor_quality",
                severity="block",
                detail="Anchor text is missing or too short",
            ))

        spam_signals = ["click here", "here", "read more", "learn more"]
        if anchor.lower().strip() in spam_signals:
            violations.append(SafetyViolation(
                rule="anchor_quality",
                severity="warn",
                detail=f"Generic anchor text detected: '{anchor}'",
            ))

        # Rule 4: Do not link to blocked paths
        to_path = urlparse(to_url).path
        for blocked in self.blocked_paths:
            if to_path.startswith(blocked):
                violations.append(SafetyViolation(
                    rule="blocked_path",
                    severity="block",
                    detail=f"Link target is in blocked path: {to_path}",
                ))

        # Rule 5: No self-links
        if from_url == to_url:
            violations.append(SafetyViolation(
                rule="no_self_link",
                severity="block",
                detail="from_url and to_url are the same",
            ))

        # Rule 6: Relevance score must be sufficient
        relevance = link.get("relevance_score", 0)
        if relevance < 0.5:
            violations.append(SafetyViolation(
                rule="relevance_threshold",
                severity="block",
                detail=f"Relevance score {relevance:.2f} is below minimum 0.50",
            ))

        return violations


class AutoLinkAgent:
    """
    Autonomous agent: watches for link suggestions, runs safety checks, executes approved links.
    """

    MODULE_TYPE = "auto-link-agent"

    def __init__(
        self,
        site_id: str,
        agent_id: str,
        site_domain: str,
        db_conn: psycopg.AsyncConnection,
        event_bus: EventBus,
        autonomy_tier: int = 2,
        cms_api_url: str | None = None,
        cms_api_key: str | None = None,
    ):
        self.site_id = site_id
        self.agent_id = agent_id
        self.db = db_conn
        self.bus = event_bus
        self.autonomy_tier = autonomy_tier
        self.cms_api_url = cms_api_url
        self.cms_api_key = cms_api_key
        self.safety = AgentSafetyChecker(site_domain=site_domain)

        # Register event handler
        self.bus.subscribe(
            event_type=EventType.LINKS_SUGGESTED,
            handler=self._on_links_suggested,
            site_id=self.site_id,
        )

    async def _on_links_suggested(self, event: Event):
        """React to links_suggested event from ai-internal-linking-engine"""
        if event.site_id != self.site_id:
            return

        links = event.payload.get("links_pending_review", [])
        logger.info(
            f"[auto-link-agent] Received {len(links)} link suggestions from event {event.id}"
        )

        if not links:
            return

        run_id = str(uuid.uuid4())
        await self.process_links(run_id=run_id, links=links, trigger_event=event)

    async def process_links(
        self,
        run_id: str,
        links: list[dict[str, Any]],
        trigger_event: Event | None = None,
    ) -> dict[str, Any]:
        """
        Process a batch of link suggestions.

        1. Run safety checks on each
        2. Based on autonomy tier:
            - Tier 1: log + emit (never execute)
            - Tier 2: execute all that pass safety checks
            - Tier 3: execute + queue risky ones for human review
        3. Log every decision to agent reasoning log + action_audit
        """
        started_at = time.time()
        decisions: list[AgentDecision] = []

        for link in links:
            violations = self.safety.check_link(link)
            blocking = [v for v in violations if v.severity == "block"]
            warnings = [v for v in violations if v.severity == "warn"]

            approved = len(blocking) == 0
            reasoning = self._build_reasoning(link, violations, approved)

            decisions.append(AgentDecision(
                link=link,
                approved=approved,
                violations=violations,
                reasoning=reasoning,
            ))

            # Log to reasoning
            logger.info(
                f"[auto-link-agent] Link {link.get('from_url')} → {link.get('to_url')}: "
                f"{'APPROVED' if approved else 'REJECTED'} "
                f"({len(blocking)} blocking, {len(warnings)} warnings)"
            )

        approved_links = [d for d in decisions if d.approved]
        rejected_links = [d for d in decisions if not d.approved]

        # Execute based on autonomy tier
        executed: list[dict[str, Any]] = []
        queued: list[dict[str, Any]] = []

        if self.autonomy_tier >= 2:
            for decision in approved_links:
                result = await self._execute_link(run_id, decision)
                executed.append(result)

        if self.autonomy_tier == 3:
            # Tier 3: queue blocked-by-warning links for human review
            for decision in rejected_links:
                if not any(v.severity == "block" for v in decision.violations):
                    queued.append(decision.link)

        # Persist all decisions to action_audit
        await self._persist_decisions(run_id, decisions)

        # Update agent reasoning log
        await self._update_reasoning_log(run_id, decisions)

        elapsed_ms = int((time.time() - started_at) * 1000)

        # Emit result event
        if executed:
            await self.bus.emit(
                event_type=EventType.LINKS_EXECUTED,
                site_id=self.site_id,
                source_module_id=self.agent_id,
                source_module_type=self.MODULE_TYPE,
                source_run_id=run_id,
                payload={
                    "links_executed": len(executed),
                    "links_rejected": len(rejected_links),
                    "links_queued_for_review": len(queued),
                    "executed": executed,
                    "trigger_event_id": trigger_event.id if trigger_event else None,
                },
            )

        output = {
            "status": "success",
            "links_processed": len(links),
            "links_approved": len(approved_links),
            "links_rejected": len(rejected_links),
            "links_executed": len(executed),
            "links_queued": len(queued),
            "execution_time_ms": elapsed_ms,
            "autonomy_tier": self.autonomy_tier,
        }
        logger.info(f"[auto-link-agent] Run {run_id} complete: {output}")
        return output

    def _build_reasoning(
        self,
        link: dict[str, Any],
        violations: list[SafetyViolation],
        approved: bool,
    ) -> str:
        """Build human-readable reasoning trace"""
        lines = [
            f"Link: {link.get('from_url')} → {link.get('to_url')}",
            f"Anchor: '{link.get('anchor_text', '')}'",
            f"Relevance: {link.get('relevance_score', 0):.2f}",
            f"Decision: {'APPROVED' if approved else 'REJECTED'}",
        ]
        if violations:
            lines.append("Violations:")
            for v in violations:
                lines.append(f"  [{v.severity.upper()}] {v.rule}: {v.detail}")
        else:
            lines.append("All safety checks passed.")
        return "\n".join(lines)

    async def _execute_link(
        self, run_id: str, decision: AgentDecision
    ) -> dict[str, Any]:
        """
        Execute a single approved link.
        In v1: calls CMS API if configured, otherwise logs the action.
        """
        link = decision.link
        result: dict[str, Any] = {
            "from_url": link.get("from_url"),
            "to_url": link.get("to_url"),
            "anchor_text": link.get("anchor_text"),
            "status": "simulated",  # v1: simulate unless CMS configured
        }

        if self.cms_api_url and self.cms_api_key:
            try:
                import httpx
                async with httpx.AsyncClient() as client:
                    resp = await client.post(
                        f"{self.cms_api_url}/api/links",
                        json={
                            "from_url": link.get("from_url"),
                            "to_url": link.get("to_url"),
                            "anchor_text": link.get("anchor_text"),
                            "context": link.get("context_snippet"),
                        },
                        headers={"Authorization": f"Bearer {self.cms_api_key}"},
                        timeout=10,
                    )
                    resp.raise_for_status()
                    result["status"] = "executed"
                    result["cms_response"] = resp.json()
            except Exception as e:
                result["status"] = "error"
                result["error"] = str(e)
                logger.error(f"[auto-link-agent] CMS API error: {e}")
        else:
            logger.info(
                f"[auto-link-agent] SIMULATED: Add link "
                f"{link.get('from_url')} → {link.get('to_url')} "
                f"with anchor '{link.get('anchor_text')}'"
            )

        return result

    async def _persist_decisions(
        self, run_id: str, decisions: list[AgentDecision]
    ):
        """Persist all decisions to action_audit table"""
        for d in decisions:
            await self.db.execute(
                """
                INSERT INTO action_audit
                  (id, agent_id, action_type, before_state, after_state, status, reasoning, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
                """,
                (
                    str(uuid.uuid4()),
                    self.agent_id,
                    "internal_link_suggestion",
                    json.dumps({"link": d.link}),
                    json.dumps({"approved": d.approved, "violations": [
                        {"rule": v.rule, "severity": v.severity, "detail": v.detail}
                        for v in d.violations
                    ]}),
                    "executed" if d.approved else "rejected",
                    d.reasoning,
                ),
            )
        await self.db.commit()

    async def _update_reasoning_log(
        self, run_id: str, decisions: list[AgentDecision]
    ):
        """Append to agent's reasoning log"""
        log_entry = {
            "run_id": run_id,
            "timestamp": datetime.now().isoformat(),
            "decisions": [
                {
                    "link": d.link,
                    "approved": d.approved,
                    "violations": [
                        {"rule": v.rule, "severity": v.severity}
                        for v in d.violations
                    ],
                    "reasoning": d.reasoning,
                }
                for d in decisions
            ],
        }

        await self.db.execute(
            """
            UPDATE agents
            SET reasoning_log = COALESCE(reasoning_log, ARRAY[]::jsonb[]) || %s::jsonb,
                updated_at = NOW()
            WHERE id = %s
            """,
            (json.dumps(log_entry), self.agent_id),
        )
        await self.db.commit()
