import pytest

from app.config import DEFAULT_OWNER_ID
from app.database import init_db
from app.repositories.contact import ContactRepository
from app.repositories.message import MessageRepository
from app.repositories.task import TaskRepository
from tests.conftest import make_client


@pytest.fixture(autouse=True)
async def setup_db():
    await init_db(clear_first=True)


@pytest.mark.asyncio
async def test_get_current_user_returns_default_owner():
    async with make_client() as client:
        response = await client.get("/api/health")
        assert response.status_code == 200

    from app.config import DEFAULT_OWNER_ID
    from app.database import AsyncSessionLocal
    from app.deps import get_current_user

    async with AsyncSessionLocal() as session:
        user = await get_current_user(session)
        assert user.id == DEFAULT_OWNER_ID
        assert user.username == "test"


@pytest.mark.asyncio
async def test_base_repository_owner_scope_filters_get_by_id(db_session):
    repo = ContactRepository(db_session)
    c_owner1 = await repo.create(name="Owner1 Contact")
    c_owner2 = await repo.create(name="Owner2 Contact")
    c_owner2.owner_id = 2
    await db_session.commit()

    scoped = ContactRepository(db_session, owner_id=DEFAULT_OWNER_ID)
    found = await scoped.get_by_id(int(c_owner1.id))
    assert found is not None

    hidden = await scoped.get_by_id(int(c_owner2.id))
    assert hidden is None


@pytest.mark.asyncio
async def test_base_repository_owner_scope_filters_get_all(db_session):
    repo = ContactRepository(db_session)
    await repo.create(name="Mine")
    other = await repo.create(name="Foreign")
    other.owner_id = 2
    await db_session.commit()

    scoped = ContactRepository(db_session, owner_id=DEFAULT_OWNER_ID)
    rows = await scoped.get_all(limit=100)
    names = {r.name for r in rows}
    assert "Mine" in names
    assert "Foreign" not in names


@pytest.mark.asyncio
async def test_create_sets_owner_id(db_session):
    scoped = ContactRepository(db_session, owner_id=DEFAULT_OWNER_ID)
    c = await scoped.create(name="Scoped")
    assert c.owner_id == DEFAULT_OWNER_ID


@pytest.mark.asyncio
async def test_update_ignores_owner_id(db_session):
    scoped = ContactRepository(db_session, owner_id=DEFAULT_OWNER_ID)
    c = await scoped.create(name="Owner Locked")
    await scoped.update(int(c.id), owner_id=2, name="Renamed")
    await db_session.commit()

    fresh = ContactRepository(db_session, owner_id=DEFAULT_OWNER_ID)
    row = await fresh.get_by_id(int(c.id))
    assert row is not None
    assert row.name == "Renamed"
    assert row.owner_id == DEFAULT_OWNER_ID


@pytest.mark.asyncio
async def test_cross_owner_returns_404_via_api():
    async with make_client() as client:
        created = await client.post("/api/contacts/", json={"name": "API Contact"})
        cid = created.json()["id"]

    from app.database import AsyncSessionLocal
    from app.models import ContactModel

    async with AsyncSessionLocal() as session:
        contact = await session.get(ContactModel, cid)
        contact.owner_id = 2
        await session.commit()

    async with make_client() as client:
        response = await client.get(f"/api/contacts/{cid}")
        assert response.status_code == 404

        listing = await client.get("/api/contacts/")
        names = [c["name"] for c in listing.json()]
        assert "API Contact" not in names


@pytest.mark.asyncio
async def test_scoped_repositories_cover_hot_tables(db_session):
    """Gating: owner-scope фильтрует hot-таблицы (messages/tasks)."""
    contact_repo = ContactRepository(db_session)
    contact = await contact_repo.create(name="Scope Contact")

    msg_repo = MessageRepository(db_session)
    msg = await msg_repo.create(
        contact_id=contact.id, channel="telegram", content="hi",
        direction="incoming", status="unread",
    )
    msg.owner_id = 2

    task_repo = TaskRepository(db_session)
    task = await task_repo.create(contact_id=contact.id, title="t")
    task.owner_id = 2
    await db_session.commit()

    scoped_msg = MessageRepository(db_session, owner_id=DEFAULT_OWNER_ID)
    assert await scoped_msg.get_by_id(int(msg.id)) is None

    scoped_task = TaskRepository(db_session, owner_id=DEFAULT_OWNER_ID)
    assert await scoped_task.get_by_id(int(task.id)) is None


