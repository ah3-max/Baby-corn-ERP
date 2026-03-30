"""
WP3：CRM 活動與任務模型

1. CRMActivity — 客戶拜訪/聯繫記錄
2. CRMTask     — 業務任務（經理指派給業務）
"""
import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, DateTime, Date, Text, ForeignKey,
    Numeric, Boolean, Integer,
)
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.orm import relationship

from database import Base


ACTIVITY_TYPES = ["visit", "call", "email", "meeting", "sample", "complaint"]
ACTIVITY_RESULTS = ["positive", "neutral", "negative"]
TASK_TYPES = ["follow_up", "visit", "collection", "delivery", "sample", "other"]
TASK_PRIORITIES = ["urgent", "high", "normal", "low"]
TASK_STATUSES = ["pending", "in_progress", "completed", "cancelled"]


class CRMActivity(Base):
    """CRM 活動記錄 — 拜訪、通話、會議等"""
    __tablename__ = "crm_activities"

    id                 = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    activity_no        = Column(String(30), unique=True, nullable=False)  # ACT-YYYYMMDD-XXX
    customer_id        = Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False)
    sales_user_id      = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)  # 負責業務
    activity_type      = Column(String(20), nullable=False)         # visit / call / email / meeting / sample / complaint
    activity_date      = Column(DateTime, nullable=False, default=datetime.utcnow)
    duration_minutes   = Column(Integer, nullable=True)
    summary            = Column(String(500), nullable=True)         # 摘要
    detail             = Column(Text, nullable=True)                # 詳情
    follow_up_date     = Column(Date, nullable=True)                # 下次跟進日期
    follow_up_action   = Column(String(200), nullable=True)         # 跟進事項
    result             = Column(String(20), nullable=True)          # positive / neutral / negative
    order_potential_twd = Column(Numeric(14, 2), nullable=True)     # 預估訂單金額
    attachments        = Column(JSON, default=list)                 # 附件 URL 列表
    created_at         = Column(DateTime, default=datetime.utcnow)
    updated_at         = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 關聯
    customer   = relationship("Customer", foreign_keys=[customer_id])
    sales_user = relationship("User", foreign_keys=[sales_user_id])


class CRMTask(Base):
    """業務任務 — 經理指派給業務的待辦事項"""
    __tablename__ = "crm_tasks"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_no         = Column(String(30), unique=True, nullable=False)  # TSK-YYYYMMDD-XXX
    assigned_to     = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)  # 指派給
    assigned_by     = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)  # 經理指派
    customer_id     = Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=True)
    task_type       = Column(String(20), nullable=False, default="other")  # follow_up / visit / collection / delivery / sample / other
    title           = Column(String(200), nullable=False)
    description     = Column(Text, nullable=True)
    priority        = Column(String(10), nullable=False, default="normal")  # urgent / high / normal / low
    due_date        = Column(Date, nullable=True)
    status          = Column(String(20), nullable=False, default="pending")  # pending / in_progress / completed / cancelled
    completed_at    = Column(DateTime, nullable=True)
    completion_note = Column(Text, nullable=True)
    created_at      = Column(DateTime, default=datetime.utcnow)
    updated_at      = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 關聯
    assignee  = relationship("User", foreign_keys=[assigned_to])
    assigner  = relationship("User", foreign_keys=[assigned_by])
    customer  = relationship("Customer", foreign_keys=[customer_id])
