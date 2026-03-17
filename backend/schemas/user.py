"""
使用者與角色相關的 Pydantic Schema
"""
from uuid import UUID
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr


# ─── 權限 ────────────────────────────────────────────

class PermissionOut(BaseModel):
    """權限輸出"""
    id: UUID
    module: str
    action: str

    class Config:
        from_attributes = True


# ─── 角色 ────────────────────────────────────────────

class RoleCreate(BaseModel):
    """建立角色"""
    name: str
    description: Optional[str] = None
    permission_ids: List[UUID] = []


class RoleUpdate(BaseModel):
    """更新角色"""
    name: Optional[str] = None
    description: Optional[str] = None
    permission_ids: Optional[List[UUID]] = None


class RoleOut(BaseModel):
    """角色輸出"""
    id: UUID
    name: str
    description: Optional[str]
    is_system: bool
    created_at: datetime
    permissions: List[PermissionOut] = []

    class Config:
        from_attributes = True


class RoleSimple(BaseModel):
    """角色簡要輸出（用於使用者列表）"""
    id: UUID
    name: str

    class Config:
        from_attributes = True


# ─── 使用者 ────────────────────────────────────────────

class UserCreate(BaseModel):
    """建立使用者"""
    email: EmailStr
    password: str
    full_name: str
    role_id: Optional[UUID] = None
    preferred_language: str = "zh-TW"
    note: Optional[str] = None


class UserUpdate(BaseModel):
    """更新使用者"""
    full_name: Optional[str] = None
    role_id: Optional[UUID] = None
    preferred_language: Optional[str] = None
    is_active: Optional[bool] = None
    note: Optional[str] = None


class UserOut(BaseModel):
    """使用者輸出"""
    id: UUID
    email: str
    full_name: str
    preferred_language: str
    is_active: bool
    note: Optional[str]
    created_at: datetime
    updated_at: datetime
    role: Optional[RoleSimple]

    class Config:
        from_attributes = True


class UserMe(BaseModel):
    """目前登入使用者資訊"""
    id: UUID
    email: str
    full_name: str
    preferred_language: str
    role: Optional[RoleSimple]
    permissions: List[str] = []   # ["supplier:view", "batch:create", ...]

    class Config:
        from_attributes = True
