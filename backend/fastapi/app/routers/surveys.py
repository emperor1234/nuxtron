# pyright: reportUnknownVariableType=false, reportUnknownArgumentType=false, reportUnknownParameterType=false, reportUnknownMemberType=false, reportUnusedFunction=false
"""
NPS / CSAT / CES Surveys (HubSpot Service Hub §6.4)
NEW: Customer satisfaction surveys — NPS, CSAT, CES and custom surveys.
Auto-send triggers, response collection, close-loop workflows.
"""
import threading
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from ..deps import AuthContext, require_auth

AuthDep = Annotated[AuthContext, Depends(require_auth)]

SURVEY_NOT_FOUND = 'Survey not found.'
RESPONSE_NOT_FOUND = 'Survey response not found.'
SURVEY_TYPES = {'nps', 'csat', 'ces', 'custom'}
TRIGGER_EVENTS = {'ticket_resolved', 'deal_closed', 'onboarding_complete', 'manual', 'scheduled', 'meeting_complete'}


class SurveyQuestionModel(BaseModel):
    question_id: str = Field(min_length=1, max_length=50)
    question_text: str = Field(min_length=1, max_length=500)
    question_type: str = Field(default='scale', max_length=20)  # scale, text, choice
    scale_min: int = Field(default=1, ge=0, le=1)
    scale_max: int = Field(default=10, ge=2, le=11)
    required: bool = True
    options: list[str] = Field(default_factory=list, max_length=10)


class SurveyCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    survey_type: str = Field(default='custom', max_length=20)
    description: str = Field(default='', max_length=1000)
    questions: list[SurveyQuestionModel] = Field(default_factory=list, max_length=20)
    trigger_event: str = Field(default='manual', max_length=40)
    trigger_delay_hours: int = Field(default=24, ge=0, le=720)
    follow_up_threshold: int = Field(default=6, ge=0, le=10)   # score below this triggers follow-up
    send_via: str = Field(default='email', max_length=20)


class SurveyResponseRequest(BaseModel):
    survey_id: int = Field(ge=1)
    respondent_email: str = Field(min_length=1, max_length=200)
    respondent_name: str = Field(default='', max_length=200)
    contact_id: str = Field(default='', max_length=100)
    answers: list[dict[str, Any]] = Field(default_factory=list, max_length=20)
    primary_score: int | None = None     # NPS: 0-10, CSAT: 1-5, CES: 1-7
    verbatim: str = Field(default='', max_length=5000)


