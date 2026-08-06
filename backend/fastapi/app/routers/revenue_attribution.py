# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnknownParameterType=false, reportUnusedFunction=false

import base64
import hashlib
import hmac
import itertools
import json
import math
import os
import re
import threading
import uuid
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Annotated, Any
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import psycopg
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from pydantic import BaseModel, Field

from ..deps import AuthContext, require_auth

AuthDep = Annotated[AuthContext, Depends(require_auth)]

_PROVIDER_SET = {"stripe", "shopify", "woocommerce"}
_TOUCHPOINT_PATTERN = re.compile(r"\btp_[a-z0-9]{8,}\b")


class RevenueTouchpointRequest(BaseModel):
    post_id: str = Field(min_length=1, max_length=160)
    platform: str = Field(min_length=1, max_length=80)
    campaign: str = Field(min_length=1, max_length=160)
    destination_url: str = Field(min_length=8, max_length=2000)
    utm_source: str | None = Field(default=None, max_length=120)
    utm_medium: str | None = Field(default=None, max_length=80)
    utm_content: str | None = Field(default=None, max_length=160)


class ConversionIngestRequest(BaseModel):
    provider: str = Field(min_length=1, max_length=40)
    external_order_id: str = Field(min_length=1, max_length=160)
    amount: float = Field(gt=0)
    currency: str = Field(default="USD", min_length=3, max_length=12)
    event_type: str = Field(default="order.paid", min_length=3, max_length=120)
    customer_ref: str | None = Field(default=None, max_length=200)
    touchpoint_keys: list[str] = Field(default_factory=list, max_length=32)
    raw_payload: dict[str, Any] = Field(default_factory=dict)


class SocialSpendRequest(BaseModel):
    channel: str = Field(min_length=1, max_length=80)
    campaign: str = Field(default="", max_length=160)
    amount: float = Field(gt=0)
    currency: str = Field(default="USD", min_length=3, max_length=12)
    spent_at: datetime | None = None
    notes: str = Field(default="", max_length=500)


class SocialRoiCalculatorRequest(BaseModel):
    attributed_revenue: float = Field(ge=0)
    paid_social_spend: float = Field(default=0.0, ge=0)
    team_cost: float = Field(default=0.0, ge=0)
    tools_cost: float = Field(default=0.0, ge=0)
    agency_cost: float = Field(default=0.0, ge=0)


def _extract_touchpoints(node: Any) -> list[str]:
    found: set[str] = set()
    stack: list[Any] = [node]

    while stack:
        value = stack.pop()
        if isinstance(value, dict):
            stack.extend(value.values())
            continue
        if isinstance(value, list):
            stack.extend(value)
            continue
        if isinstance(value, str):
            found.update(_TOUCHPOINT_PATTERN.findall(value))
            parsed = urlparse(value)
            query_pairs = parse_qsl(parsed.query, keep_blank_values=True)
            found.update(qv for qk, qv in query_pairs if qk == "nux_touchpoint" and qv)

    return sorted(found)


def _inject_utm(url: str, source: str, medium: str, campaign: str, content: str, touchpoint_key: str) -> str:
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        raise HTTPException(status_code=422, detail="destination_url must include scheme and host.")
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    query["utm_source"] = source.strip().lower()
    query["utm_medium"] = medium.strip().lower()
    query["utm_campaign"] = campaign.strip().lower().replace(" ", "_")
    query["utm_content"] = content.strip().lower().replace(" ", "_")
    query["nux_touchpoint"] = touchpoint_key
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, urlencode(query), parsed.fragment))


def _verify_stripe_signature(secret: str, raw_body: bytes, sig_header: str) -> bool:
    fields: dict[str, str] = {}
    for part in sig_header.split(","):
        if "=" not in part:
            continue
        key, value = part.strip().split("=", 1)
        fields[key] = value
    timestamp = fields.get("t")
    signature = fields.get("v1")
    if not timestamp or not signature:
        return False
    signed_payload = f"{timestamp}.{raw_body.decode('utf-8')}".encode()
    expected = hmac.new(secret.encode("utf-8"), signed_payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def _verify_base64_hmac(secret: str, raw_body: bytes, signature_header: str) -> bool:
    digest = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).digest()
    expected = base64.b64encode(digest).decode("utf-8")
    return hmac.compare_digest(expected, signature_header)


def _extract_conversion(provider: str, payload: dict[str, Any]) -> tuple[str, float, str, str, str | None, list[str]]:
    extractor_map: dict[str, Callable[[dict[str, Any]], tuple[str, float, str, str, str | None]]] = {
        "stripe": _extract_stripe_conversion,
        "shopify": _extract_shopify_conversion,
        "woocommerce": _extract_woocommerce_conversion,
    }
    extractor = extractor_map.get(provider, _extract_woocommerce_conversion)
    external_order_id, amount, currency, event_type, customer_ref = extractor(payload)
    touchpoints = _extract_touchpoints(payload)
    return external_order_id, amount, currency, event_type, customer_ref, touchpoints


