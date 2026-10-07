# VK-канал: инструкция по пересозданию (база BiziBox-2.1)

> Полная выкройка для повторной реализации VK-канала на чистой базе 2.1.
> Читай по порядку, повторяй шаги. Все упомянутые правки — в файлах, которые
> в 2.1 **уже существуют** (архитектура адаптеров та же, что в 2.0).

## Предусловия (со стороны VK)

- Сообщество VK + токен с правом **«Сообщения сообщества»** (не «Управление сообществом»!).
  Ошибка `15: Access denied: no access to call this method` = токен без этого права
  (при этом `groups.getById` работает, а `groups.getLongPollServer` — нет).
- Включён **Long Poll API**: «Работа с API» → «Long Poll API» → «Включить» + событие «Входящее сообщение» (`message_new`).
- `group_id` — число из `vk.com/club<ID>`. **Callback API НЕ нужен** (мы ходим через Long Poll, не через webhook).
- В `requirements.txt` уже есть `httpx==0.27.0` — REST-клиент для VK.

---

## Шаг 1. Новые файлы (создать целиком)

### 1.1 `backend/app/channels/vk.py` — адаптер

```python
import logging
import random
from datetime import datetime, timezone
from typing import Any

import httpx

from .base import BaseChannelAdapter

logger = logging.getLogger(__name__)

VK_API_URL = "https://api.vk.com/method"
DEFAULT_API_VERSION = "5.199"
DEFAULT_POLL_WAIT = 5


class VkApiError(Exception):
    pass


class VkAdapter(BaseChannelAdapter):
    channel_type = "vk"

    def __init__(self, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self._transport = transport
        self._client: httpx.AsyncClient | None = None
        self.config: dict[str, Any] = {}
        self._group_id: int = 0
        self._token: str = ""
        self._api_version: str = DEFAULT_API_VERSION
        self._poll_wait: int = DEFAULT_POLL_WAIT
        self._lp_server: str | None = None
        self._lp_key: str | None = None
        self._lp_ts: str | None = None
        self._user_cache: dict[int, str] = {}

    def _ensure_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=httpx.Timeout(30.0), transport=self._transport)
        return self._client

    async def connect(self, config: dict[str, Any]) -> bool:
        self.config = dict(config)
        self._group_id = int(config.get("group_id") or 0)
        self._token = str(config.get("token") or "")
        self._api_version = str(config.get("api_version") or DEFAULT_API_VERSION)
        self._poll_wait = int(config.get("poll_wait") or DEFAULT_POLL_WAIT)
        if not self._group_id or not self._token:
            logger.error("VK connect error: group_id and token are required")
            return False
        try:
            if not await self._init_long_poll():
                logger.error("VK connect error: failed to get Long Poll server")
                await self.disconnect()
                return False
            await self._api("groups.getById", group_id=self._group_id)
            return True
        except Exception as e:
            logger.error("VK connect error: %s", e)
            await self.disconnect()
            return False

    async def disconnect(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None
        self._lp_server = None
        self._lp_key = None
        self._lp_ts = None

    async def _api(self, method: str, **params: Any) -> Any:
        client = self._ensure_client()
        payload: dict[str, Any] = {"v": self._api_version, "access_token": self._token}
        payload.update(params)
        resp = await client.post(f"{VK_API_URL}/{method}", data=payload)
        resp.raise_for_status()
        data = resp.json()
        if data.get("error"):
            err = data["error"]
            raise VkApiError(f"{err.get('error_code')}: {err.get('error_msg')}")
        return data.get("response")

    async def _init_long_poll(self) -> bool:
        resp = await self._api("groups.getLongPollServer", group_id=self._group_id)
        if not isinstance(resp, dict):
            return False
        self._lp_server = resp.get("server")
        self._lp_key = resp.get("key")
        self._lp_ts = str(resp.get("ts", ""))
        return bool(self._lp_server and self._lp_key)

    async def _long_poll_check(self) -> list[dict[str, Any]]:
        if not self._lp_server or not self._lp_key:
            return []
        client = self._ensure_client()
        resp = await client.get(
            self._lp_server,
            params={"act": "a_check", "key": self._lp_key, "ts": self._lp_ts or "",
                    "wait": self._poll_wait, "mode": 2, "version": 3},
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("failed"):
            logger.warning("VK long poll failed=%s — re-initializing", data.get("failed"))
            await self._init_long_poll()
            return []
        if data.get("ts"):
            self._lp_ts = str(data["ts"])
        updates: list[dict[str, Any]] = data.get("updates", [])
        return updates

    async def _resolve_users(self, user_ids: set[int]) -> dict[int, str]:
        names: dict[int, str] = {}
        to_fetch = [uid for uid in user_ids if uid not in self._user_cache]
        if to_fetch:
            try:
                resp = await self._api("users.get", user_ids=",".join(str(u) for u in to_fetch))
                for u in resp:
                    uid = int(u.get("id"))
                    name = " ".join(filter(None, [u.get("first_name"), u.get("last_name")])).strip()
                    self._user_cache[uid] = name or f"id{uid}"
            except Exception as e:
                logger.warning("VK users.get error: %s", e)
        for uid in user_ids:
            names[uid] = self._user_cache.get(uid, f"id{uid}")
        return names

    @staticmethod
    def _unwrap_message(obj: Any) -> dict[str, Any] | None:
        if not isinstance(obj, dict):
            return None
        message = obj.get("message")
        if isinstance(message, dict):
            return message
        return obj

    async def fetch_messages(self, since: datetime | None = None, limit: int = 50) -> list[dict[str, Any]]:
        if self._client is None or not self._lp_server or not self._lp_key:
            return []
        try:
            updates = await self._long_poll_check()
        except Exception as e:
            logger.warning("VK fetch error: %s", e)
            return []
        user_ids: set[int] = set()
        for update in updates:
            if update.get("type") != "message_new":
                continue
            msg = self._unwrap_message(update.get("object"))
            if not msg:
                continue
            from_id = int(msg.get("from_id") or msg.get("peer_id") or 0)
            if from_id > 0:
                user_ids.add(from_id)
        await self._resolve_users(user_ids)
        messages: list[dict[str, Any]] = []
        for update in updates:
            if update.get("type") != "message_new":
                continue
            msg = self._unwrap_message(update.get("object"))
            if not msg:
                continue
            converted = self._message_to_dict(msg)
            if converted is not None:
                messages.append(converted)
                if len(messages) >= limit:
                    break
        return messages

    def _message_to_dict(self, msg: dict[str, Any]) -> dict[str, Any] | None:
        from_id = int(msg.get("from_id") or msg.get("peer_id") or 0)
        peer_id = int(msg.get("peer_id") or from_id or 0)
        if peer_id == 0:
            return None
        direction = "outgoing" if from_id == -self._group_id else "incoming"
        date = msg.get("date")
        created_at = (datetime.fromtimestamp(int(date), tz=timezone.utc).replace(tzinfo=None)
                      if date else datetime.now(timezone.utc).replace(tzinfo=None))
        contact_id = from_id if from_id > 0 else peer_id
        return {
            "channel": "vk",
            "channel_id": str(peer_id),
            "message_id": str(msg.get("conversation_message_id") or msg.get("id") or ""),
            "direction": direction,
            "contact_id": str(contact_id),
            "contact_name": self._user_cache.get(contact_id, f"id{contact_id}"),
            "contact_type": "vk",
            "content": msg.get("text") or "",
            "reply_to": None,
            "status": "read" if direction == "outgoing" else "unread",
            "created_at": created_at,
            "attachments": [],
        }

    async def send_message(self, channel_id: str, text: str, reply_to: str | None = None,
                           subject: str | None = None) -> dict[str, Any]:
        if self._client is None:
            raise Exception("VK client not connected")
        params: dict[str, Any] = {"peer_id": int(channel_id), "message": text,
                                  "random_id": random.randint(0, 2**63 - 1)}
        if reply_to:
            params["reply_to"] = int(reply_to)
        message_id = await self._api("messages.send", **params)
        return {"channel": "vk", "channel_id": str(channel_id),
                "message_id": str(message_id) if message_id else None, "content": text,
                "created_at": datetime.now(timezone.utc).replace(tzinfo=None)}

    async def get_dialog(self, channel_id: str, limit: int = 50) -> list[dict[str, Any]]:
        if self._client is None:
            return []
        try:
            resp = await self._api("messages.getHistory", peer_id=int(channel_id), count=limit)
        except Exception as e:
            logger.warning("VK getHistory error: %s", e)
            return []
        items = resp.get("items", []) if isinstance(resp, dict) else []
        result: list[dict[str, Any]] = []
        for m in items:
            from_id = int(m.get("from_id") or 0)
            direction = "outgoing" if from_id == -self._group_id else "incoming"
            date = m.get("date")
            created_at = (datetime.fromtimestamp(int(date), tz=timezone.utc).replace(tzinfo=None)
                          if date else datetime.now(timezone.utc).replace(tzinfo=None))
            result.append({
                "message_id": str(m.get("conversation_message_id") or m.get("id") or ""),
                "direction": direction,
                "content": m.get("text") or "",
                "created_at": created_at,
            })
        return result
```

