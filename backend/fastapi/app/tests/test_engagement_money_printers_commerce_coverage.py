"""Focused coverage tests for engagement_money_printers_commerce.py branches."""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")
os.environ.setdefault("APP_ENC_KEY", "00" * 32)

H = {"X-API-Key": "test-api-key", "X-Tenant-Id": "commerce-coverage-tenant"}


@pytest.fixture(scope="module")
def client() -> TestClient:
    from backend.fastapi.app.main import app

    return TestClient(app, raise_server_exceptions=False)


class TestCommerceCoverage:
    def test_create_order_product_not_found(self, client: TestClient) -> None:
        r = client.post(
            "/money-printers/commerce-pro/orders",
            headers=H,
            json={"product_id": 999999, "quantity": 1, "buyer_email": "buyer@example.com"},
        )
        assert r.status_code == 404

    def test_order_status_backorder_when_inventory_zero(self, client: TestClient) -> None:
        r_product = client.post(
            "/money-printers/commerce-pro/products",
            headers=H,
            json={
                "name": "Out of Stock Item",
                "description": "No inventory",
                "price_usd": 25,
                "currency": "usd",
                "inventory": 0,
                "digital": False,
            },
        )
        assert r_product.status_code in (200, 201)
        product_id = r_product.json()["product"]["id"]

        r_order = client.post(
            "/money-printers/commerce-pro/orders",
            headers=H,
            json={"product_id": product_id, "quantity": 2, "buyer_email": "buyer@example.com", "note": "waitlist"},
        )
        assert r_order.status_code in (200, 201)
        order = r_order.json()["order"]
        assert order["order_status"] == "backorder"
        assert order["total_usd"] == 50.0

    def test_order_status_partial_when_quantity_exceeds_inventory(self, client: TestClient) -> None:
        r_product = client.post(
            "/money-printers/commerce-pro/products",
            headers=H,
            json={
                "name": "Limited Item",
                "description": "Small inventory",
                "price_usd": 10,
                "currency": "usd",
                "inventory": 2,
                "digital": False,
            },
        )
        product_id = r_product.json()["product"]["id"]

        r_order = client.post(
            "/money-printers/commerce-pro/orders",
            headers=H,
            json={"product_id": product_id, "quantity": 3, "buyer_email": "buyer2@example.com"},
        )
        assert r_order.status_code in (200, 201)
        assert r_order.json()["order"]["order_status"] == "partial"

    def test_order_status_confirmed_when_quantity_fits_inventory(self, client: TestClient) -> None:
        r_product = client.post(
            "/money-printers/commerce-pro/products",
            headers=H,
            json={
                "name": "In Stock Item",
                "description": "Enough inventory",
                "price_usd": 40,
                "currency": "usd",
                "inventory": 10,
                "digital": True,
            },
        )
        product_id = r_product.json()["product"]["id"]

        r_order = client.post(
            "/money-printers/commerce-pro/orders",
            headers=H,
            json={"product_id": product_id, "quantity": 4, "buyer_email": "buyer3@example.com"},
        )
        assert r_order.status_code in (200, 201)
        assert r_order.json()["order"]["order_status"] == "confirmed"
