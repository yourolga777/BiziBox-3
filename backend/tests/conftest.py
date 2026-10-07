from collections.abc import AsyncGenerator
from typing import Any, cast

import pytest  # noqa: F401  (используется фикстурой _disable_rate_limit)
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Patch the global engine BEFORE any test module imports app.main.
# This prevents tests from accidentally touching the production database.
import app.database as _db_mod
import app.user_context as _user_ctx

TEST_DATABASE_URL = "sqlite+aiosqlite://"

_test_engine = create_async_engine(
    TEST_DATABASE_URL, connect_args={"check_same_thread": False}
)

from sqlalchemy import event  # noqa: E402

from app.db_functions import register_sqlite_functions  # noqa: E402

event.listen(_test_engine.sync_engine, "connect", register_sqlite_functions)
_test_session_factory = async_sessionmaker(
    _test_engine, class_=AsyncSession, expire_on_commit=False
)

_db_mod.engine = _test_engine
_db_mod.AsyncSessionLocal = _test_session_factory
_user_ctx.get_active_login = lambda: "test"

from app.database import Base  # noqa: E402
from app.models import (  # noqa: E402, F401
    ChannelModel,
    ContactFolderModel,
    ContactModel,
    ImportMappingModel,
    MessageModel,
    SettingsModel,
    TaskModel,
    UserModel,
)


@pytest.fixture(autouse=True)
def _disable_rate_limit():
    """Отключает глобальный rate-limit для тестов (иначе сотни запросов
    с одного адреса упрутся в default_limits=60/minute и сломают suite).

    Тесты, проверяющие сам rate-limit, включают limiter.enabled=True вручную.
    """
    from app.main import app

    app.state.limiter.enabled = False
    yield
    app.state.limiter.enabled = True


def make_transport() -> ASGITransport:
    """ASGITransport с корректной типизацией ASGI-приложения.

    FastAPI.__call__ не совпадает по сигнатуре с ожидаемым httpx типом ASGI-app,
    поэтому явно кастим в Any (тестовый хелпер, не продакшен-код).
    """
    from app.main import app

    return ASGITransport(app=cast(Any, app))


def make_client() -> AsyncClient:
    """AsyncClient с in-process ASGI-транспортом для HTTP-тестов."""
    return AsyncClient(transport=make_transport(), base_url="http://test")


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = async_sessionmaker(
        bind=_test_engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        yield session

    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
