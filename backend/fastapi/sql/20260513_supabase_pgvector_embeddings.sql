-- Supabase pgvector baseline for AI embeddings (idempotent).
-- Intended for PostgreSQL 15+ and Supabase-managed Postgres.

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

-- Supabase-aware RLS policies: only create auth.uid() policies when auth schema exists.
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM information_schema.schemata WHERE schema_name = 'auth') THEN
    IF NOT EXISTS (
      SELECT 1
      FROM pg_policies
      WHERE schemaname = 'public'
        AND tablename = 'ai_embeddings'
        AND policyname = 'ai_embeddings_select_own'
    ) THEN
      EXECUTE 'CREATE POLICY ai_embeddings_select_own ON ai_embeddings FOR SELECT USING (auth.uid() = user_id)';
    END IF;

    IF NOT EXISTS (
      SELECT 1
      FROM pg_policies
      WHERE schemaname = 'public'
        AND tablename = 'ai_embeddings'
        AND policyname = 'ai_embeddings_insert_own'
    ) THEN
      EXECUTE 'CREATE POLICY ai_embeddings_insert_own ON ai_embeddings FOR INSERT WITH CHECK (auth.uid() = user_id)';
    END IF;

    IF NOT EXISTS (
      SELECT 1
      FROM pg_policies
      WHERE schemaname = 'public'
        AND tablename = 'ai_embeddings'
        AND policyname = 'ai_embeddings_update_own'
    ) THEN
      EXECUTE 'CREATE POLICY ai_embeddings_update_own ON ai_embeddings FOR UPDATE USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id)';
    END IF;

    IF NOT EXISTS (
      SELECT 1
      FROM pg_policies
      WHERE schemaname = 'public'
        AND tablename = 'ai_embeddings'
        AND policyname = 'ai_embeddings_delete_own'
    ) THEN
      EXECUTE 'CREATE POLICY ai_embeddings_delete_own ON ai_embeddings FOR DELETE USING (auth.uid() = user_id)';
    END IF;
  END IF;
END $$;

COMMIT;
