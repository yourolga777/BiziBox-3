import json
import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import DEFAULT_OWNER_ID, settings, update_env_file
from ..database import get_async_session_maker, get_session, init_db
from ..deps import get_current_user, set_poll_service
from ..models import UserModel
from ..schemas.settings import SettingsUpdate
from ..services.channel_message_service import ChannelMessageService
from ..services.channel_service import ChannelService
from ..services.poll_service import PollService
from ..services.seed_service import seed_default_owner
from ..services.settings_service import SettingsService
from ..user_context import (
    ensure_user_data_dir,
    get_active_login,
    get_user_onboarding_file,
    set_active_login,
)
from ..utils.crypto import decrypt, encrypt
from ..utils.masking import mask_secret

logger = logging.getLogger(__name__)

router = APIRouter()


def _mask_proxy_secrets(data: dict[str, Any]) -> dict[str, Any]:
    proxy_cfg = data.get("proxy_config")
    if isinstance(proxy_cfg, dict):
        for key in ("password", "secret"):
            if proxy_cfg.get(key):
                proxy_cfg[key] = mask_secret(str(proxy_cfg[key]))
    return data


@router.get("/")
async def get_settings(
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> dict[str, Any]:
    service = SettingsService(session, owner_id=int(current_user.id))
    return _mask_proxy_secrets(await service.get_all())


@router.patch("/")
async def update_settings(
    data: SettingsUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> dict[str, Any]:
    service = SettingsService(session, owner_id=int(current_user.id))
    old = await service.get_all()

    values = dict(data.values)

    # Не затирать пароль/secret прокси пустыми значениями при частичном
    # обновлении: если фронт не прислал новые секреты, сохраняем старые.
    if "proxy_config" in values:
        new_px = values["proxy_config"]
        old_px = old.get("proxy_config")
        if isinstance(new_px, dict) and isinstance(old_px, dict):
            for secret_key in ("password", "secret"):
                if not new_px.get(secret_key) and old_px.get(secret_key):
                    new_px[secret_key] = old_px[secret_key]

    await service.set_many(values)

    changed_intervals = {}
    for key in ("telegram_poll_interval", "email_poll_interval", "vk_poll_interval"):
        if key in values and values[key] != old.get(key):
            changed_intervals[key] = int(values[key])

    if changed_intervals:
        from ..deps import get_poll_service

        ps = get_poll_service()
        if ps:
            channel_map = {
                "telegram_poll_interval": "telegram",
                "email_poll_interval": "email",
                "vk_poll_interval": "vk",
            }
            for key, new_interval in changed_intervals.items():
                channel_type = channel_map[key]
                adapter = ps.get_channel(channel_type)
                if adapter is None:
                    continue
                await ps.stop(channel_type)
                ps.start(channel_type, new_interval)
                logger.info(
                    "Polling interval for %s changed to %ss — restarted",
                    channel_type, new_interval,
                )

    if "proxy_config" in values and values["proxy_config"] != old.get("proxy_config"):
        channel_service = ChannelService(session, owner_id=int(current_user.id))
        await channel_service.reconnect_telegram()

    return _mask_proxy_secrets(await service.get_all())


# --- Onboarding endpoints ---

class TelegramConfig(BaseModel):
    api_id: Optional[int] = None
    api_hash: Optional[str] = None
    phone: Optional[str] = None
    password_2fa: Optional[str] = None


class EmailConfig(BaseModel):
    email: Optional[str] = None
    password: Optional[str] = None
    imap_host: Optional[str] = None
    imap_port: Optional[int] = 993
    smtp_host: Optional[str] = None
    smtp_port: Optional[int] = 465


class VkConfig(BaseModel):
    group_id: Optional[int] = None
    password_2fa: Optional[str] = None
    token: Optional[str] = None


class ProxyConfig(BaseModel):
    enabled: Optional[bool] = None
    type: Optional[str] = None
    host: Optional[str] = None
    port: Optional[int] = None
    username: Optional[str] = None
    password: Optional[str] = None
    secret: Optional[str] = None
    mode: Optional[str] = None  # direct | system_vpn | custom_proxy


class OnboardingComplete(BaseModel):
    login: str = Field(..., min_length=1, max_length=100)
    telegram: Optional[TelegramConfig] = None
    email: Optional[EmailConfig] = None
    vk: Optional[VkConfig] = None
    proxy: Optional[ProxyConfig] = None


def _read_onboarding_config(login: str) -> dict[str, Any]:
    config: Dict[str, Any] = {}
    path = get_user_onboarding_file(login)
    if path.exists():
        try:
            encrypted = path.read_text(encoding="utf-8")
            decrypted = decrypt(encrypted)
            if decrypted:
                config = json.loads(decrypted)
        except Exception as e:
            logger.error("Не удалось расшифровать ONBOARDING_FILE для %s: %s", login, e)
            config = {}
    return config


@router.get("/onboarding-status")
async def onboarding_status() -> dict[str, Any]:
    login = get_active_login()
    if not login:
        return {"onboarded": False}

    session_maker = get_async_session_maker(login)
    async with session_maker() as session:
        service = SettingsService(session, owner_id=DEFAULT_OWNER_ID)
        onboarded = await service.get("onboarded")
        return {"onboarded": onboarded is True, "login": login}


@router.get("/onboarding-config")
async def get_onboarding_config(login: Optional[str] = None) -> dict[str, Any]:
    active = login or get_active_login()
    config = _read_onboarding_config(active) if active else {}

    # API id/hash не показываем — приложение всегда использует свои серверные
    # значения. Секреты (2FA Telegram, пароль почты) НЕ маскируем: приложение
    # локальное, данные хранятся на компьютере пользователя и нужны для
    # предзаполнения при повторном входе.
    tg = config.get("telegram")
    if isinstance(tg, dict):
        tg.pop("api_id", None)
        tg.pop("api_hash", None)
        tg.pop("api_hash_set", None)

    px = config.get("proxy")
    if isinstance(px, dict):
        if px.get("password"):
            px["password"] = mask_secret(str(px["password"]))
        else:
            px.pop("password", None)
        if px.get("secret"):
            px["secret"] = mask_secret(str(px["secret"]))
        else:
            px.pop("secret", None)

    return config


@router.post("/onboarding-complete")
async def onboarding_complete(data: OnboardingComplete) -> dict[str, Any]:
    login = data.login.strip()
    if not login:
        raise HTTPException(status_code=400, detail="Login is required")

    ensure_user_data_dir(login)
    await init_db(login)

    session_maker = get_async_session_maker(login)
    async with session_maker() as session:
        # Ensure the owner row matches the login.
        await session.run_sync(seed_default_owner)  # type: ignore[arg-type]
        from ..repositories.user import UserRepository
        user_repo = UserRepository(session)
        user = await user_repo.get_by_id(DEFAULT_OWNER_ID)
        if user is not None and user.username != login:
            user.username = login
            await session.flush()

        payload = data.model_dump(exclude_none=True)
        payload.pop("login", None)
        encrypted = encrypt(json.dumps(payload, ensure_ascii=False, default=str))
        get_user_onboarding_file(login).write_text(encrypted, encoding="utf-8")

        service = SettingsService(session, owner_id=DEFAULT_OWNER_ID)

        if data.telegram:
            tg = data.telegram
            if tg.api_id:
                await service.set("telegram_api_id", tg.api_id)
            if tg.api_hash:
                await service.set("telegram_api_hash", tg.api_hash)
            if tg.phone:
                await service.set("telegram_phone", tg.phone)

        if data.email:
            em = data.email
            if em.email:
                channel_service = ChannelService(session, owner_id=DEFAULT_OWNER_ID)
                email_config: dict[str, Any] = {
                    "email": em.email,
                    "imap_host": em.imap_host,
                    "imap_port": em.imap_port,
                    "smtp_host": em.smtp_host,
                    "smtp_port": em.smtp_port,
                }
                if em.password:
                    email_config["password"] = encrypt(em.password)
                await channel_service.create(
                    channel_type="email",
                    name=em.email,
                    config=email_config,
                )

        if data.vk:
            vk = data.vk
            if vk.group_id and vk.token:
                env_updates = {
                    "VK_GROUP_ID": str(vk.group_id),
                    "VK_ACCESS_TOKEN": vk.token,
                }
                if vk.password_2fa:
                    env_updates["VK_2FA_PASSWORD"] = vk.password_2fa
                update_env_file(env_updates)
                settings.VK_GROUP_ID = vk.group_id
                settings.VK_ACCESS_TOKEN = vk.token
                if vk.password_2fa:
                    settings.VK_2FA_PASSWORD = vk.password_2fa

        if data.proxy:
            px = data.proxy
            proxy_data = px.model_dump(exclude_none=True)
            mode = px.mode or ("custom_proxy" if (px.host and px.port) else "direct")
            proxy_data["mode"] = mode
            proxy_data["enabled"] = mode == "custom_proxy" and bool(px.host and px.port)
            await service.set("proxy_config", proxy_data)

        await service.set("onboarded", True)
        await session.commit()

    set_active_login(login)

    # Restart poll service for the new active user.
    from ..deps import get_poll_service

    old_ps = get_poll_service()
    if old_ps:
        await old_ps.stop_all()
        for _ct, adapter in list(old_ps.channels.items()):
            try:
                await adapter.disconnect()
            except Exception as e:
                logger.error("Error disconnecting old channel: %s", e)

    new_ps = PollService(
        session_factory=session_maker,
        cms_factory=ChannelMessageService,
    )
    set_poll_service(new_ps)
    async with session_maker() as session:
        channel_service = ChannelService(session)
        await channel_service.restore_channels(new_ps)

    return {"onboarded": True, "login": login}


@router.post("/reset-onboarding")
async def reset_onboarding(
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> dict[str, Any]:
    service = SettingsService(session, owner_id=int(current_user.id))
    await service.set("onboarded", False)
    return {"onboarded": False}


@router.post("/auth/logout")
async def logout() -> dict[str, Any]:
    from ..deps import get_poll_service

    ps = get_poll_service()
    if ps:
        await ps.stop_all()
        for _ct, adapter in list(ps.channels.items()):
            try:
                await adapter.disconnect()
            except Exception as e:
                logger.error("Error disconnecting channel on logout: %s", e)
    set_active_login(None)
    return {"onboarded": False}
