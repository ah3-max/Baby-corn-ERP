"""
提醒通知模型
系統自動產生的通知，例如庫存老化警告、待出貨提醒等。
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, CheckConstraint, Index
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.orm import relationship

from database import Base


class Notification(Base):
    """提醒通知

    系統自動或手動產生，推送給指定使用者。
    message 欄位為 JSON，可包含 entity_type / entity_id / details 等結構化資訊。
    """
    __tablename__ = "notifications"
    __table_args__ = (
        CheckConstraint(
            "notification_type IN ('stock_age_warning','stock_age_critical',"
            "'pending_shipment','pending_payment','cost_incomplete','qc_required')",
            name="ck_notifications_type",
        ),
        # 未讀通知的部分索引，加速查詢
        Index(
            "ix_notifications_unread",
            "recipient_user_id", "is_read",
            postgresql_where="is_read = FALSE",
        ),
    )

    id                  = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    recipient_user_id   = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    notification_type   = Column(String(30), nullable=False)                  # 通知類型
    title               = Column(String(200), nullable=False)                 # 通知標題
    message             = Column(JSON, nullable=True)                         # 結構化內容
    is_read             = Column(Boolean, default=False, nullable=False)      # 是否已讀
    read_at             = Column(DateTime, nullable=True)                     # 已讀時間
    created_at          = Column(DateTime, default=datetime.utcnow)
    expires_at          = Column(DateTime, nullable=True)                     # 過期時間

    # 關聯
    recipient = relationship("User", foreign_keys=[recipient_user_id])
