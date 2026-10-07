import asyncio
import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from .config import DEFAULT_OWNER_ID, settings
from .database import get_async_session_maker, init_db
from .deps import get_poll_service, set_poll_service
from .errors import AppError
from .routers import (
    backup_router,
    calendar_router,
    channels_router,
    contact_folders_router,
    contacts_router,
    dashboard_router,
    export_router,
    import_router,
    messages_router,
    orders_router,
    outbox_router,
    products_router,
    reminders_router,
    settings_router,
    startup_router,
    suppliers_router,
    tasks_router,
    vpn_help_router,
)
from .routers.channels import cleanup_pending_auths
from .services.channel_message_service import ChannelMessageService
from .services.channel_service import ChannelService
from .services.message_service import MessageService
from .services.outbox_service import OutboxService
from .services.poll_service import PollService
from .services.reminder_scheduler import ReminderScheduler
from .services.settings_service import SettingsService
from .user_context import get_active_login
from .utils.logger import setup_logging
from .version import VERSION

logger = logging.getLogger(__name__)

poll_service: PollService | None = None
_outbox_task: asyncio.Task[Any] | None = None
_channel_reconnect_task: asyncio.Task[Any] | None = None
_reminder_scheduler: ReminderScheduler | None = None


async def _outbox_worker_loop() -> None:
    """Периодически доставляет pending-записи outbox (retry с backoff)."""
    while True:
        try:
            ps = get_poll_service()
            if ps is not None:
                session_maker = get_async_session_maker()
                async with session_maker() as session:
                    service = OutboxService(session, owner_id=DEFAULT_OWNER_ID)
                    await service.process_pending(
                        ps.channels,
                        settings.OUTBOX_MAX_ATTEMPTS,
                        settings.OUTBOX_BASE_DELAY,
                    )
                    await session.commit()
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error("Outbox worker error: %s", e)
        await asyncio.sleep(settings.OUTBOX_POLL_INTERVAL)


async def _channel_reconnect_loop() -> None:
    """Периодически переподключает каналы, отвалившиеся при старте без сети."""
    while True:
        try:
            ps = get_poll_service()
            if ps is not None:
                session_maker = get_async_session_maker()
                async with session_maker() as session:
                    service = ChannelService(session)
                    await service.reconnect_disconnected(ps)
                    await session.commit()
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error("Channel reconnect worker error: %s", e)
        await asyncio.sleep(settings.CHANNEL_RECONNECT_INTERVAL)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    global poll_service
    global _outbox_task
    global _channel_reconnect_task
    global _reminder_scheduler
    setup_logging()
    logger.info("Starting BiziBox...")

    _default_secrets = ("change-me-in-production", "dev-secret-key-not-for-production")
    if settings.SECRET_KEY in _default_secrets:
        logger.warning("SECRET_KEY не изменён — установите свой в .env")
    _default_enc = ("change-me-in-production", "dev-encryption-key-not-for-production")
    if settings.ENCRYPTION_KEY in _default_enc:
        logger.warning("ENCRYPTION_KEY не изменён — установите свой в .env")

    active_login = get_active_login()
    poll_service = None

    if active_login:
        await init_db()

        session_maker = get_async_session_maker()
        async with session_maker() as session:
            settings_service = SettingsService(session)
            await settings_service.ensure_defaults({
                "telegram_poll_interval": 300,
                "email_poll_interval": 60,
                "theme": "light",
                "onboarded": False,
            })

        poll_service = PollService(
            session_factory=session_maker,
            cms_factory=ChannelMessageService,
        )
        set_poll_service(poll_service)
        async with session_maker() as session:
            channel_service = ChannelService(session)
            await channel_service.restore_channels(poll_service)
        _outbox_task = asyncio.create_task(_outbox_worker_loop())
        _channel_reconnect_task = asyncio.create_task(_channel_reconnect_loop())
        _reminder_scheduler = ReminderScheduler(session_maker, interval=60)
        _reminder_scheduler.start()
    else:
        logger.info("No active user; skipping DB init and channel restore. Onboarding required.")

    yield

    logger.info("Shutting down BiziBox...")
    await cleanup_pending_auths()
    if _reminder_scheduler:
        await _reminder_scheduler.stop()
        _reminder_scheduler = None
    if _outbox_task:
        _outbox_task.cancel()
        try:
            await _outbox_task
        except asyncio.CancelledError:
            pass
        _outbox_task = None
    if _channel_reconnect_task:
        _channel_reconnect_task.cancel()
        try:
            await _channel_reconnect_task
        except asyncio.CancelledError:
            pass
        _channel_reconnect_task = None
    if poll_service:
        await poll_service.stop_all()
        for ct, adapter in list(poll_service.channels.items()):
            try:
                await adapter.disconnect()
            except Exception as e:
                logger.error(f"Error disconnecting {ct}: {e}")

    if active_login:
        try:
            session_maker = get_async_session_maker()
            async with session_maker() as session:
                message_service = MessageService(session, owner_id=DEFAULT_OWNER_ID)
                deleted = await message_service.cleanup_spam()
                await session.commit()
                if deleted:
                    logger.info("Cleaned up %d spam messages on shutdown", deleted)
        except Exception as e:
            logger.error("Spam cleanup on shutdown failed: %s", e)


limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[settings.RATE_LIMIT_DEFAULT],
    enabled=settings.RATE_LIMIT_ENABLED,
)

app = FastAPI(
    title="BiziBox API",
    version=VERSION,
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={"detail": jsonable_encoder(exc.errors())},
    )


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled exception: %s", exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "Внутренняя ошибка сервера"},
    )


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(SlowAPIMiddleware)

app.include_router(calendar_router)
app.include_router(messages_router, prefix="/api/messages", tags=["messages"])
app.include_router(outbox_router, prefix="/api/outbox", tags=["outbox"])
app.include_router(reminders_router, prefix="/api/reminders", tags=["reminders"])
app.include_router(contacts_router, prefix="/api/contacts", tags=["contacts"])
app.include_router(contact_folders_router, prefix="/api/folders", tags=["folders"])
app.include_router(tasks_router, prefix="/api/tasks", tags=["tasks"])
app.include_router(orders_router, prefix="/api/orders", tags=["orders"])
app.include_router(products_router, prefix="/api/products", tags=["products"])
app.include_router(suppliers_router, prefix="/api/suppliers", tags=["suppliers"])
app.include_router(channels_router, prefix="/api/channels", tags=["channels"])
app.include_router(dashboard_router, prefix="/api/dashboard", tags=["dashboard"])
app.include_router(export_router, prefix="/api/export", tags=["export"])
app.include_router(import_router, prefix="/api/import", tags=["import"])
app.include_router(backup_router, prefix="/api/backup", tags=["backup"])
app.include_router(settings_router, prefix="/api/settings", tags=["settings"])
app.include_router(startup_router, prefix="/api/startup", tags=["startup"])
app.include_router(vpn_help_router, prefix="/api/vpn-help", tags=["vpn-help"])


@app.get("/api/health")
@limiter.limit("60/minute")
async def health(request: Request) -> dict[str, Any]:
    return {"status": "ok", "version": VERSION, "app": "BiziBox"}


def _resolve_frontend_dist() -> Path | None:
    """Каталог собранного фронтенда или None, если сборки нет.

    В frozen-сборке (PyInstaller) фронтенд лежит в sys._MEIPASS/frontend;
    в dev — в frontend/dist рядом с backend/.
    """
    if getattr(sys, "frozen", False):
        base = Path(getattr(sys, "_MEIPASS", Path.cwd()))
        candidate = base / "frontend"
    else:
        backend_dir = Path(__file__).resolve().parent.parent
        candidate = backend_dir.parent / "frontend" / "dist"
    candidate = candidate.resolve()
    return candidate if (candidate / "index.html").is_file() else None


_frontend_dir = _resolve_frontend_dist()

if _frontend_dir is not None:
    frontend_dir = _frontend_dir
    _assets_dir = frontend_dir / "assets"
    if _assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=str(_assets_dir)), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def _spa_fallback(full_path: str, request: Request) -> Response:
        # GET /api/xxx без слеша не совпадает с роутами (они зарегистрированы
        # с `/` на конце), поэтому редиректим на версию со слешем. Если слеш
        # уже есть и маршрут всё равно не нашёлся — это честный 404.
        if full_path.startswith("api/"):
            if not full_path.endswith("/"):
                query = request.url.query
                url = f"/{full_path}/" + (f"?{query}" if query else "")
                return RedirectResponse(url=url, status_code=307)
            return JSONResponse(status_code=404, content={"detail": "Not found"})
        candidate = (frontend_dir / full_path).resolve()
        if candidate.is_file() and candidate.is_relative_to(frontend_dir):
            if candidate.name == "index.html":
                return FileResponse(candidate, headers={"Cache-Control": "no-store"})
            return FileResponse(candidate)
        return FileResponse(frontend_dir / "index.html", headers={"Cache-Control": "no-store"})
else:
    logger.warning("frontend/dist не найден — отдаю только API")

    @app.get("/", include_in_schema=False)
    async def _no_frontend() -> JSONResponse:
        return JSONResponse(
            status_code=503,
            content={
                "detail": "Frontend build not found. Run `npm run build` in frontend/."
            },
        )
