"""Загрузка эффективных настроек Telegram: api_id/api_hash/прокси.

Источник данных — настройки пользователя (settings-таблица, заполняется
при онбординге), с fallback на значения из .env. Это позволяет введённым
при онбординге ключам работать без ручной правки .env.
"""

from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from .settings_service import SettingsService


def _proxy_from_env() -> Optional[dict[str, Any]]:
    if not settings.TELEGRAM_PROXY_ENABLED:
        return None
    proxy: dict[str, Any] = {
        "scheme": settings.TELEGRAM_PROXY_TYPE,
        "hostname": settings.TELEGRAM_PROXY_HOST,
        "port": settings.TELEGRAM_PROXY_PORT,
    }
    if settings.TELEGRAM_PROXY_TYPE == "mtproto" and settings.TELEGRAM_PROXY_SECRET:
        proxy["secret"] = settings.TELEGRAM_PROXY_SECRET
    elif settings.TELEGRAM_PROXY_USERNAME and settings.TELEGRAM_PROXY_PASSWORD:
        proxy["username"] = settings.TELEGRAM_PROXY_USERNAME
        proxy["password"] = settings.TELEGRAM_PROXY_PASSWORD
    return proxy


def _proxy_from_config(cfg: Any) -> Optional[dict[str, Any]]:
    if not isinstance(cfg, dict):
        return None
    # Явное «прокси выключен» из онбординга/настроек. Отсутствие флага
    # трактуем как включённый — это сохраняет совместимость со старыми
    # записями proxy_config, где флага enabled не было.
    if cfg.get("enabled") is False:
        return None
    if cfg.get("mode") in ("direct", "system_vpn"):
        return None
    host = cfg.get("host")
    port = cfg.get("port")
    if not host or not port:
        return None
    ptype = cfg.get("type") or "socks5"
    proxy: dict[str, Any] = {
        "scheme": ptype,
        "hostname": str(host),
        "port": int(port),
    }
    if ptype == "mtproto" and cfg.get("secret"):
        proxy["secret"] = str(cfg["secret"])
    elif cfg.get("username") and cfg.get("password"):
        proxy["username"] = str(cfg["username"])
        proxy["password"] = str(cfg["password"])
    return proxy


async def load_effective_telegram_config(
    session: AsyncSession, owner_id: Optional[int] = None
) -> dict[str, Any]:
    """Возвращает {api_id, api_hash, proxy} с учётом онбординга и .env."""
    svc = SettingsService(session, owner_id)
    api_id = await svc.get("telegram_api_id") or settings.TELEGRAM_API_ID
    api_hash = await svc.get("telegram_api_hash") or settings.TELEGRAM_API_HASH

    proxy_cfg = await svc.get("proxy_config")
    proxy = _proxy_from_config(proxy_cfg) if proxy_cfg is not None else _proxy_from_env()

    return {"api_id": api_id, "api_hash": api_hash, "proxy": proxy}
