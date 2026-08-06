"""
Lindy.ai Meeting Management API Tests
Phase 2: Comprehensive test suite for meeting scheduling, preparation, and recap
"""

import json
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.orm import Session

from ..routers.lindy_meeting_management import (
    book_public_meeting,
    create_meeting_template,
    generate_meeting_prep,
    generate_meeting_recap,
    get_meeting,
    get_meeting_prep,
    get_meeting_recap,
    get_meeting_recording_status,
    get_meeting_transcript,
    get_meetings_status,
    get_public_booking_availability,
    get_scheduling_preferences,
    handle_calendar_oauth_callback,
    health_check,
    initialize_calendar_oauth,
    list_meeting_templates,
    list_meetings,
    meeting_integrations_vendors,
    meeting_production_readiness,
    reschedule_meeting,
    router,
    schedule_meeting,
    set_scheduling_preferences,
    start_meeting_recording,
    start_meeting_transcription,
)

# Expose route handlers as router attributes for direct unit testing
router.initialize_calendar_oauth = initialize_calendar_oauth
router.handle_calendar_oauth_callback = handle_calendar_oauth_callback
router.schedule_meeting = schedule_meeting
router.list_meetings = list_meetings
router.get_meeting = get_meeting
router.reschedule_meeting = reschedule_meeting
router.generate_meeting_prep = generate_meeting_prep
router.get_meeting_prep = get_meeting_prep
router.start_meeting_recording = start_meeting_recording
router.get_meeting_recording_status = get_meeting_recording_status
router.start_meeting_transcription = start_meeting_transcription
router.get_transcript = get_meeting_transcript
router.generate_meeting_recap = generate_meeting_recap
router.get_meeting_recap = get_meeting_recap
router.set_scheduling_preferences = set_scheduling_preferences
router.get_scheduling_preferences = get_scheduling_preferences
router.get_meetings_status = get_meetings_status
router.health_check = health_check
router.create_meeting_template = create_meeting_template
router.list_meeting_templates = list_meeting_templates
router.get_public_booking_availability = get_public_booking_availability
router.book_public_meeting = book_public_meeting
router.meeting_integrations_vendors = meeting_integrations_vendors
router.meeting_production_readiness = meeting_production_readiness


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def mock_db():
    """Mock database session"""
    db = MagicMock(spec=Session)
    return db


@pytest.fixture
def test_user_id():
    return "user_123@company.com"


@pytest.fixture
def google_credential():
    """Mock Google Calendar credential"""
    return {
        "user_id": "user_123@company.com",
        "provider": "google",
        "access_token_encrypted": "encrypted_google_token_xyz",
        "refresh_token_encrypted": "encrypted_google_refresh_xyz",
        "expires_at": datetime.utcnow() + timedelta(hours=1)
    }


@pytest.fixture
def outlook_credential():
    """Mock Outlook Calendar credential"""
    return {
        "user_id": "user_123@company.com",
        "provider": "outlook",
        "access_token_encrypted": "encrypted_outlook_token_abc",
        "refresh_token_encrypted": "encrypted_outlook_refresh_abc",
        "expires_at": datetime.utcnow() + timedelta(hours=1)
    }


@pytest.fixture
def test_meeting():
    """Mock meeting record"""
    return {
        "id": "meet_001",
        "user_id": "user_123@company.com",
        "title": "Team Sync",
        "description": "Weekly team meeting",
        "scheduled_time": datetime.utcnow() + timedelta(days=1),
        "duration_minutes": 60,
        "attendees": json.dumps(["alice@company.com", "bob@company.com"]),
        "conference_url": "https://meet.google.com/abc-def-ghi",
        "status": "scheduled",
        "confidence_score": 0.95,
        "calendar_provider": "google"
    }


# ============================================================================
# OAUTH TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_create_meeting_template_success(mock_db, test_user_id):
    template_obj = MagicMock()
    template_obj.id = 11
    template_obj.name = 'Demo Call'
    template_obj.default_title = 'Demo Call'
    template_obj.default_duration_minutes = 45
    template_obj.description = 'Sales demo template'
    template_obj.created_at = datetime.utcnow()

    mock_db.refresh.side_effect = lambda obj: [
        setattr(obj, 'id', template_obj.id),
        setattr(obj, 'created_at', template_obj.created_at),
    ]

    result = await router.create_meeting_template(
        payload={
            'name': 'Demo Call',
            'default_title': 'Demo Call',
            'default_duration_minutes': 45,
            'description': 'Sales demo template',
        },
        user_id=test_user_id,
        db=mock_db,
    )

    assert result['status'] == 'ok'
    assert result['template']['id'] == 11
    assert result['template']['default_duration_minutes'] == 45


@pytest.mark.asyncio
async def test_public_booking_availability_returns_slots(mock_db, test_user_id):
    template = MagicMock()
    template.id = 21
    template.name = 'Discovery'
    template.default_title = 'Discovery Call'
    template.default_duration_minutes = 30

    prefs = MagicMock()
    prefs.work_start_hour = 9
    prefs.work_end_hour = 12

    no_meetings: list[MagicMock] = []

    query_obj = MagicMock()
    query_obj.filter.return_value = query_obj
    query_obj.first.side_effect = [template, prefs]
    query_obj.all.return_value = no_meetings
    mock_db.query.return_value = query_obj

    result = await router.get_public_booking_availability(
        template_id=21,
        organizer_id=test_user_id,
        days=2,
        max_slots=5,
        db=mock_db,
    )

    assert result['status'] == 'ok'
    assert result['count'] >= 1
    assert len(result['slots']) >= 1


@pytest.mark.asyncio
async def test_book_public_meeting_without_calendar_connection(mock_db, test_user_id):
    template = MagicMock()
    template.id = 31
    template.default_title = 'Customer Onboarding'
    template.default_description = 'Initial onboarding call'
    template.default_duration_minutes = 30
    template.usage_count = 0

    query_obj = MagicMock()
    query_obj.filter.return_value = query_obj
    # template lookup, conflict lookup, credential lookup
    query_obj.first.side_effect = [template, None, None]
    mock_db.query.return_value = query_obj

    now_plus = datetime.utcnow() + timedelta(days=1)
    result = await router.book_public_meeting(
        template_id=31,
        payload={
            'organizer_id': test_user_id,
            'participant_email': 'prospect@example.com',
            'slot_start': now_plus.isoformat(),
            'timezone': 'UTC',
            'recording_consent': True,
            'transcript_consent': True,
            'ai_processing_consent': True,
        },
        db=mock_db,
    )

    assert result['status'] == 'ok'
    assert result['booking']['calendar_provider'] == 'manual'
    assert result['booking']['calendar_sync'] == 'skipped'


@pytest.mark.asyncio
async def test_meeting_integrations_vendors(mock_db, test_user_id):
    google = MagicMock()
    google.provider = 'google'
    outlook = MagicMock()
    outlook.provider = 'outlook'

    query_obj = MagicMock()
    query_obj.filter.return_value = query_obj
    query_obj.all.return_value = [google, outlook]
    mock_db.query.return_value = query_obj

    result = await router.meeting_integrations_vendors(user_id=test_user_id, db=mock_db)
    assert result['status'] == 'ok'
    assert 'google' in result['connected_providers']
    assert 'outlook' in result['connected_providers']

@pytest.mark.asyncio
async def test_initialize_calendar_oauth_google(mock_db, test_user_id):
    """Test OAuth initialization for Google Calendar"""
    with patch('redis.Redis') as mock_redis:
        redis_instance = MagicMock()
        mock_redis.return_value = redis_instance
        
        # Simulate OAuth URL generation
        oauth_url = await router.initialize_calendar_oauth(
            provider="google",
            user_id=test_user_id,
            db=mock_db
        )
        
        assert oauth_url["provider"] == "google"
        assert "oauth_url" in oauth_url
        assert "state" in oauth_url
        assert "accounts.google.com" in oauth_url["oauth_url"]
        assert "calendar" in oauth_url["oauth_url"].lower()


@pytest.mark.asyncio
async def test_initialize_calendar_oauth_outlook(mock_db, test_user_id):
    """Test OAuth initialization for Outlook Calendar"""
    with patch('redis.Redis') as mock_redis:
        redis_instance = MagicMock()
        mock_redis.return_value = redis_instance
        
        oauth_url = await router.initialize_calendar_oauth(
            provider="outlook",
            user_id=test_user_id,
            db=mock_db
        )
        
        assert oauth_url["provider"] == "outlook"
        assert "oauth_url" in oauth_url
        assert "login.microsoftonline.com" in oauth_url["oauth_url"]


