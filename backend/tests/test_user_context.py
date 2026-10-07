"""Per-user data context: legacy migration + fresh DB per login.

AC D4: данные your_olga изолированы в своей БД; новый логин получает
отдельный путь к чистой БД (0 сущностей) — owner scope enforced через
раздельные SQLite-файлы и owner_id.
"""

import sqlite3
from pathlib import Path

import pytest

import app.user_context as uc


@pytest.fixture
def tmp_data(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(uc, "DATA_DIR", tmp_path)
    monkeypatch.setattr(uc, "USERS_DIR", tmp_path / "users")
    monkeypatch.setattr(uc, "ACTIVE_USER_FILE", tmp_path / ".active_login")
    monkeypatch.setattr(uc, "LEGACY_DB_FILE", tmp_path / "bizibox.db")
    monkeypatch.setattr(uc, "LEGACY_DB_BACKUP", tmp_path / "bizibox.db.legacy")
    return tmp_path


def test_new_login_gets_separate_clean_db(tmp_data: Path):
    """Два разных логина указывают на разные файлы БД — изоляция данных."""
    url_a = uc.get_user_db_url("your_olga")
    url_b = uc.get_user_db_url("new_user")
    assert url_a != url_b
    assert "your_olga" in url_a
    assert "new_user" in url_b


def test_legacy_db_migrates_to_default_login(tmp_data: Path):
    """Legacy bizibox.db мигрирует в users/your_olga/ с username=your_olga."""
    legacy = tmp_data / "bizibox.db"
    conn = sqlite3.connect(legacy)
    conn.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT)")
    conn.execute("INSERT INTO users (id, username) VALUES (1, 'owner')")
    conn.commit()
    conn.close()

    uc._migrate_legacy_user(uc.DEFAULT_LOGIN)

    migrated_path = uc.get_user_db_path(uc.DEFAULT_LOGIN)
    assert migrated_path.exists()

    conn2 = sqlite3.connect(migrated_path)
    username = conn2.execute("SELECT username FROM users WHERE id = 1").fetchone()[0]
    conn2.close()
    assert username == uc.DEFAULT_LOGIN
    assert not legacy.exists()
    assert (tmp_data / "bizibox.db.legacy").exists()


def test_sanitize_login_filesystem_safe():
    assert uc._sanitize_login("вася/петя") == "вася_петя"
    assert uc._sanitize_login("  ") == "user"
    assert uc._sanitize_login("alice") == "alice"
