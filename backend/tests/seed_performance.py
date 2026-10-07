"""
Seed script for performance testing.
Generates 1000 contacts, 5000 messages, 200 tasks.
Run: python -m backend.tests.seed_performance
"""

import asyncio
import random
import string
from datetime import datetime, timedelta

from ..app.database import AsyncSessionLocal, init_db  # type: ignore[import-untyped]
from ..app.models import (  # type: ignore[import-untyped]
    ContactModel,
    MessageModel,
    TaskModel,
)
from ..app.repositories.base import BaseRepository  # type: ignore[import-untyped]


def _random_string(length: int = 10) -> str:
    return "".join(random.choices(string.ascii_lowercase, k=length))


async def seed():
    await init_db()
    async with AsyncSessionLocal() as session:
        contacts = []
        for i in range(1000):
            contact = await BaseRepository(ContactModel, session).create(
                name=f"Контакт {i + 1}",
                phone=f"+7{random.randint(900, 999)}{random.randint(1000000, 9999999)}",
                email=f"contact{i + 1}@example.com",
                telegram_id=f"tg{i + 1}" if i < 500 else None,
                telegram_username=f"user{i + 1}" if i < 500 else None,
                notes=f"Заметки контакта {i + 1}" if i % 3 == 0 else None,
            )
            contacts.append(contact)
        print(f"Created {len(contacts)} contacts")

        messages = []
        for i in range(5000):
            contact = random.choice(contacts)
            created_at = datetime.now() - timedelta(
                days=random.randint(0, 30),
                hours=random.randint(0, 23),
                minutes=random.randint(0, 59),
            )
            msg = await BaseRepository(MessageModel, session).create(
                contact_id=contact.id,
                channel=random.choice(["telegram", "email"]),
                channel_message_id=f"ch-{i}" if i % 10 == 0 else None,
                content=f"Тестовое сообщение {i + 1} от {contact.name}. "
                        f"{' '.join(_random_string(5) for _ in range(random.randint(1, 10)))}",
                direction=random.choice(["incoming", "outgoing"]),
                status=random.choice(["unread", "read", "archived"]),
                created_at=created_at,
                updated_at=created_at,
            )
            messages.append(msg)
        print(f"Created {len(messages)} messages")

        tasks = []
        for i in range(200):
            contact = random.choice(contacts)
            task = await BaseRepository(TaskModel, session).create(
                contact_id=contact.id,
                title=f"Задача {i + 1}",
                description=f"Описание задачи {i + 1}. Связана с {contact.name}",
                status=random.choice(["new", "in_progress", "completed"]),
                due_date=datetime.now() + timedelta(days=random.randint(1, 30)),
            )
            tasks.append(task)
        print(f"Created {len(tasks)} tasks")

        await session.commit()
    print("Done! Database seeded with performance test data.")


if __name__ == "__main__":
    asyncio.run(seed())