### 1.2 `backend/app/routers/channels/vk.py` — роутер

```python
import logging
from typing import Any

from cryptography.fernet import InvalidToken
from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ...config import settings
from ...database import get_session
from ...deps import get_poll_service
from ...repositories.channel import ChannelRepository
from ...schemas.channel import ChannelConnectVK
from ...services.settings_service import get_poll_interval
from ...utils.crypto import decrypt, encrypt
from .base import router

logger = logging.getLogger(__name__)


@router.post("/vk/connect")
async def connect_vk(data: ChannelConnectVK, session: AsyncSession = Depends(get_session)) -> dict[str, Any]:
    repo = ChannelRepository(session)
    existing = await repo.get_by_type("vk")
    for ch in existing:
        if ch.is_connected:
            raise HTTPException(status_code=400, detail="VK already connected")
    group_id = data.group_id or settings.VK_GROUP_ID
    token = data.token or settings.VK_ACCESS_TOKEN
    if not group_id or not token:
        raise HTTPException(status_code=400, detail="Укажите group_id и token VK (или заполните .env)")
    config = {"group_id": group_id, "token": encrypt(token)}
    if existing:
        channel = existing[0]
        await repo.update(channel.id, config=config)
    else:
        channel = await repo.create(type="vk", name="VK", config=config, is_connected=False)
    await session.commit()
    try:
        from ...channels.vk import VkAdapter
        adapter = VkAdapter()
        connected = await adapter.connect({"group_id": group_id, "token": token})
        if not connected:
            raise HTTPException(status_code=400, detail="Ошибка подключения к VK. Проверьте токен.")
        await repo.update(channel.id, is_connected=True)
        await session.commit()
        ps = get_poll_service()
        if ps:
            ps.register_channel("vk", adapter)
            ps.start("vk", await get_poll_interval(session, "vk_poll_interval", settings.VK_POLL_INTERVAL))
        return {"status": "connected", "message": "VK подключён",
                "polling": bool(ps and ps.is_running("vk")) if ps else False}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("VK connect error: %s", e)
        raise HTTPException(status_code=500, detail=f"Ошибка подключения: {str(e)}")


@router.post("/vk/reconnect-stored")
async def reconnect_vk_stored(session: AsyncSession = Depends(get_session)) -> dict[str, Any]:
    repo = ChannelRepository(session)
    existing = await repo.get_by_type("vk")
    if not existing:
        raise HTTPException(status_code=404, detail="VK канал не найден. Сначала подключите его.")
    channel = existing[0]
    cfg: Any = channel.config or {}
    group_id = cfg.get("group_id") or settings.VK_GROUP_ID
    token: Any = cfg.get("token") or settings.VK_ACCESS_TOKEN
    if not group_id:
        raise HTTPException(status_code=400, detail="Сохранённый group_id не найден. Подключитесь заново.")
    try:
        from ...channels.vk import VkAdapter
        try:
            token = decrypt(token)
        except InvalidToken:
            pass
        ps = get_poll_service()
        if ps:
            old = ps.get_channel("vk")
            if old:
                try:
                    await old.disconnect()
                except Exception:
                    pass
            await ps.stop("vk")
        adapter = VkAdapter()
        connected = await adapter.connect({"group_id": group_id, "token": token})
        if not connected:
            raise HTTPException(status_code=400, detail="Ошибка подключения к VK. Проверьте токен.")
        await repo.update(channel.id, is_connected=True)
        await session.commit()
        if ps:
            ps.register_channel("vk", adapter)
            ps.start("vk", await get_poll_interval(session, "vk_poll_interval", settings.VK_POLL_INTERVAL))
        return {"status": "connected", "message": "VK переподключён",
                "polling": bool(ps and ps.is_running("vk")) if ps else False}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("VK reconnect-stored error: %s", e)
        raise HTTPException(status_code=500, detail=f"Ошибка переподключения: {str(e)}")
```

