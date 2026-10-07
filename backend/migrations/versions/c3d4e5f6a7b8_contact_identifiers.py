"""contact identifiers for merged contact aliases

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-10-06 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'contact_identifiers',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('owner_id', sa.Integer(), server_default='1', nullable=False),
        sa.Column('contact_id', sa.Integer(), nullable=False),
        sa.Column('channel', sa.String(length=20), nullable=False),
        sa.Column('value', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.ForeignKeyConstraint(['contact_id'], ['contacts.id'], ),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('contact_identifiers', schema=None) as batch_op:
        batch_op.create_index('ix_contact_identifiers_id', ['id'], unique=False)
        batch_op.create_index('ix_contact_identifiers_owner_id', ['owner_id'], unique=False)
        batch_op.create_index('ix_contact_identifiers_contact_id', ['contact_id'], unique=False)
        batch_op.create_index(
            'uq_ci_owner_contact_channel_value',
            ['owner_id', 'contact_id', 'channel', 'value'],
            unique=True,
        )


def downgrade() -> None:
    with op.batch_alter_table('contact_identifiers', schema=None) as batch_op:
        batch_op.drop_index('uq_ci_owner_contact_channel_value')
        batch_op.drop_index('ix_contact_identifiers_contact_id')
        batch_op.drop_index('ix_contact_identifiers_owner_id')
        batch_op.drop_index('ix_contact_identifiers_id')
    op.drop_table('contact_identifiers')