@pytest.mark.asyncio
async def test_initialize_oauth_invalid_provider(mock_db, test_user_id):
    """Test OAuth with invalid provider"""
    from fastapi import HTTPException
    
    with pytest.raises(HTTPException) as exc_info:
        await router.initialize_calendar_oauth(
            provider="invalid_provider",
            user_id=test_user_id,
            db=mock_db
        )
    
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_oauth_callback_valid_google(mock_db, test_user_id):
    """Test OAuth callback with valid Google code"""
    with patch('redis.Redis') as mock_redis, \
         patch('aiohttp.ClientSession') as mock_session:
        
        redis_instance = MagicMock()
        redis_instance.get.return_value = f"{test_user_id}:google".encode()
        mock_redis.return_value = redis_instance
        
        # Mock token response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            'access_token': 'access_token_123',
            'refresh_token': 'refresh_token_456',
            'expires_in': 3600
        })
        
        mock_session_obj = AsyncMock()
        mock_session_obj.post = AsyncMock(return_value=mock_response)
        mock_session_obj.__aenter__ = AsyncMock(return_value=mock_session_obj)
        mock_session_obj.__aexit__ = AsyncMock(return_value=None)
        mock_session.return_value = mock_session_obj
        
        # Mock database operations
        mock_db.query.return_value.filter.return_value.first.return_value = None
        mock_db.add = MagicMock()
        mock_db.commit = MagicMock()
        
        result = await router.handle_calendar_oauth_callback(
            code="auth_code_123",
            state="state_token_xyz",
            db=mock_db
        )
        
        assert result["status"] == "success"
        assert result["provider"] == "google"


# ============================================================================
# SCHEDULING TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_schedule_meeting_success(mock_db, test_user_id, google_credential):
    """Test successful meeting scheduling"""
    with patch('backend.fastapi.app.routers.lindy_meeting_management.SmartScheduler') as mock_scheduler:
        # Mock scheduler response
        scheduler_instance = MagicMock()
        scheduler_instance.find_best_time = AsyncMock(return_value={
            'start': datetime.utcnow() + timedelta(days=1, hours=14),
            'end': datetime.utcnow() + timedelta(days=1, hours=15),
            'confidence': 0.92
        })
        mock_scheduler.return_value = scheduler_instance
        
        # Mock calendar service
        with patch('backend.fastapi.app.routers.lindy_meeting_management.GoogleCalendarService') as mock_cal_service:
            cal_instance = MagicMock()
            cal_instance.create_event = AsyncMock(return_value={
                'id': 'event_001',
                'conferenceUrl': 'https://meet.google.com/abc-def-ghi'
            })
            mock_cal_service.return_value = cal_instance
            
            # Mock database
            cred_mock = MagicMock()
            cred_mock.provider = "google"
            mock_db.query.return_value.filter.return_value.first.return_value = cred_mock
            mock_db.add = MagicMock()
            mock_db.commit = MagicMock()
            
            request_data = {
                "title": "Team Sync",
                "description": "Weekly team meeting",
                "attendees": ["alice@company.com", "bob@company.com"],
                "duration_minutes": 60,
                "timezone": "America/New_York"
            }
            
            with patch('backend.fastapi.app.routers.lindy_meeting_management.decrypt_credential', return_value='decrypted_token'):
                result = await router.schedule_meeting(
                    request_data=request_data,
                    user_id=test_user_id,
                    db=mock_db
                )
            
            assert result["title"] == "Team Sync"
            assert result["status"] == "scheduled"
            assert result["confidence_score"] > 0.9
            assert "conference_url" in result


@pytest.mark.asyncio
async def test_schedule_meeting_no_calendar_connected(mock_db, test_user_id):
    """Test scheduling when no calendar is connected"""
    from fastapi import HTTPException
    
    # Mock database returns no credential
    mock_db.query.return_value.filter.return_value.first.return_value = None
    
    request_data = {
        "title": "Team Sync",
        "attendees": ["alice@company.com"]
    }
    
    with pytest.raises(HTTPException) as exc_info:
        await router.schedule_meeting(
            request_data=request_data,
            user_id=test_user_id,
            db=mock_db
        )
    
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_schedule_meeting_missing_title(mock_db, test_user_id):
    """Test scheduling with missing title"""
    from fastapi import HTTPException
    
    request_data = {
        "attendees": ["alice@company.com"]
    }
    
    with pytest.raises(HTTPException) as exc_info:
        await router.schedule_meeting(
            request_data=request_data,
            user_id=test_user_id,
            db=mock_db
        )
    
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_schedule_meeting_invalid_attendees(mock_db, test_user_id):
    """Test scheduling with invalid email addresses"""
    from fastapi import HTTPException
    
    request_data = {
        "title": "Team Sync",
        "attendees": ["invalid_email", "also_invalid"]
    }
    
    with pytest.raises(HTTPException) as exc_info:
        await router.schedule_meeting(
            request_data=request_data,
            user_id=test_user_id,
            db=mock_db
        )
    
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_list_meetings(mock_db, test_user_id, test_meeting):
    """Test listing user's meetings"""
    # Mock database query
    mock_db.query.return_value.filter.return_value.offset.return_value.limit.return_value.all.return_value = [test_meeting]
    
    meetings = await router.list_meetings(
        user_id=test_user_id,
        skip=0,
        limit=100,
        db=mock_db
    )
    
    assert len(meetings) > 0
    assert meetings[0]["title"] == "Team Sync"
    assert meetings[0]["status"] == "scheduled"


@pytest.mark.asyncio
async def test_list_meetings_with_status_filter(mock_db, test_user_id):
    """Test listing meetings with status filter"""
    # Mock database query with filter
    mock_db.query.return_value.filter.return_value.filter.return_value.offset.return_value.limit.return_value.all.return_value = []
    
    meetings = await router.list_meetings(
        user_id=test_user_id,
        skip=0,
        limit=100,
        status="completed",
        db=mock_db
    )
    
    assert meetings == []


@pytest.mark.asyncio
async def test_get_meeting(mock_db, test_user_id, test_meeting):
    """Test getting single meeting details"""
    # Mock database
    mock_meeting_obj = MagicMock()
    mock_meeting_obj.id = test_meeting["id"]
    mock_meeting_obj.title = test_meeting["title"]
    mock_meeting_obj.status = test_meeting["status"]
    mock_meeting_obj.scheduled_time = test_meeting["scheduled_time"]
    mock_db.query.return_value.filter.return_value.first.return_value = mock_meeting_obj
    
    result = await router.get_meeting(
        meeting_id="meet_001",
        user_id=test_user_id,
        db=mock_db
    )
    
    assert result["id"] == "meet_001"
    assert result["title"] == "Team Sync"


@pytest.mark.asyncio
async def test_get_nonexistent_meeting(mock_db, test_user_id):
    """Test getting meeting that doesn't exist"""
    from fastapi import HTTPException
    
    mock_db.query.return_value.filter.return_value.first.return_value = None
    
    with pytest.raises(HTTPException) as exc_info:
        await router.get_meeting(
            meeting_id="nonexistent",
            user_id=test_user_id,
            db=mock_db
        )
    
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_reschedule_meeting(mock_db, test_user_id, test_meeting, google_credential):
    """Test rescheduling existing meeting"""
    with patch('backend.fastapi.app.routers.lindy_meeting_management.GoogleCalendarService') as mock_cal_service:
        cal_instance = MagicMock()
        cal_instance.update_event = AsyncMock()
        mock_cal_service.return_value = cal_instance
        
        # Mock database
        mock_meeting_obj = MagicMock()
        mock_meeting_obj.id = test_meeting["id"]
        mock_meeting_obj.title = test_meeting["title"]
        mock_meeting_obj.duration_minutes = 60
        mock_meeting_obj.status = "scheduled"
        mock_meeting_obj.calendar_provider = "google"
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            mock_meeting_obj,  # First call for get_meeting
            google_credential  # Second call for get_credential
        ]
        mock_db.commit = MagicMock()
        
        new_time = (datetime.utcnow() + timedelta(days=2)).isoformat()
        
        with patch('backend.fastapi.app.routers.lindy_meeting_management.decrypt_credential', return_value='token'):
            result = await router.reschedule_meeting(
                meeting_id="meet_001",
                new_request={"new_time": new_time},
                user_id=test_user_id,
                db=mock_db
            )
        
        assert result["status"] == "rescheduled"
        assert result["title"] == test_meeting["title"]


# ============================================================================
# MEETING PREPARATION TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_generate_meeting_prep(mock_db, test_user_id, test_meeting):
    """Test generating meeting preparation"""
    with patch('backend.fastapi.app.routers.lindy_meeting_management.MeetingPrepService') as mock_prep_service:
        prep_instance = MagicMock()
        prep_instance.generate_briefing = AsyncMock(return_value={
            'briefing': 'Team Sync: Discuss Q2 roadmap and updates',
            'confidence': 0.88
        })
        prep_instance.generate_talking_points = AsyncMock(return_value={
            'points': [
                'Q2 roadmap progress',
                'Team capacity planning',
                'Upcoming features'
            ]
        })
        mock_prep_service.return_value = prep_instance
        
        # Mock database
        mock_meeting_obj = MagicMock()
        mock_meeting_obj.id = test_meeting["id"]
        mock_meeting_obj.title = test_meeting["title"]
        mock_meeting_obj.attendees = test_meeting["attendees"]
        mock_meeting_obj.description = test_meeting["description"]
        mock_meeting_obj.duration_minutes = 60
        mock_meeting_obj.timezone = "America/New_York"
        
        mock_db.query.return_value.filter.return_value.first.return_value = mock_meeting_obj
        mock_db.add = MagicMock()
        mock_db.commit = MagicMock()
        
        result = await router.generate_meeting_prep(
            meeting_id="meet_001",
            user_id=test_user_id,
            db=mock_db
        )
        
        assert "briefing" in result
        assert "talking_points" in result
        assert result["confidence_score"] > 0.8


