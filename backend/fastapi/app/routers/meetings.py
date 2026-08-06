# pyright: reportUnknownVariableType=false, reportUnknownArgumentType=false, reportUnknownParameterType=false, reportUnknownMemberType=false, reportUnusedFunction=false
"""
Meeting Scheduling (HubSpot Sales Hub §5.4)
NEW: Meeting booking links, round-robin assignment, calendar sync.
Teams/1-on-1 bookings, buffer times, custom form fields.
"""
import threading
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from ..deps import AuthContext, require_auth

AuthDep = Annotated[AuthContext, Depends(require_auth)]

MEETING_LINK_NOT_FOUND = 'Meeting link not found.'
BOOKING_NOT_FOUND = 'Booking not found.'
AVAILABILITY_TYPES = {'business_hours', 'custom', '24_7'}
BOOKING_TYPES = {'one_on_one', 'group', 'round_robin', 'collective'}
DAY_TO_INDEX = {'mon': 0, 'tue': 1, 'wed': 2, 'thu': 3, 'fri': 4, 'sat': 5, 'sun': 6}


class AvailabilityWindow(BaseModel):
    day: str = Field(max_length=10)           # mon, tue, wed, thu, fri, sat, sun
    start_time: str = Field(max_length=5)     # HH:MM
    end_time: str = Field(max_length=5)       # HH:MM


class MeetingLinkCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    slug: str = Field(min_length=1, max_length=100)
    duration_minutes: int = Field(default=30, ge=5, le=480)
    booking_type: str = Field(default='one_on_one', max_length=20)
    description: str = Field(default='', max_length=2000)
    buffer_before_minutes: int = Field(default=0, ge=0, le=60)
    buffer_after_minutes: int = Field(default=0, ge=0, le=60)
    min_notice_hours: int = Field(default=2, ge=0, le=168)
    max_bookings_per_day: int = Field(default=8, ge=1, le=50)
    timezone: str = Field(default='UTC', max_length=50)
    availability: list[AvailabilityWindow] = Field(default_factory=list, max_length=7)
    custom_form_fields: list[str] = Field(default_factory=list, max_length=10)


class BookingCreateRequest(BaseModel):
    meeting_link_slug: str = Field(min_length=1, max_length=100)
    attendee_email: str = Field(min_length=1, max_length=200)
    attendee_name: str = Field(min_length=1, max_length=200)
    attendee_company: str = Field(default='', max_length=200)
    start_time: str = Field(min_length=1, max_length=50)      # ISO 8601
    timezone: str = Field(default='UTC', max_length=50)
    notes: str = Field(default='', max_length=2000)
    custom_answers: dict[str, str] = Field(default_factory=dict)


class BookingStatusRequest(BaseModel):
    status: str = Field(max_length=20)  # confirmed, cancelled, rescheduled, no_show


def _parse_booking_datetime(value: str) -> datetime:
    normalized = value.replace('Z', '+00:00') if value.endswith('Z') else value
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _parse_clock_minutes(value: str) -> int:
    hour_text, minute_text = value.split(':', 1)
    return int(hour_text) * 60 + int(minute_text)


def _matches_availability(start_at: datetime, availability: list[dict[str, Any]], duration_minutes: int) -> bool:
    if not availability:
        return True
    weekday = start_at.weekday()
    start_minutes = start_at.hour * 60 + start_at.minute
    end_minutes = start_minutes + duration_minutes
    for window in availability:
        day_value = str(window.get('day', '')).strip().lower()
        if DAY_TO_INDEX.get(day_value) != weekday:
            continue
        window_start = _parse_clock_minutes(str(window.get('start_time', '00:00')))
        window_end = _parse_clock_minutes(str(window.get('end_time', '23:59')))
        if start_minutes >= window_start and end_minutes <= window_end:
            return True
    return False


