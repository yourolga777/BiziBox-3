"""multiple labels: contact folders M2M + contact spheres junction

Revision ID: g1h2i3j4k5l6
Revises: c3d4e5f6a7b8
Create Date: 2026-10-06 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'g1h2i3j4k5l6'
down_revision: Union[str, None] = 'c3d4e5f6a7b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'contact_folder_association',
        sa.Column('contact_id', sa.Integer(), nullable=False),
        sa.Column('folder_id', sa.Integer(), nullable=False),
        sa.Column('owner_id', sa.Integer(), server_default='1', nullable=False),
        sa.ForeignKeyConstraint(['contact_id'], ['contacts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['folder_id'], ['contact_folders.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('contact_id', 'folder_id'),
    )
    op.create_table(
        'contact_spheres',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('owner_id', sa.Integer(), server_default='1', nullable=False),
        sa.Column('contact_id', sa.Integer(), nullable=False),
        sa.Column('sphere', sa.String(length=20), nullable=False),
        sa.ForeignKeyConstraint(['contact_id'], ['contacts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )

    with op.batch_alter_table('contact_spheres', schema=None) as batch_op:
        batch_op.create_index('ix_cs_contact_id', ['contact_id'], unique=False)
        batch_op.create_index(
            'uq_cs_owner_contact_sphere',
            ['owner_id', 'contact_id', 'sphere'],
            unique=True,
        )

    # Перенос существующих данных: folder_id → association, life_sphere → spheres.
    op.execute(
        "INSERT INTO contact_folder_association (owner_id, contact_id, folder_id) "
        "SELECT owner_id, id, folder_id FROM contacts WHERE folder_id IS NOT NULL"
    )
    op.execute(
        "INSERT INTO contact_spheres (owner_id, contact_id, sphere) "
        "SELECT owner_id, id, life_sphere FROM contacts WHERE life_sphere IS NOT NULL"
    )


def downgrade() -> None:
    with op.batch_alter_table('contact_spheres', schema=None) as batch_op:
        batch_op.drop_index('uq_cs_owner_contact_sphere')
        batch_op.drop_index('ix_cs_contact_id')
    op.drop_table('contact_spheres')
    op.drop_table('contact_folder_association')
