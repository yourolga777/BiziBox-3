"""add channel mode (both / incoming_only / outgoing_only)

Revision ID: a3b4c5d6e7f8
Revises: a2b3c4d5e6f7
Create Date: 2026-10-08 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'a3b4c5d6e7f8'
down_revision: Union[str, None] = 'a2b3c4d5e6f7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'channels',
        sa.Column('mode', sa.String(length=20), nullable=False, server_default='both'),
    )


def downgrade() -> None:
    op.drop_column('channels', 'mode')
