"""
WP2：QC 品質管理強化模型

包含：
1. QCSamplingRule     — 抽樣規則（依批次大小決定抽樣比例）
2. QCInspection       — QC 檢驗主表（擴充版，取代舊 QCRecord 的新增場景）
3. QCPhoto            — QC 照片（每張獨立記錄）
4. QCScoreCard        — 品質評分卡（逐項打分）
5. ChannelQCStandard  — 通路品質標準
6. ProcessingStepLog  — 加工步驟記錄
7. TemperatureLog     — 溫度記錄（支援手動 + 未來 IoT）
8. FactoryAutomationLog — Phase 3 預留：工廠自動化記錄
9. ShelfLifePrediction  — Phase 3 預留：AI 保存期限預測
"""
import uuid
from datetime import datetime, date
from sqlalchemy import (
    Column, String, DateTime, Date, Text, ForeignKey, JSON,
    Numeric, Boolean, Integer, CheckConstraint, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from database import Base


# ── 1. 抽樣規則 ──────────────────────────────────────────────────────

class QCSamplingRule(Base):
    """抽樣規則 — 依批次重量區間決定抽樣比例與每箱開盒數"""
    __tablename__ = "qc_sampling_rules"

    id                = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rule_code         = Column(String(30), unique=True, nullable=False)
    product_type_id   = Column(UUID(as_uuid=True), ForeignKey("product_types.id"), nullable=True)
    batch_size_min_kg = Column(Numeric(10, 2), nullable=True)   # 批次最小重量
    batch_size_max_kg = Column(Numeric(10, 2), nullable=True)   # 批次最大重量
    sampling_pct      = Column(Numeric(5, 2), nullable=False)    # 抽樣比例 %（如 5.00 或 10.00）
    boxes_per_sample  = Column(Integer, default=1)               # 每箱開幾盒檢查
    description       = Column(Text, nullable=True)
    is_active         = Column(Boolean, default=True, nullable=False)
    created_at        = Column(DateTime, default=datetime.utcnow)
    updated_at        = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 關聯
    product_type = relationship("ProductType", foreign_keys=[product_type_id])


# ── 2. QC 檢驗主表 ──────────────────────────────────────────────────

INSPECTION_STAGES = [
    "factory_incoming",    # 泰國工廠進料檢驗
    "factory_processing",  # 工廠加工中檢驗
    "pre_packing",         # 包裝前檢驗
    "pre_export",          # 出口前檢驗
    "tw_arrival",          # 台灣到貨檢驗
    "tw_pre_delivery",     # 台灣出貨前檢驗
]

INSPECTION_RESULTS = ["pass", "fail", "conditional_pass"]
INSPECTION_GRADES = ["A", "B", "C", "D", "reject"]


class QCInspection(Base):
    """QC 檢驗主表 — 每次檢驗一筆記錄

    包含：抽樣統計、環境數據、綜合評分、缺陷統計、等級分佈、
    建議事項、農藥殘留等完整 QC 資訊。
    """
    __tablename__ = "qc_inspections"
    __table_args__ = (
        CheckConstraint(
            "overall_result IN ('pass','fail','conditional_pass')",
            name="ck_qc_inspections_result",
        ),
    )

    id                      = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    inspection_no           = Column(String(30), unique=True, nullable=False)  # QC-YYYYMMDD-XXX
    batch_id                = Column(UUID(as_uuid=True), ForeignKey("batches.id"), nullable=False)
    inspection_stage        = Column(String(30), nullable=False)  # factory_incoming / tw_arrival 等

    # 抽樣資訊
    sampling_rule_id        = Column(UUID(as_uuid=True), ForeignKey("qc_sampling_rules.id"), nullable=True)
    total_boxes_in_batch    = Column(Integer, nullable=True)      # 批次總箱數
    sampled_boxes           = Column(Integer, nullable=True)      # 抽樣箱數
    sampled_units           = Column(Integer, nullable=True)      # 抽樣盒數

    # 檢驗人員
    inspector_user_id       = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    inspector_name          = Column(String(100), nullable=False)
    inspection_datetime     = Column(DateTime, nullable=False, default=datetime.utcnow)

    # 環境條件
    environment_temp_c      = Column(Numeric(5, 2), nullable=True)    # 環境溫度 °C
    environment_humidity_pct = Column(Numeric(5, 2), nullable=True)   # 環境濕度 %

    # 綜合結果
    overall_result          = Column(String(20), nullable=False)       # pass / fail / conditional_pass
    overall_grade           = Column(String(10), nullable=True)        # A / B / C / D / reject
    overall_score           = Column(Numeric(5, 2), nullable=True)     # 0-100 綜合分數

    # 缺陷與等級統計（JSON）
    defect_summary          = Column(JSON, default=dict)   # {"black_head": 3, "pest_damage": 1, ...}
    grade_distribution      = Column(JSON, default=dict)   # {"A": 45, "B": 30, "C": 15, ...}

    # 建議事項
    recommendation          = Column(Text, nullable=True)  # QC 建議
    next_batch_notes        = Column(Text, nullable=True)  # 給下一批貨的注意事項

    # 農藥殘留
    pesticide_test_result   = Column(JSON, nullable=True)  # [{name, value_ppm, limit_ppm, pass}]

    # 審計
    created_by              = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at              = Column(DateTime, default=datetime.utcnow)
    updated_at              = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 關聯
    batch          = relationship("Batch", foreign_keys=[batch_id])
    sampling_rule  = relationship("QCSamplingRule", foreign_keys=[sampling_rule_id])
    inspector      = relationship("User", foreign_keys=[inspector_user_id])
    creator        = relationship("User", foreign_keys=[created_by])
    photos         = relationship("QCPhoto", back_populates="inspection", cascade="all, delete-orphan")
    score_cards    = relationship("QCScoreCard", back_populates="inspection", cascade="all, delete-orphan")


# ── 3. QC 照片 ──────────────────────────────────────────────────────

PHOTO_TYPES = [
    "overview",       # 整體概況
    "sample_box",     # 抽樣箱
    "sample_unit",    # 抽樣盒（單支）
    "defect",         # 缺陷特寫
    "environment",    # 環境照
    "label",          # 標籤照
    "thermometer",    # 溫度計照
]


class QCPhoto(Base):
    """QC 照片 — 每張照片獨立記錄，支援分類、箱盒編號、AI 分析預留"""
    __tablename__ = "qc_photos"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    inspection_id   = Column(UUID(as_uuid=True), ForeignKey("qc_inspections.id"), nullable=False)
    photo_type      = Column(String(20), nullable=False, default="overview")
    file_url        = Column(String(500), nullable=False)
    thumbnail_url   = Column(String(500), nullable=True)
    box_no          = Column(String(20), nullable=True)    # 第幾箱
    unit_no         = Column(String(20), nullable=True)    # 第幾盒
    caption         = Column(String(200), nullable=True)   # 照片說明
    ai_analysis     = Column(JSON, nullable=True)          # Phase 3 AI 分析結果預留
    created_at      = Column(DateTime, default=datetime.utcnow)

    # 關聯
    inspection = relationship("QCInspection", back_populates="photos")


# ── 4. 品質評分卡 ────────────────────────────────────────────────────

SCORE_ITEMS = [
    "ear_length",        # 穗長 (cm)
    "ear_diameter",      # 直徑 (mm)
    "husk_integrity",    # 外葉完整度 (1-5)
    "color_grade",       # 色澤等級 (1-5)
    "freshness",         # 新鮮度 (1-5)
    "cleanliness",       # 清潔度（尾巴、鬍鬚）(1-5)
    "pest_check",        # 蟲害檢查 (pass/fail)
    "black_head",        # 黑頭檢查 (pass/fail)
    "luster",            # 光澤度 (1-5)
    "moisture",          # 水分 (%)
    "tail_trimmed",      # 尾巴是否去淨 (pass/fail)
    "whisker_clean",     # 鬍鬚是否洗淨 (pass/fail)
    "weight_per_unit_g", # 單盒重量 (g)，目標 100-105g
    "size_grade",        # 尺寸分級 (S/M/L/XL)
]


class QCScoreCard(Base):
    """品質評分卡 — 每個檢驗項目逐項打分"""
    __tablename__ = "qc_score_cards"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    inspection_id   = Column(UUID(as_uuid=True), ForeignKey("qc_inspections.id"), nullable=False)
    score_item      = Column(String(30), nullable=False)     # ear_length / pest_check 等
    score_value     = Column(Numeric(10, 4), nullable=True)  # 數值型分數或測量值
    score_text      = Column(String(50), nullable=True)      # 文字型（如 pass/fail, S/M/L）
    is_pass         = Column(Boolean, nullable=True)         # 此項是否合格
    weight          = Column(Numeric(5, 2), default=1)       # 該項目在綜合評分中的權重
    ai_score        = Column(JSON, nullable=True)            # Phase 3 AI 打分結果預留
    note            = Column(String(200), nullable=True)
    created_at      = Column(DateTime, default=datetime.utcnow)

    # 關聯
    inspection = relationship("QCInspection", back_populates="score_cards")


# ── 5. 通路品質標準 ──────────────────────────────────────────────────

class ChannelQCStandard(Base):
    """通路品質標準 — 定義每個通路/客戶接受的品質等級與價格區間"""
    __tablename__ = "channel_qc_standards"

    id                = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    standard_code     = Column(String(30), unique=True, nullable=False)
    channel_type      = Column(String(20), nullable=False)  # chain_store / distributor / wholesaler / restaurant / consignee
    customer_id       = Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=True)  # 可綁定特定客戶
    product_type_id   = Column(UUID(as_uuid=True), ForeignKey("product_types.id"), nullable=True)
    grade_requirements = Column(JSON, default=dict)  # {"min_grade":"B","max_defect_pct":5,"min_score":75,...}
    pricing_tier      = Column(JSON, default=dict)   # {"A":{"min":85,"max":120},"B":{"min":60,"max":85},...}
    description       = Column(Text, nullable=True)
    is_active         = Column(Boolean, default=True, nullable=False)
    created_at        = Column(DateTime, default=datetime.utcnow)
    updated_at        = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 關聯
    customer     = relationship("Customer", foreign_keys=[customer_id])
    product_type = relationship("ProductType", foreign_keys=[product_type_id])