def _extract_stripe_conversion(payload: dict[str, Any]) -> tuple[str, float, str, str, str | None]:
    event_type = str(payload.get("type") or "stripe.unknown")
    data = payload.get("data")
    data_object = data.get("object", {}) if isinstance(data, dict) else {}
    external_order_id = str(
        data_object.get("id")
        or payload.get("id")
        or data_object.get("payment_intent")
        or f"stripe-{uuid.uuid4().hex[:12]}"
    )
    amount_raw = data_object.get("amount_total") or data_object.get("amount") or 0
    amount = float(amount_raw) / 100.0 if isinstance(amount_raw, (int, float)) else float(amount_raw or 0)
    currency = str(data_object.get("currency") or "usd").upper()
    customer_ref = str(data_object.get("customer_email") or data_object.get("customer") or "").strip() or None
    return external_order_id, amount, currency, event_type, customer_ref


def _extract_shopify_conversion(payload: dict[str, Any]) -> tuple[str, float, str, str, str | None]:
    event_type = str(payload.get("topic") or "orders/paid")
    external_order_id = str(payload.get("id") or payload.get("order_id") or f"shopify-{uuid.uuid4().hex[:12]}")
    amount = float(payload.get("total_price") or payload.get("current_total_price") or 0)
    currency = str(payload.get("currency") or "USD").upper()
    customer = payload.get("customer")
    customer_dict = customer if isinstance(customer, dict) else {}
    customer_ref = str(customer_dict.get("email") or payload.get("email") or "").strip() or None
    return external_order_id, amount, currency, event_type, customer_ref


def _extract_woocommerce_conversion(payload: dict[str, Any]) -> tuple[str, float, str, str, str | None]:
    event_type = str(payload.get("event") or payload.get("type") or "order.created")
    external_order_id = str(payload.get("id") or payload.get("order_id") or f"woo-{uuid.uuid4().hex[:12]}")
    amount = float(payload.get("total") or payload.get("amount") or 0)
    currency = str(payload.get("currency") or "USD").upper()
    billing = payload.get("billing")
    billing_dict = billing if isinstance(billing, dict) else {}
    customer_ref = str(billing_dict.get("email") or payload.get("customer_email") or "").strip() or None
    return external_order_id, amount, currency, event_type, customer_ref


