import asyncio
import email
import imaplib
import io
import logging
import smtplib
from datetime import datetime
from email import encoders
from email.message import Message
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any

from ..paths import get_data_dir
from ..utils.email_parser import (
    decode_mime_header,
    extract_attachments,
    extract_body,
    extract_display_name,
    extract_email,
    parse_email_date,
)
from .base import BaseChannelAdapter, ChannelFetchTimeoutError

logger = logging.getLogger(__name__)

_DATA_DIR = get_data_dir()


class EmailAdapter(BaseChannelAdapter):
    channel_type = "email"

    FETCH_TIMEOUT_SECONDS: float = 60

    def __init__(self) -> None:
        self.imap: imaplib.IMAP4_SSL | None = None
        self.smtp: smtplib.SMTP_SSL | None = None
        self.config: dict[str, Any] = {}
        self.data_dir: Path = _DATA_DIR

    async def connect(self, config: dict[str, Any]) -> bool:
        self.config = config
        self.data_dir = Path(config.get("data_dir", _DATA_DIR))

        def _connect() -> bool:
            try:
                imap = imaplib.IMAP4_SSL(
                    config.get("imap_host"),  # type: ignore[arg-type]
                    config.get("imap_port", 993),
                    timeout=30,
                )
                imap.login(config["email"], config["password"])
                imap.select("INBOX")

                smtp = smtplib.SMTP_SSL(
                    config.get("smtp_host"),  # type: ignore[arg-type]
                    config.get("smtp_port", 465),
                    timeout=30,
                )
                smtp.login(config["email"], config["password"])

                self.imap = imap
                self.smtp = smtp
                return True
            except Exception as e:
                logger.error("Email connect error: %s", e)
                return False

        return await asyncio.to_thread(_connect)

    async def disconnect(self) -> None:
        def _disconnect() -> None:
            if self.imap:
                try:
                    self.imap.close()
                    self.imap.logout()
                except Exception:
                    pass
                self.imap = None
            if self.smtp:
                try:
                    self.smtp.quit()
                except Exception:
                    pass
                self.smtp = None

        await asyncio.to_thread(_disconnect)

    async def fetch_messages(
        self,
        since: datetime | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        if not self.imap:
            return []

        def _fetch() -> list[dict[str, Any]]:
            messages = []

            if since:
                date_str = since.strftime("%d-%b-%Y")
                status, search_data = self.imap.search(None, f"SINCE {date_str}")  # type: ignore[union-attr]
            else:
                status, search_data = self.imap.search(None, "ALL")  # type: ignore[union-attr]

            if status != "OK" or not search_data[0]:
                return []

            email_ids = search_data[0].split()
            email_ids = email_ids[-limit:] if len(email_ids) > limit else email_ids

            status_uid, uid_data = self.imap.status("INBOX", "(UIDVALIDITY)")  # type: ignore[union-attr]
            uid_validity = ""
            if status_uid == "OK" and uid_data[0]:
                import re

                decoded = uid_data[0].decode("utf-8", errors="ignore")
                match = re.search(r"UIDVALIDITY\s+(\d+)", decoded)
                if match:
                    uid_validity = match.group(1)

            for email_id in email_ids:
                status, data = self.imap.fetch(email_id, "(RFC822)")  # type: ignore[union-attr]
                if status != "OK":
                    continue

                raw_email = data[0][1]  # type: ignore[index]
                msg = email.message_from_bytes(bytes(raw_email))

                subject = self._decode_mime_header(str(msg.get("Subject", "")))
                from_header = str(msg.get("From", ""))
                from_email = self._extract_email(from_header)
                from_name = extract_display_name(from_header)
                raw_date = msg.get("Date")
                date = self._parse_date(str(raw_date) if raw_date else None)
                body = self._extract_body(msg)
                attachments = extract_attachments(msg, self.data_dir)

                message_id_header = msg.get("Message-ID", "").strip()
                if not message_id_header:
                    message_id_header = f"{email_id}-{uid_validity}"

                messages.append(
                    {
                        "channel": "email",
                        "channel_id": from_email,
                        "message_id": message_id_header,
                        "direction": "incoming",
                        "contact_id": from_email,
                        "contact_name": from_name or from_email,
                        "contact_type": "email",
                        "subject": subject,
                        "content": body,
                        "reply_to": None,
                        "created_at": date or datetime.now(),
                        "attachments": attachments,
                    }
                )

            return messages

        try:
            return await asyncio.wait_for(
                asyncio.to_thread(_fetch),
                timeout=self.FETCH_TIMEOUT_SECONDS,
            )
        except asyncio.TimeoutError:
            logger.warning(
                "Email fetch timed out after %ss — reconnecting",
                self.FETCH_TIMEOUT_SECONDS,
            )
            self.imap = None
            if await self.reconnect():
                try:
                    return await asyncio.wait_for(
                        asyncio.to_thread(_fetch),
                        timeout=self.FETCH_TIMEOUT_SECONDS,
                    )
                except asyncio.TimeoutError:
                    logger.warning(
                        "Email fetch timed out again after %ss",
                        self.FETCH_TIMEOUT_SECONDS,
                    )
            raise ChannelFetchTimeoutError(
                f"Email fetch timed out after {self.FETCH_TIMEOUT_SECONDS}s"
            )
        except (imaplib.IMAP4.abort, OSError, EOFError) as e:
            logger.warning(
                "Email IMAP connection lost (type=%s), reconnecting and retrying once",
                type(e).__name__,
            )
            if await self.reconnect():
                try:
                    return await asyncio.wait_for(
                        asyncio.to_thread(_fetch),
                        timeout=self.FETCH_TIMEOUT_SECONDS,
                    )
                except asyncio.TimeoutError:
                    logger.warning(
                        "Email fetch timed out after %ss",
                        self.FETCH_TIMEOUT_SECONDS,
                    )
            raise ChannelFetchTimeoutError(f"Email fetch failed: {e}")

    async def reconnect(self) -> bool:
        return await self.connect(self.config)

    async def send_message(
        self,
        channel_id: str,
        text: str,
        reply_to: str | None = None,
        subject: str | None = None,
    ) -> dict[str, Any]:
        if not self.smtp:
            raise Exception("SMTP client not connected")

        def _send() -> dict[str, Any]:
            msg = MIMEMultipart()
            msg["From"] = self.config["email"]
            msg["To"] = channel_id
            msg["Subject"] = subject or "Ответ на ваше сообщение"
            if reply_to:
                msg["In-Reply-To"] = reply_to
                msg["References"] = reply_to

            msg.attach(MIMEText(text, "plain", "utf-8"))

            self.smtp.sendmail(  # type: ignore[union-attr]
                self.config["email"],
                [channel_id],
                msg.as_string(),
            )

            return {
                "channel": "email",
                "channel_id": channel_id,
                "message_id": None,
                "content": text,
                "created_at": datetime.now(),
            }

        return await asyncio.to_thread(_send)

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
        if not self.smtp:
            raise Exception("SMTP client not connected")

        path = Path(file_path)
        if not path.is_file():
            raise FileNotFoundError(f"Attachment file not found: {file_path}")

        def _send() -> dict[str, Any]:
            msg = MIMEMultipart()
            msg["From"] = self.config["email"]
            msg["To"] = channel_id
            msg["Subject"] = subject or "Ответ на ваше сообщение"
            if reply_to:
                msg["In-Reply-To"] = reply_to
                msg["References"] = reply_to

            if caption:
                msg.attach(MIMEText(caption, "plain", "utf-8"))

            maintype, _, subtype = (mime_type or "application/octet-stream").partition("/")
            part = MIMEBase(maintype or "application", subtype or "octet-stream")
            part.set_payload(path.read_bytes())
            encoders.encode_base64(part)
            part.add_header(
                "Content-Disposition",
                f'attachment; filename="{file_name or path.name}"',
            )
            msg.attach(part)

            self.smtp.sendmail(  # type: ignore[union-attr]
                self.config["email"],
                [channel_id],
                msg.as_string(),
            )

            return {
                "channel": "email",
                "channel_id": channel_id,
                "message_id": None,
                "content": caption or "",
                "created_at": datetime.now(),
            }

        return await asyncio.to_thread(_send)

    async def get_dialog(self, channel_id: str, limit: int = 50) -> list[dict[str, Any]]:
        if not self.imap:
            return []

        def _get_dialog() -> list[dict[str, Any]]:
            status, search_data = self.imap.search(None, f'FROM "{channel_id}"')  # type: ignore[union-attr]
            if status != "OK" or not search_data[0]:
                return []

            email_ids = search_data[0].split()
            email_ids = email_ids[-limit:] if len(email_ids) > limit else email_ids

            messages = []
            for email_id in email_ids:
                status, data = self.imap.fetch(email_id, "(RFC822)")  # type: ignore[union-attr]
                if status != "OK":
                    continue

                raw_email = data[0][1]  # type: ignore[index]
                msg = email.message_from_bytes(bytes(raw_email))

                body = self._extract_body(msg)
                date_str = msg.get("Date")
                date = self._parse_date(date_str)

                messages.append(
                    {
                        "message_id": str(email_id, "utf-8"),
                        "direction": "incoming",
                        "content": body,
                        "created_at": date or datetime.now(),
                    }
                )

            return messages

        return await asyncio.to_thread(_get_dialog)

    def _decode_mime_header(self, raw: str) -> str:
        return decode_mime_header(raw)

    def _extract_email(self, text: str) -> str:
        return extract_email(text)

    def _parse_date(self, date_str: str | None) -> datetime | None:
        return parse_email_date(date_str)

    def _extract_body(self, msg: Message) -> str:
        return extract_body(msg)

    async def download_file(self, file_path: str | None) -> Any:
        if not file_path:
            raise ValueError("file_path is empty")

        target = self.data_dir / file_path
        if not target.is_file():
            raise FileNotFoundError(f"Attachment file not found: {file_path}")

        def _read() -> io.BytesIO:
            with target.open("rb") as f:
                return io.BytesIO(f.read())

        return await asyncio.to_thread(_read)