# ── 6. 加工步驟記錄 ──────────────────────────────────────────────────

class ProcessingStepLog(Base):
    """加工步驟記錄 — 對應 ProductType.processing_steps，記錄每步驟的時間、環境、重量"""
    __tablename__ = "processing_step_logs"

    id                    = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    processing_order_id   = Column(UUID(as_uuid=True), ForeignKey("processing_orders.id"), nullable=False)
    batch_id              = Column(UUID(as_uuid=True), ForeignKey("batches.id"), nullable=False)
    step_name             = Column(String(30), nullable=False)  # peeling / washing / grading / weighing / packing / cold_storage
    step_sequence         = Column(Integer, nullable=False, default=0)
    started_at            = Column(DateTime, nullable=True)
    completed_at          = Column(DateTime, nullable=True)
    operator_name         = Column(String(100), nullable=True)
    environment_temp_c    = Column(Numeric(5, 2), nullable=True)
    environment_humidity_pct = Column(Numeric(5, 2), nullable=True)
    input_weight_kg       = Column(Numeric(10, 2), nullable=True)
    output_weight_kg      = Column(Numeric(10, 2), nullable=True)
    waste_kg              = Column(Numeric(10, 2), nullable=True)
    notes                 = Column(Text, nullable=True)
    photos                = Column(JSON, default=list)  # [photo_url, ...]
    created_at            = Column(DateTime, default=datetime.utcnow)

    # 關聯
    processing_order = relationship("ProcessingOrder", foreign_keys=[processing_order_id])
    batch            = relationship("Batch", foreign_keys=[batch_id])