class _RevenueAttributionStore:
    def __init__(
        self,
        *,
        touchpoints_memory: list[dict[str, Any]],
        conversions_memory: list[dict[str, Any]],
        spend_memory: list[dict[str, Any]],
        db_ready_fn: Callable[[], bool],
        db_dsn_fn: Callable[[], str],
    ) -> None:
        self._touchpoints_memory = touchpoints_memory
        self._conversions_memory = conversions_memory
        self._spend_memory = spend_memory
        self._db_ready_fn = db_ready_fn
        self._db_dsn_fn = db_dsn_fn
        self._lock = threading.Lock()
        self._db_init_lock = threading.Lock()
        self._db_initialized = False

    def ensure_tables(self) -> None:
        if not self._db_ready_fn() or self._db_initialized:
            return
        with self._db_init_lock:
            if self._db_initialized:
                return
            with psycopg.connect(self._db_dsn_fn()) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        CREATE TABLE IF NOT EXISTS revenue_attribution_touchpoints (
                            id BIGSERIAL PRIMARY KEY,
                            tenant_id TEXT NOT NULL,
                            touchpoint_key TEXT NOT NULL UNIQUE,
                            post_id TEXT NOT NULL,
                            platform TEXT NOT NULL,
                            campaign TEXT NOT NULL,
                            source TEXT NOT NULL,
                            medium TEXT NOT NULL,
                            content TEXT NOT NULL,
                            destination_url TEXT NOT NULL,
                            tracked_url TEXT NOT NULL,
                            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                        )
                        """
                    )
                    cur.execute(
                        """
                        CREATE TABLE IF NOT EXISTS revenue_attribution_conversions (
                            id BIGSERIAL PRIMARY KEY,
                            tenant_id TEXT NOT NULL,
                            provider TEXT NOT NULL,
                            external_order_id TEXT NOT NULL,
                            customer_ref TEXT,
                            currency TEXT NOT NULL,
                            amount NUMERIC(12, 2) NOT NULL,
                            event_type TEXT NOT NULL,
                            touchpoint_keys TEXT[] NOT NULL DEFAULT '{}',
                            raw_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
                            received_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                            UNIQUE (tenant_id, provider, external_order_id, event_type)
                        )
                        """
                    )
                    cur.execute(
                        "CREATE INDEX IF NOT EXISTS idx_revenue_touchpoints_tenant_post ON revenue_attribution_touchpoints (tenant_id, post_id)"
                    )
                    cur.execute(
                        "CREATE INDEX IF NOT EXISTS idx_revenue_conversions_tenant_received ON revenue_attribution_conversions (tenant_id, received_at DESC)"
                    )
                    cur.execute(
                        """
                        CREATE TABLE IF NOT EXISTS revenue_attribution_spend (
                            id BIGSERIAL PRIMARY KEY,
                            tenant_id TEXT NOT NULL,
                            channel TEXT NOT NULL,
                            campaign TEXT NOT NULL DEFAULT '',
                            currency TEXT NOT NULL,
                            amount NUMERIC(12, 2) NOT NULL,
                            notes TEXT NOT NULL DEFAULT '',
                            spent_at TIMESTAMPTZ NOT NULL,
                            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                        )
                        """
                    )
                    cur.execute(
                        "CREATE INDEX IF NOT EXISTS idx_revenue_spend_tenant_spent_at ON revenue_attribution_spend (tenant_id, spent_at DESC)"
                    )
                conn.commit()
            self._db_initialized = True

    def record_spend(self, tenant_id: str, payload: SocialSpendRequest) -> dict[str, Any]:
        spent_at = payload.spent_at.astimezone(UTC).isoformat() if payload.spent_at else datetime.now(UTC).isoformat()
        item: dict[str, Any] = {
            "tenant_id": tenant_id,
            "channel": payload.channel.strip().lower(),
            "campaign": payload.campaign.strip(),
            "currency": payload.currency.strip().upper(),
            "amount": round(float(payload.amount), 2),
            "notes": payload.notes,
            "spent_at": spent_at,
            "created_at": datetime.now(UTC).isoformat(),
        }

        self.ensure_tables()
        if self._db_ready_fn():
            with psycopg.connect(self._db_dsn_fn()) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO revenue_attribution_spend (
                            tenant_id, channel, campaign, currency, amount, notes, spent_at
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        RETURNING id, created_at
                        """,
                        (
                            tenant_id,
                            item["channel"],
                            item["campaign"],
                            item["currency"],
                            Decimal(str(item["amount"])),
                            item["notes"],
                            item["spent_at"],
                        ),
                    )
                    row = cur.fetchone()
                conn.commit()
            if row:
                item["id"] = int(row[0])
                item["created_at"] = row[1].isoformat()
            return item

        with self._lock:
            item["id"] = len(self._spend_memory) + 1
            self._spend_memory.append(item)
        return item

    def list_spend(self, tenant_id: str, limit: int, offset: int) -> list[dict[str, Any]]:
        self.ensure_tables()
        if self._db_ready_fn():
            with psycopg.connect(self._db_dsn_fn()) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT id, channel, campaign, currency, amount, notes, spent_at, created_at
                        FROM revenue_attribution_spend
                        WHERE tenant_id = %s
                        ORDER BY spent_at DESC, id DESC
                        LIMIT %s OFFSET %s
                        """,
                        (tenant_id, limit, offset),
                    )
                    rows = cur.fetchall()
            return [
                {
                    "id": row[0],
                    "channel": row[1],
                    "campaign": row[2],
                    "currency": row[3],
                    "amount": float(row[4]),
                    "notes": row[5],
                    "spent_at": row[6].isoformat(),
                    "created_at": row[7].isoformat(),
                }
                for row in rows
            ]

        with self._lock:
            items = [s.copy() for s in self._spend_memory if s.get("tenant_id") == tenant_id]
        items.sort(key=lambda r: str(r.get("spent_at", "")), reverse=True)
        return items[offset : offset + limit]

    def load_spend(self, tenant_id: str, window_days: int) -> list[dict[str, Any]]:
        self.ensure_tables()
        if self._db_ready_fn():
            with psycopg.connect(self._db_dsn_fn()) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT id, channel, campaign, currency, amount, notes, spent_at, created_at
                        FROM revenue_attribution_spend
                        WHERE tenant_id = %s AND spent_at >= %s
                        ORDER BY spent_at DESC, id DESC
                        """,
                        (tenant_id, datetime.now(UTC) - timedelta(days=window_days)),
                    )
                    rows = cur.fetchall()
            return [
                {
                    "id": row[0],
                    "channel": row[1],
                    "campaign": row[2],
                    "currency": row[3],
                    "amount": float(row[4]),
                    "notes": row[5],
                    "spent_at": row[6].isoformat(),
                    "created_at": row[7].isoformat(),
                }
                for row in rows
            ]

        with self._lock:
            items = [s.copy() for s in self._spend_memory if s.get("tenant_id") == tenant_id]
        items.sort(key=lambda r: str(r.get("spent_at", "")), reverse=True)
        return items

    def create_touchpoint(self, tenant_id: str, payload: RevenueTouchpointRequest) -> dict[str, Any]:
        touchpoint_key = f"tp_{uuid.uuid4().hex[:14]}"
        source = payload.utm_source or payload.platform
        medium = payload.utm_medium or "social"
        content = payload.utm_content or payload.post_id
        tracked_url = _inject_utm(payload.destination_url, source, medium, payload.campaign, content, touchpoint_key)
        item: dict[str, Any] = {
            "touchpoint_key": touchpoint_key,
            "tenant_id": tenant_id,
            "post_id": payload.post_id,
            "platform": payload.platform,
            "campaign": payload.campaign,
            "source": source,
            "medium": medium,
            "content": content,
            "destination_url": payload.destination_url,
            "tracked_url": tracked_url,
            "created_at": datetime.now(UTC).isoformat(),
        }

        self.ensure_tables()
        if self._db_ready_fn():
            with psycopg.connect(self._db_dsn_fn()) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO revenue_attribution_touchpoints (
                            tenant_id, touchpoint_key, post_id, platform, campaign, source, medium, content, destination_url, tracked_url
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        RETURNING id, created_at
                        """,
                        (
                            tenant_id,
                            touchpoint_key,
                            payload.post_id,
                            payload.platform,
                            payload.campaign,
                            source,
                            medium,
                            content,
                            payload.destination_url,
                            tracked_url,
                        ),
                    )
                    row = cur.fetchone()
                conn.commit()
            if row:
                item["id"] = int(row[0])
                item["created_at"] = row[1].isoformat()
            return item

        with self._lock:
            item["id"] = len(self._touchpoints_memory) + 1
            self._touchpoints_memory.append(item)
        return item

    def list_touchpoints(self, tenant_id: str, limit: int, offset: int) -> list[dict[str, Any]]:
        self.ensure_tables()
        if self._db_ready_fn():
            with psycopg.connect(self._db_dsn_fn()) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT id, touchpoint_key, post_id, platform, campaign, source, medium, content, destination_url, tracked_url, created_at
                        FROM revenue_attribution_touchpoints
                        WHERE tenant_id = %s
                        ORDER BY created_at DESC, id DESC
                        LIMIT %s OFFSET %s
                        """,
                        (tenant_id, limit, offset),
                    )
                    rows = cur.fetchall()
            return [
                {
                    "id": row[0],
                    "touchpoint_key": row[1],
                    "post_id": row[2],
                    "platform": row[3],
                    "campaign": row[4],
                    "source": row[5],
                    "medium": row[6],
                    "content": row[7],
                    "destination_url": row[8],
                    "tracked_url": row[9],
                    "created_at": row[10].isoformat(),
                }
                for row in rows
            ]

        with self._lock:
            items = [t.copy() for t in self._touchpoints_memory if t.get("tenant_id") == tenant_id]
        items.sort(key=lambda r: str(r.get("created_at", "")), reverse=True)
        return items[offset : offset + limit]

    def persist_conversion(
        self,
        *,
        tenant_id: str,
        provider: str,
        external_order_id: str,
        amount: float,
        currency: str,
        event_type: str,
        customer_ref: str | None,
        touchpoint_keys: list[str],
        raw_payload: dict[str, Any],
    ) -> dict[str, Any]:
        normalized_keys = sorted({k for k in touchpoint_keys if k})
        record: dict[str, Any] = {
            "tenant_id": tenant_id,
            "provider": provider,
            "external_order_id": external_order_id,
            "amount": round(float(amount), 2),
            "currency": currency.upper(),
            "event_type": event_type,
            "customer_ref": customer_ref,
            "touchpoint_keys": normalized_keys,
            "raw_payload": raw_payload,
            "received_at": datetime.now(UTC).isoformat(),
        }

        self.ensure_tables()
        if self._db_ready_fn():
            with psycopg.connect(self._db_dsn_fn()) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO revenue_attribution_conversions (
                            tenant_id, provider, external_order_id, customer_ref, currency, amount, event_type, touchpoint_keys, raw_payload
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)
                        ON CONFLICT (tenant_id, provider, external_order_id, event_type)
                        DO UPDATE SET
                            customer_ref = EXCLUDED.customer_ref,
                            currency = EXCLUDED.currency,
                            amount = EXCLUDED.amount,
                            touchpoint_keys = EXCLUDED.touchpoint_keys,
                            raw_payload = EXCLUDED.raw_payload,
                            received_at = NOW()
                        RETURNING id, received_at
                        """,
                        (
                            tenant_id,
                            provider,
                            external_order_id,
                            customer_ref,
                            currency.upper(),
                            Decimal(str(round(float(amount), 2))),
                            event_type,
                            normalized_keys,
                            json.dumps(raw_payload),
                        ),
                    )
                    row = cur.fetchone()
                conn.commit()
            if row:
                record["id"] = int(row[0])
                record["received_at"] = row[1].isoformat()
            return record

        with self._lock:
            existing = next(
                (
                    c
                    for c in self._conversions_memory
                    if c.get("tenant_id") == tenant_id
                    and c.get("provider") == provider
                    and c.get("external_order_id") == external_order_id
                    and c.get("event_type") == event_type
                ),
                None,
            )
            if existing is not None:
                existing.update(record)
                return existing.copy()
            record["id"] = len(self._conversions_memory) + 1
            self._conversions_memory.append(record)
        return record

    def load_report_data(self, tenant_id: str, window_days: int) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
        self.ensure_tables()
        if self._db_ready_fn():
            with psycopg.connect(self._db_dsn_fn()) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT touchpoint_key, post_id, platform, campaign, source, medium, content
                        FROM revenue_attribution_touchpoints
                        WHERE tenant_id = %s
                        """,
                        (tenant_id,),
                    )
                    tp_rows = cur.fetchall()
                    cur.execute(
                        """
                        SELECT id, provider, external_order_id, amount, currency, event_type, touchpoint_keys, received_at
                        FROM revenue_attribution_conversions
                        WHERE tenant_id = %s AND received_at >= %s
                        ORDER BY received_at DESC, id DESC
                        """,
                        (tenant_id, datetime.now(UTC) - timedelta(days=window_days)),
                    )
                    conv_rows = cur.fetchall()
            touchpoints = {
                row[0]: {
                    "touchpoint_key": row[0],
                    "post_id": row[1],
                    "platform": row[2],
                    "campaign": row[3],
                    "source": row[4],
                    "medium": row[5],
                    "content": row[6],
                }
                for row in tp_rows
            }
            conversions = [
                {
                    "id": row[0],
                    "provider": row[1],
                    "external_order_id": row[2],
                    "amount": float(row[3]),
                    "currency": row[4],
                    "event_type": row[5],
                    "touchpoint_keys": list(row[6] or []),
                    "received_at": row[7].isoformat(),
                }
                for row in conv_rows
            ]
            return touchpoints, conversions

        with self._lock:
            touchpoints = {
                str(t.get("touchpoint_key")): t.copy()
                for t in self._touchpoints_memory
                if t.get("tenant_id") == tenant_id
            }
            conversions = [
                c.copy()
                for c in self._conversions_memory
                if c.get("tenant_id") == tenant_id
            ]
        conversions.sort(key=lambda c: str(c.get("received_at", "")), reverse=True)
        return touchpoints, conversions


