"""База известных VPN/прокси-сервисов для подсказок в онбординге и настройках.

Используется эндпоинтом ``/api/vpn-help``: сначала ищем здесь, при отсутствии
делается живой web-поиск (см. ``routers/vpn_help.py``).

Категории:
- ``system_vpn`` — работает на уровне системы (весь трафик через туннель),
  прокси настраивать НЕ нужно.
- ``proxy`` — открывает локальный socks5/http порт, который надо указать.
- ``mtproto`` — специальный прокси только для Telegram (нужен secret).
"""

from typing import Any, Optional

VPN_SERVICES: dict[str, dict[str, Any]] = {
    "openvpn": {
        "name": "OpenVPN",
        "category": "system_vpn",
        "aliases": ["open vpn", "openvpn gui", "openvpn connect"],
        "description": "Классический VPN-клиент: весь трафик компьютера идёт через зашифрованный туннель.",
        "advice": "Настраивать прокси не нужно. В BiziBox выберите «Системный VPN».",
        "default_port": None,
    },
    "wireguard": {
        "name": "WireGuard",
        "category": "system_vpn",
        "aliases": ["wire guard", "wg"],
        "description": "Быстрый современный VPN, встроен в Windows и многие клиенты. Работает на уровне системы.",
        "advice": "Выберите «Системный VPN» — прокси не нужен.",
        "default_port": None,
    },
    "happ": {
        "name": "Happ",
        "category": "system_vpn",
        "aliases": ["happ vpn"],
        "description": "Популярный VPN-клиент. Работает на уровне системы — весь трафик идёт через VPN-туннель.",
        "advice": (
            "Выберите «Системный VPN». Если в Happ включён отдельный локальный "
            "прокси-режим (socks5/HTTP), укажите его порт через «Свой прокси»."
        ),
        "default_port": None,
    },
    "mullvad": {
        "name": "Mullvad",
        "category": "system_vpn",
        "aliases": ["mullvad vpn"],
        "description": "VPN-сервис с системным клиентом (WireGuard/OpenVPN).",
        "advice": "Выберите «Системный VPN».",
        "default_port": None,
    },
    "protonvpn": {
        "name": "Proton VPN",
        "category": "system_vpn",
        "aliases": ["proton vpn", "proton"],
        "description": "VPN-клиент, работает на уровне системы.",
        "advice": "Выберите «Системный VPN».",
        "default_port": None,
    },
    "nordvpn": {
        "name": "NordVPN",
        "category": "system_vpn",
        "aliases": ["nord vpn", "nord"],
        "description": "VPN-клиент, работает на уровне системы.",
        "advice": "Выберите «Системный VPN».",
        "default_port": None,
    },
    "outline": {
        "name": "Outline",
        "category": "system_vpn",
        "aliases": ["outline vpn", "outline client"],
        "description": "VPN-клиент (на базе Shadowsocks), работает на уровне системы.",
        "advice": "Выберите «Системный VPN».",
        "default_port": None,
    },
    "v2rayn": {
        "name": "v2rayN",
        "category": "proxy",
        "aliases": ["v2ray", "v2rayn", "v2ray ng", "v2rayng"],
        "description": "Клиент V2Ray для Windows. Открывает локальный socks5/HTTP-порт.",
        "advice": "Выберите «Свой прокси»: тип SOCKS5, хост 127.0.0.1, порт из настроек v2rayN (обычно 10808).",
        "default_port": "10808",
    },
    "clash": {
        "name": "Clash",
        "category": "proxy",
        "aliases": ["clash for windows", "clash verge", "mihomo", "clash meta", "clashx"],
        "description": "Прокси-клиент (Clash for Windows / Clash Verge / Mihomo). Открывает локальный порт.",
        "advice": "Выберите «Свой прокси»: тип SOCKS5/HTTP, хост 127.0.0.1, порт из настроек Clash (обычно 7890).",
        "default_port": "7890",
    },
    "nekoray": {
        "name": "Nekoray / NekoBox",
        "category": "proxy",
        "aliases": ["nekoray", "nekobox", "neko box"],
        "description": "GUI-клиенты для V2Ray/Xray, открывают локальный socks-порт.",
        "advice": "Выберите «Свой прокси»: тип SOCKS5, хост 127.0.0.1, порт из настроек клиента.",
        "default_port": "2080",
    },
    "hiddify": {
        "name": "Hiddify",
        "category": "proxy",
        "aliases": ["hiddify", "hiddify next"],
        "description": "Клиент для V2Ray/Xray/Sing-box. Может работать и как системный VPN, и как локальный прокси.",
        "advice": (
            "Если работает как системный VPN — «Системный VPN». Если включён "
            "локальный прокси-режим — «Свой прокси» с его socks-портом."
        ),
        "default_port": None,
    },
    "shadowsocks": {
        "name": "Shadowsocks",
        "category": "proxy",
        "aliases": ["shadowsocks", "ss"],
        "description": "Протокол прокси; клиенты открывают локальный socks5-порт.",
        "advice": "Выберите «Свой прокси»: тип SOCKS5, хост 127.0.0.1, порт из клиента (обычно 1080).",
        "default_port": "1080",
    },
    "mtproto": {
        "name": "MTProto-прокси",
        "category": "mtproto",
        "aliases": ["mtproto", "mtproto proxy", "mtproto прокси"],
        "description": "Специальный прокси именно для Telegram (нужен секретный ключ secret).",
        "advice": "Выберите «Свой прокси»: тип MTProto, укажите host, port и secret.",
        "default_port": None,
    },
    "singbox": {
        "name": "Sing-box",
        "category": "proxy",
        "aliases": ["sing-box", "singbox", "sing box"],
        "description": "Универсальное прокси-ядро, открывает локальный порт.",
        "advice": "Выберите «Свой прокси» с socks/HTTP-портом из настроек sing-box.",
        "default_port": None,
    },
}


def _normalize(name: str) -> str:
    return " ".join(name.strip().lower().split())


def lookup_builtin(name: str) -> Optional[dict[str, Any]]:
    """Ищет сервис по названию: точное имя → алиасы → вхождение подстроки."""
    q = _normalize(name)
    if not q:
        return None

    for service in VPN_SERVICES.values():
        if _normalize(service["name"]) == q:
            return dict(service)
    for service in VPN_SERVICES.values():
        for alias in service.get("aliases", []):
            if _normalize(alias) == q:
                return dict(service)
    for service in VPN_SERVICES.values():
        key = _normalize(service["name"])
        if key and (key in q or q in key):
            return dict(service)
    return None
