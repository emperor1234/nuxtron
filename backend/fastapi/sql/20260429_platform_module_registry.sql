-- Platform module registry schema for DB-backed hybrid stack catalogs.
-- Apply manually with psql or your deployment migration workflow.

CREATE TABLE IF NOT EXISTS platform_module_registry (
    module_id TEXT PRIMARY KEY,
    category TEXT NOT NULL,
    goal TEXT NOT NULL,
    constraint_text TEXT NOT NULL DEFAULT '100% free + open-source.',
    hybrid_stack TEXT NOT NULL,
    hybrid_score TEXT NOT NULL DEFAULT '100/100 (100%)',
    outcomes JSONB NOT NULL DEFAULT '[]'::jsonb,
    display_order INT NOT NULL DEFAULT 100,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS platform_module_tools (
    id BIGSERIAL PRIMARY KEY,
    module_id TEXT NOT NULL REFERENCES platform_module_registry(module_id) ON DELETE CASCADE,
    tool_type TEXT NOT NULL CHECK (tool_type IN ('free', 'open_source')),
    tool_name TEXT NOT NULL,
    score INT NOT NULL CHECK (score >= 0 AND score <= 100),
    capabilities JSONB NOT NULL DEFAULT '[]'::jsonb,
    sort_order INT NOT NULL DEFAULT 100
);

CREATE INDEX IF NOT EXISTS idx_platform_module_registry_active_order
ON platform_module_registry (is_active, display_order, module_id);

CREATE INDEX IF NOT EXISTS idx_platform_module_tools_module_order
ON platform_module_tools (module_id, tool_type, sort_order, id);
