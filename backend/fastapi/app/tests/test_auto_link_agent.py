"""
Tests for auto_link_agent.py pure helper classes.
"""
from __future__ import annotations

import os

os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")


class TestAgentSafetyChecker:
    def _make_checker(self):
        from backend.fastapi.app.modules.auto_link_agent import AgentSafetyChecker
        return AgentSafetyChecker(site_domain="example.com")

    def test_valid_link_passes(self) -> None:
        checker = self._make_checker()
        link = {
            "from_url": "https://example.com/page-a",
            "to_url": "https://example.com/page-b",
            "anchor_text": "Learn about SEO basics",
            "relevance_score": 0.8,
        }
        violations = checker.check_link(link)
        assert violations == []

    def test_cross_domain_blocked(self) -> None:
        checker = self._make_checker()
        link = {
            "from_url": "https://example.com/page-a",
            "to_url": "https://evil.com/page-b",
            "anchor_text": "Good anchor text",
            "relevance_score": 0.8,
        }
        violations = checker.check_link(link)
        rules = [v.rule for v in violations]
        assert "same_domain" in rules

    def test_empty_url_blocked(self) -> None:
        checker = self._make_checker()
        link = {
            "from_url": "",
            "to_url": "https://example.com/page-b",
            "anchor_text": "Anchor",
            "relevance_score": 0.8,
        }
        violations = checker.check_link(link)
        rules = [v.rule for v in violations]
        assert "url_required" in rules

    def test_short_anchor_blocked(self) -> None:
        checker = self._make_checker()
        link = {
            "from_url": "https://example.com/page-a",
            "to_url": "https://example.com/page-b",
            "anchor_text": "x",
            "relevance_score": 0.8,
        }
        violations = checker.check_link(link)
        rules = [v.rule for v in violations]
        assert "anchor_quality" in rules

    def test_empty_anchor_blocked(self) -> None:
        checker = self._make_checker()
        link = {
            "from_url": "https://example.com/page-a",
            "to_url": "https://example.com/page-b",
            "anchor_text": "",
            "relevance_score": 0.8,
        }
        violations = checker.check_link(link)
        rules = [v.rule for v in violations]
        assert "anchor_quality" in rules

    def test_generic_anchor_warns(self) -> None:
        checker = self._make_checker()
        link = {
            "from_url": "https://example.com/page-a",
            "to_url": "https://example.com/page-b",
            "anchor_text": "click here",
            "relevance_score": 0.8,
        }
        violations = checker.check_link(link)
        rules = [v.rule for v in violations]
        assert "anchor_quality" in rules
        severity = [v.severity for v in violations if v.rule == "anchor_quality"]
        assert "warn" in severity

    def test_blocked_path(self) -> None:
        checker = self._make_checker()
        link = {
            "from_url": "https://example.com/page-a",
            "to_url": "https://example.com/admin/settings",
            "anchor_text": "Admin Settings Page",
            "relevance_score": 0.8,
        }
        violations = checker.check_link(link)
        rules = [v.rule for v in violations]
        assert "blocked_path" in rules

    def test_self_link_blocked(self) -> None:
        checker = self._make_checker()
        link = {
            "from_url": "https://example.com/page-a",
            "to_url": "https://example.com/page-a",
            "anchor_text": "Same page link",
            "relevance_score": 0.8,
        }
        violations = checker.check_link(link)
        rules = [v.rule for v in violations]
        assert "no_self_link" in rules

    def test_low_relevance_blocked(self) -> None:
        checker = self._make_checker()
        link = {
            "from_url": "https://example.com/page-a",
            "to_url": "https://example.com/page-b",
            "anchor_text": "Relevant anchor text",
            "relevance_score": 0.3,
        }
        violations = checker.check_link(link)
        rules = [v.rule for v in violations]
        assert "relevance_threshold" in rules

    def test_custom_blocked_paths(self) -> None:
        from backend.fastapi.app.modules.auto_link_agent import AgentSafetyChecker
        checker = AgentSafetyChecker(
            site_domain="example.com",
            blocked_paths=["/secret", "/private"],
        )
        link = {
            "from_url": "https://example.com/page-a",
            "to_url": "https://example.com/secret/data",
            "anchor_text": "Secret data page",
            "relevance_score": 0.8,
        }
        violations = checker.check_link(link)
        rules = [v.rule for v in violations]
        assert "blocked_path" in rules

    def test_all_violations_are_blocking_means_no_approval(self) -> None:
        checker = self._make_checker()
        link = {
            "from_url": "",
            "to_url": "",
            "anchor_text": "",
            "relevance_score": 0.0,
        }
        violations = checker.check_link(link)
        blocking = [v for v in violations if v.severity == "block"]
        assert len(blocking) > 0


class TestBuildReasoning:
    def test_approved_reasoning(self) -> None:
        from backend.fastapi.app.modules.auto_link_agent import AutoLinkAgent
        agent = AutoLinkAgent.__new__(AutoLinkAgent)
        link = {
            "from_url": "https://example.com/a",
            "to_url": "https://example.com/b",
            "anchor_text": "Click for details",
            "relevance_score": 0.9,
        }
        reasoning = agent._build_reasoning(link, [], approved=True)
        assert "APPROVED" in reasoning
        assert "All safety checks passed" in reasoning

    def test_rejected_reasoning(self) -> None:
        from backend.fastapi.app.modules.auto_link_agent import AutoLinkAgent, SafetyViolation
        agent = AutoLinkAgent.__new__(AutoLinkAgent)
        link = {
            "from_url": "https://example.com/a",
            "to_url": "https://example.com/b",
            "anchor_text": "",
            "relevance_score": 0.1,
        }
        violations = [
            SafetyViolation(rule="anchor_quality", severity="block", detail="Too short"),
            SafetyViolation(rule="relevance_threshold", severity="block", detail="Too low"),
        ]
        reasoning = agent._build_reasoning(link, violations, approved=False)
        assert "REJECTED" in reasoning
        assert "anchor_quality" in reasoning
        assert "relevance_threshold" in reasoning

    def test_reasoning_contains_urls(self) -> None:
        from backend.fastapi.app.modules.auto_link_agent import AutoLinkAgent
        agent = AutoLinkAgent.__new__(AutoLinkAgent)
        link = {
            "from_url": "https://example.com/source-page",
            "to_url": "https://example.com/target-page",
            "anchor_text": "Good anchor",
            "relevance_score": 0.75,
        }
        reasoning = agent._build_reasoning(link, [], approved=True)
        assert "source-page" in reasoning
        assert "target-page" in reasoning