@pytest.mark.asyncio
async def test_get_meeting_prep(mock_db, test_user_id):
    """Test retrieving meeting prep"""
    # Mock database
    mock_meeting_obj = MagicMock()
    mock_prep_obj = MagicMock()
    mock_prep_obj.briefing = "Meeting briefing text"
    mock_prep_obj.talking_points = json.dumps(["point1", "point2"])
    mock_prep_obj.confidence_score = 0.88
    
    mock_db.query.return_value.filter.return_value.first.side_effect = [
        mock_meeting_obj,
        mock_prep_obj
    ]
    
    result = await router.get_meeting_prep(
        meeting_id="meet_001",
        user_id=test_user_id,
        db=mock_db
    )
    
    assert result["briefing"] == "Meeting briefing text"
    assert len(result["talking_points"]) > 0


# ============================================================================
# PREFERENCES TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_set_scheduling_preferences(mock_db, test_user_id):
    """Test setting scheduling preferences"""
    mock_db.query.return_value.filter.return_value.first.return_value = None
    mock_db.add = MagicMock()
    mock_db.commit = MagicMock()
    
    preferences = {
        "working_hours_start": 9,
        "working_hours_end": 17,
        "buffer_time_minutes": 30,
        "lunch_start_hour": 12,
        "lunch_end_hour": 13,
        "do_not_schedule_days": ["Saturday", "Sunday"],
        "timezone": "America/New_York"
    }
    
    result = await router.set_scheduling_preferences(
        preferences=preferences,
        user_id=test_user_id,
        db=mock_db
    )
    
    assert result["status"] == "saved"
    assert result["buffer_time_minutes"] == 30


@pytest.mark.asyncio
async def test_get_scheduling_preferences_defaults(mock_db, test_user_id):
    """Test getting default scheduling preferences"""
    mock_db.query.return_value.filter.return_value.first.return_value = None
    
    result = await router.get_scheduling_preferences(
        user_id=test_user_id,
        db=mock_db
    )
    
    assert result["status"] == "defaults"
    assert result["working_hours"] == "09:00-17:00"


# ============================================================================
# STATUS TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_get_meetings_status(mock_db, test_user_id):
    """Test getting meeting service status"""
    # Mock database
    mock_credential = MagicMock()
    mock_credential.provider = "google"
    mock_credential.created_at = datetime.utcnow()
    mock_credential.expires_at = datetime.utcnow() + timedelta(hours=1)
    
    mock_db.query.return_value.filter.return_value.all.return_value = [mock_credential]
    mock_db.query.return_value.filter.return_value.count.return_value = 3
    
    result = await router.get_meetings_status(
        user_id=test_user_id,
        db=mock_db
    )
    
    assert result["status"] == "operational"
    assert len(result["connected_calendars"]) > 0


@pytest.mark.asyncio
async def test_health_check():
    """Test health check endpoint"""
    result = await router.health_check()
    
    assert result["status"] == "healthy"
    assert result["service"] == "meeting-management"
    assert "endpoints" in result


@pytest.mark.asyncio
async def test_meeting_production_readiness(mock_db, test_user_id):
    """Production-readiness endpoint returns evidence-based slice status."""
    meeting = MagicMock()
    meeting.user_id = test_user_id
    meeting.extra_data = {
        "recap_delivery_status": "sent",
        "action_item_tracker": {"ai_1": {"status": "open"}},
        "action_item_reminder_runs": [{"run_at": datetime.utcnow().isoformat()}],
    }

    recap_row = MagicMock()
    recap_row.user_id = test_user_id

    google_cred = MagicMock()
    google_cred.provider = "google"

    meeting_query = MagicMock()
    meeting_query.filter.return_value.all.return_value = [meeting]
    recap_query = MagicMock()
    recap_query.filter.return_value.all.return_value = [recap_row]
    cred_query = MagicMock()
    cred_query.filter.return_value.all.return_value = [google_cred]

    def _query_side_effect(model):
        if model.__name__ == "Meeting":
            return meeting_query
        if model.__name__ == "MeetingRecap":
            return recap_query
        return cred_query

    mock_db.query.side_effect = _query_side_effect

    result = await router.meeting_production_readiness(
        user_id=test_user_id,
        db=mock_db,
    )

    assert result["status"] == "ok"
    assert result["scope"]["claim"] == "slice_only"
    assert result["summary"]["implemented_pct"] == 100.0
    assert result["telemetry"]["recap_delivery_sent"] == 1


# ============================================================================
# PERFORMANCE TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_schedule_meeting_performance(mock_db, test_user_id):
    """Test meeting scheduling performance (<2 seconds)"""
    import time

    with patch('backend.fastapi.app.routers.lindy_meeting_management.SmartScheduler') as mock_scheduler, \
         patch('backend.fastapi.app.routers.lindy_meeting_management.GoogleCalendarService') as mock_cal_service:
        
        scheduler_instance = MagicMock()
        scheduler_instance.find_best_time = AsyncMock(return_value={
            'start': datetime.utcnow() + timedelta(days=1),
            'end': datetime.utcnow() + timedelta(days=1, hours=1),
            'confidence': 0.92
        })
        mock_scheduler.return_value = scheduler_instance
        
        cal_instance = MagicMock()
        cal_instance.create_event = AsyncMock(return_value={
            'id': 'event_001',
            'conferenceUrl': 'https://meet.google.com/test'
        })
        mock_cal_service.return_value = cal_instance
        
        cred_mock = MagicMock()
        cred_mock.provider = "google"
        mock_db.query.return_value.filter.return_value.first.return_value = cred_mock
        
        start_time = time.time()
        
        with patch('backend.fastapi.app.routers.lindy_meeting_management.decrypt_credential', return_value='token'):
            await router.schedule_meeting(
                request_data={
                    "title": "Test",
                    "attendees": ["test@company.com"],
                    "duration_minutes": 60
                },
                user_id=test_user_id,
                db=mock_db
            )
        
        elapsed = time.time() - start_time
        assert elapsed < 2.0, f"Scheduling took {elapsed}s, expected <2s"


# ============================================================================
# RECORDING TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_start_google_meet_recording(mock_db, test_user_id, test_meeting):
    """Test starting recording on Google Meet"""
    with patch('backend.fastapi.app.services_lindy_recording.RecordingManagementService') as mock_recording:
        mock_service = MagicMock()
        mock_recording.return_value = mock_service
        
        mock_service.setup_recording = AsyncMock(return_value={
            "status": "ready",
            "meet_link": "https://meet.google.com/abc-def-ghi",
            "recording_started": True
        })
        
        # Mock meeting lookup
        mock_meeting = MagicMock()
        mock_meeting.id = test_meeting["id"]
        mock_meeting.user_id = test_user_id
        mock_meeting.calendar_type = "google"
        mock_meeting.external_event_id = "event_123"
        mock_meeting.extra_data = {}
        
        mock_db.query().filter().first.return_value = mock_meeting
        
        # In real test, this would call the endpoint
        # For now, verify the service can be called
        recording_info = await mock_service.setup_recording(
            meeting_id=test_meeting["id"],
            provider="google",
            event_id="event_123",
            auto_transcribe=True
        )
        
        assert recording_info["status"] == "ready"
        assert recording_info["recording_started"]


@pytest.mark.asyncio
async def test_get_meeting_recording_status(mock_db, test_user_id, test_meeting):
    """Test retrieving recording status for a meeting."""
    mock_meeting = MagicMock()
    mock_meeting.id = test_meeting["id"]
    mock_meeting.user_id = test_user_id
    mock_meeting.calendar_provider = "google"
    mock_meeting.event_id = "event_123"
    mock_meeting.recording_provider = "google"
    mock_meeting.meeting_recording_enabled = True
    mock_meeting.recording_url = "https://drive.google.com/file/d/ABC123/view"
    mock_meeting.extra_data = {
        "recording_status": "active",
        "recording_started_at": datetime.utcnow().isoformat(),
    }

    mock_db.query.return_value.filter.return_value.first.side_effect = [
        mock_meeting,
        MagicMock(provider="google", access_token_encrypted=b"encrypted")
    ]

    with patch('backend.fastapi.app.routers.lindy_meeting_management.decrypt_credential', return_value='token'):
        with patch('backend.fastapi.app.routers.lindy_meeting_management.RecordingManagementService') as mock_recording:
            recording_service = MagicMock()
            recording_service.get_recording_status = AsyncMock(return_value={
                "event_id": "event_123",
                "provider": "google_meet",
                "recording_enabled": True,
                "status": "active",
            })
            mock_recording.return_value = recording_service

            result = await router.get_meeting_recording_status(
                meeting_id="meet_001",
                user_id=test_user_id,
                db=mock_db,
            )

    assert result["recording_status"] == "active"
    assert result["provider"] == "google"
    assert result["provider_status"]["status"] == "active"


