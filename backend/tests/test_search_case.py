import uuid

import pytest

from app.database import init_db
from tests.conftest import make_client


@pytest.fixture(autouse=True)
async def setup_db():
    await init_db(clear_first=True)


async def _create_contact(client, **kwargs) -> int:
    resp = await client.post("/api/contacts/", json=kwargs)
    assert resp.status_code in (200, 201), resp.text
    return resp.json()["id"]


@pytest.mark.asyncio
async def test_contact_search_cyrillic_query_matches_latin_name():
    async with make_client() as client:
        await _create_contact(client, name="Andrey Yumashev", phone="+7 900 123-45-67")
        resp = await client.get("/api/contacts/?search=" + "андрей юмашев")
    assert len(resp.json()) == 1
    assert resp.json()[0]["name"] == "Andrey Yumashev"


@pytest.mark.asyncio
async def test_contact_search_latin_query_matches_cyrillic_name():
    async with make_client() as client:
        await _create_contact(client, name="Андрей Юмашев")
        resp = await client.get("/api/contacts/?search=andrey yumashev")
    assert len(resp.json()) == 1
    assert resp.json()[0]["name"] == "Андрей Юмашев"


@pytest.mark.asyncio
async def test_contact_search_by_telegram_id():
    tg_id = str(100000000 + uuid.uuid4().int % 100000000)
    async with make_client() as client:
        await _create_contact(client, name="Telegram User", telegram_id=tg_id)
        resp = await client.get(f"/api/contacts/?search={tg_id}")
    assert len(resp.json()) == 1
    assert resp.json()[0]["telegram_id"] == tg_id


@pytest.mark.asyncio
async def test_contact_search_by_phone_digits_only():
    async with make_client() as client:
        await _create_contact(client, name="Иван", phone="+7 (900) 123-45-67")
        resp = await client.get("/api/contacts/?search=79001234567")
    assert len(resp.json()) == 1
    assert resp.json()[0]["phone"] == "+7 (900) 123-45-67"


@pytest.mark.asyncio
async def test_contact_search_by_phone_with_eight_prefix():
    async with make_client() as client:
        await _create_contact(client, name="Иван", phone="+7 900 123-45-67")
        resp = await client.get("/api/contacts/?search=8 900 123 45 67")
    assert len(resp.json()) == 1
    assert resp.json()[0]["phone"] == "+7 900 123-45-67"


@pytest.mark.asyncio
async def test_contact_search_by_phone_local_ten_digits():
    async with make_client() as client:
        await _create_contact(client, name="Иван", phone="+7 (900) 123-45-67")
        resp = await client.get("/api/contacts/?search=9001234567")
    assert len(resp.json()) == 1
    assert resp.json()[0]["phone"] == "+7 (900) 123-45-67"


@pytest.mark.asyncio
async def test_contact_search_by_phone_partial_digits():
    async with make_client() as client:
        await _create_contact(client, name="Иван", phone="+7 (900) 123-45-67")
        resp = await client.get("/api/contacts/?search=900123456")
    assert len(resp.json()) == 1
    assert resp.json()[0]["phone"] == "+7 (900) 123-45-67"


@pytest.mark.asyncio
async def test_contact_search_by_phone_with_formatting():
    async with make_client() as client:
        await _create_contact(client, name="Иван", phone="+7 (900) 123-45-67")
        resp = await client.get("/api/contacts/?search=+7 (900) 123-45-67")
    assert len(resp.json()) == 1
    assert resp.json()[0]["phone"] == "+7 (900) 123-45-67"


@pytest.mark.asyncio
async def test_contact_search_by_phone_stored_with_eight_prefix():
    async with make_client() as client:
        await _create_contact(client, name="Иван", phone="8 900 123 45 67")
        resp = await client.get("/api/contacts/?search=+7 (900) 123-45-67")
    assert len(resp.json()) == 1
    assert resp.json()[0]["phone"] == "8 900 123 45 67"
