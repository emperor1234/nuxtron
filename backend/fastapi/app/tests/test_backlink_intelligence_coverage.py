"""
Backlink Intelligence — comprehensive coverage tests.

All 38+ assertions against the full backlink-intel router.
"""

from __future__ import annotations

import os
import uuid

os.environ["ALLOW_HEADER_API_KEYS"] = "true"
os.environ["FASTAPI_API_KEY"] = "test-api-key"

from backend.fastapi.app.legacy_main import app  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

client = TestClient(app)

H = {"X-API-Key": "test-api-key", "X-Tenant-Id": "bl-test-tenant"}
H2 = {"X-API-Key": "test-api-key", "X-Tenant-Id": "bl-test-tenant-2"}
BASE = "/backlink-intel"


class TestBacklinkIntelligenceCoverage:
    # ------------------------------------------------------------------
    # Overview
    # ------------------------------------------------------------------

    def test_overview_returns_authority_score(self):
        r = client.get(f"{BASE}/overview", headers=H)
        assert r.status_code == 200
        data = r.json()["overview"]
        assert "authority_score" in data
        assert 0 <= data["authority_score"] <= 100

    def test_overview_has_aggregate_keys(self):
        r = client.get(f"{BASE}/overview", headers=H)
        assert r.status_code == 200
        data = r.json()["overview"]
        for key in ("total_backlinks", "active_backlinks", "referring_domains", "dofollow_count", "dofollow_pct", "new_backlinks_30d", "toxic_count"):
            assert key in data, f"Missing key: {key}"

    def test_overview_authority_label_present(self):
        r = client.get(f"{BASE}/overview", headers=H)
        assert r.json()["overview"]["authority_score_label"] in ("Weak", "Moderate", "Strong")

    def test_overview_requires_auth(self):
        r = client.get(f"{BASE}/overview")
        assert r.status_code in (401, 403, 422)

    # ------------------------------------------------------------------
    # Domains CRUD
    # ------------------------------------------------------------------

    def test_add_domain(self):
        domain = f"test-domain-{uuid.uuid4().hex[:6]}.com"
        r = client.post(f"{BASE}/domains", json={"domain": domain, "label": "Main Site"}, headers=H)
        assert r.status_code == 201
        assert r.json()["domain"]["domain"] == domain

    def test_add_domain_authority_score_populated(self):
        domain = f"auth-domain-{uuid.uuid4().hex[:6]}.com"
        r = client.post(f"{BASE}/domains", json={"domain": domain}, headers=H)
        assert 0 <= r.json()["domain"]["authority_score"] <= 100

    def test_add_domain_duplicate_returns_409(self):
        domain = f"dup-{uuid.uuid4().hex[:6]}.com"
        client.post(f"{BASE}/domains", json={"domain": domain}, headers=H)
        r2 = client.post(f"{BASE}/domains", json={"domain": domain}, headers=H)
        assert r2.status_code == 409

    def test_list_domains(self):
        r = client.get(f"{BASE}/domains", headers=H)
        assert r.status_code == 200
        assert "domains" in r.json()
        assert "total" in r.json()

    def test_delete_domain(self):
        domain = f"del-{uuid.uuid4().hex[:6]}.com"
        r = client.post(f"{BASE}/domains", json={"domain": domain}, headers=H)
        domain_id = r.json()["domain"]["id"]
        r2 = client.delete(f"{BASE}/domains/{domain_id}", headers=H)
        assert r2.status_code == 200
        assert r2.json()["deleted"] == domain_id

    def test_delete_domain_not_found(self):
        r = client.delete(f"{BASE}/domains/{uuid.uuid4()}", headers=H)
        assert r.status_code == 404

    # ------------------------------------------------------------------
    # Backlinks
    # ------------------------------------------------------------------

    def test_list_backlinks_returns_seeded(self):
        r = client.get(f"{BASE}/backlinks", headers=H)
        assert r.status_code == 200
        data = r.json()
        assert data["total"] >= 1
        assert len(data["backlinks"]) >= 1

    def test_list_backlinks_pagination(self):
        r = client.get(f"{BASE}/backlinks?page=1&page_size=5", headers=H)
        assert r.status_code == 200
        assert len(r.json()["backlinks"]) <= 5

    def test_list_backlinks_filter_by_status(self):
        r = client.get(f"{BASE}/backlinks?status=healthy", headers=H)
        assert r.status_code == 200
        for bl in r.json()["backlinks"]:
            assert bl["status"] == "healthy"

    def test_list_backlinks_search(self):
        # Import a known backlink then search for it
        src = f"searchable-{uuid.uuid4().hex[:6]}.com"
        client.post(f"{BASE}/backlinks", json={
            "source_domain": src,
            "source_url": f"https://{src}/blog",
            "target_url": "https://yourdomain.com",
            "anchor_text": "unique anchor XYZ",
            "link_type": "text",
            "link_follow": "dofollow",
            "source_authority": 45,
        }, headers=H)
        r = client.get(f"{BASE}/backlinks?search=unique+anchor+XYZ", headers=H)
        assert r.status_code == 200
        assert any("unique anchor XYZ" in bl["anchor_text"] for bl in r.json()["backlinks"])

    def test_import_backlink(self):
        r = client.post(f"{BASE}/backlinks", json={
            "source_domain": "example-blog.com",
            "source_url": "https://example-blog.com/article",
            "target_url": "https://yourdomain.com",
            "anchor_text": "best platform",
            "link_type": "text",
            "link_follow": "dofollow",
            "source_authority": 60,
        }, headers=H)
        assert r.status_code == 201
        bl = r.json()["backlink"]
        assert bl["status"] == "healthy"
        assert bl["source_authority"] == 60

    def test_update_backlink_status_valid(self):
        # Import then update
        r = client.post(f"{BASE}/backlinks", json={
            "source_domain": "spam-site.com",
            "source_url": "https://spam-site.com/x",
            "target_url": "https://yourdomain.com",
            "anchor_text": "click here",
            "link_type": "text",
            "link_follow": "dofollow",
            "source_authority": 5,
        }, headers=H)
        bl_id = r.json()["backlink"]["id"]
        r2 = client.patch(f"{BASE}/backlinks/{bl_id}/status", json={"status": "toxic"}, headers=H)
        assert r2.status_code == 200
        assert r2.json()["backlink"]["status"] == "toxic"

    def test_update_backlink_status_invalid(self):
        r_bl = client.post(f"{BASE}/backlinks", json={
            "source_domain": "ok.com",
            "source_url": "https://ok.com/x",
            "target_url": "https://yourdomain.com",
            "anchor_text": "ok",
            "link_type": "text",
            "link_follow": "dofollow",
            "source_authority": 50,
        }, headers=H)
        bl_id = r_bl.json()["backlink"]["id"]
        r = client.patch(f"{BASE}/backlinks/{bl_id}/status", json={"status": "unknown-status"}, headers=H)
        assert r.status_code == 422

    def test_delete_backlink(self):
        r = client.post(f"{BASE}/backlinks", json={
            "source_domain": "to-delete.com",
            "source_url": "https://to-delete.com/x",
            "target_url": "https://yourdomain.com",
            "anchor_text": "delete me",
            "link_type": "text",
            "link_follow": "dofollow",
            "source_authority": 20,
        }, headers=H)
        bl_id = r.json()["backlink"]["id"]
        r2 = client.delete(f"{BASE}/backlinks/{bl_id}", headers=H)
        assert r2.status_code == 200
        assert r2.json()["deleted"] == bl_id

    def test_delete_backlink_not_found(self):
        r = client.delete(f"{BASE}/backlinks/{uuid.uuid4()}", headers=H)
        assert r.status_code == 404

    # ------------------------------------------------------------------
    # Backlink Audit
    # ------------------------------------------------------------------

    def test_run_audit_returns_structure(self):
        r = client.post(f"{BASE}/audit", json={"domain": "yourdomain.com"}, headers=H)
        assert r.status_code == 200
        audit = r.json()["audit"]
        for key in ("id", "total_links_audited", "toxic_count", "suspicious_count", "healthy_count", "overall_risk_pct", "risk_level", "results"):
            assert key in audit, f"Missing: {key}"

    def test_run_audit_risk_level_values(self):
        r = client.post(f"{BASE}/audit", json={"domain": "yourdomain.com"}, headers=H)
        assert r.json()["audit"]["risk_level"] in ("Low", "Moderate", "Critical")

    def test_run_audit_results_have_signals(self):
        r = client.post(f"{BASE}/audit", json={"domain": "yourdomain.com"}, headers=H)
        results = r.json()["audit"]["results"]
        assert isinstance(results, list)
        for item in results:
            assert "signals" in item
            assert isinstance(item["signals"], list)

    def test_audit_history_grows(self):
        client.post(f"{BASE}/audit", json={"domain": "yourdomain.com"}, headers=H)
        r = client.get(f"{BASE}/audit/history", headers=H)
        assert r.status_code == 200
        assert r.json()["total"] >= 1

    def test_audit_history_no_results_key(self):
        r = client.get(f"{BASE}/audit/history", headers=H)
        for audit in r.json()["audits"]:
            assert "results" not in audit, "History should return summaries, not full results"

    # ------------------------------------------------------------------
    # Gap Analysis
    # ------------------------------------------------------------------

    def test_gap_analysis_returns_opportunities(self):
        r = client.post(f"{BASE}/gap-analysis", json={
            "your_domain": "yourdomain.com",
            "competitor_domains": ["ahrefs.com", "moz.com"],
        }, headers=H)
        assert r.status_code == 200
        data = r.json()["gap_analysis"]
        assert "opportunities" in data
        assert "competitors" in data
        assert len(data["competitors"]) == 2
        if data["opportunities"]:
            assert max(item.get("competitor_count", 0) for item in data["opportunities"]) >= 1

    def test_gap_analysis_competitor_structure(self):
        r = client.post(f"{BASE}/gap-analysis", json={
            "your_domain": "yourdomain.com",
            "competitor_domains": ["semrush.com"],
        }, headers=H)
        comp = r.json()["gap_analysis"]["competitors"][0]
        for key in ("domain", "authority_score", "referring_domains", "exclusive_domains", "shared_domains"):
            assert key in comp, f"Missing key: {key}"

    def test_gap_analysis_max_4_competitors(self):
        r = client.post(f"{BASE}/gap-analysis", json={
            "your_domain": "yourdomain.com",
            "competitor_domains": ["a.com", "b.com", "c.com", "d.com", "e.com"],
        }, headers=H)
        # 5 competitors should fail validation (max_length=4)
        assert r.status_code == 422

    # ------------------------------------------------------------------
    # Prospects
    # ------------------------------------------------------------------

    def test_list_prospects_seeded(self):
        r = client.get(f"{BASE}/prospects", headers=H)
        assert r.status_code == 200
        assert r.json()["total"] >= 1

    def test_add_prospect(self):
        r = client.post(f"{BASE}/prospects", json={
            "domain": f"newprospect-{uuid.uuid4().hex[:6]}.com",
            "target_page": "https://example.com/resources",
            "contact_email": "hello@example.com",
            "notes": "Good fit for guest post",
        }, headers=H)
        assert r.status_code == 201
        p = r.json()["prospect"]
        assert p["status"] == "new"
        assert p["pitch_sent"] is False

    def test_update_prospect_status_contacted(self):
        r = client.post(f"{BASE}/prospects", json={"domain": f"outreach-{uuid.uuid4().hex[:6]}.com"}, headers=H)
        pid = r.json()["prospect"]["id"]
        r2 = client.patch(f"{BASE}/prospects/{pid}/status", json={"status": "contacted"}, headers=H)
        assert r2.status_code == 200
        assert r2.json()["prospect"]["status"] == "contacted"
        assert r2.json()["prospect"]["pitch_sent"] is True

    def test_update_prospect_status_won(self):
        r = client.post(f"{BASE}/prospects", json={"domain": f"won-{uuid.uuid4().hex[:6]}.com"}, headers=H)
        pid = r.json()["prospect"]["id"]
        r2 = client.patch(f"{BASE}/prospects/{pid}/status", json={"status": "won"}, headers=H)
        assert r2.json()["prospect"]["status"] == "won"

    def test_update_prospect_status_invalid(self):
        r = client.post(f"{BASE}/prospects", json={"domain": f"invalid-{uuid.uuid4().hex[:6]}.com"}, headers=H)
        pid = r.json()["prospect"]["id"]
        r2 = client.patch(f"{BASE}/prospects/{pid}/status", json={"status": "maybe"}, headers=H)
        assert r2.status_code == 422

    def test_filter_prospects_by_status(self):
        r = client.get(f"{BASE}/prospects?status=new", headers=H)
        assert r.status_code == 200
        for p in r.json()["prospects"]:
            assert p["status"] == "new"

    def test_delete_prospect(self):
        r = client.post(f"{BASE}/prospects", json={"domain": f"del-p-{uuid.uuid4().hex[:6]}.com"}, headers=H)
        pid = r.json()["prospect"]["id"]
        r2 = client.delete(f"{BASE}/prospects/{pid}", headers=H)
        assert r2.status_code == 200
        assert r2.json()["deleted"] == pid

    # ------------------------------------------------------------------
    # Analytics
    # ------------------------------------------------------------------

    def test_analytics_structure(self):
        r = client.get(f"{BASE}/analytics", headers=H)
        assert r.status_code == 200
        data = r.json()["analytics"]
        for key in ("timeseries", "anchor_distribution", "follow_distribution", "authority_buckets", "total_analyzed"):
            assert key in data, f"Missing key: {key}"

    def test_analytics_custom_days(self):
        r = client.get(f"{BASE}/analytics?days=30", headers=H)
        assert r.status_code == 200
        assert r.json()["analytics"]["days"] == 30

    def test_analytics_authority_buckets_keys(self):
        r = client.get(f"{BASE}/analytics", headers=H)
        buckets = r.json()["analytics"]["authority_buckets"]
        for k in ("0-20", "21-40", "41-60", "61-80", "81-100"):
            assert k in buckets

    # ------------------------------------------------------------------
    # Authority Score
    # ------------------------------------------------------------------

    def test_authority_score_any_domain(self):
        r = client.post(f"{BASE}/authority-score", json={"domain": "moz.com"}, headers=H)
        assert r.status_code == 200
        data = r.json()["authority_score"]
        assert 0 <= data["score"] <= 100
        assert data["domain"] == "moz.com"
        assert data["label"] in ("Weak", "Moderate", "Strong")

    def test_authority_score_has_delta(self):
        r = client.post(f"{BASE}/authority-score", json={"domain": "ahrefs.com"}, headers=H)
        data = r.json()["authority_score"]
        assert "delta" in data
        assert "your_score" in data

    # ------------------------------------------------------------------
    # Disavow
    # ------------------------------------------------------------------

    def test_disavow_generates_content(self):
        # Import a toxic backlink
        r = client.post(f"{BASE}/backlinks", json={
            "source_domain": "toxic-spam.com",
            "source_url": "https://toxic-spam.com/x",
            "target_url": "https://yourdomain.com",
            "anchor_text": "click here",
            "link_type": "text",
            "link_follow": "dofollow",
            "source_authority": 3,
        }, headers=H)
        bl_id = r.json()["backlink"]["id"]
        r2 = client.post(f"{BASE}/disavow", json={"backlink_ids": [bl_id]}, headers=H)
        assert r2.status_code == 200
        data = r2.json()["disavow"]
        assert "content" in data
        assert "domain:toxic-spam.com" in data["content"]
        assert data["domains_count"] >= 1

    def test_disavow_not_found_returns_404(self):
        r = client.post(f"{BASE}/disavow", json={"backlink_ids": [str(uuid.uuid4())]}, headers=H)
        assert r.status_code == 404

    # ------------------------------------------------------------------
    # Tenant Isolation
    # ------------------------------------------------------------------

    def test_tenant_isolation_domains(self):
        domain = f"iso-{uuid.uuid4().hex[:6]}.com"
        client.post(f"{BASE}/domains", json={"domain": domain}, headers=H)
        r2 = client.get(f"{BASE}/domains", headers=H2)
        domains_t2 = [d["domain"] for d in r2.json()["domains"]]
        assert domain not in domains_t2

    def test_tenant_isolation_backlinks(self):
        # Import a backlink in tenant 1
        r = client.post(f"{BASE}/backlinks", json={
            "source_domain": "tenant1-exclusive.com",
            "source_url": "https://tenant1-exclusive.com/x",
            "target_url": "https://yourdomain.com",
            "anchor_text": "exclusive",
            "link_type": "text",
            "link_follow": "dofollow",
            "source_authority": 55,
        }, headers=H)
        assert r.status_code == 201
        # Tenant 2 should not see it
        r2 = client.get(f"{BASE}/backlinks?search=tenant1-exclusive", headers=H2)
        assert all(bl["source_domain"] != "tenant1-exclusive.com" for bl in r2.json()["backlinks"])

    # ------------------------------------------------------------------
    # Auth guards
    # ------------------------------------------------------------------

    def test_all_endpoints_require_auth(self):
        endpoints = [
            ("GET",    f"{BASE}/overview"),
            ("GET",    f"{BASE}/domains"),
            ("GET",    f"{BASE}/backlinks"),
            ("GET",    f"{BASE}/audit/history"),
            ("GET",    f"{BASE}/prospects"),
            ("GET",    f"{BASE}/analytics"),
        ]
        for method, url in endpoints:
            r = client.request(method, url)
            assert r.status_code in (401, 403, 422), f"{method} {url} should require auth, got {r.status_code}"
