"""
QC 檢驗記錄模型
每個批次可有多筆 QC 記錄，記錄品管檢驗歷程。
支援多種檢查類型：到廠驗收、包裝前/後、出口前、農藥殘留。
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Numeric, Integer, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.orm import relationship

from database import Base

QC_RESULTS = ["pass", "fail", "conditional_pass"]
QC_GRADES  = ["A", "B", "C", "D"]

# QC 檢查類型
QC_INSPECTION_TYPES = [
    "factory_incoming",  # 到廠驗收
    "pre_packing",       # 包裝前檢查
    "post_packing",      # 包裝後檢查
    "pre_export",        # 出口前檢查
    "pesticide",         # 農藥殘留檢驗
]


class QCRecord(Base):
    """QC 檢驗記錄"""
    __tablename__ = "qc_records"
    __table_args__ = (
        CheckConstraint(
            "inspection_type IN ('factory_incoming','pre_packing',"
            "'post_packing','pre_export','pesticide')",
            name="ck_qc_records_inspection_type",
        ),
    )

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    batch_id         = Column(UUID(as_uuid=True), ForeignKey("batches.id"), nullable=False)
    inspection_type  = Column(String(30), nullable=True)                         # 檢查類型（nullable 漸進遷移）
    inspector_name   = Column(String(100), nullable=False)                       # 檢驗人員
    checked_at       = Column(DateTime, nullable=False, default=datetime.utcnow) # 檢驗時間
    result           = Column(String(20), nullable=False)                        # pass/fail/conditional_pass
    grade            = Column(String(5), nullable=True)                          # A/B/C/D
    weight_checked   = Column(Numeric(10, 2), nullable=True)                     # 抽查重量（kg）

    # ── 品質細項（JSON 存 ear_length_cm, diameter_mm, color_grade 等）──
    quality_data     = Column(JSON, default=dict)                                # 品質檢查細項
    defect_rate_pct  = Column(Numeric(5, 2), nullable=True)                      # 不良率 %

    # ── 農藥殘留 ──────────────────────────────────────────────────────
    pesticide_name   = Column(String(100), nullable=True)                        # 農藥名稱
    pesticide_value  = Column(Numeric(8, 4), nullable=True)                      # 檢測值（ppm）
    pesticide_limit  = Column(Numeric(8, 4), nullable=True)                      # 法規限值（ppm）

    # ── 照片 ──────────────────────────────────────────────────────────
    photo_count      = Column(Integer, default=0)                                # 關聯照片數

    notes            = Column(Text, nullable=True)                               # 備註
    # ── B-05 認證標準欄位 ─────────────────────────────────────────────
    certification_standard = Column(String(50), nullable=True)          # ISO22000/HACCP/BRC/IFS/ORGANIC
    heavy_metal_test       = Column(JSON, nullable=True)                 # 重金屬檢驗結果 JSON
    microbial_test         = Column(JSON, nullable=True)                 # 微生物檢驗結果 JSON

    created_by       = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    updated_by       = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    deleted_at       = Column(DateTime, nullable=True)
    created_at       = Column(DateTime, default=datetime.utcnow)
    updated_at       = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    batch   = relationship("Batch",  foreign_keys=[batch_id])
    creator = relationship("User",   foreign_keys=[created_by])
