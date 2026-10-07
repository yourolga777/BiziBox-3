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
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(30.0),
                transport=self._transport,
            )
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
        payload: dict[str, Any] = {
            "v": self._api_version,
            "access_token": self._token,
        }
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
            params={
                "act": "a_check",
                "key": self._lp_key,
                "ts": self._lp_ts or "",
                "wait": self._poll_wait,
                "mode": 2,
                "version": 3,
            },
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
                resp = await self._api(
                    "users.get",
                    user_ids=",".join(str(u) for u in to_fetch),
                )
                for u in resp:
                    uid = int(u.get("id"))
                    name = " ".join(
                        filter(None, [u.get("first_name"), u.get("last_name")])
                    ).strip()
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

    async def fetch_messages(
        self,
        since: datetime | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
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
        created_at = (
            datetime.fromtimestamp(int(date), tz=timezone.utc).replace(tzinfo=None)
            if date
            else datetime.now(timezone.utc).replace(tzinfo=None)
        )
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

    async def send_message(
        self,
        channel_id: str,
        text: str,
        reply_to: str | None = None,
        subject: str | None = None,
    ) -> dict[str, Any]:
        if self._client is None:
            raise Exception("VK client not connected")
        params: dict[str, Any] = {
            "peer_id": int(channel_id),
            "message": text,
            "random_id": random.randint(0, 2**63 - 1),
        }
        if reply_to:
            params["reply_to"] = int(reply_to)
        message_id = await self._api("messages.send", **params)
        return {
            "channel": "vk",
            "channel_id": str(channel_id),
            "message_id": str(message_id) if message_id else None,
            "content": text,
            "created_at": datetime.now(timezone.utc).replace(tzinfo=None),
        }

    async def get_dialog(self, channel_id: str, limit: int = 50) -> list[dict[str, Any]]:
        if self._client is None:
            return []
        try:
            resp = await self._api(
                "messages.getHistory",
                peer_id=int(channel_id),
                count=limit,
            )
        except Exception as e:
            logger.warning("VK getHistory error: %s", e)
            return []
        items = resp.get("items", []) if isinstance(resp, dict) else []
        result: list[dict[str, Any]] = []
        for m in items:
            from_id = int(m.get("from_id") or 0)
            direction = "outgoing" if from_id == -self._group_id else "incoming"
            date = m.get("date")
            created_at = (
                datetime.fromtimestamp(int(date), tz=timezone.utc).replace(tzinfo=None)
                if date
                else datetime.now(timezone.utc).replace(tzinfo=None)
            )
            result.append(
                {
                    "message_id": str(
                        m.get("conversation_message_id") or m.get("id") or ""
                    ),
                    "direction": direction,
                    "content": m.get("text") or "",
                    "created_at": created_at,
                }
            )
        return result
