from datetime import datetime, timedelta, timezone

import pytest

from app.database import init_db
from tests.conftest import make_client


@pytest.fixture(autouse=True)
async def setup_db():
    await init_db(clear_first=True)


def _iso(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


@pytest.mark.asyncio
async def test_contact_updated_at_changes_after_patch():
    async with make_client() as client:
        created = await client.post("/api/contacts/", json={"name": "Иван"})
        cid = created.json()["id"]
        before = created.json()["updated_at"]
        assert before is not None

        patched = await client.patch(f"/api/contacts/{cid}", json={"name": "Иван Петров"})
        after = patched.json()["updated_at"]

        assert patched.status_code == 200
        assert _iso(after) > _iso(before)


@pytest.mark.asyncio
async def test_task_updated_at_changes_after_patch():
    async with make_client() as client:
        created = await client.post("/api/tasks/", json={"title": "Задача"})
        tid = created.json()["id"]
        before = created.json()["updated_at"]

        patched = await client.patch(f"/api/tasks/{tid}", json={"status": "completed"})
        after = patched.json()["updated_at"]

        assert patched.status_code == 200
        assert _iso(after) > _iso(before)


@pytest.mark.asyncio
async def test_updated_at_present_in_get_responses():
    async with make_client() as client:
        contact = await client.post("/api/contacts/", json={"name": "Контакт"})
        task = await client.post("/api/tasks/", json={"title": "Дело"})

        for path in [
            f"/api/contacts/{contact.json()['id']}",
            f"/api/tasks/{task.json()['id']}",
        ]:
            response = await client.get(path)
            assert response.status_code == 200
            assert response.json()["updated_at"] is not None, f"updated_at отсутствует в GET {path}"


@pytest.mark.asyncio
async def test_updated_at_in_body_is_ignored():
    fake = datetime.now(tz=timezone.utc) - timedelta(days=30)

    async with make_client() as client:
        created = await client.post("/api/contacts/", json={"name": "Без фейка"})
        cid = created.json()["id"]

        patched = await client.patch(f"/api/contacts/{cid}", json={
            "name": "С фейком",
            "updated_at": fake.isoformat(),
        })

        assert patched.status_code == 200
        got = datetime.fromisoformat(patched.json()["updated_at"].replace("Z", "+00:00"))
        assert got.replace(tzinfo=None) > fake.replace(tzinfo=None), "отправленный updated_at не должен применяться"
