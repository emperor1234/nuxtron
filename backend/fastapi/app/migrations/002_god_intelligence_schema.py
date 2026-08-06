"""
God Intelligence — Complete Production Schema Migration
Supabase PostgreSQL tables with proper indexing, RLS, and constraints
"""

MIGRATION_SQL = """
-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ════════════════════════════════════════════════════════════
-- 1. INTEL TARGETS — Competitive entities being tracked
-- ════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS intel_targets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id UUID NOT NULL,
    name TEXT NOT NULL,
    domain TEXT,
    twitter_handle TEXT,
    instagram_handle TEXT,
    facebook_page TEXT,
    reddit_username TEXT,
    youtube_channel_id TEXT,
    category TEXT DEFAULT 'competitor' CHECK (category IN ('competitor', 'partner', 'customer', 'reference')),
    priority INT DEFAULT 3 CHECK (priority BETWEEN 1 AND 5),
    track_website BOOLEAN DEFAULT true,
    track_ads BOOLEAN DEFAULT true,
    track_social BOOLEAN DEFAULT true,
    track_news BOOLEAN DEFAULT true,
    is_active BOOLEAN DEFAULT true,
    last_full_scan_at TIMESTAMPTZ,
    next_scan_scheduled_at TIMESTAMPTZ,
    scan_frequency_hours INT DEFAULT 6,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_intel_targets_org ON intel_targets(org_id, is_active);
CREATE INDEX idx_intel_targets_active ON intel_targets(is_active, updated_at DESC);
CREATE UNIQUE INDEX idx_intel_targets_unique ON intel_targets(org_id, name);

-- ════════════════════════════════════════════════════════════
-- 2. INTEL SOCIAL POSTS — Competitor social content analysis
-- ════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS intel_social_posts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id UUID NOT NULL,
    target_id UUID NOT NULL REFERENCES intel_targets(id) ON DELETE CASCADE,
    platform TEXT NOT NULL CHECK (platform IN ('twitter', 'reddit', 'instagram', 'linkedin', 'tiktok', 'youtube')),
    platform_post_id TEXT NOT NULL,
    post_url TEXT NOT NULL,
    author_handle TEXT NOT NULL,
    content TEXT,
    content_type TEXT DEFAULT 'text' CHECK (content_type IN ('text', 'image', 'video', 'carousel', 'link')),
    likes INT DEFAULT 0,
    comments INT DEFAULT 0,
    shares INT DEFAULT 0,
    views INT DEFAULT 0,
    posted_at TIMESTAMPTZ NOT NULL,
    scraped_at TIMESTAMPTZ DEFAULT NOW(),
    engagement_rate FLOAT DEFAULT 0.0 CHECK (engagement_rate >= 0 AND engagement_rate <= 100),
    engagement_velocity FLOAT DEFAULT 0.0,
    virality_coefficient FLOAT DEFAULT 0.0 CHECK (virality_coefficient >= 0 AND virality_coefficient <= 100),
    content_resonance_index FLOAT DEFAULT 0.0 CHECK (content_resonance_index >= 0 AND content_resonance_index <= 100),
    estimated_organic_reach INT DEFAULT 0,
    trend_phase TEXT DEFAULT 'stable' CHECK (trend_phase IN ('pre_emerging', 'emerging', 'growing', 'peak', 'declining', 'fading', 'dead', 'stable')),
    trend_score FLOAT DEFAULT 0.0,
    content_embedding vector(1536),
    is_viral_flagged BOOLEAN DEFAULT false,
    is_archived BOOLEAN DEFAULT false,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(platform, platform_post_id)
);

CREATE INDEX idx_intel_posts_org_cri ON intel_social_posts(org_id, content_resonance_index DESC);
CREATE INDEX idx_intel_posts_target_platform ON intel_social_posts(target_id, platform, posted_at DESC);
CREATE INDEX idx_intel_posts_viral ON intel_social_posts(org_id, is_viral_flagged, virality_coefficient DESC) WHERE is_viral_flagged = true;
CREATE INDEX idx_intel_posts_trend_phase ON intel_social_posts(org_id, trend_phase, trend_score DESC);
CREATE INDEX idx_intel_posts_posted_at ON intel_social_posts(org_id, posted_at DESC);
CREATE INDEX idx_intel_posts_embed ON intel_social_posts USING ivfflat (content_embedding vector_cosine_ops) WITH (lists = 100);

-- ════════════════════════════════════════════════════════════
-- 3. POST METRICS HISTORY — Time-series engagement tracking
-- ════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS intel_post_metrics_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    post_id UUID NOT NULL REFERENCES intel_social_posts(id) ON DELETE CASCADE,
    org_id UUID NOT NULL,
    likes INT NOT NULL,
    comments INT NOT NULL,
    shares INT NOT NULL,
    views INT NOT NULL,
    engagement_rate FLOAT NOT NULL,
    velocity FLOAT NOT NULL,
    snapshot_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_metrics_history_post_time ON intel_post_metrics_history(post_id, snapshot_at DESC);
CREATE INDEX idx_metrics_history_org_time ON intel_post_metrics_history(org_id, snapshot_at DESC);

-- ════════════════════════════════════════════════════════════
-- 4. INTEL ADS — Competitor ad spend & creative analysis
-- ════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS intel_ads (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id UUID NOT NULL,
    target_id UUID NOT NULL REFERENCES intel_targets(id) ON DELETE CASCADE,
    ad_id TEXT NOT NULL,
    platform TEXT NOT NULL CHECK (platform IN ('facebook', 'instagram', 'tiktok', 'google', 'linkedin')),
    headline TEXT,
    primary_text TEXT,
    secondary_text TEXT,
    call_to_action TEXT,
    landing_url TEXT,
    platforms TEXT[],
    estimated_daily_spend_min INT,
    estimated_daily_spend_max INT,
    estimated_total_spend_min INT,
    estimated_total_spend_max INT,
    estimated_impressions_min INT,
    estimated_impressions_max INT,
    demographic_distribution JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT true,
    first_seen_at TIMESTAMPTZ DEFAULT NOW(),
    last_seen_at TIMESTAMPTZ DEFAULT NOW(),
    creative_variation_count INT DEFAULT 1,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(platform, ad_id)
);

CREATE INDEX idx_intel_ads_org_active ON intel_ads(org_id, is_active, updated_at DESC);
CREATE INDEX idx_intel_ads_target ON intel_ads(target_id, platform, estimated_total_spend_max DESC);
CREATE INDEX idx_intel_ads_spend ON intel_ads(org_id, estimated_daily_spend_max DESC) WHERE is_active = true;

-- ════════════════════════════════════════════════════════════
-- 5. INTEL WEBSITE SNAPSHOTS — Competitive website changes
-- ════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS intel_website_snapshots (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id UUID NOT NULL,
    target_id UUID NOT NULL REFERENCES intel_targets(id) ON DELETE CASCADE,
    domain TEXT NOT NULL,
    pages_snapshot JSONB NOT NULL,
    content_hash TEXT,
    technologies JSONB DEFAULT '{}',
    metadata_changes JSONB DEFAULT '{}',
    has_changes BOOLEAN DEFAULT false,
    diff_summary TEXT,
    snapshot_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_website_snapshots_target ON intel_website_snapshots(target_id, snapshot_at DESC);

-- ════════════════════════════════════════════════════════════
-- 6. INTEL SEO RANKINGS — Keyword position tracking
-- ════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS intel_seo_rankings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id UUID NOT NULL,
    target_id UUID NOT NULL REFERENCES intel_targets(id) ON DELETE CASCADE,
    keyword TEXT NOT NULL,
    search_volume INT,
    current_position INT,
    url TEXT,
    snippet TEXT,
    recorded_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_seo_rankings_target_keyword ON intel_seo_rankings(target_id, keyword, recorded_at DESC);

-- ════════════════════════════════════════════════════════════
-- 7. INTEL TRENDS — Trend detection with ROI scoring
-- ════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS intel_trends (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id UUID NOT NULL,
    keyword TEXT NOT NULL,
    lifecycle_phase TEXT NOT NULL DEFAULT 'stable' CHECK (lifecycle_phase IN ('pre_emerging', 'emerging', 'growing', 'peak', 'declining', 'fading', 'dead')),
    current_volume INT DEFAULT 0,
    volume_24h_change_pct FLOAT DEFAULT 0.0,
    volume_7d_change_pct FLOAT DEFAULT 0.0,
    momentum_score FLOAT DEFAULT 50.0,
    roi_opportunity_score FLOAT DEFAULT 50.0 CHECK (roi_opportunity_score >= 0 AND roi_opportunity_score <= 100),
    action_urgency TEXT DEFAULT 'low' CHECK (action_urgency IN ('immediate', 'this_week', 'this_month', 'low')),
    platform_breakdown JSONB DEFAULT '{}',
    related_keywords TEXT[],
    predicted_peak_date TIMESTAMPTZ,
    content_recommendations JSONB DEFAULT '{}',
    is_tracked BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(org_id, keyword)
);

CREATE INDEX idx_trends_opportunity ON intel_trends(org_id, roi_opportunity_score DESC);
CREATE INDEX idx_trends_phase ON intel_trends(org_id, lifecycle_phase, roi_opportunity_score DESC);
CREATE INDEX idx_trends_urgency ON intel_trends(org_id, action_urgency, updated_at DESC);

-- ════════════════════════════════════════════════════════════
-- 8. INTEL VIRAL REGISTRY — Viral content detection log
-- ════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS intel_viral_registry (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id UUID NOT NULL,
    post_id UUID NOT NULL REFERENCES intel_social_posts(id) ON DELETE CASCADE,
    target_id UUID NOT NULL REFERENCES intel_targets(id) ON DELETE CASCADE,
    viral_score FLOAT NOT NULL,
    predicted_reach_magnitude INT,
    reached_virality_at TIMESTAMPTZ,
    peak_engagement_rate FLOAT,
    detected_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_viral_registry_org ON intel_viral_registry(org_id, viral_score DESC);

-- ════════════════════════════════════════════════════════════
-- 9. INTEL ROI PREDICTIONS — ML-based content ROI projections
-- ════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS intel_roi_predictions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id UUID NOT NULL,
    prediction_type TEXT NOT NULL CHECK (prediction_type IN ('post', 'campaign', 'trend')),
    input_data JSONB NOT NULL,
    predicted_reach_p25 INT,
    predicted_reach_p50 INT,
    predicted_reach_p75 INT,
    predicted_engagement_rate_p50 FLOAT,
    predicted_leads_p25 INT,
    predicted_leads_p50 INT,
    predicted_leads_p75 INT,
    predicted_revenue_usd_p25 FLOAT,
    predicted_revenue_usd_p50 FLOAT,
    predicted_revenue_usd_p75 FLOAT,
    predicted_roas FLOAT,
    confidence_score FLOAT,
    improvements JSONB DEFAULT '[]',
    actual_results JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_roi_predictions_org ON intel_roi_predictions(org_id, created_at DESC);

-- ════════════════════════════════════════════════════════════
-- 10. INTEL REPORTS — Intelligence synthesis & summaries
-- ════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS intel_reports (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id UUID NOT NULL,
    report_type TEXT NOT NULL CHECK (report_type IN ('daily', 'weekly', 'monthly', 'custom')),
    title TEXT NOT NULL,
    summary TEXT,
    full_report_data JSONB,
    key_findings JSONB DEFAULT '[]',
    recommendations JSONB DEFAULT '[]',
    created_by UUID,
    is_published BOOLEAN DEFAULT false,
    published_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_intel_reports_org_type ON intel_reports(org_id, report_type, created_at DESC);

-- ════════════════════════════════════════════════════════════
-- 11. INTEL CONTENT CONTEXT — AI-generated content briefs
-- ════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS intel_content_context (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id UUID NOT NULL,
    content_brief JSONB NOT NULL,
    platform TEXT NOT NULL,
    topic TEXT NOT NULL,
    trend_keyword TEXT,
    competitor_target_id UUID REFERENCES intel_targets(id) ON DELETE SET NULL,
    strategy_headline TEXT,
    recommended_hooks TEXT[],
    key_messages TEXT[],
    visual_direction TEXT,
    best_time_to_post TIME,
    hashtags_primary TEXT[],
    hashtags_niche TEXT[],
    content_structure JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_content_context_org ON intel_content_context(org_id, created_at DESC);

-- ════════════════════════════════════════════════════════════
-- ROW LEVEL SECURITY (Org-based access control)
-- ════════════════════════════════════════════════════════════
ALTER TABLE intel_targets ENABLE ROW LEVEL SECURITY;
ALTER TABLE intel_social_posts ENABLE ROW LEVEL SECURITY;
ALTER TABLE intel_post_metrics_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE intel_ads ENABLE ROW LEVEL SECURITY;
ALTER TABLE intel_website_snapshots ENABLE ROW LEVEL SECURITY;
ALTER TABLE intel_seo_rankings ENABLE ROW LEVEL SECURITY;
ALTER TABLE intel_trends ENABLE ROW LEVEL SECURITY;
ALTER TABLE intel_viral_registry ENABLE ROW LEVEL SECURITY;
ALTER TABLE intel_roi_predictions ENABLE ROW LEVEL SECURITY;
ALTER TABLE intel_reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE intel_content_context ENABLE ROW LEVEL SECURITY;

-- RLS policies — All read/write scoped to org_id from auth.jwt
CREATE POLICY "org_isolation_targets" ON intel_targets
    FOR ALL USING (org_id = current_setting('app.current_org_id')::uuid);

CREATE POLICY "org_isolation_posts" ON intel_social_posts
    FOR ALL USING (org_id = current_setting('app.current_org_id')::uuid);

CREATE POLICY "org_isolation_ads" ON intel_ads
    FOR ALL USING (org_id = current_setting('app.current_org_id')::uuid);

CREATE POLICY "org_isolation_trends" ON intel_trends
    FOR ALL USING (org_id = current_setting('app.current_org_id')::uuid);

CREATE POLICY "org_isolation_roi" ON intel_roi_predictions
    FOR ALL USING (org_id = current_setting('app.current_org_id')::uuid);

CREATE POLICY "org_isolation_reports" ON intel_reports
    FOR ALL USING (org_id = current_setting('app.current_org_id')::uuid);

-- ════════════════════════════════════════════════════════════
-- MATERIALIZED VIEWS for reporting & analytics
-- ════════════════════════════════════════════════════════════
CREATE MATERIALIZED VIEW IF NOT EXISTS intel_dashboard_cache AS
SELECT
    org_id,
    COUNT(DISTINCT CASE WHEN is_active THEN id END) as targets_tracked,
    (SELECT COUNT(*) FROM intel_social_posts WHERE org_id = intel_targets.org_id) as posts_analyzed,
    (SELECT COUNT(*) FROM intel_social_posts WHERE org_id = intel_targets.org_id AND virality_coefficient > 40) as viral_posts_detected,
    (SELECT AVG(engagement_rate) FROM intel_social_posts WHERE org_id = intel_targets.org_id) as avg_engagement_rate,
    (SELECT COUNT(*) FROM intel_ads WHERE org_id = intel_targets.org_id AND is_active) as active_ads,
    (SELECT COUNT(*) FROM intel_trends WHERE org_id = intel_targets.org_id AND lifecycle_phase IN ('pre_emerging', 'emerging')) as emerging_trends
FROM intel_targets
GROUP BY org_id;

CREATE UNIQUE INDEX idx_dashboard_cache_org ON intel_dashboard_cache(org_id);
"""

