-- Unified 31-module core SaaS schema (idempotent).
-- Use with PostgreSQL 15+.

BEGIN;

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS tenants (
  id UUID PRIMARY KEY,
  slug TEXT UNIQUE NOT NULL,
  name TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS modules (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  category TEXT NOT NULL,
  goal TEXT NOT NULL DEFAULT '',
  plane TEXT NOT NULL,
  version TEXT NOT NULL DEFAULT 'v1',
  status TEXT NOT NULL DEFAULT 'active',
  display_order INT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE modules ADD COLUMN IF NOT EXISTS goal TEXT NOT NULL DEFAULT '';
ALTER TABLE modules ADD COLUMN IF NOT EXISTS plane TEXT NOT NULL DEFAULT 'intelligence';
ALTER TABLE modules ADD COLUMN IF NOT EXISTS version TEXT NOT NULL DEFAULT 'v1';
ALTER TABLE modules ADD COLUMN IF NOT EXISTS status TEXT NOT NULL DEFAULT 'active';
ALTER TABLE modules ADD COLUMN IF NOT EXISTS display_order INT NOT NULL DEFAULT 100;
ALTER TABLE modules ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW();

CREATE TABLE IF NOT EXISTS module_tooling (
  id BIGSERIAL PRIMARY KEY,
  module_id TEXT NOT NULL REFERENCES modules(id) ON DELETE CASCADE,
  tool_name TEXT NOT NULL,
  tool_type TEXT NOT NULL CHECK (tool_type IN ('free', 'oss', 'paid_optional')),
  score INT NOT NULL CHECK (score BETWEEN 0 AND 100),
  capabilities JSONB NOT NULL DEFAULT '[]'::jsonb
);

CREATE TABLE IF NOT EXISTS module_dependencies (
  id BIGSERIAL PRIMARY KEY,
  module_id TEXT NOT NULL REFERENCES modules(id) ON DELETE CASCADE,
  depends_on_module_id TEXT NOT NULL REFERENCES modules(id) ON DELETE CASCADE,
  dependency_type TEXT NOT NULL DEFAULT 'data',
  UNIQUE (module_id, depends_on_module_id)
);

CREATE TABLE IF NOT EXISTS tenant_module_settings (
  id BIGSERIAL PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  module_id TEXT NOT NULL REFERENCES modules(id) ON DELETE CASCADE,
  enabled BOOLEAN NOT NULL DEFAULT TRUE,
  rollout_stage TEXT NOT NULL DEFAULT 'general',
  quota_limit BIGINT,
  config JSONB NOT NULL DEFAULT '{}'::jsonb,
  UNIQUE (tenant_id, module_id)
);

CREATE TABLE IF NOT EXISTS module_connectors (
  id BIGSERIAL PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  module_id TEXT NOT NULL REFERENCES modules(id) ON DELETE CASCADE,
  connector_name TEXT NOT NULL,
  connector_type TEXT NOT NULL,
  is_enabled BOOLEAN NOT NULL DEFAULT TRUE,
  secrets_ref TEXT,
  config JSONB NOT NULL DEFAULT '{}'::jsonb,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (tenant_id, module_id, connector_name)
);

CREATE TABLE IF NOT EXISTS module_runs (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  module_id TEXT NOT NULL REFERENCES modules(id),
  trigger_type TEXT NOT NULL,
  input_payload JSONB NOT NULL,
  output_payload JSONB,
  score NUMERIC(5,2),
  status TEXT NOT NULL,
  rollout_stage TEXT,
  blocked_reason TEXT,
  approved_by TEXT,
  started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  completed_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS module_metrics (
  id BIGSERIAL PRIMARY KEY,
  run_id UUID NOT NULL REFERENCES module_runs(id) ON DELETE CASCADE,
  metric_key TEXT NOT NULL,
  metric_value NUMERIC,
  metric_meta JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS module_events (
  id BIGSERIAL PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  module_id TEXT REFERENCES modules(id),
  event_type TEXT NOT NULL,
  payload JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS tenant_billing_usage (
  id BIGSERIAL PRIMARY KEY,
  tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  module_id TEXT NOT NULL REFERENCES modules(id),
  usage_date DATE NOT NULL,
  runs_count BIGINT NOT NULL DEFAULT 0,
  tokens_in BIGINT NOT NULL DEFAULT 0,
  tokens_out BIGINT NOT NULL DEFAULT 0,
  cost_estimate NUMERIC(12,4) NOT NULL DEFAULT 0,
  UNIQUE (tenant_id, module_id, usage_date)
);

CREATE INDEX IF NOT EXISTS idx_module_runs_tenant_started_at
  ON module_runs (tenant_id, started_at DESC);

CREATE INDEX IF NOT EXISTS idx_module_events_tenant_created_at
  ON module_events (tenant_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_tenant_module_settings_enabled
  ON tenant_module_settings (tenant_id, enabled);

-- Seed module registry (1-31) without overwriting existing rows.
INSERT INTO modules (id, name, category, goal, plane, version, status, display_order)
VALUES
  ('seo-ai', 'SEO-AI', 'Search Intelligence', 'Keyword research and SERP optimization', 'intelligence', 'v1', 'active', 1),
  ('geo', 'GEO', 'Search Intelligence', 'Generative engine visibility optimization', 'intelligence', 'v1', 'active', 2),
  ('aio-2', 'AIO-2', 'Search Intelligence', 'Agentic intelligence optimization', 'intelligence', 'v1', 'active', 3),
  ('llmo', 'LLMO', 'Search Intelligence', 'LLM workflow optimization', 'intelligence', 'v1', 'active', 4),
  ('sageo', 'SAGEO', 'Search Intelligence', 'Search-augmented generative SEO', 'intelligence', 'v1', 'active', 5),
  ('vso', 'VSO', 'Search Intelligence', 'Voice search optimization', 'experience', 'v1', 'active', 6),
  ('sxo', 'SXO', 'Search Intelligence', 'Search experience optimization', 'experience', 'v1', 'active', 7),
  ('gxo', 'GXO', 'Search Intelligence', 'Generative experience optimization', 'experience', 'v1', 'active', 8),
  ('entity-first-seo', 'Entity-First SEO', 'Search Intelligence', 'Entity-centric optimization', 'intelligence', 'v1', 'active', 9),
  ('peao', 'PEAO', 'Search Intelligence', 'Predictive algorithm optimization', 'data', 'v1', 'active', 10),
  ('msvo', 'MSVO', 'Search Intelligence', 'Multi-surface visibility optimization', 'data', 'v1', 'active', 11),
  ('daeo', 'DAEO', 'Search Intelligence', 'Decentralized answer engine optimization', 'intelligence', 'v1', 'active', 12),
  ('cxao', 'CXAO', 'Experience Optimization', 'Conversational answer optimization', 'experience', 'v1', 'active', 13),
  ('eeat-suite', 'E-E-A-T Optimization Suite', 'Experience Optimization', 'Trust and authority optimization', 'governance', 'v1', 'active', 14),
  ('autonomous-agent-engine', 'Autonomous Agent Orchestration Engine', 'Experience Optimization', 'Multi-agent orchestration runtime', 'orchestration', 'v1', 'active', 15),
  ('programmatic-seo-engine', 'Programmatic SEO Engine', 'Experience Optimization', 'Programmatic page generation and publishing', 'experience', 'v1', 'active', 16),
  ('seo-ab-testing', 'SEO A/B Testing Framework', 'Experience Optimization', 'Controlled SEO experimentation', 'experiment', 'v1', 'active', 17),
  ('ecommerce-seo-suite', 'Ecommerce SEO Suite', 'Experience Optimization', 'Product and category SEO optimization', 'experience', 'v1', 'active', 18),
  ('revenue-attribution-intelligence', 'Revenue Attribution Intelligence', 'Growth and Governance', 'Attribution and revenue intelligence', 'data', 'v1', 'active', 19),
  ('growth-playbooks-automation', 'Growth Playbooks Automation', 'Growth and Governance', 'Automated growth workflows', 'orchestration', 'v1', 'active', 20),
  ('trust-risk-governance', 'Trust and Risk Governance', 'Growth and Governance', 'Policy, risk, and governance controls', 'governance', 'v1', 'active', 21),
  ('multi-channel-activation-loop', 'Multi-Channel Activation Loop', 'Growth and Governance', 'Activation orchestration across channels', 'orchestration', 'v1', 'active', 22),
  ('autonomous-link-building-system', 'Autonomous Link Building System', 'Expansion Modules', 'Automated link prospecting and workflows', 'orchestration', 'v1', 'active', 23),
  ('international-multilingual-seo', 'International and Multilingual SEO', 'Expansion Modules', 'Multilingual and regional SEO workflows', 'experience', 'v1', 'active', 24),
  ('site-migration-seo-manager', 'Site Migration SEO Manager', 'Expansion Modules', 'SEO-safe migration control', 'orchestration', 'v1', 'active', 25),
  ('video-seo-module', 'Video SEO Module', 'Expansion Modules', 'Video metadata and discoverability optimization', 'experience', 'v1', 'active', 26),
  ('local-seo-suite', 'Local SEO Suite', 'Expansion Modules', 'Local intent and map visibility optimization', 'experience', 'v1', 'active', 27),
  ('news-seo-google-discover', 'News SEO and Google Discover', 'SaaS Platform Modules', 'News freshness and discover optimization', 'experience', 'v1', 'active', 28),
  ('analytics-reporting-intelligence', 'Analytics Reporting and Intelligence', 'SaaS Platform Modules', 'Central analytics and anomaly intelligence', 'data', 'v1', 'active', 29),
  ('agency-multi-tenant-platform', 'Agency and Multi-Tenant Platform', 'SaaS Platform Modules', 'Tenant isolation and agency operations', 'governance', 'v1', 'active', 30),
  ('integrations-automation-layer', 'Integrations and Automation Layer', 'SaaS Platform Modules', 'Cross-module connector and job automation', 'orchestration', 'v1', 'active', 31)
ON CONFLICT (id) DO NOTHING;

COMMIT;
