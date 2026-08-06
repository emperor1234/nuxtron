"""
Lindy.ai Email Management Models

Extends Nuxtron platform with production-grade email management:
- Email storage with AI tagging
- Email drafts (AI-generated)
- Email analytics
- OAuth credentials management
"""

from __future__ import annotations

import sys
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import ARRAY, JSON, Boolean, DateTime, Float, Index, LargeBinary, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .models import BaseTenantModel

# Ensure both import styles resolve to the same module instance.
sys.modules['app.models_lindy_email'] = sys.modules[__name__]
sys.modules['backend.fastapi.app.models_lindy_email'] = sys.modules[__name__]

JsonObject = dict[str, Any]
JsonField = JSON().with_variant(JSONB, 'postgresql')
StringArrayField = ARRAY(String).with_variant(JSON, 'sqlite')


class EmailOAuthCredential(BaseTenantModel):
    """OAuth credentials for email providers (Gmail, Outlook) - encrypted storage."""

    __tablename__ = 'email_oauth_credentials'
    __table_args__ = (
        Index('ix_email_oauth_tenant_provider', 'tenant_id', 'email_provider'),
    )

    email_provider: Mapped[str] = mapped_column(String(50), nullable=False)  # gmail, outlook
    user_email: Mapped[str] = mapped_column(String(255), nullable=False)

    # Encrypted credentials
    access_token_encrypted: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    refresh_token_encrypted: Mapped[bytes | None] = mapped_column(LargeBinary, default=None)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)

    # Scopes granted
    scopes: Mapped[list[str]] = mapped_column(StringArrayField, default=list, nullable=False)

    # Metadata
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Email(BaseTenantModel):
    """Represents an email message with AI triage metadata."""

    __tablename__ = 'emails'
    __table_args__ = (
        Index('ix_emails_tenant_from', 'tenant_id', 'from_address'),
        Index('ix_emails_tenant_status', 'tenant_id', 'status'),
        Index('ix_emails_tenant_labels', 'tenant_id'),
    )

    # Email identifiers
    message_id: Mapped[str] = mapped_column(String(512), unique=True, nullable=False)
    thread_id: Mapped[str | None] = mapped_column(String(512), default=None, index=True)
    
    # Message content
    from_address: Mapped[str] = mapped_column(String(255), nullable=False)
    to_addresses: Mapped[list[str]] = mapped_column(StringArrayField, default=list)
    cc_addresses: Mapped[list[str]] = mapped_column(StringArrayField, default=list)
    bcc_addresses: Mapped[list[str]] = mapped_column(StringArrayField, default=list)
    
    subject: Mapped[str | None] = mapped_column(String(1024), default=None)
    body: Mapped[str | None] = mapped_column(Text, default=None)  # Plain text
    body_html: Mapped[str | None] = mapped_column(Text, default=None)  # HTML
    
    # Labels & Triage
    provider_labels: Mapped[list[str]] = mapped_column(StringArrayField, default=list)  # Gmail labels
    ai_labels: Mapped[list[str]] = mapped_column(StringArrayField, default=list)  # AI-generated labels
    
    # Priority (AI-detected)
    priority: Mapped[str] = mapped_column(String(20), default='normal')  # low, normal, high, urgent
    
    # Status
    status: Mapped[str] = mapped_column(String(20), default='unread')  # unread, read, archived, spam, deleted
    is_starred: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Attachments
    has_attachments: Mapped[bool] = mapped_column(Boolean, default=False)
    attachment_count: Mapped[int] = mapped_column(default=0)
    attachments_metadata: Mapped[JsonObject] = mapped_column(JsonField, default=dict)
    
    # Timestamps
    email_received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    
    # AI Analysis Metadata
    ai_confidence: Mapped[float] = mapped_column(Float, default=0.0)  # Confidence in AI labels
    sentiment: Mapped[str | None] = mapped_column(String(50), default=None)  # positive, negative, neutral
    requires_response: Mapped[bool] = mapped_column(Boolean, default=False)
    is_phishing: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Full extra data
    extra_data: Mapped[JsonObject] = mapped_column(JsonField, default=dict)


