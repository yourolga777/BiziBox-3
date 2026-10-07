"""orders with items and comments

Revision ID: f7a8b9c0d1e2
Revises: f6a7b8c9d0e1
Create Date: 2026-09-24 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'f7a8b9c0d1e2'
down_revision: Union[str, None] = 'f6a7b8c9d0e1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'orders',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('owner_id', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('order_number', sa.String(length=50), nullable=True),
        sa.Column('contact_id', sa.Integer(), nullable=False),
        sa.Column('message_id', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('total', sa.Float(), nullable=True),
        sa.Column('delivery_address', sa.Text(), nullable=True),
        sa.Column('payment_method', sa.String(length=50), nullable=True),
        sa.Column('paid', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['contact_id'], ['contacts.id']),
        sa.ForeignKeyConstraint(['message_id'], ['messages.id']),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id']),
    )
    op.create_index('uq_orders_owner_order_number', 'orders', ['owner_id', 'order_number'], unique=True)
    op.create_index('ix_orders_owner_created', 'orders', ['owner_id', 'created_at'])
    op.create_index(op.f('ix_orders_status'), 'orders', ['status'])
    op.create_index(op.f('ix_orders_owner_id'), 'orders', ['owner_id'])
    op.create_index(op.f('ix_orders_contact_id'), 'orders', ['contact_id'])
    op.create_index(op.f('ix_orders_message_id'), 'orders', ['message_id'])
    op.create_index(op.f('ix_orders_deleted_at'), 'orders', ['deleted_at'])

    op.create_table(
        'order_items',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('owner_id', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('order_id', sa.Integer(), nullable=False),
        # Без FK на products: таблица продуктов появится в модуле 2; FK
        # добавим отдельной миграцией.
        sa.Column('product_id', sa.Integer(), nullable=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('quantity', sa.Float(), nullable=True),
        sa.Column('price', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id']),
    )
    op.create_index(op.f('ix_order_items_order_id'), 'order_items', ['order_id'])
    op.create_index(op.f('ix_order_items_owner_id'), 'order_items', ['owner_id'])
    op.create_index(op.f('ix_order_items_product_id'), 'order_items', ['product_id'])

    op.create_table(
        'order_comments',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('owner_id', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('order_id', sa.Integer(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id']),
    )
    op.create_index(op.f('ix_order_comments_order_id'), 'order_comments', ['order_id'])
    op.create_index(op.f('ix_order_comments_owner_id'), 'order_comments', ['owner_id'])


def downgrade() -> None:
    op.drop_table('order_comments')
    op.drop_table('order_items')
    op.drop_table('orders')