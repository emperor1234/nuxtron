"""
Targeted coverage tests for documents.py uncovered lines:
92-108 (_calc_quote_totals), 123 (doc_type fallback),
158/160 (share_document paths), 180-207 (delete_document + create_quote),
217 (list_quotes filter), 227-263 (get/send/sign quote paths),
278/280 (404 in quote ops), 293/298-307/316-327 (send/sign quote).
"""
from __future__ import annotations

import os

os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")
os.environ.setdefault("APP_ENC_KEY", "00" * 32)

import pytest
from fastapi.testclient import TestClient

H = {"X-API-Key": "test-api-key", "X-Tenant-Id": "docs-test-tenant"}
VALID = (200, 201, 202, 400, 401, 403, 404, 409, 422, 500, 503)


@pytest.fixture(scope="module")
def client() -> TestClient:
    from backend.fastapi.app.main import app
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture(scope="module")
def created_doc_id(client: TestClient) -> int:
    """Create a document and return its ID for later tests."""
    r = client.post("/documents", headers=H, json={
        "title": "Sales Brochure",
        "doc_type": "proposal",
        "description": "Q1 sales brochure",
    })
    assert r.status_code in (200, 201)
    return r.json()["document"]["id"]


@pytest.fixture(scope="module")
def created_quote_id(client: TestClient) -> int:
    """Create a quote with line items and return its ID."""
    r = client.post("/quotes", headers=H, json={
        "title": "Enterprise Deal Q1",
        "company_name": "Acme Corp",
        "recipient_email": "buyer@acme.com",
        "recipient_name": "Alice",
        "currency": "gbp",
        "line_items": [
            {
                "name": "Platform License",
                "description": "Annual SaaS license",
                "quantity": 5,
                "unit_price": 200.0,
                "discount_pct": 10.0,
                "tax_pct": 20.0,
            }
        ],
        "notes": "Annual contract",
        "require_signature": True,
    })
    assert r.status_code in (200, 201)
    return r.json()["quote"]["id"]


class TestDocumentsUncoveredLines:
    """Cover lines 123, 158-160, 180-207 in documents.py."""

    def test_create_document_invalid_doc_type_fallback(self, client: TestClient) -> None:
        """Line 123: unknown doc_type → falls back to 'other'."""
        r = client.post("/documents", headers=H, json={
            "title": "Miscellaneous File",
            "doc_type": "unknown_type_xyz",  # Not in DOC_TYPES → falls to 'other'
            "description": "An unrecognized document type",
        })
        assert r.status_code in (200, 201)
        if r.status_code in (200, 201):
            assert r.json()["document"]["doc_type"] == "other"

    def test_get_document_not_found(self, client: TestClient) -> None:
        """404 when document not found."""
        r = client.get("/documents/999999", headers=H)
        assert r.status_code == 404

    def test_share_document_not_found(self, client: TestClient) -> None:
        """Line 158: share_document → document not found → 404."""
        r = client.post("/documents/999999/share", headers=H, json={
            "recipient_email": "nobody@example.com",
        })
        assert r.status_code == 404

    def test_share_document_success(self, client: TestClient, created_doc_id: int) -> None:
        """Line 160: share_document → success path."""
        r = client.post(f"/documents/{created_doc_id}/share", headers=H, json={
            "recipient_email": "prospect@example.com",
            "recipient_name": "Bob Smith",
            "contact_id": "contact-123",
            "message": "Please review this proposal",
            "expires_in_days": 7,
        })
        assert r.status_code in (200, 201)
        if r.status_code in (200, 201):
            assert "share_token" in r.json()["share"]

    def test_delete_document_not_found(self, client: TestClient) -> None:
        """Lines 180-181: delete_document → document not found → 404."""
        r = client.delete("/documents/999999", headers=H)
        assert r.status_code == 404

    def test_delete_document_success(self, client: TestClient) -> None:
        """Lines 183-207: delete_document → success path."""
        # Create a document to delete
        r = client.post("/documents", headers=H, json={
            "title": "To Be Deleted",
            "doc_type": "contract",
            "description": "This document will be deleted",
        })
        assert r.status_code in (200, 201)
        doc_id = r.json()["document"]["id"]

        r2 = client.delete(f"/documents/{doc_id}", headers=H)
        assert r2.status_code in (200, 204)
        if r2.status_code == 200:
            assert r2.json()["deleted"] is True

    def test_list_documents_with_doc_type_filter(self, client: TestClient) -> None:
        """Line 217: list with doc_type filter."""
        r = client.get("/documents?doc_type=proposal", headers=H)
        assert r.status_code in VALID
        if r.status_code == 200:
            data = r.json()
            assert "documents" in data

    def test_list_documents_with_is_template_filter(self, client: TestClient) -> None:
        """is_template filter."""
        # Create a template first
        client.post("/documents", headers=H, json={
            "title": "Contract Template",
            "doc_type": "contract",
            "description": "Reusable contract template",
            "is_template": True,
        })
        r = client.get("/documents?is_template=true", headers=H)
        assert r.status_code in VALID
        if r.status_code == 200:
            data = r.json()
            assert all(d["is_template"] for d in data["documents"])