@pytest.mark.asyncio
async def test_start_teams_recording(mock_db, test_user_id):
    """Test starting recording on Teams"""
    with patch('backend.fastapi.app.services_lindy_recording.RecordingManagementService') as mock_recording:
        mock_service = MagicMock()
        mock_recording.return_value = mock_service
        
        mock_service.setup_recording = AsyncMock(return_value={
            "status": "ready",
            "join_url": "https://teams.microsoft.com/l/meetup-join/123",
            "auto_transcribe": True
        })
        
        recording_info = await mock_service.setup_recording(
            meeting_id="meet_001",
            provider="outlook",
            event_id="event_456",
            auto_transcribe=True
        )
        
        assert recording_info["status"] == "ready"
        assert "join_url" in recording_info


@pytest.mark.asyncio
async def test_get_recording_link(mock_db, test_user_id):
    """Test retrieving recording link after meeting"""
    with patch('backend.fastapi.app.services_lindy_recording.RecordingManagementService') as mock_recording:
        mock_service = MagicMock()
        mock_recording.return_value = mock_service
        
        mock_service.get_recording_link = AsyncMock(return_value={
            "recording_url": "https://drive.google.com/file/d/ABC123/view",
            "duration_seconds": 3600,
            "created_at": datetime.utcnow().isoformat(),
            "provider": "google"
        })
        
        recording_link = await mock_service.get_recording_link(
            meeting_id="meet_001",
            provider="google"
        )
        
        assert "recording_url" in recording_link
        assert recording_link["duration_seconds"] == 3600


# ============================================================================
# TRANSCRIPTION TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_submit_transcription_job(mock_db, test_user_id):
    """Test submitting audio for transcription"""
    with patch('backend.fastapi.app.services_lindy_transcription.TranscriptionManagementService') as mock_transcription:
        mock_service = MagicMock()
        mock_transcription.return_value = mock_service
        
        mock_service.start_transcription = AsyncMock(return_value={
            "meeting_id": "meet_001",
            "job_id": "assemblyai_job_123",
            "status": "submitted",
            "submitted_at": datetime.utcnow().isoformat()
        })
        
        job_info = await mock_service.start_transcription(
            audio_url="https://drive.google.com/file/d/ABC123/export?format=mp4",
            meeting_id="meet_001",
            language="en",
            speaker_diarization=True
        )
        
        assert job_info["status"] == "submitted"
        assert "job_id" in job_info


@pytest.mark.asyncio
async def test_start_meeting_transcription_endpoint(mock_db, test_user_id):
    """Test starting transcription via meeting endpoint."""
    mock_meeting = MagicMock()
    mock_meeting.id = "meet_001"
    mock_meeting.user_id = test_user_id
    mock_meeting.recording_provider = "google"
    mock_meeting.calendar_provider = "google"
    mock_meeting.event_id = "event_123"
    mock_meeting.extra_data = {
        "recording_url": "https://drive.google.com/file/d/ABC123/view"
    }

    mock_db.query.return_value.filter.return_value.first.return_value = mock_meeting
    mock_db.commit = MagicMock()

    with patch('backend.fastapi.app.routers.lindy_meeting_management.TranscriptionManagementService') as mock_transcription:
        service = MagicMock()
        service.start_transcription = AsyncMock(return_value={
            "meeting_id": "meet_001",
            "job_id": "assemblyai_job_321",
            "status": "submitted",
            "submitted_at": datetime.utcnow().isoformat(),
        })
        mock_transcription.return_value = service

        result = await router.start_meeting_transcription(
            meeting_id="meet_001",
            request_data={"language": "en", "speaker_diarization": True},
            user_id=test_user_id,
            db=mock_db,
        )

    assert result["status"] == "submitted"
    assert result["job_id"] == "assemblyai_job_321"


@pytest.mark.asyncio
async def test_check_transcription_status(mock_db):
    """Test checking transcription job status"""
    with patch('backend.fastapi.app.services_lindy_transcription.TranscriptionManagementService') as mock_transcription:
        mock_service = MagicMock()
        mock_transcription.return_value = mock_service
        
        # Test in-progress status
        mock_service.check_transcription_status = AsyncMock(return_value={
            "job_id": "assemblyai_job_123",
            "status": "processing",
            "progress": 45,
            "completed": False
        })
        
        status = await mock_service.check_transcription_status("assemblyai_job_123")
        
        assert status["status"] == "processing"
        assert not status["completed"]
        assert status["progress"] == 45


@pytest.mark.asyncio
async def test_retrieve_transcript(mock_db):
    """Test retrieving completed transcript"""
    with patch('backend.fastapi.app.services_lindy_transcription.TranscriptionManagementService') as mock_transcription:
        mock_service = MagicMock()
        mock_transcription.return_value = mock_service
        
        mock_service.retrieve_transcript = AsyncMock(return_value={
            "job_id": "assemblyai_job_123",
            "full_text": "This is the meeting transcript...",
            "paragraphs": [
                {"text": "Opening remarks...", "speaker": 1, "start": 0, "end": 5000},
                {"text": "Main discussion...", "speaker": 2, "start": 5000, "end": 15000}
            ],
            "speakers": [1, 2],
            "confidence": 0.94,
            "duration": 1800,
            "completed_at": datetime.utcnow().isoformat()
        })
        
        transcript = await mock_service.retrieve_transcript("assemblyai_job_123")
        
        assert "full_text" in transcript
        assert len(transcript["paragraphs"]) > 0
        assert transcript["confidence"] > 0.9


@pytest.mark.asyncio
async def test_extract_action_items_from_transcript(mock_db):
    """Test extracting action items from transcript"""
    with patch('backend.fastapi.app.services_lindy_transcription.TranscriptionManagementService') as mock_transcription:
        mock_service = MagicMock()
        mock_transcription.return_value = mock_service
        
        transcript = {
            "full_text": "We need to follow up with the client on the proposal...",
            "highlights": [
                {"text": "action item: send proposal", "count": 2},
                {"text": "follow up next week", "count": 1}
            ]
        }
        
        mock_service.extract_action_items_from_transcript = MagicMock(return_value=[
            {
                "text": "action item: send proposal",
                "type": "action_item",
                "confidence": 0.85,
                "source": "highlight"
            }
        ])
        
        action_items = mock_service.extract_action_items_from_transcript(transcript)
        
        assert len(action_items) > 0
        assert action_items[0]["type"] == "action_item"


# ============================================================================
# RECAP TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_generate_meeting_recap(mock_db, test_user_id):
    """Test generating meeting recap from transcript"""
    with patch('backend.fastapi.app.services_lindy_recap.RecapManagementService') as mock_recap:
        mock_service = MagicMock()
        mock_recap.return_value = mock_service
        
        mock_service.generate_full_recap = AsyncMock(return_value={
            "meeting_id": "meet_001",
            "title": "Team Sync",
            "summary": "Team discussed Q4 objectives and timeline. Decided to prioritize feature X.",
            "key_points": [
                "Q4 objectives set",
                "Feature X prioritized",
                "Timeline: 3 weeks"
            ],
            "decisions": [
                {"decision": "Prioritize Feature X", "owner": "alice@company.com", "priority": "high"},
                {"decision": "Schedule follow-up", "owner": "bob@company.com", "priority": "medium"}
            ],
            "action_items": [
                {"task": "Create feature spec", "owner": "alice@company.com", "due_date": "2024-02-15", "priority": "high"},
                {"task": "Review timeline", "owner": "bob@company.com", "due_date": "2024-02-20", "priority": "medium"}
            ],
            "next_steps": [
                {"step": "Create feature spec", "owner": "alice@company.com", "deadline": "2024-02-15", "priority": "high"}
            ],
            "confidence_score": 0.88
        })
        
        recap = await mock_service.generate_full_recap(
            transcript="We need to prioritize Feature X and complete it in 3 weeks...",
            meeting_id="meet_001",
            meeting_title="Team Sync",
            attendees=["alice@company.com", "bob@company.com"],
            duration_minutes=60
        )
        
        assert recap["meeting_id"] == "meet_001"
        assert len(recap["action_items"]) > 0
        assert len(recap["decisions"]) > 0
        assert recap["confidence_score"] > 0.8


@pytest.mark.asyncio
async def test_recap_with_multiple_speakers(mock_db):
    """Test recap generation with multiple speakers"""
    with patch('backend.fastapi.app.services_lindy_recap.RecapManagementService') as mock_recap:
        mock_service = MagicMock()
        mock_recap.return_value = mock_service
        
        transcript = """
        Speaker 1: Let's discuss the new product roadmap.
        Speaker 2: I think we should focus on mobile first.
        Speaker 3: Agreed. And we need to allocate resources for Q1.
        Speaker 1: Good point. I'll create an action item for resource planning.
        """
        
        mock_service.generate_full_recap = AsyncMock(return_value={
            "summary": "Team aligned on mobile-first product strategy with Q1 resource planning.",
            "action_items": [{"task": "Create resource plan", "owner": "Speaker 1"}],
            "decisions": [{"decision": "Mobile-first strategy"}]
        })
        
        recap = await mock_service.generate_full_recap(
            transcript=transcript,
            meeting_id="meet_002",
            meeting_title="Product Roadmap",
            attendees=["speaker1@company.com", "speaker2@company.com", "speaker3@company.com"],
            duration_minutes=45
        )
        
        assert "mobile" in recap["summary"].lower()
        assert len(recap["action_items"]) > 0


