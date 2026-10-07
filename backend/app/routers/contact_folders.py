from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_session
from ..deps import get_current_user
from ..models import UserModel
from ..schemas.contact_folder import (
    ContactFolderCreate,
    ContactFolderResponse,
    ContactFolderUpdate,
    FolderReorderRequest,
)
from ..services.folder_service import FolderService

router = APIRouter()


@router.get("/", response_model=List[ContactFolderResponse])
async def get_folders(
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> list[ContactFolderResponse]:
    service = FolderService(session, owner_id=int(current_user.id))
    return await service.get_all()


@router.post("/reorder", response_model=List[ContactFolderResponse])
async def reorder_folders(
    data: FolderReorderRequest,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> list[ContactFolderResponse]:
    service = FolderService(session, owner_id=int(current_user.id))
    return await service.reorder(data.ids)


@router.post("/", response_model=ContactFolderResponse, status_code=201)
async def create_folder(
    data: ContactFolderCreate,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> ContactFolderResponse:
    service = FolderService(session, owner_id=int(current_user.id))
    return await service.create(data)


@router.patch("/{folder_id}", response_model=ContactFolderResponse)
async def update_folder(
    folder_id: int,
    data: ContactFolderUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> ContactFolderResponse:
    service = FolderService(session, owner_id=int(current_user.id))
    folder = await service.update(folder_id, data)
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")
    return folder


@router.delete("/{folder_id}", status_code=204)
async def delete_folder(
    folder_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> None:
    service = FolderService(session, owner_id=int(current_user.id))
    try:
        deleted = await service.delete(folder_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not deleted:
        raise HTTPException(status_code=404, detail="Folder not found")
