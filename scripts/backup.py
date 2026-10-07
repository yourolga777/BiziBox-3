"""Полный бэкап данных BiziBox.

Копирует в backups/bizibox-backup-<timestamp>/:
- БД пользователей (консистентный снимок через sqlite3 backup API, WAL-safe);
- ключ шифрования (.encryption_key), активный логин, onboarding.enc, вложения;
- .env.

Использование:
    python scripts/backup.py
"""

import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"
DATA_DIR = BACKEND / "data"
BACKUPS_DIR = ROOT / "backups"

IGNORE = shutil.ignore_patterns("logs", "backup", "*.db", "*.db-wal", "*.db-shm")


def _backup_db(src: Path, dst: Path) -> None:
    src_conn = sqlite3.connect(str(src))
    dst_conn = sqlite3.connect(str(dst))
    try:
        with dst_conn:
            src_conn.backup(dst_conn)
    finally:
        dst_conn.close()
        src_conn.close()


def main() -> None:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = BACKUPS_DIR / f"bizibox-backup-{ts}"
    dest.mkdir(parents=True, exist_ok=True)

    # 1. Данные целиком (без БД, логов и вложенных бэкапов).
    shutil.copytree(DATA_DIR, dest / "data", ignore=IGNORE)
    print("copied: data/ (ключ, онбординг, вложения)")

    # 2. БД пользователей — консистентный снимок.
    for db in (DATA_DIR / "users").rglob("*.db"):
        rel = db.relative_to(DATA_DIR)
        dst_db = dest / "data" / rel
        dst_db.parent.mkdir(parents=True, exist_ok=True)
        _backup_db(db, dst_db)
        print(f"backed up DB: {rel}")

    # 3. .env
    env = BACKEND / ".env"
    if env.exists():
        shutil.copy2(env, dest / ".env")
        print("copied: .env")

    print(f"\nБэкап готов: {dest}")


if __name__ == "__main__":
    main()
