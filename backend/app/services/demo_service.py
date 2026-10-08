"""Демо-режим: создаёт логин `demo` с предзаполненными данными.

Позволяет пощупать все функции приложения без регистрации и подключения
реальных каналов. Данные изолированы в `data/users/demo/` и пересоздаются
заново при каждом входе в демо.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ..config import DEFAULT_OWNER_ID
from ..database import get_async_session_maker, init_db
from ..deps import get_poll_service, set_poll_service
from ..models import (
    CalendarEventModel,
    ContactFolderModel,
    ContactModel,
    MessageModel,
    OrderCommentModel,
    OrderItemModel,
    OrderModel,
    ProductModel,
    SupplierModel,
    TaskModel,
)
from ..repositories.user import UserRepository
from ..services.channel_message_service import ChannelMessageService
from ..services.channel_service import ChannelService
from ..services.poll_service import PollService
from ..services.settings_service import SettingsService
from ..user_context import ensure_user_data_dir, set_active_login

logger = logging.getLogger(__name__)

DEMO_LOGIN = "demo"


async def _restart_poll_service(session_maker: async_sessionmaker[AsyncSession]) -> None:
    """Пересоздаёт poll-сервис под демо-пользователя (каналов нет, но сервис нужен)."""
    old_ps = get_poll_service()
    if old_ps:
        await old_ps.stop_all()
        for _ct, adapter in list(old_ps.channels.items()):
            try:
                await adapter.disconnect()
            except Exception as e:  # pragma: no cover - defensive
                logger.error("Error disconnecting old channel: %s", e)

    new_ps = PollService(
        session_factory=session_maker,
        cms_factory=ChannelMessageService,
    )
    set_poll_service(new_ps)
    async with session_maker() as session:
        channel_service = ChannelService(session)
        await channel_service.restore_channels(new_ps)


async def seed_demo_data(session: AsyncSession) -> None:
    """Наполняет демо-БД данными по всем разделам приложения."""
    now = datetime.now()
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday = today - timedelta(days=1)

    # --- Папки (системные уже созданы; привязываем по category_key) ---
    folder_rows = (await session.execute(select(ContactFolderModel))).scalars().all()
    folder_by_key: dict[str, int] = {}
    for f in folder_rows:
        if f.category_key and f.category_key not in folder_by_key:
            folder_by_key[f.category_key] = f.id

    def fid(*keys: str) -> int | None:
        for k in keys:
            if k in folder_by_key:
                return folder_by_key[k]
        return None

    # --- Контакты ---
    contacts: dict[str, ContactModel] = {}
    contact_specs: list[dict[str, Any]] = [
        dict(name="Алексей Смирнов", sphere="work", folder=("customers",),
             phone="+7 912 300 11 22", tg_username="alex_smirnov", is_known=True),
        dict(name="Мария Иванова", sphere="work", folder=("customers",),
             phone="+7 921 400 33 44", email="maria@studio.ru", is_known=True),
        dict(name="Дмитрий Козлов", sphere="work", folder=("customers",),
             phone="+7 903 555 66 77", tg_username="dmitry_kozlov", is_known=True),
        dict(name="Елена Соколова", sphere="work", folder=("customers",),
             phone="+7 911 222 33 44", vk_id="vk_elena", is_known=True),
        dict(name="ООО «ЗвукПро»", sphere="work", folder=("suppliers",),
             email="sales@zvukpro.ru", phone="+7 495 111 22 33", is_known=True),
        dict(name="ООО «АудиоТрейд»", sphere="work", folder=("suppliers",),
             email="import@audiotrade.ru", phone="+7 495 222 33 44", is_known=True),
        dict(name="Игорь Волков", sphere="work", folder=("customers",),
             phone="+7 926 700 88 99", tg_username="igor_volkov", is_known=True),
        dict(name="Ольга Петрова", sphere="personal", folder=("family",),
             phone="+7 916 000 11 22", birthday=date(1985, 5, 14), is_known=True),
        dict(name="Сергей Орлов", sphere="personal", folder=("friends",),
             tg_username="sergey_orlov", vk_id="vk_sergey", birthday=date(1990, 11, 2), is_known=True),
        dict(name="Новый клиент (из Авито)", sphere="work", folder=None,
             phone="+7 999 123 45 67", is_known=False,
             notes="Позвонил по объявлению о продаже микрофона"),
    ]
    for spec in contact_specs:
        keys = spec.get("folder")
        contact = ContactModel(
            owner_id=DEFAULT_OWNER_ID,
            name=spec["name"],
            life_sphere=spec["sphere"],
            folder_id=fid(*keys) if keys else None,
            phone=spec.get("phone"),
            email=spec.get("email"),
            telegram_username=spec.get("tg_username"),
            vk_id=spec.get("vk_id"),
            birthday=spec.get("birthday"),
            notes=spec.get("notes"),
            is_known=spec.get("is_known", True),
            created_at=today - timedelta(days=30),
        )
        session.add(contact)
        contacts[spec["name"]] = contact
    await session.flush()

    # --- Поставщики ---
    supplier_zvuk = SupplierModel(
        owner_id=DEFAULT_OWNER_ID,
        contact_id=contacts["ООО «ЗвукПро»"].id,
        company_name="ЗвукПро",
        inn="7701234567",
        notes="Основной поставщик наушников и микрофонов",
    )
    supplier_audio = SupplierModel(
        owner_id=DEFAULT_OWNER_ID,
        contact_id=contacts["ООО «АудиоТрейд»"].id,
        company_name="АудиоТрейд",
        inn="7707654321",
        notes="Импорт из-за рубежа, срок поставки 2–3 недели",
    )
    session.add_all([supplier_zvuk, supplier_audio])
    await session.flush()

    # --- Товары (аудио-оборудование) ---
    products: dict[str, ProductModel] = {}
    product_specs: list[dict[str, Any]] = [
        dict(name="Наушники Sony WH-1000XM5", sku="AUD-001", price=32990.0, purchase=24000.0,
             stock=12, supplier=supplier_zvuk),
        dict(name="Микрофон Shure SM7B", sku="AUD-002", price=42000.0, purchase=31000.0,
             stock=5, supplier=supplier_zvuk),
        dict(name="Аудиоинтерфейс Focusrite Scarlett 2i2", sku="AUD-003", price=15500.0, purchase=11800.0,
             stock=8, supplier=supplier_audio),
        dict(name="Студийные мониторы Yamaha HS8", sku="AUD-004", price=62000.0, purchase=47000.0,
             stock=4, supplier=supplier_audio),
        dict(name="Цифровой микшер Behringer X32", sku="AUD-005", price=185000.0, purchase=142000.0,
             stock=2, supplier=supplier_audio),
        dict(name="Кабель XLR 5 м", sku="AUD-006", price=890.0, purchase=450.0,
             stock=50, supplier=supplier_zvuk),
        dict(name="Стойка микрофонная", sku="AUD-007", price=2400.0, purchase=1600.0,
             stock=15, supplier=supplier_zvuk),
    ]
    for i, spec in enumerate(product_specs):
        product = ProductModel(
            owner_id=DEFAULT_OWNER_ID,
            name=spec["name"],
            sku=spec["sku"],
            price=spec["price"],
            purchase_price=spec["purchase"],
            stock=spec["stock"],
            unit="шт",
            supplier_id=spec["supplier"].id,
            created_at=today - timedelta(days=20 - i),
        )
        session.add(product)
        products[spec["name"]] = product
    await session.flush()

    # --- Заказы ---
    order_specs: list[dict[str, Any]] = [
        dict(number="ORD-1001", contact="Алексей Смирнов", status="new", paid=False,
             address="г. Москва, ул. Ленина, 10", payment="Карта", days_ago=0,
             items=[("Наушники Sony WH-1000XM5", 1, 32990.0)],
             comments=["Клиент просил оригинал, не реплику"]),
        dict(number="ORD-1002", contact="Мария Иванова", status="new", paid=True,
             address="г. Санкт-Петербург, Невский пр., 25", payment="Наличные", days_ago=1,
             items=[("Микрофон Shure SM7B", 1, 42000.0), ("Кабель XLR 5 м", 2, 890.0)],
             comments=["Оплата получена, ждём отгрузку"]),
        dict(number="ORD-1003", contact="Дмитрий Козлов", status="in_progress", paid=False,
             address="г. Казань, ул. Баумана, 3", payment="Карта", days_ago=3,
             items=[("Аудиоинтерфейс Focusrite Scarlett 2i2", 1, 15500.0)],
             comments=["Товар в пути от поставщика"]),
        dict(number="ORD-1004", contact="Елена Соколова", status="shipped", paid=True,
             address="г. Екатеринбург, ул. Мира, 12", payment="Карта", days_ago=5,
             items=[("Студийные мониторы Yamaha HS8", 2, 62000.0)],
             comments=["Отправлен СДЭК, трек-номер выслан"]),
        dict(number="ORD-1005", contact="Мария Иванова", status="completed", paid=True,
             address="г. Санкт-Петербург, Невский пр., 25", payment="Наличные", days_ago=10,
             items=[("Стойка микрофонная", 3, 2400.0), ("Кабель XLR 5 м", 4, 890.0)],
             comments=["Заказ выполнен, клиент доволен"]),
        dict(number="ORD-1006", contact="Дмитрий Козлов", status="cancelled", paid=False,
             address=None, payment="Карта", days_ago=12,
             items=[("Цифровой микшер Behringer X32", 1, 185000.0)],
             comments=["Клиент отказался — передумал по бюджету"]),
    ]
    for spec in order_specs:
        contact = contacts[spec["contact"]]
        items_total = sum(qty * price for _name, qty, price in spec["items"])
        order = OrderModel(
            owner_id=DEFAULT_OWNER_ID,
            order_number=spec["number"],
            contact_id=contact.id,
            status=spec["status"],
            total=items_total,
            paid=spec["paid"],
            delivery_address=spec["address"],
            payment_method=spec["payment"],
            created_at=today - timedelta(days=spec["days_ago"]),
        )
        session.add(order)
        await session.flush()
        for name, qty, price in spec["items"]:
            prod = products.get(name)
            session.add(OrderItemModel(
                owner_id=DEFAULT_OWNER_ID,
                order_id=order.id,
                product_id=prod.id if prod else None,
                name=name,
                quantity=qty,
                price=price,
            ))
        for text in spec["comments"]:
            session.add(OrderCommentModel(
                owner_id=DEFAULT_OWNER_ID,
                order_id=order.id,
                content=text,
            ))

    # --- Задачи ---
    task_specs: list[dict[str, Any]] = [
        dict(title="Перезвонить Алексею по заказу ORD-1001", contact="Алексей Смирнов",
             status="new", due=today + timedelta(hours=3)),
        dict(title="Отправить счёт ООО «АудиоТрейд»", contact="ООО «АудиоТрейд»",
             status="new", due=today + timedelta(days=1)),
        dict(title="Забрать микрофоны со склада", contact=None,
             status="new", due=yesterday),
        dict(title="Ответить Елене во ВКонтакте", contact="Елена Соколова",
             status="new", due=today + timedelta(hours=5)),
        dict(title="Проверить поступление товара от ЗвукПро", contact="ООО «ЗвукПро»",
             status="in_progress", due=today + timedelta(days=2)),
        dict(title="Подготовить объявление на Авито (наушники)", contact=None,
             status="in_progress", due=None),
        dict(title="Ответить Марии по доставке", contact="Мария Иванова",
             status="completed", due=yesterday),
        dict(title="Созвон с Игорем по партнёрству", contact="Игорь Волков",
             status="new", due=today + timedelta(days=5)),
        dict(title="Инвентаризация кабелей", contact=None,
             status="completed", due=today - timedelta(days=7)),
    ]
    for spec in task_specs:
        task_contact = contacts.get(spec["contact"]) if spec["contact"] else None
        session.add(TaskModel(
            owner_id=DEFAULT_OWNER_ID,
            contact_id=task_contact.id if task_contact else None,
            title=spec["title"],
            status=spec["status"],
            due_date=spec["due"],
            created_at=today - timedelta(days=3),
        ))

    # --- События календаря ---
    event_specs: list[dict[str, Any]] = [
        dict(title="Встреча с клиентом", date=today + timedelta(days=1), time="14:00"),
        dict(title="Отгрузка заказа ORD-1004", date=today + timedelta(days=2), time="10:30"),
        dict(title="Выставка Prolight + Sound", date=today + timedelta(days=14), time=None),
        dict(title="Оплата аренды склада", date=today + timedelta(days=6), time=None),
    ]
    for spec in event_specs:
        session.add(CalendarEventModel(
            owner_id=DEFAULT_OWNER_ID,
            title=spec["title"],
            date=spec["date"],
            time=spec["time"],
        ))

    # --- Сообщения (входящие/исходящие по Telegram, Email и VK) ---
    def msg(contact: str, channel: str, direction: str, text: str, *,
            minutes_ago: int = 0, unread: bool = False, idx: int = 0) -> None:
        session.add(MessageModel(
            owner_id=DEFAULT_OWNER_ID,
            contact_id=contacts[contact].id,
            channel=channel,
            channel_message_id=f"demo-{channel}-{idx}",
            content=text,
            direction=direction,
            status="unread" if unread else "read",
            created_at=now - timedelta(minutes=minutes_ago),
        ))

    msg("Алексей Смирнов", "telegram", "incoming",
        "Здравствуйте! Наушники Sony WH-1000XM5 есть в наличии? Оригинал?", unread=True, idx=1, minutes_ago=25)
    msg("Алексей Смирнов", "telegram", "outgoing",
        "Добрый день! Да, в наличии, оригинал с гарантией. Могу отправить сегодня.", idx=2, minutes_ago=20)
    msg("Алексей Смирнов", "telegram", "incoming",
        "Отлично, оформляйте. Адрес скину в чат.", unread=True, idx=3, minutes_ago=15)
    msg("Мария Иванова", "telegram", "incoming",
        "Добрый вечер, а микрофон Shure подойдёт для подкастов?", unread=True, idx=4, minutes_ago=120)
    msg("Мария Иванова", "email", "incoming",
        "Добрый день! Прошу выставить счёт на студийные мониторы Yamaha HS8 (2 шт).",
        unread=True, idx=5, minutes_ago=180)
    msg("Мария Иванова", "email", "outgoing",
        "Здравствуйте! Счёт отправлен, товар зарезервируем на 3 дня.", idx=6, minutes_ago=160)
    msg("Дмитрий Козлов", "telegram", "incoming",
        "Когда примерно приедет аудиоинтерфейс Focusrite?", unread=True, idx=7, minutes_ago=240)
    msg("Дмитрий Козлов", "telegram", "outgoing",
        "Ожидаем на складе в среду, сразу отправим.", idx=8, minutes_ago=220)
    msg("Елена Соколова", "vk", "incoming",
        "Здравствуйте! Увидела у вас мониторы Yamaha HS8. Есть доставка в Екатеринбург?",
        unread=True, idx=9, minutes_ago=90)
    msg("Елена Соколова", "vk", "outgoing",
        "Добрый день! Да, отправляем СДЭК, 2–3 дня до Екатеринбурга.", idx=10, minutes_ago=80)
    msg("ООО «ЗвукПро»", "email", "incoming",
        "Добрый день! Прайс на микрофоны обновлён, скидка 5% при заказе от 100 тыс.", idx=11, minutes_ago=300)
    msg("ООО «АудиоТрейд»", "email", "incoming",
        "Партия Yamaha HS8 прошла таможню, отгрузка завтра.", idx=12, minutes_ago=400)
    msg("Игорь Волков", "telegram", "incoming",
        "Привет! Есть предложение по совместной закупке. Перезвони?", unread=True, idx=13, minutes_ago=1500)
    msg("Ольга Петрова", "telegram", "incoming",
        "Привет! Не забудь про ужин в субботу :)", unread=True, idx=14, minutes_ago=1500)
    msg("Ольга Петрова", "telegram", "outgoing",
        "Привет! Конечно, помню :)", idx=15, minutes_ago=1490)
    msg("Сергей Орлов", "telegram", "incoming",
        "Советую глянуть новый интерфейс Universal Audio — зашёл бы в наш ассортимент.", idx=16, minutes_ago=1600)

    await session.flush()


async def activate_demo() -> dict[str, Any]:
    """Создаёт (или пересоздаёт) демо-пользователя и делает его активным."""
    ensure_user_data_dir(DEMO_LOGIN)
    await init_db(DEMO_LOGIN, clear_first=True)

    session_maker = get_async_session_maker(DEMO_LOGIN)
    async with session_maker() as session:
        user_repo = UserRepository(session)
        user = await user_repo.get_by_id(DEFAULT_OWNER_ID)
        if user is not None and user.username != DEMO_LOGIN:
            user.username = DEMO_LOGIN
            await session.flush()

        await seed_demo_data(session)

        settings_service = SettingsService(session, owner_id=DEFAULT_OWNER_ID)
        await settings_service.set("onboarded", True)
        await session.commit()

    set_active_login(DEMO_LOGIN)
    await _restart_poll_service(session_maker)

    return {"onboarded": True, "login": DEMO_LOGIN}
