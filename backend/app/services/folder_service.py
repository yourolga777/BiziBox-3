from typing import List, Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import ContactFolderModel, ContactModel
from ..repositories.contact_folder import ContactFolderRepository
from ..schemas.contact_folder import (
    ContactFolderCreate,
    ContactFolderResponse,
    ContactFolderUpdate,
)


class FolderService:
    def __init__(self, session: AsyncSession, owner_id: Optional[int] = None):
        self.session = session
        self.owner_id = owner_id
        self.folder_repo = ContactFolderRepository(session, owner_id)

    async def get_all(self) -> List[ContactFolderResponse]:
        folders = await self.folder_repo.get_all(limit=None)
        return [ContactFolderResponse.model_validate(f) for f in folders]

    async def reorder(self, ids: List[int]) -> List[ContactFolderResponse]:
        """Пересчитывает sort_order по переданному порядку (вся строка целиком)."""
        folders = await self.folder_repo.get_all(limit=None)
        by_id = {int(f.id): f for f in folders}
        seen: set[int] = set()
        ordered: List[ContactFolderModel] = []
        for raw_id in ids:
            folder = by_id.get(int(raw_id))
            if folder is None or int(raw_id) in seen:
                continue
            seen.add(int(raw_id))
            ordered.append(folder)
        rest = [f for f in folders if int(f.id) not in seen]
        for index, folder in enumerate(ordered + rest):
            if folder.sort_order != index:
                await self.folder_repo.update(folder.id, sort_order=index)
        return await self.get_all()

    async def get_by_id(self, folder_id: int) -> Optional[ContactFolderResponse]:
        folder = await self.folder_repo.get_by_id(folder_id)
        if folder is None:
            return None
        return ContactFolderResponse.model_validate(folder)

    async def create(self, data: ContactFolderCreate) -> ContactFolderResponse:
        folder = await self.folder_repo.create(**data.model_dump())
        return ContactFolderResponse.model_validate(folder)

    async def update(
        self, folder_id: int, data: ContactFolderUpdate
    ) -> Optional[ContactFolderResponse]:
        folder = await self.folder_repo.update(
            folder_id, **data.model_dump(exclude_unset=True)
        )
        if folder is None:
            return None
        return ContactFolderResponse.model_validate(folder)

    async def delete(self, folder_id: int) -> bool:
        folder = await self.folder_repo.get_by_id(folder_id)
        if folder is None:
            return False
        if folder.is_default:
            raise ValueError("Cannot delete default folders")
        children = (
            await self.session.execute(
                select(ContactFolderModel).where(
                    ContactFolderModel.parent_id == folder_id
                )
            )
        ).scalars().all()
        for child in children:
            await self.folder_repo.update(child.id, parent_id=folder.parent_id)
        await self.session.execute(
            update(ContactModel)
            .where(ContactModel.folder_id == folder_id)
            .values(folder_id=None)
        )
        await self.session.flush()
        return await self.folder_repo.delete(folder_id)
