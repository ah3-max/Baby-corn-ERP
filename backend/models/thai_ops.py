"""
泰國端物流與生產模型（H-02 ~ H-08）

涵蓋：
H-02  ContainerTemperatureLog — 貨櫃溫度紀錄
H-03  Vehicle                 — 車輛管理
H-04  VehicleMaintenance      — 車輛維修紀錄
H-05  DeliveryTrip            — 配送行程強化（新表補充 DeliveryOrder）
H-06  ReturnOrder / Item      — 退貨管理
H-07  ContractFarming         — 契作合約
H-08  SupplierEvaluation      — 供應商評鑑

注意：H-01（Shipment 海運強化欄位）已直接修改 models/shipment.py
"""
import uuid
from datetime import datetime, date
from sqlalchemy import (
    Column, String, Boolean, DateTime, Date, Text, Numeric,
    Integer, ForeignKey, CheckConstraint, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.orm import relationship

from database import Base


# ─── H-02 貨櫃溫度紀錄 ─────────────────────────────────────

class ContainerTemperatureLog(Base):
    """貨櫃溫度 / 濕度紀錄（IOT 或手動輸入）"""
    __tablename__ = "container_temperature_logs"
    __table_args__ = (
        CheckConstraint(
            "data_source IN ('iot','manual')",
            name="ck_container_temp_source",
        ),
    )

    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    container_no   = Column(String(50), nullable=False)                    # 貨櫃號碼
    shipment_id    = Column(UUID(as_uuid=True), ForeignKey("shipments.id"), nullable=True)

    recorded_at    = Column(DateTime, nullable=False)                      # 紀錄時間
    temperature_c  = Column(Numeric(5, 2), nullable=False)                 # 溫度（℃）
    humidity_pct   = Column(Numeric(5, 2), nullable=True)                  # 濕度（%）
    location_gps   = Column(String(100), nullable=True)                    # GPS 座標 "lat,lon"
    data_source    = Column(String(10), nullable=False, default="manual")  # iot/manual
    is_alarm       = Column(Boolean, default=False, nullable=False)        # 是否告警
    alarm_reason   = Column(String(200), nullable=True)                    # 告警原因

    created_at     = Column(DateTime, default=datetime.utcnow)

    # 關聯
    shipment = relationship("Shipment", foreign_keys=[shipment_id])


# ─── H-03 車輛管理 ─────────────────────────────────────────

class Vehicle(Base):
    """公司自有車輛（冷藏車/廂型車/機車）"""
    __tablename__ = "vehicles"
    __table_args__ = (
        CheckConstraint(
            "vehicle_type IN ('refrigerated_truck','van','motorcycle','pickup','other')",
            name="ck_vehicle_type",
        ),
    )

    id                 = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plate_no           = Column(String(20), unique=True, nullable=False)   # 車牌號碼
    vehicle_type       = Column(String(30), nullable=False)                # 車輛類型
    brand              = Column(String(50), nullable=True)                 # 廠牌
    model              = Column(String(50), nullable=True)                 # 型號
    year               = Column(Integer, nullable=True)                    # 出廠年份
    color              = Column(String(30), nullable=True)                 # 顏色
    max_weight_kg      = Column(Numeric(8, 2), nullable=True)              # 最大載重 kg
    max_volume_cbm     = Column(Numeric(6, 2), nullable=True)              # 最大容積 m³
    insurance_expiry   = Column(Date, nullable=True)                       # 保險到期日
    inspection_expiry  = Column(Date, nullable=True)                       # 定期檢驗到期日
    gps_device_id      = Column(String(100), nullable=True)                # GPS 設備 ID
    is_active          = Column(Boolean, default=True, nullable=False)
    notes              = Column(Text, nullable=True)
    deleted_at         = Column(DateTime, nullable=True)
    created_at         = Column(DateTime, default=datetime.utcnow)
    updated_at         = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 關聯
    maintenances = relationship("VehicleMaintenance", back_populates="vehicle")


# ─── H-04 車輛維修紀錄 ────────────────────────────────────

class VehicleMaintenance(Base):
    """車輛維修 / 保養紀錄"""
    __tablename__ = "vehicle_maintenances"
    __table_args__ = (
        CheckConstraint(
            "maintenance_type IN ('regular_service','repair','tire','inspection','insurance','other')",
            name="ck_vehicle_maintenance_type",
        ),
    )

    id                   = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    vehicle_id           = Column(UUID(as_uuid=True), ForeignKey("vehicles.id"), nullable=False)
    maintenance_type     = Column(String(30), nullable=False)              # 維修類型
    service_date         = Column(Date, nullable=False)                    # 服務日期
    next_service_date    = Column(Date, nullable=True)                     # 下次保養日期
    next_service_km      = Column(Integer, nullable=True)                  # 下次保養里程
    odometer_at_service  = Column(Integer, nullable=True)                  # 當時里程數
    vendor               = Column(String(200), nullable=True)              # 服務廠商
    invoice_no           = Column(String(100), nullable=True)              # 發票號碼
    cost                 = Column(Numeric(10, 2), nullable=True)           # 費用
    cost_currency        = Column(String(3), default="TWD")                # 費用幣別
    items                = Column(JSON, default=list)                      # 維修項目 [{item, cost}]
    photo_urls           = Column(JSON, default=list)                      # 照片 URL 清單
    notes                = Column(Text, nullable=True)
    created_by           = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at           = Column(DateTime, default=datetime.utcnow)
    updated_at           = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 關聯
    vehicle = relationship("Vehicle", back_populates="maintenances")
    creator = relationship("User", foreign_keys=[created_by])


# ─── H-05 配送行程（補充 DeliveryOrder）────────────────────

class DeliveryTrip(Base):
    """配送行程記錄（對應一個 DeliveryOrder，記錄司機整趟行程資訊）"""
    __tablename__ = "delivery_trips"

    id                 = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    trip_no            = Column(String(30), unique=True, nullable=False)    # TRIP-YYYYMMDD-XXX
    delivery_order_id  = Column(UUID(as_uuid=True), ForeignKey("delivery_orders.id"), nullable=True)
    vehicle_id         = Column(UUID(as_uuid=True), ForeignKey("vehicles.id"), nullable=True)
    driver_id          = Column(UUID(as_uuid=True), ForeignKey("drivers.id"), nullable=True)

    # 行程資訊
    departure_time     = Column(DateTime, nullable=True)                    # 出發時間
    return_time        = Column(DateTime, nullable=True)                    # 返回時間
    total_km           = Column(Numeric(8, 2), nullable=True)               # 總里程數
    total_hours        = Column(Numeric(5, 2), nullable=True)               # 總行程時數
    actual_stops       = Column(Integer, nullable=True)                     # 實際送達站數
    delivered_count    = Column(Integer, default=0)                         # 成功配送筆數
    failed_count       = Column(Integer, default=0)                         # 失敗配送筆數
    is_empty_return    = Column(Boolean, default=False)                     # 空車回程
    load_rate          = Column(Numeric(5, 2), nullable=True)               # 車輛裝載率 %
    route_stops        = Column(JSON, default=list)                         # 路線站點 [{address, seq, status}]

    # 費用
    total_fuel_cost    = Column(Numeric(10, 2), nullable=True)              # 油費（TWD）
    toll_fee           = Column(Numeric(10, 2), nullable=True)              # 過路費（TWD）
    driver_allowance   = Column(Numeric(10, 2), nullable=True)              # 司機補貼（TWD）
    other_cost         = Column(Numeric(10, 2), nullable=True)              # 其他費用（TWD）
    total_trip_cost    = Column(Numeric(12, 2), nullable=True)              # 本趟總費用（TWD）

    notes              = Column(Text, nullable=True)
    created_by         = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    deleted_at         = Column(DateTime, nullable=True)
    created_at         = Column(DateTime, default=datetime.utcnow)
    updated_at         = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 關聯
    vehicle        = relationship("Vehicle", foreign_keys=[vehicle_id])
    driver         = relationship("Driver", foreign_keys=[driver_id])
    creator        = relationship("User", foreign_keys=[created_by])


# ─── H-06 退貨管理 ────────────────────────────────────────

class ReturnOrder(Base):
    """退貨單"""
    __tablename__ = "return_orders"
    __table_args__ = (
        CheckConstraint(
            "return_type IN ('return','exchange','partial')",
            name="ck_return_type",
        ),
        CheckConstraint(
            "status IN ('pending','approved','receiving','received','inspecting','completed','rejected')",
            name="ck_return_status",
        ),
        CheckConstraint(
            "refund_status IN ('pending','refunded','deducted','na')",
            name="ck_refund_status",
        ),
        CheckConstraint(
            "responsibility IN ('company','customer','logistics','unknown')",
            name="ck_return_responsibility",
        ),
    )

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    return_no        = Column(String(30), unique=True, nullable=False)    # RT-YYYYMMDD-XXX
    sales_order_id   = Column(UUID(as_uuid=True), ForeignKey("sales_orders.id"), nullable=True)
    customer_id      = Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False)
    warehouse_id     = Column(UUID(as_uuid=True), ForeignKey("warehouses.id"), nullable=True)

    return_type      = Column(String(20), nullable=False, default="return")  # return/exchange/partial
    reason           = Column(Text, nullable=True)                          # 退貨原因
    disposal_method  = Column(String(50), nullable=True)                    # 處置方式（rework/destroy/resell）
    responsibility   = Column(String(20), nullable=True, default="unknown") # 責任歸屬

    status           = Column(String(20), nullable=False, default="pending")
    request_date     = Column(Date, nullable=False, default=date.today)
    approved_at      = Column(DateTime, nullable=True)
    received_date    = Column(Date, nullable=True)

    refund_amount    = Column(Numeric(12, 2), nullable=True)                # 退款金額
    refund_currency  = Column(String(3), default="TWD")
    refund_status    = Column(String(20), nullable=False, default="na")

    approved_by      = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_by       = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    deleted_at       = Column(DateTime, nullable=True)
    created_at       = Column(DateTime, default=datetime.utcnow)
    updated_at       = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 關聯
    customer     = relationship("Customer", foreign_keys=[customer_id])
    approver     = relationship("User", foreign_keys=[approved_by])
    creator      = relationship("User", foreign_keys=[created_by])
    items        = relationship("ReturnOrderItem", back_populates="return_order", cascade="all, delete-orphan")


