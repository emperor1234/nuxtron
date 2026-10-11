"""Manage social profile schema and forced organization isolation.

Revision ID: 8b41d69ce205
Revises: 7e2f4c9a1b66
"""
from alembic import op

revision = '8b41d69ce205'
down_revision = '7e2f4c9a1b66'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Existing installations may already have the runtime-created table.
    op.execute('''
        CREATE TABLE IF NOT EXISTS public.social_brand_profiles_store (
            tenant_id TEXT PRIMARY KEY,
            profile JSONB NOT NULL,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    ''')
    op.execute('ALTER TABLE public.social_brand_profiles_store ENABLE ROW LEVEL SECURITY')
    op.execute('ALTER TABLE public.social_brand_profiles_store FORCE ROW LEVEL SECURITY')
    op.execute('''
        CREATE POLICY nuxtron_social_profiles_organization
        ON public.social_brand_profiles_store FOR ALL
        USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), ''))
        WITH CHECK (
            tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')
            AND profile->>'tenant_id' = tenant_id
        )
    ''')


def downgrade() -> None:
    # Preserve customer profiles: this table may predate the Alembic revision.
    op.execute('DROP POLICY IF EXISTS nuxtron_social_profiles_organization ON public.social_brand_profiles_store')
    op.execute('ALTER TABLE public.social_brand_profiles_store NO FORCE ROW LEVEL SECURITY')
    op.execute('ALTER TABLE public.social_brand_profiles_store DISABLE ROW LEVEL SECURITY')
