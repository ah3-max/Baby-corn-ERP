"""
採購單資料庫模型
支援兩種模式：農民直購 / 中盤商採購
"""
import uuid
from datetime import datetime, date
from sqlalchemy import Column, String, Boolean, DateTime, Date, Text, ForeignKey, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from database import Base


class PurchaseOrder(Base):
    """採購單主表"""
    __tablename__ = "purchase_orders"

    id                = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_no          = Column(String(30), unique=True, nullable=False)          # 採購編號 PO-YYYYMMDD-XXX
    order_date        = Column(Date, nullable=False, default=date.today)         # 採購日期
    supplier_id       = Column(UUID(as_uuid=True), ForeignKey("suppliers.id"), nullable=False)   # 採購來源（農民/中盤商）
    source_farmer_id  = Column(UUID(as_uuid=True), ForeignKey("suppliers.id"), nullable=True)    # 中盤商時的原始農民來源

    # 重量與價格
    estimated_weight  = Column(Numeric(10, 2), nullable=False)                   # 預計重量（kg）
    unit_price        = Column(Numeric(10, 2), nullable=False)                   # 單價（THB/kg）
    total_amount      = Column(Numeric(12, 2), nullable=False)                   # 總金額（THB）

    # 時間
    expected_arrival  = Column(DateTime, nullable=True)                          # 預計到廠時間

    # 狀態：draft / confirmed / in_transit / arrived / closed
    status            = Column(String(20), nullable=False, default="draft")

    # 到廠資訊（arrived 後填入）
    arrived_at        = Column(DateTime, nullable=True)                          # 實際到廠時間
    received_weight   = Column(Numeric(10, 2), nullable=True)                   # 收貨重量（kg）
    defect_weight     = Column(Numeric(10, 2), nullable=True)                   # 不良重量（kg）
    usable_weight     = Column(Numeric(10, 2), nullable=True)                   # 可用重量（kg）
    defect_rate       = Column(Numeric(5, 2), nullable=True)                    # 不良率（%）
    arrival_note      = Column(Text, nullable=True)                             # 到廠備註

    note              = Column(Text, nullable=True)                             # 採購備註
    created_by        = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at        = Column(DateTime, default=datetime.utcnow)
    updated_at        = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 關聯
    supplier       = relationship("Supplier", foreign_keys=[supplier_id])
    source_farmer  = relationship("Supplier", foreign_keys=[source_farmer_id])
    creator        = relationship("User", foreign_keys=[created_by])