def test_all_owner_routers_declare_get_current_user():
    """Gating (негативный сценарий): если роутер забыл Depends(get_current_user)
    на каком-то эндпоинте, этот тест падает — данные этого эндпоинта перестанут
    фильтроваться по owner. Раньше тест искал подстроку в файле, теперь AST
    проверяет каждый @router.*-эндпоинт отдельно."""
    import ast
    import inspect
    import os

    from app import routers

    routers_dir = os.path.dirname(inspect.getfile(routers))
    modules = [
        "calendar.py", "contacts.py",
        "contact_folders.py", "dashboard.py", "export.py",
        "import_router.py", "messages.py", "settings.py",
        "startup.py", "tasks.py",
    ]
    router_methods = {"get", "post", "put", "patch", "delete"}
    # Глобальные эндпоинты (не работают с owner-данными), по дизайну:
    # settings.py — onboarding-файл.
    global_endpoints: dict[str, set[tuple[str, str]]] = {
        "settings": {
            ("get", "/onboarding-config"),
            ("get", "/onboarding-status"),
            ("post", "/onboarding-complete"),
            ("post", "/auth/logout"),
        },
    }
    found: dict[str, set[tuple[str, str]]] = {}

    def has_current_user_dep(func: ast.AsyncFunctionDef) -> bool:
        args = func.args.posonlyargs + func.args.args
        defaults = [None] * (len(args) - len(func.args.defaults)) + list(
            func.args.defaults
        )
        pairs = list(zip(args, defaults))
        pairs += list(zip(func.args.kwonlyargs, func.args.kw_defaults))
        for arg, default in pairs:
            if default is None:
                continue
            if (
                isinstance(default, ast.Call)
                and isinstance(default.func, ast.Name)
                and default.func.id == "Depends"
                and len(default.args) == 1
            ):
                target = default.args[0]
                if (
                    isinstance(target, ast.Name)
                    and target.id == "get_current_user"
                ) or (
                    isinstance(target, ast.Attribute)
                    and target.attr == "get_current_user"
                ):
                    return True
        return False

    for name in modules:
        stem = name.removesuffix(".py")
        path = os.path.join(routers_dir, name)
        with open(path, encoding="utf-8") as f:
            tree = ast.parse(f.read())
        found[stem] = set()
        for node in ast.walk(tree):
            if not isinstance(node, ast.AsyncFunctionDef):
                continue
            for deco in node.decorator_list:
                if not isinstance(deco, ast.Call):
                    continue
                deco_fn = deco.func
                if not (
                    isinstance(deco_fn, ast.Attribute)
                    and isinstance(deco_fn.value, ast.Name)
                    and deco_fn.value.id == "router"
                    and deco_fn.attr in router_methods
                ):
                    continue
                ep_path = None
                if deco.args and isinstance(deco.args[0], ast.Constant):
                    ep_path = deco.args[0].value
                key = (deco_fn.attr, ep_path)
                found[stem].add(key)
                if key in global_endpoints.get(stem, set()):
                    continue
                assert has_current_user_dep(node), (
                    f"{name} endpoint {deco_fn.attr.upper()} {ep_path} "
                    f"не декларирует Depends(get_current_user)"
                )

    for stem, exempts in global_endpoints.items():
        assert exempts <= found[stem], (
            f"{stem}: allowlist глобальных эндпоинтов устарел, "
            f"нет в коде: {sorted(exempts - found[stem])}"
        )
        found[stem] -= exempts

    # После вычета allowlist у каждого модуля остаются только владельческие
    # эндпоинты — все они обязаны иметь get_current_user.
    assert all(found.values()), f"Модули без эндпоинтов: {[k for k, v in found.items() if not v]}"
