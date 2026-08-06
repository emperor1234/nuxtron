from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..deps import AuthContext, require_auth

AuthDep = Annotated[AuthContext, Depends(require_auth)]


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


class ManychatTagCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    color: str = Field(default='#3b82f6', max_length=16)


class ManychatSegmentCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    description: str = Field(default='', max_length=400)
    conditions: list[dict[str, Any]] = Field(default_factory=list)


class ManychatFlowCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    channel: str = Field(default='instagram', max_length=40)
    trigger_type: str = Field(default='keyword', max_length=80)
    trigger_value: str = Field(min_length=1, max_length=200)
    steps: list[dict[str, Any]] = Field(default_factory=list)
    status: str = Field(default='active', pattern=r'^(active|paused|draft)$')


class ManychatBroadcastCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    channel: str = Field(default='instagram', max_length=40)
    target_segment_ids: list[int] = Field(default_factory=list)
    message: str = Field(min_length=1, max_length=2000)
    scheduled_for: str | None = Field(default=None, max_length=80)


class ManychatSequenceCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    channel: str = Field(default='instagram', max_length=40)
    steps: list[dict[str, Any]] = Field(default_factory=list)
    enrollment_trigger: str = Field(default='tag_added', max_length=80)


class ManychatKeywordCreateRequest(BaseModel):
    keyword: str = Field(min_length=1, max_length=120)
    channel: str = Field(default='instagram', max_length=40)
    reply_text: str = Field(min_length=1, max_length=1000)
    assign_tag_ids: list[int] = Field(default_factory=list)


class ManychatEventSimulationRequest(BaseModel):
    channel: str = Field(default='instagram', max_length=40)
    message_text: str = Field(min_length=1, max_length=1000)
    contact_handle: str = Field(min_length=1, max_length=120)


class ManychatContactTagAssignRequest(BaseModel):
    contact_handle: str = Field(min_length=1, max_length=120)
    tag_id: int = Field(gt=0)


class ManychatSequenceEnrollRequest(BaseModel):
    contact_handle: str = Field(min_length=1, max_length=120)
    sequence_id: int = Field(gt=0)


@dataclass
class _ManychatState:
    lock: threading.Lock = field(default_factory=threading.Lock)
    tags: list[dict[str, Any]] = field(default_factory=list)
    segments: list[dict[str, Any]] = field(default_factory=list)
    flows: list[dict[str, Any]] = field(default_factory=list)
    broadcasts: list[dict[str, Any]] = field(default_factory=list)
    sequences: list[dict[str, Any]] = field(default_factory=list)
    keywords: list[dict[str, Any]] = field(default_factory=list)
    contact_tags: dict[str, set[int]] = field(default_factory=dict)
    sequence_enrollments: list[dict[str, Any]] = field(default_factory=list)
    automation_runs: list[dict[str, Any]] = field(default_factory=list)


STATE = _ManychatState()


def _seed_defaults(tenant_id: str) -> None:
    with STATE.lock:
        if not any(item.get('tenant_id') == tenant_id for item in STATE.tags):
            STATE.tags.extend(
                [
                    {
                        'id': len(STATE.tags) + 1,
                        'tenant_id': tenant_id,
                        'name': 'Lead',
                        'color': '#16a34a',
                        'created_at': _utc_now(),
                    },
                    {
                        'id': len(STATE.tags) + 2,
                        'tenant_id': tenant_id,
                        'name': 'VIP',
                        'color': '#f59e0b',
                        'created_at': _utc_now(),
                    },
                ]
            )

        if not any(item.get('tenant_id') == tenant_id for item in STATE.segments):
            STATE.segments.append(
                {
                    'id': len(STATE.segments) + 1,
                    'tenant_id': tenant_id,
                    'name': 'New Leads (7d)',
                    'description': 'Contacts tagged Lead in the last 7 days',
                    'conditions': [
                        {'field': 'tag', 'operator': 'contains', 'value': 'Lead'},
                        {'field': 'created_at', 'operator': 'gte_days_ago', 'value': 7},
                    ],
                    'created_at': _utc_now(),
                }
            )

        if not any(item.get('tenant_id') == tenant_id for item in STATE.keywords):
            lead_tag = next((item for item in STATE.tags if item.get('tenant_id') == tenant_id and item.get('name') == 'Lead'), None)
            STATE.keywords.append(
                {
                    'id': len(STATE.keywords) + 1,
                    'tenant_id': tenant_id,
                    'keyword': 'demo',
                    'channel': 'instagram',
                    'reply_text': 'Thanks for your interest. We sent the demo details via DM.',
                    'assign_tag_ids': [int(lead_tag['id'])] if lead_tag else [],
                    'created_at': _utc_now(),
                }
            )

        if not any(item.get('tenant_id') == tenant_id for item in STATE.flows):
            STATE.flows.append(
                {
                    'id': len(STATE.flows) + 1,
                    'tenant_id': tenant_id,
                    'name': 'IG Demo Request Flow',
                    'channel': 'instagram',
                    'trigger_type': 'keyword',
                    'trigger_value': 'demo',
                    'steps': [
                        {'type': 'message', 'text': 'Welcome! Tell us your use case.'},
                        {'type': 'tag', 'name': 'Lead'},
                        {'type': 'notify', 'target': 'sales_queue'},
                    ],
                    'status': 'active',
                    'created_at': _utc_now(),
                    'updated_at': _utc_now(),
                }
            )