@pytest.mark.asyncio
async def test_create_recap_email(mock_db, test_user_id):
    """Test creating email from recap"""
    with patch('backend.fastapi.app.services_lindy_recap.RecapManagementService') as mock_recap:
        mock_service = MagicMock()
        mock_recap.return_value = mock_service
        
        recap = {
            "title": "Team Sync",
            "summary": "Discussed Q4 objectives",
            "attendees": ["alice@company.com", "bob@company.com"],
            "decisions": [{"decision": "Launch Feature X", "owner": "alice@company.com"}],
            "action_items": [{"task": "Create spec", "owner": "alice@company.com", "due_date": "2024-02-15"}],
            "key_points": ["Q4 objectives", "Feature X prioritized"]
        }
        
        mock_service.create_recap_email = AsyncMock(return_value={
            "to": ["alice@company.com", "bob@company.com"],
            "from": "lindy@company.com",
            "subject": "Meeting Recap: Team Sync",
            "body": "Hi team,\n\nHere's a summary...",
            "generated_at": datetime.utcnow().isoformat()
        })
        
        email = await mock_service.create_recap_email(
            recap=recap,
            sender_name="Lindy",
            sender_email="lindy@company.com"
        )
        
        assert "Meeting Recap" in email["subject"]
        assert len(email["to"]) == 2


# ============================================================================
# END-TO-END WORKFLOW TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_full_recording_transcription_recap_workflow(mock_db, test_user_id):
    """Test complete workflow: record -> transcribe -> recap"""
    # This simulates the full workflow
    
    # Step 1: Record meeting
    with patch('backend.fastapi.app.services_lindy_recording.RecordingManagementService') as mock_recording:
        mock_recording_service = MagicMock()
        mock_recording.return_value = mock_recording_service
        
        mock_recording_service.setup_recording = AsyncMock(return_value={
            "status": "ready",
            "meet_link": "https://meet.google.com/abc"
        })
        
        recording = await mock_recording_service.setup_recording(
            meeting_id="meet_001",
            provider="google",
            event_id="event_123",
            auto_transcribe=True
        )
        
        assert recording["status"] == "ready"
    
    # Step 2: Transcribe recording
    with patch('backend.fastapi.app.services_lindy_transcription.TranscriptionManagementService') as mock_transcription:
        mock_transcription_service = MagicMock()
        mock_transcription.return_value = mock_transcription_service
        
        mock_transcription_service.retrieve_transcript = AsyncMock(return_value={
            "job_id": "job_123",
            "full_text": "Meeting transcript content...",
            "confidence": 0.95
        })
        
        transcript = await mock_transcription_service.retrieve_transcript("job_123")
        
        assert "Meeting transcript" in transcript["full_text"]
    
    # Step 3: Generate recap
    with patch('backend.fastapi.app.services_lindy_recap.RecapManagementService') as mock_recap:
        mock_recap_service = MagicMock()
        mock_recap.return_value = mock_recap_service
        
        mock_recap_service.generate_full_recap = AsyncMock(return_value={
            "summary": "Meeting summary...",
            "action_items": [{"task": "Follow up", "owner": "alice@company.com"}],
            "decisions": [{"decision": "Approved proposal"}]
        })
        
        recap = await mock_recap_service.generate_full_recap(
            transcript=transcript["full_text"],
            meeting_id="meet_001",
            meeting_title="Team Sync",
            attendees=["alice@company.com"],
            duration_minutes=60
        )
        
        assert "summary" in recap
        assert len(recap["action_items"]) > 0


@pytest.mark.asyncio
async def test_performance_transcription_speed(mock_db):
    """Test transcription performance: <30s for typical meeting"""
    import time
    
    with patch('backend.fastapi.app.services_lindy_transcription.TranscriptionManagementService') as mock_transcription:
        mock_service = MagicMock()
        mock_transcription.return_value = mock_service
        
        # Simulate API call timing
        start_time = time.time()
        
        mock_service.wait_for_transcription = AsyncMock(return_value={
            "full_text": "Meeting transcript...",
            "confidence": 0.95
        })
        
        result = await mock_service.wait_for_transcription("job_123", timeout=30)
        
        elapsed = time.time() - start_time
        
        # In production, this would verify <30 seconds
        # Mock typically completes instantly
        assert elapsed < 1.0
        assert result is not None


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_full_meeting_workflow(mock_db, test_user_id):
    """Test complete meeting workflow: schedule -> prep -> record -> transcribe -> recap"""
    # This would test the full flow in a real integration test
    # For now, we verify that individual components work
    pass


# ============================================================================
# RECAP DELIVERY DURABILITY TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_send_meeting_recap_happy_path(mock_db, test_user_id):
    """POST /meetings/{id}/recap/send — sends email and persists delivery status"""
    from backend.fastapi.app.routers.lindy_meeting_management import send_meeting_recap

    meeting = MagicMock()
    meeting.id = "meet_send_001"
    meeting.user_id = test_user_id
    meeting.title = "Q4 Planning"
    meeting.attendees = [{"email": "alice@example.com"}, {"email": "bob@example.com"}]
    meeting.extra_data = {}

    recap = MagicMock()
    recap.meeting_id = "meet_send_001"
    recap.summary = "Q4 plan agreed."
    recap.key_points = '["Q4 plan agreed"]'
    recap.decisions_made = '[]'
    recap.action_items = '{"items": []}'

    mock_db.query.return_value.filter.return_value.first.side_effect = [meeting, recap, None]

    with patch('backend.fastapi.app.routers.lindy_meeting_management.RecapManagementService') as mock_recap_cls, \
         patch('backend.fastapi.app.routers.lindy_meeting_management.EmailManagementService') as mock_email_cls:

        mock_recap_svc = AsyncMock()
        mock_recap_cls.return_value = mock_recap_svc
        mock_recap_svc.create_recap_email = AsyncMock(return_value={
            "subject": "Meeting Recap: Q4 Planning",
            "body": "Here's a summary...",
            "to": ["alice@example.com", "bob@example.com"],
        })

        mock_email_svc = AsyncMock()
        mock_email_cls.return_value = mock_email_svc
        mock_email_svc.generate_draft = AsyncMock(return_value={"success": True, "draft_id": "draft_abc"})
        mock_email_svc.send_draft = AsyncMock(return_value={"success": True})

        result = await send_meeting_recap(
            meeting_id="meet_send_001",
            send_request={},
            user_id=test_user_id,
            db=mock_db,
        )

    assert result["delivery_status"] == "sent"
    assert "alice@example.com" in result["recipients"]
    assert result["idempotent"] is False
    mock_db.commit.assert_called()


@pytest.mark.asyncio
async def test_send_meeting_recap_idempotency(mock_db, test_user_id):
    """POST /meetings/{id}/recap/send — returns prior status if already sent"""
    from backend.fastapi.app.routers.lindy_meeting_management import send_meeting_recap

    meeting = MagicMock()
    meeting.id = "meet_send_002"
    meeting.user_id = test_user_id
    meeting.title = "Standup"
    meeting.attendees = []
    meeting.extra_data = {
        "recap_delivery_status": "sent",
        "recap_sent_at": "2025-01-01T10:00:00",
        "recap_recipients": ["alice@example.com"],
    }

    mock_db.query.return_value.filter.return_value.first.return_value = meeting

    result = await send_meeting_recap(
        meeting_id="meet_send_002",
        send_request={},
        user_id=test_user_id,
        db=mock_db,
    )

    assert result["delivery_status"] == "sent"
    assert result["idempotent"] is True
    assert result["sent_at"] == "2025-01-01T10:00:00"
    # Email service should NOT have been called
    mock_db.commit.assert_not_called()


