"""classification v2: channels sphere + drop partners/contractors folders

Revision ID: b2c3d4e5f6a7
Revises: a0b1c9d2e3f4
Create Date: 2026-10-06 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, None] = 'a0b1c9d2e3f4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_REMOVE_KEYS = {"channels", "partners", "contractors"}

# Полный набор системных папок таксономии v2 (без Каналы/Партнёры/Подрядчики).
_SYSTEM_FOLDERS = [
    ("Семья", "#ec4899", 1, "family", "personal"),
    ("Друзья", "#8b5cf6", 2, "friends", "personal"),
    ("Учёба", "#6366f1", 3, "study", "personal"),
    ("Группы", "#14b8a6", 4, "groups", "personal"),
    ("Заказчики", "#f59e0b", 1, "customers", "work"),
    ("Поставщики", "#10b981", 2, "suppliers", "work"),
    ("Сотрудники", "#ef4444", 3, "employees", "work"),
]


def upgrade() -> None:
    conn = op.get_bind()

    rows = conn.execute(
        sa.text("SELECT id, parent_id, category_key FROM contact_folders")
    ).fetchall()
    folders = [
        {"id": r[0], "parent_id": r[1], "category_key": r[2]} for r in rows
    ]
    by_id = {f["id"]: f for f in folders}

    roots = [f for f in folders if f["category_key"] in _REMOVE_KEYS]

    # Нормализуем sphere для системных категорий, созданных legacy-сидом
    # (без sphere): привязываем их к сферам до вставки недостающих.
    conn.execute(
        sa.text(
            "UPDATE contact_folders SET sphere = 'personal' "
            "WHERE category_key IN ('family', 'friends', 'study', 'groups') "
            "AND sphere IS NULL"
        )
    )
    conn.execute(
        sa.text(
            "UPDATE contact_folders SET sphere = 'work' "
            "WHERE category_key IN ('customers', 'suppliers', 'employees') "
            "AND sphere IS NULL"
        )
    )

    # Добавляем недостающие системные папки (идемпотентно).
    for name, color, sort_order, category_key, sphere in _SYSTEM_FOLDERS:
        conn.execute(
            sa.text(
                "INSERT OR IGNORE INTO contact_folders "
                "(owner_id, name, color, sort_order, is_default, category_key, sphere) "
                "VALUES (1, :name, :color, :sort_order, 1, :category_key, :sphere)"
            ),
            {
                "name": name,
                "color": color,
                "sort_order": sort_order,
                "category_key": category_key,
                "sphere": sphere,
            },
        )

    if not roots:
        return

    # Все папки в деревьях удаляемых корней (корень + подпапки).
    to_delete: set[int] = set()

    def collect(fid: int) -> None:
        if fid in to_delete:
            return
        to_delete.add(fid)
        for f in folders:
            if f["parent_id"] == fid:
                collect(f["id"])

    for r in roots:
        collect(r["id"])

    channel_roots = {f["id"] for f in roots if f["category_key"] == "channels"}
    pc_roots = {
        f["id"] for f in roots if f["category_key"] in ("partners", "contractors")
    }

    def belongs_to(fid: int, root_set: set[int]) -> bool:
        seen: set[int] = set()
        cur: Union[int, None] = fid
        while cur is not None and cur not in seen:
            if cur in root_set:
                return True
            seen.add(cur)
            parent = by_id.get(cur)
            cur = parent["parent_id"] if parent else None
        return False

    channel_ids = {fid for fid in to_delete if belongs_to(fid, channel_roots)}
    pc_ids = {fid for fid in to_delete if belongs_to(fid, pc_roots)}

    if channel_ids:
        ids = ",".join(str(i) for i in channel_ids)
        conn.execute(
            sa.text(
                f"UPDATE contacts SET life_sphere = 'channels', folder_id = NULL "
                f"WHERE folder_id IN ({ids}) AND deleted_at IS NULL"
            )
        )

    if pc_ids:
        ids = ",".join(str(i) for i in pc_ids)
        conn.execute(
            sa.text(
                f"UPDATE contacts SET life_sphere = NULL, folder_id = NULL "
                f"WHERE folder_id IN ({ids}) AND deleted_at IS NULL"
            )
        )

    if to_delete:
        ids = ",".join(str(i) for i in to_delete)
        conn.execute(sa.text(f"DELETE FROM contact_folders WHERE id IN ({ids})"))


def downgrade() -> None:
    conn = op.get_bind()

    for name, color, sort_order, category_key in [
        ("Каналы", "#0ea5e9", 5, "channels"),
        ("Партнёры", "#3b82f6", 6, "partners"),
        ("Подрядчики", "#8b5cf6", 7, "contractors"),
    ]:
        conn.execute(
            sa.text(
                "INSERT OR IGNORE INTO contact_folders "
                "(owner_id, name, color, sort_order, is_default, category_key, sphere) "
                "VALUES (1, :name, :color, :sort_order, 1, :category_key, NULL)"
            ),
            {
                "name": name,
                "color": color,
                "sort_order": sort_order,
                "category_key": category_key,
            },
        )

    conn.execute(
        sa.text("UPDATE contacts SET life_sphere = NULL WHERE life_sphere = 'channels'")
    )
