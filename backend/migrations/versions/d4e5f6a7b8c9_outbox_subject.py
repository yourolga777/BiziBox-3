"""outbox subject column for email reply threading

Revision ID: d4e5f6a7b8c9
Revises: c1f2e3d4a5b6
Create Date: 2026-09-02 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'd4e5f6a7b8c9'
down_revision: Union[str, None] = 'c1f2e3d4a5b6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('outbox_messages', schema=None) as batch_op:
        batch_op.add_column(sa.Column('subject', sa.String(length=255), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('outbox_messages', schema=None) as batch_op:
        batch_op.drop_column('subject')
