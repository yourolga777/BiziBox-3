import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.contact import ContactRepository


@pytest.mark.asyncio
async def test_get_or_create_persists_telegram_username(db_session: AsyncSession):
    repo = ContactRepository(db_session)
    contact = await repo.get_or_create(
        name="Alice",
        channel="telegram",
        channel_id="12345",
        telegram_username="alice",
    )

    assert contact.telegram_username == "alice"
    stored = await repo.get_by_telegram_id("12345")
    assert stored is not None
    assert stored.telegram_username == "alice"


@pytest.mark.asyncio
async def test_get_or_create_updates_telegram_username(db_session: AsyncSession):
    repo = ContactRepository(db_session)
    first = await repo.get_or_create(
        name="Alice",
        channel="telegram",
        channel_id="12345",
        telegram_username="alice",
    )

    again = await repo.get_or_create(
        name="Alice",
        channel="telegram",
        channel_id="12345",
        telegram_username="alice_new",
    )

    assert again.id == first.id
    stored = await repo.get_by_telegram_id("12345")
    assert stored is not None
    assert stored.telegram_username == "alice_new"


@pytest.mark.asyncio
async def test_get_or_create_email_keeps_telegram_username_none(
    db_session: AsyncSession,
):
    repo = ContactRepository(db_session)
    contact = await repo.get_or_create(
        name="Elena",
        channel="email",
        channel_id="elena@example.com",
    )

    assert contact.telegram_username is None
    assert contact.email == "elena@example.com"


@pytest.mark.asyncio
async def test_get_or_create_email_updates_placeholder_name(
    db_session: AsyncSession,
):
    repo = ContactRepository(db_session)
    first = await repo.get_or_create(
        name="elena@example.com",
        channel="email",
        channel_id="elena@example.com",
    )
    assert first.name == "elena@example.com"

    again = await repo.get_or_create(
        name="Elena Ivanova",
        channel="email",
        channel_id="elena@example.com",
    )
    assert again.id == first.id
    stored = await repo.get_by_email("elena@example.com")
    assert stored is not None
    assert stored.name == "Elena Ivanova"


@pytest.mark.asyncio
async def test_get_or_create_email_does_not_overwrite_real_name(
    db_session: AsyncSession,
):
    repo = ContactRepository(db_session)
    first = await repo.get_or_create(
        name="Elena Ivanova",
        channel="email",
        channel_id="elena@example.com",
    )

    again = await repo.get_or_create(
        name="Another Name",
        channel="email",
        channel_id="elena@example.com",
    )
    assert again.id == first.id
    stored = await repo.get_by_email("elena@example.com")
    assert stored is not None
    assert stored.name == "Elena Ivanova"
