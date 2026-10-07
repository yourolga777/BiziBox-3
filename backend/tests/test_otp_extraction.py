import pytest

from app.database import init_db
from app.services.otp import extract_otp
from tests.conftest import make_client


@pytest.fixture(autouse=True)
async def setup_db():
    await init_db(clear_first=True)


@pytest.mark.parametrize(
    ("content", "expected"),
    [
        ("Ваш код подтверждения: 123456", "123456"),
        ("Код: 1234", "1234"),
        ("Пароль для входа — 87654321", "87654321"),
        ("Your code is 456789", "456789"),
        ("password: 123-456", "123456"),
        ("Login code 12 34 56", "123456"),
        ("одноразовый пароль 9876", "9876"),
        ("PIN: 1357", "1357"),
        ("Код 13579 пришёл", "13579"),
    ],
)
def test_extract_otp_positive(content, expected):
    assert extract_otp(content) == expected


@pytest.mark.parametrize(
    "content",
    [
        None,
        "",
        "Привет, как дела?",
        "Сумма заказа 1234567890 рублей",  # 10 цифр — не OTP
        "Код: 12",  # слишком короткий
        "Скидка 50% на всё",
    ],
)
def test_extract_otp_negative(content):
    assert extract_otp(content) is None


async def _service_folder_id(client) -> int:
    resp = await client.post(
        "/api/folders/",
        json={"name": "Сервисные", "category_key": "service", "sphere": "work"},
    )
    assert resp.status_code == 201
    return int(resp.json()["id"])


async def _create_message_for_contact(client, folder_id, content):
    contact = await client.post(
        "/api/contacts/",
        json={"name": "OTP", "folder_id": folder_id, "life_sphere": "work"},
    )
    assert contact.status_code == 201
    cid = contact.json()["id"]
    created = await client.post(
        "/api/messages/",
        json={
            "contact_id": cid,
            "channel": "telegram",
            "content": content,
            "direction": "incoming",
        },
    )
    assert created.status_code == 201
    return created.json()["id"]


@pytest.mark.asyncio
async def test_service_contact_returns_extracted_code():
    async with make_client() as client:
        fid = await _service_folder_id(client)
        mid = await _create_message_for_contact(
            client, fid, "Ваш код подтверждения: 123456"
        )
        response = await client.get(f"/api/messages/{mid}")
    assert response.status_code == 200
    assert response.json()["extracted_code"] == "123456"


@pytest.mark.asyncio
async def test_service_contact_english_code():
    async with make_client() as client:
        fid = await _service_folder_id(client)
        mid = await _create_message_for_contact(
            client, fid, "Your verification code: 654321"
        )
        response = await client.get(f"/api/messages/{mid}")
    assert response.json()["extracted_code"] == "654321"


@pytest.mark.asyncio
async def test_non_service_contact_extracted_code_null():
    async with make_client() as client:
        for sphere in ("personal", "work", None):
            contact = await client.post(
                "/api/contacts/",
                json={"name": f"Non svc {sphere}", "life_sphere": sphere},
            )
            cid = contact.json()["id"]
            created = await client.post(
                "/api/messages/",
                json={
                    "contact_id": cid,
                    "channel": "telegram",
                    "content": "Ваш код: 123456",
                    "direction": "incoming",
                },
            )
            response = await client.get(f"/api/messages/{created.json()['id']}")
            assert response.json()["extracted_code"] is None, sphere


@pytest.mark.asyncio
async def test_service_contact_without_code_null():
    async with make_client() as client:
        fid = await _service_folder_id(client)
        mid = await _create_message_for_contact(
            client, fid, "Спасибо за покупку!"
        )
        response = await client.get(f"/api/messages/{mid}")
    assert response.json()["extracted_code"] is None
