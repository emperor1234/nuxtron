-- Tenant-scoped fallback RLS for ai_embeddings when Supabase auth is unavailable.

BEGIN;

DO $outer$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM information_schema.schemata WHERE schema_name = 'auth') THEN
    EXECUTE $sql$
      CREATE OR REPLACE FUNCTION public.get_current_tenant_id() RETURNS UUID AS $func$
        SELECT current_setting('app.current_tenant_id', true)::UUID;
      $func$ LANGUAGE SQL STABLE
    $sql$;

    IF NOT EXISTS (
      SELECT 1
      FROM pg_policies
      WHERE schemaname = 'public'
        AND tablename = 'ai_embeddings'
        AND policyname = 'ai_embeddings_select_tenant'
    ) THEN
      EXECUTE 'CREATE POLICY ai_embeddings_select_tenant ON ai_embeddings FOR SELECT USING (tenant_id = public.get_current_tenant_id())';
    END IF;

    IF NOT EXISTS (
      SELECT 1
      FROM pg_policies
      WHERE schemaname = 'public'
        AND tablename = 'ai_embeddings'
        AND policyname = 'ai_embeddings_insert_tenant'
    ) THEN
      EXECUTE 'CREATE POLICY ai_embeddings_insert_tenant ON ai_embeddings FOR INSERT WITH CHECK (tenant_id = public.get_current_tenant_id())';
    END IF;

    IF NOT EXISTS (
      SELECT 1
      FROM pg_policies
      WHERE schemaname = 'public'
        AND tablename = 'ai_embeddings'
        AND policyname = 'ai_embeddings_update_tenant'
    ) THEN
      EXECUTE 'CREATE POLICY ai_embeddings_update_tenant ON ai_embeddings FOR UPDATE USING (tenant_id = public.get_current_tenant_id()) WITH CHECK (tenant_id = public.get_current_tenant_id())';
    END IF;

    IF NOT EXISTS (
      SELECT 1
      FROM pg_policies
      WHERE schemaname = 'public'
        AND tablename = 'ai_embeddings'
        AND policyname = 'ai_embeddings_delete_tenant'
    ) THEN
      EXECUTE 'CREATE POLICY ai_embeddings_delete_tenant ON ai_embeddings FOR DELETE USING (tenant_id = public.get_current_tenant_id())';
    END IF;
  END IF;
END $outer$;

COMMIT;