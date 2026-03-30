"""
WP4：物流派遣模型

1. Driver             — 司機
2. DeliveryOrder      — 配送單（業務經理下單 → 司機收單 → 出庫 → 配送 → 簽收）
3. DeliveryOrderItem  — 配送明細（每站一筆）
4. DeliveryProof      — 配送憑證（簽收照片/簽名）
5. OutboundOrder      — 出庫單
6. OutboundOrderItem  — 出庫明細
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


# ── 1. 司機 ──────────────────────────────────────────────

class Driver(Base):
    """司機 — 含車輛資訊、載重上限"""
    __tablename__ = "drivers"

    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    driver_code   = Column(String(20), unique=True, nullable=False)  # DR-XXX
    user_id       = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)  # 若有系統帳號
    name          = Column(String(100), nullable=False)
    phone         = Column(String(30), nullable=True)
    line_id       = Column(String(50), nullable=True)
    vehicle_type  = Column(String(30), nullable=True)  # refrigerated_truck / van / motorcycle
    vehicle_plate = Column(String(20), nullable=True)   # 車牌
    license_no    = Column(String(30), nullable=True)    # 駕照號
    max_load_kg   = Column(Numeric(10, 2), nullable=True)  # 最大載重
    is_active     = Column(Boolean, default=True, nullable=False)
    note          = Column(Text, nullable=True)
    created_at    = Column(DateTime, default=datetime.utcnow)
    updated_at    = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 關聯
    user = relationship("User", foreign_keys=[user_id])


# ── 2. 配送單 ────────────────────────────────────────────

DELIVERY_STATUSES = [
    "pending",           # 待派單
    "accepted",          # 司機已接單
    "picking",           # 揀貨中
    "loaded",            # 已裝車
    "in_transit",        # 配送中
    "delivered",         # 已完成
    "partial_delivered", # 部分完成
    "cancelled",         # 已取消
]

DELIVERY_STATUS_NEXT = {
    "pending":    "accepted",
    "accepted":   "picking",
    "picking":    "loaded",
    "loaded":     "in_transit",
    "in_transit": "delivered",
}


class DeliveryOrder(Base):
    """配送單 — 業務經理下單，司機收單配送"""
    __tablename__ = "delivery_orders"

    id                    = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    delivery_no           = Column(String(30), unique=True, nullable=False)  # DEL-YYYYMMDD-XXX
    order_type            = Column(String(20), nullable=False, default="sales_delivery")  # sales_delivery / market_delivery / sample / return
    driver_id             = Column(UUID(as_uuid=True), ForeignKey("drivers.id"), nullable=True)
    assigned_by           = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)  # 業務經理
    dispatch_date         = Column(Date, nullable=False, default=date.today)
    route_description     = Column(Text, nullable=True)
    status                = Column(String(20), nullable=False, default="pending")

    # 統計
    total_weight_kg       = Column(Numeric(10, 2), default=0)
    total_boxes           = Column(Integer, default=0)

    # 時間
    departure_time        = Column(DateTime, nullable=True)
    return_time           = Column(DateTime, nullable=True)

    # 溫度記錄
    vehicle_temp_departure = Column(Numeric(5, 2), nullable=True)
    vehicle_temp_arrival   = Column(Numeric(5, 2), nullable=True)

    # 費用
    fuel_cost_twd         = Column(Numeric(10, 2), nullable=True)
    toll_cost_twd         = Column(Numeric(10, 2), nullable=True)
    other_cost_twd        = Column(Numeric(10, 2), nullable=True)

    driver_note           = Column(Text, nullable=True)
    created_by            = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at            = Column(DateTime, default=datetime.utcnow)
    updated_at            = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 關聯
    driver    = relationship("Driver", foreign_keys=[driver_id])
    assigner  = relationship("User", foreign_keys=[assigned_by])
    creator   = relationship("User", foreign_keys=[created_by])
    items     = relationship("DeliveryOrderItem", back_populates="delivery_order", cascade="all, delete-orphan")


# ── 3. 配送明細 ──────────────────────────────────────────

class DeliveryOrderItem(Base):
    """配送明細 — 每站一筆，含客戶、品項、簽收狀態"""
    __tablename__ = "delivery_order_items"

    id                = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    delivery_order_id = Column(UUID(as_uuid=True), ForeignKey("delivery_orders.id"), nullable=False)
    sales_order_id    = Column(UUID(as_uuid=True), ForeignKey("sales_orders.id"), nullable=True)
    daily_sale_id     = Column(UUID(as_uuid=True), ForeignKey("daily_sales.id"), nullable=True)
    customer_id       = Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False)
    lot_id            = Column(UUID(as_uuid=True), ForeignKey("inventory_lots.id"), nullable=True)
    quantity_kg       = Column(Numeric(10, 2), nullable=False)
    quantity_boxes    = Column(Integer, nullable=True)
    delivery_address  = Column(Text, nullable=True)
    delivery_sequence = Column(Integer, default=0)  # 配送順序
    status            = Column(String(20), nullable=False, default="pending")  # pending / delivered / rejected / partial
    delivered_at      = Column(DateTime, nullable=True)
    received_by       = Column(String(100), nullable=True)  # 簽收人
    signature_photo_url = Column(String(500), nullable=True)
    rejection_reason  = Column(Text, nullable=True)
    note              = Column(Text, nullable=True)
    created_at        = Column(DateTime, default=datetime.utcnow)

    # 關聯
    delivery_order = relationship("DeliveryOrder", back_populates="items")
    customer       = relationship("Customer", foreign_keys=[customer_id])
    lot            = relationship("InventoryLot", foreign_keys=[lot_id])


# ── 4. 配送憑證 ──────────────────────────────────────────

class DeliveryProof(Base):
    """配送憑證 — 簽收照片、簽名、文件"""
    __tablename__ = "delivery_proofs"

    id                      = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    delivery_order_item_id  = Column(UUID(as_uuid=True), ForeignKey("delivery_order_items.id"), nullable=False)
    proof_type              = Column(String(20), nullable=False)  # signature / photo / document
    file_url                = Column(String(500), nullable=False)
    note                    = Column(Text, nullable=True)
    created_at              = Column(DateTime, default=datetime.utcnow)

    # 關聯
    delivery_order_item = relationship("DeliveryOrderItem", foreign_keys=[delivery_order_item_id])


# ── 5. 出庫單 ────────────────────────────────────────────

OUTBOUND_STATUSES = ["draft", "approved", "picked", "shipped", "completed", "cancelled"]

OUTBOUND_STATUS_NEXT = {
    "draft":    "approved",
    "approved": "picked",
    "picked":   "shipped",
    "shipped":  "completed",
}


class OutboundOrder(Base):
    """出庫單 — 配送/移轉/報廢/樣品/退貨"""
    __tablename__ = "outbound_orders"

    id                = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    outbound_no       = Column(String(30), unique=True, nullable=False)  # OUT-YYYYMMDD-XXX
    outbound_type     = Column(String(20), nullable=False, default="delivery")  # delivery / transfer / scrap / sample / return
    delivery_order_id = Column(UUID(as_uuid=True), ForeignKey("delivery_orders.id"), nullable=True)
    warehouse_id      = Column(UUID(as_uuid=True), ForeignKey("warehouses.id"), nullable=True)
    approved_by       = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    status            = Column(String(20), nullable=False, default="draft")
    total_weight_kg   = Column(Numeric(10, 2), default=0)
    total_boxes       = Column(Integer, default=0)
    pick_started_at   = Column(DateTime, nullable=True)
    pick_completed_at = Column(DateTime, nullable=True)
    shipped_at        = Column(DateTime, nullable=True)
    note              = Column(Text, nullable=True)
    created_by        = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at        = Column(DateTime, default=datetime.utcnow)
    updated_at        = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 關聯
    delivery_order = relationship("DeliveryOrder", foreign_keys=[delivery_order_id])
    warehouse      = relationship("Warehouse", foreign_keys=[warehouse_id])
    approver       = relationship("User", foreign_keys=[approved_by])
    creator        = relationship("User", foreign_keys=[created_by])
    items          = relationship("OutboundOrderItem", back_populates="outbound_order", cascade="all, delete-orphan")


# ── 6. 出庫明細 ──────────────────────────────────────────

class OutboundOrderItem(Base):
    """出庫明細 — 每筆庫存批號一行"""
    __tablename__ = "outbound_order_items"

    id                 = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    outbound_order_id  = Column(UUID(as_uuid=True), ForeignKey("outbound_orders.id"), nullable=False)
    lot_id             = Column(UUID(as_uuid=True), ForeignKey("inventory_lots.id"), nullable=False)
    batch_id           = Column(UUID(as_uuid=True), ForeignKey("batches.id"), nullable=True)
    quantity_kg        = Column(Numeric(10, 2), nullable=False)
    quantity_boxes     = Column(Integer, nullable=True)
    actual_picked_kg   = Column(Numeric(10, 2), nullable=True)   # 實際揀貨量
    actual_picked_boxes = Column(Integer, nullable=True)
    location_id        = Column(UUID(as_uuid=True), ForeignKey("warehouse_locations.id"), nullable=True)
    picked_by          = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    picked_at          = Column(DateTime, nullable=True)
    status             = Column(String(20), nullable=False, default="pending")  # pending / picked / short
    created_at         = Column(DateTime, default=datetime.utcnow)

    # 關聯
    outbound_order = relationship("OutboundOrder", back_populates="items")
    lot            = relationship("InventoryLot", foreign_keys=[lot_id])
    batch          = relationship("Batch", foreign_keys=[batch_id])
    location       = relationship("WarehouseLocation", foreign_keys=[location_id])
    picker         = relationship("User", foreign_keys=[picked_by])
