import shutil
import sys
from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_DEFAULT_SECRETS = ("change-me-in-production", "dev-secret-key-not-for-production")
_DEFAULT_ENCRYPTION_KEYS = ("change-me-in-production", "dev-encryption-key-not-for-production")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    DATABASE_URL: str = "sqlite+aiosqlite:///./data/bizibox.db"
    ALLOWED_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:5174", "http://localhost:3000"]
    SECRET_KEY: str = "change-me-in-production"
    DEBUG: bool = False

    ENCRYPTION_KEY: str = "change-me-in-production"

    HOST: str = "127.0.0.1"
    PORT: int = 7910
    ENVIRONMENT: str = "development"
    ALLOW_ENCRYPTION_KEY_RESET: bool = False

    TELEGRAM_API_ID: int = 0
    TELEGRAM_API_HASH: str = ""
    TELEGRAM_POLL_INTERVAL: int = 300
    TELEGRAM_PROXY_ENABLED: bool = False
    TELEGRAM_PROXY_TYPE: str = "socks5"
    TELEGRAM_PROXY_HOST: str = ""
    TELEGRAM_PROXY_PORT: int = 9050
    TELEGRAM_PROXY_USERNAME: str = ""
    TELEGRAM_PROXY_PASSWORD: str = ""
    TELEGRAM_PROXY_SECRET: str = ""
    EMAIL_POLL_INTERVAL: int = 60
    VK_GROUP_ID: int = 0
    VK_ACCESS_TOKEN: str = ""
    VK_2FA_PASSWORD: str = ""
    VK_POLL_INTERVAL: int = 10

    OUTBOX_POLL_INTERVAL: int = 15
    OUTBOX_MAX_ATTEMPTS: int = 5
    OUTBOX_BASE_DELAY: int = 5
    OUTBOX_SEND_TIMEOUT: float = 20.0
    CHANNEL_RECONNECT_INTERVAL: int = 60

    RATE_LIMIT_ENABLED: bool = False
    RATE_LIMIT_DEFAULT: str = "60/minute"

    @model_validator(mode="after")
    def _reject_default_secrets_in_production(self) -> "Settings":
        if self.ENVIRONMENT != "development":
            if self.SECRET_KEY in _DEFAULT_SECRETS:
                raise ValueError(
                    "SECRET_KEY не изменён — установите свой в .env перед запуском в production"
                )
            if self.ENCRYPTION_KEY in _DEFAULT_ENCRYPTION_KEYS:
                raise ValueError(
                    "ENCRYPTION_KEY не изменён — установите свой в .env перед запуском в production"
                )
        return self

    @model_validator(mode="after")
    def _reject_wildcard_cors_in_production(self) -> "Settings":
        if self.ENVIRONMENT != "development" and "*" in self.ALLOWED_ORIGINS:
            raise ValueError(
                "ALLOWED_ORIGINS содержит '*' — недопустимо вне development. "
                "Перечислите конкретные origin'ы."
            )
        return self

    _SENSITIVE_FIELDS = frozenset(
        {
            "SECRET_KEY",
            "ENCRYPTION_KEY",
            "TELEGRAM_API_HASH",
            "TELEGRAM_PROXY_PASSWORD",
            "TELEGRAM_PROXY_SECRET",
            "VK_ACCESS_TOKEN",
            "VK_2FA_PASSWORD",
        }
    )

    def __repr__(self) -> str:
        fields = []
        for k, v in self.model_dump().items():
            if k in self._SENSITIVE_FIELDS and v:
                v = self._mask(v)
            fields.append(f"{k}={v!r}")
        return f"Settings({', '.join(fields)})"

    __str__ = __repr__

    @staticmethod
    def _mask(value: str) -> str:
        if len(value) <= 8:
            return "****"
        return value[:4] + "****"


DEFAULT_OWNER_ID: int = 1


def _ensure_env_file() -> None:
    """Создаёт .env из .env.example при первом запуске, если файла нет.

    pydantic-settings читает .env из рабочей директории, поэтому создаём
    файл там же. Источник — .env.example рядом с бэкендом.
    """
    env_path = Path(".env")
    if env_path.exists():
        return
    candidates = (
        Path(".env.example"),
        Path(__file__).resolve().parent.parent / ".env.example",
    )
    for src in candidates:
        if src.exists():
            shutil.copy2(src, env_path)
            return


_ensure_env_file() if "pytest" not in sys.modules else None


settings = Settings()


def update_env_file(updates: dict[str, str]) -> None:
    """Обновляет/добавляет ключи в .env, не трогая остальные строки."""
    env_path = Path(".env")
    existing: list[str] = []
    if env_path.exists():
        existing = env_path.read_text(encoding="utf-8").splitlines()

    updated: set[str] = set()
    out: list[str] = []
    for line in existing:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            out.append(line)
            continue
        key = stripped.split("=", 1)[0].strip()
        if key in updates:
            out.append(f"{key}={updates[key]}")
            updated.add(key)
        else:
            out.append(line)

    for key, value in updates.items():
        if key not in updated:
            out.append(f"{key}={value}")

    env_path.write_text("\n".join(out) + "\n", encoding="utf-8")
