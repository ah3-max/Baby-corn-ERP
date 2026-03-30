"""
收付款紀錄模型
記錄客戶付款資訊，可關聯到銷售訂單。
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Date, Text, ForeignKey, Numeric, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from database import Base


class PaymentRecord(Base):
    """收付款紀錄"""
    __tablename__ = "payment_records"
    __table_args__ = (
        CheckConstraint(
            "payment_method IN ('cash','transfer','check')",
            name="ck_payment_records_method",
        ),
        CheckConstraint(
            "status IN ('pending','confirmed','bounced')",
            name="ck_payment_records_status",
        ),
    )

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id      = Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False)
    sales_order_id   = Column(UUID(as_uuid=True), ForeignKey("sales_orders.id"), nullable=True)
    payment_date     = Column(Date, nullable=False)                                    # 付款日期
    amount_twd       = Column(Numeric(12, 2), nullable=False)                          # 金額（TWD）
    payment_method   = Column(String(20), nullable=False)                              # cash/transfer/check
    reference_no     = Column(String(50), nullable=True)                               # 轉帳帳號/支票號碼
    status           = Column(String(15), nullable=False, default="pending")           # 狀態
    confirmed_by     = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    confirmed_at     = Column(DateTime, nullable=True)                                 # 確認時間
    notes            = Column(Text, nullable=True)
    created_by       = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at       = Column(DateTime, default=datetime.utcnow)

    # 關聯
    customer     = relationship("Customer", back_populates="payments", foreign_keys=[customer_id])
    sales_order  = relationship("SalesOrder", back_populates="payments", foreign_keys=[sales_order_id])
    confirmer    = relationship("User", foreign_keys=[confirmed_by])
    creator      = relationship("User", foreign_keys=[created_by])