def _resolve_tenant_id(x_tenant_id: str | None, payload: dict[str, Any]) -> str:
    if x_tenant_id and x_tenant_id.strip():
        return x_tenant_id.strip()
    payload_tenant = str(payload.get("tenant_id") or "").strip()
    if payload_tenant:
        return payload_tenant
    metadata = payload.get("metadata")
    if isinstance(metadata, dict):
        metadata_tenant = str(metadata.get("tenant_id") or "").strip()
        if metadata_tenant:
            return metadata_tenant
    return "tenant-demo"


def _verify_provider_signature(provider_lc: str, headers: Any, raw_body: bytes) -> None:
    if provider_lc == "stripe":
        secret = os.getenv("WEBHOOK_STRIPE_SECRET", "").strip()
        sig_header = headers.get("Stripe-Signature", "").strip()
        if secret and (not sig_header or not _verify_stripe_signature(secret, raw_body, sig_header)):
            raise HTTPException(status_code=401, detail="Invalid Stripe webhook signature.")
        return

    if provider_lc == "shopify":
        secret = os.getenv("WEBHOOK_SHOPIFY_SECRET", "").strip()
        sig_header = headers.get("X-Shopify-Hmac-Sha256", "").strip()
        if secret and (not sig_header or not _verify_base64_hmac(secret, raw_body, sig_header)):
            raise HTTPException(status_code=401, detail="Invalid Shopify webhook signature.")
        return

    if provider_lc == "woocommerce":
        secret = os.getenv("WEBHOOK_WOOCOMMERCE_SECRET", "").strip()
        sig_header = headers.get("X-Wc-Webhook-Signature", "").strip()
        if secret and (not sig_header or not _verify_base64_hmac(secret, raw_body, sig_header)):
            raise HTTPException(status_code=401, detail="Invalid WooCommerce webhook signature.")


