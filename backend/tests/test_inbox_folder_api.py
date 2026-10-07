import pytest

from app.database import init_db
from tests.conftest import make_client


@pytest.fixture(autouse=True)
async def setup_db():
    await init_db(clear_first=True)


async def _make_contact(client, name: str, **extra) -> int:
    resp = await client.post("/api/contacts/", json={"name": name, **extra})
    assert resp.status_code == 201
    return int(resp.json()["id"])


async def _make_message(client, contact_id: int, content: str, **extra) -> None:
    resp = await client.post("/api/messages/", json={
        "contact_id": contact_id,
        "channel": "telegram",
        "content": content,
        "direction": "incoming",
        **extra,
    })
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_get_messages_filter_by_folder():
    async with make_client() as client:
        folder = await client.post("/api/folders/", json={"name": "Проекты"})
        fid = folder.json()["id"]
        in_cid = await _make_contact(client, "In", folder_id=fid)
        out_cid = await _make_contact(client, "Out")

        await _make_message(client, in_cid, "в папке")
        await _make_message(client, out_cid, "не в папке")

        resp = await client.get(f"/api/messages/?folder_id={fid}")
    assert resp.status_code == 200
    contents = [m["content"] for m in resp.json()]
    assert "в папке" in contents
    assert "не в папке" not in contents


@pytest.mark.asyncio
async def test_get_messages_filter_by_sphere():
    async with make_client() as client:
        sid = await _make_contact(client, "Service", life_sphere="work")
        pid = await _make_contact(client, "Personal", life_sphere="personal")

        await _make_message(client, sid, "service msg")
        await _make_message(client, pid, "personal msg")

        resp = await client.get("/api/messages/?life_sphere=work")
    assert resp.status_code == 200
    contents = [m["content"] for m in resp.json()]
    assert "service msg" in contents
    assert "personal msg" not in contents


@pytest.mark.asyncio
async def test_get_messages_filter_by_channel():
    async with make_client() as client:
        cid = await _make_contact(client, "Ch")
        await _make_message(client, cid, "tg")
        await _make_message(client, cid, "em", channel="email")

        resp = await client.get("/api/messages/?channel=telegram")
    assert resp.status_code == 200
    contents = [m["content"] for m in resp.json()]
    assert "tg" in contents
    assert "em" not in contents


@pytest.mark.asyncio
async def test_get_messages_scope_new_returns_only_unread():
    async with make_client() as client:
        cid = await _make_contact(client, "U")
        await _make_message(client, cid, "unread msg", status="unread")
        await _make_message(client, cid, "read msg", status="read")

        resp = await client.get("/api/messages/?scope=new")
    assert resp.status_code == 200
    contents = [m["content"] for m in resp.json()]
    assert "unread msg" in contents
    assert "read msg" not in contents


@pytest.mark.asyncio
async def test_get_messages_scope_all_returns_all():
    async with make_client() as client:
        cid = await _make_contact(client, "A")
        await _make_message(client, cid, "unread msg", status="unread")
        await _make_message(client, cid, "read msg", status="read")

        resp = await client.get("/api/messages/?scope=all")
    assert resp.status_code == 200
    contents = [m["content"] for m in resp.json()]
    assert "unread msg" in contents
    assert "read msg" in contents


@pytest.mark.asyncio
async def test_get_messages_nonexistent_folder_404():
    async with make_client() as client:
        resp = await client.get("/api/messages/?folder_id=999999")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_messages_pagination():
    async with make_client() as client:
        cid = await _make_contact(client, "Pag")
        for i in range(5):
            await _make_message(client, cid, f"msg {i}")

        page1 = await client.get("/api/messages/?skip=0&limit=2")
        page2 = await client.get("/api/messages/?skip=2&limit=2")
    assert page1.status_code == 200
    assert page2.status_code == 200
    assert len(page1.json()) == 2
    assert len(page2.json()) == 2


@pytest.mark.asyncio
async def test_get_messages_invalid_scope_422():
    async with make_client() as client:
        resp = await client.get("/api/messages/?scope=bogus")
    assert resp.status_code == 422
