"""add warranty claims and claim lifecycle

Revision ID: c9f61b8e4a22
Revises: b8e52a9c3d41
Create Date: 2026-09-24

Phase 9 — Warranty Claim Assistant & Brand Support Dossier:
- warranty_claims table with foreign keys, indices, and enum status
"""
from alembic import op
import sqlalchemy as sa

from app.core.database import GUID


# revision identifiers, used by Alembic.
revision = 'c9f61b8e4a22'
down_revision = 'b8e52a9c3d41'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Create warranty_claims table
    op.create_table(
        'warranty_claims',
        sa.Column('id', GUID(), nullable=False),
        sa.Column('product_id', GUID(), nullable=False),
        sa.Column('user_id', GUID(), nullable=False),
        sa.Column('warranty_id', GUID(), nullable=True),
        sa.Column('claim_reference', sa.String(length=100), nullable=True),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('issue_description', sa.Text(), nullable=False),
        sa.Column(
            'status',
            sa.Enum(
                'draft', 'submitted', 'in_review', 'approved', 'repaired', 'replaced', 'rejected', 'closed',
                name='claim_status',
            ),
            nullable=False,
            server_default='draft',
        ),
        sa.Column('incident_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('resolution_notes', sa.Text(), nullable=True),
        sa.Column('claim_cost_covered', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('contact_email', sa.String(length=255), nullable=True),
        sa.Column('contact_phone', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], name=op.f('fk_warranty_claims_product_id_products'), ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_warranty_claims_user_id_users'), ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['warranty_id'], ['warranties.id'], name=op.f('fk_warranty_claims_warranty_id_warranties'), ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_warranty_claims'))
    )
    op.create_index(op.f('ix_warranty_claims_product_id'), 'warranty_claims', ['product_id'], unique=False)
    op.create_index(op.f('ix_warranty_claims_user_id'), 'warranty_claims', ['user_id'], unique=False)
    op.create_index(op.f('ix_warranty_claims_status'), 'warranty_claims', ['status'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_warranty_claims_status'), table_name='warranty_claims')
    op.drop_index(op.f('ix_warranty_claims_user_id'), table_name='warranty_claims')
    op.drop_index(op.f('ix_warranty_claims_product_id'), table_name='warranty_claims')
    op.drop_table('warranty_claims')
    # Drop enum if on postgres
    bind = op.get_bind()
    if bind.engine.name == 'postgresql':
        sa.Enum(name='claim_status').drop(bind, checkfirst=True)
