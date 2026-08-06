"""Tests for pure helper functions in engagement_money_printers_bank.py and engagement_talent_agency.py."""
import os

os.environ.setdefault("APP_ENC_KEY", "00" * 32)
os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")

from backend.fastapi.app.routers.engagement_money_printers_bank import _build_printer_rollup
from backend.fastapi.app.routers.engagement_talent_agency import (
    _normalize_deliverables,
    _talent_deal_stage,
)

# ─── _build_printer_rollup ───────────────────────────────────────────────────

class TestBuildPrinterRollup:
    def test_empty_inputs(self):
        rollup, confidences = _build_printer_rollup(["ads", "email"], [], [])
        assert "ads" in rollup
        assert "email" in rollup
        assert rollup["ads"]["ideas"] == 0
        assert rollup["email"]["validated"] == 0

    def test_counts_ideas_per_printer(self):
        ideas = [
            {"printer": "ads", "expected_monthly_revenue_usd": 1000.0},
            {"printer": "ads", "expected_monthly_revenue_usd": 500.0},
            {"printer": "email", "expected_monthly_revenue_usd": 200.0},
        ]
        rollup, _ = _build_printer_rollup(["ads", "email"], ideas, [])
        assert rollup["ads"]["ideas"] == 2
        assert rollup["email"]["ideas"] == 1

    def test_sums_revenue(self):
        ideas = [
            {"printer": "ads", "expected_monthly_revenue_usd": 1000.0},
            {"printer": "ads", "expected_monthly_revenue_usd": 500.0},
        ]
        rollup, _ = _build_printer_rollup(["ads"], ideas, [])
        assert rollup["ads"]["projected_monthly_revenue_usd"] == 1500.0

    def test_counts_validations(self):
        validations = [
            {"printer": "ads", "outcome": "validated", "confidence": 80},
            {"printer": "ads", "outcome": "invalidated", "confidence": 20},
            {"printer": "email", "outcome": "validated", "confidence": 60},
        ]
        rollup, _ = _build_printer_rollup(["ads", "email"], [], validations)
        assert rollup["ads"]["validated"] == 1
        assert rollup["ads"]["invalidated"] == 1
        assert rollup["email"]["validated"] == 1

    def test_avg_confidence_computed(self):
        validations = [
            {"printer": "ads", "outcome": "validated", "confidence": 80},
            {"printer": "ads", "outcome": "validated", "confidence": 60},
        ]
        rollup, _ = _build_printer_rollup(["ads"], [], validations)
        assert rollup["ads"]["avg_confidence"] == 70

    def test_unknown_printer_ignored(self):
        ideas = [{"printer": "unknown_printer", "expected_monthly_revenue_usd": 500.0}]
        rollup, _ = _build_printer_rollup(["ads"], ideas, [])
        assert "unknown_printer" not in rollup
        assert rollup["ads"]["ideas"] == 0


# ─── _normalize_deliverables ─────────────────────────────────────────────────

class TestNormalizeDeliverables:
    def test_list_input(self):
        result = _normalize_deliverables(["story", "reel", "post"])
        assert result == ["story", "reel", "post"]

    def test_string_with_plus_separator(self):
        result = _normalize_deliverables("story+reel+post")
        assert result == ["story", "reel", "post"]

    def test_string_with_comma_separator(self):
        result = _normalize_deliverables("story,reel,post")
        assert result == ["story", "reel", "post"]

    def test_strips_whitespace(self):
        result = _normalize_deliverables("  story  +  reel  ")
        assert result == ["story", "reel"]

    def test_empty_list(self):
        result = _normalize_deliverables([])
        assert result == []

    def test_list_strips_whitespace(self):
        result = _normalize_deliverables(["  story  ", "reel"])
        assert result == ["story", "reel"]


# ─── _talent_deal_stage ──────────────────────────────────────────────────────

class TestTalentDealStage:
    def test_not_accepted_is_proposed(self):
        result = _talent_deal_stage(10000.0, False)
        assert result == "proposed"

    def test_low_budget_is_micro_deal(self):
        result = _talent_deal_stage(500.0, True)
        assert result == "micro_deal"

    def test_mid_budget_is_mid_market(self):
        result = _talent_deal_stage(2000.0, True)
        assert result == "mid_market_deal"

    def test_high_budget_is_enterprise(self):
        result = _talent_deal_stage(10000.0, True)
        assert result == "enterprise_deal"

    def test_boundary_1000_is_mid_market(self):
        result = _talent_deal_stage(1000.0, True)
        assert result == "mid_market_deal"

    def test_boundary_5000_is_enterprise(self):
        result = _talent_deal_stage(5000.0, True)
        assert result == "enterprise_deal"
