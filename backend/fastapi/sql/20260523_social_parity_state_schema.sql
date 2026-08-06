-- Social parity persistence schema
-- Formal SQL migration for PostgreSQL environments.

CREATE TABLE IF NOT EXISTS social_parity_state (
    tenant_id VARCHAR(128) PRIMARY KEY,
    schema_version INTEGER NOT NULL,
    state_version INTEGER NOT NULL,
    state_payload TEXT NOT NULL,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS social_parity_state_versions (
    event_id VARCHAR(36) PRIMARY KEY,
    tenant_id VARCHAR(128) NOT NULL,
    schema_version INTEGER NOT NULL,
    state_version INTEGER NOT NULL,
    state_payload TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_social_parity_state_versions_tenant_created_at
    ON social_parity_state_versions (tenant_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_social_parity_state_versions_tenant_version
    ON social_parity_state_versions (tenant_id, state_version DESC);
