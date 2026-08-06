-- ULTIMATE Platform: PostgreSQL Schema
-- Multi-tenant, RLS-protected, production-ready
-- Run with: psql -U postgres -h localhost -d postgres -f schema.sql

-- Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgvector";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- for full-text search

-- ============================================================================
-- 1. CORE ENTITIES
-- ============================================================================

-- Sites (tenants)
CREATE TABLE sites (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  tenant_id UUID NOT NULL,
  domain TEXT NOT NULL,
  name TEXT,
  vertical TEXT,  -- "saas", "ecommerce", "local", "news", "content"
  goal TEXT,  -- "growth", "recovery", "consolidation", "migration", "launch"
  status TEXT DEFAULT 'active',  -- "active", "paused", "archived"
  config JSONB,  -- branding, integrations, API keys (encrypted in app)
  llm_pool JSONB,  -- LLM configuration
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  CONSTRAINT sites_unique_domain_per_tenant UNIQUE(tenant_id, domain)
);
CREATE INDEX idx_sites_tenant ON sites(tenant_id);
CREATE INDEX idx_sites_status ON sites(status) WHERE status = 'active';

-- Pages (atomic SEO unit)
CREATE TABLE pages (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  site_id UUID NOT NULL REFERENCES sites(id) ON DELETE CASCADE,
  path TEXT NOT NULL,  -- /pricing
  url TEXT NOT NULL,
  title TEXT,
  h1 TEXT,
  content_hash TEXT,  -- SHA256 of body (detect changes)
  content_type TEXT,  -- "article", "product", "category", "landing"
  intent TEXT,  -- "informational", "transactional", "navigational"
  embedding VECTOR(1536),  -- pgvector for semantic search
  crawled_at TIMESTAMPTZ,
  indexed_at TIMESTAMPTZ,  -- last GSC sync
  status_code INT,
  cwr_score FLOAT,  -- Core Web Vitals score (0-100)
  is_indexable BOOLEAN DEFAULT TRUE,
  canonical_id UUID REFERENCES pages(id),  -- self-ref if canonical
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  deleted_at TIMESTAMPTZ,  -- soft delete
  CONSTRAINT pages_unique_per_site UNIQUE(site_id, path)
);
CREATE INDEX idx_pages_site_crawled ON pages(site_id, crawled_at DESC);
CREATE INDEX idx_pages_site_indexed ON pages(site_id, indexed_at DESC);
CREATE INDEX idx_pages_site_status ON pages(site_id, status_code);
CREATE INDEX idx_pages_embedding ON pages USING ivfflat (embedding vector_cosine_ops) WHERE embedding IS NOT NULL;
CREATE INDEX idx_pages_site_deleted ON pages(site_id) WHERE deleted_at IS NULL;

-- Entities (Knowledge Graph nodes)
CREATE TABLE entities (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  site_id UUID NOT NULL REFERENCES sites(id) ON DELETE CASCADE,
  neo4j_id TEXT,  -- pointer to Neo4j
  name TEXT NOT NULL,
  type TEXT,  -- "brand", "product", "concept", "location", "person", "org"
  description TEXT,
  embedding VECTOR(1536),  -- semantic meaning
  aliases TEXT[],  -- "Apple Inc", "Apple Computer"
  signal_strength FLOAT DEFAULT 0,  -- confidence score
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  CONSTRAINT entities_unique_per_site UNIQUE(site_id, name, type)
);
CREATE INDEX idx_entities_site ON entities(site_id);
CREATE INDEX idx_entities_type ON entities(type);
CREATE INDEX idx_entities_embedding ON entities USING ivfflat (embedding vector_cosine_ops) WHERE embedding IS NOT NULL;

