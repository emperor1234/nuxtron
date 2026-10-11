-- PostgreSQL pgvector baseline for tenant-scoped AI embeddings.

BEGIN;

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS ai_embeddings (
  id BIGSERIAL PRIMARY KEY,
  tenant_id UUID NOT NULL,
  user_id UUID,
  content TEXT NOT NULL DEFAULT '',
  embedding VECTOR(1536) NOT NULL,
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  source TEXT NOT NULL DEFAULT 'unknown',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ai_embeddings_tenant_created_at
  ON ai_embeddings (tenant_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_ai_embeddings_embedding_hnsw
  ON ai_embeddings USING hnsw (embedding vector_cosine_ops);

ALTER TABLE ai_embeddings ENABLE ROW LEVEL SECURITY;

CREATE OR REPLACE FUNCTION public.get_current_tenant_id() RETURNS UUID AS $$
  SELECT NULLIF(current_setting('app.current_tenant_id', true), '')::UUID;
$$ LANGUAGE SQL STABLE;

DROP POLICY IF EXISTS ai_embeddings_select_tenant ON ai_embeddings;
CREATE POLICY ai_embeddings_select_tenant
  ON ai_embeddings
  FOR SELECT
  USING (tenant_id = public.get_current_tenant_id());

DROP POLICY IF EXISTS ai_embeddings_insert_tenant ON ai_embeddings;
CREATE POLICY ai_embeddings_insert_tenant
  ON ai_embeddings
  FOR INSERT
  WITH CHECK (tenant_id = public.get_current_tenant_id());

DROP POLICY IF EXISTS ai_embeddings_update_tenant ON ai_embeddings;
CREATE POLICY ai_embeddings_update_tenant
  ON ai_embeddings
  FOR UPDATE
  USING (tenant_id = public.get_current_tenant_id())
  WITH CHECK (tenant_id = public.get_current_tenant_id());

DROP POLICY IF EXISTS ai_embeddings_delete_tenant ON ai_embeddings;
CREATE POLICY ai_embeddings_delete_tenant
  ON ai_embeddings
  FOR DELETE
  USING (tenant_id = public.get_current_tenant_id());

COMMIT;
