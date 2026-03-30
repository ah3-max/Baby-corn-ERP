"""附件相關 Pydantic Schema"""
from uuid import UUID
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel


class AttachmentCreate(BaseModel):
    entity_type: str
    entity_id: UUID
    file_name: str
    file_size: Optional[int] = None
    mime_type: Optional[str] = None
    storage_path: str
    tags: List[str] = []


class AttachmentTagOut(BaseModel):
    id: UUID
    tag: str
    created_at: datetime

    class Config:
        from_attributes = True


class AttachmentOut(BaseModel):
    id: UUID
    entity_type: str
    entity_id: UUID
    file_name: str
    file_size: Optional[int]
    mime_type: Optional[str]
    storage_path: str
    uploaded_by: Optional[UUID]
    created_at: datetime
    tags: List[AttachmentTagOut] = []

    class Config:
        from_attributes = True
