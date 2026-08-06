"""
Lindy.ai Meeting Management Models

Production-grade meeting management with:
- Calendar integration (Google, Outlook)
- Smart scheduling algorithm
- Meeting recording & transcription
- Meeting notes & recap generation
"""

from __future__ import annotations

import sys
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import ARRAY, JSON, Boolean, DateTime, Float, Index, Integer, LargeBinary, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, synonym

from .models import BaseTenantModel

# Ensure both import styles resolve to the same module instance.
sys.modules['app.models_lindy_meeting'] = sys.modules[__name__]
sys.modules['backend.fastapi.app.models_lindy_meeting'] = sys.modules[__name__]

JsonObject = dict[str, Any]
JsonField = JSON().with_variant(JSONB, 'postgresql')
StringArrayField = ARRAY(String).with_variant(JSON, 'sqlite')


class CalendarOAuthCredential(BaseTenantModel):
    """OAuth credentials for calendar providers."""

    __tablename__ = 'calendar_oauth_credentials'
    __table_args__ = (
        Index('ix_calendar_oauth_tenant_provider', 'tenant_id', 'provider'),
    )

    user_id = synonym('tenant_id')
    provider: Mapped[str] = mapped_column(String(50), nullable=False)  # google, outlook
    user_email: Mapped[str] = mapped_column(String(255), nullable=False)

    # Encrypted credentials
    access_token_encrypted: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    refresh_token_encrypted: Mapped[bytes | None] = mapped_column(LargeBinary, default=None)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)

    # Scopes
    scopes: Mapped[list[str]] = mapped_column(StringArrayField, default=list)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Metadata
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)


class CalendarEvent(BaseTenantModel):
    """Represents a calendar event from integrated calendars."""

    __tablename__ = 'calendar_events'
    __table_args__ = (
        Index('ix_calendar_events_tenant_datetime', 'tenant_id', 'start_time'),
        Index('ix_calendar_events_tenant_provider', 'tenant_id', 'provider'),
    )

    user_id = synonym('tenant_id')

    # Event identifiers
    event_id: Mapped[str] = mapped_column(String(512), unique=True, nullable=False)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)  # google, outlook
    calendar_id: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # Event details
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, default=None)
    location: Mapped[str | None] = mapped_column(String(500), default=None)
    
    # Time info
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    timezone: Mapped[str] = mapped_column(String(50), default='UTC')
    
    # Attendees
    organizer_email: Mapped[str] = mapped_column(String(255), nullable=False)
    attendee_emails: Mapped[list[str]] = mapped_column(StringArrayField, default=list)
    
    # Status
    status: Mapped[str] = mapped_column(String(50), default='tentative')  # tentative, confirmed, cancelled
    is_recurring: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Extra data
    extra_data: Mapped[JsonObject] = mapped_column(JsonField, default=dict)


class Meeting(BaseTenantModel):
    """Represents a meeting with Lindy-specific metadata."""

    __tablename__ = 'meetings'
    __table_args__ = (
        Index('ix_meetings_tenant_datetime', 'tenant_id', 'scheduled_start'),
        Index('ix_meetings_tenant_status', 'tenant_id', 'status'),
    )

    user_id = synonym('tenant_id')

    # Link to calendar event
    calendar_event_id: Mapped[int | None] = mapped_column(default=None)
    
    # Meeting details
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, default=None)
    location: Mapped[str | None] = mapped_column(String(500), default=None)
    
    # Scheduling
    scheduled_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    scheduled_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    scheduled_time = synonym('scheduled_start')
    start_time = synonym('scheduled_start')
    end_time = synonym('scheduled_end')
    
    # Actual times
    actual_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    actual_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    
    # Attendees
    organizer_id: Mapped[str] = mapped_column(String(255), nullable=False)
    attendees: Mapped[JsonObject] = mapped_column(JsonField, default=dict)  # {email: status}
    duration_minutes: Mapped[int | None] = mapped_column(Integer, default=60)
    timezone: Mapped[str] = mapped_column(String(50), default='UTC')
    
    # Status
    status: Mapped[str] = mapped_column(String(50), default='scheduled')  # scheduled, in_progress, completed, cancelled
    calendar_provider: Mapped[str | None] = mapped_column(String(50), default=None)
    calendar_type = synonym('calendar_provider')
    event_id: Mapped[str | None] = mapped_column(String(512), default=None)
    external_event_id = synonym('event_id')
    conference_url: Mapped[str | None] = mapped_column(String(1024), default=None)
    confidence_score: Mapped[float | None] = mapped_column(Float, default=None)
    
    # Lindy AI Features
    ai_prep_generated: Mapped[bool] = mapped_column(Boolean, default=False)
    prep_notes: Mapped[str | None] = mapped_column(Text, default=None)
    
    meeting_recording_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    recording_url: Mapped[str | None] = mapped_column(String(1024), default=None)
    recording_provider: Mapped[str | None] = mapped_column(String(50), default=None)  # google_meet, teams, etc.
    
    # Transcription
    transcript: Mapped[str | None] = mapped_column(Text, default=None)
    transcript_timestamp_url: Mapped[str | None] = mapped_column(String(1024), default=None)
    
    # AI Analysis
    ai_summary: Mapped[str | None] = mapped_column(Text, default=None)
    key_decisions: Mapped[list[str]] = mapped_column(StringArrayField, default=list)
    action_items_extracted: Mapped[list[str]] = mapped_column(StringArrayField, default=list)
    
    # Extra data
    extra_data: Mapped[JsonObject] = mapped_column(JsonField, default=dict)


