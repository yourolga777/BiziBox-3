"""R2-13: поведенческий тест кросс-owner невидимости.

Сценарий: строки owner 2 просачиваются в API/service-запросы owner 1
(запросы вне BaseRepository — прямые session.execute в сервисах и роутерах).
Тест внедряет owner-2 данные в БД и проверяет, что ни один публичный
эндпоинт (и сервисный метод) их не возвращает и не модифицирует.
"""

from typing import cast

import pytest

from app.config import DEFAULT_OWNER_ID
from app.database import init_db
from app.models import (
    ContactModel,
    ContactNoteModel,
    MessageModel,
    TaskModel,
)
from app.services.contact_service import ContactService
from tests.conftest import make_client

FOREIGN_OWNER = 2


@pytest.fixture(autouse=True)
async def setup_db():
    await init_db(clear_first=True)


async def _seed_foreign_data(db_session) -> tuple[int, int]:
    """Создаёт строки owner 2 во всех hot-таблицах.

    Возвращает (id_контакта, id_заметки).
    """
    c2 = ContactModel(
        name="Foreign Contact",
        phone="+70001112233",
        email="foreign@example.com",
        owner_id=FOREIGN_OWNER,
    )
    db_session.add(c2)
    await db_session.flush()
    cid2 = cast(int, c2.id)

    db_session.add(MessageModel(
        contact_id=cid2,
        channel="telegram",
        content="foreign secret",
        direction="incoming",
        status="unread",
        owner_id=FOREIGN_OWNER,
    ))
    db_session.add(TaskModel(
        contact_id=cid2,
        title="Foreign Task",
        owner_id=FOREIGN_OWNER,
    ))
    note = ContactNoteModel(
        contact_id=cid2,
        content="foreign note",
        author="x",
        owner_id=FOREIGN_OWNER,
    )
    db_session.add(note)
    await db_session.flush()
    note_id = cast(int, note.id)

    await db_session.commit()
    return cid2, note_id


async def _seed_owner1_contact(db_session, **fields) -> int:
    contact = ContactModel(**fields, owner_id=DEFAULT_OWNER_ID)
    db_session.add(contact)
    await db_session.flush()
    cid = cast(int, contact.id)
    await db_session.commit()
    return cid


@pytest.mark.asyncio
async def test_contacts_list_and_get_hide_foreign(db_session):
    cid2, _ = await _seed_foreign_data(db_session)

    async with make_client() as client:
        listing = await client.get("/api/contacts/")
        assert listing.status_code == 200
        names = [c["name"] for c in listing.json()]
        assert "Foreign Contact" not in names

        fetched = await client.get(f"/api/contacts/{cid2}")
        assert fetched.status_code == 404


@pytest.mark.asyncio
async def test_timeline_and_notes_hide_foreign(db_session):
    cid2, note2 = await _seed_foreign_data(db_session)

    async with make_client() as client:
        timeline = await client.get(f"/api/contacts/{cid2}/timeline")
        assert timeline.status_code == 200
        assert timeline.json() == []

        notes = await client.get(f"/api/contacts/{cid2}/notes")
        assert notes.status_code == 200
        assert notes.json() == []

        created = await client.post(
            f"/api/contacts/{cid2}/notes",
            json={"content": "note on foreign contact"},
        )
        assert created.status_code == 404

        deleted = await client.delete(f"/api/contacts/notes/{note2}")
        assert deleted.status_code == 404


@pytest.mark.asyncio
async def test_export_csv_excludes_foreign(db_session):
    await _seed_foreign_data(db_session)

    async with make_client() as client:
        exported = await client.get("/api/contacts/export")
        assert exported.status_code == 200
        body = exported.text
        assert "Foreign Contact" not in body
        assert "+70001112233" not in body
        assert "foreign@example.com" not in body


@pytest.mark.asyncio
async def test_duplicates_ignore_foreign(db_session):
    await _seed_foreign_data(db_session)
    # Два своих контакта + один чужой с тем же email — группа должна
    # содержать только свои id.
    cid_a = await _seed_owner1_contact(db_session, name="Dup A", email="shared@example.com")
    cid_b = await _seed_owner1_contact(db_session, name="Dup B", email="shared@example.com")

    foreign = ContactModel(
        name="Foreign Dup",
        email="shared@example.com",
        owner_id=FOREIGN_OWNER,
    )
    db_session.add(foreign)
    await db_session.flush()
    foreign_id = cast(int, foreign.id)
    await db_session.commit()

    async with make_client() as client:
        duplicates = await client.get("/api/contacts/duplicates")
        assert duplicates.status_code == 200
        groups = duplicates.json()

    shared_groups = [g for g in groups if "shared@example.com" in g["reason"]]
    assert shared_groups, "группа по shared@example.com не найдена"
    member_ids = {c["id"] for c in shared_groups[0]["contacts"]}
    assert member_ids == {cid_a, cid_b}
    assert foreign_id not in member_ids


@pytest.mark.asyncio
async def test_import_does_not_match_foreign_phone(db_session):
    await _seed_foreign_data(db_session)

    service = ContactService(db_session, owner_id=DEFAULT_OWNER_ID)
    result = await service.import_csv(
        "name,phone,email\nImported,+70001112233,new@example.com\n"
    )
    assert result == {"created": 1, "updated": 0}

    from sqlalchemy import select

    from app.models import ContactModel

    foreign = (await db_session.execute(
        select(ContactModel).where(ContactModel.owner_id == FOREIGN_OWNER)
    )).scalar_one()
    assert foreign.phone == "+70001112233"
    assert foreign.email == "foreign@example.com"
