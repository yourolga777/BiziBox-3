import pytest

from tests.conftest import make_client


@pytest.mark.asyncio
async def test_vpn_help_builtin_proxy():
    async with make_client() as client:
        response = await client.get("/api/vpn-help", params={"name": "v2rayN"})
    assert response.status_code == 200
    data = response.json()
    assert data["found"] is True
    assert data["category"] == "proxy"
    assert data["source"] == "builtin"
    assert data["default_port"] == "10808"


@pytest.mark.asyncio
async def test_vpn_help_builtin_system_vpn():
    async with make_client() as client:
        response = await client.get("/api/vpn-help", params={"name": "Happ"})
    assert response.status_code == 200
    data = response.json()
    assert data["found"] is True
    assert data["category"] == "system_vpn"
    assert data["source"] == "builtin"


@pytest.mark.asyncio
async def test_vpn_help_builtin_by_alias():
    async with make_client() as client:
        response = await client.get("/api/vpn-help", params={"name": "Clash Verge"})
    assert response.status_code == 200
    data = response.json()
    assert data["found"] is True
    assert data["category"] == "proxy"


@pytest.mark.asyncio
async def test_vpn_help_web_fallback(monkeypatch):
    async def fake_web(name: str):
        return {
            "found": True,
            "name": name,
            "category": "unknown",
            "description": "Some service description",
            "advice": "generic",
            "default_port": None,
            "source": "web",
        }

    monkeypatch.setattr("app.routers.vpn_help._web_lookup", fake_web)
    async with make_client() as client:
        response = await client.get("/api/vpn-help", params={"name": "zzzunknownservice"})
    assert response.status_code == 200
    data = response.json()
    assert data["found"] is True
    assert data["source"] == "web"


@pytest.mark.asyncio
async def test_vpn_help_not_found(monkeypatch):
    async def fake_web(name: str):
        return None

    monkeypatch.setattr("app.routers.vpn_help._web_lookup", fake_web)
    async with make_client() as client:
        response = await client.get("/api/vpn-help", params={"name": "zzzunknownservice"})
    assert response.status_code == 200
    data = response.json()
    assert data["found"] is False
    assert "message" in data
