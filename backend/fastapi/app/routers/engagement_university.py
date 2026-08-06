# pyright: reportUnusedFunction=false, reportUnknownVariableType=false, reportUnknownArgumentType=false

import threading
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..deps import AuthContext, require_auth

AuthDep = Annotated[AuthContext, Depends(require_auth)]


class UniversityCourseRequest(BaseModel):
    title: str = Field(min_length=4, max_length=180)
    track: str = Field(default='growth', max_length=80)
    level: str = Field(default='beginner', max_length=40)
    price_usd: float = Field(default=0.0, ge=0.0, le=1000000.0)


class UniversityCohortRequest(BaseModel):
    course_id: int
    starts_at: str = Field(min_length=10, max_length=40)
    capacity: int = Field(default=25, ge=1, le=10000)
    mentor_name: str = Field(default='', max_length=120)


class UniversityEnrollRequest(BaseModel):
    cohort_id: int
    learner_email: str = Field(default='', max_length=320)


class UniversityProgressRequest(BaseModel):
    enrollment_id: int
    checkpoint: str = Field(min_length=2, max_length=160)
    completion_delta: int = Field(default=10, ge=1, le=100)
    note: str = Field(default='', max_length=320)


@dataclass
class UniversityContext:
    enforce_rate_limit: Callable[[str, int, int], None]
    lock: threading.Lock
    university_courses_memory: list[dict[str, Any]]
    university_cohorts_memory: list[dict[str, Any]]
    university_enrollments_memory: list[dict[str, Any]]
    tenant_display_name_fn: Callable[[str], str]
    append_credit_fn: Callable[[str, int, str], None]
    append_notification_fn: Callable[[str, str, str, str], None]
    append_audit_fn: Callable[[str, str, dict[str, Any]], None]
    course_not_found: str
    cohort_not_found: str
    cohort_at_capacity: str
    enrollment_not_found: str


def register_university_routes(*, router: APIRouter, context: UniversityContext) -> None:
    _register_university_catalog_routes(router, context)
    _register_university_progress_routes(router, context)


def _register_university_catalog_routes(router: APIRouter, ctx: UniversityContext) -> None:
    @router.get('/money-printers/nuxtron-university/catalog')
    def nuxtron_university_catalog(auth: AuthDep) -> dict[str, Any]:
        ctx.enforce_rate_limit(f'{auth.tenant_id}:nuxtron-university:catalog', 240, 60)
        with ctx.lock:
            courses = [item.copy() for item in ctx.university_courses_memory if item.get('tenant_id') == auth.tenant_id]
            cohorts = [item.copy() for item in ctx.university_cohorts_memory if item.get('tenant_id') == auth.tenant_id]
        courses.sort(key=lambda item: str(item.get('created_at', '')), reverse=True)
        cohorts.sort(key=lambda item: str(item.get('starts_at', '')), reverse=True)
        return {
            'status': 'ok', 'tenant_id': auth.tenant_id,
            'catalog': {'courses': courses, 'cohorts': cohorts, 'course_count': len(courses), 'cohort_count': len(cohorts)},
        }

    @router.post('/money-printers/nuxtron-university/courses')
    def nuxtron_university_create_course(payload: UniversityCourseRequest, auth: AuthDep) -> dict[str, Any]:
        ctx.enforce_rate_limit(f'{auth.tenant_id}:nuxtron-university:courses:create', 120, 60)
        with ctx.lock:
            now_iso = datetime.now(UTC).isoformat()
            course = {
                'id': len(ctx.university_courses_memory) + 1,
                'tenant_id': auth.tenant_id,
                'title': payload.title,
                'track': payload.track.strip().lower(),
                'level': payload.level.strip().lower(),
                'price_usd': round(float(payload.price_usd), 2),
                'status': 'draft',
                'created_at': now_iso,
                'updated_at': now_iso,
            }
            ctx.university_courses_memory.append(course)
            ctx.append_audit_fn(auth.tenant_id, 'nuxtron_university_course_created', {'course_id': course['id']})
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'course': course}

    @router.post('/money-printers/nuxtron-university/cohorts', responses={404: {'description': 'University course not found.'}})
    def nuxtron_university_create_cohort(payload: UniversityCohortRequest, auth: AuthDep) -> dict[str, Any]:
        ctx.enforce_rate_limit(f'{auth.tenant_id}:nuxtron-university:cohorts:create', 120, 60)
        with ctx.lock:
            course = next(
                (item for item in ctx.university_courses_memory
                 if item.get('tenant_id') == auth.tenant_id and int(item.get('id', 0)) == int(payload.course_id)),
                None,
            )
            if course is None:
                raise HTTPException(status_code=404, detail=ctx.course_not_found)
            now_iso = datetime.now(UTC).isoformat()
            cohort = {
                'id': len(ctx.university_cohorts_memory) + 1,
                'tenant_id': auth.tenant_id,
                'course_id': int(course['id']),
                'starts_at': payload.starts_at,
                'capacity': int(payload.capacity),
                'mentor_name': payload.mentor_name.strip() or ctx.tenant_display_name_fn(auth.tenant_id),
                'status': 'scheduled',
                'created_at': now_iso,
                'updated_at': now_iso,
            }
            ctx.university_cohorts_memory.append(cohort)
            ctx.append_audit_fn(auth.tenant_id, 'nuxtron_university_cohort_created',
                {'cohort_id': cohort['id'], 'course_id': int(course['id'])})
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'cohort': cohort}

    @router.post(
        '/money-printers/nuxtron-university/enrollments',
        responses={
            404: {'description': 'University cohort not found.'},
            422: {'description': 'University cohort is at capacity.'},
        },
    )
    def nuxtron_university_enroll(payload: UniversityEnrollRequest, auth: AuthDep) -> dict[str, Any]:
        ctx.enforce_rate_limit(f'{auth.tenant_id}:nuxtron-university:enrollments:create', 120, 60)
        with ctx.lock:
            cohort = next(
                (item for item in ctx.university_cohorts_memory
                 if item.get('tenant_id') == auth.tenant_id and int(item.get('id', 0)) == int(payload.cohort_id)),
                None,
            )
            if cohort is None:
                raise HTTPException(status_code=404, detail=ctx.cohort_not_found)
            enrolled_count = sum(
                1 for item in ctx.university_enrollments_memory
                if item.get('tenant_id') == auth.tenant_id and int(item.get('cohort_id', 0)) == int(cohort['id'])
            )
            if enrolled_count >= int(cohort.get('capacity', 0)):
                raise HTTPException(status_code=422, detail=ctx.cohort_at_capacity)
            now_iso = datetime.now(UTC).isoformat()
            enrollment = {
                'id': len(ctx.university_enrollments_memory) + 1,
                'tenant_id': auth.tenant_id,
                'cohort_id': int(cohort['id']),
                'learner_email': payload.learner_email.strip().lower() or f'learner{len(ctx.university_enrollments_memory)+1}@example.com',
                'completion_percent': 0,
                'checkpoints': [],
                'status': 'active',
                'created_at': now_iso,
                'updated_at': now_iso,
            }
            ctx.university_enrollments_memory.append(enrollment)
            ctx.append_audit_fn(auth.tenant_id, 'nuxtron_university_enrollment_created',
                {'enrollment_id': enrollment['id'], 'cohort_id': int(cohort['id'])})
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'enrollment': enrollment}


