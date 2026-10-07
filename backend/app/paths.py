"""Централизованное определение путей к данным и бандл-ресурсам.

В PyInstaller-сборке (frozen) пути, построенные от ``__file__``, указывают на
временную папку распаковки ``sys._MEIPASS``, которая удаляется при выходе.
Поэтому:

- **данные** (БД, ключ шифрования, логи, сессии, вложения) кладутся в
  персистентную папку ``data/`` рядом с исполняемым файлом;
- **read-only ресурсы** (migrations, alembic.ini, фронтенд) читаются из
  бандла ``sys._MEIPASS``.
"""

from __future__ import annotations

import sys
from pathlib import Path


def is_frozen() -> bool:
    """True внутри PyInstaller-сборки."""
    return bool(getattr(sys, "frozen", False))


def get_bundle_dir() -> Path:
    """Каталог read-only ресурсов, упакованных в сборку.

    - frozen: ``sys._MEIPASS`` (временная папка распаковки);
    - dev: ``<repo>/backend``.
    """
    if is_frozen():
        return Path(getattr(sys, "_MEIPASS", Path.cwd()))
    return Path(__file__).resolve().parent.parent


def get_data_dir() -> Path:
    """Персистентный каталог пользовательских данных.

    - frozen: ``data/`` рядом с исполняемым файлом (портабельно / в ``{app}``);
    - dev: ``<repo>/backend/data``.
    """
    if is_frozen():
        return Path(sys.executable).resolve().parent / "data"
    return Path(__file__).resolve().parent.parent / "data"


def ensure_bundle_importable() -> None:
    """Гарантирует, что ресурсы бандла импортируемы (пакет ``migrations``)."""
    bundle = str(get_bundle_dir())
    if bundle not in sys.path:
        sys.path.insert(0, bundle)
