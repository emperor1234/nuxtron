# pyright: reportUnknownVariableType=false, reportUnknownArgumentType=false, reportUnknownParameterType=false, reportUnknownMemberType=false, reportUnusedFunction=false
"""
Sales Sequences (HubSpot Sales Hub §5.3)
NEW: Multi-touch outreach cadences — email, call, LinkedIn, task steps.
Auto-pause on reply; resume on go-cold. Performance analytics per step.
"""
import threading
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from ..deps import AuthContext, require_auth

AuthDep = Annotated[AuthContext, Depends(require_auth)]

SEQUENCE_NOT_FOUND = 'Sequence not found.'
ENROLLMENT_NOT_FOUND = 'Enrollment not found.'
STEP_TYPES = {'email', 'call', 'linkedin', 'task', 'sms', 'video'}


class SequenceStepModel(BaseModel):
    step_type: str = Field(default='email', max_length=20)
    delay_days: int = Field(default=1, ge=0, le=365)
    delay_hours: int = Field(default=0, ge=0, le=23)
    subject: str = Field(default='', max_length=200)
    body: str = Field(default='', max_length=10000)
    task_description: str = Field(default='', max_length=500)


class SequenceCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str = Field(default='', max_length=1000)
    steps: list[SequenceStepModel] = Field(default_factory=list, max_length=20)


class EnrollmentCreateRequest(BaseModel):
    sequence_id: int = Field(ge=1)
    contact_id: str = Field(min_length=1, max_length=100)
    contact_email: str = Field(min_length=1, max_length=200)
    contact_name: str = Field(default='', max_length=200)


class StepOutcomeRequest(BaseModel):
    outcome: str = Field(max_length=50)  # replied, called, connected, completed, skipped
    notes: str = Field(default='', max_length=1000)


