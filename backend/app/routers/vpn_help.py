"""Справка по VPN/прокси-сервисам по названию.

Гибрид: сначала встроенная база ``services/vpn_services.py``, при отсутствии —
живой web-поиск (DuckDuckGo Instant Answer). Используется формой онбординга и
настроек («Я не знаю, что у меня за сервис»).
"""

import logging
from typing import Any, Optional

import httpx
from fastapi import APIRouter, Query

from ..services.vpn_services import lookup_builtin

logger = logging.getLogger(__name__)

router = APIRouter()

_GENERIC_ADVICE = (
    "Если приложение работает на уровне системы (весь трафик через VPN) — "
    "выберите «Системный VPN». Если оно открывает локальный socks/HTTP-порт — "
    "выберите «Свой прокси» и укажите этот порт."
)


async def _web_lookup(name: str) -> Optional[dict[str, Any]]:
    try:
        async with httpx.AsyncClient(timeout=6.0) as client:
            resp = await client.get(
                "https://api.duckduckgo.com/",
                params={
                    "q": f"{name} VPN proxy",
                    "format": "json",
                    "no_html": "1",
                    "skip_disambig": "1",
                },
            )
            resp.raise_for_status()
            data = resp.json()
    except Exception as e:
        logger.warning("vpn-help web lookup failed: %s", e)
        return None

    abstract = (data.get("AbstractText") or data.get("Abstract") or "").strip()
    if not abstract:
        return None

    return {
        "found": True,
        "name": name,
        "category": "unknown",
        "description": abstract,
        "advice": _GENERIC_ADVICE,
        "default_port": None,
        "source": "web",
    }


@router.get("")
async def vpn_help(name: str = Query(..., min_length=1, max_length=100)) -> dict[str, Any]:
    query = name.strip()
    if not query:
        return {"found": False, "message": "Введите название сервиса."}

    builtin = lookup_builtin(query)
    if builtin is not None:
        return {
            "found": True,
            "name": builtin["name"],
            "category": builtin["category"],
            "description": builtin["description"],
            "advice": builtin["advice"],
            "default_port": builtin.get("default_port"),
            "source": "builtin",
        }

    web = await _web_lookup(query)
    if web is not None:
        return web

    return {
        "found": False,
        "message": "Сервис не найден. Проверьте название или выберите режим по тому, как работает приложение.",
    }
