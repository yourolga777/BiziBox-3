"""products and suppliers tables, FK on order_items.product_id

Revision ID: a0b1c2d3e4f5
Revises: f7a8b9c0d1e2
Create Date: 2026-09-25 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'a0b1c2d3e4f5'
down_revision: Union[str, None] = 'f7a8b9c0d1e2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'suppliers',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('owner_id', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('contact_id', sa.Integer(), nullable=False),
        sa.Column('company_name', sa.String(length=255), nullable=True),
        sa.Column('inn', sa.String(length=20), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['contact_id'], ['contacts.id']),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id']),
    )
    op.create_index('uq_suppliers_owner_contact', 'suppliers', ['owner_id', 'contact_id'], unique=True)
    op.create_index('ix_suppliers_owner_id', 'suppliers', ['owner_id'])
    op.create_index('ix_suppliers_contact_id', 'suppliers', ['contact_id'])
    op.create_index('ix_suppliers_deleted_at', 'suppliers', ['deleted_at'])

    op.create_table(
        'products',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('owner_id', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('sku', sa.String(length=100), nullable=True),
        sa.Column('price', sa.Float(), nullable=True),
        sa.Column('purchase_price', sa.Float(), nullable=True),
        sa.Column('stock', sa.Float(), nullable=True),
        sa.Column('unit', sa.String(length=20), nullable=True, server_default='шт'),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('supplier_id', sa.Integer(), nullable=True),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['supplier_id'], ['suppliers.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id']),
    )
    op.create_index('uq_products_owner_sku', 'products', ['owner_id', 'sku'], unique=True,
                    sqlite_where=sa.text('sku IS NOT NULL'))
    op.create_index('ix_products_owner_id', 'products', ['owner_id'])
    op.create_index('ix_products_supplier_id', 'products', ['supplier_id'])
    op.create_index('ix_products_deleted_at', 'products', ['deleted_at'])

    with op.batch_alter_table('order_items', schema=None) as batch_op:
        batch_op.create_foreign_key(
            'fk_order_items_product_id',
            'products',
            ['product_id'],
            ['id'],
            ondelete='SET NULL',
        )


def downgrade() -> None:
    with op.batch_alter_table('order_items', schema=None) as batch_op:
        batch_op.drop_constraint('fk_order_items_product_id', type_='foreignkey')

    op.drop_table('products')
    op.drop_table('suppliers')
