"""contact taxonomy: types + hierarchical folders + favorite

Revision ID: c1f2e3d4a5b6
Revises: a1b2c3d4e5f6
Create Date: 2026-08-31 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'c1f2e3d4a5b6'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


SYSTEM_FOLDERS = [
    ("family", "Семья", "#ec4899", 1, "personal"),
    ("friends", "Друзья", "#8b5cf6", 2, "personal"),
    ("groups", "Группы", "#6366f1", 3, "personal"),
    ("channels", "Каналы", "#0ea5e9", 1, "needed"),
    ("service", "Сервисные", "#10b981", 2, "needed"),
]


def upgrade() -> None:
    # 1. Добавляем колонки папкам до миграции данных.
    with op.batch_alter_table('contact_folders', schema=None) as batch_op:
        batch_op.add_column(sa.Column('contact_type', sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column('parent_id', sa.Integer(), nullable=True))
        batch_op.create_index(batch_op.f('ix_contact_folders_contact_type'), ['contact_type'], unique=False)
        batch_op.create_index(batch_op.f('ix_contact_folders_parent_id'), ['parent_id'], unique=False)
        batch_op.create_foreign_key(
            'fk_contact_folders_parent_id', 'contact_folders', ['parent_id'], ['id']
        )

    # 2. Миграция данных контактов (до удаления is_spam).
    op.execute("UPDATE contacts SET contact_type = 'needed' WHERE contact_type = 'service'")
    op.execute("UPDATE contacts SET contact_type = 'spam' WHERE is_spam = 1 AND contact_type != 'spam'")
    op.execute(
        "UPDATE contacts SET contact_type = 'needed', folder_id = NULL "
        "WHERE folder_id IN (SELECT id FROM contact_folders WHERE category_key = 'needed')"
    )
    op.execute(
        "UPDATE contacts SET contact_type = 'spam', folder_id = NULL "
        "WHERE folder_id IN (SELECT id FROM contact_folders WHERE category_key = 'spam')"
    )

    # 3. Приводим системные папки к новой таксономии.
    for key, name, color, sort, ctype in SYSTEM_FOLDERS:
        op.execute(
            "INSERT OR IGNORE INTO contact_folders "
            "(owner_id, name, color, sort_order, is_default, category_key, contact_type) "
            f"VALUES (1, '{name}', '{color}', {sort}, 1, '{key}', '{ctype}')"
        )
        op.execute(
            "UPDATE contact_folders SET "
            f"contact_type = '{ctype}', name = '{name}', color = '{color}', sort_order = {sort} "
            f"WHERE category_key = '{key}' AND owner_id = 1"
        )
    op.execute("DELETE FROM contact_folders WHERE category_key IN ('needed', 'spam')")

    # 4. Колонки контактов: is_important -> is_favorite, удаление chat_type/is_spam.
    with op.batch_alter_table('contacts', schema=None) as batch_op:
        batch_op.add_column(sa.Column('is_favorite', sa.Boolean(), nullable=True))
    op.execute("UPDATE contacts SET is_favorite = COALESCE(is_important, 0)")
    with op.batch_alter_table('contacts', schema=None) as batch_op:
        batch_op.drop_index('ix_contacts_is_important')
        batch_op.drop_index('ix_contacts_chat_type')
        batch_op.drop_index('ix_contacts_is_spam')
        batch_op.drop_column('is_important')
        batch_op.drop_column('chat_type')
        batch_op.drop_column('is_spam')
        batch_op.create_index(batch_op.f('ix_contacts_is_favorite'), ['is_favorite'], unique=False)


def downgrade() -> None:
    with op.batch_alter_table('contacts', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_contacts_is_favorite'))
        batch_op.add_column(sa.Column('is_important', sa.Boolean(), nullable=True))
        batch_op.add_column(sa.Column('is_spam', sa.Boolean(), nullable=True))
        batch_op.add_column(sa.Column('chat_type', sa.String(length=20), nullable=True))
    op.execute("UPDATE contacts SET is_important = COALESCE(is_favorite, 0)")
    op.execute("UPDATE contacts SET is_spam = 1 WHERE contact_type = 'spam'")
    op.execute("UPDATE contacts SET contact_type = 'service' WHERE contact_type = 'needed'")
    with op.batch_alter_table('contacts', schema=None) as batch_op:
        batch_op.drop_column('is_favorite')
        batch_op.create_index(batch_op.f('ix_contacts_is_important'), ['is_important'], unique=False)
        batch_op.create_index(batch_op.f('ix_contacts_chat_type'), ['chat_type'], unique=False)
        batch_op.create_index(batch_op.f('ix_contacts_is_spam'), ['is_spam'], unique=False)

    with op.batch_alter_table('contact_folders', schema=None) as batch_op:
        batch_op.drop_constraint('fk_contact_folders_parent_id', type_='foreignkey')
        batch_op.drop_index(batch_op.f('ix_contact_folders_parent_id'))
        batch_op.drop_index(batch_op.f('ix_contact_folders_contact_type'))
        batch_op.drop_column('parent_id')
        batch_op.drop_column('contact_type')
