import logging
from typing import Optional

from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from .config import DEFAULT_OWNER_ID
from .database import get_session
from .models.user import UserModel
from .repositories.user import UserRepository
from .services.poll_service import PollService
from .user_context import get_active_login

logger = logging.getLogger(__name__)

_poll_service: Optional[PollService] = None


def set_poll_service(service: Optional[PollService]) -> None:
    global _poll_service
    _poll_service = service
    logger.debug("poll_service set to %s", service)


def get_poll_service() -> Optional[PollService]:
    return _poll_service


async def get_current_user(
    session: AsyncSession = Depends(get_session),
) -> UserModel:
    # РЕЛИЗ 1 interim: один активный логин на экземпляр приложения.
    # Данные изолированы по папкам users/<login>/; owner_id = id юзера в его БД.
    login = get_active_login()
    if not login:
        raise HTTPException(status_code=401, detail="No active user")

    user_repo = UserRepository(session)
    user = await user_repo.get_by_username(login)
    if user is None:
        user = await user_repo.get_by_id(DEFAULT_OWNER_ID)
        if user is not None:
            user.username = login
            await session.flush()
        else:
            user = await user_repo.create(
                id=DEFAULT_OWNER_ID,
                username=login,
                password_hash="",
                is_active=True,
            )
            await session.flush()
    return user