### 1.3 `frontend/src/components/channels/VkConnect.tsx`

```tsx
import { useState, useEffect } from 'react'
import { Info, MessageCircle } from 'lucide-react'
import Button from '../common/Button'
import { channelApi } from '../../api/client'
import { settingsApi } from '../../api/settings'

interface VkConnectProps { onConnected: () => void }

function VkConnect({ onConnected }: VkConnectProps) {
  const [form, setForm] = useState({ group_id: '', token: '' })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    settingsApi.onboardingConfig().then(config => {
      if (config.vk) {
        setForm(prev => ({
          ...prev,
          group_id: config.vk?.group_id ? String(config.vk.group_id) : prev.group_id,
          token: config.vk?.token || prev.token,
        }))
      }
    }).catch(() => {})
  }, [])

  const connect = async () => {
    setLoading(true); setError(null)
    try {
      await channelApi.connectVk({
        group_id: form.group_id ? Number(form.group_id) : undefined,
        token: form.token || undefined,
      })
      onConnected()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Ошибка подключения')
    } finally { setLoading(false) }
  }

  return (
    <div className="p-4 rounded-xl border border-gray-200 bg-white space-y-3">
      <div className="flex items-center gap-2">
        <MessageCircle className="w-5 h-5 text-blue-600" />
        <span className="font-medium text-gray-900">Подключить ВКонтакте</span>
      </div>
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 flex items-start gap-2">
        <Info className="w-4 h-4 text-blue-600 mt-0.5 shrink-0" />
        <div className="text-xs text-blue-700 space-y-1">
          <p className="font-medium">Как получить данные</p>
          <p>1. Создайте сообщество на vk.com и включите «Сообщения сообщества».</p>
          <p>2. «Управление» → «Работа с API» → «Ключи доступа» → создайте ключ с правом «Сообщения сообщества».</p>
          <p>3. Включите Long Poll API и событие «Входящее сообщение».</p>
          <p className="text-blue-500">Поля можно оставить пустыми — данные возьмутся из .env.</p>
        </div>
      </div>
      <div className="grid grid-cols-1 gap-3">
        <input type="text" value={form.group_id}
          onChange={(e) => setForm(prev => ({ ...prev, group_id: e.target.value }))}
          placeholder="ID сообщества (например, 12345678)"
          className="px-3 py-2 rounded-lg border border-gray-300 text-sm outline-none focus:border-primary focus:ring-1 focus:ring-primary" />
        <input type="password" value={form.token}
          onChange={(e) => setForm(prev => ({ ...prev, token: e.target.value }))}
          placeholder="Токен (ключ доступа)"
          className="px-3 py-2 rounded-lg border border-gray-300 text-sm outline-none focus:border-primary focus:ring-1 focus:ring-primary" />
      </div>
      {error && <p className="text-sm text-red-600">{error}</p>}
      <Button onClick={connect} disabled={loading}>{loading ? 'Подключение...' : 'Подключить'}</Button>
    </div>
  )
}

export default VkConnect
```

