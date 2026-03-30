"""
系統稽核模型 — Append-Only 設計

1. DomainEvent — 領域事件（記錄系統內所有重要事件）
2. AuditLog    — 稽核日誌（記錄使用者操作）

兩者皆為 Append-Only，不可 UPDATE / DELETE。
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.orm import relationship

from database import Base


class DomainEvent(Base):
    """領域事件 — Append-Only

    記錄系統內所有重要業務事件，例如：
    - batch.created / batch.status_changed
    - cost_event.recorded
    - qc.completed
    """
    __tablename__ = "domain_events"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_type      = Column(String(60), nullable=False)       # 事件類型，如 'batch.created'
    aggregate_type  = Column(String(30), nullable=False)       # 聚合根類型，如 'batch'
    aggregate_id    = Column(UUID(as_uuid=True), nullable=False)  # 聚合根 ID
    payload         = Column(JSON, nullable=True)               # 事件內容（JSON）
    actor_id        = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    ip_address      = Column(String(45), nullable=True)        # 支援 IPv6
    recorded_at     = Column(DateTime, default=datetime.utcnow, nullable=False)

    # 關聯
    actor = relationship("User", foreign_keys=[actor_id])


class AuditLog(Base):
    """稽核日誌 — Append-Only

    記錄使用者的所有操作行為，用於安全稽核與合規追蹤。
    """
    __tablename__ = "audit_logs"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id         = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    action          = Column(String(30), nullable=False)       # 操作類型：create/update/delete/login/export 等
    entity_type     = Column(String(30), nullable=True)        # 實體類型，如 'batch', 'cost_event'
    entity_id       = Column(UUID(as_uuid=True), nullable=True)  # 實體 ID
    changes         = Column(JSON, nullable=True)               # 變更內容（JSON diff）
    ip_address      = Column(String(45), nullable=True)        # 支援 IPv6
    user_agent      = Column(String(500), nullable=True)       # 瀏覽器 User-Agent
    recorded_at     = Column(DateTime, default=datetime.utcnow, nullable=False)

    # 關聯
    user = relationship("User", foreign_keys=[user_id])