def _build_report_response(
    *,
    tenant_id: str,
    window_days: int,
    touchpoints: dict[str, dict[str, Any]],
    conversions: list[dict[str, Any]],
) -> dict[str, Any]:
    total_revenue = 0.0
    attributed_revenue = 0.0
    by_post: dict[str, float] = {}
    by_channel: dict[str, float] = {}
    conversion_rows: list[dict[str, Any]] = []

    for conv in conversions:
        amount = float(conv.get("amount") or 0)
        total_revenue += amount
        keys = [str(k) for k in conv.get("touchpoint_keys", []) if str(k) in touchpoints]

        if not keys:
            conversion_rows.append(
                {
                    "conversion_id": conv.get("id"),
                    "provider": conv.get("provider"),
                    "external_order_id": conv.get("external_order_id"),
                    "amount": amount,
                    "touchpoints": [],
                    "shapley": {},
                }
            )
            continue

        post_ids = [str(touchpoints[k].get("post_id") or k) for k in keys]
        post_contrib = _shapley_contributions(post_ids, amount)
        attributed_revenue += amount
        for post_id, value in post_contrib.items():
            by_post[post_id] = by_post.get(post_id, 0.0) + value

        channel_keys = [str(touchpoints[k].get("source") or touchpoints[k].get("platform") or "unknown") for k in keys]
        channel_contrib = _shapley_contributions(channel_keys, amount)
        for channel, value in channel_contrib.items():
            by_channel[channel] = by_channel.get(channel, 0.0) + value

        conversion_rows.append(
            {
                "conversion_id": conv.get("id"),
                "provider": conv.get("provider"),
                "external_order_id": conv.get("external_order_id"),
                "amount": amount,
                "touchpoints": keys,
                "shapley": {k: round(v, 2) for k, v in post_contrib.items()},
            }
        )

    top_posts = [
        {"post_id": post_id, "attributed_revenue": round(revenue, 2)}
        for post_id, revenue in sorted(by_post.items(), key=lambda item: item[1], reverse=True)
    ]
    channels = [
        {"channel": channel, "attributed_revenue": round(revenue, 2)}
        for channel, revenue in sorted(by_channel.items(), key=lambda item: item[1], reverse=True)
    ]

    return {
        "status": "ok",
        "tenant_id": tenant_id,
        "window_days": window_days,
        "totals": {
            "conversions": len(conversions),
            "tracked_conversions": sum(1 for c in conversion_rows if c.get("touchpoints")),
            "revenue": round(total_revenue, 2),
            "attributed_revenue": round(attributed_revenue, 2),
            "unattributed_revenue": round(total_revenue - attributed_revenue, 2),
        },
        "channels": channels,
        "top_posts": top_posts,
        "conversions": conversion_rows[:100],
    }


