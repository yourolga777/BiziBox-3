from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any


class ChannelFetchTimeoutError(Exception):
    """Fetch канала не уложился в отведённый таймаут.

    Отличается от «успешно, 0 новых сообщений» — позволяет вызывающему коду
    (poll_service, download) не обновлять last_polled_at при реальном сбое.
    """


class BaseChannelAdapter(ABC):
    channel_type: str

    @abstractmethod
    async def connect(self, config: dict[str, Any]) -> bool:
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        pass

    @abstractmethod
    async def fetch_messages(
        self,
        since: datetime | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        pass

    @abstractmethod
    async def send_message(
        self,
        channel_id: str,
        text: str,
        reply_to: str | None = None,
        subject: str | None = None,
    ) -> dict[str, Any]:
        pass

    @abstractmethod
    async def get_dialog(
        self,
        channel_id: str,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        pass

    async def download_file(self, file_path: str | None) -> Any:
        raise NotImplementedError(
            f"Channel {self.channel_type} does not support file downloads"
        )

    async def fetch_older_messages(
        self,
        chat_id: str,
        offset_id: int = 0,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Загружает более ранние сообщения из канала (кнопка «Загрузить ещё»)."""
        raise NotImplementedError(
            f"Channel {self.channel_type} does not support fetching older messages"
        )

    async def send_file(
        self,
        channel_id: str,
        file_path: str,
        file_name: str | None = None,
        mime_type: str | None = None,
        reply_to: str | None = None,
        caption: str | None = None,
        subject: str | None = None,
    ) -> dict[str, Any]:
        raise NotImplementedError(
            f"Channel {self.channel_type} does not support file sending"
        )

    async def resolve_channel_id(self, recipient: str) -> str:
        """Преобразует «человеческий» получатель (username/@username или email)
        в channel_id, который понимает send_message. По умолчанию — как есть."""
        return recipient