class MeetingPrep(BaseTenantModel):
    """AI-generated meeting prep notes."""

    __tablename__ = 'meeting_preps'

    user_id = synonym('tenant_id')
    meeting_id: Mapped[int] = mapped_column(default=None, nullable=True)
    
    # Prep content
    briefing: Mapped[str] = mapped_column(Text, nullable=False)  # Main briefing
    attendee_profiles: Mapped[JsonObject] = mapped_column(JsonField, default=dict)
    talking_points: Mapped[list[str]] = mapped_column(StringArrayField, default=list)
    potential_questions: Mapped[list[str]] = mapped_column(StringArrayField, default=list)
    agenda: Mapped[str | None] = mapped_column(Text, default=None)
    
    # Metadata
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    confidence_score: Mapped[float] = mapped_column(Float, default=0.85)


class MeetingRecap(BaseTenantModel):
    """Meeting recap and follow-up automation."""

    __tablename__ = 'meeting_recaps'

    user_id = synonym('tenant_id')
    meeting_id: Mapped[int] = mapped_column(nullable=False)
    
    # Summary
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    key_points: Mapped[list[str]] = mapped_column(StringArrayField, default=list)
    decisions_made: Mapped[list[str]] = mapped_column(StringArrayField, default=list)
    decisions = synonym('decisions_made')
    
    # Action items
    action_items: Mapped[JsonObject] = mapped_column(JsonField, default=dict)  # {item: {owner, due_date}}
    
    # Follow-up
    follow_up_emails_sent: Mapped[bool] = mapped_column(Boolean, default=False)
    follow_up_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)


class SchedulingPreference(BaseTenantModel):
    """User scheduling preferences for smart meeting scheduling."""

    __tablename__ = 'scheduling_preferences'

    user_id = synonym('tenant_id')

    # Working hours
    work_start_hour: Mapped[int] = mapped_column(default=9)
    work_end_hour: Mapped[int] = mapped_column(default=17)
    working_hours_start = synonym('work_start_hour')
    working_hours_end = synonym('work_end_hour')
    
    # Preferences
    preferred_meeting_duration_minutes: Mapped[int] = mapped_column(default=30)
    min_buffer_minutes: Mapped[int] = mapped_column(default=15)  # Between meetings
    buffer_time_minutes = synonym('min_buffer_minutes')
    max_meetings_per_day: Mapped[int] = mapped_column(default=8)
    
    # Calendar preferences
    do_not_schedule_days: Mapped[list[str]] = mapped_column(StringArrayField, default=list)  # Mon-Sun
    do_not_schedule_times: Mapped[JsonObject] = mapped_column(JsonField, default=dict)
    
    # Smart features
    auto_reschedule_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    lunch_block_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    lunch_start_hour: Mapped[int] = mapped_column(default=12)
    lunch_duration_hours: Mapped[int] = mapped_column(default=1)
    lunch_end_hour: Mapped[int | None] = mapped_column(Integer, default=13)
    timezone: Mapped[str] = mapped_column(String(50), default='UTC')


class MeetingTemplate(BaseTenantModel):
    """Reusable meeting templates."""

    __tablename__ = 'meeting_templates'

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, default=None)
    
    # Template details
    default_title: Mapped[str] = mapped_column(String(500), nullable=False)
    default_description: Mapped[str | None] = mapped_column(Text, default=None)
    default_duration_minutes: Mapped[int] = mapped_column(default=30)
    
    # Attendees (templates)
    default_attendee_patterns: Mapped[list[str]] = mapped_column(StringArrayField, default=list)
    
    # Agenda
    suggested_agenda: Mapped[str | None] = mapped_column(Text, default=None)
    
    usage_count: Mapped[int] = mapped_column(default=0)


class MeetingConsentLog(BaseTenantModel):
    """Recording and AI processing consent logging (GDPR)."""

    __tablename__ = 'meeting_consent_logs'

    participant_email: Mapped[str] = mapped_column(String(255), nullable=False)

    # Consent types
    recording_consent: Mapped[bool] = mapped_column(Boolean, default=False)
    transcript_consent: Mapped[bool] = mapped_column(Boolean, default=False)
    ai_processing_consent: Mapped[bool] = mapped_column(Boolean, default=False)

    # Audit
    consented_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    ip_address: Mapped[str | None] = mapped_column(String(45), default=None)
