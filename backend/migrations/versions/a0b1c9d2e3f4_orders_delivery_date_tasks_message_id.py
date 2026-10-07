"""orders delivery_date and tasks message_id

Revision ID: a0b1c9d2e3f4
Revises: a0b1c2d3e4f5
Create Date: 2026-10-05 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'a0b1c9d2e3f4'
down_revision: Union[str, None] = 'a0b1c2d3e4f5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('orders', sa.Column('delivery_date', sa.Date(), nullable=True))
    with op.batch_alter_table('tasks', schema=None) as batch_op:
        batch_op.add_column(sa.Column('message_id', sa.Integer(), nullable=True))
        batch_op.create_index('ix_tasks_message_id', ['message_id'])
        batch_op.create_foreign_key('fk_tasks_message_id_messages', 'messages', ['message_id'], ['id'])


def downgrade() -> None:
    with op.batch_alter_table('tasks', schema=None) as batch_op:
        batch_op.drop_constraint('fk_tasks_message_id_messages', type_='foreignkey')
        batch_op.drop_index('ix_tasks_message_id')
        batch_op.drop_column('message_id')
    op.drop_column('orders', 'delivery_date')
