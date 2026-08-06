"""
Database migration for complete social media management platform.
Creates tables for publishing, analytics, engagement, team collaboration.
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op  # type: ignore[import-not-found]


def upgrade():
    """Create all tables for social media platform"""
    
    # Social Media Content table
    op.create_table(
        'social_media_content',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('tenant_id', sa.String(36), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('base_caption', sa.Text, nullable=True),
        sa.Column('media_assets', postgresql.JSON, nullable=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='draft'),
        sa.Column('content_type', sa.String(50), nullable=False),
        sa.Column('platform_variations', postgresql.JSON, nullable=True),
        sa.Column('scheduled_for', sa.DateTime, nullable=True),
        sa.Column('published_at', sa.DateTime, nullable=True),
        sa.Column('expires_at', sa.DateTime, nullable=True),
        sa.Column('requires_approval', sa.Boolean, server_default='false'),
        sa.Column('approved_by', sa.String(36), nullable=True),
        sa.Column('approved_at', sa.DateTime, nullable=True),
        sa.Column('approval_notes', sa.Text, nullable=True),
        sa.Column('engagement_metrics', postgresql.JSON, nullable=True),
        sa.Column('platform_post_ids', postgresql.JSON, nullable=True),
        sa.Column('error_messages', postgresql.JSON, nullable=True),
        sa.Column('created_by', sa.String(36), nullable=False),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
    )
    
    op.create_index('idx_social_content_tenant', 'social_media_content', ['tenant_id'])
    op.create_index('idx_social_content_status', 'social_media_content', ['status'])
    op.create_index('idx_social_content_scheduled', 'social_media_content', ['scheduled_for'])
    
    # Social Analytics table
    op.create_table(
        'social_analytics',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('tenant_id', sa.String(36), nullable=False),
        sa.Column('platform', sa.String(50), nullable=False),
        sa.Column('post_id', sa.String(255), nullable=False),
        sa.Column('impressions', sa.Integer, server_default='0'),
        sa.Column('reach', sa.Integer, server_default='0'),
        sa.Column('engagement_count', sa.Integer, server_default='0'),
        sa.Column('engagement_rate', sa.Float, server_default='0.0'),
        sa.Column('likes', sa.Integer, server_default='0'),
        sa.Column('comments', sa.Integer, server_default='0'),
        sa.Column('shares', sa.Integer, server_default='0'),
        sa.Column('reposts', sa.Integer, server_default='0'),
        sa.Column('clicks', sa.Integer, server_default='0'),
        sa.Column('conversions', sa.Integer, server_default='0'),
        sa.Column('video_views', sa.Integer, server_default='0'),
        sa.Column('video_watch_time_seconds', sa.Integer, server_default='0'),
        sa.Column('average_watch_duration', sa.Float, server_default='0.0'),
        sa.Column('audience_demographics', postgresql.JSON, nullable=True),
        sa.Column('top_audience_locations', postgresql.JSON, nullable=True),
        sa.Column('device_breakdown', postgresql.JSON, nullable=True),
        sa.Column('sentiment_score', sa.Float, nullable=True),
        sa.Column('sentiment_breakdown', postgresql.JSON, nullable=True),
        sa.Column('collected_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('platform_retrieved_at', sa.DateTime, nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
    )
    
    op.create_index('idx_tenant_platform_collected', 'social_analytics', ['tenant_id', 'platform', 'collected_at'])
    op.create_index('idx_post_analytics', 'social_analytics', ['post_id', 'platform'])
    
    # Audience Metrics table
    op.create_table(
        'audience_metrics',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('tenant_id', sa.String(36), nullable=False),
        sa.Column('platform', sa.String(50), nullable=False),
        sa.Column('total_followers', sa.Integer, server_default='0'),
        sa.Column('follower_growth_daily', sa.Integer, server_default='0'),
        sa.Column('follower_growth_weekly', sa.Integer, server_default='0'),
        sa.Column('follower_growth_monthly', sa.Integer, server_default='0'),
        sa.Column('age_breakdown', postgresql.JSON, nullable=True),
        sa.Column('gender_breakdown', postgresql.JSON, nullable=True),
        sa.Column('top_locations', postgresql.JSON, nullable=True),
        sa.Column('top_interests', postgresql.JSON, nullable=True),
        sa.Column('most_active_times', postgresql.JSON, nullable=True),
        sa.Column('most_active_devices', postgresql.JSON, nullable=True),
        sa.Column('collected_at', sa.DateTime, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
    )
    
    op.create_index('idx_tenant_audience_metrics', 'audience_metrics', ['tenant_id', 'platform'])
    
    # Social Engagement (comments, mentions) table
    op.create_table(
        'social_engagement',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('tenant_id', sa.String(36), nullable=False),
        sa.Column('platform', sa.String(50), nullable=False),
        sa.Column('post_id', sa.String(255), nullable=False),
        sa.Column('engagement_type', sa.String(50), nullable=False),  # comment, mention, like, share
        sa.Column('author_id', sa.String(255), nullable=False),
        sa.Column('author_name', sa.String(255), nullable=True),
        sa.Column('author_handle', sa.String(255), nullable=True),
        sa.Column('content', sa.Text, nullable=False),
        sa.Column('sentiment', sa.String(20), nullable=True),  # positive, negative, neutral
        sa.Column('sentiment_score', sa.Float, nullable=True),
        sa.Column('is_from_follower', sa.Boolean, server_default='false'),
        sa.Column('parent_engagement_id', sa.String(36), nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('platform_created_at', sa.DateTime, nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
    )
    
    op.create_index('idx_engagement_tenant', 'social_engagement', ['tenant_id'])
    op.create_index('idx_engagement_post', 'social_engagement', ['post_id', 'platform'])
    op.create_index('idx_engagement_created', 'social_engagement', ['created_at'])
    
    # DM Automation Templates
    op.create_table(
        'dm_automation_templates',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('tenant_id', sa.String(36), nullable=False),
        sa.Column('platform', sa.String(50), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('template_text', sa.Text, nullable=False),
        sa.Column('intent_keywords', postgresql.JSON, nullable=False),  # List[str]
        sa.Column('enabled', sa.Boolean, server_default='true'),
        sa.Column('auto_respond', sa.Boolean, server_default='true'),
        sa.Column('require_human_approval', sa.Boolean, server_default='false'),
        sa.Column('response_delay_seconds', sa.Integer, nullable=True),
        sa.Column('created_by', sa.String(36), nullable=False),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
    )
    
    op.create_index('idx_dm_templates_tenant', 'dm_automation_templates', ['tenant_id', 'platform'])
    
    # Social Listening Keywords
    op.create_table(
        'social_listening_keywords',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('tenant_id', sa.String(36), nullable=False),
        sa.Column('keyword', sa.String(255), nullable=False),
        sa.Column('platforms', postgresql.JSON, nullable=False),  # List[str]
        sa.Column('is_active', sa.Boolean, server_default='true'),
        sa.Column('alert_on_mention', sa.Boolean, server_default='true'),
        sa.Column('alert_on_negative_sentiment', sa.Boolean, server_default='true'),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
    )
    
    op.create_index('idx_listening_keywords_tenant', 'social_listening_keywords', ['tenant_id', 'keyword'])
    
    # Social Listening Results
    op.create_table(
        'social_listening_results',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('tenant_id', sa.String(36), nullable=False),
        sa.Column('keyword', sa.String(255), nullable=False),
        sa.Column('platform', sa.String(50), nullable=False),
        sa.Column('post_id', sa.String(255), nullable=False),
        sa.Column('author_id', sa.String(255), nullable=False),
        sa.Column('author_name', sa.String(255), nullable=True),
        sa.Column('content', sa.Text, nullable=False),
        sa.Column('url', sa.String(1024), nullable=True),
        sa.Column('sentiment', sa.String(20), nullable=True),
        sa.Column('sentiment_score', sa.Float, nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('platform_created_at', sa.DateTime, nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
    )
    
    op.create_index('idx_listening_results_tenant', 'social_listening_results', ['tenant_id', 'created_at'])
    
    # Reviews
    op.create_table(
        'social_reviews',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('tenant_id', sa.String(36), nullable=False),
        sa.Column('platform', sa.String(50), nullable=False),  # google, yelp, trustpilot, tripadvsor
        sa.Column('external_id', sa.String(255), nullable=False),
        sa.Column('author_name', sa.String(255), nullable=True),
        sa.Column('rating', sa.Integer, nullable=False),  # 1-5 stars
        sa.Column('title', sa.String(255), nullable=True),
        sa.Column('content', sa.Text, nullable=False),
        sa.Column('has_response', sa.Boolean, server_default='false'),
        sa.Column('response_text', sa.Text, nullable=True),
        sa.Column('response_author', sa.String(36), nullable=True),
        sa.Column('sentiment', sa.String(20), nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('platform_created_at', sa.DateTime, nullable=True),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
    )
    
    op.create_index('idx_reviews_tenant', 'social_reviews', ['tenant_id', 'platform'])
    op.create_index('idx_reviews_rating', 'social_reviews', ['rating'])
    
    # Content Calendar events
    op.create_table(
        'content_calendar_events',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('tenant_id', sa.String(36), nullable=False),
        sa.Column('content_id', sa.String(36), nullable=False),
        sa.Column('event_date', sa.Date, nullable=False),
        sa.Column('event_time', sa.Time, nullable=True),
        sa.Column('platforms', postgresql.JSON, nullable=False),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.ForeignKeyConstraint(['content_id'], ['social_media_content.id']),
    )
    
    op.create_index('idx_calendar_tenant_date', 'content_calendar_events', ['tenant_id', 'event_date'])
    
    # Vendor Credentials (encrypted)
    op.create_table(
        'vendor_credentials',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('tenant_id', sa.String(36), nullable=False),
        sa.Column('vendor_id', sa.String(100), nullable=False),
        sa.Column('platform', sa.String(50), nullable=True),
        sa.Column('api_key_encrypted', sa.Text, nullable=False),
        sa.Column('api_secret_encrypted', sa.Text, nullable=True),
        sa.Column('access_token_encrypted', sa.Text, nullable=True),
        sa.Column('refresh_token_encrypted', sa.Text, nullable=True),
        sa.Column('additional_config', postgresql.JSON, nullable=True),
        sa.Column('expires_at', sa.DateTime, nullable=True),
        sa.Column('is_active', sa.Boolean, server_default='true'),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
    )
    
    op.create_index('idx_credentials_tenant_vendor', 'vendor_credentials', ['tenant_id', 'vendor_id'])


def downgrade():
    """Drop all tables created in upgrade"""
    op.drop_table('vendor_credentials')
    op.drop_table('content_calendar_events')
    op.drop_table('social_reviews')
    op.drop_table('social_listening_results')
    op.drop_table('social_listening_keywords')
    op.drop_table('dm_automation_templates')
    op.drop_table('social_engagement')
    op.drop_table('audience_metrics')
    op.drop_table('social_analytics')
    op.drop_table('social_media_content')
