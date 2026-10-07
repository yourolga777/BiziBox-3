"""Entry point for PyInstaller portable build (desktop mode).

Запускает FastAPI-сервер в фоновом потоке, открывает браузер с интерфейсом и
держит иконку в системном трее («Открыть» / «Выход»). Выход через трей
корректно останавливает сервер.

При первом запуске создаёт ``.env`` рядом с исполняемым файлом: production-
настройки, сгенерированные SECRET_KEY/ENCRYPTION_KEY и предзаполненные
Telegram/proxy значения.
"""

import os
import secrets
import socket
import sys
import threading
import time
import webbrowser
from pathlib import Path

HOST = "127.0.0.1"
PORT = 7910
PORT_RANGE = range(7910, 7926)
BASE_URL = f"http://{HOST}:{PORT}"

# Предзаполненные значения. api_id/api_hash принадлежат приложению, а не
# пользователю (вход идёт по номеру телефона). Прокси не навязывается —
# пользователь указывает свой при онбординге или в Настройках.
TELEGRAM_API_ID = "31317005"
TELEGRAM_API_HASH = "35292436c9eaf4972b461d783dedfd09"
PROXY_ENABLED = "False"

_server = None


def _app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def _ensure_stdio() -> None:
    # В windowed-режиме (console=False) PyInstaller ставит stdout/stderr в None,
    # из-за чего падает logging. Перенаправляем в devnull.
    if sys.stdout is None:
        sys.stdout = open(os.devnull, "w", encoding="utf-8")
    if sys.stderr is None:
        sys.stderr = open(os.devnull, "w", encoding="utf-8")


def _ensure_data_dirs() -> None:
    for sub in ("logs", "sessions"):
        os.makedirs(os.path.join("data", sub), exist_ok=True)


def _ensure_env_file() -> None:
    env_path = Path(".env")
    if env_path.exists():
        return

    from cryptography.fernet import Fernet

    encryption_key = Fernet.generate_key().decode()
    secret_key = secrets.token_hex(32)
    content = (
        "# BiziBox — файл создан автоматически при первом запуске.\n"
        "# Любые настройки можно менять вручную.\n"
        "ENVIRONMENT=production\n"
        f"SECRET_KEY={secret_key}\n"
        f"ENCRYPTION_KEY={encryption_key}\n"
        f"TELEGRAM_API_ID={TELEGRAM_API_ID}\n"
        f"TELEGRAM_API_HASH={TELEGRAM_API_HASH}\n"
        f"TELEGRAM_PROXY_ENABLED={PROXY_ENABLED}\n"
    )
    env_path.write_text(content, encoding="utf-8")


def _pick_free_port() -> int:
    """Первый свободный порт из PORT_RANGE.

    Порт может быть занят другим инстансом BiziBox/IziBox или любым
    сторонним процессом — чтобы никого не трогать, выбираем свободный.

    Важно: без SO_REUSEADDR — на Windows эта опция позволяет забиндить
    сокет на уже занятый порт, и проба вернёт ложноположительный результат.
    """
    for port in PORT_RANGE:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.bind((HOST, port))
                return port
            except OSError:
                continue
    raise RuntimeError(
        f"Нет свободного порта в диапазоне {PORT_RANGE.start}-{PORT_RANGE.stop - 1}"
    )


def _start_server(application) -> None:
    global _server
    import uvicorn

    config = uvicorn.Config(application, host=HOST, port=PORT, log_level="info")
    _server = uvicorn.Server(config)
    _server.run()


def _wait_ready(timeout: float = 30.0) -> bool:
    import urllib.request

    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"{BASE_URL}/api/health", timeout=1.0) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            pass
        time.sleep(0.25)
    return False


def _tray_image():
    from PIL import Image, ImageDraw, ImageFont

    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle((2, 2, 61, 61), radius=14, fill=(37, 99, 235, 255))
    try:
        font = ImageFont.truetype("arial.ttf", 38)
    except Exception:
        font = ImageFont.load_default()
    draw.text((17, 8), "B", fill=(255, 255, 255, 255), font=font)
    return img


def _find_private_browser() -> tuple[str | None, list[str]]:
    """Ищет установленный браузер и флаг приватного/инкогнито-режима."""
    import shutil

    candidates = [
        ("msedge", ["--inprivate", "--force-device-scale-factor=1"]),
        ("chrome", ["--incognito", "--force-device-scale-factor=1"]),
        ("firefox", ["--private-window"]),
    ]
    for name, flags in candidates:
        path = shutil.which(name)
        if path:
            return path, flags

    try:
        import winreg

        for key, flags in [
            (
                r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\msedge.exe",
                ["--inprivate", "--force-device-scale-factor=1"],
            ),
            (
                r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe",
                ["--incognito", "--force-device-scale-factor=1"],
            ),
        ]:
            try:
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key) as k:
                    path = winreg.QueryValue(k, None)
                    if path:
                        return str(path), flags
            except OSError:
                continue
    except Exception:
        pass

    return None, []


def _open_incognito(url: str) -> None:
    """Открывает URL в новом окне браузера в режиме инкогнито."""
    import subprocess

    path, flags = _find_private_browser()
    if path:
        try:
            subprocess.Popen([path, *flags, url])
            return
        except Exception:
            pass
    webbrowser.open(url)


def _open_ui(*_args) -> None:
    _open_incognito(BASE_URL)


def _run_tray() -> None:
    import pystray  # type: ignore[import-untyped]

    menu = pystray.Menu(
        pystray.MenuItem("Открыть BiziBox", _open_ui, default=True),
        pystray.MenuItem("Выход", lambda icon, item: icon.stop()),
    )
    icon = pystray.Icon("BiziBox", _tray_image(), "BiziBox", menu)
    icon.run()


def _shutdown() -> None:
    if _server is not None:
        _server.should_exit = True


def main() -> None:
    global PORT
    global BASE_URL

    _ensure_stdio()
    os.chdir(_app_dir())
    _ensure_data_dirs()
    _ensure_env_file()

    # Импорт в главном потоке: pyrogram на этапе импорта вызывает
    # asyncio.get_event_loop(), что падает в фоновом потоке без event loop.
    from app.main import app as application

    PORT = _pick_free_port()
    BASE_URL = f"http://{HOST}:{PORT}"

    thread = threading.Thread(target=_start_server, args=(application,), daemon=True)
    thread.start()
    _wait_ready()
    _open_incognito(BASE_URL)

    try:
        _run_tray()
    except Exception:
        import logging

        logging.getLogger(__name__).exception(
            "Не удалось запустить иконку в трее; сервер продолжает работу"
        )
        thread.join()
    else:
        _shutdown()
        thread.join(timeout=5)


if __name__ == "__main__":
    main()