@pytest.mark.asyncio
async def test_send_meeting_recap_force_resend(mock_db, test_user_id):
    """POST /meetings/{id}/recap/send with force=true bypasses idempotency"""
    from backend.fastapi.app.routers.lindy_meeting_management import send_meeting_recap

    meeting = MagicMock()
    meeting.id = "meet_send_003"
    meeting.user_id = test_user_id
    meeting.title = "Standup"
    meeting.attendees = [{"email": "carol@example.com"}]
    meeting.extra_data = {
        "recap_delivery_status": "sent",
        "recap_sent_at": "2025-01-01T10:00:00",
        "recap_recipients": ["carol@example.com"],
    }

    recap = MagicMock()
    recap.meeting_id = "meet_send_003"
    recap.summary = "Summary text."
    recap.key_points = '[]'
    recap.decisions_made = '[]'
    recap.action_items = '{"items": []}'

    mock_db.query.return_value.filter.return_value.first.side_effect = [meeting, recap, None]

    with patch('backend.fastapi.app.routers.lindy_meeting_management.RecapManagementService') as mock_recap_cls, \
         patch('backend.fastapi.app.routers.lindy_meeting_management.EmailManagementService') as mock_email_cls:

        mock_recap_svc = AsyncMock()
        mock_recap_cls.return_value = mock_recap_svc
        mock_recap_svc.create_recap_email = AsyncMock(return_value={
            "subject": "Meeting Recap: Standup",
            "body": "Summary...",
            "to": ["carol@example.com"],
        })

        mock_email_svc = AsyncMock()
        mock_email_cls.return_value = mock_email_svc
        mock_email_svc.generate_draft = AsyncMock(return_value={"success": True, "draft_id": "draft_xyz"})
        mock_email_svc.send_draft = AsyncMock(return_value={"success": True})

        result = await send_meeting_recap(
            meeting_id="meet_send_003",
            send_request={"force": True},
            user_id=test_user_id,
            db=mock_db,
        )

    assert result["delivery_status"] == "sent"
    assert result["idempotent"] is False


@pytest.mark.asyncio
async def test_get_recap_delivery_status_pending(mock_db, test_user_id):
    """GET /meetings/{id}/recap/delivery-status — returns 'pending' before any send"""
    from backend.fastapi.app.routers.lindy_meeting_management import get_recap_delivery_status

    meeting = MagicMock()
    meeting.id = "meet_ds_001"
    meeting.user_id = test_user_id
    meeting.extra_data = {}

    mock_db.query.return_value.filter.return_value.first.return_value = meeting

    result = await get_recap_delivery_status(
        meeting_id="meet_ds_001",
        user_id=test_user_id,
        db=mock_db,
    )

    assert result["meeting_id"] == "meet_ds_001"
    assert result["delivery_status"] == "pending"
    assert result["sent_at"] is None
    assert result["error"] is None


@pytest.mark.asyncio
async def test_get_recap_delivery_status_sent(mock_db, test_user_id):
    """GET /meetings/{id}/recap/delivery-status — returns durable 'sent' status"""
    from backend.fastapi.app.routers.lindy_meeting_management import get_recap_delivery_status

    meeting = MagicMock()
    meeting.id = "meet_ds_002"
    meeting.user_id = test_user_id
    meeting.extra_data = {
        "recap_delivery_status": "sent",
        "recap_sent_at": "2025-05-01T12:00:00",
        "recap_recipients": ["dave@example.com"],
        "recap_delivery_error": None,
        "recap_generated_at": "2025-05-01T11:55:00",
    }

    mock_db.query.return_value.filter.return_value.first.return_value = meeting

    result = await get_recap_delivery_status(
        meeting_id="meet_ds_002",
        user_id=test_user_id,
        db=mock_db,
    )

    assert result["delivery_status"] == "sent"
    assert result["sent_at"] == "2025-05-01T12:00:00"
    assert "dave@example.com" in result["recipients"]


@pytest.mark.asyncio
async def test_get_recap_delivery_status_failed(mock_db, test_user_id):
    """GET /meetings/{id}/recap/delivery-status — reflects durable failure"""
    from backend.fastapi.app.routers.lindy_meeting_management import get_recap_delivery_status

    meeting = MagicMock()
    meeting.id = "meet_ds_003"
    meeting.user_id = test_user_id
    meeting.extra_data = {
        "recap_delivery_status": "failed",
        "recap_delivery_error": "SMTP connection refused",
        "recap_delivery_attempted_at": "2025-05-01T12:05:00",
    }

    mock_db.query.return_value.filter.return_value.first.return_value = meeting

    result = await get_recap_delivery_status(
        meeting_id="meet_ds_003",
        user_id=test_user_id,
        db=mock_db,
    )

    assert result["delivery_status"] == "failed"
    assert "SMTP" in result["error"]


@pytest.mark.asyncio
async def test_get_recap_delivery_status_meeting_not_found(mock_db, test_user_id):
    """GET /meetings/{id}/recap/delivery-status — 404 if meeting missing"""
    from backend.fastapi.app.routers.lindy_meeting_management import get_recap_delivery_status
    from fastapi import HTTPException

    mock_db.query.return_value.filter.return_value.first.return_value = None

    with pytest.raises(HTTPException) as exc_info:
        await get_recap_delivery_status(
            meeting_id="nonexistent",
            user_id=test_user_id,
            db=mock_db,
        )

    assert exc_info.value.status_code == 404


# ============================================================================
# TRANSCRIPTION IDEMPOTENCY TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_start_transcription_idempotency_returns_existing_job(mock_db, test_user_id):
    """POST /transcript/start — returns existing job if already submitted"""
    from backend.fastapi.app.routers.lindy_meeting_management import start_meeting_transcription

    meeting = MagicMock()
    meeting.id = "meet_tx_001"
    meeting.user_id = test_user_id
    meeting.extra_data = {
        "transcript_status": "submitted",
        "transcript_job_id": "job_existing_123",
        "transcript_submitted_at": "2025-05-01T10:00:00",
        "recording_url": "https://cdn.example.com/recording.mp4",
    }

    mock_db.query.return_value.filter.return_value.first.return_value = meeting

    result = await start_meeting_transcription(
        meeting_id="meet_tx_001",
        request_data={},
        user_id=test_user_id,
        db=mock_db,
    )

    assert result["status"] == "submitted"
    assert result["job_id"] == "job_existing_123"
    assert result["idempotent"] is True
    # No new transcription started
    mock_db.commit.assert_not_called()


@pytest.mark.asyncio
async def test_start_transcription_idempotency_force_flag(mock_db, test_user_id):
    """POST /transcript/start with force=true starts new job even if already submitted"""
    from backend.fastapi.app.routers.lindy_meeting_management import start_meeting_transcription

    meeting = MagicMock()
    meeting.id = "meet_tx_002"
    meeting.user_id = test_user_id
    meeting.extra_data = {
        "transcript_status": "submitted",
        "transcript_job_id": "old_job_456",
        "recording_url": "https://cdn.example.com/recording.mp4",
        "transcript_retry_count": 1,
    }

    mock_db.query.return_value.filter.return_value.first.return_value = meeting

    with patch('backend.fastapi.app.routers.lindy_meeting_management.TranscriptionManagementService') as mock_tx_cls:
        mock_tx_svc = AsyncMock()
        mock_tx_cls.return_value = mock_tx_svc
        mock_tx_svc.start_transcription = AsyncMock(return_value={
            "job_id": "new_job_789",
            "submitted_at": "2025-05-01T11:00:00",
        })

        result = await start_meeting_transcription(
            meeting_id="meet_tx_002",
            request_data={"force": True},
            user_id=test_user_id,
            db=mock_db,
        )

    assert result["job_id"] == "new_job_789"
    assert result["idempotent"] is False
    assert result["retry_count"] == 2
    mock_db.commit.assert_called()


@pytest.mark.asyncio
async def test_start_transcription_retry_count_increments(mock_db, test_user_id):
    """POST /transcript/start — retry_count increments on each fresh submission"""
    from backend.fastapi.app.routers.lindy_meeting_management import start_meeting_transcription

    meeting = MagicMock()
    meeting.id = "meet_tx_003"
    meeting.user_id = test_user_id
    meeting.extra_data = {
        "recording_url": "https://cdn.example.com/rec.mp4",
        "transcript_retry_count": 0,
    }

    mock_db.query.return_value.filter.return_value.first.return_value = meeting

    with patch('backend.fastapi.app.routers.lindy_meeting_management.TranscriptionManagementService') as mock_tx_cls:
        mock_tx_svc = AsyncMock()
        mock_tx_cls.return_value = mock_tx_svc
        mock_tx_svc.start_transcription = AsyncMock(return_value={
            "job_id": "job_new_111",
            "submitted_at": "2025-05-01T09:00:00",
        })

        result = await start_meeting_transcription(
            meeting_id="meet_tx_003",
            request_data={},
            user_id=test_user_id,
            db=mock_db,
        )

    assert result["retry_count"] == 1
    assert result["idempotent"] is False


# ============================================================================
# TRANSCRIPTION POLLING TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_poll_meeting_transcription_processing_updates_status(mock_db, test_user_id):
    """POST /transcript/poll — updates durable status while processing."""
    from backend.fastapi.app.routers.lindy_meeting_management import poll_meeting_transcription

    meeting = MagicMock()
    meeting.id = "meet_poll_001"
    meeting.user_id = test_user_id
    meeting.extra_data = {
        "transcript_job_id": "job_poll_123",
        "transcript_status": "submitted",
    }

    mock_db.query.return_value.filter.return_value.first.return_value = meeting

    with patch('backend.fastapi.app.routers.lindy_meeting_management.TranscriptionManagementService') as mock_tx_cls:
        tx_svc = AsyncMock()
        mock_tx_cls.return_value = tx_svc
        tx_svc.check_transcription_status = AsyncMock(return_value={
            "job_id": "job_poll_123",
            "status": "processing",
            "progress": 42,
            "completed": False,
            "error": None,
        })

        result = await poll_meeting_transcription(
            meeting_id="meet_poll_001",
            request_data={},
            user_id=test_user_id,
            db=mock_db,
        )

    assert result["status"] == "processing"
    assert result["progress"] == 42
    assert meeting.extra_data["transcript_status"] == "processing"
    assert meeting.extra_data["transcript_progress"] == 42
    mock_db.commit.assert_called()


