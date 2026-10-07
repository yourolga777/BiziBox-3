"""contact previous_life_sphere for spam snapshot

Revision ID: f6a7b8c9d0e1
Revises: e0f1a2b3c4d5
Create Date: 2026-09-23 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'f6a7b8c9d0e1'
down_revision: Union[str, None] = 'e0f1a2b3c4d5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Снимок предыдущей сферы перед пометкой спамом, чтобы снятие спама
    # возвращало контакт в исходную классификацию (или NULL — «Другое»).
    with op.batch_alter_table('contacts', schema=None) as batch_op:
        batch_op.add_column(sa.Column('previous_life_sphere', sa.String(length=20), nullable=True))
        batch_op.create_index('ix_contacts_previous_life_sphere', ['previous_life_sphere'])


def downgrade() -> None:
    with op.batch_alter_table('contacts', schema=None) as batch_op:
        batch_op.drop_index('ix_contacts_previous_life_sphere')
        batch_op.drop_column('previous_life_sphere')