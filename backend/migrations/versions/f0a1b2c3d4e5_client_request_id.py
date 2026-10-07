"""client_request_id for idempotent message send

Revision ID: f0a1b2c3d4e5
Revises: e5f6a7b8c9d0
Create Date: 2026-09-03 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'f0a1b2c3d4e5'
down_revision: Union[str, None] = 'e5f6a7b8c9d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('messages', schema=None) as batch_op:
        batch_op.add_column(sa.Column('client_request_id', sa.String(length=64), nullable=True))
        batch_op.create_index('ix_messages_client_request_id', ['client_request_id'])
    with op.batch_alter_table('outbox_messages', schema=None) as batch_op:
        batch_op.add_column(sa.Column('client_request_id', sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column('attachments', sa.Text(), nullable=True))
        batch_op.create_index('ix_outbox_messages_client_request_id', ['client_request_id'])


def downgrade() -> None:
    with op.batch_alter_table('outbox_messages', schema=None) as batch_op:
        batch_op.drop_index('ix_outbox_messages_client_request_id')
        batch_op.drop_column('attachments')
        batch_op.drop_column('client_request_id')
    with op.batch_alter_table('messages', schema=None) as batch_op:
        batch_op.drop_index('ix_messages_client_request_id')
        batch_op.drop_column('client_request_id')
