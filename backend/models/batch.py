"""
批次資料庫模型
每個到廠採購單可開立一個或多個批次，批次為系統核心追蹤單位
狀態流程：processing → qc_pending → qc_done → packaging → ready_to_export
           → exported → in_transit_tw → in_stock → sold → closed
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Numeric, Boolean, Integer
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.orm import relationship

from database import Base


# 批次合法狀態清單（有序，用於狀態推進驗證）
BATCH_STATUSES = [
    "processing",       # 工廠加工中
    "qc_pending",       # 待 QC 檢查
    "qc_done",          # QC 完成
    "packaging",        # 包裝中
    "ready_to_export",  # 備貨完成，等待出口
    "exported",         # 已出口
    "in_transit_tw",    # 台灣運輸中
    "in_stock",         # 台灣庫存中
    "sold",             # 已售出
    "closed",           # 結案（終態）
]

# 每個狀態的下一個合法狀態
STATUS_NEXT: dict[str, str | None] = {
    "processing":      "qc_pending",
    "qc_pending":      "qc_done",
    "qc_done":         "packaging",
    "packaging":       "ready_to_export",
    "ready_to_export": "exported",
    "exported":        "in_transit_tw",
    "in_transit_tw":   "in_stock",
    "in_stock":        "sold",
    "sold":            "closed",
    "closed":          None,
}


class Batch(Base):
    """批次主表 — 供應鏈追蹤核心"""
    __tablename__ = "batches"

    id                = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    batch_no          = Column(String(30), unique=True, nullable=False)           # 批次編號 BT-YYYYMMDD-XXX
    purchase_order_id = Column(UUID(as_uuid=True), ForeignKey("purchase_orders.id"), nullable=False)
    product_type_id   = Column(UUID(as_uuid=True), ForeignKey("product_types.id"), nullable=True)  # 品項類型（nullable，漸進遷移）
    size_grade        = Column(String(5), nullable=True)                                           # 規格分級，如 'S','M','L','XL'
    quality_data      = Column(JSON, default=dict)                                                 # 品質檢查資料（依 ProductType.quality_schema）
    region_code       = Column(String(5), nullable=True)                                           # 產區代碼

    # 重量追蹤
    initial_weight    = Column(Numeric(10, 2), nullable=False)                   # 初始重量（kg，來自採購單的可用重量）
    current_weight    = Column(Numeric(10, 2), nullable=False)                   # 目前可用重量（加工後可能減少）

    # 狀態
    status            = Column(String(30), nullable=False, default="processing") # 批次目前狀態

    note              = Column(Text, nullable=True)                              # 備註

    # ── 生鮮時效追蹤 ──────────────────────────────────────────────────
    # 田間採摘
    harvest_datetime        = Column(DateTime, nullable=True)           # 採摘時間（時效起點）
    harvest_location        = Column(String(200), nullable=True)        # 採摘地點（農場 / 地區）
    harvest_temperature     = Column(Numeric(4, 1), nullable=True)      # 採摘時溫度 °C
    harvest_weather         = Column(String(50), nullable=True)         # sunny/cloudy/rainy/storm/hot
    transport_refrigerated  = Column(Boolean, nullable=True)            # 採摘→工廠 是否冷藏運輸

    # 工廠里程碑
    factory_arrival_dt      = Column(DateTime, nullable=True)           # 抵達工廠時間
    factory_temp_on_arrival = Column(Numeric(4, 1), nullable=True)      # 到廠時品溫 °C
    factory_complete_dt     = Column(DateTime, nullable=True)           # 加工完成時間
    cold_storage_temp       = Column(Numeric(4, 1), nullable=True)      # 冷藏庫設定溫度 °C

    # 包裝 / 出口
    packed_dt               = Column(DateTime, nullable=True)           # 包裝完成時間
    container_loaded_dt     = Column(DateTime, nullable=True)           # 裝貨（容器）時間

    # 有效期設定
    shelf_life_days         = Column(Integer, nullable=True)            # 有效天數（預設 23）

    created_by        = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at        = Column(DateTime, default=datetime.utcnow)
    updated_at        = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 關聯
    purchase_order = relationship("PurchaseOrder", foreign_keys=[purchase_order_id])
    product_type   = relationship("ProductType", foreign_keys=[product_type_id])
    creator        = relationship("User", foreign_keys=[created_by])
