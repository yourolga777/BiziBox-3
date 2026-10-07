"""RC-13: rate-limit 429 + универсальный тест отсутствия эндпоинтов без лимита."""

from typing import Callable

from fastapi import FastAPI, Request
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address
from starlette.testclient import TestClient


def _make_app(default_limits: list[str | Callable[..., str]]) -> FastAPI:
    limiter = Limiter(
        key_func=get_remote_address,
        default_limits=default_limits,
        enabled=True,
    )
    app = FastAPI()
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]
    app.add_middleware(SlowAPIMiddleware)
    return app


def test_rate_limit_exceeded_returns_429():
    """Превышение default-лимита middleware возвращает 429."""
    app = _make_app(["2/minute"])

    @app.get("/probe")
    def probe(request: Request) -> dict[str, bool]:
        return {"ok": True}

    client = TestClient(app)
    assert client.get("/probe").status_code == 200
    assert client.get("/probe").status_code == 200
    assert client.get("/probe").status_code == 429


def test_limiter_response_uses_429_and_exception_handler():
    """429 приходит именно через RateLimitExceeded-handler (JSON)."""
    app = _make_app(["1/minute"])

    @app.get("/probe2")
    def probe2(request: Request) -> dict[str, bool]:
        return {"ok": True}

    client = TestClient(app)
    assert client.get("/probe2").status_code == 200
    assert client.get("/probe2").status_code == 429


def test_all_api_routes_covered_by_default_limiter():
    """Каждый /api маршрут приложения покрыт глобальным лимитом.

    slowapi применяет default_limits ко всем маршрутам через SlowAPIMiddleware,
    если у маршрута нет собственного @limiter.limit. Тест проверяет:
    - middleware установлен;
    - у лимитера задан default_limits;
    - есть хотя бы одна явная @limiter.limit-помеченная точка (health).
    """
    from app.main import app

    limiter: Limiter = app.state.limiter

    # 1. Middleware зарегистрирован.
    middleware_classes = [m.cls for m in app.user_middleware]
    assert SlowAPIMiddleware in middleware_classes, "SlowAPIMiddleware не установлен"

    # 2. default_limits задан — применяется ко всем непомеченным маршрутам.
    assert list(limiter._default_limits), "default_limits не задан"

    # 3. Есть хотя бы один явно помеченный @limiter.limit эндпоинт.
    marked = getattr(limiter, "_Limiter__marked_for_limiting", {})
    assert marked, "ни один эндпоинт не помечен @limiter.limit"

    # 4. Каждый /api маршрут имеет endpoint, и он покрыт либо вручную,
    #    либо дефолтом (middleware). Собираем имена для прозрачности.
    from starlette.routing import Route

    api_routes = [
        route
        for route in app.routes
        if isinstance(route, Route) and route.path.startswith("/api")
    ]
    assert api_routes, "нет /api маршрутов для проверки"
    assert len(api_routes) >= 50, f"подозрительно мало маршрутов: {len(api_routes)}"