def create_social_manychat_router() -> APIRouter:  # noqa: C901
    router = APIRouter(prefix='/social/manychat', tags=['social-manychat'])

    @router.get('/overview')
    def get_manychat_overview(auth: AuthDep) -> dict[str, Any]:
        _seed_defaults(auth.tenant_id)
        with STATE.lock:
            tenant_tags = [item for item in STATE.tags if item.get('tenant_id') == auth.tenant_id]
            tenant_segments = [item for item in STATE.segments if item.get('tenant_id') == auth.tenant_id]
            tenant_flows = [item for item in STATE.flows if item.get('tenant_id') == auth.tenant_id]
            tenant_broadcasts = [item for item in STATE.broadcasts if item.get('tenant_id') == auth.tenant_id]
            tenant_sequences = [item for item in STATE.sequences if item.get('tenant_id') == auth.tenant_id]
            tenant_keywords = [item for item in STATE.keywords if item.get('tenant_id') == auth.tenant_id]
            tenant_runs = [item for item in STATE.automation_runs if item.get('tenant_id') == auth.tenant_id]

        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'counts': {
                'tags': len(tenant_tags),
                'segments': len(tenant_segments),
                'flows': len(tenant_flows),
                'broadcasts': len(tenant_broadcasts),
                'sequences': len(tenant_sequences),
                'keywords': len(tenant_keywords),
                'automation_runs': len(tenant_runs),
            },
            'feature_matrix': [
                {'feature': 'Audience tags', 'status': 'implemented'},
                {'feature': 'Audience segments', 'status': 'implemented'},
                {'feature': 'Keyword automations', 'status': 'implemented'},
                {'feature': 'Flow builder entities', 'status': 'implemented'},
                {'feature': 'Broadcast campaign entities', 'status': 'implemented'},
                {'feature': 'Drip sequence entities', 'status': 'implemented'},
            ],
            'vendors': [
                {'vendor': 'Meta', 'products': ['Instagram Graph API', 'Facebook Messenger API'], 'use_case': 'Inbound messages, keyword triggers, outbound replies'},
                {'vendor': 'WhatsApp Business Platform', 'products': ['Cloud API'], 'use_case': 'Template and session messaging automations'},
                {'vendor': 'Zapier', 'products': ['Webhooks', 'Actions'], 'use_case': 'External workflow triggers and CRM syncs'},
                {'vendor': 'Make', 'products': ['Scenarios', 'Webhooks'], 'use_case': 'No-code orchestration across SaaS systems'},
                {'vendor': 'OpenAI-compatible LLM provider', 'products': ['Text generation API'], 'use_case': 'AI reply drafts and dynamic copy'},
            ],
        }

    @router.get('/tags')
    def list_manychat_tags(auth: AuthDep) -> dict[str, Any]:
        _seed_defaults(auth.tenant_id)
        with STATE.lock:
            items = [item.copy() for item in STATE.tags if item.get('tenant_id') == auth.tenant_id]
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'items': items}

    @router.post('/tags')
    def create_manychat_tag(payload: ManychatTagCreateRequest, auth: AuthDep) -> dict[str, Any]:
        with STATE.lock:
            item = {
                'id': len(STATE.tags) + 1,
                'tenant_id': auth.tenant_id,
                'name': payload.name.strip(),
                'color': payload.color.strip() or '#3b82f6',
                'created_at': _utc_now(),
            }
            STATE.tags.append(item)
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'item': item}

    @router.get('/segments')
    def list_manychat_segments(auth: AuthDep) -> dict[str, Any]:
        _seed_defaults(auth.tenant_id)
        with STATE.lock:
            items = [item.copy() for item in STATE.segments if item.get('tenant_id') == auth.tenant_id]
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'items': items}

    @router.post('/segments')
    def create_manychat_segment(payload: ManychatSegmentCreateRequest, auth: AuthDep) -> dict[str, Any]:
        with STATE.lock:
            item = {
                'id': len(STATE.segments) + 1,
                'tenant_id': auth.tenant_id,
                'name': payload.name.strip(),
                'description': payload.description.strip(),
                'conditions': payload.conditions,
                'created_at': _utc_now(),
            }
            STATE.segments.append(item)
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'item': item}

    @router.post('/contacts/tag-assign', responses={404: {'description': 'Tag not found for tenant.'}})
    def assign_manychat_contact_tag(payload: ManychatContactTagAssignRequest, auth: AuthDep) -> dict[str, Any]:
        with STATE.lock:
            tag = next((item for item in STATE.tags if item.get('tenant_id') == auth.tenant_id and int(item.get('id', 0)) == payload.tag_id), None)
            if tag is None:
                raise HTTPException(status_code=404, detail='Tag not found for tenant.')

            handle_key = f"{auth.tenant_id}:{payload.contact_handle.strip().lower()}"
            assigned = STATE.contact_tags.setdefault(handle_key, set())
            assigned.add(payload.tag_id)

        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'contact_handle': payload.contact_handle,
            'tag_id': payload.tag_id,
            'assigned_tag_ids': sorted(assigned),
        }

    @router.get('/flows')
    def list_manychat_flows(auth: AuthDep) -> dict[str, Any]:
        _seed_defaults(auth.tenant_id)
        with STATE.lock:
            items = [item.copy() for item in STATE.flows if item.get('tenant_id') == auth.tenant_id]
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'items': items}

    @router.post('/flows')
    def create_manychat_flow(payload: ManychatFlowCreateRequest, auth: AuthDep) -> dict[str, Any]:
        with STATE.lock:
            item = {
                'id': len(STATE.flows) + 1,
                'tenant_id': auth.tenant_id,
                'name': payload.name.strip(),
                'channel': payload.channel.strip().lower(),
                'trigger_type': payload.trigger_type.strip().lower(),
                'trigger_value': payload.trigger_value.strip().lower(),
                'steps': payload.steps,
                'status': payload.status,
                'created_at': _utc_now(),
                'updated_at': _utc_now(),
            }
            STATE.flows.append(item)
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'item': item}

    @router.get('/keywords')
    def list_manychat_keywords(auth: AuthDep) -> dict[str, Any]:
        _seed_defaults(auth.tenant_id)
        with STATE.lock:
            items = [item.copy() for item in STATE.keywords if item.get('tenant_id') == auth.tenant_id]
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'items': items}

    @router.post('/keywords')
    def create_manychat_keyword(payload: ManychatKeywordCreateRequest, auth: AuthDep) -> dict[str, Any]:
        with STATE.lock:
            item = {
                'id': len(STATE.keywords) + 1,
                'tenant_id': auth.tenant_id,
                'keyword': payload.keyword.strip().lower(),
                'channel': payload.channel.strip().lower(),
                'reply_text': payload.reply_text.strip(),
                'assign_tag_ids': payload.assign_tag_ids,
                'created_at': _utc_now(),
            }
            STATE.keywords.append(item)
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'item': item}

    @router.get('/broadcasts')
    def list_manychat_broadcasts(auth: AuthDep) -> dict[str, Any]:
        with STATE.lock:
            items = [item.copy() for item in STATE.broadcasts if item.get('tenant_id') == auth.tenant_id]
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'items': items}

    @router.post('/broadcasts')
    def create_manychat_broadcast(payload: ManychatBroadcastCreateRequest, auth: AuthDep) -> dict[str, Any]:
        scheduled_for = payload.scheduled_for.strip() if isinstance(payload.scheduled_for, str) else (_utc_now())
        with STATE.lock:
            item = {
                'id': len(STATE.broadcasts) + 1,
                'tenant_id': auth.tenant_id,
                'name': payload.name.strip(),
                'channel': payload.channel.strip().lower(),
                'target_segment_ids': payload.target_segment_ids,
                'message': payload.message.strip(),
                'status': 'scheduled',
                'scheduled_for': scheduled_for,
                'estimated_recipients': max(1, len(payload.target_segment_ids) * 42),
                'created_at': _utc_now(),
            }
            STATE.broadcasts.append(item)
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'item': item}

    @router.post('/broadcasts/{broadcast_id}/send', responses={404: {'description': 'Broadcast not found for tenant.'}})
    def send_manychat_broadcast(broadcast_id: int, auth: AuthDep) -> dict[str, Any]:
        with STATE.lock:
            broadcast = next((item for item in STATE.broadcasts if item.get('tenant_id') == auth.tenant_id and int(item.get('id', 0)) == broadcast_id), None)
            if broadcast is None:
                raise HTTPException(status_code=404, detail='Broadcast not found for tenant.')
            broadcast['status'] = 'sent'
            broadcast['sent_at'] = _utc_now()
            updated = broadcast.copy()
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'item': updated}

    @router.get('/sequences')
    def list_manychat_sequences(auth: AuthDep) -> dict[str, Any]:
        with STATE.lock:
            items = [item.copy() for item in STATE.sequences if item.get('tenant_id') == auth.tenant_id]
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'items': items}

    @router.post('/sequences')
    def create_manychat_sequence(payload: ManychatSequenceCreateRequest, auth: AuthDep) -> dict[str, Any]:
        with STATE.lock:
            item = {
                'id': len(STATE.sequences) + 1,
                'tenant_id': auth.tenant_id,
                'name': payload.name.strip(),
                'channel': payload.channel.strip().lower(),
                'steps': payload.steps,
                'enrollment_trigger': payload.enrollment_trigger.strip(),
                'created_at': _utc_now(),
            }
            STATE.sequences.append(item)
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'item': item}

    @router.post('/sequences/enroll', responses={404: {'description': 'Sequence not found for tenant.'}})
    def enroll_manychat_sequence(payload: ManychatSequenceEnrollRequest, auth: AuthDep) -> dict[str, Any]:
        with STATE.lock:
            sequence = next((item for item in STATE.sequences if item.get('tenant_id') == auth.tenant_id and int(item.get('id', 0)) == payload.sequence_id), None)
            if sequence is None:
                raise HTTPException(status_code=404, detail='Sequence not found for tenant.')
            enrollment = {
                'id': len(STATE.sequence_enrollments) + 1,
                'tenant_id': auth.tenant_id,
                'sequence_id': payload.sequence_id,
                'contact_handle': payload.contact_handle.strip(),
                'status': 'active',
                'next_step_at': (datetime.now(UTC) + timedelta(hours=24)).isoformat(),
                'created_at': _utc_now(),
            }
            STATE.sequence_enrollments.append(enrollment)
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'enrollment': enrollment}

    @router.post('/simulate-event')
    def simulate_manychat_event(payload: ManychatEventSimulationRequest, auth: AuthDep) -> dict[str, Any]:
        _seed_defaults(auth.tenant_id)
        normalized_channel = payload.channel.strip().lower()
        normalized_text = payload.message_text.strip().lower()
        handle_key = f"{auth.tenant_id}:{payload.contact_handle.strip().lower()}"

        with STATE.lock:
            matching_keywords = [
                item for item in STATE.keywords
                if item.get('tenant_id') == auth.tenant_id
                and str(item.get('channel') or '').lower() == normalized_channel
                and str(item.get('keyword') or '') in normalized_text
            ]

            matching_flows = [
                item for item in STATE.flows
                if item.get('tenant_id') == auth.tenant_id
                and str(item.get('status') or '') == 'active'
                and str(item.get('channel') or '') == normalized_channel
                and str(item.get('trigger_type') or '') == 'keyword'
                and str(item.get('trigger_value') or '') in normalized_text
            ]

            assigned_tag_ids = STATE.contact_tags.setdefault(handle_key, set())
            replies: list[str] = []
            for keyword in matching_keywords:
                replies.append(str(keyword.get('reply_text') or ''))
                for tag_id in keyword.get('assign_tag_ids') or []:
                    assigned_tag_ids.add(int(tag_id))

            run = {
                'id': len(STATE.automation_runs) + 1,
                'tenant_id': auth.tenant_id,
                'channel': normalized_channel,
                'contact_handle': payload.contact_handle.strip(),
                'message_text': payload.message_text,
                'keyword_matches': [item.get('keyword') for item in matching_keywords],
                'flow_matches': [item.get('name') for item in matching_flows],
                'replies': replies,
                'assigned_tag_ids': sorted(assigned_tag_ids),
                'created_at': _utc_now(),
            }
            STATE.automation_runs.append(run)

        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'run': run}

    return router
