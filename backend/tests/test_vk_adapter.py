import httpx
import pytest

from app.channels.vk import VkAdapter

GROUP_ID = 123
TOKEN = "vk1.a.test"
LP_SERVER = "https://lp.vk.com/test"


def _handler(api, lp=None):
    def fn(request: httpx.Request) -> httpx.Response:
        if request.url.host == "api.vk.com":
            method = request.url.path.rstrip("/").split("/")[-1]
            body = api.get(
                method, {"error": {"error_code": 1, "error_msg": "unknown method"}}
            )
            return httpx.Response(200, json=body)
        if request.url.host == "lp.vk.com":
            if lp is None:
                return httpx.Response(
                    200, json={"ts": "200", "updates": [], "failed": 0}
                )
            if isinstance(lp, httpx.Response):
                return lp
            return httpx.Response(200, json=lp)
        return httpx.Response(404)

    return fn


def _adapter(api, lp=None):
    return VkAdapter(transport=httpx.MockTransport(_handler(api, lp)))


def _base_api():
    return {
        "groups.getLongPollServer": {
            "response": {"server": LP_SERVER, "key": "k", "ts": "1"}
        },
        "groups.getById": {"response": [{"id": GROUP_ID, "name": "Shop"}]},
    }


@pytest.mark.asyncio
async def test_vk_connect_requires_group_id_and_token():
    adapter = VkAdapter()
    assert await adapter.connect({}) is False
    assert await adapter.connect({"group_id": GROUP_ID}) is False
    assert await adapter.connect({"token": TOKEN}) is False


@pytest.mark.asyncio
async def test_vk_connect_success():
    adapter = _adapter(_base_api())
    assert await adapter.connect({"group_id": GROUP_ID, "token": TOKEN}) is True


@pytest.mark.asyncio
async def test_vk_connect_failure_on_bad_token():
    adapter = _adapter(
        {
            "groups.getLongPollServer": {
                "error": {"error_code": 5, "error_msg": "auth failed"}
            }
        }
    )
    assert await adapter.connect({"group_id": GROUP_ID, "token": "bad"}) is False


@pytest.mark.asyncio
async def test_vk_no_client_operations():
    adapter = VkAdapter()
    assert await adapter.fetch_messages() == []
    assert await adapter.get_dialog("456") == []
    with pytest.raises(Exception, match="VK client not connected"):
        await adapter.send_message("456", "hello")


@pytest.mark.asyncio
async def test_vk_fetch_messages_parses_message_new():
    update = {
        "type": "message_new",
        "object": {
            "message": {
                "from_id": 456,
                "peer_id": 456,
                "id": 111,
                "conversation_message_id": 222,
                "date": 1700000000,
                "text": "Привет",
            }
        },
        "group_id": GROUP_ID,
    }
    api = _base_api()
    api["users.get"] = {
        "response": [{"id": 456, "first_name": "Иван", "last_name": "Петров"}]
    }
    adapter = _adapter(api, lp={"ts": "200", "updates": [update], "failed": 0})

    assert await adapter.connect({"group_id": GROUP_ID, "token": TOKEN}) is True
    messages = await adapter.fetch_messages()

    assert len(messages) == 1
    m = messages[0]
    assert m["channel"] == "vk"
    assert m["channel_id"] == "456"
    assert m["message_id"] == "222"
    assert m["direction"] == "incoming"
    assert m["contact_id"] == "456"
    assert m["contact_name"] == "Иван Петров"
    assert m["content"] == "Привет"


@pytest.mark.asyncio
async def test_vk_fetch_outgoing_message():
    update = {
        "type": "message_new",
        "object": {
            "message": {
                "from_id": -GROUP_ID,
                "peer_id": 456,
                "id": 333,
                "conversation_message_id": 444,
                "date": 1700000000,
                "text": "Ответ бота",
            }
        },
        "group_id": GROUP_ID,
    }
    adapter = _adapter(_base_api(), lp={"ts": "200", "updates": [update], "failed": 0})

    await adapter.connect({"group_id": GROUP_ID, "token": TOKEN})
    messages = await adapter.fetch_messages()

    assert len(messages) == 1
    assert messages[0]["direction"] == "outgoing"


@pytest.mark.asyncio
async def test_vk_fetch_error_returns_empty():
    adapter = _adapter(_base_api(), lp=httpx.Response(500))
    await adapter.connect({"group_id": GROUP_ID, "token": TOKEN})
    assert await adapter.fetch_messages() == []


@pytest.mark.asyncio
async def test_vk_send_message():
    api = _base_api()
    api["messages.send"] = {"response": 789}
    adapter = _adapter(api)
    await adapter.connect({"group_id": GROUP_ID, "token": TOKEN})

    result = await adapter.send_message("456", "Ответ")

    assert result["message_id"] == "789"
    assert result["channel"] == "vk"
    assert result["channel_id"] == "456"


@pytest.mark.asyncio
async def test_vk_get_dialog():
    api = _base_api()
    api["messages.getHistory"] = {
        "response": {
            "items": [
                {
                    "id": 1,
                    "conversation_message_id": 10,
                    "from_id": 456,
                    "date": 1700000000,
                    "text": "Привет",
                }
            ]
        }
    }
    adapter = _adapter(api)
    await adapter.connect({"group_id": GROUP_ID, "token": TOKEN})

    result = await adapter.get_dialog("456")

    assert len(result) == 1
    assert result[0]["message_id"] == "10"
    assert result[0]["content"] == "Привет"
    assert result[0]["direction"] == "incoming"