def _register_university_progress_routes(router: APIRouter, ctx: UniversityContext) -> None:
    @router.post('/money-printers/nuxtron-university/progress', responses={404: {'description': 'University enrollment not found.'}})
    def nuxtron_university_progress(payload: UniversityProgressRequest, auth: AuthDep) -> dict[str, Any]:
        ctx.enforce_rate_limit(f'{auth.tenant_id}:nuxtron-university:progress', 120, 60)
        with ctx.lock:
            enrollment = next(
                (item for item in ctx.university_enrollments_memory
                 if item.get('tenant_id') == auth.tenant_id and int(item.get('id', 0)) == int(payload.enrollment_id)),
                None,
            )
            if enrollment is None:
                raise HTTPException(status_code=404, detail=ctx.enrollment_not_found)
            before = int(enrollment.get('completion_percent', 0))
            after = min(100, before + int(payload.completion_delta))
            checkpoint_event = {
                'checkpoint': payload.checkpoint,
                'completion_before': before,
                'completion_after': after,
                'note': payload.note,
                'created_at': datetime.now(UTC).isoformat(),
            }
            checkpoints = list(enrollment.get('checkpoints', []))
            checkpoints.append(checkpoint_event)
            enrollment['checkpoints'] = checkpoints
            enrollment['completion_percent'] = after
            enrollment['status'] = 'completed' if after >= 100 else 'active'
            enrollment['updated_at'] = checkpoint_event['created_at']
            credits_awarded = 0
            if after >= 100 and before < 100:
                credits_awarded = 65
                ctx.append_credit_fn(auth.tenant_id, credits_awarded, 'nuxtron_university_completion')
                ctx.append_notification_fn(
                    auth.tenant_id, 'Nuxtron University Completion',
                    f'Enrollment #{enrollment["id"]} completed and certification is now ready.',
                    'nuxtron_university',
                )
            ctx.append_audit_fn(auth.tenant_id, 'nuxtron_university_progress_checkpoint',
                {'enrollment_id': int(enrollment['id']), 'completion_after': after})
        return {
            'status': 'ok', 'tenant_id': auth.tenant_id,
            'enrollment': enrollment, 'checkpoint_event': checkpoint_event, 'credits_awarded': credits_awarded,
        }

    @router.get('/money-printers/nuxtron-university/overview')
    def nuxtron_university_overview(auth: AuthDep) -> dict[str, Any]:
        ctx.enforce_rate_limit(f'{auth.tenant_id}:nuxtron-university:overview', 240, 60)
        with ctx.lock:
            courses = [item.copy() for item in ctx.university_courses_memory if item.get('tenant_id') == auth.tenant_id]
            cohorts = [item.copy() for item in ctx.university_cohorts_memory if item.get('tenant_id') == auth.tenant_id]
            enrollments = [item.copy() for item in ctx.university_enrollments_memory if item.get('tenant_id') == auth.tenant_id]
        completion = [int(item.get('completion_percent', 0)) for item in enrollments]
        avg_completion = int(sum(completion) / len(completion)) if completion else 0
        completed = sum(1 for item in enrollments if int(item.get('completion_percent', 0)) >= 100)
        return {
            'status': 'ok', 'tenant_id': auth.tenant_id,
            'university': {
                'courses': len(courses), 'cohorts': len(cohorts), 'enrollments': len(enrollments),
                'completed_enrollments': completed, 'average_completion_percent': avg_completion,
                'completion_readiness': min(100, completed * 20 + avg_completion // 2),
            },
        }