class EmailDraft(BaseTenantModel):
    """AI-generated email drafts for user review & sending."""

    __tablename__ = 'email_drafts'
    __table_args__ = (
        Index('ix_email_drafts_tenant_status', 'tenant_id', 'status'),
    )

    # Link to original email (for reply drafts)
    original_email_id: Mapped[int | None] = mapped_column(default=None)
    
    # Draft content
    to_addresses: Mapped[list[str]] = mapped_column(StringArrayField, default=list)
    cc_addresses: Mapped[list[str]] = mapped_column(StringArrayField, default=list)
    subject: Mapped[str] = mapped_column(String(1024), nullable=False)
    draft_text: Mapped[str] = mapped_column(Text, nullable=False)
    draft_html: Mapped[str | None] = mapped_column(Text, default=None)
    
    # AI Metadata
    tone: Mapped[str] = mapped_column(String(50), default='professional')  # professional, casual, assertive, friendly
    ai_confidence: Mapped[float] = mapped_column(Float, default=0.95)
    model_used: Mapped[str] = mapped_column(String(100), default='gpt-4')  # gpt-4, claude-3-opus
    prompt_version: Mapped[str] = mapped_column(String(50), default='1.0')
    
    # Status
    status: Mapped[str] = mapped_column(String(50), default='draft')  # draft, regenerating, user_edited, ready, sent, rejected
    
    # User interaction
    user_edited: Mapped[bool] = mapped_column(Boolean, default=False)
    edit_count: Mapped[int] = mapped_column(default=0)
    
    # Sending
    sent: Mapped[bool] = mapped_column(Boolean, default=False)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    
    # Extra data
    extra_data: Mapped[JsonObject] = mapped_column(JsonField, default=dict)


class EmailTemplate(BaseTenantModel):
    """Reusable email templates for common responses."""

    __tablename__ = 'email_templates'

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, default=None)
    
    subject_template: Mapped[str] = mapped_column(String(1024), nullable=False)
    body_template: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Variables that can be substituted
    variables: Mapped[list[str]] = mapped_column(StringArrayField, default=list)
    
    # Usage tracking
    usage_count: Mapped[int] = mapped_column(default=0)
    is_ai_generated: Mapped[bool] = mapped_column(Boolean, default=False)


class EmailAnalytics(BaseTenantModel):
    """Email engagement analytics and metrics."""

    __tablename__ = 'email_analytics'
    __table_args__ = (
        Index('ix_email_analytics_tenant_date', 'tenant_id', 'date'),
    )

    # Tracking
    date: Mapped[str] = mapped_column(String(10), nullable=False)  # YYYY-MM-DD
    
    # Metrics
    total_emails_received: Mapped[int] = mapped_column(default=0)
    total_emails_sent: Mapped[int] = mapped_column(default=0)
    emails_with_ai_drafts: Mapped[int] = mapped_column(default=0)
    drafts_accepted: Mapped[int] = mapped_column(default=0)
    drafts_rejected: Mapped[int] = mapped_column(default=0)
    
    # Engagement
    avg_response_time_hours: Mapped[float] = mapped_column(default=0.0)
    total_time_saved_minutes: Mapped[float] = mapped_column(default=0.0)
    
    # AI Performance
    ai_label_accuracy: Mapped[float] = mapped_column(default=0.0)
    ai_priority_detection_accuracy: Mapped[float] = mapped_column(default=0.0)
    avg_draft_quality_score: Mapped[float] = mapped_column(default=0.0)
    
    extra_data: Mapped[JsonObject] = mapped_column(JsonField, default=dict)


class EmailSequence(BaseTenantModel):
    """Email automation sequences (follow-up emails, campaigns)."""

    __tablename__ = 'email_sequences'

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, default=None)

    # Sequence config
    type: Mapped[str] = mapped_column(String(50), nullable=False)  # follow_up, nurture, onboarding
    steps: Mapped[JsonObject] = mapped_column(JsonField, nullable=False)  # Array of sequence steps

    # Execution
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    total_emails_sent: Mapped[int] = mapped_column(default=0)


class EmailConsentLog(BaseTenantModel):
    """Tracks user consent for email communications (GDPR compliance)."""

    __tablename__ = 'email_consent_logs'

    email_address: Mapped[str] = mapped_column(String(255), nullable=False)

    # Consent types
    marketing_emails: Mapped[bool] = mapped_column(Boolean, default=False)
    transactional_emails: Mapped[bool] = mapped_column(Boolean, default=True)
    ai_processing: Mapped[bool] = mapped_column(Boolean, default=False)

    # Audit trail
    consented_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    ip_address: Mapped[str | None] = mapped_column(String(45), default=None)
    user_agent: Mapped[str | None] = mapped_column(String(1024), default=None)

    extra_data: Mapped[JsonObject] = mapped_column(JsonField, default=dict)
