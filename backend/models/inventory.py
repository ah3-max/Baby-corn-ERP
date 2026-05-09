"""
台灣庫存管理模型
Warehouse       - 倉庫
WarehouseLocation - 庫位
InventoryLot    - 庫存批次（每次入庫一筆）
InventoryTransaction - 庫存異動記錄
"""
import uuid
from datetime import datetime, date
from sqlalchemy import (
    Column, String, Text, ForeignKey, Numeric,
    Integer, DateTime, Date, Boolean
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from database import Base


class Warehouse(Base):
    """倉庫"""
    __tablename__ = "warehouses"

    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name       = Column(String(100), nullable=False)
    address    = Column(Text, nullable=True)
    notes      = Column(Text, nullable=True)
    is_active  = Column(Boolean, default=True, nullable=False)
    # ── B-06 冷鏈欄位 ──────────────────────────────────────────────────
    storage_type        = Column(String(20), nullable=True)       # frozen/chilled/ambient
    temperature_min     = Column(Numeric(5, 2), nullable=True)    # 最低儲存溫度 °C
    temperature_max     = Column(Numeric(5, 2), nullable=True)    # 最高儲存溫度 °C
    humidity_min        = Column(Numeric(5, 2), nullable=True)    # 最低濕度 %
    humidity_max        = Column(Numeric(5, 2), nullable=True)    # 最高濕度 %
    total_capacity_pallets = Column(Integer, nullable=True)       # 總托盤容量
    country_code        = Column(String(2), default="TW", nullable=False)  # 倉庫所在國家
    deleted_at = Column(DateTime, nullable=True)                           # 軟刪除時間
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    locations = relationship("WarehouseLocation", back_populates="warehouse", cascade="all, delete-orphan")
    lots      = relationship("InventoryLot", back_populates="warehouse")


class WarehouseLocation(Base):
    """庫位（倉庫內的具體位置）"""
    __tablename__ = "warehouse_locations"

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    warehouse_id = Column(UUID(as_uuid=True), ForeignKey("warehouses.id"), nullable=False)
    name         = Column(String(50), nullable=False)   # 例：A01、冷凍庫-1
    notes        = Column(Text, nullable=True)
    is_active    = Column(Boolean, default=True, nullable=False)
    created_at   = Column(DateTime, default=datetime.utcnow)

    warehouse = relationship("Warehouse", back_populates="locations")
    lots      = relationship("InventoryLot", back_populates="location")


class InventoryLot(Base):
    """
    庫存批次
    每次入庫對應一個 Lot，可追蹤 FIFO、庫齡、規格
    """
    __tablename__ = "inventory_lots"

    id                 = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lot_no             = Column(String(30), unique=True, nullable=False)     # LOT-20240101-001
    batch_id           = Column(UUID(as_uuid=True), ForeignKey("batches.id"), nullable=False)
    warehouse_id       = Column(UUID(as_uuid=True), ForeignKey("warehouses.id"), nullable=False)
    location_id        = Column(UUID(as_uuid=True), ForeignKey("warehouse_locations.id"), nullable=True)

    spec               = Column(String(50), nullable=True)    # 規格：A級/B級/冷藏/冷凍
    received_date      = Column(Date, nullable=False)         # 入庫日（FIFO 依此排序）

    initial_weight_kg  = Column(Numeric(10, 2), nullable=False)
    initial_boxes      = Column(Integer, nullable=True)

    current_weight_kg  = Column(Numeric(10, 2), nullable=False)
    current_boxes      = Column(Integer, nullable=True)

    shipped_weight_kg  = Column(Numeric(10, 2), default=0, nullable=False)
    shipped_boxes      = Column(Integer, default=0, nullable=True)

    scrapped_weight_kg = Column(Numeric(10, 2), default=0, nullable=False)

    # active / depleted / scrapped
    status             = Column(String(20), default="active", nullable=False)

    notes              = Column(Text, nullable=True)
    # ── Module K: 台灣進口入庫資訊 ────────────────────────────────────
    import_type            = Column(String(10), nullable=True)     # air / sea
    customs_declaration_no = Column(String(100), nullable=True)    # 報關號碼
    customs_clearance_date = Column(Date, nullable=True)           # 通關日期
    inspection_result      = Column(String(20), nullable=True)     # pass/fail/pending/exempted
    received_by            = Column(String(100), nullable=True)    # 入庫人員
    shipment_id            = Column(UUID(as_uuid=True), ForeignKey("shipments.id"), nullable=True)

    # ── 到港重量與報關費用 ──────────────────────────────────────────
    arrival_weight_kg      = Column(Numeric(10, 2), nullable=True)  # 實際到貨重量（與出口重量比對損耗）
    customs_fee_twd        = Column(Numeric(10, 2), nullable=True)  # 報關費（TWD）
    quarantine_fee_twd     = Column(Numeric(10, 2), nullable=True)  # 檢疫費（TWD）
    import_tax_twd         = Column(Numeric(10, 2), nullable=True)  # 關稅（TWD）
    cold_chain_fee_twd     = Column(Numeric(10, 2), nullable=True)  # 冷鏈物流費（TWD）
    tw_transport_fee_twd   = Column(Numeric(10, 2), nullable=True)  # 台灣內陸運費（TWD）
    # ── B-06 冷鏈到貨欄位 ─────────────────────────────────────────────
    actual_temp_on_arrival = Column(Numeric(5, 2), nullable=True)     # 到貨時實測溫度 °C
    humidity_on_arrival    = Column(Numeric(5, 2), nullable=True)     # 到貨時濕度 %
    expiry_date            = Column(Date, nullable=True)               # 有效期限
    quality_status         = Column(String(20), default="approved", nullable=True)  # approved/on_hold/rejected/quarantine

    created_by         = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    updated_by         = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)  # 最後更新者
    deleted_at         = Column(DateTime, nullable=True)                                     # 軟刪除時間
    created_at         = Column(DateTime, default=datetime.utcnow)
    updated_at         = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    batch     = relationship("Batch",             foreign_keys=[batch_id])
    warehouse = relationship("Warehouse",         back_populates="lots")
    location  = relationship("WarehouseLocation", back_populates="lots")
    shipment  = relationship("Shipment",          foreign_keys=[shipment_id])  # WP1-3：補齊 ORM 關聯
    creator   = relationship("User",              foreign_keys=[created_by])
    transactions = relationship("InventoryTransaction", back_populates="lot",
                                order_by="InventoryTransaction.created_at")


class InventoryTransaction(Base):
    """
    庫存異動記錄
    type: in（入庫）/ out（出庫）/ scrap（報廢）/ adjust（調整）
    """
    __tablename__ = "inventory_transactions"

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lot_id       = Column(UUID(as_uuid=True), ForeignKey("inventory_lots.id"), nullable=False)
    txn_type     = Column(String(10), nullable=False)   # in / out / scrap / adjust
    weight_kg    = Column(Numeric(10, 2), nullable=False)
    boxes        = Column(Integer, nullable=True)
    reference    = Column(String(100), nullable=True)   # 銷售單號、出貨單號等
    reason       = Column(Text, nullable=True)
    created_by   = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at   = Column(DateTime, default=datetime.utcnow)

    lot     = relationship("InventoryLot", back_populates="transactions")
    creator = relationship("User", foreign_keys=[created_by])
