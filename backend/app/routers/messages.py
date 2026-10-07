import asyncio
import io
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any, List, Literal, Optional
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_session
from ..deps import get_current_user, get_poll_service
from ..models import ContactFolderModel, ContactModel, UserModel
from ..repositories.attachment import AttachmentRepository
from ..repositories.contact import ContactRepository
from ..repositories.contact_folder import ContactFolderRepository
from ..repositories.message import MessageRepository
from ..schemas.channel import ChannelSendMessage, ChannelSendNew, ChannelSendReply
from ..schemas.message import (
    BulkActionRequest,
    BulkIdsRequest,
    BulkStatusUpdate,
    LoadPreviousRequest,
    MessageCreate,
    MessageResponse,
    MessageUpdate,
    SnoozeRequest,
    ThreadResponse,
)
from ..services.channel_message_service import ChannelMessageService
from ..services.message_service import MessageService
from ..user_context import get_active_login, get_user_data_dir
from .dashboard import invalidate_metrics_cache

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/", response_model=List[MessageResponse])
async def get_messages(
    contact_id: Optional[int] = Query(None),
    channel: Optional[str] = Query(None),
    life_sphere: Optional[str] = Query(None),
    folder_id: Optional[int] = Query(None, ge=1),
    scope: Optional[Literal["all", "new"]] = Query(None),
    unread: bool = Query(False),
    flagged: bool = Query(False),
    skip: int = Query(0, ge=0),
    limit: int = Query(1000, ge=1, le=1000),
    include_deleted: bool = Query(False),
    min_id: Optional[int] = Query(None, ge=1),
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> list[MessageResponse]:
    service = MessageService(session, owner_id=int(current_user.id))

    exclude_spam = folder_id is None and life_sphere is None

    if folder_id is not None:
        folder_repo = ContactFolderRepository(
            session, owner_id=int(current_user.id)
        )
        folder = await folder_repo.get_by_id(folder_id)
        if not folder:
            raise HTTPException(status_code=404, detail="Folder not found")

    if scope == "new":
        unread = True

    return await service.get_all(
        contact_id=contact_id,
        channel=channel,
        life_sphere=life_sphere,
        folder_id=folder_id,
        unread=unread,
        flagged=flagged,
        skip=skip,
        limit=limit,
        include_deleted=include_deleted,
        min_id=min_id,
        exclude_spam=exclude_spam,
    )


@router.get("/inbox", response_model=List[MessageResponse])
async def get_inbox_messages(
    skip: int = Query(0, ge=0),
    limit: int = Query(200, ge=1, le=1000),
    include_deleted: bool = Query(False),
    min_id: Optional[int] = Query(None, ge=1),
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> list[MessageResponse]:
    service = MessageService(session, owner_id=int(current_user.id))
    return await service.get_by_scope(
        scope="inbox",
        skip=skip,
        limit=limit,
        include_deleted=include_deleted,
        min_id=min_id,
    )


@router.get("/threads", response_model=List[ThreadResponse])
async def get_threads(
    skip: int = Query(0, ge=0),
    limit: Optional[int] = Query(None, ge=1),
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> list[ThreadResponse]:
    service = MessageService(session, owner_id=int(current_user.id))
    return await service.get_threads(skip=skip, limit=limit)


@router.get("/spam", response_model=List[MessageResponse])
async def get_spam_messages(
    skip: int = Query(0, ge=0),
    limit: int = Query(200, ge=1, le=1000),
    include_deleted: bool = Query(False),
    min_id: Optional[int] = Query(None, ge=1),
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> list[MessageResponse]:
    service = MessageService(session, owner_id=int(current_user.id))
    return await service.get_spam(
        skip=skip,
        limit=limit,
        include_deleted=include_deleted,
        min_id=min_id,
    )


@router.get("/spam/count", response_model=dict[str, Any])
async def get_spam_count(
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> dict[str, Any]:
    service = MessageService(session, owner_id=int(current_user.id))
    return {"count": await service.count_unread_spam()}


@router.post("/spam/load", response_model=dict[str, Any])
async def load_spam_messages(
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> dict[str, Any]:
    ps = get_poll_service()
    if not ps:
        return {"loaded": 0, "messages": []}

    spam_contacts = (
        await session.execute(
            select(ContactModel).where(
                ContactModel.life_sphere == "spam",
                ContactModel.deleted_at.is_(None),
                ContactModel.owner_id == int(current_user.id),
            )
        )
    ).scalars().all()

    loaded_messages: list[MessageResponse] = []
    for contact in spam_contacts:
        channel_id = contact.telegram_id
        if not channel_id:
            continue
        adapter = ps.get_channel("telegram")
        if not adapter:
            continue

        raw_messages = await adapter.get_dialog(channel_id, limit=200)
        for msg in raw_messages:
            msg["channel"] = "telegram"
            msg["contact_id"] = channel_id
            msg["contact_name"] = contact.name
            try:
                cms = ChannelMessageService(session, owner_id=int(current_user.id))
                result = await cms.process_incoming(msg, allow_spam=True)
                await session.commit()
                if result is not None:
                    loaded_messages.append(result)
            except Exception:
                await session.rollback()

    return {"loaded": len(loaded_messages), "messages": loaded_messages}


@router.post("/channels/load", response_model=dict[str, Any])
async def load_channel_messages(
    folder_id: Optional[int] = Query(None, ge=1),
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> dict[str, Any]:
    ps = get_poll_service()
    if not ps:
        return {"loaded": 0, "messages": []}

    channel_contacts = await _get_channel_contacts(
        session, int(current_user.id), folder_id
    )

    loaded_messages: list[MessageResponse] = []
    for contact in channel_contacts:
        channel_id = contact.telegram_id
        if not channel_id:
            continue
        adapter = ps.get_channel("telegram")
        if not adapter:
            continue

        raw_messages = await adapter.get_dialog(channel_id, limit=200)
        for msg in raw_messages:
            msg["channel"] = "telegram"
            msg["contact_id"] = channel_id
            msg["contact_name"] = contact.name
            try:
                cms = ChannelMessageService(session, owner_id=int(current_user.id))
                result = await cms.process_incoming(msg, allow_channels=True)
                await session.commit()
                if result is not None:
                    loaded_messages.append(result)
            except Exception:
                await session.rollback()

    return {"loaded": len(loaded_messages), "messages": loaded_messages}


async def _get_channel_contacts(
    session: AsyncSession,
    owner_id: int,
    folder_id: Optional[int] = None,
) -> list[ContactModel]:
    query = select(ContactModel).where(
        ContactModel.life_sphere == "channels",
        ContactModel.deleted_at.is_(None),
        ContactModel.owner_id == owner_id,
    )
    if folder_id is not None:
        folder_ids = await _folder_descendants(session, owner_id, folder_id)
        query = query.where(ContactModel.folder_id.in_(folder_ids))
    result = await session.execute(query)
    return list(result.scalars().all())


async def _folder_descendants(
    session: AsyncSession, owner_id: int, folder_id: int
) -> list[int]:
    rows = (
        await session.execute(
            select(ContactFolderModel.id, ContactFolderModel.parent_id).where(
                ContactFolderModel.owner_id == owner_id
            )
        )
    ).all()
    children: dict[Optional[int], list[int]] = {}
    for fid, pid in rows:
        children.setdefault(pid, []).append(int(fid))
    result: list[int] = []
    stack = [folder_id]
    while stack:
        cur = stack.pop()
        if cur in result:
            continue
        result.append(cur)
        stack.extend(children.get(cur, []))
    return result


@router.get("/archive", response_model=List[MessageResponse])
async def get_archived_messages(
    skip: int = Query(0, ge=0),
    limit: int = Query(200, ge=1, le=1000),
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> list[MessageResponse]:
    service = MessageService(session, owner_id=int(current_user.id))
    return await service.get_all(
        skip=skip,
        limit=limit,
        include_deleted=True,
    )


@router.get("/dialog/{contact_id}", response_model=List[MessageResponse])
async def get_dialog(
    contact_id: int,
    limit: int = Query(200, ge=1, le=1000),
    before_created_at: Optional[datetime] = Query(None),
    before_id: Optional[int] = Query(None, ge=1),
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> list[MessageResponse]:
    service = MessageService(session, owner_id=int(current_user.id))
    return await service.get_dialog(
        contact_id,
        limit=limit,
        before_created_at=before_created_at,
        before_id=before_id,
    )


@router.post("/sync-dialog/{contact_id}")
async def sync_dialog(
    contact_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> dict[str, Any]:
    ps = get_poll_service()
    contact_repo = ContactRepository(session, owner_id=int(current_user.id))
    contact = await contact_repo.get_by_id(contact_id)
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")

    channel_id = contact.telegram_id
    if not channel_id:
        return {"new_messages": 0, "message": "Not a Telegram contact"}

    adapter = ps.get_channel("telegram") if ps else None
    if not adapter:
        return {"new_messages": 0, "message": "Telegram adapter not connected"}

    raw_messages = await adapter.get_dialog(channel_id, limit=200)
    new_count = 0
    for msg in raw_messages:
        msg["channel"] = "telegram"
        msg["contact_id"] = channel_id
        try:
            cms = ChannelMessageService(session, owner_id=int(current_user.id))
            result = await cms.process_incoming(msg)
            await session.commit()
            if result is not None:
                new_count += 1
        except Exception:
            await session.rollback()

    return {"new_messages": new_count}


@router.post("/load-previous", response_model=list[MessageResponse])
async def load_previous_messages(
    data: LoadPreviousRequest,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> list[MessageResponse]:
    ps = get_poll_service()
    if not ps:
        raise HTTPException(status_code=503, detail="Каналы не подключены")

    contact_repo = ContactRepository(session, owner_id=int(current_user.id))
    contact = await contact_repo.get_by_id(data.contact_id)
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")

    channel_id = contact.telegram_id
    if not channel_id:
        raise HTTPException(
            status_code=400,
            detail="Контакт не привязан к Telegram",
        )

    adapter = ps.get_channel("telegram")
    if not adapter:
        raise HTTPException(
            status_code=503,
            detail="Telegram не подключён",
        )

    message_repo = MessageRepository(session, owner_id=int(current_user.id))
    oldest = await message_repo.get_oldest_by_contact(data.contact_id)
    offset_id = int(oldest.channel_message_id) if oldest and oldest.channel_message_id else 0

    raw_messages = await adapter.fetch_older_messages(
        chat_id=channel_id,
        offset_id=offset_id,
        limit=data.count,
    )

    saved: list[MessageResponse] = []
    for msg in raw_messages:
        msg["channel"] = "telegram"
        msg["contact_id"] = channel_id
        msg["contact_name"] = contact.name
        try:
            cms = ChannelMessageService(session, owner_id=int(current_user.id))
            result = await cms.process_incoming(msg)
            await session.commit()
            if result is not None:
                saved.append(result)
        except Exception:
            await session.rollback()

    return saved


@router.get("/search", response_model=List[MessageResponse])
async def search_messages(
    q: str = Query("", max_length=200),
    limit: int = Query(200, ge=1, le=1000),
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> list[MessageResponse]:
    if not q.strip():
        return []
    service = MessageService(session, owner_id=int(current_user.id))
    try:
        return await service.search(q, limit=limit)
    except Exception:
        logger.exception("Message search failed for q=%r", q)
        return []


@router.get("/{message_id}", response_model=MessageResponse)
async def get_message(
    message_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> MessageResponse:
    service = MessageService(session, owner_id=int(current_user.id))
    message = await service.get_by_id(message_id)
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    return message


@router.get("/{message_id}/attachments/{attachment_id}/download")
async def download_attachment(
    message_id: int,
    attachment_id: int,
    request: Request,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> Response:
    message_repo = MessageRepository(session, owner_id=int(current_user.id))
    message = await message_repo.get_by_id(message_id)
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")

    att_repo = AttachmentRepository(session)
    attachment = await att_repo.get_for_message(attachment_id, message_id)
    if not attachment:
        raise HTTPException(status_code=404, detail="Attachment not found")

    ps = get_poll_service()
    adapter = ps.get_channel(message.channel) if ps else None

    data: io.BytesIO | None = None
    if adapter is not None:
        try:
            data = await adapter.download_file(attachment.file_path)
        except Exception as e:
            logger.warning("Attachment download via adapter failed: %s", e)

    # Локальный фоллбэк: файл уже сохранён на диске (email-вложения) — отдаём без
    # живого адаптера, чтобы предпросмотр работал даже когда канал не подключён.
    if data is None and attachment.file_path:
        login = get_active_login()
        if login:
            local_path = Path(get_user_data_dir(login)) / attachment.file_path
            if local_path.is_file():
                data = await asyncio.to_thread(
                    lambda: io.BytesIO(local_path.read_bytes())
                )

    if data is None:
        raise HTTPException(status_code=502, detail="Не удалось скачать файл")

    filename = attachment.file_name or f"attachment_{attachment.id}"
    media_type = attachment.mime_type or "application/octet-stream"
    safe_name = re.sub(r'[\r\n"]', "_", str(filename))
    ascii_name = safe_name.encode("ascii", "ignore").decode() or "attachment"
    encoded_name = quote(safe_name)
    inline = (
        media_type.startswith("image/")
        or media_type.startswith("audio/")
        or media_type.startswith("video/")
        or media_type == "application/pdf"
    )
    disposition = (
        f'{"inline" if inline else "attachment"}; filename="{ascii_name}"; '
        f"filename*=UTF-8''{encoded_name}"
    )

    data.seek(0, io.SEEK_END)
    total_size = data.tell()
    data.seek(0)

    if total_size <= 0:
        return StreamingResponse(
            iter([b""]),
            media_type=media_type,
            headers={"Content-Disposition": disposition},
        )

    start = 0
    end = total_size - 1
    status_code = 200
    headers: dict[str, str] = {
        "Content-Disposition": disposition,
        "Accept-Ranges": "bytes",
        "Content-Length": str(total_size),
    }

    range_header = request.headers.get("range")
    if range_header:
        match = re.fullmatch(r"bytes=(\d*)-(\d*)", range_header.strip())
        valid = match is not None
        if match:
            s_raw, e_raw = match.groups()
            if s_raw == "" and e_raw == "":
                valid = False
            elif s_raw == "":
                suffix = int(e_raw)
                if suffix <= 0:
                    valid = False
                else:
                    start = max(0, total_size - suffix)
                    end = total_size - 1
            else:
                start = int(s_raw)
                end = int(e_raw) if e_raw != "" else total_size - 1
                if start > end or start >= total_size:
                    valid = False
                else:
                    end = min(end, total_size - 1)
        if not valid:
            return Response(
                status_code=416,
                headers={"Content-Range": f"bytes */{total_size}"},
            )
        status_code = 206
        headers["Content-Range"] = f"bytes {start}-{end}/{total_size}"
        headers["Content-Length"] = str(end - start + 1)

    data.seek(start)
    chunk = data.read(end - start + 1)

    return StreamingResponse(
        iter([chunk]),
        status_code=status_code,
        media_type=media_type,
        headers=headers,
    )


@router.post("/", response_model=MessageResponse, status_code=201)
async def create_message(
    data: MessageCreate,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> MessageResponse:
    service = MessageService(session, owner_id=int(current_user.id))
    return await service.create(data)


@router.post("/send", response_model=MessageResponse)
async def send_reply(
    data: ChannelSendReply,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> MessageResponse:
    cms = ChannelMessageService(session, owner_id=int(current_user.id))
    reply = await cms.send_reply(
        message_id=data.message_id,
        content=data.content,
        client_request_id=data.client_request_id,
        recipient=data.recipient,
    )
    if not reply:
        raise HTTPException(status_code=404, detail="Original message not found")
    return reply


@router.post("/send-file", response_model=MessageResponse)
async def send_file_reply(
    message_id: int = Form(...),
    content: str = Form(""),
    files: list[UploadFile] = File(...),
    client_request_id: Optional[str] = Form(None),
    recipient: Optional[str] = Form(None),
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> MessageResponse:
    cms = ChannelMessageService(session, owner_id=int(current_user.id))
    reply = await cms.send_file_reply(
        message_id=message_id,
        content=content,
        files=files,
        client_request_id=client_request_id,
        recipient=recipient,
    )
    if not reply:
        raise HTTPException(status_code=404, detail="Original message not found")
    return reply


@router.post("/send-message", response_model=MessageResponse)
async def send_message(
    data: ChannelSendMessage,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> MessageResponse:
    cms = ChannelMessageService(session, owner_id=int(current_user.id))
    reply = await cms.send_message(
        contact_id=data.contact_id,
        channel=data.channel,
        content=data.content,
        client_request_id=data.client_request_id,
        recipient=data.recipient,
    )
    if not reply:
        raise HTTPException(status_code=404, detail="Contact not found")
    return reply


@router.post("/send-file-message", response_model=MessageResponse)
async def send_file_message(
    contact_id: int = Form(...),
    channel: str = Form(...),
    content: str = Form(""),
    files: list[UploadFile] = File(...),
    client_request_id: Optional[str] = Form(None),
    recipient: Optional[str] = Form(None),
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> MessageResponse:
    cms = ChannelMessageService(session, owner_id=int(current_user.id))
    reply = await cms.send_file_message(
        contact_id=contact_id,
        channel=channel,
        content=content,
        files=files,
        client_request_id=client_request_id,
        recipient=recipient,
    )
    if not reply:
        raise HTTPException(status_code=404, detail="Contact not found")
    return reply


@router.post("/send-new", response_model=MessageResponse)
async def send_new(
    data: ChannelSendNew,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> MessageResponse:
    cms = ChannelMessageService(session, owner_id=int(current_user.id))
    from ..deps import get_poll_service
    ps = get_poll_service()
    if ps:
        for ct in ("telegram", "email", "vk"):
            adapter = ps.get_channel(ct)
            if adapter is not None:
                cms.register_channel(ct, adapter)
    try:
        return await cms.send_to_recipient(
            channel=data.channel,
            recipient=data.recipient,
            content=data.content,
            client_request_id=data.client_request_id,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(502, f"Не удалось отправить сообщение: {e}")


class ForwardRequest(BaseModel):
    message_id: int = Field(..., gt=0)
    target_contact_id: int = Field(..., gt=0)
    content: str = Field(..., min_length=1)


@router.post("/forward", response_model=MessageResponse)
async def forward_message(
    data: ForwardRequest,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> MessageResponse:
    source = await MessageRepository(session, owner_id=int(current_user.id)).get_by_id(
        data.message_id
    )
    if not source:
        raise HTTPException(status_code=404, detail="Message not found")

    target = await ContactRepository(session, owner_id=int(current_user.id)).get_by_id(
        data.target_contact_id
    )
    if not target:
        raise HTTPException(status_code=404, detail="Contact not found")

    if target.telegram_username:
        channel, recipient = "telegram", f"@{target.telegram_username.lstrip('@')}"
    elif target.telegram_id:
        channel, recipient = "telegram", str(target.telegram_id)
    elif target.email:
        channel, recipient = "email", str(target.email)
    elif target.vk_id:
        channel, recipient = "vk", str(target.vk_id)
    else:
        raise HTTPException(
            status_code=400,
            detail="У контакта нет адреса для пересылки (телефон/email не указаны)",
        )

    cms = ChannelMessageService(session, owner_id=int(current_user.id))
    from ..deps import get_poll_service
    ps = get_poll_service()
    if ps:
        for ct in ("telegram", "email", "vk"):
            adapter = ps.get_channel(ct)
            if adapter is not None:
                cms.register_channel(ct, adapter)

    try:
        return await cms.send_to_recipient(
            channel=channel,
            recipient=recipient,
            content=data.content,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(502, f"Не удалось переслать сообщение: {e}")


@router.post("/bulk/restore", response_model=dict)
async def bulk_restore(
    data: BulkIdsRequest,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> dict[str, Any]:
    service = MessageService(session, owner_id=int(current_user.id))
    restored = await service.bulk_restore(data.ids)
    return {"restored": restored}


@router.post("/bulk/read", response_model=dict)
async def bulk_read(
    data: BulkActionRequest,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> dict[str, Any]:
    if not data.ids:
        raise HTTPException(status_code=400, detail="ids must not be empty")
    service = MessageService(session, owner_id=int(current_user.id))
    updated = await service.bulk_update_status(data.ids, "read")
    if updated > 0:
        invalidate_metrics_cache()
    return {"read": updated}


@router.post("/bulk/archive", response_model=dict)
async def bulk_archive(
    data: BulkActionRequest,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> dict[str, Any]:
    if not data.ids:
        raise HTTPException(status_code=400, detail="ids must not be empty")
    service = MessageService(session, owner_id=int(current_user.id))
    archived = await service.bulk_update_status(data.ids, "archived")
    if archived > 0:
        invalidate_metrics_cache()
    return {"archived": archived}


@router.post("/bulk/delete", response_model=dict)
async def bulk_delete_post(
    data: BulkActionRequest,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> dict[str, Any]:
    if not data.ids:
        raise HTTPException(status_code=400, detail="ids must not be empty")
    service = MessageService(session, owner_id=int(current_user.id))
    deleted = await service.bulk_delete(data.ids)
    if deleted > 0:
        invalidate_metrics_cache()
    return {"deleted": deleted}


@router.patch("/bulk/status", response_model=dict)
async def bulk_update_status(
    data: BulkStatusUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> dict[str, Any]:
    service = MessageService(session, owner_id=int(current_user.id))
    updated = await service.bulk_update_status(data.ids, data.status)
    if updated > 0:
        invalidate_metrics_cache()
    return {"updated": updated}


@router.patch("/{message_id}", response_model=MessageResponse)
async def update_message(
    message_id: int,
    data: MessageUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> MessageResponse:
    service = MessageService(session, owner_id=int(current_user.id))
    message = await service.update(message_id, data)
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    return message


@router.patch("/{message_id}/snooze", response_model=MessageResponse)
async def snooze_message(
    message_id: int,
    data: SnoozeRequest,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> MessageResponse:
    service = MessageService(session, owner_id=int(current_user.id))
    message = await service.snooze(message_id, data.until)
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    return message


@router.delete("/bulk", response_model=dict)
async def bulk_delete(
    data: BulkIdsRequest,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> dict[str, Any]:
    service = MessageService(session, owner_id=int(current_user.id))
    deleted = await service.bulk_delete(data.ids)
    return {"deleted": deleted}


@router.delete("/contact/{contact_id}", response_model=dict)
async def delete_contact_messages(
    contact_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> dict[str, Any]:
    service = MessageService(session, owner_id=int(current_user.id))
    deleted = await service.delete_contact_messages(contact_id)
    if deleted > 0:
        invalidate_metrics_cache()
    return {"deleted": deleted}


@router.post("/contact/{contact_id}/mark-read", response_model=dict)
async def mark_contact_read(
    contact_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> dict[str, Any]:
    service = MessageService(session, owner_id=int(current_user.id))
    updated = await service.mark_contact_read(contact_id)
    if updated > 0:
        invalidate_metrics_cache()
    return {"updated": updated}


@router.post("/contact/{contact_id}/mark-unread", response_model=dict)
async def mark_contact_unread(
    contact_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> dict[str, Any]:
    service = MessageService(session, owner_id=int(current_user.id))
    ok = await service.mark_contact_unread(contact_id)
    if ok:
        invalidate_metrics_cache()
    return {"updated": 1 if ok else 0}


@router.delete("/{message_id}", status_code=204)
async def delete_message(
    message_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> None:
    service = MessageService(session, owner_id=int(current_user.id))
    deleted = await service.delete(message_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Message not found")
