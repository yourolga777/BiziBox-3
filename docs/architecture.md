# Архитектура BiziBox

**BiziBox** — монолитное локальное PWA-приложение «сообщения и дела в одном окне». Backend (FastAPI) отдаёт REST API и раздаёт собранный фронтенд; фронтенд (React) — SPA/PWA.

## Стек

- **Backend:** Python 3.13, FastAPI, SQLAlchemy 2.0 (async), SQLite, Alembic
- **Frontend:** React 19, TypeScript 5.6+, Vite 6, Tailwind CSS 4, PWA (vite-plugin-pwa)
- **Хранение:** SQLite в `backend/data/bizibox.db` (WAL), секреты шифруются Fernet (ключ `backend/data/.encryption_key`)

## Структура папок

```
backend/
  app/
    main.py           # lifespan, роутеры, CORS, статика фронтенда
    config.py         # настройки (Settings ← backend/.env)
    database.py       # async engine, init_db, Alembic-миграции
    deps.py           # get_current_user, get_poll_service
    models/           # SQLAlchemy-модели
    repositories/     # BaseRepository + конкретные репозитории
    services/         # бизнес-логика (message/contact/task/calendar/…)
    schemas/          # Pydantic-схемы
    routers/          # FastAPI-роутеры
    channels/         # адаптеры каналов (Telegram, Email)
    utils/            # crypto, fts, autolink, logger, search
  migrations/         # Alembic-миграции (одна initial)
  tests/              # pytest
frontend/
  src/
    api/              # API-клиент (client.ts + модули)
    components/       # React-компоненты (inbox/contacts/tasks/calendar/…)
    pages/            # страницы (Inbox, Tasks, Contacts, Calendar, Dashboard…)
    hooks/            # react-query-хуки
    types/            # TypeScript-типы
    utils/            # утилиты
    notifications/    # push-уведомления
    offline/          # IndexedDB, очередь, синхронизация
docs/                 # документация
scripts/              # вспомогательные скрипты (graph, seed)
installer/            # Inno Setup
```

## Ключевые архитектурные решения

1. **Монолит** — backend и фронтенд в одном репозитории; фронтенд собирается в `dist/` и раздаётся FastAPI.
2. **Локальные данные** — SQLite (WAL), Fernet-шифрование чувствительных данных; без облака.
3. **Async** — `async/await` для всех I/O (SQLAlchemy 2.0 async, aiosqlite).
4. **Адаптеры каналов** — `BaseChannelAdapter` (`channels/base.py`) → `telegram.py`, `email.py`. Новый канал = новый адаптер.
5. **Репозитории** — `BaseRepository` (owner-scope, soft-delete) + конкретные репозитории.
6. **Фоновые циклы** — asyncio-циклы: outbox worker, reminder scheduler (60 с), спам-очистка при shutdown.
7. **Поиск** — FTS5 (`messages_fts`) + `scripts/graph` для карты зависимостей.

## Модель данных (основные сущности)

- `users` — владельцы (single-user по умолчанию, `DEFAULT_OWNER_ID`).
- `contacts` — тип (`personal/service/spam/other`), папка, день рождения, важность, спам.
- `contact_folders` — папки (системные `is_default` и пользовательские).
- `messages` — канал, направление, статус, snooze, спам (через контакт), FTS.
- `tasks` — 3 статуса (`new/in_progress/completed`), дедлайн, напоминание, повторение.
- `calendar_events` — отдельные события календаря.
- `task_comments`, `contact_fields`, `contact_notes`, `contact_tags`, `message_attachments`, `outbox_messages`, `settings`.

## Календарь

`GET /api/calendar/events` возвращает merged-список: задачи (`type=task`), события (`type=event`), дни рождения (`type=birthday`, `id=-contact.id`).

## Удалённые модули (из форка)

Из исходной кодовой базы удалены:

- **Заказы** — `order.py`, `order_service.py`, `order_extractor.py`, `routers/orders.py`, `pages/Orders.tsx`, `OrderDetail.tsx`.
- **Каталог** — `product.py`, `supplier.py`, `product_service.py`, `routers/products.py`, `routers/suppliers.py`, `pages/Products.tsx`.
- **Категории** — `category.py`, `categories.py`, `CategoryPicker.tsx`.
- **AI-модуль** — `app/ai/`, `routers/ai.py`, `AiSettings` (реализация), AI-поля сообщений.
- **Авто-правила** — `message_rule.py`, `message_rule_service.py`.

AI-ассистент заменён заглушкой-страницей «будет позже».

## API (основные группы)

- `/api/messages` — inbox, диалоги, спам, snooze, bulk-действия, поиск.
- `/api/contacts`, `/api/folders`, `/api/tags` — контакты, папки, теги.
- `/api/tasks` — задачи (3 статуса), комментарии.
- `/api/calendar/events` — сводный календарь + CRUD событий.
- `/api/reminders` — напоминания.
- `/api/backup` — экспорт/импорт зашифрованного бэкапа.
- `/api/channels`, `/api/dashboard`, `/api/settings`, `/api/startup`.