# ── 7. 溫度記錄 ──────────────────────────────────────────────────────

class TemperatureLog(Base):
    """溫度記錄 — 支援手動輸入和未來 IoT 自動上傳"""
    __tablename__ = "temperature_logs"

    id                    = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entity_type           = Column(String(30), nullable=False)  # batch / processing_order / shipment / inventory_lot / delivery_order
    entity_id             = Column(UUID(as_uuid=True), nullable=False)
    log_source            = Column(String(20), nullable=False, default="manual")  # manual / iot_sensor / thermometer_photo
    sensor_id             = Column(String(50), nullable=True)   # IoT 感測器 ID（Phase 3）
    temperature_c         = Column(Numeric(5, 2), nullable=False)
    humidity_pct          = Column(Numeric(5, 2), nullable=True)
    location_description  = Column(String(200), nullable=True)  # 如 "冷藏庫 A"
    is_alert              = Column(Boolean, default=False)
    alert_reason          = Column(String(200), nullable=True)
    recorded_at           = Column(DateTime, nullable=False, default=datetime.utcnow)
    created_at            = Column(DateTime, default=datetime.utcnow)


# ── 8. Phase 3 預留：工廠自動化記錄 ──────────────────────────────────

class FactoryAutomationLog(Base):
    """Phase 3 預留 — 工廠自動化機械手臂視覺辨識記錄"""
    __tablename__ = "factory_automation_logs"

    id                = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    batch_id          = Column(UUID(as_uuid=True), ForeignKey("batches.id"), nullable=False)
    station           = Column(String(20), nullable=False)  # vision_inspect / auto_trim / auto_sort / auto_weigh / auto_pack
    unit_id           = Column(String(50), nullable=True)   # 單支識別碼
    vision_result     = Column(JSON, nullable=True)         # {length_cm, diameter_mm, estimated_weight_g, color_score, ...}
    action_taken      = Column(String(20), nullable=True)   # pass / trim / reject / regrade
    box_id            = Column(String(50), nullable=True)   # 裝入哪個盒子
    box_weight_g      = Column(Numeric(6, 1), nullable=True)  # 盒子重量（目標 101-103g）
    processing_time_ms = Column(Integer, nullable=True)
    camera_image_url  = Column(String(500), nullable=True)
    recorded_at       = Column(DateTime, default=datetime.utcnow)

    # 關聯
    batch = relationship("Batch", foreign_keys=[batch_id])


# ── 9. Phase 3 預留：AI 保存期限預測 ─────────────────────────────────

class ShelfLifePrediction(Base):
    """Phase 3 預留 — AI 基於歷史數據預測保存期限"""
    __tablename__ = "shelf_life_predictions"

    id                    = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    batch_id              = Column(UUID(as_uuid=True), ForeignKey("batches.id"), nullable=False)
    predicted_days        = Column(Integer, nullable=False)
    confidence_pct        = Column(Numeric(5, 2), nullable=True)
    factors               = Column(JSON, nullable=True)  # {harvest_temp, transport_hours, qc_score, ...}
    suggested_sell_by_date = Column(Date, nullable=True)
    suggested_price_range = Column(JSON, nullable=True)  # {"min": 60, "max": 90}
    risk_level            = Column(String(10), nullable=True)  # low / medium / high
    created_at            = Column(DateTime, default=datetime.utcnow)

    # 關聯
    batch = relationship("Batch", foreign_keys=[batch_id])