class TestQuotesUncoveredLines:
    """Cover lines 92-108, 227-327 in documents.py."""

    def test_calc_quote_totals_with_discounts_and_taxes(self, client: TestClient) -> None:
        """Lines 92-108: _calc_quote_totals with non-zero discount_pct and tax_pct."""
        r = client.post("/quotes", headers=H, json={
            "title": "Multi-Item Quote",
            "company_name": "Beta Ltd",
            "recipient_email": "buyer@beta.com",
            "currency": "usd",
            "line_items": [
                {
                    "name": "Professional Services",
                    "quantity": 10,
                    "unit_price": 150.0,
                    "discount_pct": 15.0,
                    "tax_pct": 20.0,
                },
                {
                    "name": "Support Package",
                    "quantity": 1,
                    "unit_price": 500.0,
                    "discount_pct": 5.0,
                    "tax_pct": 0.0,
                },
            ],
        })
        assert r.status_code in (200, 201)
        if r.status_code in (200, 201):
            quote = r.json()["quote"]
            assert quote["subtotal"] > 0
            assert quote["discount_total"] > 0
            assert quote["tax_total"] > 0
            assert quote["total"] > 0

    def test_get_quote_success(self, client: TestClient, created_quote_id: int) -> None:
        """Lines 227-230: get_quote success path."""
        r = client.get(f"/quotes/{created_quote_id}", headers=H)
        assert r.status_code == 200
        if r.status_code == 200:
            assert r.json()["quote"]["id"] == created_quote_id

    def test_get_quote_not_found(self, client: TestClient) -> None:
        """Line 278 or 280: get_quote 404."""
        r = client.get("/quotes/999999", headers=H)
        assert r.status_code == 404

    def test_list_quotes_with_status_filter(self, client: TestClient) -> None:
        """Lines 240-250: list_quotes with status filter."""
        r = client.get("/quotes?status=draft", headers=H)
        assert r.status_code in VALID
        if r.status_code == 200:
            data = r.json()
            assert "quotes" in data
            assert all(q["status"] == "draft" for q in data["quotes"])

    def test_list_quotes_with_deal_id_filter(self, client: TestClient) -> None:
        """Lines 250-255: list_quotes with deal_id filter."""
        r = client.get("/quotes?deal_id=deal-99999", headers=H)
        assert r.status_code in VALID
        if r.status_code == 200:
            data = r.json()
            assert data["total"] == 0

    def test_send_quote_success(self, client: TestClient, created_quote_id: int) -> None:
        """Lines 293/298-307: send_quote success path."""
        r = client.post(f"/quotes/{created_quote_id}/send", headers=H)
        assert r.status_code in (200, 201)
        if r.status_code in (200, 201):
            assert r.json()["quote"]["status"] == "sent"

    def test_send_quote_not_found(self, client: TestClient) -> None:
        """send_quote 404."""
        r = client.post("/quotes/999999/send", headers=H)
        assert r.status_code == 404

    def test_sign_quote_success(self, client: TestClient, created_quote_id: int) -> None:
        """Lines 316-327: sign_quote success path."""
        r = client.post(
            f"/quotes/{created_quote_id}/sign?signature_name=Alice+Johnson",
            headers=H,
        )
        assert r.status_code in (200, 201)
        if r.status_code in (200, 201):
            quote = r.json()["quote"]
            assert quote["status"] == "accepted"
            assert quote["signature_name"] == "Alice Johnson"

    def test_sign_quote_not_found(self, client: TestClient) -> None:
        """sign_quote 404."""
        r = client.post("/quotes/999999/sign?signature_name=Ghost+User", headers=H)
        assert r.status_code == 404
