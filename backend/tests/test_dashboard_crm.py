import pytest

from app.database import init_db
from app.routers import dashboard
from tests.conftest import make_client


@pytest.fixture(autouse=True)
async def setup_db():
    await init_db(clear_first=True)


async def _client():
    return make_client()


@pytest.mark.asyncio
async def test_dashboard_metrics_new_fields():
    async with await _client() as client:
        c = (await client.post('/api/contacts/', json={'name': 'Дэш'})).json()
        for ch in ['telegram', 'telegram', 'email']:
            await client.post('/api/messages/', json={
                'contact_id': c['id'], 'channel': ch, 'content': 'привет',
                'direction': 'incoming',
            })
        r = await client.get('/api/dashboard/metrics')
        assert r.status_code == 200
        data = r.json()
        assert 'channel_distribution' in data
        assert 'top_contacts' in data
        tg = next(
            (
                x
                for x in data["channel_distribution"]
                if x["channel"] == "telegram"
            ),
            None,
        )
        assert tg is not None
        assert tg["count"] == 2
        top = data["top_contacts"]
        assert top and top[0]["contact_name"] == "Дэш"
        assert top[0]["message_count"] == 3


@pytest.mark.asyncio
async def test_dashboard_unread_chats_counts_chats_not_messages():
    dashboard._cache.clear()
    async with await _client() as client:
        a = (await client.post('/api/contacts/', json={'name': 'A'})).json()
        b = (await client.post('/api/contacts/', json={'name': 'B'})).json()
        spam = (await client.post('/api/contacts/', json={'name': 'Spam'})).json()

        for _ in range(2):
            await client.post('/api/messages/', json={
                'contact_id': a['id'], 'channel': 'telegram',
                'content': 'привет', 'direction': 'incoming',
            })
        await client.post('/api/messages/', json={
            'contact_id': b['id'], 'channel': 'email',
            'content': 'письмо', 'direction': 'incoming',
        })
        await client.patch(f"/api/contacts/{spam['id']}", json={'life_sphere': 'spam'})
        for _ in range(3):
            await client.post('/api/messages/', json={
                'contact_id': spam['id'], 'channel': 'telegram',
                'content': 'x', 'direction': 'incoming',
            })

        r = await client.get('/api/dashboard/metrics')
        assert r.status_code == 200
        data = r.json()
        assert data['unread_messages'] == 6
        assert data['unread_chats'] == 2
