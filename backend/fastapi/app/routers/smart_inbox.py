# pyright: reportUnusedFunction=false
"""
Smart Inbox — SproutSocial Blueprint §3
ADDED: Unified social engagement hub aggregating inbound DMs, comments, mentions,
and reviews. Features AI message classification, sentiment detection, team assignment,
collision-prevention locking, internal notes, and a saved-replies template library.
NO duplication: separate from the existing notifications system (outbound/internal) and
the social_listening feed (keyword monitoring). This module handles INBOUND engagement.
"""

import asyncio
import hashlib
import os
import threading
import time
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from ..deps import AuthContext, require_auth
from ..integrations.vendor_manager import get_vendor_manager

AuthDep = Annotated[AuthContext, Depends(require_auth)]

MESSAGE_NOT_FOUND = 'Inbox message not found.'
REPLY_NOT_FOUND = 'Saved reply not found.'
LOCK_NOT_HELD = 'Lock not held by caller or already released.'

# ADDED: AI classification categories (§3.1.2 Smart Inbox AI Features)
MESSAGE_TYPES = {'question', 'complaint', 'compliment', 'spam', 'conversation', 'crisis'}
SENTIMENT_VALUES = {'positive', 'neutral', 'negative'}
MESSAGE_STATUSES = {'pending', 'in_progress', 'complete', 'flagged', 'requires_approval'}
NETWORK_VALUES = {'facebook', 'instagram', 'x', 'linkedin', 'tiktok', 'youtube', 'whatsapp', 'google', 'reddit'}
SOURCE_TYPES = {'dm', 'comment', 'mention', 'review', 'story_reply', 'live_comment', 'ad_comment'}

_NETWORK_VENDOR_MAP = {
    'facebook': 'meta_graph_api',
    'instagram': 'meta_graph_api',
    'linkedin': 'linkedin_api',
    'twitter': 'twitter_api',
    'x': 'twitter_api',
    'tiktok': 'tiktok_api',
    'reddit': 'reddit_api',
    'youtube': 'youtube_api',
}
vendor_manager = get_vendor_manager()

# ── Request models ──────────────────────────────────────────────────────────────

class InboxMessageIngestRequest(BaseModel):
    """ADDED: Ingest an inbound message into the Smart Inbox."""
    network: str = Field(min_length=2, max_length=40)
    source_type: str = Field(default='dm', min_length=2, max_length=40, description='dm/comment/mention/review/story_reply')
    author_handle: str = Field(min_length=1, max_length=120)
    author_display_name: str | None = Field(default=None, max_length=160)
    author_follower_count: int = Field(default=0, ge=0, le=50_000_000)
    text: str = Field(min_length=1, max_length=5000)
    external_message_id: str | None = Field(default=None, max_length=200, description='Original platform message ID for dedup.')
    parent_message_id: str | None = Field(default=None, max_length=200, description='Thread parent ID for threaded view.')
    # ADDED: optional override — if sender is known to be a CRM contact
    crm_contact_id: str | None = Field(default=None, max_length=200)


class MessageUpdateRequest(BaseModel):
    """ADDED: Update message assignment, status, or tags."""
    assigned_to: str | None = Field(default=None, max_length=160, description='Team member handle to assign message to.')
    status: str | None = Field(default=None, max_length=40, description='pending/in_progress/complete/flagged/requires_approval')
    tags: list[str] | None = Field(default=None, max_length=20, description='Custom labels e.g. Product Feedback, Shipping Issue')
    due_at: str | None = Field(default=None, max_length=40, description='ISO datetime for assignment due date.')


class InternalNoteRequest(BaseModel):
    """ADDED: Add an internal team note to a message (never sent to the customer)."""
    author: str = Field(min_length=1, max_length=160)
    note: str = Field(min_length=1, max_length=2000)


class LockRequest(BaseModel):
    """ADDED: Acquire collision-prevention lock before composing a reply."""
    locked_by: str = Field(min_length=1, max_length=160, description='Team member handle acquiring the lock.')


class SavedReplyRequest(BaseModel):
    """ADDED: Create a pre-approved reply template for the saved replies library."""
    title: str = Field(min_length=1, max_length=120)
    body: str = Field(min_length=1, max_length=4000)
    # ADDED: tags for organising and searching the library
    tags: list[str] = Field(default_factory=list, max_length=10)
    networks: list[str] = Field(default_factory=list, max_length=10, description='Applicable networks; empty = all.')


class SavedReplyUpdateRequest(BaseModel):
    """ADDED: Update a saved reply."""
    title: str | None = Field(default=None, max_length=120)
    body: str | None = Field(default=None, max_length=4000)
    tags: list[str] | None = Field(default=None, max_length=10)
    networks: list[str] | None = Field(default=None, max_length=10)


class AutoResponseRequest(BaseModel):
    """Execute an auto-response using a saved reply or suggested reply."""
    saved_reply_id: int | None = Field(default=None, ge=1)
    suggestion_index: int | None = Field(default=None, ge=0, le=2)
    responder: str = Field(min_length=1, max_length=160)
    require_approval: bool = Field(default=False)


class ResponseApprovalRequest(BaseModel):
    """Approve and deliver a previously staged auto-response."""
    approver: str = Field(min_length=1, max_length=160)
    note: str | None = Field(default=None, max_length=500)


class ResponseRejectionRequest(BaseModel):
    """Reject a previously staged auto-response."""
    reviewer: str = Field(min_length=1, max_length=160)
    note: str | None = Field(default=None, max_length=500)


class ResponseReplayRequest(BaseModel):
    """Retry a failed outbound auto-response delivery from the inbox DLQ."""
    operator: str = Field(min_length=1, max_length=160)
    note: str | None = Field(default=None, max_length=500)


class DeliveryFailureResolveRequest(BaseModel):
    """Resolve a failed outbound inbox delivery for manual follow-up."""
    operator: str = Field(min_length=1, max_length=160)
    note: str | None = Field(default=None, max_length=500)


class DeliveryFailureBulkResolveRequest(BaseModel):
    """Resolve multiple failed outbound deliveries for manual follow-up."""
    failure_ids: list[int] = Field(min_length=1, max_length=100)
    operator: str = Field(min_length=1, max_length=160)
    note: str | None = Field(default=None, max_length=500)


class DeliveryFailureBulkReplayRequest(BaseModel):
    """Replay multiple failed outbound deliveries in one operation."""
    failure_ids: list[int] = Field(min_length=1, max_length=50)
    operator: str = Field(min_length=1, max_length=160)
    note: str | None = Field(default=None, max_length=500)


class DeliveryFailureReplayPendingRequest(BaseModel):
    """Replay a limited batch of pending delivery failures."""
    operator: str = Field(min_length=1, max_length=160)
    note: str | None = Field(default=None, max_length=500)
    limit: int = Field(default=25, ge=1, le=50)
    network: str | None = Field(default=None, max_length=40)


# ── AI classification stub ──────────────────────────────────────────────────────

def _ai_classify(text: str) -> tuple[str, str, float]:
    """
    ADDED: Deterministic AI classification stub.
    Returns (message_type, sentiment, confidence).
    In production this would call Sprout's BERT-fine-tuned NLP model (§18.4).
    """
    lowered = text.lower()
    # Sentiment
    positive_words = {'thank', 'love', 'great', 'awesome', 'excellent', 'fantastic', 'perfect', 'amazing', 'good', 'helpful'}
    negative_words = {'hate', 'terrible', 'awful', 'broken', 'wrong', 'bad', 'worst', 'disappointed', 'refund', 'cancel'}
    crisis_words = {'recall', 'lawsuit', 'safety', 'dangerous', 'legal', 'sue', 'fda', 'scandal'}
    spam_words = {'click here', 'free money', 'buy now', 'limited offer', 'winner', 'congratulations you won'}

    pos = sum(1 for w in positive_words if w in lowered)
    neg = sum(1 for w in negative_words if w in lowered)

    if any(w in lowered for w in spam_words):
        return 'spam', 'neutral', 0.91
    if any(w in lowered for w in crisis_words):
        return 'crisis', 'negative', 0.87
    if '?' in text:
        sentiment = 'negative' if neg > pos else 'neutral'
        return 'question', sentiment, 0.82
    if neg > pos:
        return 'complaint', 'negative', 0.79
    if pos > neg:
        return 'compliment', 'positive', 0.84
    return 'conversation', 'neutral', 0.68


def _priority_score(message_type: str, sentiment: str, follower_count: int) -> int:
    """
    ADDED: Message Priority Scoring (§3.1.2).
    Higher scores = higher priority for team response.
    """
    score = 0
    if message_type == 'crisis':
        score += 100
    elif message_type == 'complaint':
        score += 50
    elif message_type == 'question':
        score += 30
    elif message_type == 'compliment':
        score += 10
    if sentiment == 'negative':
        score += 20
    # Follower count tier boost
    if follower_count >= 100_000:
        score += 40
    elif follower_count >= 10_000:
        score += 20
    elif follower_count >= 1_000:
        score += 10
    return score


def _suggested_replies(message_type: str) -> list[str]:
    """
    ADDED: Suggested Replies stub (§3.1.2).
    Returns 3 ready-to-send reply suggestions based on message type.
    Production: RAG system + GPT-4o refinement (§18.4).
    """
    if message_type == 'question':
        return [
            'Thanks for reaching out! Let me look into that for you and get back to you shortly.',
            'Great question! I\'ll connect you with the right person to help. Can I get your email?',
            'Happy to help! Could you share a bit more detail so we can assist you quickly?',
        ]
    if message_type == 'complaint':
        return [
            'We\'re so sorry to hear about this experience. This is definitely not the standard we hold ourselves to.',
            'Thank you for letting us know. We take this seriously and want to make it right. Please DM us your order details.',
            'I apologise for the inconvenience caused. Let me escalate this to our team right away.',
        ]
    if message_type == 'compliment':
        return [
            'Thank you so much! This genuinely makes our day. We\'ll share this with the team! 🙌',
            'We really appreciate you taking the time to share this — it means a lot to us!',
            'Hearing this puts a huge smile on our faces. Thank you for your support! ❤️',
        ]
    if message_type == 'crisis':
        return [
            'We take this very seriously and our team is looking into it immediately. Please DM us your contact details.',
            'Thank you for bringing this to our attention. We are investigating urgently and will update you shortly.',
            'We sincerely apologise. A senior team member will reach out to you directly within the hour.',
        ]
    return [
        'Thanks for your message! We\'ll get back to you as soon as possible.',
        'Hi there! Thanks for reaching out. How can we help you today?',
        'Thanks for connecting with us! A team member will be in touch shortly.',
    ]


# ── Router factory ──────────────────────────────────────────────────────────────

