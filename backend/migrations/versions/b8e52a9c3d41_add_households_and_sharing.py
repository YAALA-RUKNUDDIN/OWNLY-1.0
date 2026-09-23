"""add households and sharing

Revision ID: b8e52a9c3d41
Revises: a7c41d2f9b60
Create Date: 2026-09-24

Phase 8 — Household and Family Sharing:
- households table
- household_members table
- household_invites table
- products.household_id column + index + foreign key
"""
from alembic import op
import sqlalchemy as sa

from app.core.database import GUID


# revision identifiers, used by Alembic.
revision = 'b8e52a9c3d41'
down_revision = 'a7c41d2f9b60'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Create households table
    op.create_table(
        'households',
        sa.Column('id', GUID(), nullable=False),
        sa.Column('name', sa.String(length=120), nullable=False),
        sa.Column('created_by_user_id', GUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id'], name=op.f('fk_households_created_by_user_id_users'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_households'))
    )
    op.create_index(op.f('ix_households_created_by_user_id'), 'households', ['created_by_user_id'], unique=False)

    # 2. Create household_members table
    op.create_table(
        'household_members',
        sa.Column('id', GUID(), nullable=False),
        sa.Column('household_id', GUID(), nullable=False),
        sa.Column('user_id', GUID(), nullable=False),
        sa.Column('role', sa.Enum('admin', 'member', 'viewer', name='household_role'), nullable=False),
        sa.Column('joined_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.ForeignKeyConstraint(['household_id'], ['households.id'], name=op.f('fk_household_members_household_id_households'), ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_household_members_user_id_users'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_household_members')),
        sa.UniqueConstraint('household_id', 'user_id', name='uq_household_member')
    )
    op.create_index(op.f('ix_household_members_household_id'), 'household_members', ['household_id'], unique=False)
    op.create_index(op.f('ix_household_members_user_id'), 'household_members', ['user_id'], unique=False)

    # 3. Create household_invites table
    op.create_table(
        'household_invites',
        sa.Column('id', GUID(), nullable=False),
        sa.Column('household_id', GUID(), nullable=False),
        sa.Column('inviter_user_id', GUID(), nullable=False),
        sa.Column('invite_code', sa.String(length=32), nullable=False),
        sa.Column('role', sa.Enum('admin', 'member', 'viewer', name='household_role'), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('accepted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.ForeignKeyConstraint(['household_id'], ['households.id'], name=op.f('fk_household_invites_household_id_households'), ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['inviter_user_id'], ['users.id'], name=op.f('fk_household_invites_inviter_user_id_users'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_household_invites'))
    )
    op.create_index(op.f('ix_household_invites_household_id'), 'household_invites', ['household_id'], unique=False)
    op.create_index(op.f('ix_household_invites_invite_code'), 'household_invites', ['invite_code'], unique=True)

    # 4. Add household_id to products
    op.add_column('products', sa.Column('household_id', GUID(), nullable=True))
    op.create_foreign_key(
        op.f('fk_products_household_id_households'),
        'products',
        'households',
        ['household_id'],
        ['id'],
        ondelete='SET NULL'
    )
    op.create_index(op.f('ix_products_household_id'), 'products', ['household_id'], unique=False)


def downgrade() -> None:
    # 1. Remove column and constraints from products
    op.drop_index(op.f('ix_products_household_id'), table_name='products')
    op.drop_constraint(op.f('fk_products_household_id_households'), 'products', type_='foreignkey')
    op.drop_column('products', 'household_id')

    # 2. Drop household_invites table
    op.drop_index(op.f('ix_household_invites_invite_code'), table_name='household_invites')
    op.drop_index(op.f('ix_household_invites_household_id'), table_name='household_invites')
    op.drop_table('household_invites')

    # 3. Drop household_members table
    op.drop_index(op.f('ix_household_members_user_id'), table_name='household_members')
    op.drop_index(op.f('ix_household_members_household_id'), table_name='household_members')
    op.drop_table('household_members')

    # 4. Drop households table
    op.drop_index(op.f('ix_households_created_by_user_id'), table_name='households')
    op.drop_table('households')

    # PostgreSQL keeps native ENUM types; clean up
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(sa.text("DROP TYPE IF EXISTS household_role"))
