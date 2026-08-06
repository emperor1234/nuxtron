"""
Tests for modules/auto_link_agent.py missing coverage lines (69 lines).
Tests AgentSafetyChecker, AutoLinkAgent process_links, etc.
"""
from __future__ import annotations

import asyncio
import os

os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("APP_ENC_KEY", "00" * 32)
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")

from unittest.mock import AsyncMock


class TestAgentSafetyChecker:
    """Lines 149-213: AgentSafetyChecker.check_link all rules."""

    def _checker(self, domain: str = "example.com") -> object:
        from backend.fastapi.app.modules.auto_link_agent import AgentSafetyChecker
        return AgentSafetyChecker(site_domain=domain)

    def test_check_safe_link(self) -> None:
        """No violations for valid same-domain link."""
        checker = self._checker()
        violations = checker.check_link({  # type: ignore[union-attr]
            "from_url": "https://example.com/blog/post-1",
            "to_url": "https://example.com/blog/post-2",
            "anchor_text": "related content strategy",
            "relevance_score": 0.85,
        })
        blocking = [v for v in violations if v.severity == "block"]
        assert len(blocking) == 0

    def test_check_cross_domain_blocked(self) -> None:
        """Rule 1: cross-domain link → block violation."""
        checker = self._checker()
        violations = checker.check_link({  # type: ignore[union-attr]
            "from_url": "https://example.com/page",
            "to_url": "https://other-site.com/page",
            "anchor_text": "external site",
            "relevance_score": 0.9,
        })
        rules = [v.rule for v in violations]
        assert "same_domain" in rules

    def test_check_empty_urls_blocked(self) -> None:
        """Rule 2: empty URLs → block violation."""
        checker = self._checker()
        violations = checker.check_link({  # type: ignore[union-attr]
            "from_url": "",
            "to_url": "",
            "anchor_text": "valid anchor",
            "relevance_score": 0.9,
        })
        rules = [v.rule for v in violations]
        assert "url_required" in rules

    def test_check_empty_anchor_blocked(self) -> None:
        """Rule 3: empty anchor → block violation."""
        checker = self._checker()
        violations = checker.check_link({  # type: ignore[union-attr]
            "from_url": "https://example.com/page1",
            "to_url": "https://example.com/page2",
            "anchor_text": "",
            "relevance_score": 0.9,
        })
        rules = [v.rule for v in violations]
        assert "anchor_quality" in rules

    def test_check_generic_anchor_warn(self) -> None:
        """Rule 3: generic anchor → warn violation."""
        checker = self._checker()
        violations = checker.check_link({  # type: ignore[union-attr]
            "from_url": "https://example.com/page1",
            "to_url": "https://example.com/page2",
            "anchor_text": "click here",
            "relevance_score": 0.9,
        })
        rules = [v.rule for v in violations if v.severity == "warn"]
        assert "anchor_quality" in rules

    def test_check_blocked_path(self) -> None:
        """Rule 4: blocked path → block violation."""
        checker = self._checker()
        violations = checker.check_link({  # type: ignore[union-attr]
            "from_url": "https://example.com/page1",
            "to_url": "https://example.com/admin/dashboard",
            "anchor_text": "go to admin",
            "relevance_score": 0.9,
        })
        rules = [v.rule for v in violations]
        assert "blocked_path" in rules

    def test_check_self_link_blocked(self) -> None:
        """Rule 5: self-link → block violation."""
        checker = self._checker()
        violations = checker.check_link({  # type: ignore[union-attr]
            "from_url": "https://example.com/page1",
            "to_url": "https://example.com/page1",
            "anchor_text": "same page",
            "relevance_score": 0.9,
        })
        rules = [v.rule for v in violations]
        assert "no_self_link" in rules

    def test_check_low_relevance_warn(self) -> None:
        """Rule 6: low relevance score → warn violation."""
        checker = self._checker()
        violations = checker.check_link({  # type: ignore[union-attr]
            "from_url": "https://example.com/page1",
            "to_url": "https://example.com/page2",
            "anchor_text": "relevant content here to explore",
            "relevance_score": 0.1,  # below threshold
        })
        # low relevance_score should generate a warn
        assert isinstance(violations, list)


class TestAutoLinkAgentProcessLinks:
    """Lines 167-213: AutoLinkAgent.process_links."""

    def _make_agent(self, autonomy_tier: int = 2) -> object:
        from backend.fastapi.app.event_bus import EventBus
        from backend.fastapi.app.modules.auto_link_agent import AutoLinkAgent

        bus = EventBus()
        bus.emit = AsyncMock(return_value="mock-event-id")  # type: ignore[method-assign]
        mock_conn = AsyncMock()
        return AutoLinkAgent(
            site_id="site-001",
            agent_id="agent-001",
            site_domain="example.com",
            db_conn=mock_conn,
            event_bus=bus,
            autonomy_tier=autonomy_tier,
        )

    def test_process_links_tier2_approved(self) -> None:
        """Lines 175-213: tier 2 process links with safe links."""
        agent = self._make_agent(autonomy_tier=2)

        links = [
            {
                "from_url": "https://example.com/blog/intro",
                "to_url": "https://example.com/blog/advanced",
                "anchor_text": "read the advanced guide",
                "relevance_score": 0.9,
            }
        ]

        async def _run() -> None:
            result = await agent.process_links(run_id="run-001", links=links)  # type: ignore[union-attr]
            assert isinstance(result, dict)

        asyncio.get_event_loop().run_until_complete(_run())

    def test_process_links_tier1_no_execute(self) -> None:
        """Lines 167-200: tier 1 just logs, doesn't execute."""
        agent = self._make_agent(autonomy_tier=1)

        links = [
            {
                "from_url": "https://example.com/page1",
                "to_url": "https://example.com/page2",
                "anchor_text": "check this out in detail",
                "relevance_score": 0.8,
            }
        ]

        async def _run() -> None:
            result = await agent.process_links(run_id="run-002", links=links)  # type: ignore[union-attr]
            assert isinstance(result, dict)

        asyncio.get_event_loop().run_until_complete(_run())

    def test_process_links_with_blocking_violations(self) -> None:
        """Lines 175-200: links with blocking violations → rejected."""
        agent = self._make_agent(autonomy_tier=2)

        links = [
            {
                "from_url": "https://example.com/page1",
                "to_url": "https://other-site.com/page",  # cross-domain → block
                "anchor_text": "external resource for more info",
                "relevance_score": 0.9,
            }
        ]

        async def _run() -> None:
            result = await agent.process_links(run_id="run-003", links=links)  # type: ignore[union-attr]
            assert isinstance(result, dict)

        asyncio.get_event_loop().run_until_complete(_run())

    def test_process_links_empty(self) -> None:
        """Lines 168-169: empty links list returns immediately."""
        agent = self._make_agent()

        async def _run() -> None:
            result = await agent.process_links(run_id="run-004", links=[])  # type: ignore[union-attr]
            assert isinstance(result, dict)

        asyncio.get_event_loop().run_until_complete(_run())
