import html
import re
from typing import Optional
from urllib.parse import urlparse

_URL_RE = re.compile(r"(?:https?://|www\.)[^\s<>\"']+", re.IGNORECASE)


def _display_domain(url: str) -> str:
    try:
        parsed = urlparse(url if "://" in url else "https://" + url)
        host = parsed.hostname or url
        return host.removeprefix("www.")
    except Exception:
        return url


def autolink(content: Optional[str]) -> str:
    """Экранирует текст и превращает http/https/www URL в кликабельные ссылки.

    Показывается домен (а не полный URL), ссылка помечается классом msg-link
    (синяя → фиолетовая после клика, стили во фронте).
    """
    if not content:
        return ""
    escaped = html.escape(content, quote=True)
    return _URL_RE.sub(_wrap_url, escaped)


def _wrap_url(match: "re.Match[str]") -> str:
    url = match.group(0)
    href = url if url.lower().startswith(("http://", "https://")) else "https://" + url
    label = html.escape(_display_domain(url))
    return (
        f'<a href="{href}" class="msg-link" target="_blank" rel="noopener noreferrer">'
        f"{label}</a>"
    )