### 1.4 Тесты

- `backend/tests/test_vk_adapter.py` — 9 тестов через `httpx.MockTransport`:
  connect требует group_id+token / connect success / connect bad-token=False / no-client ops /
  fetch parses message_new / fetch outgoing / fetch error→[] / send_message / get_dialog.
  Хелпер: `VkAdapter(transport=httpx.MockTransport(handler))`, handler маршрутизирует по `request.url.host`
  (`api.vk.com` → метод из path, `lp.vk.com` → longpoll-ответ).
- `backend/tests/test_vk_channel.py` — 5 тестов: `get_or_create` дедуп по vk_id, `get_by_vk_id`,
  фильтр `channel="vk"`, `_resolve_channel_id` (vk_id), `_vk_config` decrypt.

---

## Шаг 2. Backend-правки (в существующих файлах 2.1)

### 2.1 `config.py`
- После `EMAIL_POLL_INTERVAL` добавить:
  ```python
  VK_GROUP_ID: int = 0
  VK_ACCESS_TOKEN: str = ""
  VK_2FA_PASSWORD: str = ""
  VK_POLL_INTERVAL: int = 10
  ```
- В `_SENSITIVE_FIELDS` добавить `"VK_ACCESS_TOKEN"` и `"VK_2FA_PASSWORD"`.
- В конец файла (после `settings = Settings()`) добавить `update_env_file(updates: dict[str, str])`:
  читает `.env` построчно, для ключа из `updates` — заменяет значение, для отсутствующего — дописывает,
  остальные строки/комментарии не трогает, пишет обратно в `Path(".env")`.