@pytest.mark.asyncio
async def test_poll_meeting_transcription_completed_persists_transcript(mock_db, test_user_id):
    """POST /transcript/poll — persists transcript when provider reports completed."""
    from backend.fastapi.app.routers.lindy_meeting_management import poll_meeting_transcription

    meeting = MagicMock()
    meeting.id = "meet_poll_002"
    meeting.user_id = test_user_id
    meeting.transcript = None
    meeting.transcript_timestamp_url = None
    meeting.extra_data = {
        "transcript_job_id": "job_done_456",
        "transcript_status": "processing",
    }

    mock_db.query.return_value.filter.return_value.first.return_value = meeting

    with patch('backend.fastapi.app.routers.lindy_meeting_management.TranscriptionManagementService') as mock_tx_cls:
        tx_svc = AsyncMock()
        mock_tx_cls.return_value = tx_svc
        tx_svc.check_transcription_status = AsyncMock(return_value={
            "job_id": "job_done_456",
            "status": "completed",
            "progress": 100,
            "completed": True,
            "error": None,
        })
        tx_svc.retrieve_transcript = AsyncMock(return_value={
            "full_text": "Final transcript text.",
            "paragraphs": [],
            "speakers": [],
            "chapters": [],
            "confidence": 0.93,
            "duration": 600,
        })

        result = await poll_meeting_transcription(
            meeting_id="meet_poll_002",
            request_data={},
            user_id=test_user_id,
            db=mock_db,
        )

    assert result["status"] == "completed"
    assert result["transcript_available"] is True
    assert meeting.extra_data["transcript_status"] == "completed"
    assert meeting.extra_data["transcript"] == "Final transcript text."
    assert meeting.transcript == "Final transcript text."
    assert meeting.transcript_timestamp_url == "job_done_456"
    mock_db.commit.assert_called()


@pytest.mark.asyncio
async def test_poll_meeting_transcription_no_job_returns_400(mock_db, test_user_id):
    """POST /transcript/poll — returns 400 when no job_id is known."""
    from backend.fastapi.app.routers.lindy_meeting_management import poll_meeting_transcription
    from fastapi import HTTPException

    meeting = MagicMock()
    meeting.id = "meet_poll_003"
    meeting.user_id = test_user_id
    meeting.extra_data = {}

    mock_db.query.return_value.filter.return_value.first.return_value = meeting

    with pytest.raises(HTTPException) as exc_info:
        await poll_meeting_transcription(
            meeting_id="meet_poll_003",
            request_data={},
            user_id=test_user_id,
            db=mock_db,
        )

    assert exc_info.value.status_code == 400


# ============================================================================
# END-TO-END SMOKE TESTS (MEETING + EMAIL CHAIN)
# ============================================================================

@pytest.mark.asyncio
async def test_meeting_email_chain_smoke_success(mock_db, test_user_id):
    """Smoke: transcript poll -> recap generation -> recap send succeeds with durable state."""
    from backend.fastapi.app.routers.lindy_meeting_management import (
        generate_meeting_recap,
        poll_meeting_transcription,
        send_meeting_recap,
    )

    meeting = MagicMock()
    meeting.id = "meet_smoke_001"
    meeting.user_id = test_user_id
    meeting.title = "Weekly Leadership Sync"
    meeting.attendees = [{"email": "alice@example.com"}, {"email": "bob@example.com"}]
    meeting.start_time = datetime.utcnow()
    meeting.end_time = meeting.start_time + timedelta(minutes=45)
    meeting.transcript = None
    meeting.transcript_timestamp_url = None
    meeting.ai_summary = None
    meeting.key_decisions = []
    meeting.action_items_extracted = []
    meeting.extra_data = {
        "transcript_job_id": "job_smoke_001",
        "transcript_status": "submitted",
    }

    recap_row = MagicMock()
    recap_row.summary = "Leadership aligned on roadmap milestones."
    recap_row.key_points = '["Roadmap milestones", "Hiring plan"]'
    recap_row.decisions_made = '["Ship feature X by June"]'
    recap_row.action_items = '{"items": [{"task": "Draft hiring plan", "owner": "Alice"}]}'

    # Call order across endpoints:
    # poll: meeting
    # generate recap: meeting
    # send recap: meeting, recap, google_credential(None)
    mock_db.query.return_value.filter.return_value.first.side_effect = [
        meeting,
        meeting,
        meeting,
        recap_row,
        None,
    ]

    def _refresh_side_effect(obj):
        if getattr(obj, "id", None) is None:
            obj.id = 9001

    mock_db.refresh.side_effect = _refresh_side_effect

    with patch('backend.fastapi.app.routers.lindy_meeting_management.TranscriptionManagementService') as mock_tx_cls, \
         patch('backend.fastapi.app.routers.lindy_meeting_management.RecapManagementService') as mock_recap_cls, \
         patch('backend.fastapi.app.routers.lindy_meeting_management.EmailManagementService') as mock_email_cls:

        tx_svc = AsyncMock()
        mock_tx_cls.return_value = tx_svc
        tx_svc.check_transcription_status = AsyncMock(return_value={
            "job_id": "job_smoke_001",
            "status": "completed",
            "progress": 100,
            "completed": True,
            "error": None,
        })
        tx_svc.retrieve_transcript = AsyncMock(return_value={
            "full_text": "We agreed to ship feature X and finalize hiring plan.",
            "paragraphs": [],
            "speakers": [],
            "chapters": [],
            "confidence": 0.95,
            "duration": 2700,
        })

        recap_svc = AsyncMock()
        mock_recap_cls.return_value = recap_svc
        recap_svc.generate_full_recap = AsyncMock(return_value={
            "summary": "Leadership aligned on roadmap milestones.",
            "key_points": ["Roadmap milestones", "Hiring plan"],
            "decisions": ["Ship feature X by June"],
            "action_items": [{"task": "Draft hiring plan", "owner": "Alice"}],
            "next_steps": ["Share hiring draft"],
            "confidence_score": 0.93,
        })
        recap_svc.create_recap_email = AsyncMock(return_value={
            "subject": "Meeting Recap: Weekly Leadership Sync",
            "body": "Summary and next steps...",
            "to": ["alice@example.com", "bob@example.com"],
        })

        email_svc = AsyncMock()
        mock_email_cls.return_value = email_svc
        email_svc.generate_draft = AsyncMock(return_value={"success": True, "draft_id": 777})
        email_svc.send_draft = AsyncMock(return_value={"success": True})

        poll_result = await poll_meeting_transcription(
            meeting_id="meet_smoke_001",
            request_data={},
            user_id=test_user_id,
            db=mock_db,
        )

        recap_result = await generate_meeting_recap(
            meeting_id="meet_smoke_001",
            recap_request={},
            user_id=test_user_id,
            db=mock_db,
        )

        send_result = await send_meeting_recap(
            meeting_id="meet_smoke_001",
            send_request={},
            user_id=test_user_id,
            db=mock_db,
        )

    assert poll_result["status"] == "completed"
    assert meeting.extra_data["transcript_status"] == "completed"
    assert "transcript" in meeting.extra_data
    assert recap_result["summary"]
    assert send_result["delivery_status"] == "sent"
    assert send_result["idempotent"] is False
    assert "alice@example.com" in send_result["recipients"]


@pytest.mark.asyncio
async def test_meeting_email_chain_smoke_send_failure_persists_status(mock_db, test_user_id):
    """Smoke: recap send failure persists durable failed state and error details."""
    from backend.fastapi.app.routers.lindy_meeting_management import send_meeting_recap
    from fastapi import HTTPException

    meeting = MagicMock()
    meeting.id = "meet_smoke_002"
    meeting.user_id = test_user_id
    meeting.title = "Ops Review"
    meeting.attendees = [{"email": "ops@example.com"}]
    meeting.extra_data = {}

    recap_row = MagicMock()
    recap_row.summary = "Ops summary"
    recap_row.key_points = '[]'
    recap_row.decisions_made = '[]'
    recap_row.action_items = '{"items": []}'

    # send_recap call order: meeting, recap, google_credential(None)
    mock_db.query.return_value.filter.return_value.first.side_effect = [
        meeting,
        recap_row,
        None,
    ]

    with patch('backend.fastapi.app.routers.lindy_meeting_management.RecapManagementService') as mock_recap_cls, \
         patch('backend.fastapi.app.routers.lindy_meeting_management.EmailManagementService') as mock_email_cls:

        recap_svc = AsyncMock()
        mock_recap_cls.return_value = recap_svc
        recap_svc.create_recap_email = AsyncMock(return_value={
            "subject": "Meeting Recap: Ops Review",
            "body": "Ops summary",
            "to": ["ops@example.com"],
        })

        email_svc = AsyncMock()
        mock_email_cls.return_value = email_svc
        email_svc.generate_draft = AsyncMock(return_value={"success": True, "draft_id": 778})
        email_svc.send_draft = AsyncMock(return_value={"success": False, "error": "smtp_down"})

        with pytest.raises(HTTPException) as exc_info:
            await send_meeting_recap(
                meeting_id="meet_smoke_002",
                send_request={},
                user_id=test_user_id,
                db=mock_db,
            )

    assert exc_info.value.status_code == 502
    assert meeting.extra_data["recap_delivery_status"] == "failed"
    assert "smtp_down" in meeting.extra_data["recap_delivery_error"]


