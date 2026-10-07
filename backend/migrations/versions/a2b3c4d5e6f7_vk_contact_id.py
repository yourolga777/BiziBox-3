"""vk_id for VK channel contacts

Revision ID: a2b3c4d5e6f7
Revises: g1h2i3j4k5l6
Create Date: 2026-10-07 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'a2b3c4d5e6f7'
down_revision: Union[str, None] = 'g1h2i3j4k5l6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('contacts', schema=None) as batch_op:
        batch_op.add_column(sa.Column('vk_id', sa.String(length=100), nullable=True))
        batch_op.create_index(
            'uq_contacts_owner_vk',
            ['owner_id', 'vk_id'],
            unique=True,
            sqlite_where=sa.text('vk_id IS NOT NULL'),
        )


def downgrade() -> None:
    with op.batch_alter_table('contacts', schema=None) as batch_op:
        batch_op.drop_index('uq_contacts_owner_vk', sqlite_where=sa.text('vk_id IS NOT NULL'))
        batch_op.drop_column('vk_id')