### 2.2 `services/channel_service.py`
- Импорт: `from ..channels.vk import VkAdapter`.
- В `restore_channels`: в начало — `vk_interval = await settings_repo.get("vk_poll_interval")` (+ fallback на `settings.VK_POLL_INTERVAL`);
  после `elif channel.type == "email":` добавить `elif channel.type == "vk":` — `VkAdapter()`, `connect(self._vk_config(cfg))`,
  `register_channel("vk", adapter)`, `start("vk", int(vk_interval), since=...)`.
- В `_poll_interval`: ветка `elif channel_type == "vk": key, default = "vk_poll_interval", settings.VK_POLL_INTERVAL`.
- В `_connect_saved`: после email-ветки — `if channel.type == "vk":` (если нет токена ни в cfg, ни в settings → None;
  `VkAdapter()` + `_try_connect(self._vk_config(cfg))`).
- Добавить хелпер `_vk_config(cfg)` (после `_with_user_paths`): копирует cfg, дешифрует `token` через `_maybe_decrypt`,
  `setdefault("group_id", settings.VK_GROUP_ID)`, если токен пуст — `settings.VK_ACCESS_TOKEN`.

### 2.3 `services/channel_message_service.py`
- `process_incoming`: после `elif channel == "email" and not contact.email:` добавить
  `elif channel == "vk" and not contact.vk_id: await self.contact_repo.update(int(contact.id), vk_id=contact_id)`.
- `send_reply` и `send_file_reply`: после `elif original.channel == "email":` добавить
  `elif original.channel == "vk": channel_id = str(contact.vk_id) if contact and contact.vk_id else None`
  (в обоих местах — использовать `replaceAll`).
- `_resolve_channel_id`: после `elif channel == "email":` добавить `elif channel == "vk": ...` (то же самое).

