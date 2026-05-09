"""
使用者與權限相關資料庫模型
包含：User、Role、Permission、RolePermission、RefreshToken
"""
import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Boolean, DateTime, Text, Integer, Numeric,
    ForeignKey, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from database import Base


class Role(Base):
    """角色表"""
    __tablename__ = "roles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(String(30), unique=True, nullable=True)              # 角色代碼（如 'admin'）nullable 漸進遷移
    name = Column(String(50), unique=True, nullable=False)             # 角色名稱（保留原欄位）
    name_zh = Column(String(50), nullable=True)                        # 繁體中文名稱
    name_en = Column(String(50), nullable=True)                        # 英文名稱
    name_th = Column(String(50), nullable=True)                        # 泰文名稱
    description = Column(Text, nullable=True)                          # 說明
    is_system = Column(Boolean, default=False, nullable=False)         # 是否為系統預設（不可刪）
    created_at = Column(DateTime, default=datetime.utcnow)

    # 關聯
    users = relationship("User", back_populates="role")
    role_permissions = relationship("RolePermission", back_populates="role", cascade="all, delete-orphan")


class Permission(Base):
    """權限項目表"""
    __tablename__ = "permissions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(String(60), unique=True, nullable=True)       # 權限代碼（如 'supplier.create'）nullable 漸進遷移
    module = Column(String(50), nullable=False)                  # 模組代碼（supplier, batch, sales...）
    action = Column(String(30), nullable=False)                  # 動作（create, read, update, delete, export）
    name_zh = Column(String(80), nullable=True)                  # 繁體中文名稱
    name_en = Column(String(80), nullable=True)                  # 英文名稱
    name_th = Column(String(80), nullable=True)                  # 泰文名稱

    __table_args__ = (
        UniqueConstraint("module", "action", name="uq_permission_module_action"),
    )

    # 關聯
    role_permissions = relationship("RolePermission", back_populates="permission")


class RolePermission(Base):
    """角色-權限對應表"""
    __tablename__ = "role_permissions"

    role_id = Column(UUID(as_uuid=True), ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True)
    permission_id = Column(UUID(as_uuid=True), ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True)

    # 關聯
    role = relationship("Role", back_populates="role_permissions")
    permission = relationship("Permission", back_populates="role_permissions")


class User(Base):
    """使用者表"""
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False)          # 電子信箱（登入帳號）
    password_hash = Column(String(255), nullable=False)               # bcrypt 雜湊密碼
    full_name = Column(String(100), nullable=False)                   # 姓名
    role_id = Column(UUID(as_uuid=True), ForeignKey("roles.id"), nullable=True)  # 所屬角色
    preferred_language = Column(String(5), default="zh-TW")          # 偏好語言：zh-TW / en / th
    is_active = Column(Boolean, default=True, nullable=False)         # 是否啟用
    token_version = Column(Integer, default=0, nullable=False)        # Token 版本號，登出/改密碼時 +1，使所有舊 Token 失效
    # ── C-06 HR 組織欄位 ────────────────────────────────────────────
    employee_level    = Column(String(20), nullable=True)             # junior/mid/senior/lead/manager/director/vp/c_level
    department_id     = Column(UUID(as_uuid=True), ForeignKey("departments.id"), nullable=True)  # 所屬部門
    reports_to_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)       # 直屬主管
    job_title         = Column(String(100), nullable=True)            # 職稱
    commission_rate   = Column(Numeric(5, 2), default=0, nullable=True)  # 業務佣金比例 %
    note = Column(Text, nullable=True)                                # 備註
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 關聯
    role           = relationship("Role", back_populates="users")
    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")
    department     = relationship("Department", foreign_keys=[department_id])
    reports_to     = relationship("User", foreign_keys=[reports_to_user_id], remote_side="User.id")


class RefreshToken(Base):
    """Refresh Token 表"""
    __tablename__ = "refresh_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token = Column(String(500), unique=True, nullable=False)   # Refresh Token 值
    expires_at = Column(DateTime, nullable=False)              # 過期時間
    created_at = Column(DateTime, default=datetime.utcnow)

    # 關聯
    user = relationship("User", back_populates="refresh_tokens")
