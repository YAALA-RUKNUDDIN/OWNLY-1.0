"""add resale and disposal fields to products

Revision ID: d0a71c8e5f33
Revises: c9f61b8e4a22
Create Date: 2026-09-24

Phase 10 — Resale & Disposal Assistant (Lifecycle Exit & Net Ownership Cost):
- condition, resale_price, resale_date, resale_platform, resale_notes on products table
- support for recycled and donated product statuses
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd0a71c8e5f33'
down_revision = 'c9f61b8e4a22'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Add resale & disposal columns to products
    op.add_column('products', sa.Column('condition', sa.String(length=30), server_default='good', nullable=False))
    op.add_column('products', sa.Column('resale_price', sa.Numeric(precision=12, scale=2), nullable=True))
    op.add_column('products', sa.Column('resale_date', sa.DateTime(timezone=True), nullable=True))
    op.add_column('products', sa.Column('resale_platform', sa.String(length=100), nullable=True))
    op.add_column('products', sa.Column('resale_notes', sa.Text(), nullable=True))

    bind = op.get_bind()
    if bind.engine.name == 'postgresql':
        op.execute("ALTER TYPE product_status ADD VALUE IF NOT EXISTS 'recycled'")
        op.execute("ALTER TYPE product_status ADD VALUE IF NOT EXISTS 'donated'")


def downgrade() -> None:
    op.drop_column('products', 'resale_notes')
    op.drop_column('products', 'resale_platform')
    op.drop_column('products', 'resale_date')
    op.drop_column('products', 'resale_price')
    op.drop_column('products', 'condition')