### 2.4 `routers/channels/__init__.py` + `base.py`
- `__init__.py`: в tuple импортов добавить `vk,  # noqa: F401`.
- `base.py` в `channel_health`: после `elif channel.type == "telegram":` добавить
  `elif channel.type == "vk": alive = getattr(adapter, "_client", None) is not None`.

### 2.5 `schemas/channel.py`
- После `ChannelConnectEmail` добавить:
  ```python
  class ChannelConnectVK(BaseModel):
      group_id: Optional[int] = Field(default=None, gt=0)
      token: Optional[str] = Field(default=None, min_length=1)
  ```
- Паттерн `channel: str = Field(..., pattern=r"^(telegram|email)$")` → `r"^(telegram|email|vk)$"` (replaceAll — 2 места).

### 2.6 `models/contact.py`
- После `telegram_username` добавить `vk_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)`.
- В `__table_args__` после `uq_contacts_owner_telegram` добавить `uq_contacts_owner_vk` (unique, owner_id+vk_id,
  `sqlite_where=text("vk_id IS NOT NULL")`).

### 2.7 Миграция `migrations/versions/<hex>_vk_contact_id.py`
- **down_revision = `g1h2i3j4k5l6`** (head 2.1!). `add_column vk_id String(100) nullable` +
  `create_index('uq_contacts_owner_vk', ['owner_id','vk_id'], unique=True, sqlite_where=sa.text('vk_id IS NOT NULL'))`.
  **БЕЗ** отдельного `ix_contacts_vk_id` (иначе index-parity тест упадёт).

### 2.8 `repositories/contact.py`
- `get_by_vk_id(vk_id, include_deleted=True)` — по образцу `get_by_email`.
- `get_or_create`: после email-ветки — `if channel == "vk" and channel_id:` дедуп через `get_by_vk_id` (+ restore, + name update).
  В kwargs — `elif channel == "vk" and channel_id: kwargs["vk_id"] = channel_id`.
- `get_all`: после `elif channel == "email":` — `elif channel == "vk": query.where(self.model.vk_id.is_not(None))`.

### 2.9 `routers/messages.py`
- `send_new` и `forward_message`: `for ct in ("telegram", "email"):` → `("telegram", "email", "vk")` (replaceAll — 2 места).
- `forward_message`: после `elif target.email:` — `elif target.vk_id: channel, recipient = "vk", str(target.vk_id)`.

### 2.10 `services/contact_service.py`
- В двух местах, где строится `channels`/`channel_types` (bulk-ответ и `_to_response`): после
  `if contact.email: channels.append("email")` добавить `if contact.vk_id: channels.append("vk")`.

### 2.11 `routers/settings.py`
- Импорт: `from ..config import DEFAULT_OWNER_ID, settings, update_env_file`.
- Схема `VkConfig` (group_id/password_2fa/token) + поле `vk: Optional[VkConfig] = None` в `OnboardingComplete`.
- `channel_map` в update_settings: добавить `"vk_poll_interval": "vk"`.
- `onboarding_complete`: после email-блока — если `data.vk` с group_id и token: `update_env_file({"VK_GROUP_ID": str(...), "VK_ACCESS_TOKEN": token})` (+ `VK_2FA_PASSWORD`, если задан) и обновить `settings.VK_*` in-memory.

---

## Шаг 3. Frontend-правки

### 3.1 `types/channel.ts`
- Добавить `VkConnectRequest { group_id?: number; token?: string }`.

### 3.2 `api/channels.ts`
- Импорт + `VkConnectRequest`; добавить `connectVk` (`POST /channels/vk/connect`) и `reconnectVkStored` (`POST /channels/vk/reconnect-stored`).

### 3.3 `utils/channelIcons.ts`
- Импорт `MessageCircle`; `vk: MessageCircle` в `channelIcons`.

