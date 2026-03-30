"""
WP3：業務團隊模型

1. SalesTeam       — 業務團隊（泰國端/台灣端）
2. SalesTeamMember — 團隊成員（經理/資深業務/業務）
"""
import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, DateTime, Text, ForeignKey,
    Numeric, Boolean, Integer,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from database import Base


class SalesTeam(Base):
    """業務團隊 — 分泰國端與台灣端"""
    __tablename__ = "sales_teams"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    team_code       = Column(String(20), unique=True, nullable=False)   # TH-SALES / TW-SALES
    team_name       = Column(String(100), nullable=False)
    region          = Column(String(20), nullable=False)                # thailand / taiwan
    manager_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    description     = Column(Text, nullable=True)
    is_active       = Column(Boolean, default=True, nullable=False)
    created_at      = Column(DateTime, default=datetime.utcnow)
    updated_at      = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 關聯
    manager = relationship("User", foreign_keys=[manager_user_id])
    members = relationship("SalesTeamMember", back_populates="team", cascade="all, delete-orphan")


class SalesTeamMember(Base):
    """團隊成員 — 含角色、月度目標"""
    __tablename__ = "sales_team_members"

    id                 = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    team_id            = Column(UUID(as_uuid=True), ForeignKey("sales_teams.id"), nullable=False)
    user_id            = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    role               = Column(String(20), nullable=False, default="sales")  # manager / senior_sales / sales
    target_monthly_twd = Column(Numeric(14, 2), default=0)                     # 月度銷售目標（TWD）
    joined_at          = Column(DateTime, default=datetime.utcnow)
    is_active          = Column(Boolean, default=True, nullable=False)
    created_at         = Column(DateTime, default=datetime.utcnow)

    # 關聯
    team = relationship("SalesTeam", back_populates="members")
    user = relationship("User", foreign_keys=[user_id])
