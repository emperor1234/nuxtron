"""
Database schema migrations for social platform integration.

Run these migrations to set up tables for:
- OAuth token storage
- Scheduled posts
- Post metrics
- Platform accounts
"""

-- ─────────────────────────────────────────────────────────────────────────────────
-- OAuth Tokens (encrypted storage)
-- ─────────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS oauth_tokens (
    id SERIAL PRIMARY KEY,
    tenant_id UUID NOT NULL,
    platform VARCHAR(50) NOT NULL,
    account_id VARCHAR(200) NOT NULL,
    account_handle VARCHAR(200),
    access_token TEXT NOT NULL,  -- Encrypted via field_encryption
    refresh_token TEXT,  -- Encrypted via field_encryption
    expires_at TIMESTAMP,
    scopes TEXT[] DEFAULT '{}',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
    UNIQUE(tenant_id, platform, account_id)
);

CREATE INDEX idx_oauth_tokens_tenant_platform
    ON oauth_tokens(tenant_id, platform);

CREATE INDEX idx_oauth_tokens_expires_at
    ON oauth_tokens(expires_at)
    WHERE expires_at IS NOT NULL;


-- ─────────────────────────────────────────────────────────────────────────────────
-- Platform Accounts
-- ─────────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS platform_accounts (
    id SERIAL PRIMARY KEY,
    tenant_id UUID NOT NULL,
    platform VARCHAR(50) NOT NULL,
    account_id VARCHAR(200) NOT NULL,
    handle VARCHAR(200),
    display_name VARCHAR(500),
    profile_url TEXT,
    followers_count BIGINT DEFAULT 0,
    followers_last_updated TIMESTAMP,
    verified BOOLEAN DEFAULT FALSE,
    account_type VARCHAR(50),  -- personal, business, creator
    metadata JSONB DEFAULT '{}',
    connected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    disconnected_at TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
    UNIQUE(tenant_id, platform, account_id)
);

CREATE INDEX idx_platform_accounts_tenant_platform
    ON platform_accounts(tenant_id, platform, is_active);


-- ─────────────────────────────────────────────────────────────────────────────────
-- Scheduled Posts
-- ─────────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS scheduled_posts (
    id SERIAL PRIMARY KEY,
    tenant_id UUID NOT NULL,
    post_id VARCHAR(200),  -- Platform-assigned ID after publishing
    content TEXT NOT NULL,
    media_urls TEXT[] DEFAULT '{}',
    media_alt_text TEXT[] DEFAULT '{}',
    platforms TEXT[] NOT NULL,
    scheduled_at TIMESTAMP NOT NULL,
    published_at TIMESTAMP,
    status VARCHAR(50) DEFAULT 'pending',  -- pending, published, failed, scheduled, cancelled
    post_url TEXT,
    created_by VARCHAR(160),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    error_message TEXT,
    metadata JSONB DEFAULT '{}',
    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
);

CREATE INDEX idx_scheduled_posts_tenant_status
    ON scheduled_posts(tenant_id, status);

CREATE INDEX idx_scheduled_posts_scheduled_at
    ON scheduled_posts(scheduled_at)
    WHERE status IN ('pending', 'scheduled');


-- ─────────────────────────────────────────────────────────────────────────────────
-- Post Metrics (aggregated analytics)
-- ─────────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS post_metrics (
    id SERIAL PRIMARY KEY,
    tenant_id UUID NOT NULL,
    scheduled_post_id INTEGER,
    platform_post_id VARCHAR(200),
    platform VARCHAR(50),
    impressions BIGINT DEFAULT 0,
    clicks BIGINT DEFAULT 0,
    engagements BIGINT DEFAULT 0,
    likes BIGINT DEFAULT 0,
    comments BIGINT DEFAULT 0,
    shares BIGINT DEFAULT 0,
    reach BIGINT DEFAULT 0,
    saves BIGINT DEFAULT 0,
    conversions INT DEFAULT 0,
    revenue_attributed DECIMAL(12, 2) DEFAULT 0,
    ctr_percent DECIMAL(5, 2) DEFAULT 0,  -- Click-through rate %
    engagement_rate_percent DECIMAL(5, 2) DEFAULT 0,
    sampled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
    FOREIGN KEY (scheduled_post_id) REFERENCES scheduled_posts(id) ON DELETE SET NULL
);

CREATE INDEX idx_post_metrics_tenant_platform
    ON post_metrics(tenant_id, platform);

CREATE INDEX idx_post_metrics_scheduled_post_id
    ON post_metrics(scheduled_post_id);

CREATE INDEX idx_post_metrics_sampled_at
    ON post_metrics(sampled_at DESC);


-- ─────────────────────────────────────────────────────────────────────────────────
-- Platform Messages (Inbox)
-- ─────────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS platform_messages (
    id SERIAL PRIMARY KEY,
    tenant_id UUID NOT NULL,
    platform_message_id VARCHAR(200),
    platform VARCHAR(50),
    source_type VARCHAR(50),  -- dm, comment, mention, review, story_reply
    author_id VARCHAR(200),
    author_handle VARCHAR(200),
    author_display_name VARCHAR(500),
    message_text TEXT NOT NULL,
    message_type VARCHAR(50),  -- question, complaint, compliment, spam, conversation, crisis
    sentiment VARCHAR(20),  -- positive, neutral, negative
    confidence DECIMAL(3, 2) DEFAULT 1.0,
    assigned_to VARCHAR(160),
    status VARCHAR(40) DEFAULT 'pending',
    tags TEXT[] DEFAULT '{}',
    created_at TIMESTAMP,
    received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
);

CREATE INDEX idx_platform_messages_tenant_status
    ON platform_messages(tenant_id, status);

CREATE INDEX idx_platform_messages_platform
    ON platform_messages(tenant_id, platform);


-- ─────────────────────────────────────────────────────────────────────────────────
-- Cleanup/Maintenance
-- ─────────────────────────────────────────────────────────────────────────────────

-- Remove expired OAuth tokens periodically
-- SELECT * FROM oauth_tokens WHERE expires_at < NOW() - INTERVAL '30 days';

-- Archive old metrics
-- ARCHIVE posts_metrics WHERE sampled_at < NOW() - INTERVAL '1 year';
