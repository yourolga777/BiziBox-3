from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_session
from ..deps import get_current_user
from ..models import UserModel
from ..schemas.task import (
    TaskCommentCreate,
    TaskCommentResponse,
    TaskCreate,
    TaskDetailResponse,
    TaskResponse,
    TaskUpdate,
)
from ..services.task_service import TaskService

router = APIRouter()


@router.get("/", response_model=List[TaskResponse])
async def get_tasks(
    status: Optional[str] = Query(None),
    contact_id: Optional[int] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> list[TaskResponse]:
    service = TaskService(session, owner_id=int(current_user.id))
    return await service.get_all(
        status=status, contact_id=contact_id, skip=skip, limit=limit
    )


@router.get("/archive", response_model=List[TaskResponse])
async def get_archived_tasks(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> list[TaskResponse]:
    service = TaskService(session, owner_id=int(current_user.id))
    return await service.get_deleted(skip=skip, limit=limit)


@router.get("/{task_id}", response_model=TaskDetailResponse)
async def get_task(
    task_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> TaskDetailResponse:
    service = TaskService(session, owner_id=int(current_user.id))
    task = await service.get_detail(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.get("/{task_id}/comments", response_model=List[TaskCommentResponse])
async def get_task_comments(
    task_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> list[TaskCommentResponse]:
    service = TaskService(session, owner_id=int(current_user.id))
    task = await service.get_detail(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task.comments


@router.post("/{task_id}/comments", response_model=TaskCommentResponse, status_code=201)
async def create_task_comment(
    task_id: int,
    data: TaskCommentCreate,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> TaskCommentResponse:
    service = TaskService(session, owner_id=int(current_user.id))
    comment = await service.add_comment(task_id, data)
    if not comment:
        raise HTTPException(status_code=404, detail="Task not found")
    return comment


@router.delete("/{task_id}/comments/{comment_id}", status_code=204)
async def delete_task_comment(
    task_id: int,
    comment_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> None:
    service = TaskService(session, owner_id=int(current_user.id))
    deleted = await service.delete_comment(comment_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Comment not found")


@router.post("/", response_model=TaskResponse, status_code=201)
async def create_task(
    data: TaskCreate,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> TaskResponse:
    service = TaskService(session, owner_id=int(current_user.id))
    return await service.create(data)


@router.patch("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: int,
    data: TaskUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> TaskResponse:
    service = TaskService(session, owner_id=int(current_user.id))
    try:
        task = await service.update(task_id, data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.delete("/{task_id}", status_code=204)
async def delete_task(
    task_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> None:
    service = TaskService(session, owner_id=int(current_user.id))
    deleted = await service.delete(task_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Task not found")


@router.post("/{task_id}/restore", response_model=TaskResponse)
async def restore_task(
    task_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> TaskResponse:
    service = TaskService(session, owner_id=int(current_user.id))
    task = await service.restore(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Archived task not found")
    return task


@router.post("/bulk-delete")
async def bulk_delete_tasks(
    ids: List[int],
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> dict[str, int]:
    service = TaskService(session, owner_id=int(current_user.id))
    count = await service.bulk_delete(ids)
    return {"deleted": count}


@router.post("/bulk-restore")
async def bulk_restore_tasks(
    ids: List[int],
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> dict[str, int]:
    service = TaskService(session, owner_id=int(current_user.id))
    count = await service.bulk_restore(ids)
    return {"restored": count}