### 3.4 `pages/Channels.tsx`
- Импорт `VkConnect`; `vkChannel`/`hasVk`; `handleReconnectVkStored`; блок переподключения `reconnectChannel?.type === 'vk'`;
  в грид «Добавить канал» — `{!hasVk && !reconnectChannel && <VkConnect onConnected={handleConnected} />}`;
  условие «Все каналы подключены» → `hasTelegram && hasEmail && hasVk`.

### 3.5 `components/inbox/ComposerModal.tsx`
- `type ChannelType = 'telegram' | 'email' | 'vk'`; массив `CHANNELS` (3 канала с иконками, vk=MessageCircle);
  `RECIPIENT_PLACEHOLDER` для vk = 'ID пользователя VK (число)'; `sendable = connectedSet.has(channel)`;
  селектор рендерится через `CHANNELS.map`; сообщение «нет каналов» обновить на 3 канала.

### 3.6 `pages/Inbox.tsx`, `pages/Contacts.tsx`, `pages/Archive.tsx`
- Inbox: `CHANNEL_FILTERS` + `{ key: 'vk', label: 'VK', icon: MessageCircle }`; пустой-label через lookup
  `CHANNEL_FILTERS.find(f => f.key === activeChannel)?.label ?? activeChannel`.
- Contacts: `channelOptions` + `{ key: 'vk', label: 'VK' }`.
- Archive: + строка `{m.channel === 'vk' && <MessageCircle ... />}`.

### 3.7 Онбординг
- `api/settings.ts`: в `OnboardingData` — `vk?: { group_id?: number; password_2fa?: string; token?: string }`.
- `pages/OnboardingSteps.tsx`: в `StepData` — `vk: { group_id: string; password_2fa: string; token: string }`;
  компонент `VkStep` (3 поля + подсказка, как у Email/TG); импорт `MessageCircle`.
- `pages/Onboarding.tsx`: `defaultData` + vk; шаг VK (5 шагов: TG → Email → VK → Прокси → Готово);
  prefill из `config.vk`; payload в `handleFinish`; summary; `loadProgress` — deep-merge секций
  (`vk: { ...defaultData.vk, ...(d.vk || {}) }`) чтобы старый localStorage без vk не падал.
- `components/channels/VkConnect.tsx` — prefill из `config.vk` (см. Шаг 1.3).

---

## Шаг 4. Сборка и тесты

- `backend/.env.example`: добавить блок VK (`VK_GROUP_ID=0`, `VK_ACCESS_TOKEN=your_...`, `VK_2FA_PASSWORD=`, `VK_POLL_INTERVAL=10`).
- `backend/BiziBox.spec`: в `hiddenimports` добавить `"httpx", "httpcore"` (для VK REST).
- `backend/tests/migrations/test_stale_revision.py`: `NEW_HEAD` → новый head (ревизия vk-миграции).
- `backend/tests/.../Onboarding.test.tsx`: `SAVED_DATA` + vk; `renderOnFinishStep` → `step: 4`.
- Проверки: `python -m pytest` (backend), `npx tsc --noEmit` / `npm run lint` / `npm test` / `npm run build` (frontend).

---

## Питфоллы (КРИТИЧНО, не пропускать)

1. **down_revision миграции = `g1h2i3j4k5l6`** (head 2.1). Если поставить старый head 2.0 — получится вторая голова, упадут 5 миграционных тестов.
2. **Index parity**: в модели и миграции одинаковый набор индексов на contacts (только `uq_contacts_owner_vk`, без лишнего `ix_contacts_vk_id`).
3. **Токен**: право «Сообщения сообщества», иначе ошибка `15`. Признак — `groups.getById` OK, `groups.getLongPollServer` нет.
4. **test_stale_revision.py** hardcode head — обновить `NEW_HEAD`.
5. **Onboarding.test.tsx** hardcode количество шагов — обновить на 5.
6. **BiziBox.spec** — без `httpx` в hiddenimports exe упадёт при импорте VK.
7. `update_env_file` пишет в `Path(".env")` от cwd (backend/) — в тестах не вызывать с реальным .env.
