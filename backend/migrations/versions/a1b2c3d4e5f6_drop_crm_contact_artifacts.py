"""drop CRM contact artifacts: tags, custom fields, auto_reply_enabled

Revision ID: a1b2c3d4e5f6
Revises: 2c41a82f6549
Create Date: 2026-08-28 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '2c41a82f6549'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_table('contact_tag_association')
    op.drop_table('contact_tags')
    op.drop_table('contact_fields')

    with op.batch_alter_table('contacts', schema=None) as batch_op:
        batch_op.drop_column('auto_reply_enabled')


def downgrade() -> None:
    with op.batch_alter_table('contacts', schema=None) as batch_op:
        batch_op.add_column(sa.Column('auto_reply_enabled', sa.Boolean(), nullable=True))

    op.create_table(
        'contact_fields',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('owner_id', sa.Integer(), server_default='1', nullable=False),
        sa.Column('contact_id', sa.Integer(), nullable=False),
        sa.Column('field_type', sa.String(length=50), nullable=False),
        sa.Column('value', sa.String(length=500), nullable=False),
        sa.Column('is_primary', sa.Boolean(), nullable=True),
        sa.Column('last_used_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.ForeignKeyConstraint(['contact_id'], ['contacts.id'], ),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('contact_fields', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_contact_fields_id'), ['id'], unique=False)
        batch_op.create_index(batch_op.f('ix_contact_fields_contact_id'), ['contact_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_contact_fields_owner_id'), ['owner_id'], unique=False)

    op.create_table(
        'contact_tags',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('owner_id', sa.Integer(), server_default='1', nullable=False),
        sa.Column('name', sa.String(length=50), nullable=False),
        sa.Column('color', sa.String(length=7), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('contact_tags', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_contact_tags_id'), ['id'], unique=False)
        batch_op.create_index(batch_op.f('ix_contact_tags_owner_id'), ['owner_id'], unique=False)

    op.create_table(
        'contact_tag_association',
        sa.Column('contact_id', sa.Integer(), nullable=False),
        sa.Column('tag_id', sa.Integer(), nullable=False),
        sa.Column('owner_id', sa.Integer(), server_default='1', nullable=False),
        sa.ForeignKeyConstraint(['contact_id'], ['contacts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tag_id'], ['contact_tags.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('contact_id', 'tag_id'),
    )
