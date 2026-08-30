"""persist Stripe billing state

Revision ID: 9d2f6f1a3b40
Revises: fe7ee0840540
Create Date: 2026-08-29
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = '9d2f6f1a3b40'
down_revision: str | None = 'fe7ee0840540'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'billing_subscriptions',
        sa.Column('stripe_subscription_id', sa.String(length=255), nullable=False),
        sa.Column('stripe_customer_id', sa.String(length=255), nullable=False),
        sa.Column('stripe_checkout_session_id', sa.String(length=255), nullable=False),
        sa.Column('plan_id', sa.String(length=40), nullable=False),
        sa.Column('billing_cycle', sa.String(length=20), nullable=False),
        sa.Column('status', sa.String(length=40), nullable=False),
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenant_profiles.tenant_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('stripe_checkout_session_id'),
        sa.UniqueConstraint('stripe_subscription_id'),
    )
    op.create_index(
        'ix_billing_subscriptions_stripe_customer_id',
        'billing_subscriptions',
        ['stripe_customer_id'],
    )
    op.create_index(
        'ix_billing_subscriptions_tenant_id',
        'billing_subscriptions',
        ['tenant_id'],
    )
    op.create_index(
        'ix_billing_subscriptions_tenant_status',
        'billing_subscriptions',
        ['tenant_id', 'status'],
    )

    op.create_table(
        'billing_credit_purchases',
        sa.Column('request_id', sa.String(length=120), nullable=False),
        sa.Column('stripe_checkout_session_id', sa.String(length=255), nullable=True),
        sa.Column('stripe_payment_intent_id', sa.String(length=255), nullable=True),
        sa.Column('credits', sa.Integer(), nullable=False),
        sa.Column('amount_cents', sa.Integer(), nullable=False),
        sa.Column('currency', sa.String(length=8), nullable=False),
        sa.Column('status', sa.String(length=40), nullable=False),
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenant_profiles.tenant_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('request_id'),
        sa.UniqueConstraint('stripe_checkout_session_id'),
    )
    op.create_index(
        'ix_billing_credit_purchases_tenant_id',
        'billing_credit_purchases',
        ['tenant_id'],
    )
    op.create_index(
        'ix_billing_credit_purchases_tenant_status',
        'billing_credit_purchases',
        ['tenant_id', 'status'],
    )

    op.create_table(
        'billing_credit_ledger',
        sa.Column('amount', sa.Integer(), nullable=False),
        sa.Column('reason', sa.String(length=80), nullable=False),
        sa.Column('stripe_checkout_session_id', sa.String(length=255), nullable=True),
        sa.Column('stripe_invoice_id', sa.String(length=255), nullable=True),
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenant_profiles.tenant_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('stripe_checkout_session_id'),
        sa.UniqueConstraint('stripe_invoice_id'),
    )
    op.create_index(
        'ix_billing_credit_ledger_tenant_id',
        'billing_credit_ledger',
        ['tenant_id'],
    )

    op.create_table(
        'stripe_webhook_events',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('event_id', sa.String(length=255), nullable=False),
        sa.Column('event_type', sa.String(length=120), nullable=False),
        sa.Column('tenant_id', sa.String(length=255), nullable=False),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('event_id'),
    )
    op.create_index(
        'ix_stripe_webhook_events_event_id',
        'stripe_webhook_events',
        ['event_id'],
    )


def downgrade() -> None:
    op.drop_index('ix_stripe_webhook_events_event_id', table_name='stripe_webhook_events')
    op.drop_table('stripe_webhook_events')
    op.drop_index('ix_billing_credit_ledger_tenant_id', table_name='billing_credit_ledger')
    op.drop_table('billing_credit_ledger')
    op.drop_index(
        'ix_billing_credit_purchases_tenant_status',
        table_name='billing_credit_purchases',
    )
    op.drop_index(
        'ix_billing_credit_purchases_tenant_id',
        table_name='billing_credit_purchases',
    )
    op.drop_table('billing_credit_purchases')
    op.drop_index(
        'ix_billing_subscriptions_tenant_status',
        table_name='billing_subscriptions',
    )
    op.drop_index(
        'ix_billing_subscriptions_tenant_id',
        table_name='billing_subscriptions',
    )
    op.drop_index(
        'ix_billing_subscriptions_stripe_customer_id',
        table_name='billing_subscriptions',
    )
    op.drop_table('billing_subscriptions')
