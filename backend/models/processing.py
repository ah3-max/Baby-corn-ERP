"""
加工單模型
記錄 OEM 工廠的加工作業，包含投入/產出批次關聯。
"""
import uuid
from datetime import datetime, date as date_type
from sqlalchemy import (
    Column, String, DateTime, Date, Text, ForeignKey,
    Numeric, CheckConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from database import Base


class ProcessingOrder(Base):
    """加工單

    每筆加工作業對應一張加工單，
    透過 ProcessingBatchLink 關聯投入 (in) 與產出 (out) 的批次。
    """
    __tablename__ = "processing_orders"
    __table_args__ = (
        CheckConstraint(
            "status IN ('draft','in_progress','completed','cancelled')",
            name="ck_processing_orders_status",
        ),
    )

    id                = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_code        = Column(String(30), unique=True, nullable=False)        # 加工單號
    oem_factory_id    = Column(UUID(as_uuid=True), ForeignKey("oem_factories.id"), nullable=False)
    process_date      = Column(Date, nullable=False)                           # 加工日期
    total_input_kg    = Column(Numeric(10, 3), nullable=True)                  # 投入總重量
    total_output_kg   = Column(Numeric(10, 3), nullable=True)                  # 產出總重量
    waste_kg          = Column(Numeric(10, 3), nullable=True)                  # 損耗重量
    yield_pct         = Column(Numeric(5, 2), nullable=True)                   # 良率 %
    fee_per_kg_thb    = Column(Numeric(8, 2), nullable=True)                   # 加工費 THB/kg
    total_fee_thb     = Column(Numeric(12, 2), nullable=True)                  # 總加工費 THB
    status            = Column(String(15), nullable=False, default="draft")    # 狀態
    notes             = Column(Text, nullable=True)
    created_by        = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at        = Column(DateTime, default=datetime.utcnow)
    updated_at        = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 關聯
    oem_factory   = relationship("OEMFactory", foreign_keys=[oem_factory_id])
    creator       = relationship("User", foreign_keys=[created_by])
    batch_links   = relationship("ProcessingBatchLink", back_populates="processing_order",
                                 cascade="all, delete-orphan")


class ProcessingBatchLink(Base):
    """加工單 ↔ 批次關聯

    direction='in'  表示該批次為加工投入原料
    direction='out' 表示該批次為加工產出成品
    """
    __tablename__ = "processing_batch_links"
    __table_args__ = (
        CheckConstraint(
            "direction IN ('in','out')",
            name="ck_processing_batch_links_direction",
        ),
        CheckConstraint(
            "weight_kg > 0",
            name="ck_processing_batch_links_weight_positive",
        ),
    )

    id                    = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    processing_order_id   = Column(
        UUID(as_uuid=True),
        ForeignKey("processing_orders.id", ondelete="CASCADE"),
        nullable=False,
    )
    batch_id              = Column(UUID(as_uuid=True), ForeignKey("batches.id"), nullable=False)
    direction             = Column(String(3), nullable=False)                  # 'in' 或 'out'
    weight_kg             = Column(Numeric(10, 3), nullable=False)             # 重量 kg

    # 關聯
    processing_order = relationship("ProcessingOrder", back_populates="batch_links")
    batch            = relationship("Batch", foreign_keys=[batch_id])