-- Modules (running instance of a feature)
CREATE TABLE modules (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  site_id UUID NOT NULL REFERENCES sites(id) ON DELETE CASCADE,
  module_type TEXT NOT NULL,  -- "seo-ai", "entity-first-seo", etc.
  status TEXT DEFAULT 'active',  -- "active", "disabled", "error"
  config JSONB,  -- module-specific settings
  llm_pool TEXT[],  -- which LLMs to prefer
  search_engines TEXT[],  -- data sources
  trigger TEXT,  -- "on_demand", "scheduled", "event", "continuous"
  cron_schedule TEXT,  -- if scheduled
  last_run_at TIMESTAMPTZ,
  next_run_at TIMESTAMPTZ,
  error_log JSONB[],  -- [{timestamp, message, severity}]
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  CONSTRAINT modules_unique_per_site UNIQUE(site_id, module_type)
);
CREATE INDEX idx_modules_site_type ON modules(site_id, module_type);
CREATE INDEX idx_modules_status ON modules(status);
CREATE INDEX idx_modules_next_run ON modules(next_run_at) WHERE status = 'active';

-- Runs (single execution of a module)
CREATE TABLE runs (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  module_id UUID NOT NULL REFERENCES modules(id) ON DELETE CASCADE,
  site_id UUID NOT NULL REFERENCES sites(id) ON DELETE CASCADE,
  triggered_by TEXT,  -- "schedule", "event", "manual", "agent"
  triggered_by_id UUID,  -- which agent or run
  input_data JSONB,
  output_data JSONB,
  status TEXT DEFAULT 'pending',  -- "pending", "running", "success", "failure"
  error_message TEXT,
  execution_time_ms INT,
  llm_used TEXT,  -- which LLM was selected
  llm_tokens_used INT,
  cost_usd NUMERIC(10, 6),  -- API cost
  started_at TIMESTAMPTZ DEFAULT NOW(),
  completed_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_runs_module ON runs(module_id);
CREATE INDEX idx_runs_site ON runs(site_id, created_at DESC);
CREATE INDEX idx_runs_status ON runs(status) WHERE status IN ('pending', 'running');
CREATE INDEX idx_runs_completed ON runs(completed_at DESC) WHERE completed_at IS NOT NULL;
CREATE INDEX idx_runs_cost ON runs(cost_usd) WHERE cost_usd > 0;

-- Metrics (measured outcome)
CREATE TABLE metrics (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  site_id UUID NOT NULL REFERENCES sites(id) ON DELETE CASCADE,
  run_id UUID REFERENCES runs(id) ON DELETE SET NULL,
  module_id UUID REFERENCES modules(id) ON DELETE SET NULL,
  page_id UUID REFERENCES pages(id) ON DELETE SET NULL,
  entity_id UUID REFERENCES entities(id) ON DELETE SET NULL,
  metric_name TEXT NOT NULL,
  value FLOAT,
  unit TEXT,  -- "count", "%", "ms", "score"
  trend TEXT,  -- "up", "down", "stable"
  tags TEXT[],
  created_at TIMESTAMPTZ DEFAULT NOW(),
  CONSTRAINT metric_value_not_null CHECK (value IS NOT NULL)
);
CREATE INDEX idx_metrics_site_module_time ON metrics(site_id, module_id, created_at DESC);
CREATE INDEX idx_metrics_page ON metrics(page_id) WHERE page_id IS NOT NULL;
CREATE INDEX idx_metrics_entity ON metrics(entity_id) WHERE entity_id IS NOT NULL;
CREATE INDEX idx_metrics_name ON metrics(metric_name);
CREATE INDEX idx_metrics_time ON metrics(created_at DESC);
CREATE INDEX idx_metrics_tags ON metrics USING gin(tags);

-- Page-Entity relationships
CREATE TABLE page_entities (
  page_id UUID NOT NULL REFERENCES pages(id) ON DELETE CASCADE,
  entity_id UUID NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
  confidence FLOAT DEFAULT 0.5,  -- 0-1, how confident is the mention?
  context TEXT,  -- snippet where entity is mentioned
  mention_count INT DEFAULT 1,
  position INT,  -- ordinal position in content
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  PRIMARY KEY (page_id, entity_id)
);
CREATE INDEX idx_page_entities_entity ON page_entities(entity_id);

-- Entity-Entity relationships (Neo4j pointer, but we denormalize some here)
CREATE TABLE entity_relationships (
  from_id UUID NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
  to_id UUID NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
  relationship_type TEXT,  -- "mentions", "related", "parent", "synonym"
  confidence FLOAT DEFAULT 0.5,
  neo4j_id TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  PRIMARY KEY (from_id, to_id, relationship_type)
);
CREATE INDEX idx_entity_rel_type ON entity_relationships(relationship_type);

-- Module data lineage (who feeds whom)
CREATE TABLE module_data_lineage (
  consuming_module_id UUID NOT NULL REFERENCES modules(id) ON DELETE CASCADE,
  producing_module_id UUID NOT NULL REFERENCES modules(id) ON DELETE CASCADE,
  site_id UUID NOT NULL REFERENCES sites(id) ON DELETE CASCADE,
  data_type TEXT,  -- "pages_analyzed", "entities_extracted", etc.
  last_transfer_at TIMESTAMPTZ,
  transfer_count INT DEFAULT 0,
  PRIMARY KEY (consuming_module_id, producing_module_id, data_type)
);
CREATE INDEX idx_lineage_producing ON module_data_lineage(producing_module_id);
CREATE INDEX idx_lineage_site ON module_data_lineage(site_id);

-- ============================================================================
-- 2. EVENTS & AUTONOMY
-- ============================================================================

-- Events (system signals)
CREATE TABLE events (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  site_id UUID NOT NULL REFERENCES sites(id) ON DELETE CASCADE,
  type TEXT NOT NULL,  -- "pages_analyzed", "entities_extracted", etc.
  source_module_id UUID REFERENCES modules(id) ON DELETE SET NULL,
  source_run_id UUID REFERENCES runs(id) ON DELETE SET NULL,
  severity TEXT DEFAULT 'info',  -- "info", "warning", "error"
  payload JSONB,
  targets TEXT[],  -- which modules should react
  processed_by UUID[],  -- which modules have handled this
  created_at TIMESTAMPTZ DEFAULT NOW(),
  expires_at TIMESTAMPTZ DEFAULT NOW() + INTERVAL '24 hours'
);
CREATE INDEX idx_events_site ON events(site_id, created_at DESC);
CREATE INDEX idx_events_type ON events(type);
CREATE INDEX idx_events_source ON events(source_module_id) WHERE source_module_id IS NOT NULL;
CREATE INDEX idx_events_expires ON events(expires_at) WHERE expires_at > NOW();
CREATE INDEX idx_events_targets ON events USING gin(targets);

-- Agents (autonomous actors)
CREATE TABLE agents (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  site_id UUID NOT NULL REFERENCES sites(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  autonomy_tier INT DEFAULT 1,  -- 1 = suggest only, 2 = auto low-risk, 3 = auto + queue
  status TEXT DEFAULT 'active',  -- "active", "paused", "reviewing"
  policies JSONB,  -- safety constraints
  reasoning_log JSONB[],  -- [{timestamp, decision, reasoning, approved}]
  error_log JSONB[],
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_agents_site_status ON agents(site_id, status);

-- Action audit (what actions have agents taken?)
CREATE TABLE action_audit (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  agent_id UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
  module_id UUID REFERENCES modules(id) ON DELETE SET NULL,
  action_type TEXT,  -- "internal_link_added", "schema_updated", etc.
  before_state JSONB,
  after_state JSONB,
  status TEXT,  -- "pending", "approved", "executed", "rolled_back"
  approved_by TEXT,  -- user email or "auto"
  approval_at TIMESTAMPTZ,
  executed_at TIMESTAMPTZ,
  rolled_back_at TIMESTAMPTZ,
  reasoning TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_action_audit_agent ON action_audit(agent_id);
CREATE INDEX idx_action_audit_executed ON action_audit(executed_at DESC) WHERE executed_at IS NOT NULL;
CREATE INDEX idx_action_audit_status ON action_audit(status);

-- ============================================================================
-- 3. HREFLANG & INTERNATIONAL
-- ============================================================================

CREATE TABLE page_hreflang (
  from_page_id UUID NOT NULL REFERENCES pages(id) ON DELETE CASCADE,
  to_page_id UUID NOT NULL REFERENCES pages(id) ON DELETE CASCADE,
  language_code TEXT,  -- "en", "es", "fr", etc.
  region_code TEXT,  -- "US", "GB", "DE", etc.
  rel_alternate_hreflang TEXT,  -- the full hreflang value
  is_canonical BOOLEAN DEFAULT FALSE,
  verified BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  PRIMARY KEY (from_page_id, to_page_id, language_code, region_code)
);
CREATE INDEX idx_hreflang_language ON page_hreflang(language_code);
CREATE INDEX idx_hreflang_verified ON page_hreflang(verified);

-- ============================================================================
-- 4. SCHEMA & STRUCTURED DATA
-- ============================================================================

CREATE TABLE page_schema (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  page_id UUID NOT NULL REFERENCES pages(id) ON DELETE CASCADE,
  schema_type TEXT,  -- "Article", "Product", "FAQPage", "NewsArticle", etc.
  schema_data JSONB,  -- the actual @context and properties
  validation_status TEXT,  -- "valid", "warning", "error"
  validation_errors TEXT[],
  detected_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_page_schema_type ON page_schema(schema_type);
CREATE INDEX idx_page_schema_validation ON page_schema(validation_status);

-- ============================================================================
-- 4.5. STRATEGY / ENHANCEMENT / RICH-RESULT TRACKING
-- ============================================================================

CREATE TABLE strategy_snapshots (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  site_id TEXT NOT NULL,
  snapshot_type TEXT NOT NULL DEFAULT 'content_strategy',
  cluster_count INT DEFAULT 0,
  gap_count INT DEFAULT 0,
  priorities JSONB,
  summary TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_strategy_snapshots_site_created ON strategy_snapshots(site_id, created_at DESC);

CREATE TABLE content_enhancement_runs (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  site_id TEXT NOT NULL,
  page_url TEXT NOT NULL,
  enhancement_run_id TEXT NOT NULL,
  content_version_id TEXT NOT NULL,
  uplift_after_publish FLOAT DEFAULT 0,
  status TEXT DEFAULT 'draft',
  created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_content_enhancement_site_created ON content_enhancement_runs(site_id, created_at DESC);
CREATE INDEX idx_content_enhancement_run_id ON content_enhancement_runs(enhancement_run_id);

CREATE TABLE rich_result_metrics (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  site_id TEXT NOT NULL,
  page_url TEXT NOT NULL,
  result_type TEXT NOT NULL,
  impressions INT DEFAULT 0,
  ctr FLOAT DEFAULT 0,
  delta_7d FLOAT DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_rich_result_site_created ON rich_result_metrics(site_id, created_at DESC);
CREATE INDEX idx_rich_result_type ON rich_result_metrics(result_type);

-- ============================================================================
-- 4.6. TOOL INTEGRATIONS REGISTRY
-- ============================================================================
-- Tracks per-tenant configured third-party tools (SEO, AI, analytics, etc.)
-- API keys are stored encrypted in the app layer; only masked values land here.

CREATE TABLE tool_integrations (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  tenant_id UUID NOT NULL,
  tool_key TEXT NOT NULL,          -- e.g. 'dataforseo', 'serper', 'deepgram'
  display_name TEXT NOT NULL,
  category TEXT NOT NULL,          -- 'seo_data', 'ai', 'analytics', 'security', 'speech'
  tier TEXT NOT NULL DEFAULT 'free', -- 'free', 'payg', 'paid'
  cost_label TEXT,                 -- e.g. 'PAYG', 'Free', '£20/mo'
  is_enabled BOOLEAN DEFAULT FALSE,
  api_key_masked TEXT,             -- last 4 chars of key, never full key
  endpoint_override TEXT,          -- optional custom endpoint
  last_tested_at TIMESTAMPTZ,
  last_test_status TEXT,           -- 'ok', 'error', 'untested'
  last_test_latency_ms INT,
  notes TEXT,
  config JSONB,                    -- extra structured config (region, model name, etc.)
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  CONSTRAINT tool_integrations_unique_per_tenant UNIQUE(tenant_id, tool_key)
);
CREATE INDEX idx_tool_integrations_tenant ON tool_integrations(tenant_id);
CREATE INDEX idx_tool_integrations_category ON tool_integrations(category);
CREATE INDEX idx_tool_integrations_enabled ON tool_integrations(tenant_id, is_enabled) WHERE is_enabled = TRUE;

-- ============================================================================
-- 5. TENANT ISOLATION & RLS
-- ============================================================================

-- Enable RLS
ALTER TABLE sites ENABLE ROW LEVEL SECURITY;
ALTER TABLE pages ENABLE ROW LEVEL SECURITY;
ALTER TABLE entities ENABLE ROW LEVEL SECURITY;
ALTER TABLE modules ENABLE ROW LEVEL SECURITY;
ALTER TABLE runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE metrics ENABLE ROW LEVEL SECURITY;
ALTER TABLE agents ENABLE ROW LEVEL SECURITY;
ALTER TABLE events ENABLE ROW LEVEL SECURITY;
ALTER TABLE action_audit ENABLE ROW LEVEL SECURITY;

-- Helper function: get current tenant_id from JWT/session
CREATE OR REPLACE FUNCTION get_current_tenant_id() RETURNS UUID AS $$
  SELECT current_setting('app.current_tenant_id')::UUID;
$$ LANGUAGE SQL STABLE;

-- RLS Policies
CREATE POLICY "sites_rls" ON sites
  USING (tenant_id = get_current_tenant_id());

CREATE POLICY "pages_rls" ON pages
  USING (
    site_id IN (SELECT id FROM sites WHERE tenant_id = get_current_tenant_id())
  );

CREATE POLICY "entities_rls" ON entities
  USING (
    site_id IN (SELECT id FROM sites WHERE tenant_id = get_current_tenant_id())
  );

CREATE POLICY "modules_rls" ON modules
  USING (
    site_id IN (SELECT id FROM sites WHERE tenant_id = get_current_tenant_id())
  );

CREATE POLICY "runs_rls" ON runs
  USING (
    site_id IN (SELECT id FROM sites WHERE tenant_id = get_current_tenant_id())
  );

CREATE POLICY "metrics_rls" ON metrics
  USING (
    site_id IN (SELECT id FROM sites WHERE tenant_id = get_current_tenant_id())
  );

CREATE POLICY "agents_rls" ON agents
  USING (
    site_id IN (SELECT id FROM sites WHERE tenant_id = get_current_tenant_id())
  );

CREATE POLICY "events_rls" ON events
  USING (
    site_id IN (SELECT id FROM sites WHERE tenant_id = get_current_tenant_id())
  );

CREATE POLICY "action_audit_rls" ON action_audit
  USING (
    agent_id IN (
      SELECT id FROM agents 
      WHERE site_id IN (SELECT id FROM sites WHERE tenant_id = get_current_tenant_id())
    )
  );

-- ============================================================================
-- 6. TRIGGERS & COMPUTED FIELDS
-- ============================================================================

-- Update page.updated_at on any change
CREATE OR REPLACE FUNCTION trigger_update_timestamp()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER pages_update_timestamp
  BEFORE UPDATE ON pages
  FOR EACH ROW
  EXECUTE FUNCTION trigger_update_timestamp();

CREATE TRIGGER entities_update_timestamp
  BEFORE UPDATE ON entities
  FOR EACH ROW
  EXECUTE FUNCTION trigger_update_timestamp();

CREATE TRIGGER modules_update_timestamp
  BEFORE UPDATE ON modules
  FOR EACH ROW
  EXECUTE FUNCTION trigger_update_timestamp();

-- ============================================================================
-- 7. VIEWS FOR COMMON QUERIES
-- ============================================================================

-- Active pages per site
CREATE VIEW v_active_pages AS
SELECT 
  p.id,
  p.site_id,
  p.path,
  p.url,
  p.crawled_at,
  p.status_code,
  p.cwr_score,
  COALESCE(COUNT(pe.entity_id), 0) as entity_count
FROM pages p
LEFT JOIN page_entities pe ON p.id = pe.page_id
WHERE p.deleted_at IS NULL
GROUP BY p.id, p.site_id;

-- Module execution summary (last 24h)
CREATE VIEW v_module_execution_24h AS
SELECT
  m.module_type,
  COUNT(r.id) as execution_count,
  COUNT(CASE WHEN r.status = 'success' THEN 1 END) as success_count,
  AVG(r.execution_time_ms) as avg_execution_time_ms,
  SUM(r.cost_usd) as total_cost_usd,
  MAX(r.completed_at) as last_run_at
FROM modules m
LEFT JOIN runs r ON m.id = r.module_id AND r.completed_at > NOW() - INTERVAL '24 hours'
GROUP BY m.module_type;

-- Metric trends (compare last 7d vs previous 7d)
CREATE VIEW v_metric_trend_7d AS
SELECT
  metric_name,
  AVG(CASE WHEN created_at > NOW() - INTERVAL '7 days' THEN value END) as last_7d_avg,
  AVG(CASE WHEN created_at BETWEEN NOW() - INTERVAL '14 days' AND NOW() - INTERVAL '7 days' THEN value END) as prev_7d_avg
FROM metrics
WHERE created_at > NOW() - INTERVAL '14 days'
GROUP BY metric_name;

-- ============================================================================
-- 8. PERFORMANCE INDEXES
-- ============================================================================

-- Composite indexes for common queries
CREATE INDEX idx_pages_site_status_crawled ON pages(site_id, status_code, crawled_at DESC);
CREATE INDEX idx_metrics_site_created_value ON metrics(site_id, created_at DESC, value);
CREATE INDEX idx_runs_site_module_completed ON runs(site_id, module_id, completed_at DESC);
CREATE INDEX idx_events_site_type_created ON events(site_id, type, created_at DESC);

-- GIN indexes for array/JSONB queries
CREATE INDEX idx_modules_llm_pool ON modules USING gin(llm_pool);
CREATE INDEX idx_entities_aliases ON entities USING gin(aliases);

-- ============================================================================
-- 9. EXTENSIONS & HELPER FUNCTIONS
-- ============================================================================

-- Function to get all metrics for a page over time
CREATE OR REPLACE FUNCTION get_page_metrics_timeline(
  p_page_id UUID,
  p_days_back INT DEFAULT 30
)
RETURNS TABLE (
  metric_name TEXT,
  value FLOAT,
  created_at TIMESTAMPTZ,
  trend TEXT
) AS $$
SELECT 
  metric_name,
  value,
  created_at,
  trend
FROM metrics
WHERE page_id = p_page_id
  AND created_at > NOW() - (p_days_back || ' days')::INTERVAL
ORDER BY metric_name, created_at DESC;
$$ LANGUAGE SQL;

-- Function to compute module health score (0-100)
CREATE OR REPLACE FUNCTION compute_module_health_score(p_module_id UUID)
RETURNS INT AS $$
DECLARE
  v_total_runs INT;
  v_success_runs INT;
  v_avg_time FLOAT;
  v_error_rate FLOAT;
  v_health_score INT;
BEGIN
  SELECT 
    COUNT(*),
    COUNT(CASE WHEN status = 'success' THEN 1 END),
    AVG(execution_time_ms)::FLOAT
  INTO v_total_runs, v_success_runs, v_avg_time
  FROM runs
  WHERE module_id = p_module_id
    AND created_at > NOW() - INTERVAL '7 days';

  IF v_total_runs = 0 THEN
    RETURN 0;
  END IF;

  v_error_rate := (v_total_runs - v_success_runs)::FLOAT / v_total_runs;
  v_health_score := ROUND(
    (v_success_runs::FLOAT / v_total_runs) * 100  -- 0-100 by success rate
    - (v_error_rate * 20)  -- penalty for errors
    - (LEAST(v_avg_time / 10000, 20))  -- penalty for slow execution
  );

  RETURN GREATEST(0, LEAST(v_health_score, 100));
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- 9b. AI AGENT INFRASTRUCTURE (Kodee-Class Agent Tables)
-- ============================================================================

-- ai_agent_tools: MCP-style tool registry — each tool the agent can call
CREATE TABLE ai_agent_tools (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  tenant_id TEXT NOT NULL,
  key TEXT NOT NULL,                         -- machine-readable: "run_site_audit"
  display_name TEXT NOT NULL,
  group_name TEXT NOT NULL,                  -- "SEO Tools", "Platform Tools", etc.
  description TEXT,
  fn_signature TEXT,                         -- "run_site_audit(site_id)"
  input_schema JSONB,                        -- JSON Schema for parameters
  required_role TEXT DEFAULT 'user',         -- "user", "admin", "super_admin"
  risk_level TEXT DEFAULT 'low',             -- "low", "medium", "high"
  requires_confirmation BOOLEAN DEFAULT FALSE,
  is_active BOOLEAN DEFAULT TRUE,
  backend_endpoint TEXT,                     -- FastAPI endpoint that backs this tool
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  CONSTRAINT ai_agent_tools_unique_per_tenant UNIQUE (tenant_id, key)
);
CREATE INDEX idx_ai_agent_tools_tenant ON ai_agent_tools(tenant_id);
CREATE INDEX idx_ai_agent_tools_group ON ai_agent_tools(group_name);
CREATE INDEX idx_ai_agent_tools_risk ON ai_agent_tools(risk_level);
CREATE INDEX idx_ai_agent_tools_active ON ai_agent_tools(is_active) WHERE is_active = TRUE;

-- ai_agent_sessions: each user conversation with the agent
CREATE TABLE ai_agent_sessions (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  tenant_id TEXT NOT NULL,
  user_id TEXT,
  session_ref TEXT NOT NULL,                 -- client-generated session handle
  phase TEXT DEFAULT 'phase1',               -- "phase1", "phase2", "phase3"
  started_at TIMESTAMPTZ DEFAULT NOW(),
  ended_at TIMESTAMPTZ,
  status TEXT DEFAULT 'active',              -- "active", "completed", "error"
  message_count INT DEFAULT 0,
  tool_call_count INT DEFAULT 0,
  model_used TEXT,                           -- e.g. "deepseek-r1:8b"
  context_snapshot JSONB,                    -- user/org/resource context at session start
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_agent_sessions_tenant ON ai_agent_sessions(tenant_id);
CREATE INDEX idx_agent_sessions_status ON ai_agent_sessions(status);
CREATE INDEX idx_agent_sessions_started ON ai_agent_sessions(started_at DESC);

-- ai_agent_tool_calls: full audit trail of every tool the agent invoked
CREATE TABLE ai_agent_tool_calls (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  session_id UUID REFERENCES ai_agent_sessions(id) ON DELETE CASCADE,
  tenant_id TEXT NOT NULL,
  tool_key TEXT NOT NULL,                    -- matches ai_agent_tools.key
  input_params JSONB,
  output_result JSONB,
  status TEXT DEFAULT 'pending',             -- "pending", "running", "success", "error", "rejected"
  risk_level TEXT,
  required_confirmation BOOLEAN DEFAULT FALSE,
  confirmed_by TEXT,                         -- user email or "auto"
  confirmed_at TIMESTAMPTZ,
  started_at TIMESTAMPTZ DEFAULT NOW(),
  completed_at TIMESTAMPTZ,
  duration_ms INT,
  error_message TEXT,
  agent_role TEXT,                           -- "planner", "executor", "critic", "supervisor"
  created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_agent_tool_calls_session ON ai_agent_tool_calls(session_id);
CREATE INDEX idx_agent_tool_calls_tenant ON ai_agent_tool_calls(tenant_id);
CREATE INDEX idx_agent_tool_calls_tool ON ai_agent_tool_calls(tool_key);
CREATE INDEX idx_agent_tool_calls_status ON ai_agent_tool_calls(status);
CREATE INDEX idx_agent_tool_calls_created ON ai_agent_tool_calls(created_at DESC);

-- ai_agent_config: per-tenant agent configuration (stack phase, enabled models, etc.)
CREATE TABLE ai_agent_config (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  tenant_id TEXT NOT NULL UNIQUE,
  current_phase TEXT DEFAULT 'phase1',       -- "phase1", "phase2", "phase3"
  enabled_models TEXT[] DEFAULT ARRAY['deepseek-r1:8b'],
  enabled_agent_roles TEXT[] DEFAULT ARRAY['planner', 'executor'],
  tool_count_limit INT DEFAULT 10,
  max_auto_actions INT DEFAULT 0,            -- 0 = confirm all, >0 = auto-approve low-risk
  audit_retention_days INT DEFAULT 90,
  allow_high_risk_tools BOOLEAN DEFAULT FALSE,
  mcp_endpoint TEXT,                         -- if MCP server is configured
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_agent_config_tenant ON ai_agent_config(tenant_id);

-- Seed default agent tools (matches frontend data)
INSERT INTO ai_agent_tools (tenant_id, key, display_name, group_name, description, fn_signature, risk_level, requires_confirmation, backend_endpoint) VALUES
  ('tenant-demo', 'run_site_audit',       'Run Site Audit',        'SEO Tools',      'Full technical SEO audit of a site',                'run_site_audit(site_id)',                  'low',    FALSE, '/seo-platform/technical/audit'),
  ('tenant-demo', 'generate_blog_post',   'Generate Blog Post',    'SEO Tools',      'AI-generated blog post for site and topic',         'generate_blog_post(site_id, topic)',        'low',    FALSE, '/seo-platform/content/write'),
  ('tenant-demo', 'optimize_page',        'Optimize Page',         'SEO Tools',      'On-page SEO optimization for a URL',                'optimize_page(url_id)',                     'medium', FALSE, '/seo-platform/on-page/analyze'),
  ('tenant-demo', 'create_internal_links','Create Internal Links',  'SEO Tools',      'Auto-suggest internal linking structure',           'create_internal_links(site_id, src, tgts)', 'medium', FALSE, '/seo-platform/internal-linking/suggest'),
  ('tenant-demo', 'create_project',       'Create Project',        'Platform Tools', 'Create a new client project',                      'create_project(client_id, name)',           'medium', FALSE, '/crm/projects'),
  ('tenant-demo', 'add_domain',           'Add Domain',            'Platform Tools', 'Add a domain to a client account',                 'add_domain(client_id, domain)',             'medium', FALSE, '/platform/domains'),
  ('tenant-demo', 'trigger_migration',    'Trigger Migration',     'Platform Tools', 'Trigger a site migration workflow',                'trigger_migration(site_id)',                'high',   TRUE,  '/seo-platform/site-migration/analyze'),
  ('tenant-demo', 'run_lighthouse_audit', 'Lighthouse Audit',      'Platform Tools', 'Run a Lighthouse performance audit on a URL',      'run_lighthouse_audit(url_id)',              'low',    FALSE, '/seo-platform/performance/audit'),
  ('tenant-demo', 'create_brief',         'Create Content Brief',  'Content Tools',  'Generate a content brief for a keyword',           'create_brief(keyword)',                     'low',    FALSE, '/seo-platform/content/brief'),
  ('tenant-demo', 'rewrite_paragraph',    'Rewrite Paragraph',     'Content Tools',  'AI rewrite of a content block on a page',          'rewrite_paragraph(page_id, block_id)',      'medium', FALSE, '/seo-platform/brand-voice/rewrite')
ON CONFLICT DO NOTHING;

-- Seed default agent config for demo tenant
INSERT INTO ai_agent_config (tenant_id, current_phase, enabled_models, enabled_agent_roles, tool_count_limit, max_auto_actions)
VALUES ('tenant-demo', 'phase1', ARRAY['deepseek-r1:8b', 'llama3:8b'], ARRAY['planner', 'executor', 'critic', 'supervisor'], 10, 0)
ON CONFLICT DO NOTHING;

-- ============================================================================
-- 10. INITIAL DATA
-- ============================================================================

-- Create default tenant (for demo)
INSERT INTO sites (tenant_id, domain, name, vertical, goal, status)
VALUES (
  '00000000-0000-0000-0000-000000000001'::UUID,
  'demo-site.com',
  'Demo Site',
  'saas',
  'growth',
  'active'
)
ON CONFLICT DO NOTHING;

COMMIT;
