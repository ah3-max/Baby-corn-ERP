"""
出口物流模型
一個出口單可關聯多個批次，追蹤從泰國到台灣的物流流程
"""
import uuid
from datetime import datetime, date
from sqlalchemy import Column, String, DateTime, Date, Text, ForeignKey, Numeric, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from database import Base

SHIPMENT_STATUSES = [
    "preparing",   # 備貨中
    "customs_th",  # 泰國報關
    "in_transit",  # 海運中
    "customs_tw",  # 台灣報關
    "arrived_tw",  # 已抵台（終態）
]

SHIPMENT_STATUS_NEXT: dict[str, str | None] = {
    "preparing":  "customs_th",
    "customs_th": "in_transit",
    "in_transit": "customs_tw",
    "customs_tw": "arrived_tw",
    "arrived_tw": None,
}


class Shipment(Base):
    """出口單主表"""
    __tablename__ = "shipments"

    id                   = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    shipment_no          = Column(String(30), unique=True, nullable=False)          # 出口編號 SH-YYYYMMDD-XXX
    export_date          = Column(Date, nullable=False, default=date.today)         # 出口日期
    carrier              = Column(String(100), nullable=True)                       # 承運商
    vessel_name          = Column(String(100), nullable=True)                       # 船名/航班
    bl_no                = Column(String(100), nullable=True)                       # 提單號
    estimated_arrival_tw = Column(Date, nullable=True)                             # 預計抵台
    actual_arrival_tw    = Column(Date, nullable=True)                             # 實際抵台
    status               = Column(String(20), nullable=False, default="preparing")
    total_weight         = Column(Numeric(10, 2), nullable=True)                   # 總重量（自動彙整）
    freight_cost         = Column(Numeric(12, 2), nullable=True)                   # 運費（THB）
    customs_cost         = Column(Numeric(12, 2), nullable=True)                   # 關稅（TWD）
    notes                = Column(Text, nullable=True)
    # ── Module J: 出口出貨詳細資訊 ─────────────────────────────────────
    transport_mode      = Column(String(10), nullable=True)     # air / sea
    shipped_boxes       = Column(Integer, nullable=True)         # 裝箱數
    shipper_name        = Column(String(100), nullable=True)     # 出貨人
    export_customs_no   = Column(String(100), nullable=True)     # 出口報關號碼
    phyto_cert_no       = Column(String(100), nullable=True)     # 植檢證號碼
    phyto_cert_date     = Column(Date, nullable=True)            # 植檢日期
    actual_departure_dt = Column(DateTime, nullable=True)        # 實際出發時間
    # ── 空運專屬欄位 ──────────────────────────────────────────────────
    awb_no              = Column(String(100), nullable=True)     # AWB 提單號碼
    flight_no           = Column(String(50), nullable=True)      # 航班號
    airline             = Column(String(100), nullable=True)     # 航空公司
    # ── 海運專屬欄位 ──────────────────────────────────────────────────
    container_no        = Column(String(100), nullable=True)     # 貨櫃號碼
    port_of_loading     = Column(String(100), nullable=True)     # 裝載港（泰國）
    port_of_discharge   = Column(String(100), nullable=True)     # 卸貨港（台灣）
    # ── 補充費用欄位（TWD）─────────────────────────────────────────────
    insurance_cost      = Column(Numeric(12, 2), nullable=True)  # 保險費（TWD）
    handling_cost       = Column(Numeric(12, 2), nullable=True)  # 搬運/倉儲費（TWD）
    other_cost          = Column(Numeric(12, 2), nullable=True)  # 其他費用（TWD）
    created_by           = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at           = Column(DateTime, default=datetime.utcnow)
    updated_at           = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    shipment_batches = relationship("ShipmentBatch", back_populates="shipment", cascade="all, delete-orphan")
    creator          = relationship("User", foreign_keys=[created_by])


class ShipmentBatch(Base):
    """出口單 ↔ 批次 多對多中間表"""
    __tablename__ = "shipment_batches"

    shipment_id = Column(UUID(as_uuid=True), ForeignKey("shipments.id"), primary_key=True)
    batch_id    = Column(UUID(as_uuid=True), ForeignKey("batches.id"),    primary_key=True)

    shipment = relationship("Shipment", back_populates="shipment_batches")
    batch    = relationship("Batch")