def create_sequences_router(  # NOSONAR
    *,
    enforce_rate_limit: Callable[[str, int, int], None],
    sequences_memory: list[dict[str, Any]],
    enrollments_memory: list[dict[str, Any]],
    step_events_memory: list[dict[str, Any]],
    audit_log_memory: list[dict[str, Any]],
) -> APIRouter:
    """NEW: Sales sequences router — HubSpot Sales Hub §5.3."""
    router = APIRouter()
    _lock = threading.Lock()

    def _append_audit(tenant_id: str, action: str, ref_id: int | None = None) -> None:
        with _lock:
            audit_log_memory.append({
                'id': len(audit_log_memory) + 1,
                'tenant_id': tenant_id,
                'action': action,
                'ref_id': ref_id,
                'created_at': datetime.now(UTC).isoformat(),
                'source': 'sequences-router',
            })

    @router.post('/sequences', summary='Create sales sequence')
    def create_sequence(payload: SequenceCreateRequest, auth: AuthDep) -> dict[str, Any]:
        """NEW: Create a multi-step sales outreach sequence."""
        enforce_rate_limit(f'{auth.tenant_id}:sequences:create', 60, 60)
        steps = []
        for i, s in enumerate(payload.steps):
            step_type = s.step_type.strip().lower()
            if step_type not in STEP_TYPES:
                step_type = 'email'
            steps.append({
                'position': i + 1,
                'step_type': step_type,
                'delay_days': s.delay_days,
                'delay_hours': s.delay_hours,
                'subject': s.subject,
                'body': s.body,
                'task_description': s.task_description,
            })
        with _lock:
            seq = {
                'id': len(sequences_memory) + 1,
                'tenant_id': auth.tenant_id,
                'name': payload.name,
                'description': payload.description,
                'steps': steps,
                'step_count': len(steps),
                'status': 'active',
                'enrollment_count': 0,
                'created_at': datetime.now(UTC).isoformat(),
                'updated_at': datetime.now(UTC).isoformat(),
            }
            sequences_memory.append(seq)
        _append_audit(auth.tenant_id, 'sequence_created', seq['id'])
        return {'status': 'ok', 'sequence': seq}

    @router.get('/sequences', summary='List sequences')
    def list_sequences(
        auth: AuthDep,
        limit: Annotated[int, Query(ge=1, le=100)] = 20,
        offset: Annotated[int, Query(ge=0)] = 0,
    ) -> dict[str, Any]:
        """NEW: List all sequences for this tenant."""
        enforce_rate_limit(f'{auth.tenant_id}:sequences:list', 120, 60)
        with _lock:
            items = [s.copy() for s in sequences_memory if s.get('tenant_id') == auth.tenant_id]
        items.sort(key=lambda x: str(x.get('created_at', '')), reverse=True)
        return {'status': 'ok', 'sequences': items[offset:offset + limit], 'total': len(items)}

    @router.get('/sequences/{sequence_id}', responses={404: {'description': SEQUENCE_NOT_FOUND}})
    def get_sequence(sequence_id: int, auth: AuthDep) -> dict[str, Any]:
        """NEW: Get a single sequence with its steps."""
        enforce_rate_limit(f'{auth.tenant_id}:sequences:get', 120, 60)
        with _lock:
            seq = next((s.copy() for s in sequences_memory
                        if s.get('id') == sequence_id and s.get('tenant_id') == auth.tenant_id), None)
        if seq is None:
            raise HTTPException(status_code=404, detail=SEQUENCE_NOT_FOUND)
        return {'status': 'ok', 'sequence': seq}

    @router.post('/sequences/{sequence_id}/enroll', responses={404: {'description': SEQUENCE_NOT_FOUND}})
    def enroll_contact(sequence_id: int, payload: EnrollmentCreateRequest, auth: AuthDep) -> dict[str, Any]:
        """NEW: Enroll a contact into a sequence."""
        enforce_rate_limit(f'{auth.tenant_id}:sequences:enroll', 120, 60)
        with _lock:
            seq = next((s for s in sequences_memory
                        if s.get('id') == sequence_id and s.get('tenant_id') == auth.tenant_id), None)
            if seq is None:
                raise HTTPException(status_code=404, detail=SEQUENCE_NOT_FOUND)
            # Check not already actively enrolled
            existing = next((e for e in enrollments_memory
                             if e.get('sequence_id') == sequence_id
                             and e.get('contact_id') == payload.contact_id
                             and e.get('status') == 'active'), None)
            if existing:
                return {'status': 'already_enrolled', 'enrollment': existing.copy()}
            enrollment = {
                'id': len(enrollments_memory) + 1,
                'tenant_id': auth.tenant_id,
                'sequence_id': sequence_id,
                'sequence_name': seq.get('name', ''),
                'contact_id': payload.contact_id,
                'contact_email': payload.contact_email,
                'contact_name': payload.contact_name,
                'current_step': 1,
                'total_steps': seq.get('step_count', 0),
                'status': 'active',  # active, paused, completed, replied, unsubscribed
                'reply_received': False,
                'enrolled_at': datetime.now(UTC).isoformat(),
                'last_activity_at': datetime.now(UTC).isoformat(),
            }
            enrollments_memory.append(enrollment)
            seq['enrollment_count'] = seq.get('enrollment_count', 0) + 1
        _append_audit(auth.tenant_id, 'sequence_contact_enrolled', enrollment['id'])
        return {'status': 'ok', 'enrollment': enrollment}

    @router.get('/sequences/{sequence_id}/enrollments', responses={404: {'description': SEQUENCE_NOT_FOUND}})
    def list_enrollments(
        sequence_id: int,
        auth: AuthDep,
        status: Annotated[str | None, Query(max_length=20)] = None,
        limit: Annotated[int, Query(ge=1, le=200)] = 50,
        offset: Annotated[int, Query(ge=0)] = 0,
    ) -> dict[str, Any]:
        """NEW: List enrollments for a sequence."""
        enforce_rate_limit(f'{auth.tenant_id}:sequences:enrollments', 120, 60)
        with _lock:
            seq = next((s for s in sequences_memory
                        if s.get('id') == sequence_id and s.get('tenant_id') == auth.tenant_id), None)
            if seq is None:
                raise HTTPException(status_code=404, detail=SEQUENCE_NOT_FOUND)
            items = [e.copy() for e in enrollments_memory
                     if e.get('sequence_id') == sequence_id
                     and (status is None or e.get('status') == status)]
        return {'status': 'ok', 'enrollments': items[offset:offset + limit], 'total': len(items)}

    @router.post('/sequences/enrollments/{enrollment_id}/step-outcome',
                 responses={404: {'description': ENROLLMENT_NOT_FOUND}})
    def record_step_outcome(enrollment_id: int, payload: StepOutcomeRequest, auth: AuthDep) -> dict[str, Any]:
        """NEW: Record outcome for current step (replied, called, etc.)."""
        enforce_rate_limit(f'{auth.tenant_id}:sequences:step-outcome', 120, 60)
        with _lock:
            enr = next((e for e in enrollments_memory
                        if e.get('id') == enrollment_id and e.get('tenant_id') == auth.tenant_id), None)
            if enr is None:
                raise HTTPException(status_code=404, detail=ENROLLMENT_NOT_FOUND)
            outcome = payload.outcome.strip().lower()
            event = {
                'id': len(step_events_memory) + 1,
                'tenant_id': auth.tenant_id,
                'enrollment_id': enrollment_id,
                'sequence_id': enr.get('sequence_id'),
                'contact_id': enr.get('contact_id'),
                'step_position': enr.get('current_step'),
                'outcome': outcome,
                'notes': payload.notes,
                'created_at': datetime.now(UTC).isoformat(),
            }
            step_events_memory.append(event)
            # Auto-pause on reply
            if outcome == 'replied':
                enr['status'] = 'replied'
                enr['reply_received'] = True
            elif outcome == 'completed' and enr.get('current_step', 1) >= enr.get('total_steps', 1):
                enr['status'] = 'completed'
            else:
                enr['current_step'] = enr.get('current_step', 1) + 1
            enr['last_activity_at'] = datetime.now(UTC).isoformat()
        _append_audit(auth.tenant_id, f'sequence_step_{outcome}', enrollment_id)
        return {'status': 'ok', 'enrollment': enr.copy(), 'event': event}

    @router.get('/sequences/{sequence_id}/analytics', responses={404: {'description': SEQUENCE_NOT_FOUND}})
    def sequence_analytics(sequence_id: int, auth: AuthDep) -> dict[str, Any]:
        """NEW: Performance analytics per sequence and per step."""
        enforce_rate_limit(f'{auth.tenant_id}:sequences:analytics', 60, 60)
        with _lock:
            seq = next((s.copy() for s in sequences_memory
                        if s.get('id') == sequence_id and s.get('tenant_id') == auth.tenant_id), None)
            if seq is None:
                raise HTTPException(status_code=404, detail=SEQUENCE_NOT_FOUND)
            enrs = [e for e in enrollments_memory if e.get('sequence_id') == sequence_id]
            events = [e for e in step_events_memory if e.get('sequence_id') == sequence_id]
        total = len(enrs)
        replied = sum(1 for e in enrs if e.get('reply_received'))
        completed = sum(1 for e in enrs if e.get('status') == 'completed')
        # Per-step breakdown
        step_stats: dict[int, dict[str, int]] = {}
        for ev in events:
            pos = int(ev.get('step_position', 1))
            outcome = str(ev.get('outcome', 'unknown'))
            bucket = step_stats.setdefault(pos, {})
            bucket[outcome] = bucket.get(outcome, 0) + 1
        return {
            'status': 'ok',
            'sequence_id': sequence_id,
            'sequence_name': seq.get('name', ''),
            'total_enrollments': total,
            'reply_count': replied,
            'reply_rate': round(replied / total * 100, 1) if total else 0,
            'completion_count': completed,
            'completion_rate': round(completed / total * 100, 1) if total else 0,
            'step_analytics': step_stats,
        }

    @router.delete('/sequences/{sequence_id}', responses={404: {'description': SEQUENCE_NOT_FOUND}})
    def delete_sequence(sequence_id: int, auth: AuthDep) -> dict[str, Any]:
        """NEW: Delete a sequence (also pauses active enrollments)."""
        enforce_rate_limit(f'{auth.tenant_id}:sequences:delete', 30, 60)
        with _lock:
            idx = next((i for i, s in enumerate(sequences_memory)
                        if s.get('id') == sequence_id and s.get('tenant_id') == auth.tenant_id), None)
            if idx is None:
                raise HTTPException(status_code=404, detail=SEQUENCE_NOT_FOUND)
            removed = sequences_memory.pop(idx)
            # Pause active enrollments
            for enr in enrollments_memory:
                if enr.get('sequence_id') == sequence_id and enr.get('status') == 'active':
                    enr['status'] = 'paused'
        _append_audit(auth.tenant_id, 'sequence_deleted', sequence_id)
        return {'status': 'ok', 'deleted': True, 'sequence': removed}

    return router
