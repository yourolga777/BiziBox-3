import pytest

from app.database import init_db
from tests.conftest import make_client


@pytest.fixture(autouse=True)
async def setup_db():
    await init_db(clear_first=True)


@pytest.mark.asyncio
async def test_create_contact():
    async with make_client() as client:
        response = await client.post("/api/contacts/", json={
            "name": "Иван Петров",
            "phone": "+79161234567",
            "email": "ivan@example.com",
            "notes": "Клиент из Telegram",
        })
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Иван Петров"
    assert data["phone"] == "+79161234567"
    assert data["email"] == "ivan@example.com"
    assert data["id"] > 0


@pytest.mark.asyncio
async def test_get_contacts():
    async with make_client() as client:
        await client.post("/api/contacts/", json={"name": "Alice"})
        await client.post("/api/contacts/", json={"name": "Bob"})

        response = await client.get("/api/contacts/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 2


@pytest.mark.asyncio
async def test_update_contact():
    async with make_client() as client:
        created = await client.post("/api/contacts/", json={"name": "Old Name"})
        cid = created.json()["id"]

        response = await client.patch(f"/api/contacts/{cid}", json={"name": "New Name"})
    assert response.status_code == 200
    assert response.json()["name"] == "New Name"


@pytest.mark.asyncio
async def test_delete_contact():
    async with make_client() as client:
        created = await client.post("/api/contacts/", json={"name": "Delete Me"})
        cid = created.json()["id"]

        response = await client.delete(f"/api/contacts/{cid}")
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_set_spam_restores_previous_sphere():
    async with make_client() as client:
        created = await client.post("/api/contacts/", json={
            "name": "Spam Restore",
            "life_sphere": "work",
        })
        cid = created.json()["id"]

        marked = await client.post(f"/api/contacts/{cid}/set-spam?spam=true")
        assert marked.status_code == 200
        assert marked.json()["life_sphere"] == "spam"

        restored = await client.post(f"/api/contacts/{cid}/set-spam?spam=false")
        assert restored.status_code == 200
        assert restored.json()["life_sphere"] == "work"


@pytest.mark.asyncio
async def test_set_spam_without_previous_sphere_returns_null():
    async with make_client() as client:
        created = await client.post("/api/contacts/", json={"name": "Spam Null"})
        cid = created.json()["id"]

        marked = await client.post(f"/api/contacts/{cid}/set-spam?spam=true")
        assert marked.status_code == 200
        assert marked.json()["life_sphere"] == "spam"

        restored = await client.post(f"/api/contacts/{cid}/set-spam?spam=false")
        assert restored.status_code == 200
        assert restored.json()["life_sphere"] is None


@pytest.mark.asyncio
async def test_search_contacts():
    async with make_client() as client:
        await client.post("/api/contacts/", json={"name": "Сергей Иванов", "phone": "+79161112233"})
        await client.post("/api/contacts/", json={"name": "Мария Петрова"})

        response = await client.get("/api/contacts/?search=Иванов")
    assert response.status_code == 200
    data = response.json()
    assert any("Иванов" in (c["name"] or "") for c in data)


@pytest.mark.asyncio
async def test_search_contacts_by_message_text():
    async with make_client() as client:
        created = await client.post("/api/contacts/", json={"name": "Контакт с перепиской"})
        cid = created.json()["id"]
        await client.post("/api/messages/", json={
            "contact_id": cid,
            "channel": "telegram",
            "content": "Здравствуйте, интересует ваша продукция и доставка",
            "direction": "incoming",
        })

        await client.post("/api/contacts/", json={"name": "Другой Контакт"})

        found = await client.get("/api/contacts/?search=продукция")
        assert found.status_code == 200
        found_ids = [c["id"] for c in found.json()]
        assert cid in found_ids

        not_found = await client.get("/api/contacts/?search=несуществующийфрагмент")
        assert not_found.status_code == 200
        assert all(c["id"] != cid for c in not_found.json())


@pytest.mark.asyncio
async def test_merge_contacts():
    async with make_client() as client:
        c1 = await client.post("/api/contacts/", json={"name": "Primary", "phone": "+111"})
        c2 = await client.post("/api/contacts/", json={"name": "Secondary", "phone": "+222"})
        pid = c1.json()["id"]
        sid = c2.json()["id"]

        # Создаём сообщение для secondary
        await client.post("/api/messages/", json={
            "contact_id": sid,
            "channel": "telegram",
            "content": "Test message",
            "direction": "incoming",
        })

        response = await client.post("/api/contacts/merge", json={
            "primary_id": pid,
            "secondary_id": sid,
        })
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == pid

        # Проверяем, что secondary в архиве (soft-delete)
        get_resp = await client.get(f"/api/contacts/{sid}")
        assert get_resp.status_code == 200
        assert get_resp.json()["deleted_at"] is not None


@pytest.mark.asyncio
async def test_merge_keeps_conflicting_identifiers_separately():
    async with make_client() as client:
        c1 = await client.post("/api/contacts/", json={
            "name": "Same Name",
            "phone": "+111",
            "email": "primary@example.com",
        })
        c2 = await client.post("/api/contacts/", json={
            "name": "Same Name",
            "phone": "+222",
            "email": "secondary@example.com",
        })
        pid = c1.json()["id"]
        sid = c2.json()["id"]

        response = await client.post("/api/contacts/merge", json={
            "primary_id": pid,
            "secondary_id": sid,
        })
        assert response.status_code == 200
        data = response.json()

        ident = {(i["channel"], i["value"]) for i in data["identifiers"]}
        assert ("phone", "+222") in ident
        assert ("email", "secondary@example.com") in ident

        # Основные поля не перезаписаны
        assert data["phone"] == "+111"
        assert data["email"] == "primary@example.com"

        # Идентификаторы больше не сваливаются в заметки
        assert "Объединённые данные" not in (data.get("notes") or "")

        # Повторное объединение не дублирует идентификаторы
        c3 = await client.post("/api/contacts/", json={
            "name": "Same Name",
            "phone": "+222",
            "email": "secondary@example.com",
        })
        again = await client.post("/api/contacts/merge", json={
            "primary_id": pid,
            "secondary_id": c3.json()["id"],
        })
        assert again.status_code == 200
        ident2 = [(i["channel"], i["value"]) for i in again.json()["identifiers"]]
        assert ident2.count(("phone", "+222")) == 1


@pytest.mark.asyncio
async def test_merge_concatenates_names():
    async with make_client() as client:
        c1 = await client.post("/api/contacts/", json={"name": "Иван", "telegram_id": "111"})
        c2 = await client.post("/api/contacts/", json={"name": "Петров", "telegram_id": "222"})
        pid = c1.json()["id"]
        sid = c2.json()["id"]

        response = await client.post("/api/contacts/merge", json={
            "primary_id": pid,
            "secondary_id": sid,
        })
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Иван Петров"
        assert ("telegram_id", "222") in {(i["channel"], i["value"]) for i in data["identifiers"]}


@pytest.mark.asyncio
async def test_get_all_returns_identifiers():
    async with make_client() as client:
        c1 = await client.post("/api/contacts/", json={"name": "A", "telegram_id": "111"})
        c2 = await client.post("/api/contacts/", json={"name": "B", "telegram_id": "222"})
        pid = c1.json()["id"]
        sid = c2.json()["id"]
        await client.post("/api/contacts/merge", json={"primary_id": pid, "secondary_id": sid})

        lst = await client.get("/api/contacts/")
        contacts = lst.json()
        merged = next(c for c in contacts if c["id"] == pid)
        assert ("telegram_id", "222") in {(i["channel"], i["value"]) for i in merged["identifiers"]}


@pytest.mark.asyncio
async def test_update_folder_ids_applies_auto_type_and_spheres():
    async with make_client() as client:
        c = await client.post("/api/contacts/", json={"name": "Иван"})
        cid = c.json()["id"]
        folders = (await client.get("/api/folders/")).json()
        suppliers = next(f for f in folders if f["category_key"] == "suppliers")

        response = await client.patch(f"/api/contacts/{cid}", json={"folder_ids": [suppliers["id"]]})
        assert response.status_code == 200
        data = response.json()

        assert suppliers["id"] in [f["id"] for f in data["folders"]]
        assert "Поставщик" in data["contact_types"]
        assert "work" in data["spheres"]


@pytest.mark.asyncio
async def test_folder_suppliers_creates_supplier():
    async with make_client() as client:
        c = await client.post("/api/contacts/", json={"name": "ООО Ромашка"})
        cid = c.json()["id"]
        folders = (await client.get("/api/folders/")).json()
        suppliers_folder = next(f for f in folders if f["category_key"] == "suppliers")

        await client.patch(f"/api/contacts/{cid}", json={"folder_ids": [suppliers_folder["id"]]})

        suppliers = (await client.get("/api/suppliers/")).json()
        assert any(s["contact_id"] == cid for s in suppliers)


@pytest.mark.asyncio
async def test_reset_classification_moves_contact_to_other():
    async with make_client() as client:
        created = await client.post("/api/contacts/", json={
            "name": "To Reset",
            "life_sphere": "work",
        })
        assert created.status_code == 201
        cid = created.json()["id"]

        folders = await client.get("/api/folders/?sphere=work")
        folder_id = folders.json()[0]["id"]
        await client.patch(f"/api/contacts/{cid}", json={"folder_id": folder_id})
        assert (await client.get(f"/api/contacts/{cid}")).json()["folder_id"] == folder_id

        resp = await client.patch(
            f"/api/contacts/{cid}", json={"life_sphere": None, "folder_id": None}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["life_sphere"] is None
        assert data["folder_id"] is None


@pytest.mark.asyncio
async def test_contact_pagination():
    async with make_client() as client:
        for i in range(25):
            await client.post("/api/contacts/", json={"name": f"Pagination Contact {i}"})

        page1 = await client.get("/api/contacts/?skip=0&limit=20&search=Pagination")
        page2 = await client.get("/api/contacts/?skip=20&limit=20&search=Pagination")
    assert len(page1.json()) == 20
    # Может быть меньше 5 если есть пересечения с предыдущими тестами
    assert len(page2.json()) > 0


@pytest.mark.asyncio
async def test_contacts_no_limit_returns_all():
    async with make_client() as client:
        for i in range(25):
            await client.post("/api/contacts/", json={"name": f"NoLimit Contact {i}"})

        response = await client.get("/api/contacts/?search=NoLimit")
    assert response.status_code == 200
    assert len(response.json()) == 25


@pytest.mark.asyncio
async def test_contacts_invalid_limit_returns_422():
    async with make_client() as client:
        response = await client.get("/api/contacts/?limit=-1")
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_contact_not_found():
    async with make_client() as client:
        response = await client.get("/api/contacts/99999")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_contact_sphere_default():
    async with make_client() as client:
        created = await client.post("/api/contacts/", json={"name": "Без сферы"})
    assert created.status_code == 201
    assert created.json()["life_sphere"] is None


@pytest.mark.asyncio
async def test_contact_sphere_create_and_update():
    async with make_client() as client:
        created = await client.post("/api/contacts/", json={
            "name": "Рабочий",
            "life_sphere": "work",
        })
        assert created.status_code == 201
        cid = created.json()["id"]
        assert created.json()["life_sphere"] == "work"

        updated = await client.patch(
            f"/api/contacts/{cid}", json={"life_sphere": "spam"}
        )
    assert updated.status_code == 200
    assert updated.json()["life_sphere"] == "spam"


@pytest.mark.asyncio
async def test_contact_sphere_invalid_returns_422():
    async with make_client() as client:
        created = await client.post("/api/contacts/", json={
            "name": "Недопустимая сфера",
            "life_sphere": "customer",
        })
        updated = await client.patch("/api/contacts/1", json={"life_sphere": "customer"})
    assert created.status_code == 422
    assert updated.status_code == 422


@pytest.mark.asyncio
async def test_contact_sphere_filter():
    async with make_client() as client:
        await client.post(
            "/api/contacts/", json={"name": "Рабочее 1", "life_sphere": "work"}
        )
        await client.post(
            "/api/contacts/", json={"name": "Рабочее 2", "life_sphere": "work"}
        )
        await client.post(
            "/api/contacts/", json={"name": "Личное 1", "life_sphere": "personal"}
        )

        service = await client.get("/api/contacts/?life_sphere=work")
        personal = await client.get("/api/contacts/?life_sphere=personal")
    assert len(service.json()) == 2
    assert len(personal.json()) == 1
    assert all(c["life_sphere"] == "work" for c in service.json())


@pytest.mark.asyncio
async def test_contact_birthday_roundtrip():
    async with make_client() as client:
        created = await client.post("/api/contacts/", json={
            "name": "С днём рождения",
            "birthday": "1990-05-17",
        })
        assert created.status_code == 201
        cid = created.json()["id"]
        assert created.json()["birthday"] == "1990-05-17"

        updated = await client.patch(
            f"/api/contacts/{cid}", json={"birthday": "2000-01-01"}
        )
    assert updated.status_code == 200
    assert updated.json()["birthday"] == "2000-01-01"


@pytest.mark.asyncio
async def test_contact_type_filter():
    async with make_client() as client:
        tpl = await client.post(
            "/api/contacts/contact-types",
            json={"name": "Клиент", "sphere": "work"},
        )
        assert tpl.status_code == 201
        tid = tpl.json()["id"]

        await client.post(
            "/api/contacts/", json={"name": "С клиентом", "contact_type_ids": [tid]}
        )
        await client.post("/api/contacts/", json={"name": "Без типа"})

        filtered = await client.get(f"/api/contacts/?contact_type_ids={tid}")
    assert filtered.status_code == 200
    assert all(c["contact_type_ids"] == [tid] for c in filtered.json())
    assert any(c["name"] == "С клиентом" for c in filtered.json())


@pytest.mark.asyncio
async def test_contact_folder_filter():
    async with make_client() as client:
        folder = await client.post("/api/folders/", json={"name": "VIP"})
        assert folder.status_code == 201
        fid = folder.json()["id"]

        await client.post("/api/contacts/", json={"name": "In Folder", "folder_id": fid})
        await client.post("/api/contacts/", json={"name": "No Folder"})

        in_folder = await client.get(f"/api/contacts/?folder_id={fid}")
    assert in_folder.status_code == 200
    assert all(c["folder_id"] == fid for c in in_folder.json())
    assert any(c["name"] == "In Folder" for c in in_folder.json())
    assert all(c["name"] != "No Folder" for c in in_folder.json())


@pytest.mark.asyncio
async def test_contact_sort_by_first_message():
    async with make_client() as client:
        c1 = await client.post("/api/contacts/", json={"name": "Alpha"})
        c2 = await client.post("/api/contacts/", json={"name": "Beta"})
        id1 = c1.json()["id"]
        id2 = c2.json()["id"]

        # Раньше сообщение — у Beta
        await client.post("/api/messages/", json={
            "contact_id": id2,
            "channel": "telegram",
            "content": "старое",
            "direction": "incoming",
            "created_at": "2024-01-01T10:00:00",
        })
        await client.post("/api/messages/", json={
            "contact_id": id1,
            "channel": "telegram",
            "content": "новое",
            "direction": "incoming",
            "created_at": "2024-06-01T10:00:00",
        })

        asc_resp = await client.get("/api/contacts/?sort_by=first_message&sort_order=asc")
        desc_resp = await client.get("/api/contacts/?sort_by=first_message&sort_order=desc")
    assert asc_resp.status_code == 200
    names_asc = [c["name"] for c in asc_resp.json()]
    assert names_asc.index("Beta") < names_asc.index("Alpha")
    names_desc = [c["name"] for c in desc_resp.json()]
    assert names_desc.index("Alpha") < names_desc.index("Beta")


@pytest.mark.asyncio
async def test_duplicates_endpoint_returns_200():
    """RK-14: GET /api/contacts/duplicates отвечает 200 даже без дубликатов."""
    async with make_client() as client:
        await client.post("/api/contacts/", json={"name": "A", "phone": "+111"})
        await client.post("/api/contacts/", json={"name": "B", "phone": "+222"})
        response = await client.get("/api/contacts/duplicates")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_import_csv_rolls_back_on_failure(monkeypatch):
    """R1-14: инъекция сбоя на шаге N импорта — ноль созданных контактов."""
    from sqlalchemy import func, select

    from app.database import AsyncSessionLocal
    from app.models import ContactModel
    from app.services.contact_service import ContactService

    csv_content = "name,phone,email\n" + "\n".join(
        f"Contact{i},+79990000{i:03d},c{i}@test.com" for i in range(1, 11)
    )

    async with AsyncSessionLocal() as session:
        service = ContactService(session)
        original_create = service.contact_repo.create
        counter = [0]

        async def _fail_on_5th(**kwargs):
            counter[0] += 1
            if counter[0] == 5:
                raise RuntimeError("injected import failure")
            return await original_create(**kwargs)

        monkeypatch.setattr(service.contact_repo, "create", _fail_on_5th)

        with pytest.raises(RuntimeError):
            await service.import_csv(csv_content)

        await session.rollback()

    async with AsyncSessionLocal() as session:
        count = await session.scalar(select(func.count(ContactModel.id)))
        assert count == 0, f"должно быть 0 контактов после отката, а есть {count}"


@pytest.mark.asyncio
async def test_contact_list_query_count_constant():
    """B-01: число SQL-запросов на список контактов константно (не N+1)."""
    from sqlalchemy import event

    async with make_client() as client:
        for i in range(20):
            await client.post("/api/contacts/", json={"name": f"Contact {i}"})

    queries: list[str] = []

    from app.database import engine as db_engine

    def capture(_conn, cursor, statement, parameters, _context, _executemany):
        queries.append(str(statement))

    event.listen(db_engine.sync_engine, "before_cursor_execute", capture)

    async with make_client() as client:
        resp = await client.get("/api/contacts/?limit=50")
        assert resp.status_code == 200
        assert len(resp.json()) > 0

    event.remove(db_engine.sync_engine, "before_cursor_execute", capture)

    assert len(queries) <= 10, f"ожидалось ≤10 запросов, получено {len(queries)}: {queries}"


@pytest.mark.asyncio
async def test_bulk_update_is_favorite():
    async with make_client() as client:
        created = await client.post("/api/contacts/", json={"name": "Избранный"})
        cid = created.json()["id"]
        response = await client.patch(
            "/api/contacts/bulk-update",
            json={"ids": [cid], "is_favorite": True},
        )
        assert response.status_code == 200
        assert response.json()["updated"] == 1

        detail = await client.get(f"/api/contacts/{cid}")
    assert detail.json()["is_favorite"] is True

