"""enforce organization RLS for intelligence and platform tables

Revision ID: 6c3e8f1a2b77
Revises: 4a1c7e9b2d10
"""

from collections.abc import Sequence

from alembic import op

revision: str = "6c3e8f1a2b77"
down_revision: str | None = "4a1c7e9b2d10"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_INTELLIGENCE_TABLES = (
    "intel_targets",
    "intel_social_posts",
    "intel_post_metrics_history",
    "intel_ads",
    "intel_website_snapshots",
    "intel_seo_rankings",
    "intel_trends",
    "intel_viral_registry",
    "intel_roi_predictions",
    "intel_reports",
    "intel_content_context",
)

_PLATFORM_TABLES = (
    "oauth_tokens",
    "platform_accounts",
    "scheduled_posts",
    "post_metrics",
    "platform_messages",
)


def _apply_policy(table: str, column: str, setting: str) -> None:
    policy = f"nuxtron_rls_{table}"
    op.execute(
        f"""
        DO $$
        BEGIN
            IF to_regclass('public.{table}') IS NOT NULL THEN
                EXECUTE 'ALTER TABLE public.{table} ENABLE ROW LEVEL SECURITY';
                EXECUTE 'ALTER TABLE public.{table} FORCE ROW LEVEL SECURITY';
                IF NOT EXISTS (
                    SELECT 1 FROM pg_policies
                    WHERE schemaname = 'public' AND tablename = '{table}' AND policyname = '{policy}'
                ) THEN
                    EXECUTE $policy$
                        CREATE POLICY {policy} ON public.{table}
                        FOR ALL
                        USING ({column} = NULLIF(current_setting('{setting}', true), '')::uuid)
                        WITH CHECK ({column} = NULLIF(current_setting('{setting}', true), '')::uuid)
                    $policy$;
                END IF;
            END IF;
        END $$;
        """
    )


def upgrade() -> None:
    for table in _INTELLIGENCE_TABLES:
        _apply_policy(table, "org_id", "app.current_org_id")
    for table in _PLATFORM_TABLES:
        _apply_policy(table, "tenant_id", "app.current_tenant_id")


def downgrade() -> None:
    for table in (*_INTELLIGENCE_TABLES, *_PLATFORM_TABLES):
        policy = f"nuxtron_rls_{table}"
        op.execute(
            f"""
            DO $$
            BEGIN
                IF to_regclass('public.{table}') IS NOT NULL THEN
                    EXECUTE 'DROP POLICY IF EXISTS {policy} ON public.{table}';
                    EXECUTE 'ALTER TABLE public.{table} NO FORCE ROW LEVEL SECURITY';
                END IF;
            END $$;
            """
        )
