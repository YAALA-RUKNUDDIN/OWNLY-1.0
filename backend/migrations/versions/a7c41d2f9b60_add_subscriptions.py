"""add subscriptions

Revision ID: a7c41d2f9b60
Revises: 5c72b958547c
Create Date: 2026-09-23

Phase 2 — plan entitlements: one row per user (created lazily by the service,
so no data backfill is needed for existing accounts).
"""
from alembic import op
import sqlalchemy as sa

from app.core.database import GUID


# revision identifiers, used by Alembic.
revision = 'a7c41d2f9b60'
down_revision = '5c72b958547c'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('subscriptions',
    sa.Column('id', GUID(), nullable=False),
    sa.Column('user_id', GUID(), nullable=False),
    sa.Column('tier', sa.Enum('free', 'premium', name='plan_tier'), nullable=False),
    sa.Column('status', sa.Enum('active', 'canceled', 'expired', name='subscription_status'), nullable=False),
    sa.Column('provider', sa.String(length=40), nullable=False),
    sa.Column('provider_ref', sa.String(length=255), nullable=True),
    sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('canceled_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_subscriptions_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_subscriptions'))
    )
    op.create_index(op.f('ix_subscriptions_user_id'), 'subscriptions', ['user_id'], unique=True)


def downgrade() -> None:
    op.drop_index(op.f('ix_subscriptions_user_id'), table_name='subscriptions')
    op.drop_table('subscriptions')
    # PostgreSQL keeps native ENUM types after their owning tables are dropped;
    # drop them so upgrade → downgrade → upgrade stays idempotent (D-002).
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        for enum_name in ("plan_tier", "subscription_status"):
            op.execute(sa.text(f"DROP TYPE IF EXISTS {enum_name}"))
