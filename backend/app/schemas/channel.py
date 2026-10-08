from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ChannelConnectTelegram(BaseModel):
    phone: str = Field(..., pattern=r"^\+?\d{7,15}$")
    via: str = Field(default="auto", pattern=r"^(auto|sms|app)$")


class ChannelConfirmTelegram(BaseModel):
    channel_id: int = Field(..., gt=0)
    code: str = Field(..., min_length=1, max_length=10)
    phone_code_hash: str = Field(..., min_length=1)


class ChannelResendTelegram(BaseModel):
    channel_id: int = Field(..., gt=0)
    phone_code_hash: str = Field(..., min_length=1)


class ChannelPasswordTelegram(BaseModel):
    channel_id: int = Field(..., gt=0)
    password: str = Field(..., min_length=1)


class ChannelConnectEmail(BaseModel):
    email: str = Field(..., max_length=255)
    password: str = Field(..., min_length=1)
    imap_host: str = Field(..., max_length=255)
    smtp_host: str = Field(..., max_length=255)
    imap_port: int = Field(default=993, ge=1, le=65535)
    smtp_port: int = Field(default=465, ge=1, le=65535)


class ChannelConnectVK(BaseModel):
    group_id: Optional[int] = Field(default=None, gt=0)
    token: Optional[str] = Field(default=None, min_length=1)


class ChannelReconnectStored(BaseModel):
    channel_id: int = Field(..., gt=0)


class DownloadResponse(BaseModel):
    new_messages: int
    last_polled_at: Optional[datetime] = None


class ChannelResponse(BaseModel):
    id: int
    type: str
    name: str
    is_connected: bool
    mode: str = "both"
    last_polled_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ChannelModeUpdate(BaseModel):
    mode: str = Field(..., pattern=r"^(both|incoming_only|outgoing_only)$")


class ChannelSendReply(BaseModel):
    message_id: int = Field(..., gt=0)
    content: str = Field(..., min_length=1)
    recipient: Optional[str] = Field(None, max_length=255)
    client_request_id: Optional[str] = Field(None, max_length=64)


class ChannelSendMessage(BaseModel):
    contact_id: int = Field(..., gt=0)
    channel: str = Field(..., pattern=r"^(telegram|email|vk)$")
    content: str = Field(..., min_length=1)
    recipient: Optional[str] = Field(None, max_length=255)
    client_request_id: Optional[str] = Field(None, max_length=64)


class ChannelSendNew(BaseModel):
    channel: str = Field(..., pattern=r"^(telegram|email|vk)$")
    recipient: str = Field(..., min_length=1, max_length=255)
    content: str = Field(..., min_length=1)
    client_request_id: Optional[str] = Field(None, max_length=64)
