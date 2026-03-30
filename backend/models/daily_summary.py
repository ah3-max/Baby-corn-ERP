"""
WP8：每日摘要與告警規則模型

1. DailySummarySnapshot — 每日營運快照（append-only）
2. AlertRule            — 告警規則定義
"""
import uuid
from datetime import datetime, date
from sqlalchemy import (
    Column, String, DateTime, Date, Text, ForeignKey,
    Numeric, Boolean, Integer,
)
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.orm import relationship

from database import Base


class DailySummarySnapshot(Base):
    """每日營運快照 — 排程產生，用於趨勢分析"""
    __tablename__ = "daily_summary_snapshots"

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    summary_date = Column(Date, unique=True, nullable=False)
    data         = Column(JSON, nullable=False)  # 完整的每日統計 JSON
    sent_to      = Column(JSON, default=list)    # 已發送給哪些使用者
    created_at   = Column(DateTime, default=datetime.utcnow)


class AlertRule(Base):
    """告警規則 — 定義條件、嚴重程度、通知對象"""
    __tablename__ = "alert_rules"

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rule_code        = Column(String(30), unique=True, nullable=False)
    rule_type        = Column(String(20), nullable=False)  # stock_age / ar_overdue / freshness / reorder / weather / budget
    condition        = Column(JSON, nullable=False)         # {"field":"age_days","operator":">","value":14}
    severity         = Column(String(10), nullable=False, default="warning")  # info / warning / critical
    notify_roles     = Column(JSON, default=list)           # ["tw_manager","admin"]
    notify_users     = Column(JSON, default=list)           # [user_id, ...]
    is_active        = Column(Boolean, default=True, nullable=False)
    cooldown_hours   = Column(Integer, default=24)          # 同一告警冷卻時間
    last_triggered_at = Column(DateTime, nullable=True)
    created_at       = Column(DateTime, default=datetime.utcnow)
    updated_at       = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
