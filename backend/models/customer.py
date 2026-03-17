"""
台灣客戶模型
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, Boolean, ForeignKey, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.orm import relationship

from database import Base


class Customer(Base):
    """台灣銷售客戶"""
    __tablename__ = "customers"
    __table_args__ = (
        CheckConstraint(
            "customer_type IN ('wholesaler','retailer','consignee','agent','potential')",
            name="ck_customers_customer_type",
        ),
        CheckConstraint(
            "credit_status IN ('good','warning','blocked')",
            name="ck_customers_credit_status",
        ),
    )

    id                     = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code                   = Column(String(20), unique=True, nullable=True)      # 客戶代碼（如 C001）nullable 漸進遷移
    name                   = Column(String(200), nullable=False)
    customer_type          = Column(String(20), nullable=True)                   # 客戶類型（nullable 漸進遷移）
    contact_name           = Column(String(100), nullable=True)
    phone                  = Column(String(50), nullable=True)
    email                  = Column(String(200), nullable=True)
    region                 = Column(String(100), nullable=True)                  # 地區（縣市）
    market_code            = Column(String(10), nullable=True)                   # 市場代碼（TPE_M1, TPE_M2）
    address                = Column(Text, nullable=True)
    payment_terms          = Column(String(200), nullable=True)                  # 付款條件
    preferred_specs        = Column(JSON, default=list)                          # 常買規格
    credit_status          = Column(String(10), default="good", nullable=False)  # 信用狀態
    assigned_sales_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)  # 負責業務
    note                   = Column(Text, nullable=True)
    is_active              = Column(Boolean, default=True, nullable=False)
    deleted_at             = Column(DateTime, nullable=True)                     # 軟刪除時間
    created_at             = Column(DateTime, default=datetime.utcnow)
    updated_at             = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 關聯
    assigned_sales = relationship("User", foreign_keys=[assigned_sales_user_id])
    sales_orders   = relationship("SalesOrder", back_populates="customer")
    payments       = relationship("PaymentRecord", back_populates="customer")
