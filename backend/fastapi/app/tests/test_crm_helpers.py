"""Tests for pure helper functions in crm.py."""
import os

os.environ.setdefault("APP_ENC_KEY", "00" * 32)
os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")

from backend.fastapi.app.routers.crm import _apply_segment_filters

CONTACTS = [
    {
        "id": 1, "tenant_id": "t1", "lifecycle_stage": "lead", "lead_score": 50,
        "tags": ["vip", "hot"], "company": "Acme Corp", "email": "alice@acme.com",
    },
    {
        "id": 2, "tenant_id": "t1", "lifecycle_stage": "customer", "lead_score": 80,
        "tags": ["customer"], "company": "Beta Inc", "email": "bob@beta.com",
    },
    {
        "id": 3, "tenant_id": "t1", "lifecycle_stage": "lead", "lead_score": 20,
        "tags": [], "company": "Gamma LLC", "email": "carol@gamma.com",
    },
    {
        "id": 4, "tenant_id": "t2", "lifecycle_stage": "lead", "lead_score": 90,
        "tags": ["vip"], "company": "Delta Co", "email": "dave@delta.com",
    },
]


class TestApplySegmentFilters:
    def test_no_filters_returns_all_tenant_contacts(self):
        result = _apply_segment_filters("t1", {}, CONTACTS)
        assert len(result) == 3
        assert all(c["tenant_id"] == "t1" for c in result)

    def test_filters_by_tenant(self):
        result = _apply_segment_filters("t2", {}, CONTACTS)
        assert len(result) == 1
        assert result[0]["email"] == "dave@delta.com"

    def test_filter_by_lifecycle_stage(self):
        result = _apply_segment_filters("t1", {"lifecycle_stage": "lead"}, CONTACTS)
        assert len(result) == 2
        assert all(c["lifecycle_stage"] == "lead" for c in result)

    def test_filter_by_lifecycle_stage_customer(self):
        result = _apply_segment_filters("t1", {"lifecycle_stage": "customer"}, CONTACTS)
        assert len(result) == 1
        assert result[0]["id"] == 2

    def test_filter_by_min_lead_score(self):
        result = _apply_segment_filters("t1", {"min_lead_score": 60}, CONTACTS)
        assert len(result) == 1
        assert result[0]["lead_score"] == 80

    def test_filter_by_tag(self):
        result = _apply_segment_filters("t1", {"tag": "vip"}, CONTACTS)
        assert len(result) == 1
        assert result[0]["id"] == 1

    def test_filter_by_company_partial_match(self):
        result = _apply_segment_filters("t1", {"company": "acme"}, CONTACTS)
        assert len(result) == 1
        assert "acme" in result[0]["company"].lower()

    def test_returns_copies_not_originals(self):
        result = _apply_segment_filters("t1", {}, CONTACTS)
        result[0]["email"] = "modified@example.com"
        # Original should be unchanged
        assert CONTACTS[0]["email"] == "alice@acme.com"

    def test_combined_filters(self):
        result = _apply_segment_filters("t1", {"lifecycle_stage": "lead", "min_lead_score": 40}, CONTACTS)
        assert len(result) == 1
        assert result[0]["id"] == 1
