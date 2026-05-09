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
    # ── 國際貿易欄位（B-02）──────────────────────────────────────────────
    exchange_rate         = Column(Numeric(10, 4), nullable=True)             # THB→TWD 匯率快照
    incoterm              = Column(String(10), nullable=True)                 # 貿易條件（FOB/CIF/CFR）
    hs_code               = Column(String(20), nullable=True)                 # 海關 HS 稅則號碼
    commercial_invoice_no = Column(String(100), nullable=True)                # 商業發票號碼
    voyage_no             = Column(String(100), nullable=True)                # 航次號碼
    # ── H-01：海運強化 18+ 里程碑欄位 ────────────────────────────────────
    shipping_mode         = Column(String(10), nullable=True)                 # FCL/LCL
    container_type        = Column(String(10), nullable=True)                 # 20RF/40RF/40HC
    forwarder             = Column(String(200), nullable=True)                # 承攬業者
    customs_broker        = Column(String(200), nullable=True)                # 報關行
    shipping_line         = Column(String(200), nullable=True)                # 船公司
    factory_exit_date     = Column(Date, nullable=True)                       # 工廠出貨日
    consolidation_date    = Column(Date, nullable=True)                       # 併裝日
    container_loading_date = Column(Date, nullable=True)                      # 裝櫃日
    customs_declare_date  = Column(Date, nullable=True)                       # 泰國報關日
    customs_cleared_date  = Column(Date, nullable=True)                       # 泰國放行日
    transshipment_port    = Column(String(100), nullable=True)                # 轉運港
    transshipment_date    = Column(Date, nullable=True)                       # 轉運日
    destination_customs_date = Column(Date, nullable=True)                    # 台灣報關日
    devanning_date        = Column(Date, nullable=True)                       # 拆櫃日
    warehouse_in_date     = Column(Date, nullable=True)                       # 入庫日
    ocean_freight_cost    = Column(Numeric(12, 2), nullable=True)             # 海運費（USD）
    document_fee          = Column(Numeric(10, 2), nullable=True)             # 文件費（USD）
    port_charge           = Column(Numeric(10, 2), nullable=True)             # 港口雜費（USD）
    trucking_fee          = Column(Numeric(10, 2), nullable=True)             # 內陸運費（TWD）
    storage_fee           = Column(Numeric(10, 2), nullable=True)             # 倉儲費（TWD）
    total_logistics_cost_twd = Column(Numeric(14, 2), nullable=True)          # 總物流成本（TWD）

    created_by           = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    updated_by           = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)   # 最後更新者
    created_at           = Column(DateTime, default=datetime.utcnow)
    updated_at           = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    shipment_batches = relationship("ShipmentBatch", back_populates="shipment", cascade="all, delete-orphan")
    creator          = relationship("User", foreign_keys=[created_by])
    updater          = relationship("User", foreign_keys=[updated_by])


class ShipmentBatch(Base):
    """出口單 ↔ 批次 多對多中間表"""
    __tablename__ = "shipment_batches"

    shipment_id = Column(UUID(as_uuid=True), ForeignKey("shipments.id"), primary_key=True)
    batch_id    = Column(UUID(as_uuid=True), ForeignKey("batches.id"),    primary_key=True)

    shipment = relationship("Shipment", back_populates="shipment_batches")
    batch    = relationship("Batch")
