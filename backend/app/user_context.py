"""Per-user data context for the local multi-user interim.

Until full JWT auth is implemented (future release), BiziBox uses a single
active login per running backend instance. The active login is stored in
`data/.active_login`. Each login gets its own folder under `data/users/<login>/`
containing a dedicated SQLite database, encrypted onboarding config, sessions
and attachments.
"""

from __future__ import annotations

import logging
import shutil
import sqlite3
from pathlib import Path

from .paths import get_data_dir

logger = logging.getLogger(__name__)

DATA_DIR = get_data_dir()
USERS_DIR = DATA_DIR / "users"
ACTIVE_USER_FILE = DATA_DIR / ".active_login"
LEGACY_DB_FILE = DATA_DIR / "bizibox.db"
LEGACY_DB_BACKUP = DATA_DIR / "bizibox.db.legacy"

DEFAULT_LOGIN = "owner"


def _sanitize_login(login: str) -> str:
    """Make a filesystem-safe directory name from a login."""
    safe = "".join(c if c.isalnum() or c in "_-." else "_" for c in login).strip("_.")
    return safe or "user"


def get_user_data_dir(login: str) -> Path:
    return USERS_DIR / _sanitize_login(login)


def ensure_user_data_dir(login: str) -> Path:
    user_dir = get_user_data_dir(login)
    user_dir.mkdir(parents=True, exist_ok=True)
    (user_dir / "attachments").mkdir(exist_ok=True)
    (user_dir / "sessions").mkdir(exist_ok=True)
    return user_dir


def get_user_db_path(login: str) -> Path:
    return get_user_data_dir(login) / "bizibox.db"


def get_user_db_url(login: str) -> str:
    return f"sqlite+aiosqlite:///{get_user_db_path(login)}"


def get_user_onboarding_file(login: str) -> Path:
    return get_user_data_dir(login) / "onboarding.enc"


def get_active_login() -> str | None:
    """Return the currently active login.

    If no active login is set but a legacy single-user database exists, it is
    migrated to `DEFAULT_LOGIN` and that login becomes active.
    """
    if ACTIVE_USER_FILE.exists():
        login = ACTIVE_USER_FILE.read_text(encoding="utf-8").strip()
        if login:
            return login

    if LEGACY_DB_FILE.exists() and LEGACY_DB_FILE.is_file():
        logger.info("Legacy single-user DB detected; migrating to %s", DEFAULT_LOGIN)
        _migrate_legacy_user(DEFAULT_LOGIN)
        set_active_login(DEFAULT_LOGIN)
        return DEFAULT_LOGIN

    return None


def set_active_login(login: str | None) -> None:
    """Set or clear the active login marker."""
    if login:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        ACTIVE_USER_FILE.write_text(_sanitize_login(login), encoding="utf-8")
    elif ACTIVE_USER_FILE.exists():
        ACTIVE_USER_FILE.unlink()


def _migrate_legacy_user(login: str) -> None:
    """Copy the legacy DB into the per-user folder and rename it."""
    user_dir = get_user_data_dir(login)
    user_dir.mkdir(parents=True, exist_ok=True)
    target_db = get_user_db_path(login)

    if target_db.exists():
        logger.warning("User DB already exists at %s; skipping migration", target_db)
        if LEGACY_DB_FILE.exists():
            LEGACY_DB_FILE.rename(LEGACY_DB_BACKUP)
        return

    shutil.copy2(LEGACY_DB_FILE, target_db)
    logger.info("Copied legacy DB to %s", target_db)

    # Ensure the single user row in the migrated DB matches the new login.
    try:
        with sqlite3.connect(target_db) as conn:
            conn.execute("UPDATE users SET username = ? WHERE id = ?", (login, 1))
            conn.commit()
        logger.info("Renamed default user to %s", login)
    except Exception as e:
        logger.warning("Could not rename default user: %s", e)

    if LEGACY_DB_BACKUP.exists():
        LEGACY_DB_BACKUP.unlink()
    LEGACY_DB_FILE.rename(LEGACY_DB_BACKUP)
    logger.info("Renamed legacy DB to %s", LEGACY_DB_BACKUP)