def _roi_metrics(revenue: float, spend: float) -> dict[str, float]:
    safe_revenue = round(float(revenue), 2)
    safe_spend = round(float(spend), 2)
    net = round(safe_revenue - safe_spend, 2)
    roas = round((safe_revenue / safe_spend), 4) if safe_spend > 0 else 0.0
    roi_pct = round(((safe_revenue - safe_spend) / safe_spend) * 100.0, 2) if safe_spend > 0 else 0.0
    return {
        "revenue": safe_revenue,
        "spend": safe_spend,
        "net_profit": net,
        "roas": roas,
        "roi_pct": roi_pct,
    }


def _build_social_roi_summary(
    *,
    tenant_id: str,
    window_days: int,
    touchpoints: dict[str, dict[str, Any]],
    conversions: list[dict[str, Any]],
    spend_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    report = _build_report_response(
        tenant_id=tenant_id,
        window_days=window_days,
        touchpoints=touchpoints,
        conversions=conversions,
    )
    attributed_revenue = float(report.get("totals", {}).get("attributed_revenue") or 0.0)
    total_spend = sum(float(row.get("amount") or 0.0) for row in spend_rows)

    spend_by_channel: dict[str, float] = {}
    spend_by_campaign: dict[str, float] = {}
    for row in spend_rows:
        channel = str(row.get("channel") or "unknown").strip().lower() or "unknown"
        campaign = str(row.get("campaign") or "unassigned").strip() or "unassigned"
        amount = float(row.get("amount") or 0.0)
        spend_by_channel[channel] = spend_by_channel.get(channel, 0.0) + amount
        spend_by_campaign[campaign] = spend_by_campaign.get(campaign, 0.0) + amount

    channels: list[dict[str, Any]] = []
    revenue_channels = {
        str(item.get("channel") or "unknown").strip().lower() or "unknown": float(item.get("attributed_revenue") or 0.0)
        for item in report.get("channels", [])
    }
    all_channels = sorted(set(revenue_channels.keys()) | set(spend_by_channel.keys()))
    for channel in all_channels:
        channels.append(
            {
                "channel": channel,
                **_roi_metrics(revenue_channels.get(channel, 0.0), spend_by_channel.get(channel, 0.0)),
            }
        )

    campaign_revenue: dict[str, float] = {}
    for conv in conversions:
        amount = float(conv.get("amount") or 0.0)
        keys = [str(k) for k in conv.get("touchpoint_keys", []) if str(k) in touchpoints]
        if not keys:
            continue
        campaign_keys = [str(touchpoints[k].get("campaign") or "unassigned").strip() or "unassigned" for k in keys]
        for campaign, value in _shapley_contributions(campaign_keys, amount).items():
            campaign_revenue[campaign] = campaign_revenue.get(campaign, 0.0) + value

    campaigns: list[dict[str, Any]] = []
    all_campaigns = sorted(set(campaign_revenue.keys()) | set(spend_by_campaign.keys()))
    for campaign in all_campaigns:
        campaigns.append(
            {
                "campaign": campaign,
                **_roi_metrics(campaign_revenue.get(campaign, 0.0), spend_by_campaign.get(campaign, 0.0)),
            }
        )

    channels.sort(key=lambda item: item.get("revenue", 0.0), reverse=True)
    campaigns.sort(key=lambda item: item.get("revenue", 0.0), reverse=True)

    return {
        "status": "ok",
        "tenant_id": tenant_id,
        "window_days": window_days,
        "totals": {
            **_roi_metrics(attributed_revenue, total_spend),
            "tracked_conversions": report.get("totals", {}).get("tracked_conversions", 0),
            "touchpoints": len(touchpoints),
            "spend_entries": len(spend_rows),
            "tracking_coverage_pct": round(
                (
                    float(report.get("totals", {}).get("tracked_conversions") or 0)
                    / float(report.get("totals", {}).get("conversions") or 1)
                )
                * 100.0,
                2,
            )
            if float(report.get("totals", {}).get("conversions") or 0) > 0
            else 0.0,
        },
        "channels": channels,
        "campaigns": campaigns,
        "attribution": {
            "totals": report.get("totals", {}),
            "top_posts": report.get("top_posts", []),
            "channels": report.get("channels", []),
        },
    }


def _register_touchpoint_routes(
    *,
    router: APIRouter,
    store: _RevenueAttributionStore,
    enforce_rate_limit: Callable[[str, int, int], None],
) -> None:
    @router.post("/analytics/revenue-attribution/touchpoints", responses={422: {"description": "Invalid destination URL."}})
    def create_touchpoint(payload: RevenueTouchpointRequest, auth: AuthDep) -> dict[str, Any]:
        enforce_rate_limit(f"{auth.tenant_id}:revenue:touchpoints:create", 180, 60)
        touchpoint = store.create_touchpoint(auth.tenant_id, payload)
        return {"status": "ok", "tenant_id": auth.tenant_id, "touchpoint": touchpoint}

    @router.get("/analytics/revenue-attribution/touchpoints")
    def list_touchpoints(
        auth: AuthDep,
        limit: Annotated[int, Query(ge=1, le=200)] = 50,
        offset: Annotated[int, Query(ge=0)] = 0,
    ) -> dict[str, Any]:
        enforce_rate_limit(f"{auth.tenant_id}:revenue:touchpoints:list", 180, 60)
        items = store.list_touchpoints(auth.tenant_id, limit, offset)
        return {"status": "ok", "tenant_id": auth.tenant_id, "count": len(items), "items": items}


def _register_conversion_routes(
    *,
    router: APIRouter,
    store: _RevenueAttributionStore,
    enforce_rate_limit: Callable[[str, int, int], None],
) -> None:
    @router.post("/analytics/revenue-attribution/conversions/ingest", responses={400: {"description": "Unsupported provider."}})
    def ingest_conversion(payload: ConversionIngestRequest, auth: AuthDep) -> dict[str, Any]:
        provider = payload.provider.strip().lower()
        if provider not in _PROVIDER_SET:
            raise HTTPException(status_code=400, detail=f"Unsupported provider {provider}. Use one of {_PROVIDER_SET}.")
        enforce_rate_limit(f"{auth.tenant_id}:revenue:conversions:ingest", 240, 60)
        record = store.persist_conversion(
            tenant_id=auth.tenant_id,
            provider=provider,
            external_order_id=payload.external_order_id,
            amount=payload.amount,
            currency=payload.currency,
            event_type=payload.event_type,
            customer_ref=payload.customer_ref,
            touchpoint_keys=payload.touchpoint_keys,
            raw_payload=payload.raw_payload,
        )
        return {"status": "ok", "tenant_id": auth.tenant_id, "conversion": record}


def _register_webhook_routes(
    *,
    router: APIRouter,
    store: _RevenueAttributionStore,
    enforce_rate_limit: Callable[[str, int, int], None],
) -> None:
    @router.post(
        "/analytics/revenue-attribution/webhooks/{provider}",
        responses={
            400: {"description": "Invalid provider or payload."},
            401: {"description": "Invalid provider webhook signature."},
        },
    )
    async def ingest_provider_webhook(
        provider: str,
        request: Request,
        x_tenant_id: Annotated[str | None, Header(alias="X-Tenant-Id")] = None,
    ) -> dict[str, Any]:
        provider_lc = provider.strip().lower()
        if provider_lc not in _PROVIDER_SET:
            raise HTTPException(status_code=400, detail=f"Unknown provider: {provider}.")

        enforce_rate_limit(f"public:revenue:webhook:{provider_lc}", 600, 60)
        raw_body = await request.body()
        _verify_provider_signature(provider_lc, request.headers, raw_body)

        try:
            payload = json.loads(raw_body.decode("utf-8")) if raw_body else {}
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"Invalid JSON payload: {exc}") from exc

        tenant_id = _resolve_tenant_id(x_tenant_id, payload)
        external_order_id, amount, currency, event_type, customer_ref, inferred_touchpoints = _extract_conversion(
            provider_lc, payload
        )

        if amount <= 0:
            return {
                "status": "ignored",
                "tenant_id": tenant_id,
                "reason": "non-positive amount",
                "provider": provider_lc,
                "external_order_id": external_order_id,
            }

        record = store.persist_conversion(
            tenant_id=tenant_id,
            provider=provider_lc,
            external_order_id=external_order_id,
            amount=amount,
            currency=currency,
            event_type=event_type,
            customer_ref=customer_ref,
            touchpoint_keys=inferred_touchpoints,
            raw_payload=payload,
        )
        return {"status": "accepted", "tenant_id": tenant_id, "conversion": record}


