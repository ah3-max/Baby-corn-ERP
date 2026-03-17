"""系統設定相關 Pydantic Schema"""
from uuid import UUID
from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel


class SystemSettingCreate(BaseModel):
    key: str
    value: Any
    description: Optional[str] = None


class SystemSettingUpdate(BaseModel):
    value: Any
    description: Optional[str] = None


class SystemSettingOut(BaseModel):
    id: UUID
    key: str
    value: Any
    description: Optional[str]
    updated_by: Optional[UUID]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