def create_smart_inbox_router(  # NOSONAR
    *,
    enforce_rate_limit: Callable[[str, int, int], None],
    audit_log_memory: list[dict[str, Any]],
    messages_memory: list[dict[str, Any]],
    notes_memory: list[dict[str, Any]],
    locks_memory: list[dict[str, Any]],
    saved_replies_memory: list[dict[str, Any]],
    delivery_failures_memory: list[dict[str, Any]],
    delivery_replay_runs_memory: list[dict[str, Any]],
) -> APIRouter:
    """
    Create the Smart Inbox router (SproutSocial §3).
    No duplication: notifications.py handles outbound/internal notifications;
    social_listening handles keyword monitoring. This handles INBOUND social engagement.
    """
    router = APIRouter()
    _lock = threading.Lock()

    def _audit(tenant_id: str, action: str, ref_id: int | None = None) -> None:
        with _lock:
            audit_log_memory.append({
                'id': len(audit_log_memory) + 1,
                'tenant_id': tenant_id,
                'action': action,
                'ref_id': ref_id,
                'created_at': datetime.now(UTC).isoformat(),
                'source': 'smart-inbox-router',
            })

    def _get_message(tenant_id: str, message_id: int) -> dict[str, Any] | None:
        with _lock:
            return next(
                (m for m in messages_memory if m.get('tenant_id') == tenant_id and m.get('id') == message_id),
                None,
            )

    def _resolve_saved_reply(tenant_id: str, reply_id: int) -> dict[str, Any] | None:
        with _lock:
            return next(
                (r for r in saved_replies_memory if r.get('tenant_id') == tenant_id and r.get('id') == reply_id),
                None,
            )

    def _resolve_delivery_target(network: str) -> tuple[str, str]:
        network_key = network.strip().lower()
        vendor_id = _NETWORK_VENDOR_MAP.get(network_key)
        if vendor_id is None:
            raise HTTPException(status_code=422, detail=f'Network {network_key} does not support outbound inbox delivery yet')

        network_env_key = network_key.upper().replace('-', '_')
        endpoint = os.getenv(f'INBOX_REPLY_ENDPOINT_{network_env_key}', '').strip()
        if not endpoint:
            endpoint = '/messages/reply/{message_id}'
        if not endpoint.startswith('/'):
            endpoint = f'/{endpoint}'
        return vendor_id, endpoint

    def _delivery_readiness_for(network: str) -> dict[str, Any]:
        network_key = network.strip().lower()
        vendor_id = _NETWORK_VENDOR_MAP.get(network_key)
        if vendor_id is None:
            return {
                'delivery_vendor': None,
                'delivery_ready': False,
                'delivery_blocker': f'Unsupported network: {network_key}',
            }
        credentials = vendor_manager.get_credentials(vendor_id)
        if credentials is None:
            return {
                'delivery_vendor': vendor_id,
                'delivery_ready': False,
                'delivery_blocker': f'Missing vendor credentials for {vendor_id}',
            }
        return {
            'delivery_vendor': vendor_id,
            'delivery_ready': True,
            'delivery_blocker': None,
        }

    def _record_replay_run(
        *,
        tenant_id: str,
        operator: str,
        note: str | None,
        requested_limit: int,
        selected_failure_ids: list[int],
        network_filter: str | None,
        replay_result: dict[str, Any],
        duration_ms: int,
    ) -> dict[str, Any]:
        now_iso = datetime.now(UTC).isoformat()
        with _lock:
            run_record = {
                'id': len(delivery_replay_runs_memory) + 1,
                'tenant_id': tenant_id,
                'operator': operator,
                'note': note,
                'requested_limit': requested_limit,
                'selected_count': len(selected_failure_ids),
                'selected_failure_ids': selected_failure_ids,
                'network_filter': network_filter,
                'count': int(replay_result.get('count') or 0),
                'replayed_count': int(replay_result.get('replayed_count') or 0),
                'failed_count': int(replay_result.get('failed_count') or 0),
                'skipped_count': int(replay_result.get('skipped_count') or 0),
                'not_found_count': int(replay_result.get('not_found_count') or 0),
                'duration_ms': duration_ms,
                'created_at': now_iso,
            }
            delivery_replay_runs_memory.append(run_record)
        return run_record.copy()

    def _percentile(values: list[int], percentile: float) -> float:
        if not values:
            return 0.0
        ordered = sorted(values)
        if len(ordered) == 1:
            return float(ordered[0])
        rank = (len(ordered) - 1) * percentile
        lower = int(rank)
        upper = min(lower + 1, len(ordered) - 1)
        if lower == upper:
            return float(ordered[lower])
        weight = rank - lower
        return float(ordered[lower] + (ordered[upper] - ordered[lower]) * weight)

    def _env_float(name: str, default: float, *, minimum: float | None = None, maximum: float | None = None) -> float:
        raw = os.getenv(name)
        if raw is None:
            return default
        try:
            parsed = float(raw)
        except ValueError:
            return default
        if minimum is not None and parsed < minimum:
            return minimum
        if maximum is not None and parsed > maximum:
            return maximum
        return parsed

    def _env_int(name: str, default: int, *, minimum: int | None = None, maximum: int | None = None) -> int:
        raw = os.getenv(name)
        if raw is None:
            return default
        try:
            parsed = int(raw)
        except ValueError:
            return default
        if minimum is not None and parsed < minimum:
            return minimum
        if maximum is not None and parsed > maximum:
            return maximum
        return parsed

    def _append_delivery_failure(
        tenant_id: str,
        *,
        message_id: int,
        network: str,
        vendor_id: str,
        endpoint: str,
        payload: dict[str, Any],
        errors: list[str],
    ) -> dict[str, Any]:
        with _lock:
            record = {
                'id': len(delivery_failures_memory) + 1,
                'tenant_id': tenant_id,
                'message_id': message_id,
                'network': network,
                'vendor_id': vendor_id,
                'endpoint': endpoint,
                'payload': payload,
                'errors': errors,
                'status': 'pending_retry',
                'created_at': datetime.now(UTC).isoformat(),
            }
            delivery_failures_memory.append(record)
            return record.copy()

    def _update_delivery_failure(
        tenant_id: str,
        failure_id: int,
        **updates: Any,
    ) -> dict[str, Any] | None:
        with _lock:
            failure = next(
                (
                    item for item in delivery_failures_memory
                    if item.get('tenant_id') == tenant_id and int(item.get('id') or 0) == failure_id
                ),
                None,
            )
            if failure is None:
                return None
            failure.update(updates)
            return failure.copy()

    def _build_delivery_idempotency_key(tenant_id: str, message_id: int, response_text: str) -> str:
        digest = hashlib.sha256(f'{tenant_id}:{message_id}:{response_text}'.encode()).hexdigest()[:24]
        return f'inbox-reply:{tenant_id}:{message_id}:{digest}'

    async def _attempt_outbound_delivery(
        *,
        vendor_id: str,
        endpoint: str,
        request_payload: dict[str, Any],
        idempotency_key: str,
    ) -> tuple[dict[str, Any] | None, list[str], int]:
        max_retries = max(1, min(int(os.getenv('INBOX_DELIVERY_MAX_RETRIES', '3') or '3'), 6))
        backoff_seconds = max(0.0, float(os.getenv('INBOX_DELIVERY_BACKOFF_SECONDS', '1') or '1'))
        vendor_response: dict[str, Any] | None = None
        delivery_errors: list[str] = []

        for attempt in range(1, max_retries + 1):
            try:
                vendor_response = await vendor_manager.make_request(
                    vendor_id,
                    'POST',
                    endpoint,
                    headers={'Idempotency-Key': idempotency_key},
                    json_data=request_payload,
                )
                return vendor_response, delivery_errors, attempt
            except Exception as exc:
                delivery_errors.append(f'attempt {attempt}: {exc}')
                if attempt < max_retries and backoff_seconds > 0:
                    await asyncio.sleep(backoff_seconds * (2 ** (attempt - 1)))

        return None, delivery_errors, max_retries

    def _build_alerts(tenant_id: str) -> list[dict[str, Any]]:
        with _lock:
            tenant_messages = [m.copy() for m in messages_memory if m.get('tenant_id') == tenant_id]
        alerts: list[dict[str, Any]] = []

        def _severity_for(message: dict[str, Any]) -> str:
            if message.get('message_type') == 'crisis':
                return 'critical'
            if int(message.get('priority_score', 0)) >= 80:
                return 'high'
            return 'medium'

        def _sort_rank(item: dict[str, Any]) -> tuple[int, int]:
            severity = str(item.get('severity', 'medium'))
            if severity == 'critical':
                severity_rank = 0
            elif severity == 'high':
                severity_rank = 1
            else:
                severity_rank = 2
            return severity_rank, -int(item.get('priority_score') or 0)

        for message in tenant_messages:
            if message.get('source_type') != 'mention' and int(message.get('priority_score', 0)) < 60:
                continue
            severity = _severity_for(message)
            alerts.append({
                'message_id': message.get('id'),
                'network': message.get('network'),
                'source_type': message.get('source_type'),
                'author_handle': message.get('author_handle'),
                'message_type': message.get('message_type'),
                'sentiment': message.get('sentiment'),
                'priority_score': message.get('priority_score'),
                'severity': severity,
                'text_preview': str(message.get('text', ''))[:160],
                'created_at': message.get('created_at'),
            })
        alerts.sort(key=_sort_rank)
        return alerts

    # ── Message ingestion ───────────────────────────────────────────────────────

    @router.post('/inbox/messages')
    def ingest_message(payload: InboxMessageIngestRequest, auth: AuthDep) -> dict[str, Any]:
        """
        ADDED: Ingest an inbound social message into the Smart Inbox.
        Applies AI classification, sentiment detection, and priority scoring automatically.
        Deduplicates by external_message_id to avoid double-ingestion from webhooks.
        """
        enforce_rate_limit(f'{auth.tenant_id}:inbox:ingest', 600, 60)
        network = payload.network.strip().lower()
        source_type = payload.source_type.strip().lower()

        # Dedup by external_message_id if provided
        if payload.external_message_id:
            with _lock:
                existing = next(
                    (
                        m for m in messages_memory
                        if m.get('tenant_id') == auth.tenant_id
                        and m.get('external_message_id') == payload.external_message_id
                    ),
                    None,
                )
            if existing:
                return {'status': 'ok', 'tenant_id': auth.tenant_id, 'message': existing.copy(), 'created': False}

        # ADDED: AI classification (§3.1.2)
        message_type, sentiment, confidence = _ai_classify(payload.text)
        priority = _priority_score(message_type, sentiment, payload.author_follower_count)
        suggestions = _suggested_replies(message_type)

        with _lock:
            message: dict[str, Any] = {
                'id': len(messages_memory) + 1,
                'tenant_id': auth.tenant_id,
                'network': network,
                'source_type': source_type,
                'external_message_id': payload.external_message_id,
                'parent_message_id': payload.parent_message_id,
                'author_handle': payload.author_handle.strip(),
                'author_display_name': payload.author_display_name,
                'author_follower_count': payload.author_follower_count,
                # ADDED: CRM linkage (§3.1.4)
                'crm_contact_id': payload.crm_contact_id,
                'text': payload.text,
                # ADDED: AI classification results (§3.1.2)
                'message_type': message_type,
                'sentiment': sentiment,
                'classification_confidence': confidence,
                'priority_score': priority,
                # ADDED: suggested replies for one-click response (§3.1.2)
                'suggested_replies': suggestions,
                # Workflow fields
                'status': 'pending',
                'assigned_to': None,
                'due_at': None,
                'tags': [],
                'replied': False,
                'replied_at': None,
                'read': False,
                'read_at': None,
                'created_at': datetime.now(UTC).isoformat(),
                'updated_at': datetime.now(UTC).isoformat(),
            }
            messages_memory.append(message)

        _audit(auth.tenant_id, 'inbox_message_ingested', message['id'])
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'message': message.copy(), 'created': True}

    @router.get('/inbox/messages')
    def list_messages(
        auth: AuthDep,
        status: Annotated[str | None, Query(max_length=40)] = None,
        network: Annotated[str | None, Query(max_length=40)] = None,
        message_type: Annotated[str | None, Query(max_length=40)] = None,
        sentiment: Annotated[str | None, Query(max_length=20)] = None,
        assigned_to: Annotated[str | None, Query(max_length=160)] = None,
        unread_only: Annotated[bool, Query()] = False,
        limit: Annotated[int, Query(ge=1, le=200)] = 50,
        offset: Annotated[int, Query(ge=0)] = 0,
    ) -> dict[str, Any]:
        """ADDED: List inbox messages with rich filtering (§3.1.3 Inbox Views)."""
        enforce_rate_limit(f'{auth.tenant_id}:inbox:list', 240, 60)
        status_f = status.strip().lower() if status else None
        network_f = network.strip().lower() if network else None
        type_f = message_type.strip().lower() if message_type else None
        sentiment_f = sentiment.strip().lower() if sentiment else None
        assigned_f = assigned_to.strip() if assigned_to else None

        with _lock:
            items = [
                m.copy() for m in messages_memory
                if m.get('tenant_id') == auth.tenant_id
                and (status_f is None or m.get('status') == status_f)
                and (network_f is None or m.get('network') == network_f)
                and (type_f is None or m.get('message_type') == type_f)
                and (sentiment_f is None or m.get('sentiment') == sentiment_f)
                and (assigned_f is None or m.get('assigned_to') == assigned_f)
                and (not unread_only or not m.get('read', False))
            ]
        # ADDED: sort by priority score descending (highest urgency first)
        items.sort(key=lambda m: int(m.get('priority_score', 0)), reverse=True)
        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'count': len(items),
            'messages': items[offset: offset + limit],
            'limit': limit,
            'offset': offset,
        }

    @router.get('/inbox/messages/{message_id}', responses={404: {'description': MESSAGE_NOT_FOUND}})
    def get_message(message_id: int, auth: AuthDep) -> dict[str, Any]:
        """ADDED: Get a single message with thread, notes, lock status, and suggested replies."""
        enforce_rate_limit(f'{auth.tenant_id}:inbox:get', 300, 60)
        message = _get_message(auth.tenant_id, message_id)
        if message is None:
            raise HTTPException(status_code=404, detail=MESSAGE_NOT_FOUND)

        # Mark as read
        with _lock:
            for m in messages_memory:
                if m.get('tenant_id') == auth.tenant_id and m.get('id') == message_id and not m.get('read'):
                    m['read'] = True
                    m['read_at'] = datetime.now(UTC).isoformat()
                    message = m.copy()
                    break

        # ADDED: include thread (messages with same parent_message_id)
        thread: list[dict[str, Any]] = []
        if message.get('parent_message_id'):
            with _lock:
                thread = [
                    m.copy() for m in messages_memory
                    if m.get('tenant_id') == auth.tenant_id
                    and m.get('parent_message_id') == message.get('parent_message_id')
                    and m.get('id') != message_id
                ]

        # ADDED: include internal notes count
        with _lock:
            notes = [n.copy() for n in notes_memory if n.get('tenant_id') == auth.tenant_id and n.get('message_id') == message_id]

        # ADDED: include current lock (collision detection §3.1.3)
        with _lock:
            lock_info = next(
                (lk.copy() for lk in locks_memory if lk.get('tenant_id') == auth.tenant_id and lk.get('message_id') == message_id),
                None,
            )

        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'message': message,
            'thread': thread,
            'notes': notes,
            'notes_count': len(notes),
            # ADDED: collision detection metadata
            'lock': lock_info,
            'is_locked': lock_info is not None,
        }

    @router.patch(
        '/inbox/messages/{message_id}',
        responses={404: {'description': MESSAGE_NOT_FOUND}, 422: {'description': 'Invalid status value'}},
    )
    def update_message(message_id: int, payload: MessageUpdateRequest, auth: AuthDep) -> dict[str, Any]:
        """ADDED: Update message assignment, status, or tags (§3.1.3 Assignment)."""
        enforce_rate_limit(f'{auth.tenant_id}:inbox:update', 300, 60)
        with _lock:
            message = next(
                (m for m in messages_memory if m.get('tenant_id') == auth.tenant_id and m.get('id') == message_id),
                None,
            )
            if message is None:
                raise HTTPException(status_code=404, detail=MESSAGE_NOT_FOUND)
            if payload.assigned_to is not None:
                message['assigned_to'] = payload.assigned_to.strip() or None
            if payload.status is not None:
                status_clean = payload.status.strip().lower()
                if status_clean not in MESSAGE_STATUSES:
                    raise HTTPException(status_code=422, detail=f'Invalid status. Must be one of: {", ".join(sorted(MESSAGE_STATUSES))}')
                message['status'] = status_clean
                if status_clean == 'complete':
                    message['completed_at'] = datetime.now(UTC).isoformat()
            if payload.tags is not None:
                message['tags'] = [t.strip() for t in payload.tags if t.strip()]
            if payload.due_at is not None:
                message['due_at'] = payload.due_at
            message['updated_at'] = datetime.now(UTC).isoformat()
            updated = message.copy()

        _audit(auth.tenant_id, 'inbox_message_updated', message_id)
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'message': updated}

    # ── Internal notes ──────────────────────────────────────────────────────────

    @router.post(
        '/inbox/messages/{message_id}/notes',
        responses={404: {'description': MESSAGE_NOT_FOUND}},
    )
    def add_note(message_id: int, payload: InternalNoteRequest, auth: AuthDep) -> dict[str, Any]:
        """ADDED: Add an internal note to a message — never visible to customers (§3.1.3)."""
        enforce_rate_limit(f'{auth.tenant_id}:inbox:notes:add', 180, 60)
        if _get_message(auth.tenant_id, message_id) is None:
            raise HTTPException(status_code=404, detail=MESSAGE_NOT_FOUND)
        with _lock:
            note: dict[str, Any] = {
                'id': len(notes_memory) + 1,
                'tenant_id': auth.tenant_id,
                'message_id': message_id,
                'author': payload.author.strip(),
                'note': payload.note,
                'created_at': datetime.now(UTC).isoformat(),
            }
            notes_memory.append(note)
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'note': note.copy()}

    @router.get('/inbox/messages/{message_id}/notes', responses={404: {'description': MESSAGE_NOT_FOUND}})
    def list_notes(message_id: int, auth: AuthDep) -> dict[str, Any]:
        """ADDED: List internal notes for a message."""
        enforce_rate_limit(f'{auth.tenant_id}:inbox:notes:list', 240, 60)
        if _get_message(auth.tenant_id, message_id) is None:
            raise HTTPException(status_code=404, detail=MESSAGE_NOT_FOUND)
        with _lock:
            items = [n.copy() for n in notes_memory if n.get('tenant_id') == auth.tenant_id and n.get('message_id') == message_id]
        items.sort(key=lambda n: str(n.get('created_at', '')))
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'count': len(items), 'notes': items}

    # ── Collision detection (locking) ───────────────────────────────────────────

    @router.post(
        '/inbox/messages/{message_id}/lock',
        responses={404: {'description': MESSAGE_NOT_FOUND}, 409: {'description': 'Message already locked by another team member.'}},
    )
    def acquire_lock(message_id: int, payload: LockRequest, auth: AuthDep) -> dict[str, Any]:
        """
        ADDED: Acquire a collision-prevention lock before composing a reply (§3.1.3).
        Returns 409 if another team member already holds the lock.
        """
        enforce_rate_limit(f'{auth.tenant_id}:inbox:lock', 300, 60)
        if _get_message(auth.tenant_id, message_id) is None:
            raise HTTPException(status_code=404, detail=MESSAGE_NOT_FOUND)
        with _lock:
            existing_lock = next(
                (lk for lk in locks_memory if lk.get('tenant_id') == auth.tenant_id and lk.get('message_id') == message_id),
                None,
            )
            lock_record: dict[str, Any]
            if existing_lock and existing_lock.get('locked_by') != payload.locked_by:
                raise HTTPException(
                    status_code=409,
                    detail=f'Message already locked by {existing_lock.get("locked_by")}. Collision detected.',
                )
            if existing_lock:
                # Renew lock
                existing_lock['locked_at'] = datetime.now(UTC).isoformat()
                lock_record = existing_lock.copy()
            else:
                lock_record = {
                    'id': len(locks_memory) + 1,
                    'tenant_id': auth.tenant_id,
                    'message_id': message_id,
                    'locked_by': payload.locked_by.strip(),
                    'locked_at': datetime.now(UTC).isoformat(),
                }
                locks_memory.append(lock_record)
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'lock': lock_record, 'collision_detected': False}

    @router.delete(
        '/inbox/messages/{message_id}/lock',
        responses={404: {'description': LOCK_NOT_HELD}},
    )
    def release_lock(message_id: int, locked_by: Annotated[str, Query(min_length=1, max_length=160)], auth: AuthDep) -> dict[str, Any]:
        """ADDED: Release the collision-prevention lock after composing/sending a reply."""
        enforce_rate_limit(f'{auth.tenant_id}:inbox:unlock', 300, 60)
        with _lock:
            index = next(
                (
                    i for i, lk in enumerate(locks_memory)
                    if lk.get('tenant_id') == auth.tenant_id
                    and lk.get('message_id') == message_id
                    and lk.get('locked_by') == locked_by
                ),
                None,
            )
            if index is None:
                raise HTTPException(status_code=404, detail=LOCK_NOT_HELD)
            locks_memory.pop(index)
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'message_id': message_id, 'released': True}

    # ── Inbox stats ─────────────────────────────────────────────────────────────

    @router.get('/inbox/stats')
    def inbox_stats(auth: AuthDep) -> dict[str, Any]:
        """ADDED: Inbox summary — total, unread, by status, by type, by sentiment, avg response time."""
        enforce_rate_limit(f'{auth.tenant_id}:inbox:stats', 120, 60)
        with _lock:
            messages = [m for m in messages_memory if m.get('tenant_id') == auth.tenant_id]

        total = len(messages)
        unread = sum(1 for m in messages if not m.get('read', False))
        by_status: dict[str, int] = {}
        by_type: dict[str, int] = {}
        by_sentiment: dict[str, int] = {}
        by_network: dict[str, int] = {}
        replied = sum(1 for m in messages if m.get('replied', False))

        for m in messages:
            s = str(m.get('status', 'pending'))
            by_status[s] = by_status.get(s, 0) + 1
            t = str(m.get('message_type', 'conversation'))
            by_type[t] = by_type.get(t, 0) + 1
            sent = str(m.get('sentiment', 'neutral'))
            by_sentiment[sent] = by_sentiment.get(sent, 0) + 1
            net = str(m.get('network', 'unknown'))
            by_network[net] = by_network.get(net, 0) + 1

        # ADDED: average priority score for triage health indicator
        avg_priority = round(sum(int(m.get('priority_score', 0)) for m in messages) / total, 1) if total else 0.0

        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'generatedAt': datetime.now(UTC).isoformat(),
            'total': total,
            'unread': unread,
            'replied': replied,
            'replyRate': round(replied / total, 4) if total else 0.0,
            'avgPriorityScore': avg_priority,
            'byStatus': by_status,
            'byMessageType': by_type,
            'bySentiment': by_sentiment,
            'byNetwork': by_network,
        }

    @router.get('/inbox/mentions/alerts')
    def mention_alerts(
        auth: AuthDep,
        severity: Annotated[str | None, Query(max_length=20)] = None,
        unresolved_only: Annotated[bool, Query()] = True,
    ) -> dict[str, Any]:
        """Return mention-driven alerts and other urgent inbound messages for triage."""
        enforce_rate_limit(f'{auth.tenant_id}:inbox:mentions:alerts', 180, 60)
        alerts = _build_alerts(auth.tenant_id)
        severity_filter = severity.strip().lower() if severity else None
        if severity_filter:
            alerts = [item for item in alerts if str(item.get('severity')) == severity_filter]
        if unresolved_only:
            with _lock:
                unresolved_ids = {
                    int(m.get('id')) for m in messages_memory
                    if m.get('tenant_id') == auth.tenant_id and str(m.get('status')) != 'complete'
                }
            alerts = [item for item in alerts if int(item.get('message_id') or 0) in unresolved_ids]
        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'count': len(alerts),
            'alerts': alerts,
        }

    @router.get('/inbox/approvals/pending')
    def pending_approvals(
        auth: AuthDep,
        network: Annotated[str | None, Query(max_length=40)] = None,
        limit: Annotated[int, Query(ge=1, le=200)] = 50,
        offset: Annotated[int, Query(ge=0)] = 0,
    ) -> dict[str, Any]:
        """List approval-pending inbox responses for reviewers."""
        enforce_rate_limit(f'{auth.tenant_id}:inbox:approvals:pending', 240, 60)
        network_filter = network.strip().lower() if network else None
        with _lock:
            items = [
                {
                    'message_id': int(m.get('id') or 0),
                    'network': m.get('network'),
                    'author_handle': m.get('author_handle'),
                    'message_type': m.get('message_type'),
                    'priority_score': int(m.get('priority_score') or 0),
                    'status': m.get('status'),
                    'response_preview': m.get('last_response_preview'),
                    'response_source': m.get('last_response_source'),
                    'response_staged_by': m.get('last_response_by'),
                    'response_staged_at': m.get('last_response_at'),
                    'created_at': m.get('created_at'),
                }
                for m in messages_memory
                if m.get('tenant_id') == auth.tenant_id
                and str(m.get('status')) == 'requires_approval'
                and str(m.get('last_response_preview', '')).strip()
                and (network_filter is None or str(m.get('network', '')).lower() == network_filter)
            ]
        for item in items:
            readiness = _delivery_readiness_for(str(item.get('network') or ''))
            item.update(readiness)
        items.sort(key=lambda item: str(item.get('response_staged_at', '')), reverse=True)
        total = len(items)
        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'count': total,
            'items': items[offset: offset + limit],
            'limit': limit,
            'offset': offset,
        }

    @router.get('/inbox/delivery-failures')
    def list_delivery_failures(
        auth: AuthDep,
        status: Annotated[str | None, Query(max_length=40)] = None,
        limit: Annotated[int, Query(ge=1, le=200)] = 50,
        offset: Annotated[int, Query(ge=0)] = 0,
    ) -> dict[str, Any]:
        """List failed outbound inbox deliveries queued for retry operations."""
        enforce_rate_limit(f'{auth.tenant_id}:inbox:delivery-failures:list', 180, 60)
        status_filter = status.strip().lower() if status else None
        with _lock:
            items = [
                item.copy() for item in delivery_failures_memory
                if item.get('tenant_id') == auth.tenant_id
                and (status_filter is None or str(item.get('status', '')).lower() == status_filter)
            ]
        items.sort(key=lambda item: int(item.get('id') or 0), reverse=True)
        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'count': len(items),
            'items': items[offset: offset + limit],
            'limit': limit,
            'offset': offset,
        }

    @router.get('/inbox/delivery-failures/metrics')
    def delivery_failure_metrics(
        auth: AuthDep,
        network: Annotated[str | None, Query(max_length=40)] = None,
    ) -> dict[str, Any]:
        """Return operational metrics for Smart Inbox delivery failures and replay actions."""
        enforce_rate_limit(f'{auth.tenant_id}:inbox:delivery-failures:metrics', 120, 60)
        network_filter = network.strip().lower() if network else None

        with _lock:
            failures = [
                item.copy() for item in delivery_failures_memory
                if item.get('tenant_id') == auth.tenant_id
                and (
                    network_filter is None
                    or str(item.get('network', '')).strip().lower() == network_filter
                )
            ]
            tenant_audit_events = [
                entry.copy() for entry in audit_log_memory
                if entry.get('tenant_id') == auth.tenant_id
                and str(entry.get('source')) == 'smart-inbox-router'
                and str(entry.get('action', '')).startswith('inbox_auto_response_delivery_')
            ]
            replay_runs = [
                item.copy() for item in delivery_replay_runs_memory
                if item.get('tenant_id') == auth.tenant_id
                and (
                    network_filter is None
                    or str(item.get('network_filter') or '').strip().lower() == network_filter
                )
            ]

        by_status: dict[str, int] = {}
        by_network: dict[str, int] = {}
        by_resolution: dict[str, int] = {}
        replay_runs_by_operator: dict[str, int] = {}
        retry_attempt_sum = 0
        oldest_pending_age_seconds = 0
        replay_runs_last_24h = 0
        replay_runs_selected_total = 0
        replay_runs_replayed_total = 0
        replay_runs_failed_total = 0
        replay_runs_with_no_selection = 0

        now = datetime.now(UTC)
        for item in failures:
            status_name = str(item.get('status') or 'unknown').lower()
            by_status[status_name] = by_status.get(status_name, 0) + 1

            network_name = str(item.get('network') or 'unknown').lower()
            by_network[network_name] = by_network.get(network_name, 0) + 1

            resolution_name = str(item.get('resolution') or '').strip().lower()
            if resolution_name:
                by_resolution[resolution_name] = by_resolution.get(resolution_name, 0) + 1

            retry_attempt_sum += int(item.get('retry_count') or 0)

            if status_name == 'pending_retry':
                created_at = str(item.get('created_at') or '').strip()
                if created_at:
                    try:
                        created_dt = datetime.fromisoformat(created_at)
                        age_seconds = int((now - created_dt).total_seconds())
                        if age_seconds > oldest_pending_age_seconds:
                            oldest_pending_age_seconds = max(0, age_seconds)
                    except ValueError:
                        continue

        for run in replay_runs:
            operator_name = str(run.get('operator') or 'unknown').strip().lower() or 'unknown'
            replay_runs_by_operator[operator_name] = replay_runs_by_operator.get(operator_name, 0) + 1

            selected_count = int(run.get('selected_count') or 0)
            replayed_count = int(run.get('replayed_count') or 0)
            failed_count = int(run.get('failed_count') or 0)
            replay_runs_selected_total += selected_count
            replay_runs_replayed_total += replayed_count
            replay_runs_failed_total += failed_count
            if selected_count == 0:
                replay_runs_with_no_selection += 1

            created_at_raw = str(run.get('created_at') or '').strip()
            if created_at_raw:
                try:
                    created_at_dt = datetime.fromisoformat(created_at_raw)
                    if created_at_dt >= now - timedelta(hours=24):
                        replay_runs_last_24h += 1
                except ValueError:
                    continue

        tenant_audit_events.sort(key=lambda item: str(item.get('created_at', '')), reverse=True)
        recent_operations = [
            {
                'action': event.get('action'),
                'ref_id': event.get('ref_id'),
                'created_at': event.get('created_at'),
            }
            for event in tenant_audit_events[:20]
        ]

        total_failures = len(failures)
        pending_count = by_status.get('pending_retry', 0)
        resolved_count = by_status.get('resolved', 0)
        pending_ratio = round(pending_count / total_failures, 4) if total_failures else 0.0
        replay_success_rate = (
            round(replay_runs_replayed_total / replay_runs_selected_total, 4)
            if replay_runs_selected_total
            else 0.0
        )
        replay_no_selection_ratio = (
            round(replay_runs_with_no_selection / len(replay_runs), 4)
            if replay_runs
            else 0.0
        )

        pending_ratio_high_threshold = _env_float('INBOX_ALERT_PENDING_RATIO_HIGH', 0.35, minimum=0.0, maximum=1.0)
        pending_min_count_threshold = _env_int('INBOX_ALERT_PENDING_MIN_COUNT', 3, minimum=0)
        oldest_pending_age_threshold_seconds = _env_int('INBOX_ALERT_OLDEST_PENDING_AGE_SECONDS', 60 * 60, minimum=0)
        replay_success_rate_low_threshold = _env_float('INBOX_ALERT_REPLAY_SUCCESS_RATE_LOW', 0.7, minimum=0.0, maximum=1.0)
        replay_min_selected_threshold = _env_int('INBOX_ALERT_REPLAY_MIN_SELECTED', 3, minimum=0)
        no_selection_ratio_high_threshold = _env_float('INBOX_ALERT_NO_SELECTION_RATIO_HIGH', 0.8, minimum=0.0, maximum=1.0)
        no_selection_min_runs_threshold = _env_int('INBOX_ALERT_NO_SELECTION_MIN_RUNS', 5, minimum=0)

        alert_flags: list[dict[str, Any]] = []
        if pending_ratio >= pending_ratio_high_threshold and pending_count >= pending_min_count_threshold:
            alert_flags.append({
                'code': 'pending_backlog_ratio_high',
                'severity': 'warning',
                'value': pending_ratio,
                'context': {
                    'pending_count': pending_count,
                    'total_failures': total_failures,
                    'ratio_threshold': pending_ratio_high_threshold,
                    'min_count_threshold': pending_min_count_threshold,
                },
            })
        if oldest_pending_age_seconds >= oldest_pending_age_threshold_seconds:
            alert_flags.append({
                'code': 'oldest_pending_age_high',
                'severity': 'warning',
                'value': oldest_pending_age_seconds,
                'context': {
                    'threshold_seconds': oldest_pending_age_threshold_seconds,
                },
            })
        if replay_runs_selected_total >= replay_min_selected_threshold and replay_success_rate <= replay_success_rate_low_threshold:
            alert_flags.append({
                'code': 'replay_success_rate_low',
                'severity': 'critical',
                'value': replay_success_rate,
                'context': {
                    'selected_total': replay_runs_selected_total,
                    'replayed_total': replay_runs_replayed_total,
                    'success_rate_threshold': replay_success_rate_low_threshold,
                    'min_selected_threshold': replay_min_selected_threshold,
                },
            })
        if len(replay_runs) >= no_selection_min_runs_threshold and replay_no_selection_ratio >= no_selection_ratio_high_threshold:
            alert_flags.append({
                'code': 'replay_runs_no_selection_spike',
                'severity': 'warning',
                'value': replay_no_selection_ratio,
                'context': {
                    'total_runs': len(replay_runs),
                    'runs_with_no_selection': replay_runs_with_no_selection,
                    'ratio_threshold': no_selection_ratio_high_threshold,
                    'min_runs_threshold': no_selection_min_runs_threshold,
                },
            })

        replay_runs.sort(key=lambda item: int(item.get('id') or 0), reverse=True)
        recent_replay_runs = [
            {
                'id': run.get('id'),
                'operator': run.get('operator'),
                'selected_count': run.get('selected_count'),
                'replayed_count': run.get('replayed_count'),
                'failed_count': run.get('failed_count'),
                'network_filter': run.get('network_filter'),
                'created_at': run.get('created_at'),
            }
            for run in replay_runs[:10]
        ]

        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'generatedAt': now.isoformat(),
            'network_filter': network_filter,
            'total_failures': total_failures,
            'pending_count': pending_count,
            'resolved_count': resolved_count,
            'pending_ratio': pending_ratio,
            'avg_retry_attempts': round(retry_attempt_sum / total_failures, 2) if total_failures else 0.0,
            'oldest_pending_age_seconds': oldest_pending_age_seconds,
            'by_status': by_status,
            'by_network': by_network,
            'by_resolution': by_resolution,
            'recent_operations': recent_operations,
            'alerts': alert_flags,
            'alert_thresholds': {
                'pending_ratio_high': pending_ratio_high_threshold,
                'pending_min_count': pending_min_count_threshold,
                'oldest_pending_age_seconds': oldest_pending_age_threshold_seconds,
                'replay_success_rate_low': replay_success_rate_low_threshold,
                'replay_min_selected': replay_min_selected_threshold,
                'no_selection_ratio_high': no_selection_ratio_high_threshold,
                'no_selection_min_runs': no_selection_min_runs_threshold,
            },
            'replay_run_metrics': {
                'total_runs': len(replay_runs),
                'runs_last_24h': replay_runs_last_24h,
                'runs_with_no_selection': replay_runs_with_no_selection,
                'selected_total': replay_runs_selected_total,
                'replayed_total': replay_runs_replayed_total,
                'failed_total': replay_runs_failed_total,
                'replayed_success_rate': replay_success_rate,
                'no_selection_ratio': replay_no_selection_ratio,
                'by_operator': replay_runs_by_operator,
                'recent_runs': recent_replay_runs,
            },
        }

    @router.post(
        '/inbox/delivery-failures/{failure_id}/replay',
        responses={404: {'description': 'Delivery failure not found'}},
    )
    async def replay_delivery_failure(failure_id: int, payload: ResponseReplayRequest, auth: AuthDep) -> dict[str, Any]:
        """Replay a failed outbound inbox delivery while guarding against duplicate sends."""
        enforce_rate_limit(f'{auth.tenant_id}:inbox:delivery-failures:replay', 120, 60)
        with _lock:
            failure = next(
                (
                    item for item in delivery_failures_memory
                    if item.get('tenant_id') == auth.tenant_id and int(item.get('id') or 0) == failure_id
                ),
                None,
            )
            if failure is None:
                raise HTTPException(status_code=404, detail='Delivery failure not found')

            message = next(
                (
                    item for item in messages_memory
                    if item.get('tenant_id') == auth.tenant_id and int(item.get('id') or 0) == int(failure.get('message_id') or 0)
                ),
                None,
            )
            if message is None:
                raise HTTPException(status_code=404, detail=MESSAGE_NOT_FOUND)

            if str(message.get('response_delivery_status')) == 'sent':
                failure['status'] = 'resolved'
                failure['resolution'] = 'already_delivered'
                failure['resolved_at'] = datetime.now(UTC).isoformat()
                failure['resolved_by'] = payload.operator.strip()
                failure['replay_note'] = payload.note.strip() if payload.note else None
                return {
                    'status': 'ok',
                    'tenant_id': auth.tenant_id,
                    'replayed': False,
                    'reason': 'already_delivered',
                    'failure': failure.copy(),
                    'message': message.copy(),
                }

            current_status = str(failure.get('status') or 'pending_retry').lower()
            if current_status not in {'pending_retry', 'replaying'}:
                return {
                    'status': 'ok',
                    'tenant_id': auth.tenant_id,
                    'replayed': False,
                    'reason': current_status,
                    'failure': failure,
                    'message': message.copy(),
                }

            replay_started_at = datetime.now(UTC).isoformat()
            failure['status'] = 'replaying'
            failure['replay_started_at'] = replay_started_at
            failure['replayed_by'] = payload.operator.strip()
            failure['replay_note'] = payload.note.strip() if payload.note else None
            request_payload = dict(failure.get('payload') or {})
            response_text = str(message.get('last_response_preview') or request_payload.get('reply_text') or '')
            idempotency_key = str(
                request_payload.get('idempotency_key')
                or message.get('response_delivery_idempotency_key')
                or _build_delivery_idempotency_key(auth.tenant_id, int(message.get('id') or 0), response_text)
            )
            request_payload['idempotency_key'] = idempotency_key

        vendor_response, delivery_errors, attempts_made = await _attempt_outbound_delivery(
            vendor_id=str(failure.get('vendor_id') or ''),
            endpoint=str(failure.get('endpoint') or ''),
            request_payload=request_payload,
            idempotency_key=idempotency_key,
        )

        now_iso = datetime.now(UTC).isoformat()
        if vendor_response is None:
            combined_errors = [*list(failure.get('errors') or []), *delivery_errors]
            updated_failure = _update_delivery_failure(
                auth.tenant_id,
                failure_id,
                status='pending_retry',
                errors=combined_errors,
                retry_count=int(failure.get('retry_count') or 0) + 1,
                last_attempted_at=now_iso,
                replayed_by=payload.operator.strip(),
                replay_note=payload.note.strip() if payload.note else None,
            )
            with _lock:
                message = next(
                    (m for m in messages_memory if m.get('tenant_id') == auth.tenant_id and m.get('id') == failure.get('message_id')),
                    None,
                )
                if message is not None:
                    message['response_delivery_status'] = 'failed'
                    message['response_delivery_attempts'] = int(message.get('response_delivery_attempts') or 0) + attempts_made
                    message['response_delivery_failure_id'] = failure_id
                    message['response_delivery_last_error'] = delivery_errors[-1] if delivery_errors else 'delivery failed'
                    message['response_delivery_idempotency_key'] = idempotency_key
                    message['updated_at'] = now_iso
                    updated_message = message.copy()
                else:
                    updated_message = None
            raise HTTPException(
                status_code=502,
                detail=f'Replay delivery failed after retries; failure_id={failure_id}',
            ) from None

        updated_failure = _update_delivery_failure(
            auth.tenant_id,
            failure_id,
            status='resolved',
            resolution='replayed',
            resolved_at=now_iso,
            resolved_by=payload.operator.strip(),
            replay_note=payload.note.strip() if payload.note else None,
            retry_count=int(failure.get('retry_count') or 0) + 1,
            last_attempted_at=now_iso,
            payload=request_payload,
        )
        with _lock:
            message = next(
                (m for m in messages_memory if m.get('tenant_id') == auth.tenant_id and m.get('id') == failure.get('message_id')),
                None,
            )
            if message is None:
                raise HTTPException(status_code=404, detail=MESSAGE_NOT_FOUND)
            message['status'] = 'complete'
            message['replied'] = True
            message['replied_at'] = now_iso
            message['response_delivered_at'] = now_iso
            message['response_delivery_vendor'] = failure.get('vendor_id')
            message['response_delivery_status'] = 'sent'
            message['response_delivery_attempts'] = int(message.get('response_delivery_attempts') or 0) + attempts_made
            message['response_delivery_result'] = vendor_response
            message['response_delivery_failure_id'] = None
            message['response_delivery_last_error'] = None
            message['response_delivery_idempotency_key'] = idempotency_key
            message['updated_at'] = now_iso
            updated_message = message.copy()

        _audit(auth.tenant_id, 'inbox_auto_response_delivery_replayed', int(failure.get('message_id') or 0))
        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'replayed': True,
            'failure': updated_failure or failure,
            'message': updated_message,
            'response': {
                'delivered': True,
                'idempotency_key': idempotency_key,
                'result': vendor_response,
            },
        }

    @router.post('/inbox/delivery-failures/replay-bulk')
    async def replay_delivery_failures_bulk(payload: DeliveryFailureBulkReplayRequest, auth: AuthDep) -> dict[str, Any]:
        """Replay multiple pending delivery failures and return per-item outcomes."""
        enforce_rate_limit(f'{auth.tenant_id}:inbox:delivery-failures:replay-bulk', 60, 60)
        deduped_ids: list[int] = []
        seen: set[int] = set()
        for raw_id in payload.failure_ids:
            if raw_id in seen:
                continue
            seen.add(raw_id)
            deduped_ids.append(raw_id)

        operator = payload.operator.strip()
        note = payload.note.strip() if payload.note else None
        items: list[dict[str, Any]] = []

        for failure_id in deduped_ids:
            with _lock:
                failure = next(
                    (
                        item for item in delivery_failures_memory
                        if item.get('tenant_id') == auth.tenant_id and int(item.get('id') or 0) == failure_id
                    ),
                    None,
                )
                if failure is None:
                    items.append({
                        'failure_id': failure_id,
                        'replayed': False,
                        'status': 'not_found',
                    })
                    continue

                message = next(
                    (
                        item for item in messages_memory
                        if item.get('tenant_id') == auth.tenant_id and int(item.get('id') or 0) == int(failure.get('message_id') or 0)
                    ),
                    None,
                )
                if message is None:
                    items.append({
                        'failure_id': failure_id,
                        'replayed': False,
                        'status': 'message_not_found',
                    })
                    continue

                if str(message.get('response_delivery_status')) == 'sent':
                    now_iso = datetime.now(UTC).isoformat()
                    failure['status'] = 'resolved'
                    failure['resolution'] = 'already_delivered'
                    failure['resolved_at'] = now_iso
                    failure['resolved_by'] = operator
                    failure['replay_note'] = note
                    items.append({
                        'failure_id': failure_id,
                        'replayed': False,
                        'status': 'already_delivered',
                    })
                    continue

                current_status = str(failure.get('status') or 'pending_retry').lower()
                if current_status not in {'pending_retry', 'replaying'}:
                    items.append({
                        'failure_id': failure_id,
                        'replayed': False,
                        'status': current_status,
                    })
                    continue

                replay_started_at = datetime.now(UTC).isoformat()
                failure['status'] = 'replaying'
                failure['replay_started_at'] = replay_started_at
                failure['replayed_by'] = operator
                failure['replay_note'] = note
                request_payload = dict(failure.get('payload') or {})
                response_text = str(message.get('last_response_preview') or request_payload.get('reply_text') or '')
                idempotency_key = str(
                    request_payload.get('idempotency_key')
                    or message.get('response_delivery_idempotency_key')
                    or _build_delivery_idempotency_key(auth.tenant_id, int(message.get('id') or 0), response_text)
                )
                request_payload['idempotency_key'] = idempotency_key
                vendor_id = str(failure.get('vendor_id') or '')
                endpoint = str(failure.get('endpoint') or '')
                message_id = int(message.get('id') or 0)

            vendor_response, delivery_errors, attempts_made = await _attempt_outbound_delivery(
                vendor_id=vendor_id,
                endpoint=endpoint,
                request_payload=request_payload,
                idempotency_key=idempotency_key,
            )

            now_iso = datetime.now(UTC).isoformat()
            if vendor_response is None:
                with _lock:
                    failure_ref = next(
                        (
                            item for item in delivery_failures_memory
                            if item.get('tenant_id') == auth.tenant_id and int(item.get('id') or 0) == failure_id
                        ),
                        None,
                    )
                    if failure_ref is not None:
                        failure_ref['status'] = 'pending_retry'
                        failure_ref['errors'] = [*list(failure_ref.get('errors') or []), *delivery_errors]
                        failure_ref['retry_count'] = int(failure_ref.get('retry_count') or 0) + 1
                        failure_ref['last_attempted_at'] = now_iso
                        failure_ref['replayed_by'] = operator
                        failure_ref['replay_note'] = note

                    message_ref = next(
                        (
                            item for item in messages_memory
                            if item.get('tenant_id') == auth.tenant_id and int(item.get('id') or 0) == message_id
                        ),
                        None,
                    )
                    if message_ref is not None:
                        message_ref['response_delivery_status'] = 'failed'
                        message_ref['response_delivery_attempts'] = int(message_ref.get('response_delivery_attempts') or 0) + attempts_made
                        message_ref['response_delivery_failure_id'] = failure_id
                        message_ref['response_delivery_last_error'] = delivery_errors[-1] if delivery_errors else 'delivery failed'
                        message_ref['response_delivery_idempotency_key'] = idempotency_key
                        message_ref['updated_at'] = now_iso

                items.append({
                    'failure_id': failure_id,
                    'replayed': False,
                    'status': 'delivery_failed',
                    'attempts_made': attempts_made,
                    'last_error': delivery_errors[-1] if delivery_errors else 'delivery failed',
                })
                continue

            with _lock:
                failure_ref = next(
                    (
                        item for item in delivery_failures_memory
                        if item.get('tenant_id') == auth.tenant_id and int(item.get('id') or 0) == failure_id
                    ),
                    None,
                )
                if failure_ref is not None:
                    failure_ref['status'] = 'resolved'
                    failure_ref['resolution'] = 'replayed'
                    failure_ref['resolved_at'] = now_iso
                    failure_ref['resolved_by'] = operator
                    failure_ref['replay_note'] = note
                    failure_ref['retry_count'] = int(failure_ref.get('retry_count') or 0) + 1
                    failure_ref['last_attempted_at'] = now_iso
                    failure_ref['payload'] = request_payload

                message_ref = next(
                    (
                        item for item in messages_memory
                        if item.get('tenant_id') == auth.tenant_id and int(item.get('id') or 0) == message_id
                    ),
                    None,
                )
                if message_ref is not None:
                    message_ref['status'] = 'complete'
                    message_ref['replied'] = True
                    message_ref['replied_at'] = now_iso
                    message_ref['response_delivered_at'] = now_iso
                    message_ref['response_delivery_vendor'] = vendor_id
                    message_ref['response_delivery_status'] = 'sent'
                    message_ref['response_delivery_attempts'] = int(message_ref.get('response_delivery_attempts') or 0) + attempts_made
                    message_ref['response_delivery_result'] = vendor_response
                    message_ref['response_delivery_failure_id'] = None
                    message_ref['response_delivery_last_error'] = None
                    message_ref['response_delivery_idempotency_key'] = idempotency_key
                    message_ref['updated_at'] = now_iso

            _audit(auth.tenant_id, 'inbox_auto_response_delivery_replayed_bulk', message_id)
            items.append({
                'failure_id': failure_id,
                'replayed': True,
                'status': 'replayed',
                'attempts_made': attempts_made,
                'idempotency_key': idempotency_key,
            })

        replayed_count = sum(1 for item in items if item.get('replayed') is True)
        not_found_count = sum(1 for item in items if item.get('status') == 'not_found')
        failed_count = sum(1 for item in items if item.get('status') == 'delivery_failed')
        skipped_count = len(items) - replayed_count - failed_count

        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'count': len(items),
            'replayed_count': replayed_count,
            'failed_count': failed_count,
            'skipped_count': skipped_count,
            'not_found_count': not_found_count,
            'items': items,
        }

    @router.post('/inbox/delivery-failures/replay-pending')
    async def replay_pending_delivery_failures(payload: DeliveryFailureReplayPendingRequest, auth: AuthDep) -> dict[str, Any]:
        """Replay the next pending failure items with limit and optional network filter."""
        enforce_rate_limit(f'{auth.tenant_id}:inbox:delivery-failures:replay-pending', 60, 60)
        run_started = time.perf_counter()
        network_filter = payload.network.strip().lower() if payload.network else None
        with _lock:
            pending = [
                item for item in delivery_failures_memory
                if item.get('tenant_id') == auth.tenant_id
                and str(item.get('status', '')).lower() == 'pending_retry'
                and (
                    network_filter is None
                    or str(item.get('network', '')).strip().lower() == network_filter
                )
            ]
        pending.sort(key=lambda item: int(item.get('id') or 0))
        selected_ids = [int(item.get('id') or 0) for item in pending[: payload.limit] if int(item.get('id') or 0) > 0]

        if not selected_ids:
            empty_result = {
                'status': 'ok',
                'tenant_id': auth.tenant_id,
                'requested_limit': payload.limit,
                'selected_count': 0,
                'selected_failure_ids': [],
                'count': 0,
                'replayed_count': 0,
                'failed_count': 0,
                'skipped_count': 0,
                'not_found_count': 0,
                'items': [],
            }
            run_record = _record_replay_run(
                tenant_id=auth.tenant_id,
                operator=payload.operator.strip(),
                note=payload.note.strip() if payload.note else None,
                requested_limit=payload.limit,
                selected_failure_ids=[],
                network_filter=network_filter,
                replay_result=empty_result,
                duration_ms=max(0, int((time.perf_counter() - run_started) * 1000)),
            )
            empty_result['run'] = run_record
            return empty_result

        replay_result = await replay_delivery_failures_bulk(
            DeliveryFailureBulkReplayRequest(
                failure_ids=selected_ids,
                operator=payload.operator,
                note=payload.note,
            ),
            auth,
        )
        replay_result['requested_limit'] = payload.limit
        replay_result['selected_count'] = len(selected_ids)
        replay_result['selected_failure_ids'] = selected_ids
        replay_result['network_filter'] = network_filter
        run_record = _record_replay_run(
            tenant_id=auth.tenant_id,
            operator=payload.operator.strip(),
            note=payload.note.strip() if payload.note else None,
            requested_limit=payload.limit,
            selected_failure_ids=selected_ids,
            network_filter=network_filter,
            replay_result=replay_result,
            duration_ms=max(0, int((time.perf_counter() - run_started) * 1000)),
        )
        replay_result['run'] = run_record
        return replay_result

    @router.get('/inbox/delivery-failures/replay-runs')
    def list_delivery_failure_replay_runs(
        auth: AuthDep,
        network: Annotated[str | None, Query(max_length=40)] = None,
        limit: Annotated[int, Query(ge=1, le=200)] = 50,
        offset: Annotated[int, Query(ge=0)] = 0,
    ) -> dict[str, Any]:
        """List replay-pending operation runs for DLQ queue-audit visibility."""
        enforce_rate_limit(f'{auth.tenant_id}:inbox:delivery-failures:replay-runs', 120, 60)
        network_filter = network.strip().lower() if network else None
        with _lock:
            items = [
                item.copy() for item in delivery_replay_runs_memory
                if item.get('tenant_id') == auth.tenant_id
                and (
                    network_filter is None
                    or str(item.get('network_filter') or '').strip().lower() == network_filter
                )
            ]
        items.sort(key=lambda item: int(item.get('id') or 0), reverse=True)
        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'count': len(items),
            'items': items[offset: offset + limit],
            'limit': limit,
            'offset': offset,
            'network_filter': network_filter,
        }

    @router.get('/inbox/delivery-failures/replay-runs/performance')
    def delivery_failure_replay_run_performance(
        auth: AuthDep,
        network: Annotated[str | None, Query(max_length=40)] = None,
        operator: Annotated[str | None, Query(max_length=120)] = None,
        window_hours: Annotated[int, Query(ge=1, le=24 * 30)] = 24,
    ) -> dict[str, Any]:
        """Return per-operator replay-run performance analytics over a bounded time window."""
        enforce_rate_limit(f'{auth.tenant_id}:inbox:delivery-failures:replay-runs:performance', 120, 60)
        network_filter = network.strip().lower() if network else None
        operator_filter = operator.strip().lower() if operator else None
        now = datetime.now(UTC)
        window_start = now - timedelta(hours=window_hours)

        with _lock:
            runs = [
                item.copy() for item in delivery_replay_runs_memory
                if item.get('tenant_id') == auth.tenant_id
                and (
                    network_filter is None
                    or str(item.get('network_filter') or '').strip().lower() == network_filter
                )
            ]

        filtered_runs: list[dict[str, Any]] = []
        for run in runs:
            created_at_raw = str(run.get('created_at') or '').strip()
            if not created_at_raw:
                continue
            try:
                created_at_dt = datetime.fromisoformat(created_at_raw)
            except ValueError:
                continue
            if created_at_dt < window_start:
                continue
            run_operator = str(run.get('operator') or 'unknown').strip().lower() or 'unknown'
            if operator_filter is not None and run_operator != operator_filter:
                continue
            filtered_runs.append(run)

        by_operator: dict[str, dict[str, Any]] = {}
        for run in filtered_runs:
            run_operator = str(run.get('operator') or 'unknown').strip().lower() or 'unknown'
            selected_count = int(run.get('selected_count') or 0)
            replayed_count = int(run.get('replayed_count') or 0)
            failed_count = int(run.get('failed_count') or 0)
            duration_ms = max(0, int(run.get('duration_ms') or 0))

            stats = by_operator.setdefault(
                run_operator,
                {
                    'operator': run_operator,
                    'runs': 0,
                    'selected_total': 0,
                    'replayed_total': 0,
                    'failed_total': 0,
                    'durations_ms': [],
                },
            )
            stats['runs'] = int(stats['runs']) + 1
            stats['selected_total'] = int(stats['selected_total']) + selected_count
            stats['replayed_total'] = int(stats['replayed_total']) + replayed_count
            stats['failed_total'] = int(stats['failed_total']) + failed_count
            stats['durations_ms'].append(duration_ms)

        operator_rows: list[dict[str, Any]] = []
        operator_success_rate_low_threshold = _env_float('INBOX_ALERT_OPERATOR_SUCCESS_RATE_LOW', 0.7, minimum=0.0, maximum=1.0)
        operator_min_selected_threshold = _env_int('INBOX_ALERT_OPERATOR_MIN_SELECTED', 3, minimum=0)
        operator_no_selection_min_runs_threshold = _env_int('INBOX_ALERT_OPERATOR_NO_SELECTION_MIN_RUNS', 5, minimum=0)
        operator_latency_spike_multiplier = _env_float('INBOX_ALERT_OPERATOR_LATENCY_SPIKE_MULTIPLIER', 2.0, minimum=1.0)
        operator_latency_min_runs_threshold = _env_int('INBOX_ALERT_OPERATOR_LATENCY_MIN_RUNS', 3, minimum=0)

        for stats in by_operator.values():
            durations: list[int] = list(stats['durations_ms'])
            selected_total = int(stats['selected_total'])
            replayed_total = int(stats['replayed_total'])
            failed_total = int(stats['failed_total'])
            success_rate = round(replayed_total / selected_total, 4) if selected_total else 0.0
            avg_duration_ms = round(sum(durations) / len(durations), 2) if durations else 0.0
            row = {
                'operator': stats['operator'],
                'runs': int(stats['runs']),
                'selected_total': selected_total,
                'replayed_total': replayed_total,
                'failed_total': failed_total,
                'success_rate': success_rate,
                'avg_duration_ms': avg_duration_ms,
                'p50_duration_ms': round(_percentile(durations, 0.5), 2) if durations else 0.0,
                'p95_duration_ms': round(_percentile(durations, 0.95), 2) if durations else 0.0,
                'alerts': [],
            }
            if selected_total >= operator_min_selected_threshold and success_rate <= operator_success_rate_low_threshold:
                row['alerts'].append('operator_success_rate_low')
            if int(row['runs']) >= operator_no_selection_min_runs_threshold and selected_total == 0:
                row['alerts'].append('operator_no_selection_only_runs')
            operator_rows.append(row)

        operator_rows.sort(key=lambda item: (int(item.get('runs') or 0), int(item.get('replayed_total') or 0)), reverse=True)
        total_selected = sum(int(item['selected_total']) for item in operator_rows)
        total_replayed = sum(int(item['replayed_total']) for item in operator_rows)
        total_failed = sum(int(item['failed_total']) for item in operator_rows)
        overall_success_rate = round(total_replayed / total_selected, 4) if total_selected else 0.0
        global_p50_duration_ms = round(_percentile([int(run.get('duration_ms') or 0) for run in filtered_runs], 0.5), 2) if filtered_runs else 0.0
        overall_success_rate_low_threshold = _env_float('INBOX_ALERT_OVERALL_SUCCESS_RATE_LOW', 0.7, minimum=0.0, maximum=1.0)
        overall_min_selected_threshold = _env_int('INBOX_ALERT_OVERALL_MIN_SELECTED', 3, minimum=0)

        for row in operator_rows:
            if (
                int(row['runs']) >= operator_latency_min_runs_threshold
                and global_p50_duration_ms > 0
                and float(row['avg_duration_ms']) >= global_p50_duration_ms * operator_latency_spike_multiplier
            ):
                row['alerts'].append('operator_latency_spike')

        anomaly_summary = {
            'operators_with_alerts': sum(1 for row in operator_rows if row['alerts']),
            'total_alerts': sum(len(list(row['alerts'])) for row in operator_rows),
            'global_p50_duration_ms': global_p50_duration_ms,
            'overall_success_rate_low': (
                overall_success_rate <= overall_success_rate_low_threshold
                and total_selected >= overall_min_selected_threshold
            ),
        }

        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'generatedAt': now.isoformat(),
            'window_hours': window_hours,
            'window_start': window_start.isoformat(),
            'network_filter': network_filter,
            'operator_filter': operator_filter,
            'total_runs': len(filtered_runs),
            'total_selected': total_selected,
            'total_replayed': total_replayed,
            'total_failed': total_failed,
            'overall_success_rate': overall_success_rate,
            'anomaly_summary': anomaly_summary,
            'anomaly_thresholds': {
                'operator_success_rate_low': operator_success_rate_low_threshold,
                'operator_min_selected': operator_min_selected_threshold,
                'operator_no_selection_min_runs': operator_no_selection_min_runs_threshold,
                'operator_latency_spike_multiplier': operator_latency_spike_multiplier,
                'operator_latency_min_runs': operator_latency_min_runs_threshold,
                'overall_success_rate_low': overall_success_rate_low_threshold,
                'overall_min_selected': overall_min_selected_threshold,
            },
            'operators': operator_rows,
        }

    @router.get('/inbox/ops-config')
    def inbox_ops_config(auth: AuthDep) -> dict[str, Any]:
        """Return effective Smart Inbox operations configuration used by replay and anomaly analytics."""
        enforce_rate_limit(f'{auth.tenant_id}:inbox:ops-config', 120, 60)

        replay_config = {
            'delivery_max_retries': _env_int('INBOX_DELIVERY_MAX_RETRIES', 3, minimum=1),
            'delivery_backoff_seconds': _env_float('INBOX_DELIVERY_BACKOFF_SECONDS', 0.5, minimum=0.0),
            'delivery_max_backoff_seconds': _env_float('INBOX_DELIVERY_MAX_BACKOFF_SECONDS', 8.0, minimum=0.0),
            'replay_pending_limit_default': 25,
            'replay_pending_limit_max': 200,
        }

        metrics_alert_thresholds = {
            'pending_ratio_high': _env_float('INBOX_ALERT_PENDING_RATIO_HIGH', 0.35, minimum=0.0, maximum=1.0),
            'pending_min_count': _env_int('INBOX_ALERT_PENDING_MIN_COUNT', 3, minimum=0),
            'oldest_pending_age_seconds': _env_int('INBOX_ALERT_OLDEST_PENDING_AGE_SECONDS', 60 * 60, minimum=0),
            'replay_success_rate_low': _env_float('INBOX_ALERT_REPLAY_SUCCESS_RATE_LOW', 0.7, minimum=0.0, maximum=1.0),
            'replay_min_selected': _env_int('INBOX_ALERT_REPLAY_MIN_SELECTED', 3, minimum=0),
            'no_selection_ratio_high': _env_float('INBOX_ALERT_NO_SELECTION_RATIO_HIGH', 0.8, minimum=0.0, maximum=1.0),
            'no_selection_min_runs': _env_int('INBOX_ALERT_NO_SELECTION_MIN_RUNS', 5, minimum=0),
        }

        performance_alert_thresholds = {
            'operator_success_rate_low': _env_float('INBOX_ALERT_OPERATOR_SUCCESS_RATE_LOW', 0.7, minimum=0.0, maximum=1.0),
            'operator_min_selected': _env_int('INBOX_ALERT_OPERATOR_MIN_SELECTED', 3, minimum=0),
            'operator_no_selection_min_runs': _env_int('INBOX_ALERT_OPERATOR_NO_SELECTION_MIN_RUNS', 5, minimum=0),
            'operator_latency_spike_multiplier': _env_float('INBOX_ALERT_OPERATOR_LATENCY_SPIKE_MULTIPLIER', 2.0, minimum=1.0),
            'operator_latency_min_runs': _env_int('INBOX_ALERT_OPERATOR_LATENCY_MIN_RUNS', 3, minimum=0),
            'overall_success_rate_low': _env_float('INBOX_ALERT_OVERALL_SUCCESS_RATE_LOW', 0.7, minimum=0.0, maximum=1.0),
            'overall_min_selected': _env_int('INBOX_ALERT_OVERALL_MIN_SELECTED', 3, minimum=0),
        }

        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'generatedAt': datetime.now(UTC).isoformat(),
            'replay': replay_config,
            'metrics_alert_thresholds': metrics_alert_thresholds,
            'performance_alert_thresholds': performance_alert_thresholds,
        }

    @router.get('/inbox/ops/runbooks')
    def inbox_ops_runbooks(
        auth: AuthDep,
        code: Annotated[str | None, Query(max_length=120)] = None,
    ) -> dict[str, Any]:
        """Return alert runbooks for Smart Inbox operations and replay governance."""
        enforce_rate_limit(f'{auth.tenant_id}:inbox:ops:runbooks', 120, 60)
        runbooks = [
            {
                'code': 'pending_backlog_ratio_high',
                'title': 'Pending Delivery Backlog High',
                'severity': 'warning',
                'steps': [
                    'Open /inbox/delivery-failures?status=pending_retry and segment by network.',
                    'Check /inbox/delivery-failures/replay-runs/performance for operator bottlenecks.',
                    'Run replay-pending with a controlled limit and verify resolved movement.',
                ],
            },
            {
                'code': 'oldest_pending_age_high',
                'title': 'Oldest Pending Failure Age High',
                'severity': 'warning',
                'steps': [
                    'Identify the oldest failure from /inbox/delivery-failures list.',
                    'Attempt targeted replay for the failure id.',
                    'If replay fails repeatedly, resolve to manual_followup and notify owner.',
                ],
            },
            {
                'code': 'replay_success_rate_low',
                'title': 'Replay Success Rate Low',
                'severity': 'critical',
                'steps': [
                    'Inspect last errors in replay-pending and replay-bulk response items.',
                    'Verify vendor credentials and endpoint readiness for affected network.',
                    'Throttle replay batches while escalating provider incident.',
                ],
            },
            {
                'code': 'replay_runs_no_selection_spike',
                'title': 'Replay No-Selection Spike',
                'severity': 'warning',
                'steps': [
                    'Confirm queue input path still creates pending_retry failures.',
                    'Validate network filter and replay limit parameters used by operators.',
                    'Review approval pipeline to ensure failures are entering DLQ when delivery fails.',
                ],
            },
            {
                'code': 'operator_success_rate_low',
                'title': 'Operator Replay Success Rate Low',
                'severity': 'warning',
                'steps': [
                    'Open replay-runs/performance with operator filter.',
                    'Check recent replay items for not_found and delivery_failed statuses.',
                    'Pair operator with runbook owner until success rate recovers.',
                ],
            },
            {
                'code': 'operator_no_selection_only_runs',
                'title': 'Operator Producing Empty Replay Runs',
                'severity': 'warning',
                'steps': [
                    'Confirm operator uses correct network filter and tenant context.',
                    'Review pending queue count before replay execution.',
                    'Adjust playbook to avoid no-op replays during zero-backlog windows.',
                ],
            },
            {
                'code': 'operator_latency_spike',
                'title': 'Operator Replay Latency Spike',
                'severity': 'warning',
                'steps': [
                    'Inspect provider latency and timeout trends for the operator runs.',
                    'Reduce replay batch size and retry with smaller windows.',
                    'Escalate provider if p95 latency remains elevated.',
                ],
            },
        ]

        code_filter = code.strip().lower() if code else None
        if code_filter is not None:
            runbooks = [item for item in runbooks if str(item.get('code')) == code_filter]

        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'count': len(runbooks),
            'items': runbooks,
            'code_filter': code_filter,
        }

    @router.get('/inbox/ops/go-live-gate')
    def inbox_ops_go_live_gate(auth: AuthDep) -> dict[str, Any]:
        """Return strict pass/fail go-live checks for Smart Inbox delivery and replay operations."""
        enforce_rate_limit(f'{auth.tenant_id}:inbox:ops:go-live-gate', 120, 60)

        required_runbook_codes = {
            'pending_backlog_ratio_high',
            'oldest_pending_age_high',
            'replay_success_rate_low',
            'replay_runs_no_selection_spike',
            'operator_success_rate_low',
            'operator_no_selection_only_runs',
            'operator_latency_spike',
        }
        configured_runbooks = inbox_ops_runbooks(auth)['items']
        configured_codes = {str(item.get('code')) for item in configured_runbooks}
        runbook_coverage_complete = required_runbook_codes.issubset(configured_codes)

        delivery_max_retries = _env_int('INBOX_DELIVERY_MAX_RETRIES', 3, minimum=1)
        delivery_backoff_seconds = _env_float('INBOX_DELIVERY_BACKOFF_SECONDS', 0.5, minimum=0.0)
        delivery_max_backoff_seconds = _env_float('INBOX_DELIVERY_MAX_BACKOFF_SECONDS', 8.0, minimum=0.0)

        supported_vendor_ids = sorted(set(_NETWORK_VENDOR_MAP.values()))
        missing_vendor_credentials = [
            vendor_id for vendor_id in supported_vendor_ids
            if vendor_manager.get_credentials(vendor_id) is None
        ]
        live_contract_matrix_enabled = str(os.getenv('SOCIAL_CONTRACT_MATRIX_LIVE_ENABLED', '')).strip().lower() in {
            '1', 'true', 'yes', 'on'
        }

        checks = [
            {
                'code': 'delivery_retry_configured',
                'passed': delivery_max_retries >= 2 and delivery_max_backoff_seconds >= delivery_backoff_seconds,
                'detail': {
                    'delivery_max_retries': delivery_max_retries,
                    'delivery_backoff_seconds': delivery_backoff_seconds,
                    'delivery_max_backoff_seconds': delivery_max_backoff_seconds,
                },
            },
            {
                'code': 'dlq_operations_wired',
                'passed': isinstance(delivery_failures_memory, list) and isinstance(delivery_replay_runs_memory, list),
                'detail': {
                    'delivery_failures_store_present': isinstance(delivery_failures_memory, list),
                    'delivery_replay_runs_store_present': isinstance(delivery_replay_runs_memory, list),
                },
            },
            {
                'code': 'runbook_coverage_complete',
                'passed': runbook_coverage_complete,
                'detail': {
                    'required_count': len(required_runbook_codes),
                    'configured_count': len(configured_codes),
                    'missing_codes': sorted(required_runbook_codes - configured_codes),
                },
            },
            {
                'code': 'vendor_credentials_configured',
                'passed': len(missing_vendor_credentials) == 0,
                'detail': {
                    'supported_vendor_ids': supported_vendor_ids,
                    'missing_vendor_credentials': missing_vendor_credentials,
                },
            },
            {
                'code': 'live_contract_checks_enabled',
                'passed': live_contract_matrix_enabled,
                'detail': {
                    'env': 'SOCIAL_CONTRACT_MATRIX_LIVE_ENABLED',
                    'enabled': live_contract_matrix_enabled,
                },
            },
            {
                'code': 'alert_thresholds_sane',
                'passed': (
                    0.0 <= _env_float('INBOX_ALERT_PENDING_RATIO_HIGH', 0.35, minimum=0.0, maximum=1.0) <= 1.0
                    and 0.0 <= _env_float('INBOX_ALERT_REPLAY_SUCCESS_RATE_LOW', 0.7, minimum=0.0, maximum=1.0) <= 1.0
                    and 0.0 <= _env_float('INBOX_ALERT_NO_SELECTION_RATIO_HIGH', 0.8, minimum=0.0, maximum=1.0) <= 1.0
                ),
                'detail': {
                    'pending_ratio_high': _env_float('INBOX_ALERT_PENDING_RATIO_HIGH', 0.35, minimum=0.0, maximum=1.0),
                    'replay_success_rate_low': _env_float('INBOX_ALERT_REPLAY_SUCCESS_RATE_LOW', 0.7, minimum=0.0, maximum=1.0),
                    'no_selection_ratio_high': _env_float('INBOX_ALERT_NO_SELECTION_RATIO_HIGH', 0.8, minimum=0.0, maximum=1.0),
                },
            },
        ]

        blockers = [item['code'] for item in checks if not bool(item.get('passed'))]
        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'generatedAt': datetime.now(UTC).isoformat(),
            'overall_ready': len(blockers) == 0,
            'check_count': len(checks),
            'passed_count': sum(1 for item in checks if bool(item.get('passed'))),
            'failed_count': len(blockers),
            'blockers': blockers,
            'checks': checks,
        }

    @router.post(
        '/inbox/delivery-failures/{failure_id}/resolve',
        responses={404: {'description': 'Delivery failure not found'}},
    )
    def resolve_delivery_failure(failure_id: int, payload: DeliveryFailureResolveRequest, auth: AuthDep) -> dict[str, Any]:
        """Resolve a failed delivery and return the message to manual handling."""
        enforce_rate_limit(f'{auth.tenant_id}:inbox:delivery-failures:resolve', 120, 60)
        now_iso = datetime.now(UTC).isoformat()
        with _lock:
            failure = next(
                (
                    item for item in delivery_failures_memory
                    if item.get('tenant_id') == auth.tenant_id and int(item.get('id') or 0) == failure_id
                ),
                None,
            )
            if failure is None:
                raise HTTPException(status_code=404, detail='Delivery failure not found')

            message = next(
                (
                    item for item in messages_memory
                    if item.get('tenant_id') == auth.tenant_id and int(item.get('id') or 0) == int(failure.get('message_id') or 0)
                ),
                None,
            )

            if str(failure.get('status') or '').lower() == 'resolved':
                return {
                    'status': 'ok',
                    'tenant_id': auth.tenant_id,
                    'resolved': False,
                    'reason': 'already_resolved',
                    'failure': failure.copy(),
                    'message': message.copy() if message is not None else None,
                }

            failure['status'] = 'resolved'
            failure['resolution'] = 'manual_followup'
            failure['resolved_at'] = now_iso
            failure['resolved_by'] = payload.operator.strip()
            failure['resolution_note'] = payload.note.strip() if payload.note else None
            updated_failure = failure.copy()

            updated_message = None
            if message is not None:
                if str(message.get('status')) == 'requires_approval':
                    message['status'] = 'in_progress'
                message['replied'] = False
                message['replied_at'] = None
                message['response_delivery_status'] = 'manual_followup_required'
                message['response_delivery_failure_id'] = None
                message['response_delivery_resolution'] = 'manual_followup'
                message['updated_at'] = now_iso
                updated_message = message.copy()

        _audit(auth.tenant_id, 'inbox_auto_response_delivery_resolved', int(updated_failure.get('message_id') or 0))
        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'resolved': True,
            'failure': updated_failure,
            'message': updated_message,
        }

    @router.post('/inbox/delivery-failures/resolve-bulk')
    def resolve_delivery_failures_bulk(payload: DeliveryFailureBulkResolveRequest, auth: AuthDep) -> dict[str, Any]:
        """Resolve multiple failed deliveries into manual follow-up in one operation."""
        enforce_rate_limit(f'{auth.tenant_id}:inbox:delivery-failures:resolve-bulk', 60, 60)
        now_iso = datetime.now(UTC).isoformat()
        note = payload.note.strip() if payload.note else None
        deduped_ids: list[int] = []
        seen: set[int] = set()
        for raw_id in payload.failure_ids:
            if raw_id in seen:
                continue
            seen.add(raw_id)
            deduped_ids.append(raw_id)

        resolved_ids: list[int] = []
        already_resolved_ids: list[int] = []
        not_found_ids: list[int] = []
        updated_message_ids: list[int] = []

        with _lock:
            for failure_id in deduped_ids:
                failure = next(
                    (
                        item for item in delivery_failures_memory
                        if item.get('tenant_id') == auth.tenant_id and int(item.get('id') or 0) == failure_id
                    ),
                    None,
                )
                if failure is None:
                    not_found_ids.append(failure_id)
                    continue

                if str(failure.get('status') or '').lower() == 'resolved':
                    already_resolved_ids.append(failure_id)
                    continue

                failure['status'] = 'resolved'
                failure['resolution'] = 'manual_followup'
                failure['resolved_at'] = now_iso
                failure['resolved_by'] = payload.operator.strip()
                failure['resolution_note'] = note
                resolved_ids.append(failure_id)

                message = next(
                    (
                        item for item in messages_memory
                        if item.get('tenant_id') == auth.tenant_id and int(item.get('id') or 0) == int(failure.get('message_id') or 0)
                    ),
                    None,
                )
                if message is not None:
                    if str(message.get('status')) == 'requires_approval':
                        message['status'] = 'in_progress'
                    message['replied'] = False
                    message['replied_at'] = None
                    message['response_delivery_status'] = 'manual_followup_required'
                    message['response_delivery_failure_id'] = None
                    message['response_delivery_resolution'] = 'manual_followup'
                    message['updated_at'] = now_iso
                    updated_message_ids.append(int(message.get('id') or 0))

        for failure_id in resolved_ids:
            _audit(auth.tenant_id, 'inbox_auto_response_delivery_resolved_bulk', failure_id)

        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'resolved_count': len(resolved_ids),
            'already_resolved_count': len(already_resolved_ids),
            'not_found_count': len(not_found_ids),
            'resolved_ids': resolved_ids,
            'already_resolved_ids': already_resolved_ids,
            'not_found_ids': not_found_ids,
            'updated_message_ids': updated_message_ids,
        }

    # ── Saved replies library (§13.2 Saved Reply Library) ──────────────────────

    @router.post('/inbox/saved-replies')
    def create_saved_reply(payload: SavedReplyRequest, auth: AuthDep) -> dict[str, Any]:
        """ADDED: Create a pre-approved reply template in the saved replies library (§13.2)."""
        enforce_rate_limit(f'{auth.tenant_id}:inbox:saved-replies:create', 120, 60)
        with _lock:
            reply: dict[str, Any] = {
                'id': len(saved_replies_memory) + 1,
                'tenant_id': auth.tenant_id,
                'title': payload.title.strip(),
                'body': payload.body,
                'tags': [t.strip().lower() for t in payload.tags if t.strip()],
                'networks': [n.strip().lower() for n in payload.networks if n.strip()],
                'use_count': 0,
                'created_at': datetime.now(UTC).isoformat(),
                'updated_at': datetime.now(UTC).isoformat(),
            }
            saved_replies_memory.append(reply)
        _audit(auth.tenant_id, 'saved_reply_created', reply['id'])
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'reply': reply.copy()}

    @router.get('/inbox/saved-replies')
    def list_saved_replies(
        auth: AuthDep,
        search: Annotated[str | None, Query(max_length=120)] = None,
        tag: Annotated[str | None, Query(max_length=40)] = None,
        network: Annotated[str | None, Query(max_length=40)] = None,
        limit: Annotated[int, Query(ge=1, le=200)] = 50,
        offset: Annotated[int, Query(ge=0)] = 0,
    ) -> dict[str, Any]:
        """ADDED: List saved replies with search and filter (§13.2)."""
        enforce_rate_limit(f'{auth.tenant_id}:inbox:saved-replies:list', 240, 60)
        search_lc = search.strip().lower() if search else None
        tag_f = tag.strip().lower() if tag else None
        network_f = network.strip().lower() if network else None
        with _lock:
            items = [
                r.copy() for r in saved_replies_memory
                if r.get('tenant_id') == auth.tenant_id
                and (search_lc is None or search_lc in str(r.get('title', '')).lower() or search_lc in str(r.get('body', '')).lower())
                and (tag_f is None or tag_f in [str(t) for t in r.get('tags', [])])
                and (network_f is None or not r.get('networks') or network_f in [str(n) for n in r.get('networks', [])])
            ]
        items.sort(key=lambda r: int(r.get('use_count', 0)), reverse=True)
        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'count': len(items),
            'replies': items[offset: offset + limit],
            'limit': limit,
            'offset': offset,
        }

    @router.patch(
        '/inbox/saved-replies/{reply_id}',
        responses={404: {'description': REPLY_NOT_FOUND}},
    )
    def update_saved_reply(reply_id: int, payload: SavedReplyUpdateRequest, auth: AuthDep) -> dict[str, Any]:
        """ADDED: Update a saved reply."""
        enforce_rate_limit(f'{auth.tenant_id}:inbox:saved-replies:update', 120, 60)
        with _lock:
            reply = next(
                (r for r in saved_replies_memory if r.get('tenant_id') == auth.tenant_id and r.get('id') == reply_id),
                None,
            )
            if reply is None:
                raise HTTPException(status_code=404, detail=REPLY_NOT_FOUND)
            if payload.title is not None:
                reply['title'] = payload.title.strip()
            if payload.body is not None:
                reply['body'] = payload.body
            if payload.tags is not None:
                reply['tags'] = [t.strip().lower() for t in payload.tags if t.strip()]
            if payload.networks is not None:
                reply['networks'] = [n.strip().lower() for n in payload.networks if n.strip()]
            reply['updated_at'] = datetime.now(UTC).isoformat()
            updated = reply.copy()
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'reply': updated}

    @router.delete(
        '/inbox/saved-replies/{reply_id}',
        responses={404: {'description': REPLY_NOT_FOUND}},
    )
    def delete_saved_reply(reply_id: int, auth: AuthDep) -> dict[str, Any]:
        """ADDED: Delete a saved reply from the library."""
        enforce_rate_limit(f'{auth.tenant_id}:inbox:saved-replies:delete', 60, 60)
        with _lock:
            index = next(
                (i for i, r in enumerate(saved_replies_memory) if r.get('tenant_id') == auth.tenant_id and r.get('id') == reply_id),
                None,
            )
            if index is None:
                raise HTTPException(status_code=404, detail=REPLY_NOT_FOUND)
            saved_replies_memory.pop(index)
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'reply_id': reply_id, 'deleted': True}

    @router.post(
        '/inbox/messages/{message_id}/auto-respond',
        responses={404: {'description': MESSAGE_NOT_FOUND}, 422: {'description': 'Invalid auto-response request'}},
    )
    def auto_respond(message_id: int, payload: AutoResponseRequest, auth: AuthDep) -> dict[str, Any]:
        """Execute an auto-response from saved replies or generated suggestions and update message state."""
        enforce_rate_limit(f'{auth.tenant_id}:inbox:auto-respond', 180, 60)
        with _lock:
            message = next(
                (m for m in messages_memory if m.get('tenant_id') == auth.tenant_id and m.get('id') == message_id),
                None,
            )
            if message is None:
                raise HTTPException(status_code=404, detail=MESSAGE_NOT_FOUND)

        response_text = ''
        source = 'suggested_reply'
        saved_reply: dict[str, Any] | None = None
        if payload.saved_reply_id is not None:
            saved_reply = _resolve_saved_reply(auth.tenant_id, payload.saved_reply_id)
            if saved_reply is None:
                raise HTTPException(status_code=422, detail='Saved reply not found for tenant')
            if saved_reply.get('networks') and str(message.get('network')) not in [str(n) for n in saved_reply.get('networks', [])]:
                raise HTTPException(status_code=422, detail='Saved reply is not configured for this network')
            response_text = str(saved_reply.get('body', ''))
            source = 'saved_reply'
        else:
            suggestions = [str(item) for item in message.get('suggested_replies', [])]
            suggestion_index = payload.suggestion_index if payload.suggestion_index is not None else 0
            if suggestion_index >= len(suggestions):
                raise HTTPException(status_code=422, detail='Suggested reply index is out of range')
            response_text = suggestions[suggestion_index]

        now_iso = datetime.now(UTC).isoformat()
        approval_required = payload.require_approval or str(message.get('message_type')) == 'crisis'
        with _lock:
            if saved_reply is not None:
                for reply in saved_replies_memory:
                    if reply.get('tenant_id') == auth.tenant_id and reply.get('id') == payload.saved_reply_id:
                        reply['use_count'] = int(reply.get('use_count', 0)) + 1
                        reply['updated_at'] = now_iso
                        break
            message['last_response_preview'] = response_text[:500]
            message['last_response_source'] = source
            message['last_response_by'] = payload.responder.strip()
            message['last_response_at'] = now_iso
            message['replied'] = not approval_required
            message['replied_at'] = now_iso if not approval_required else None
            message['status'] = 'requires_approval' if approval_required else 'complete'
            message['updated_at'] = now_iso
            updated = message.copy()

        _audit(auth.tenant_id, 'inbox_auto_response_executed', message_id)
        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'message': updated,
            'response': {
                'text': response_text,
                'source': source,
                'approval_required': approval_required,
                'delivered': not approval_required,
            },
        }

    @router.post(
        '/inbox/messages/{message_id}/approve-response',
        responses={
            404: {'description': MESSAGE_NOT_FOUND},
            409: {'description': 'No approval-pending response exists'},
            422: {'description': 'Unsupported delivery network'},
            502: {'description': 'Outbound provider delivery failed'},
        },
    )
    async def approve_response(message_id: int, payload: ResponseApprovalRequest, auth: AuthDep) -> dict[str, Any]:
        """Approve and deliver a staged auto-response for messages awaiting approval."""
        enforce_rate_limit(f'{auth.tenant_id}:inbox:approve-response', 180, 60)
        with _lock:
            message = next(
                (m for m in messages_memory if m.get('tenant_id') == auth.tenant_id and m.get('id') == message_id),
                None,
            )
            if message is None:
                raise HTTPException(status_code=404, detail=MESSAGE_NOT_FOUND)
            if str(message.get('status')) != 'requires_approval' or not str(message.get('last_response_preview', '')).strip():
                raise HTTPException(status_code=409, detail='No approval-pending response exists')

            network = str(message.get('network', ''))
            external_message_id = str(message.get('external_message_id') or message.get('id') or '')
            response_text = str(message.get('last_response_preview', ''))

        vendor_id, endpoint_template = _resolve_delivery_target(network)
        endpoint = endpoint_template.replace('{message_id}', external_message_id)

        request_payload = {
            'message_id': external_message_id,
            'reply_text': response_text,
            'network': network,
            'approved_by': payload.approver.strip(),
        }
        idempotency_key = str(
            message.get('response_delivery_idempotency_key')
            or _build_delivery_idempotency_key(auth.tenant_id, message_id, response_text)
        )
        request_payload['idempotency_key'] = idempotency_key
        vendor_response, delivery_errors, attempts_made = await _attempt_outbound_delivery(
            vendor_id=vendor_id,
            endpoint=endpoint,
            request_payload=request_payload,
            idempotency_key=idempotency_key,
        )

        if vendor_response is None:
            failure = _append_delivery_failure(
                auth.tenant_id,
                message_id=message_id,
                network=network,
                vendor_id=vendor_id,
                endpoint=endpoint,
                payload=request_payload,
                errors=delivery_errors,
            )
            with _lock:
                message = next(
                    (m for m in messages_memory if m.get('tenant_id') == auth.tenant_id and m.get('id') == message_id),
                    None,
                )
                if message is not None:
                    message['response_delivery_status'] = 'failed'
                    message['response_delivery_attempts'] = attempts_made
                    message['response_delivery_failure_id'] = failure.get('id')
                    message['response_delivery_last_error'] = delivery_errors[-1] if delivery_errors else 'delivery failed'
                    message['response_delivery_idempotency_key'] = idempotency_key
                    message['updated_at'] = datetime.now(UTC).isoformat()
            raise HTTPException(status_code=502, detail=f'Approved response delivery failed after retries; failure_id={failure.get("id")}')

        now_iso = datetime.now(UTC).isoformat()
        with _lock:
            message = next(
                (m for m in messages_memory if m.get('tenant_id') == auth.tenant_id and m.get('id') == message_id),
                None,
            )
            if message is None:
                raise HTTPException(status_code=404, detail=MESSAGE_NOT_FOUND)

            message['status'] = 'complete'
            message['replied'] = True
            message['replied_at'] = now_iso
            message['response_approved_by'] = payload.approver.strip()
            message['response_approved_at'] = now_iso
            message['response_approval_note'] = payload.note.strip() if payload.note else None
            message['response_delivered_at'] = now_iso
            message['response_delivery_vendor'] = vendor_id
            message['response_delivery_status'] = 'sent'
            message['response_delivery_attempts'] = attempts_made
            message['response_delivery_result'] = vendor_response
            message['response_delivery_failure_id'] = None
            message['response_delivery_last_error'] = None
            message['response_delivery_idempotency_key'] = idempotency_key
            message['updated_at'] = now_iso
            updated = message.copy()

        _audit(auth.tenant_id, 'inbox_auto_response_approved', message_id)
        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'message': updated,
            'response': {
                'text': str(updated.get('last_response_preview', '')),
                'source': updated.get('last_response_source'),
                'approved_by': updated.get('response_approved_by'),
                'delivered': True,
            },
        }

    @router.post(
        '/inbox/messages/{message_id}/reject-response',
        responses={404: {'description': MESSAGE_NOT_FOUND}, 409: {'description': 'No approval-pending response exists'}},
    )
    def reject_response(message_id: int, payload: ResponseRejectionRequest, auth: AuthDep) -> dict[str, Any]:
        """Reject a staged auto-response and return the message to active handling."""
        enforce_rate_limit(f'{auth.tenant_id}:inbox:reject-response', 180, 60)
        now_iso = datetime.now(UTC).isoformat()
        with _lock:
            message = next(
                (m for m in messages_memory if m.get('tenant_id') == auth.tenant_id and m.get('id') == message_id),
                None,
            )
            if message is None:
                raise HTTPException(status_code=404, detail=MESSAGE_NOT_FOUND)
            if str(message.get('status')) != 'requires_approval' or not str(message.get('last_response_preview', '')).strip():
                raise HTTPException(status_code=409, detail='No approval-pending response exists')

            message['status'] = 'in_progress'
            message['replied'] = False
            message['replied_at'] = None
            message['response_rejected_by'] = payload.reviewer.strip()
            message['response_rejected_at'] = now_iso
            message['response_rejection_note'] = payload.note.strip() if payload.note else None
            message['updated_at'] = now_iso
            updated = message.copy()

        _audit(auth.tenant_id, 'inbox_auto_response_rejected', message_id)
        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'message': updated,
            'response': {
                'text': str(updated.get('last_response_preview', '')),
                'source': updated.get('last_response_source'),
                'rejected_by': updated.get('response_rejected_by'),
                'delivered': False,
            },
        }

    return router
