from typing import Any, List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_session
from ..deps import get_current_user
from ..models import UserModel
from ..schemas.contact import (
    BulkIdsRequest,
    BulkMergeRequest,
    BulkUpdateRequest,
    ContactCreate,
    ContactResponse,
    ContactTypeTemplateCreate,
    ContactTypeTemplateResponse,
    ContactTypeTemplateUpdate,
    ContactUpdate,
    DuplicateGroup,
    MergeContactsRequest,
    NoteCreate,
    NoteResponse,
    TimelineEvent,
)
from ..services.contact_service import ContactService

router = APIRouter()


@router.get("/", response_model=List[ContactResponse])
async def get_contacts(
    search: Optional[str] = Query(None),
    channel: Optional[str] = Query(None),
    subsection: Optional[str] = Query(None),
    life_sphere: Optional[str] = Query(None),
    contact_type_ids: Optional[List[int]] = Query(None),
    folder_id: Optional[int] = Query(None),
    is_favorite: Optional[bool] = Query(None),
    unclassified: bool = Query(False),
    sort_by: str = Query("name"),
    sort_order: str = Query("asc"),
    skip: int = Query(0, ge=0),
    limit: Optional[int] = Query(None, ge=1),
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> list[ContactResponse]:
    service = ContactService(session, owner_id=int(current_user.id))
    return await service.get_all(
        search=search,
        channel=channel,
        subsection=subsection,
        life_sphere=life_sphere,
        contact_type_ids=contact_type_ids,
        folder_id=folder_id,
        is_favorite=is_favorite,
        unclassified=unclassified,
        sort_by=sort_by,
        sort_order=sort_order,
        skip=skip,
        limit=limit,
    )


@router.get("/export", response_class=PlainTextResponse)
async def export_contacts(
    ids: Optional[str] = Query(None),
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> str:
    service = ContactService(session, owner_id=int(current_user.id))
    id_list = [int(i) for i in ids.split(",")] if ids else None
    csv_data = await service.export_csv(ids=id_list)
    return csv_data


@router.get("/archive", response_model=List[ContactResponse])
async def get_archived_contacts(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=1000),
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> list[ContactResponse]:
    service = ContactService(session, owner_id=int(current_user.id))
    return await service.get_deleted(skip=skip, limit=limit)


@router.patch("/bulk-update")
async def bulk_update_contacts(
    data: BulkUpdateRequest,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> dict[str, Any]:
    service = ContactService(session, owner_id=int(current_user.id))
    fields: dict[str, object] = {}
    if data.is_known is not None:
        fields["is_known"] = data.is_known
    if data.folder_id is not None:
        fields["folder_id"] = data.folder_id
    if data.is_favorite is not None:
        fields["is_favorite"] = data.is_favorite
    if data.life_sphere is not None:
        fields["life_sphere"] = data.life_sphere
    if data.contact_type_ids is not None:
        for cid in data.ids:
            await service.contact_repo.set_contact_types(cid, data.contact_type_ids)
        return {"updated": len(data.ids)}
    count = await service.bulk_update(data.ids, **fields)
    return {"updated": count}


@router.get("/contact-types", response_model=List[ContactTypeTemplateResponse])
async def get_contact_types(
    sphere: Optional[str] = Query(None),
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> list[ContactTypeTemplateResponse]:
    service = ContactService(session, owner_id=int(current_user.id))
    return await service.get_type_templates(sphere=sphere)


@router.post("/contact-types", response_model=ContactTypeTemplateResponse, status_code=201)
async def create_contact_type(
    data: ContactTypeTemplateCreate,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> ContactTypeTemplateResponse:
    service = ContactService(session, owner_id=int(current_user.id))
    try:
        return await service.create_type_template(data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/contact-types/{template_id}", response_model=ContactTypeTemplateResponse)
async def update_contact_type(
    template_id: int,
    data: ContactTypeTemplateUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> ContactTypeTemplateResponse:
    service = ContactService(session, owner_id=int(current_user.id))
    template = await service.update_type_template(template_id, data)
    if not template:
        raise HTTPException(status_code=404, detail="Type not found")
    return template


@router.delete("/contact-types/{template_id}", status_code=204)
async def delete_contact_type(
    template_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> None:
    service = ContactService(session, owner_id=int(current_user.id))
    try:
        deleted = await service.delete_type_template(template_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not deleted:
        raise HTTPException(status_code=404, detail="Type not found")


@router.get("/duplicates", response_model=List[DuplicateGroup])
async def get_duplicates(
    contact_id: Optional[int] = Query(None),
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> list[dict[str, Any]]:
    service = ContactService(session, owner_id=int(current_user.id))
    return await service.get_duplicates(contact_id=contact_id)


# --- Параметризованные маршруты ниже литеральных ---

@router.get("/{contact_id}", response_model=ContactResponse)
async def get_contact(
    contact_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> ContactResponse:
    service = ContactService(session, owner_id=int(current_user.id))
    contact = await service.get_by_id(contact_id)
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    return contact


@router.post("/", response_model=ContactResponse, status_code=201)
async def create_contact(
    data: ContactCreate,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> ContactResponse:
    service = ContactService(session, owner_id=int(current_user.id))
    try:
        return await service.create(data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/{contact_id}", response_model=ContactResponse)
async def update_contact(
    contact_id: int,
    data: ContactUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> ContactResponse:
    service = ContactService(session, owner_id=int(current_user.id))
    try:
        contact = await service.update(contact_id, data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    return contact


@router.patch("/{contact_id}/append", response_model=ContactResponse)
async def append_contact_fields(
    contact_id: int,
    data: ContactUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> ContactResponse:
    service = ContactService(session, owner_id=int(current_user.id))
    contact = await service.append_fields(contact_id, data)
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    return contact


@router.delete("/{contact_id}", status_code=204)
async def delete_contact(
    contact_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> None:
    service = ContactService(session, owner_id=int(current_user.id))
    deleted = await service.delete(contact_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Contact not found")


@router.delete("/{contact_id}/permanent", status_code=204)
async def permanent_delete_contact(
    contact_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> None:
    service = ContactService(session, owner_id=int(current_user.id))
    deleted = await service.permanent_delete(contact_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Contact not found")


@router.post("/{contact_id}/restore", response_model=ContactResponse)
async def restore_contact(
    contact_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> ContactResponse:
    service = ContactService(session, owner_id=int(current_user.id))
    contact = await service.restore(contact_id)
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    return contact


@router.post("/{contact_id}/set-spam", response_model=ContactResponse)
async def set_spam_contact(
    contact_id: int,
    spam: bool = Query(...),
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> ContactResponse:
    service = ContactService(session, owner_id=int(current_user.id))
    contact = await service.set_spam(contact_id, spam)
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    return contact


@router.post("/{contact_id}/block", response_model=ContactResponse)
async def block_contact(
    contact_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> ContactResponse:
    service = ContactService(session, owner_id=int(current_user.id))
    contact = await service.update(contact_id, ContactUpdate(is_blocked=True))
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    return contact


@router.post("/{contact_id}/unblock", response_model=ContactResponse)
async def unblock_contact(
    contact_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> ContactResponse:
    service = ContactService(session, owner_id=int(current_user.id))
    contact = await service.update(contact_id, ContactUpdate(is_blocked=False))
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    return contact


@router.post("/merge", response_model=ContactResponse)
async def merge_contacts(
    data: MergeContactsRequest,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> ContactResponse:
    service = ContactService(session, owner_id=int(current_user.id))
    try:
        contact = await service.merge(data.primary_id, data.secondary_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not contact:
        raise HTTPException(status_code=400, detail="Failed to merge contacts")
    return contact


@router.post("/bulk-merge", response_model=ContactResponse)
async def bulk_merge_contacts(
    data: BulkMergeRequest,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> ContactResponse:
    service = ContactService(session, owner_id=int(current_user.id))
    contact = await service.bulk_merge(data.primary_id, data.secondary_ids)
    if not contact:
        raise HTTPException(status_code=400, detail="Failed to merge contacts")
    return contact


@router.post("/bulk-delete")
async def bulk_delete_contacts(
    data: BulkIdsRequest,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> dict[str, Any]:
    service = ContactService(session, owner_id=int(current_user.id))
    count = await service.bulk_delete(data.ids)
    return {"deleted": count}


@router.post("/bulk-restore")
async def bulk_restore_contacts(
    data: BulkIdsRequest,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> dict[str, Any]:
    service = ContactService(session, owner_id=int(current_user.id))
    count = await service.bulk_restore(data.ids)
    return {"restored": count}


@router.get("/{contact_id}/timeline", response_model=List[TimelineEvent])
async def get_timeline(
    contact_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> list[TimelineEvent]:
    service = ContactService(session, owner_id=int(current_user.id))
    return await service.get_timeline(contact_id)


@router.get("/{contact_id}/notes", response_model=List[NoteResponse])
async def get_notes(
    contact_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> list[NoteResponse]:
    service = ContactService(session, owner_id=int(current_user.id))
    return await service.get_notes(contact_id)


@router.post("/{contact_id}/notes", response_model=NoteResponse, status_code=201)
async def create_note(
    contact_id: int,
    data: NoteCreate,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> NoteResponse:
    service = ContactService(session, owner_id=int(current_user.id))
    note = await service.create_note(contact_id, data)
    if not note:
        raise HTTPException(status_code=404, detail="Contact not found")
    return note


@router.delete("/notes/{note_id}", status_code=204)
async def delete_note(
    note_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> None:
    service = ContactService(session, owner_id=int(current_user.id))
    deleted = await service.delete_note(note_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Note not found")


@router.post("/import")
async def import_contacts(
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> dict[str, int]:
    service = ContactService(session, owner_id=int(current_user.id))
    content_bytes = await file.read()
    content = content_bytes.decode("utf-8-sig")
    return await service.import_csv(content)