class ReturnOrderItem(Base):
    """退貨單明細"""
    __tablename__ = "return_order_items"

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    return_order_id  = Column(UUID(as_uuid=True), ForeignKey("return_orders.id"), nullable=False)
    product_type_id  = Column(UUID(as_uuid=True), ForeignKey("product_types.id"), nullable=True)
    lot_id           = Column(UUID(as_uuid=True), ForeignKey("inventory_lots.id"), nullable=True)

    qty_returned_kg  = Column(Numeric(10, 2), nullable=False)              # 退回數量 kg
    qty_accepted_kg  = Column(Numeric(10, 2), nullable=True)               # 驗收合格數量 kg
    return_reason    = Column(Text, nullable=True)                         # 退貨原因（明細）
    quality_notes    = Column(Text, nullable=True)                         # 品質備註

    return_order = relationship("ReturnOrder", back_populates="items")


# ─── H-07 契作合約 ────────────────────────────────────────

class ContractFarming(Base):
    """契作合約（與農民/供應商的種植合約）"""
    __tablename__ = "contract_farmings"
    __table_args__ = (
        CheckConstraint(
            "farming_method IN ('conventional','organic','gap','other')",
            name="ck_farming_method",
        ),
        CheckConstraint(
            "status IN ('planned','active','harvesting','completed','cancelled')",
            name="ck_contract_farming_status",
        ),
    )

    id                     = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    supplier_id            = Column(UUID(as_uuid=True), ForeignKey("suppliers.id"), nullable=False)
    agreement_number       = Column(String(100), unique=True, nullable=False)    # 合約編號
    farm_id                = Column(String(100), nullable=True)                  # 農場 ID / 地段號碼

    # 農業資訊
    crop_type              = Column(String(100), nullable=False, default="baby_corn")  # 作物種類
    planting_area_rai      = Column(Numeric(10, 2), nullable=True)               # 種植面積（萊）
    expected_yield_kg      = Column(Numeric(12, 2), nullable=True)               # 預計產量 kg
    seed_variety           = Column(String(100), nullable=True)                  # 種子品種
    farming_method         = Column(String(20), nullable=False, default="conventional")

    # 合約條件
    guaranteed_price_per_kg = Column(Numeric(8, 4), nullable=True)               # 保證收購價（/kg）
    price_currency         = Column(String(3), default="THB")

    # 時程
    planting_date          = Column(Date, nullable=True)                         # 種植日
    expected_harvest_date  = Column(Date, nullable=True)                         # 預計採收日
    actual_harvest_date    = Column(Date, nullable=True)                         # 實際採收日

    status                 = Column(String(20), nullable=False, default="planned")
    notes                  = Column(Text, nullable=True)
    created_by             = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    deleted_at             = Column(DateTime, nullable=True)
    created_at             = Column(DateTime, default=datetime.utcnow)
    updated_at             = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 關聯
    supplier = relationship("Supplier", foreign_keys=[supplier_id])
    creator  = relationship("User", foreign_keys=[created_by])


