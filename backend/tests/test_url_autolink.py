import pytest

from app.database import init_db
from app.utils.autolink import autolink
from tests.conftest import make_client


@pytest.fixture(autouse=True)
async def setup_db():
    await init_db(clear_first=True)


def test_autolink_http_url():
    html = autolink("Visit https://example.com now")
    assert '<a href="https://example.com"' in html
    assert 'target="_blank"' in html
    assert 'rel="noopener noreferrer"' in html


def test_autolink_https_url():
    html = autolink("http://a.ru/path?x=1")
    assert '<a href="http://a.ru/path?x=1"' in html


def test_autolink_escapes_xss():
    html = autolink('<script>alert("x")</script> https://ok.com')
    assert "<script>" not in html
    assert "&lt;script&gt;" in html
    assert '<a href="https://ok.com"' in html


def test_autolink_no_url_no_anchor():
    html = autolink("просто текст без ссылок")
    assert "<a " not in html
    assert html == "просто текст без ссылок"


def test_autolink_empty_and_none():
    assert autolink("") == ""
    assert autolink(None) == ""


def test_autolink_shows_domain_and_class():
    html = autolink("go https://example.com/very/long/path?q=1")
    assert '<a href="https://example.com/very/long/path?q=1"' in html
    assert 'class="msg-link"' in html
    assert ">example.com</a>" in html
    assert "very/long/path</a>" not in html


def test_autolink_www():
    html = autolink("www.example.com")
    assert 'href="https://www.example.com"' in html
    assert ">example.com</a>" in html


@pytest.mark.asyncio
async def test_message_response_contains_content_html():
    async with make_client() as client:
        contact = await client.post("/api/contacts/", json={"name": "Linker"})
        cid = contact.json()["id"]
        created = await client.post(
            "/api/messages/",
            json={
                "contact_id": cid,
                "channel": "telegram",
                "content": "Ссылка https://example.org/page",
                "direction": "incoming",
            },
        )
        mid = created.json()["id"]
        detail = await client.get(f"/api/messages/{mid}")
    body = detail.json()
    assert body["content_html"] is not None
    assert '<a href="https://example.org/page"' in body["content_html"]


@pytest.mark.asyncio
async def test_message_response_escapes_script_in_content_html():
    async with make_client() as client:
        contact = await client.post("/api/contacts/", json={"name": "XSS"})
        cid = contact.json()["id"]
        created = await client.post(
            "/api/messages/",
            json={
                "contact_id": cid,
                "channel": "telegram",
                "content": "<img src=x onerror=alert(1)> https://safe.com",
                "direction": "incoming",
            },
        )
        mid = created.json()["id"]
        detail = await client.get(f"/api/messages/{mid}")
    body = detail.json()
    assert "<img" not in body["content_html"]
    assert "&lt;img" in body["content_html"]
    assert '<a href="https://safe.com"' in body["content_html"]