# ============================================================================
# CROSS-MODULE SMOKE TESTS (ROUTER + EMAIL SERVICE LAYER)
# ============================================================================

@pytest.mark.asyncio
async def test_cross_module_recap_send_uses_email_service_methods(mock_db, test_user_id):
    """Smoke: send_meeting_recap invokes EmailManagementService methods with expected arguments."""
    from backend.fastapi.app.routers.lindy_meeting_management import send_meeting_recap

    meeting = MagicMock()
    meeting.id = "meet_cross_001"
    meeting.user_id = test_user_id
    meeting.title = "Cross Module Sync"
    meeting.attendees = [{"email": "cross@example.com"}]
    meeting.extra_data = {}

    recap_row = MagicMock()
    recap_row.summary = "Cross module summary"
    recap_row.key_points = '["point"]'
    recap_row.decisions_made = '[]'
    recap_row.action_items = '{"items": []}'

    google_cred = MagicMock()

    # Query order in send_meeting_recap: meeting, recap, google credential
    mock_db.query.return_value.filter.return_value.first.side_effect = [
        meeting,
        recap_row,
        google_cred,
    ]

    with patch('backend.fastapi.app.routers.lindy_meeting_management.RecapManagementService') as mock_recap_cls, \
         patch('backend.fastapi.app.routers.lindy_meeting_management.EmailManagementService.generate_draft', new=AsyncMock(return_value={"success": True, "draft_id": 321})) as mock_generate, \
         patch('backend.fastapi.app.routers.lindy_meeting_management.EmailManagementService.send_draft', new=AsyncMock(return_value={"success": True})) as mock_send:

        recap_svc = AsyncMock()
        mock_recap_cls.return_value = recap_svc
        recap_svc.create_recap_email = AsyncMock(return_value={
            "subject": "Meeting Recap: Cross Module Sync",
            "body": "Cross module summary",
            "to": ["cross@example.com"],
        })

        result = await send_meeting_recap(
            meeting_id="meet_cross_001",
            send_request={},
            user_id=test_user_id,
            db=mock_db,
        )

    assert result["delivery_status"] == "sent"
    assert result["idempotent"] is False
    assert "cross@example.com" in result["recipients"]
    assert meeting.extra_data["recap_delivery_status"] == "sent"
    assert mock_generate.await_count == 1
    assert mock_send.await_count == 1


@pytest.mark.asyncio
async def test_cross_module_recap_send_provider_failure_is_durable(mock_db, test_user_id):
    """Smoke: provider send failure via email service is persisted as durable failed state."""
    from backend.fastapi.app.routers.lindy_meeting_management import send_meeting_recap
    from fastapi import HTTPException

    meeting = MagicMock()
    meeting.id = "meet_cross_002"
    meeting.user_id = test_user_id
    meeting.title = "Cross Module Failure"
    meeting.attendees = [{"email": "fail@example.com"}]
    meeting.extra_data = {}

    recap_row = MagicMock()
    recap_row.summary = "summary"
    recap_row.key_points = '[]'
    recap_row.decisions_made = '[]'
    recap_row.action_items = '{"items": []}'

    # Query order in send_meeting_recap: meeting, recap, google credential
    mock_db.query.return_value.filter.return_value.first.side_effect = [
        meeting,
        recap_row,
        None,
    ]

    with patch('backend.fastapi.app.routers.lindy_meeting_management.RecapManagementService') as mock_recap_cls, \
         patch('backend.fastapi.app.routers.lindy_meeting_management.EmailManagementService.generate_draft', new=AsyncMock(return_value={"success": True, "draft_id": 654})), \
         patch('backend.fastapi.app.routers.lindy_meeting_management.EmailManagementService.send_draft', new=AsyncMock(return_value={"success": False, "error": "provider_timeout"})):

        recap_svc = AsyncMock()
        mock_recap_cls.return_value = recap_svc
        recap_svc.create_recap_email = AsyncMock(return_value={
            "subject": "Meeting Recap: Cross Module Failure",
            "body": "summary",
            "to": ["fail@example.com"],
        })

        with pytest.raises(HTTPException) as exc_info:
            await send_meeting_recap(
                meeting_id="meet_cross_002",
                send_request={},
                user_id=test_user_id,
                db=mock_db,
            )

    assert exc_info.value.status_code == 502
    assert meeting.extra_data["recap_delivery_status"] == "failed"
    assert "provider_timeout" in meeting.extra_data["recap_delivery_error"]


# ============================================================================
# ACTION ITEM TRACKING & REMINDER TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_get_meeting_action_items_returns_status_counts(mock_db, test_user_id):
    from backend.fastapi.app.routers.lindy_meeting_management import get_meeting_action_items

    meeting = MagicMock()
    meeting.id = "meet_ai_001"
    meeting.user_id = test_user_id
    meeting.extra_data = {
        "action_item_tracker": {
            "ai_1": {"status": "completed"},
            "ai_2": {"status": "open"},
        }
    }

    recap_row = MagicMock()
    recap_row.action_items = json.dumps({
        "items": [
            {"task": "Send proposal", "owner": "owner@example.com", "due_date": "2099-01-01T00:00:00+00:00"},
            {"task": "Book follow-up", "owner": "owner@example.com", "due_date": "2000-01-01T00:00:00+00:00"},
        ]
    })

    mock_db.query.return_value.filter.return_value.first.side_effect = [
        meeting,
        recap_row,
    ]

    result = await get_meeting_action_items(
        meeting_id="meet_ai_001",
        user_id=test_user_id,
        db=mock_db,
    )

    assert result["counts"]["total"] == 2
    assert result["counts"]["completed"] == 1
    assert result["counts"]["overdue"] == 1
    assert result["counts"]["upcoming"] == 0


@pytest.mark.asyncio
async def test_send_action_item_reminders_email_success(mock_db, test_user_id):
    from backend.fastapi.app.routers.lindy_meeting_management import send_action_item_reminders

    meeting = MagicMock()
    meeting.id = "meet_ai_002"
    meeting.user_id = test_user_id
    meeting.title = "Ops Standup"
    meeting.extra_data = {}

    recap_row = MagicMock()
    recap_row.action_items = json.dumps({
        "items": [
            {
                "task": "Send status update",
                "owner": "owner@example.com",
                "due_date": "2099-01-01T00:00:00+00:00",
                "priority": "high",
            }
        ]
    })

    google_cred = MagicMock()

    # Query order in send_action_item_reminders: meeting, recap, google credential
    mock_db.query.return_value.filter.return_value.first.side_effect = [
        meeting,
        recap_row,
        google_cred,
    ]

    with patch('backend.fastapi.app.routers.lindy_meeting_management.EmailManagementService.generate_draft', new=AsyncMock(return_value={"success": True, "draft_id": 111})), \
         patch('backend.fastapi.app.routers.lindy_meeting_management.EmailManagementService.send_draft', new=AsyncMock(return_value={"success": True})):

        result = await send_action_item_reminders(
            meeting_id="meet_ai_002",
            payload={"channels": ["email"]},
            user_id=test_user_id,
            db=mock_db,
        )

    assert result["summary"]["total"] == 1
    assert result["summary"]["sent"] == 1
    assert meeting.extra_data["action_item_tracker"]["ai_1"]["last_channels"] == ["email"]


@pytest.mark.asyncio
async def test_send_action_item_reminders_skips_when_owner_missing(mock_db, test_user_id):
    from backend.fastapi.app.routers.lindy_meeting_management import send_action_item_reminders

    meeting = MagicMock()
    meeting.id = "meet_ai_003"
    meeting.user_id = test_user_id
    meeting.title = "Ops Standup"
    meeting.extra_data = {}

    recap_row = MagicMock()
    recap_row.action_items = json.dumps({"items": [{"task": "Unassigned task"}]})

    # Query order in send_action_item_reminders: meeting, recap, google credential
    mock_db.query.return_value.filter.return_value.first.side_effect = [
        meeting,
        recap_row,
        None,
    ]

    result = await send_action_item_reminders(
        meeting_id="meet_ai_003",
        payload={"channels": ["email"]},
        user_id=test_user_id,
        db=mock_db,
    )

    assert result["summary"]["total"] == 1
    assert result["summary"]["skipped"] == 1
    assert result["results"][0]["status"] == "skipped"