def _register_report_route(
    *,
    router: APIRouter,
    store: _RevenueAttributionStore,
    enforce_rate_limit: Callable[[str, int, int], None],
) -> None:
    @router.get("/analytics/revenue-attribution/report")
    def revenue_report(
        auth: AuthDep,
        window_days: Annotated[int, Query(ge=1, le=365)] = 90,
    ) -> dict[str, Any]:
        enforce_rate_limit(f"{auth.tenant_id}:revenue:report", 120, 60)
        touchpoints, conversions = store.load_report_data(auth.tenant_id, window_days)
        return _build_report_response(
            tenant_id=auth.tenant_id,
            window_days=window_days,
            touchpoints=touchpoints,
            conversions=conversions,
        )


def _register_social_roi_routes(
    *,
    router: APIRouter,
    store: _RevenueAttributionStore,
    enforce_rate_limit: Callable[[str, int, int], None],
) -> None:
    @router.post("/analytics/social-roi/spend")
    def record_spend(payload: SocialSpendRequest, auth: AuthDep) -> dict[str, Any]:
        enforce_rate_limit(f"{auth.tenant_id}:social-roi:spend:create", 180, 60)
        item = store.record_spend(auth.tenant_id, payload)
        return {"status": "ok", "tenant_id": auth.tenant_id, "spend": item}

    @router.get("/analytics/social-roi/spend")
    def list_spend(
        auth: AuthDep,
        limit: Annotated[int, Query(ge=1, le=200)] = 50,
        offset: Annotated[int, Query(ge=0)] = 0,
    ) -> dict[str, Any]:
        enforce_rate_limit(f"{auth.tenant_id}:social-roi:spend:list", 180, 60)
        items = store.list_spend(auth.tenant_id, limit, offset)
        return {"status": "ok", "tenant_id": auth.tenant_id, "count": len(items), "items": items}

    @router.post("/analytics/social-roi/calculator")
    def roi_calculator(payload: SocialRoiCalculatorRequest, auth: AuthDep) -> dict[str, Any]:
        enforce_rate_limit(f"{auth.tenant_id}:social-roi:calculator", 240, 60)
        total_spend = (
            float(payload.paid_social_spend)
            + float(payload.team_cost)
            + float(payload.tools_cost)
            + float(payload.agency_cost)
        )
        breakdown = {
            "paid_social_spend": round(float(payload.paid_social_spend), 2),
            "team_cost": round(float(payload.team_cost), 2),
            "tools_cost": round(float(payload.tools_cost), 2),
            "agency_cost": round(float(payload.agency_cost), 2),
        }
        return {
            "status": "ok",
            "tenant_id": auth.tenant_id,
            "input": {
                "attributed_revenue": round(float(payload.attributed_revenue), 2),
                **breakdown,
            },
            "totals": _roi_metrics(float(payload.attributed_revenue), total_spend),
        }

    @router.get("/analytics/social-roi/summary")
    def roi_summary(
        auth: AuthDep,
        window_days: Annotated[int, Query(ge=1, le=365)] = 90,
    ) -> dict[str, Any]:
        enforce_rate_limit(f"{auth.tenant_id}:social-roi:summary", 120, 60)
        touchpoints, conversions = store.load_report_data(auth.tenant_id, window_days)
        spend_rows = store.load_spend(auth.tenant_id, window_days)
        return _build_social_roi_summary(
            tenant_id=auth.tenant_id,
            window_days=window_days,
            touchpoints=touchpoints,
            conversions=conversions,
            spend_rows=spend_rows,
        )


