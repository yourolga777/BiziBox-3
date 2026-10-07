"""contact life_sphere + folder sphere + type templates

Revision ID: e0f1a2b3c4d5
Revises: d2e3f4a5b6c7
Create Date: 2026-09-23 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'e0f1a2b3c4d5'
down_revision: Union[str, None] = 'd2e3f4a5b6c7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # contacts: contact_type -> life_sphere
    with op.batch_alter_table('contacts', schema=None) as batch_op:
        batch_op.add_column(sa.Column('life_sphere', sa.String(length=20), nullable=True))
        batch_op.create_index('ix_contacts_life_sphere', ['life_sphere'])

    # Перенос значений старой таксономии: needed -> work, остальные как есть.
    op.execute("UPDATE contacts SET life_sphere = 'work' WHERE contact_type = 'needed'")
    op.execute("UPDATE contacts SET life_sphere = 'personal' WHERE contact_type = 'personal'")
    op.execute("UPDATE contacts SET life_sphere = 'spam' WHERE contact_type = 'spam'")
    # other/dialogs -> NULL

    with op.batch_alter_table('contacts', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_contacts_contact_type'))
        batch_op.drop_column('contact_type')

    # contact_folders: contact_type -> sphere
    with op.batch_alter_table('contact_folders', schema=None) as batch_op:
        batch_op.add_column(sa.Column('sphere', sa.String(length=20), nullable=True))
        batch_op.create_index(batch_op.f('ix_contact_folders_sphere'), ['sphere'])

    op.execute("UPDATE contact_folders SET sphere = 'work' WHERE contact_type = 'needed'")
    op.execute("UPDATE contact_folders SET sphere = 'personal' WHERE contact_type = 'personal'")
    op.execute("UPDATE contact_folders SET sphere = 'spam' WHERE contact_type = 'spam'")

    with op.batch_alter_table('contact_folders', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_contact_folders_contact_type'))
        batch_op.drop_column('contact_type')

    # Уникальность папок теперь по (owner_id, category_key, sphere),
    # разрешая две папки "Каналы" — по одной на сферу.
    op.execute("DROP INDEX IF EXISTS idx_folders_owner_category_key")
    op.execute(
        "CREATE UNIQUE INDEX idx_folders_owner_category_key "
        "ON contact_folders (owner_id, category_key, sphere) "
        "WHERE category_key IS NOT NULL"
    )

    # Таблицы типов контактов (шаблоны + связь M2M).
    op.create_table(
        'contact_type_templates',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('owner_id', sa.Integer(), nullable=False),
        sa.Column('sphere', sa.String(length=20), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('slug', sa.String(length=100), nullable=True),
        sa.Column('sort_order', sa.Integer(), nullable=True),
        sa.Column('is_custom', sa.Boolean(), nullable=True),
        sa.Column('is_system', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id']),
    )
    op.create_index('uq_ctt_owner_slug', 'contact_type_templates', ['owner_id', 'slug'], unique=True, sqlite_where=sa.text('slug IS NOT NULL'))
    op.create_index(op.f('ix_contact_type_templates_sphere'), 'contact_type_templates', ['sphere'])
    op.create_index(op.f('ix_contact_type_templates_owner_id'), 'contact_type_templates', ['owner_id'])
    op.create_index(op.f('ix_contact_type_templates_slug'), 'contact_type_templates', ['slug'])

    op.create_table(
        'contact_contact_type_association',
        sa.Column('contact_id', sa.Integer(), primary_key=True),
        sa.Column('template_id', sa.Integer(), primary_key=True),
        sa.Column('owner_id', sa.Integer(), nullable=False, server_default='1'),
        sa.ForeignKeyConstraint(['contact_id'], ['contacts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['template_id'], ['contact_type_templates.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id']),
    )

    # Системные шаблоны типов.
    op.bulk_insert(
        sa.table(
            'contact_type_templates',
            sa.column('owner_id', sa.Integer),
            sa.column('sphere', sa.String),
            sa.column('name', sa.String),
            sa.column('slug', sa.String),
            sa.column('sort_order', sa.Integer),
            sa.column('is_custom', sa.Boolean),
            sa.column('is_system', sa.Boolean),
        ),
        [
            {'owner_id': 1, 'sphere': 'personal', 'name': 'Друзья', 'slug': 'friends', 'sort_order': 1, 'is_custom': False, 'is_system': True},
            {'owner_id': 1, 'sphere': 'personal', 'name': 'Семья', 'slug': 'family', 'sort_order': 2, 'is_custom': False, 'is_system': True},
            {'owner_id': 1, 'sphere': 'personal', 'name': 'Учёба', 'slug': 'study', 'sort_order': 3, 'is_custom': False, 'is_system': True},
            {'owner_id': 1, 'sphere': 'work', 'name': 'Клиент', 'slug': 'client', 'sort_order': 1, 'is_custom': False, 'is_system': True},
            {'owner_id': 1, 'sphere': 'work', 'name': 'Поставщик', 'slug': 'supplier', 'sort_order': 2, 'is_custom': False, 'is_system': True},
            {'owner_id': 1, 'sphere': 'work', 'name': 'Партнёр', 'slug': 'partner', 'sort_order': 3, 'is_custom': False, 'is_system': True},
            {'owner_id': 1, 'sphere': 'work', 'name': 'Подрядчик', 'slug': 'contractor', 'sort_order': 4, 'is_custom': False, 'is_system': True},
            {'owner_id': 1, 'sphere': 'work', 'name': 'Сотрудник', 'slug': 'employee', 'sort_order': 5, 'is_custom': False, 'is_system': True},
        ],
    )


def downgrade() -> None:
    op.drop_table('contact_contact_type_association')
    op.drop_table('contact_type_templates')

    op.execute("DROP INDEX IF EXISTS idx_folders_owner_category_key")
    op.execute(
        "CREATE UNIQUE INDEX idx_folders_owner_category_key "
        "ON contact_folders (owner_id, category_key) "
        "WHERE category_key IS NOT NULL"
    )

    with op.batch_alter_table('contact_folders', schema=None) as batch_op:
        batch_op.add_column(sa.Column('contact_type', sa.String(length=20), nullable=True))
        batch_op.create_index(batch_op.f('ix_contact_folders_contact_type'), ['contact_type'])

    op.execute("UPDATE contact_folders SET contact_type = 'needed' WHERE sphere = 'work'")
    op.execute("UPDATE contact_folders SET contact_type = sphere WHERE sphere IN ('personal', 'spam')")

    with op.batch_alter_table('contact_folders', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_contact_folders_sphere'))
        batch_op.drop_column('sphere')

    with op.batch_alter_table('contacts', schema=None) as batch_op:
        batch_op.add_column(sa.Column('contact_type', sa.String(length=20), nullable=True))
        batch_op.create_index(batch_op.f('ix_contacts_contact_type'), ['contact_type'])

    op.execute("UPDATE contacts SET contact_type = 'needed' WHERE life_sphere = 'work'")
    op.execute("UPDATE contacts SET contact_type = life_sphere WHERE life_sphere IN ('personal', 'spam')")

    with op.batch_alter_table('contacts', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_contacts_life_sphere'))
        batch_op.drop_column('life_sphere')