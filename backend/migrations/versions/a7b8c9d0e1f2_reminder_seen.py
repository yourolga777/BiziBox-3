"""task reminder_seen_at + calendar_event last_reminded_at/reminder_seen_at

Revision ID: a7b8c9d0e1f2
Revises: f1b2c3d4e5f6
Create Date: 2026-09-17 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'a7b8c9d0e1f2'
down_revision: Union[str, None] = 'f1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('tasks', schema=None) as batch_op:
        batch_op.add_column(sa.Column('reminder_seen_at', sa.DateTime(), nullable=True))

    with op.batch_alter_table('calendar_events', schema=None) as batch_op:
        batch_op.add_column(sa.Column('last_reminded_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('reminder_seen_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('calendar_events', schema=None) as batch_op:
        batch_op.drop_column('reminder_seen_at')
        batch_op.drop_column('last_reminded_at')

    with op.batch_alter_table('tasks', schema=None) as batch_op:
        batch_op.drop_column('reminder_seen_at')