def _shapley_contributions(players: list[str], revenue: float) -> dict[str, float]:
    unique_players = sorted({p for p in players if p})
    n = len(unique_players)
    if n == 0:
        return {}
    if n > 8:
        split = revenue / n
        return dict.fromkeys(unique_players, split)

    n_fact = math.factorial(n)

    def _value(coalition_size: int) -> float:
        return revenue * (coalition_size / n)

    out: dict[str, float] = {}
    for idx, player in enumerate(unique_players):
        others = [p for i, p in enumerate(unique_players) if i != idx]
        score = 0.0
        for k in range(len(others) + 1):
            for _ in itertools.combinations(others, k):
                weight = (math.factorial(k) * math.factorial(n - k - 1)) / n_fact
                marginal = _value(k + 1) - _value(k)
                score += weight * marginal
        out[player] = score
    return out


def create_revenue_attribution_router(
    *,
    enforce_rate_limit: Callable[[str, int, int], None],
    touchpoints_memory: list[dict[str, Any]],
    conversions_memory: list[dict[str, Any]],
    spend_memory: list[dict[str, Any]],
    db_ready_fn: Callable[[], bool],
    db_dsn_fn: Callable[[], str],
) -> APIRouter:
    router = APIRouter()
    store = _RevenueAttributionStore(
        touchpoints_memory=touchpoints_memory,
        conversions_memory=conversions_memory,
        spend_memory=spend_memory,
        db_ready_fn=db_ready_fn,
        db_dsn_fn=db_dsn_fn,
    )
    _register_touchpoint_routes(router=router, store=store, enforce_rate_limit=enforce_rate_limit)
    _register_conversion_routes(router=router, store=store, enforce_rate_limit=enforce_rate_limit)
    _register_webhook_routes(router=router, store=store, enforce_rate_limit=enforce_rate_limit)
    _register_report_route(router=router, store=store, enforce_rate_limit=enforce_rate_limit)
    _register_social_roi_routes(router=router, store=store, enforce_rate_limit=enforce_rate_limit)
    return router
