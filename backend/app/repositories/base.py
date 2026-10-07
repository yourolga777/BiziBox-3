from datetime import datetime, timezone
from typing import Any, Generic, List, Optional, Type, TypeVar

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

T = TypeVar("T")
S = TypeVar("S")


class BaseRepository(Generic[T]):
    def __init__(self, model: Type[T], session: AsyncSession, owner_id: Optional[int] = None):
        self.model = model
        self.session = session
        self.owner_id = owner_id

    def _owner_clause(self) -> Any:
        if self.owner_id is not None and hasattr(self.model, "owner_id"):
            return self.model.owner_id == self.owner_id  # type: ignore[attr-defined]
        return None

    def _scoped(self, stmt: S) -> S:
        clause = self._owner_clause()
        if clause is not None:
            stmt = stmt.where(clause)  # type: ignore[attr-defined]
        return stmt

    async def create(self, **kwargs: Any) -> T:
        if self.owner_id is not None and hasattr(self.model, "owner_id"):
            kwargs["owner_id"] = self.owner_id
        instance = self.model(**kwargs)
        self.session.add(instance)
        await self.session.flush()
        return instance

    async def get_by_id(self, id: int) -> Optional[T]:
        result = await self.session.execute(
            self._scoped(select(self.model).where(self.model.id == id))  # type: ignore[attr-defined]
        )
        return result.scalar_one_or_none()

    async def get_all(self, skip: int = 0, limit: int = 100) -> List[T]:
        result = await self.session.execute(
            self._scoped(select(self.model).offset(skip).limit(limit))
        )
        return list(result.scalars().all())

    async def update(self, id: int, **kwargs: Any) -> Optional[T]:
        kwargs.pop("owner_id", None)
        if hasattr(self.model, "updated_at"):
            kwargs.setdefault("updated_at", datetime.now(timezone.utc))
        await self.session.execute(
            self._scoped(update(self.model).where(self.model.id == id).values(**kwargs))  # type: ignore[attr-defined]
        )
        await self.session.flush()
        return await self.get_by_id(id)

    async def delete(self, id: int) -> bool:
        result = await self.session.execute(
            self._scoped(delete(self.model).where(self.model.id == id))  # type: ignore[attr-defined]
        )
        await self.session.flush()
        return result.rowcount > 0

    async def soft_delete(self, id: int) -> bool:
        result = await self.session.execute(
            self._scoped(update(self.model).where(self.model.id == id).values(  # type: ignore[attr-defined]
                deleted_at=datetime.now(timezone.utc)
            ))
        )
        await self.session.flush()
        return result.rowcount > 0

    async def restore(self, id: int) -> Optional[T]:
        await self.session.execute(
            self._scoped(update(self.model).where(self.model.id == id).values(  # type: ignore[attr-defined]
                deleted_at=None
            ))
        )
        await self.session.flush()
        return await self.get_by_id(id)
