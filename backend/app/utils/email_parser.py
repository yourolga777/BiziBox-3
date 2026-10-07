import base64
import quopri
import re
from datetime import datetime, timezone
from email.header import decode_header
from email.message import Message
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from uuid import uuid4

_MIME_PATTERN = re.compile(r"=\?([^?]+)\?([BbQq])\?([^?]*)\?=")

_BLOCK_TAGS = frozenset([
    "p", "div", "br", "tr", "li", "h1", "h2", "h3", "h4", "h5", "h6",
    "blockquote", "section", "article", "header", "footer", "pre",
])


class _HTMLTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._parts: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in ("style", "script", "head", "title"):
            self._skip_depth += 1
        elif tag in _BLOCK_TAGS:
            self._parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in ("style", "script", "head", "title"):
            if self._skip_depth > 0:
                self._skip_depth -= 1
        elif tag == "br":
            self._parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self._skip_depth == 0:
            self._parts.append(data.replace("\xa0", " "))

    def get_text(self) -> str:
        raw = "".join(self._parts)
        lines = [line.strip() for line in raw.splitlines()]
        text = "\n".join(line for line in lines if line)
        return re.sub(r"\n{3,}", "\n\n", text)


def strip_html(html: str) -> str:
    extractor = _HTMLTextExtractor()
    extractor.feed(html)
    return extractor.get_text()


def decode_mime_header(raw: str) -> str:
    raw = raw.strip()
    if not raw:
        return ""

    try:
        parts = decode_header(raw)
        result = []
        for data, charset in parts:
            if isinstance(data, bytes):
                result.append(data.decode(charset or "utf-8", errors="replace"))
            else:
                result.append(data)
        decoded = " ".join(result)
        if "=?" not in decoded:
            return decoded
    except Exception:
        pass

    fixed = raw.replace("?==?", "?= =?")
    try:
        parts = decode_header(fixed)
        result = []
        for data, charset in parts:
            if isinstance(data, bytes):
                result.append(data.decode(charset or "utf-8", errors="replace"))
            else:
                result.append(data)
        decoded = " ".join(result)
        if "=?" not in decoded:
            return decoded
    except Exception:
        pass

    pos = 0
    result = []
    for m in _MIME_PATTERN.finditer(raw):
        if m.start() > pos:
            result.append(raw[pos:m.start()])
        charset, encoding, data = m.group(1), m.group(2).upper(), m.group(3)
        try:
            if encoding == "B":
                payload = base64.b64decode(data)
            else:
                payload = quopri.decodestring(data)
            result.append(payload.decode(charset, errors="replace"))
        except Exception:
            result.append(m.group(0))
        pos = m.end()
    if pos < len(raw):
        result.append(raw[pos:])
    text = "".join(result)
    return text if "=?" not in text else raw


def extract_email(text: str) -> str:
    match = re.search(r"<(.+?)>", text)
    return match.group(1) if match else text.strip()


def extract_display_name(text: str) -> str:
    """Возвращает человекочитаемое имя из поля From.

    Примеры:
        'Ольга Исаева <olga@example.com>' -> 'Ольга Исаева'
        'olga@example.com' -> ''
    """
    decoded = decode_mime_header(text).strip()
    if not decoded:
        return ""
    # "Name <email>" — берём часть до угловых скобок
    match = re.match(r"^(.*?)<.+?>\s*$", decoded)
    if match:
        name = match.group(1).strip().strip('"').strip("'")
        return name
    # Если строка выглядит как чистый email — имени нет
    if "@" in decoded and " " not in decoded:
        return ""
    return decoded


def parse_email_date(date_str: str | None) -> datetime | None:
    if not date_str:
        return None
    try:
        dt = parsedate_to_datetime(date_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    except Exception:
        return None


def has_cyrillic_or_ascii(text: str, raw: bytes) -> bool:
    if any("\u0400" <= ch <= "\u04FF" or "\u0500" <= ch <= "\u052F" for ch in text):
        return True
    if not any(b > 0x7F for b in raw):
        return True
    return False


def decode_payload(payload: bytes, preferred: str) -> str:
    try:
        text = payload.decode(preferred, errors="strict")
        if has_cyrillic_or_ascii(text, payload):
            return text
    except (UnicodeDecodeError, LookupError):
        pass

    for fallback in ["koi8-r", "windows-1251", "utf-8"]:
        if fallback == preferred:
            continue
        try:
            text = payload.decode(fallback, errors="strict")
            if has_cyrillic_or_ascii(text, payload):
                return text
        except (UnicodeDecodeError, LookupError):
            continue

    return payload.decode("utf-8", errors="replace")


def extract_body(msg: Message) -> str:
    body: list[str] = []
    html_parts: list[str] = []

    if msg.is_multipart():
        for part in msg.walk():
            ct = part.get_content_type()
            try:
                payload = part.get_payload(decode=True)
                if not payload:
                    continue
                charset = part.get_content_charset() or "utf-8"
                text = decode_payload(payload, charset)  # type: ignore[arg-type]
                if ct == "text/plain":
                    body.append(text)
                elif ct == "text/html":
                    html_parts.append(text)
            except Exception:
                pass
    else:
        ct = msg.get_content_type()
        try:
            payload = msg.get_payload(decode=True)
            if payload:
                charset = msg.get_content_charset() or "utf-8"
                text = decode_payload(payload, charset)  # type: ignore[arg-type]
                if ct == "text/plain":
                    body.append(text)
                elif ct == "text/html":
                    html_parts.append(text)
        except Exception:
            pass

    if not body and html_parts:
        body = [strip_html(h) for h in html_parts]

    return "\n".join(body).strip()


def extract_attachments(msg: Message, save_dir: Path) -> list[dict[str, Any]]:
    """Извлекает MIME-вложения (части с filename) и сохраняет их на диск.

    Возвращает список dict с полями AttachmentInput: file_name, file_size,
    mime_type, file_path (относительный путь от save_dir).
    """
    attachments: list[dict[str, Any]] = []

    for part in msg.walk():
        if part.get_content_maintype() == "multipart":
            continue
        if part.get_content_maintype() == "text":
            continue

        try:
            filename = part.get_filename()
            if not filename:
                continue
            payload = part.get_payload(decode=True)
            if not payload or not isinstance(payload, bytes):
                continue
        except Exception:
            continue

        original_name = decode_mime_header(filename) or f"attachment_{len(attachments)}"
        safe_name = Path(original_name).name or f"attachment_{len(attachments)}"
        suffix = Path(safe_name).suffix
        stored = f"attachments/{uuid4().hex}{suffix}"

        dest = save_dir / stored
        try:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(payload)
        except OSError:
            continue

        attachments.append(
            {
                "file_name": safe_name,
                "file_size": len(payload),
                "mime_type": part.get_content_type(),
                "file_path": stored,
            }
        )

    return attachments
