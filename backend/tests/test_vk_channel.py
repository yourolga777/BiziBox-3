from unittest.mock import MagicMock

import pytest

from app.repositories.contact import ContactRepository
from app.services.channel_message_service import ChannelMessageService
from app.services.channel_service import ChannelService
from app.utils.crypto import encrypt


@pytest.mark.asyncio
async def test_contact_get_or_create_vk_dedup(db_session):
    repo = ContactRepository(db_session)
    c1 = await repo.get_or_create(name="Иван", channel="vk", channel_id="456")
    c2 = await repo.get_or_create(name="Иван", channel="vk", channel_id="456")
    assert c1.id == c2.id
    assert c2.vk_id == "456"


@pytest.mark.asyncio
async def test_contact_get_by_vk_id(db_session):
    repo = ContactRepository(db_session)
    await repo.get_or_create(name="Иван", channel="vk", channel_id="456")
    found = await repo.get_by_vk_id("456")
    assert found is not None
    assert found.vk_id == "456"


@pytest.mark.asyncio
async def test_contact_filter_by_vk_channel(db_session):
    repo = ContactRepository(db_session)
    await repo.get_or_create(name="Иван", channel="vk", channel_id="456")
    await repo.get_or_create(name="Петя", channel="vk", channel_id="789")
    await repo.get_or_create(name="Тг", channel="telegram", channel_id="111")

    vk_contacts = await repo.get_all(channel="vk")
    assert len(vk_contacts) == 2


@pytest.mark.asyncio
async def test_resolve_channel_id_vk(db_session):
    repo = ContactRepository(db_session)
    contact = await repo.get_or_create(name="Иван", channel="vk", channel_id="456")
    service = ChannelMessageService(db_session)

    channel_id = await service._resolve_channel_id(contact, "vk")
    assert channel_id == "456"


def test_vk_config_decrypts_token():
    service = ChannelService(MagicMock())
    token = "vk1.a.secret"
    cfg = service._vk_config({"group_id": 123, "token": encrypt(token)})

    assert cfg["group_id"] == 123
    assert cfg["token"] == token