def create_surveys_router(  # NOSONAR
    *,
    enforce_rate_limit: Callable[[str, int, int], None],
    surveys_memory: list[dict[str, Any]],
    survey_responses_memory: list[dict[str, Any]],
    audit_log_memory: list[dict[str, Any]],
) -> APIRouter:
    """NEW: NPS/CSAT surveys router — HubSpot Service Hub §6.4."""
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
                'source': 'surveys-router',
            })

    def _build_default_questions(survey_type: str) -> list[dict[str, Any]]:
        if survey_type == 'nps':
            return [{'question_id': 'nps_score', 'question_text': 'How likely are you to recommend us to a friend or colleague?',
                     'question_type': 'scale', 'scale_min': 0, 'scale_max': 10, 'required': True, 'options': []},
                    {'question_id': 'nps_reason', 'question_text': 'What is the primary reason for your score?',
                     'question_type': 'text', 'scale_min': 1, 'scale_max': 10, 'required': False, 'options': []}]
        if survey_type == 'csat':
            return [{'question_id': 'csat_score', 'question_text': 'How satisfied are you with your experience?',
                     'question_type': 'scale', 'scale_min': 1, 'scale_max': 5, 'required': True, 'options': []},
                    {'question_id': 'csat_reason', 'question_text': 'Tell us more about your experience.',
                     'question_type': 'text', 'scale_min': 1, 'scale_max': 5, 'required': False, 'options': []}]
        if survey_type == 'ces':
            return [{'question_id': 'ces_score', 'question_text': 'How easy was it to resolve your issue today?',
                     'question_type': 'scale', 'scale_min': 1, 'scale_max': 7, 'required': True, 'options': []}]
        return []

    @router.post('/surveys', summary='Create survey')
    def create_survey(payload: SurveyCreateRequest, auth: AuthDep) -> dict[str, Any]:
        """NEW: Create an NPS, CSAT, CES, or custom survey."""
        enforce_rate_limit(f'{auth.tenant_id}:surveys:create', 30, 60)
        survey_type = payload.survey_type.strip().lower()
        if survey_type not in SURVEY_TYPES:
            survey_type = 'custom'
        trigger_event = payload.trigger_event.strip().lower()
        if trigger_event not in TRIGGER_EVENTS:
            trigger_event = 'manual'
        questions = [q.model_dump() for q in payload.questions]
        if not questions:
            questions = _build_default_questions(survey_type)
        with _lock:
            survey = {
                'id': len(surveys_memory) + 1,
                'tenant_id': auth.tenant_id,
                'name': payload.name,
                'survey_type': survey_type,
                'description': payload.description,
                'questions': questions,
                'trigger_event': trigger_event,
                'trigger_delay_hours': payload.trigger_delay_hours,
                'follow_up_threshold': payload.follow_up_threshold,
                'send_via': payload.send_via,
                'status': 'active',
                'response_count': 0,
                'created_at': datetime.now(UTC).isoformat(),
                'updated_at': datetime.now(UTC).isoformat(),
            }
            surveys_memory.append(survey)
        _append_audit(auth.tenant_id, 'survey_created', survey['id'])
        return {'status': 'ok', 'survey': survey}

    @router.get('/surveys', summary='List surveys')
    def list_surveys(
        auth: AuthDep,
        survey_type: Annotated[str | None, Query(max_length=20)] = None,
        limit: Annotated[int, Query(ge=1, le=100)] = 20,
        offset: Annotated[int, Query(ge=0)] = 0,
    ) -> dict[str, Any]:
        """NEW: List all surveys for this tenant."""
        enforce_rate_limit(f'{auth.tenant_id}:surveys:list', 120, 60)
        with _lock:
            items = [s.copy() for s in surveys_memory if s.get('tenant_id') == auth.tenant_id]
        if survey_type:
            items = [s for s in items if s.get('survey_type') == survey_type]
        return {'status': 'ok', 'surveys': items[offset:offset + limit], 'total': len(items)}

    @router.get('/surveys/{survey_id}', responses={404: {'description': SURVEY_NOT_FOUND}})
    def get_survey(survey_id: int, auth: AuthDep) -> dict[str, Any]:
        """NEW: Get a survey with its questions."""
        enforce_rate_limit(f'{auth.tenant_id}:surveys:get', 120, 60)
        with _lock:
            survey = next((s.copy() for s in surveys_memory
                           if s.get('id') == survey_id and s.get('tenant_id') == auth.tenant_id), None)
        if survey is None:
            raise HTTPException(status_code=404, detail=SURVEY_NOT_FOUND)
        return {'status': 'ok', 'survey': survey}

    @router.post('/surveys/{survey_id}/respond', responses={404: {'description': SURVEY_NOT_FOUND}})
    def submit_response(survey_id: int, payload: SurveyResponseRequest, auth: AuthDep) -> dict[str, Any]:
        """NEW: Submit a survey response."""
        enforce_rate_limit(f'{auth.tenant_id}:surveys:respond', 120, 60)
        with _lock:
            survey = next((s for s in surveys_memory
                           if s.get('id') == survey_id and s.get('tenant_id') == auth.tenant_id), None)
            if survey is None:
                raise HTTPException(status_code=404, detail=SURVEY_NOT_FOUND)
            # Classify NPS
            nps_category = None
            if survey.get('survey_type') == 'nps' and payload.primary_score is not None:
                score = int(payload.primary_score)
                if score <= 6:
                    nps_category = 'detractor'
                elif score <= 8:
                    nps_category = 'passive'
                else:
                    nps_category = 'promoter'
            response = {
                'id': len(survey_responses_memory) + 1,
                'tenant_id': auth.tenant_id,
                'survey_id': survey_id,
                'survey_type': survey.get('survey_type'),
                'respondent_email': payload.respondent_email,
                'respondent_name': payload.respondent_name,
                'contact_id': payload.contact_id,
                'answers': payload.answers,
                'primary_score': payload.primary_score,
                'verbatim': payload.verbatim,
                'nps_category': nps_category,
                'requires_follow_up': (
                    payload.primary_score is not None
                    and int(payload.primary_score) <= int(survey.get('follow_up_threshold', 6))
                ),
                'follow_up_completed': False,
                'created_at': datetime.now(UTC).isoformat(),
            }
            survey_responses_memory.append(response)
            survey['response_count'] = survey.get('response_count', 0) + 1
        _append_audit(auth.tenant_id, 'survey_response_submitted', response['id'])
        return {'status': 'ok', 'response': response}

    @router.get('/surveys/{survey_id}/responses', responses={404: {'description': SURVEY_NOT_FOUND}})
    def list_responses(
        survey_id: int,
        auth: AuthDep,
        limit: Annotated[int, Query(ge=1, le=500)] = 100,
        offset: Annotated[int, Query(ge=0)] = 0,
    ) -> dict[str, Any]:
        """NEW: List responses for a survey."""
        enforce_rate_limit(f'{auth.tenant_id}:surveys:responses', 60, 60)
        with _lock:
            survey = next((s for s in surveys_memory
                           if s.get('id') == survey_id and s.get('tenant_id') == auth.tenant_id), None)
            if survey is None:
                raise HTTPException(status_code=404, detail=SURVEY_NOT_FOUND)
            items = [r.copy() for r in survey_responses_memory
                     if r.get('survey_id') == survey_id]
        return {'status': 'ok', 'responses': items[offset:offset + limit], 'total': len(items)}

    @router.get('/surveys/{survey_id}/analytics', responses={404: {'description': SURVEY_NOT_FOUND}})
    def survey_analytics(survey_id: int, auth: AuthDep) -> dict[str, Any]:
        """NEW: Survey analytics — NPS score, CSAT avg, response rate, breakdown."""
        enforce_rate_limit(f'{auth.tenant_id}:surveys:analytics', 60, 60)
        with _lock:
            survey = next((s.copy() for s in surveys_memory
                           if s.get('id') == survey_id and s.get('tenant_id') == auth.tenant_id), None)
            if survey is None:
                raise HTTPException(status_code=404, detail=SURVEY_NOT_FOUND)
            responses = [r for r in survey_responses_memory if r.get('survey_id') == survey_id]
        scored = [r for r in responses if r.get('primary_score') is not None]
        scores = [int(r['primary_score']) for r in scored]
        analytics: dict[str, Any] = {
            'status': 'ok',
            'survey_id': survey_id,
            'survey_type': survey.get('survey_type'),
            'total_responses': len(responses),
            'avg_score': round(sum(scores) / len(scores), 2) if scores else None,
            'score_distribution': {},
        }
        # Score distribution
        dist: dict[int, int] = {}
        for s in scores:
            dist[s] = dist.get(s, 0) + 1
        analytics['score_distribution'] = dist
        # NPS-specific
        if survey.get('survey_type') == 'nps':
            promoters = sum(1 for s in scores if s >= 9)
            detractors = sum(1 for s in scores if s <= 6)
            n = len(scores)
            analytics['nps_score'] = round((promoters - detractors) / n * 100) if n else None
            analytics['promoters'] = promoters
            analytics['passives'] = sum(1 for s in scores if 7 <= s <= 8)
            analytics['detractors'] = detractors
        # Follow-up queue
        analytics['follow_up_pending'] = sum(
            1 for r in responses if r.get('requires_follow_up') and not r.get('follow_up_completed')
        )
        return analytics

    return router