def upgrade():
    """Apply migration"""
    from backend.fastapi.app.core.supabase_client import get_supabase
    from sqlalchemy import text
    
    sb = get_supabase()
    sb.query(text(MIGRATION_SQL)).execute()
    print("✓ God Intelligence schema created successfully")

def downgrade():
    """Rollback migration"""
    from backend.fastapi.app.core.supabase_client import get_supabase
    from sqlalchemy import text
    
    archival_sql = """
    DO $$
    BEGIN
        IF to_regclass('public.intel_dashboard_cache') IS NOT NULL
           AND to_regclass('public.intel_dashboard_cache__archived') IS NULL THEN
            ALTER MATERIALIZED VIEW intel_dashboard_cache RENAME TO intel_dashboard_cache__archived;
        END IF;
    END $$;

    DO $$
    BEGIN
        IF to_regclass('public.intel_content_context') IS NOT NULL
           AND to_regclass('public.intel_content_context__archived') IS NULL THEN
            ALTER TABLE intel_content_context RENAME TO intel_content_context__archived;
        END IF;

        IF to_regclass('public.intel_reports') IS NOT NULL
           AND to_regclass('public.intel_reports__archived') IS NULL THEN
            ALTER TABLE intel_reports RENAME TO intel_reports__archived;
        END IF;

        IF to_regclass('public.intel_roi_predictions') IS NOT NULL
           AND to_regclass('public.intel_roi_predictions__archived') IS NULL THEN
            ALTER TABLE intel_roi_predictions RENAME TO intel_roi_predictions__archived;
        END IF;

        IF to_regclass('public.intel_viral_registry') IS NOT NULL
           AND to_regclass('public.intel_viral_registry__archived') IS NULL THEN
            ALTER TABLE intel_viral_registry RENAME TO intel_viral_registry__archived;
        END IF;

        IF to_regclass('public.intel_trends') IS NOT NULL
           AND to_regclass('public.intel_trends__archived') IS NULL THEN
            ALTER TABLE intel_trends RENAME TO intel_trends__archived;
        END IF;

        IF to_regclass('public.intel_seo_rankings') IS NOT NULL
           AND to_regclass('public.intel_seo_rankings__archived') IS NULL THEN
            ALTER TABLE intel_seo_rankings RENAME TO intel_seo_rankings__archived;
        END IF;

        IF to_regclass('public.intel_website_snapshots') IS NOT NULL
           AND to_regclass('public.intel_website_snapshots__archived') IS NULL THEN
            ALTER TABLE intel_website_snapshots RENAME TO intel_website_snapshots__archived;
        END IF;

        IF to_regclass('public.intel_post_metrics_history') IS NOT NULL
           AND to_regclass('public.intel_post_metrics_history__archived') IS NULL THEN
            ALTER TABLE intel_post_metrics_history RENAME TO intel_post_metrics_history__archived;
        END IF;

        IF to_regclass('public.intel_ads') IS NOT NULL
           AND to_regclass('public.intel_ads__archived') IS NULL THEN
            ALTER TABLE intel_ads RENAME TO intel_ads__archived;
        END IF;

        IF to_regclass('public.intel_social_posts') IS NOT NULL
           AND to_regclass('public.intel_social_posts__archived') IS NULL THEN
            ALTER TABLE intel_social_posts RENAME TO intel_social_posts__archived;
        END IF;

        IF to_regclass('public.intel_targets') IS NOT NULL
           AND to_regclass('public.intel_targets__archived') IS NULL THEN
            ALTER TABLE intel_targets RENAME TO intel_targets__archived;
        END IF;
    END $$;
    """
    sb = get_supabase()
    sb.query(text(archival_sql)).execute()
    print("✓ God Intelligence schema archived without destructive deletes")