# ─── H-08 供應商評鑑 ──────────────────────────────────────

class SupplierEvaluation(Base):
    """供應商定期評鑑"""
    __tablename__ = "supplier_evaluations"
    __table_args__ = (
        CheckConstraint(
            "tier_recommendation IN ('A','B','C','D')",
            name="ck_supplier_eval_tier",
        ),
    )

    id                      = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    supplier_id             = Column(UUID(as_uuid=True), ForeignKey("suppliers.id"), nullable=False)

    # 評鑑期間
    evaluation_period_start = Column(Date, nullable=False)                        # 評鑑期間開始
    evaluation_period_end   = Column(Date, nullable=False)                        # 評鑑期間結束
    evaluation_date         = Column(Date, nullable=False, default=date.today)    # 評鑑日期

    # 評分（0~100）
    quality_score           = Column(Numeric(5, 2), nullable=True)                # 品質分數
    delivery_score          = Column(Numeric(5, 2), nullable=True)                # 交期分數
    price_score             = Column(Numeric(5, 2), nullable=True)                # 價格競爭力分數
    service_score           = Column(Numeric(5, 2), nullable=True)                # 服務配合度分數
    overall_score           = Column(Numeric(5, 2), nullable=True)                # 綜合分數

    tier_recommendation     = Column(String(1), nullable=True)                    # A/B/C/D 等級
    comments                = Column(Text, nullable=True)                         # 評鑑意見

    evaluator_id            = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at              = Column(DateTime, default=datetime.utcnow)
    updated_at              = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 關聯
    supplier  = relationship("Supplier", foreign_keys=[supplier_id])
    evaluator = relationship("User", foreign_keys=[evaluator_id])