def create_meetings_router(  # NOSONAR
    *,
    enforce_rate_limit: Callable[[str, int, int], None],
    meeting_links_memory: list[dict[str, Any]],
    bookings_memory: list[dict[str, Any]],
    audit_log_memory: list[dict[str, Any]],
) -> APIRouter:
    """NEW: Meeting scheduling router — HubSpot Sales Hub §5.4."""
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
                'source': 'meetings-router',
            })

    @router.post('/meetings/links', summary='Create meeting booking link', responses={409: {'description': 'Meeting link slug already exists for this tenant.'}})
    def create_meeting_link(payload: MeetingLinkCreateRequest, auth: AuthDep) -> dict[str, Any]:
        """NEW: Create a shareable meeting booking link."""
        enforce_rate_limit(f'{auth.tenant_id}:meetings:create-link', 30, 60)
        booking_type = payload.booking_type.strip().lower()
        if booking_type not in BOOKING_TYPES:
            booking_type = 'one_on_one'
        # Default 5-day business hours if no availability provided
        availability = [a.model_dump() for a in payload.availability]
        if not availability:
            for day in ['mon', 'tue', 'wed', 'thu', 'fri']:
                availability.append({'day': day, 'start_time': '09:00', 'end_time': '17:00'})
        with _lock:
            # Slug uniqueness per tenant
            if any(m.get('slug') == payload.slug and m.get('tenant_id') == auth.tenant_id
                   for m in meeting_links_memory):
                raise HTTPException(status_code=409, detail='Meeting link slug already exists for this tenant.')
            link = {
                'id': len(meeting_links_memory) + 1,
                'tenant_id': auth.tenant_id,
                'name': payload.name,
                'slug': payload.slug,
                'duration_minutes': payload.duration_minutes,
                'booking_type': booking_type,
                'description': payload.description,
                'buffer_before_minutes': payload.buffer_before_minutes,
                'buffer_after_minutes': payload.buffer_after_minutes,
                'min_notice_hours': payload.min_notice_hours,
                'max_bookings_per_day': payload.max_bookings_per_day,
                'timezone': payload.timezone,
                'availability': availability,
                'custom_form_fields': payload.custom_form_fields,
                'booking_count': 0,
                'active': True,
                'created_at': datetime.now(UTC).isoformat(),
            }
            meeting_links_memory.append(link)
        _append_audit(auth.tenant_id, 'meeting_link_created', link['id'])
        return {'status': 'ok', 'meeting_link': link, 'booking_url': f'https://meetings.app/{auth.tenant_id}/{payload.slug}'}

    @router.get('/meetings/links', summary='List meeting links')
    def list_meeting_links(
        auth: AuthDep,
        limit: Annotated[int, Query(ge=1, le=100)] = 20,
        offset: Annotated[int, Query(ge=0)] = 0,
    ) -> dict[str, Any]:
        """NEW: List all meeting booking links for this tenant."""
        enforce_rate_limit(f'{auth.tenant_id}:meetings:list-links', 120, 60)
        with _lock:
            items = [m.copy() for m in meeting_links_memory if m.get('tenant_id') == auth.tenant_id]
        return {'status': 'ok', 'meeting_links': items[offset:offset + limit], 'total': len(items)}

    @router.get('/meetings/links/{slug}', responses={404: {'description': MEETING_LINK_NOT_FOUND}})
    def get_meeting_link(slug: str, auth: AuthDep) -> dict[str, Any]:
        """NEW: Get a meeting link by slug."""
        enforce_rate_limit(f'{auth.tenant_id}:meetings:get-link', 120, 60)
        with _lock:
            link = next((m.copy() for m in meeting_links_memory
                         if m.get('slug') == slug and m.get('tenant_id') == auth.tenant_id), None)
        if link is None:
            raise HTTPException(status_code=404, detail=MEETING_LINK_NOT_FOUND)
        return {'status': 'ok', 'meeting_link': link}

    @router.post('/meetings/book', summary='Book a meeting', responses={404: {'description': MEETING_LINK_NOT_FOUND}, 409: {'description': 'Requested booking is invalid or conflicts with availability.'}})
    def book_meeting(payload: BookingCreateRequest, auth: AuthDep) -> dict[str, Any]:
        """NEW: Book a meeting slot."""
        enforce_rate_limit(f'{auth.tenant_id}:meetings:book', 60, 60)
        start_at = _parse_booking_datetime(payload.start_time)
        with _lock:
            link = next((m for m in meeting_links_memory
                         if m.get('slug') == payload.meeting_link_slug
                         and m.get('tenant_id') == auth.tenant_id), None)
            if link is None:
                raise HTTPException(status_code=404, detail=MEETING_LINK_NOT_FOUND)
            if start_at < datetime.now(UTC) + timedelta(hours=int(link.get('min_notice_hours', 0))):
                raise HTTPException(status_code=409, detail='Meeting start time violates minimum notice requirement.')
            duration_minutes = int(link.get('duration_minutes', 30))
            if not _matches_availability(start_at, list(link.get('availability', [])), duration_minutes):
                raise HTTPException(status_code=409, detail='Requested time is outside configured availability.')
            # Check max bookings per day for start_time date
            start_date = payload.start_time[:10]  # YYYY-MM-DD
            day_count = sum(1 for b in bookings_memory
                            if b.get('meeting_link_id') == link.get('id')
                            and str(b.get('start_time', '')).startswith(start_date)
                            and b.get('status') == 'confirmed')
            if day_count >= link.get('max_bookings_per_day', 8):
                raise HTTPException(status_code=409, detail='No available slots on this date.')
            proposed_start = start_at - timedelta(minutes=int(link.get('buffer_before_minutes', 0)))
            proposed_end = start_at + timedelta(minutes=duration_minutes + int(link.get('buffer_after_minutes', 0)))
            for existing in bookings_memory:
                if existing.get('meeting_link_id') != link.get('id') or existing.get('status') != 'confirmed':
                    continue
                existing_start_raw = str(existing.get('start_time', ''))
                if not existing_start_raw:
                    continue
                existing_start = _parse_booking_datetime(existing_start_raw)
                existing_buffered_start = existing_start - timedelta(minutes=int(link.get('buffer_before_minutes', 0)))
                existing_buffered_end = existing_start + timedelta(minutes=duration_minutes + int(link.get('buffer_after_minutes', 0)))
                if proposed_start < existing_buffered_end and proposed_end > existing_buffered_start:
                    raise HTTPException(status_code=409, detail='Requested time conflicts with an existing booking.')
            booking = {
                'id': len(bookings_memory) + 1,
                'tenant_id': auth.tenant_id,
                'meeting_link_id': link.get('id'),
                'meeting_link_slug': payload.meeting_link_slug,
                'meeting_name': link.get('name', ''),
                'duration_minutes': link.get('duration_minutes', 30),
                'attendee_email': payload.attendee_email,
                'attendee_name': payload.attendee_name,
                'attendee_company': payload.attendee_company,
                'start_time': payload.start_time,
                'timezone': payload.timezone,
                'notes': payload.notes,
                'custom_answers': payload.custom_answers,
                'status': 'confirmed',  # confirmed, cancelled, rescheduled, no_show
                'confirmation_code': f'BK-{len(bookings_memory) + 1:06d}',
                'booked_at': datetime.now(UTC).isoformat(),
            }
            bookings_memory.append(booking)
            link['booking_count'] = link.get('booking_count', 0) + 1
        _append_audit(auth.tenant_id, 'meeting_booked', booking['id'])
        return {'status': 'ok', 'booking': booking, 'confirmation_code': booking['confirmation_code']}

    @router.get('/meetings/bookings', summary='List bookings')
    def list_bookings(
        auth: AuthDep,
        status: Annotated[str | None, Query(max_length=20)] = None,
        from_date: Annotated[str | None, Query(max_length=10)] = None,
        to_date: Annotated[str | None, Query(max_length=10)] = None,
        limit: Annotated[int, Query(ge=1, le=200)] = 50,
        offset: Annotated[int, Query(ge=0)] = 0,
    ) -> dict[str, Any]:
        """NEW: List all bookings for this tenant."""
        enforce_rate_limit(f'{auth.tenant_id}:meetings:list-bookings', 120, 60)
        with _lock:
            items = [b.copy() for b in bookings_memory if b.get('tenant_id') == auth.tenant_id]
        if status:
            items = [b for b in items if b.get('status') == status]
        if from_date:
            items = [b for b in items if str(b.get('start_time', '')) >= from_date]
        if to_date:
            items = [b for b in items if str(b.get('start_time', '')) <= to_date + 'Z']
        items.sort(key=lambda x: str(x.get('start_time', '')))
        return {'status': 'ok', 'bookings': items[offset:offset + limit], 'total': len(items)}

    @router.patch('/meetings/bookings/{booking_id}', responses={404: {'description': BOOKING_NOT_FOUND}})
    def update_booking_status(booking_id: int, payload: BookingStatusRequest, auth: AuthDep) -> dict[str, Any]:
        """NEW: Update booking status (cancel, reschedule, mark no-show)."""
        enforce_rate_limit(f'{auth.tenant_id}:meetings:update-booking', 60, 60)
        with _lock:
            booking = next((b for b in bookings_memory
                            if b.get('id') == booking_id and b.get('tenant_id') == auth.tenant_id), None)
            if booking is None:
                raise HTTPException(status_code=404, detail=BOOKING_NOT_FOUND)
            booking['status'] = payload.status
            booking['updated_at'] = datetime.now(UTC).isoformat()
        _append_audit(auth.tenant_id, f'meeting_booking_{payload.status}', booking_id)
        return {'status': 'ok', 'booking': booking.copy()}

    @router.get('/meetings/analytics', summary='Meeting analytics')
    def meeting_analytics(auth: AuthDep) -> dict[str, Any]:
        """NEW: Meeting booking analytics — totals, no-shows, busiest slots."""
        enforce_rate_limit(f'{auth.tenant_id}:meetings:analytics', 60, 60)
        with _lock:
            bookings = [b for b in bookings_memory if b.get('tenant_id') == auth.tenant_id]
            links = [m for m in meeting_links_memory if m.get('tenant_id') == auth.tenant_id]
        total = len(bookings)
        confirmed = sum(1 for b in bookings if b.get('status') == 'confirmed')
        cancelled = sum(1 for b in bookings if b.get('status') == 'cancelled')
        no_show = sum(1 for b in bookings if b.get('status') == 'no_show')
        # Hour distribution
        hour_dist: dict[int, int] = {}
        for b in bookings:
            start = str(b.get('start_time', ''))
            if 'T' in start:
                try:
                    hour = int(start.split('T')[1][:2])
                    hour_dist[hour] = hour_dist.get(hour, 0) + 1
                except (ValueError, IndexError):
                    pass
        return {
            'status': 'ok',
            'total_bookings': total,
            'confirmed': confirmed,
            'cancelled': cancelled,
            'no_show': no_show,
            'show_up_rate': round(confirmed / (confirmed + no_show) * 100, 1) if (confirmed + no_show) > 0 else 100,
            'total_meeting_links': len(links),
            'hourly_distribution': hour_dist,
        }

    return router
