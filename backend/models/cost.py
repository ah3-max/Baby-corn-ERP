"""
成本管理模型 — Append-Only 帳本設計

三個核心 class：
1. CostEvent       — 成本事件帳本（Append-Only，不可 UPDATE/DELETE）
2. BatchCostSheet  — 批次成本彙總快取（由程式自動計算）
3. BatchCostSheetItem — 快取明細行
"""
import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, DateTime, Text, ForeignKey,
    Numeric, Boolean, Integer, CheckConstraint,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from database import Base


# ── 成本層級定義 ──────────────────────────────────────────────────────
COST_LAYERS = [
    "material",       # 原料採購
    "processing",     # 工廠加工
    "th_logistics",   # 泰國端物流
    "freight",        # 國際運費
    "tw_customs",     # 台灣報關/關稅
    "tw_logistics",   # 台灣端物流
    "market",         # 市場銷售費用
]


class CostEvent(Base):
    """成本事件帳本 — Append-Only

    所有成本變動皆以新增記錄方式寫入，不可 UPDATE / DELETE。
    沖銷時新增一筆 is_adjustment=True 的反向記錄，
    adjustment_ref 指向被沖銷的原始 CostEvent。
    """
    __tablename__ = "cost_events"
    __table_args__ = (
        # amount_thb 和 amount_twd 至少一個不為 NULL
        CheckConstraint(
            "amount_thb IS NOT NULL OR amount_twd IS NOT NULL",
            name="ck_cost_events_amount_not_null",
        ),
        # cost_layer 只允許指定值
        CheckConstraint(
            "cost_layer IN ('material','processing','th_logistics',"
            "'freight','tw_customs','tw_logistics','market')",
            name="ck_cost_events_layer",
        ),
    )

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    batch_id        = Column(UUID(as_uuid=True), ForeignKey("batches.id"), nullable=False)
    cost_layer      = Column(String(20), nullable=False)        # 成本層級
    cost_type       = Column(String(60), nullable=False)        # 成本類型代碼
    description_zh  = Column(String(200), nullable=True)        # 繁體中文描述
    description_en  = Column(String(200), nullable=True)        # 英文描述
    description_th  = Column(String(200), nullable=True)        # 泰文描述
    amount_thb      = Column(Numeric(12, 2), nullable=True)     # 泰銖金額
    amount_twd      = Column(Numeric(12, 2), nullable=True)     # 新台幣金額
    exchange_rate   = Column(Numeric(8, 4), nullable=True)      # 匯率（THB→TWD）
    quantity        = Column(Numeric(10, 3), nullable=True)     # 數量
    unit_cost       = Column(Numeric(10, 4), nullable=True)     # 單價
    unit_label      = Column(String(20), nullable=True)         # 單位標籤（kg/箱/次）
    is_adjustment   = Column(Boolean, default=False, nullable=False)  # 是否為沖銷記錄
    adjustment_ref  = Column(
        UUID(as_uuid=True),
        ForeignKey("cost_events.id"),
        nullable=True,
    )  # 指向被沖銷的原始記錄
    recorded_at     = Column(DateTime, default=datetime.utcnow, nullable=False)
    recorded_by     = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    notes           = Column(Text, nullable=True)

    # 關聯
    batch               = relationship("Batch", foreign_keys=[batch_id])
    recorder            = relationship("User", foreign_keys=[recorded_by])
    original_event      = relationship("CostEvent", remote_side=[id], foreign_keys=[adjustment_ref])


class BatchCostSheet(Base):
    """批次成本彙總快取 — 由程式自動計算，使用者不直接寫入

    每個批次只有一筆快取記錄（UNIQUE batch_id），
    當有新的 CostEvent 寫入時由後端重新計算。
    """
    __tablename__ = "batch_cost_sheets"
    __table_args__ = (
        UniqueConstraint("batch_id", name="uq_batch_cost_sheets_batch_id"),
    )

    id                      = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    batch_id                = Column(UUID(as_uuid=True), ForeignKey("batches.id"), nullable=False)

    # 七層成本彙總（統一轉換為 TWD）
    layer1_material_twd     = Column(Numeric(14, 2), default=0)
    layer2_processing_twd   = Column(Numeric(14, 2), default=0)
    layer3_th_logistics_twd = Column(Numeric(14, 2), default=0)
    layer4_freight_twd      = Column(Numeric(14, 2), default=0)
    layer5_tw_customs_twd   = Column(Numeric(14, 2), default=0)
    layer6_tw_logistics_twd = Column(Numeric(14, 2), default=0)
    layer7_market_twd       = Column(Numeric(14, 2), default=0)

    # 成本彙總
    total_cost_twd          = Column(Numeric(14, 2), default=0)   # 總成本（TWD）
    weight_kg               = Column(Numeric(10, 3), nullable=True)  # 批次重量
    cost_per_kg_twd         = Column(Numeric(10, 4), nullable=True)  # 每公斤成本

    # 收入彙總
    total_revenue_twd       = Column(Numeric(14, 2), default=0)   # 總營收（TWD）
    total_sold_kg           = Column(Numeric(10, 3), nullable=True)  # 已售重量
    avg_sale_price_twd      = Column(Numeric(10, 4), nullable=True)  # 平均售價

    # 利潤
    profit_per_kg_twd       = Column(Numeric(10, 4), nullable=True)  # 每公斤利潤
    margin_pct              = Column(Numeric(6, 2), nullable=True)   # 毛利率 %

    # 計算用匯率與驗證
    exchange_rate           = Column(Numeric(8, 4), nullable=True)   # 計算時使用的匯率
    cost_event_count        = Column(Integer, default=0)             # 快速驗證用
    last_calculated_at      = Column(DateTime, nullable=True)        # 最後計算時間

    # 關聯
    batch = relationship("Batch", foreign_keys=[batch_id])
    items = relationship("BatchCostSheetItem", back_populates="cost_sheet", cascade="all, delete-orphan")


class BatchCostSheetItem(Base):
    """批次成本快取明細行

    對應 BatchCostSheet 的逐行明細，
    由程式自動從 CostEvent 計算產生。
    """
    __tablename__ = "batch_cost_sheet_items"

    id                    = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cost_sheet_id         = Column(UUID(as_uuid=True), ForeignKey("batch_cost_sheets.id"), nullable=False)
    batch_id              = Column(UUID(as_uuid=True), ForeignKey("batches.id"), nullable=False)
    cost_layer            = Column(String(20), nullable=False)
    cost_type             = Column(String(60), nullable=False)
    description_zh        = Column(String(200), nullable=True)
    description_en        = Column(String(200), nullable=True)
    description_th        = Column(String(200), nullable=True)
    amount_thb            = Column(Numeric(12, 2), nullable=True)
    amount_twd            = Column(Numeric(12, 2), nullable=True)
    exchange_rate         = Column(Numeric(8, 4), nullable=True)
    converted_twd         = Column(Numeric(14, 2), nullable=True)   # 統一換算後的 TWD 金額
    sort_order            = Column(Integer, default=0)               # 排序順序
    is_adjustment         = Column(Boolean, default=False)
    source_cost_event_id  = Column(UUID(as_uuid=True), ForeignKey("cost_events.id"), nullable=True)

    # 關聯
    cost_sheet  = relationship("BatchCostSheet", back_populates="items")
    batch       = relationship("Batch", foreign_keys=[batch_id])
    source_event = relationship("CostEvent", foreign_keys=[source_cost_event_id])
