"""通知相關 Pydantic Schema"""
from uuid import UUID
from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel


class NotificationCreate(BaseModel):
    recipient_user_id: UUID
    notification_type: str
    title: str
    message: Optional[dict] = None
    expires_at: Optional[datetime] = None


class NotificationOut(BaseModel):
    id: UUID
    recipient_user_id: UUID
    notification_type: str
    title: str
    message: Optional[Any]
    is_read: bool
    read_at: Optional[datetime]
    created_at: datetime
    expires_at: Optional[datetime]

    class Config:
        from_attributes = True
