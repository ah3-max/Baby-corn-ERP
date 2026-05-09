"""
合約、公告、行事曆、會議、客訴、品質追溯模型（J/K/L 段）

涵蓋：
J-02  Contract / ContractPaySchedule / ContractRenewal — 合約管理
K-01  Announcement         — 公告
K-02  BusinessEvent        — 公司行事曆
K-03  PromoCalendar        — 大檔期行事曆
K-04  MeetingRecord        — 會議紀錄（含 K-06 AI 欄位）
K-05  MeetingActionItem    — 會議待辦事項
L-01  CustomerComplaint    — 客訴管理
L-03  PesticideResidueTest / PesticideResidueTestItem — 農藥殘留
"""
import uuid
from datetime import datetime, date
from sqlalchemy import (
    Column, String, Boolean, DateTime, Date, Text, Numeric,
    Integer, ForeignKey, CheckConstraint, UniqueConstraint, Time, Index,
)
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.orm import relationship

from database import Base


# ─── J-02 合約管理 ────────────────────────────────────────

class Contract(Base):
    """合約主表"""
    __tablename__ = "contracts"
    __table_args__ = (
        CheckConstraint(
            "contract_type IN ('sales','purchase','service','lease','nda','other')",
            name="ck_contract_type",
        ),
        CheckConstraint(
            "status IN ('draft','active','expired','terminated','renewed')",
            name="ck_contract_status",
        ),
        Index("ix_contracts_status_end", "status", "effective_to"),
    )

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    contract_no      = Column(String(50), unique=True, nullable=False)     # CT-YYYYMMDD-XXX
    title            = Column(String(300), nullable=False)                  # 合約名稱
    contract_type    = Column(String(20), nullable=False)                   # 合約類型
    status           = Column(String(20), nullable=False, default="draft")

    # 簽約對象
    customer_id      = Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=True)
    supplier_id      = Column(UUID(as_uuid=True), ForeignKey("suppliers.id"), nullable=True)

    # 合約期間
    signed_at        = Column(Date, nullable=True)                          # 簽約日期
    effective_from   = Column(Date, nullable=True)                          # 生效日
    effective_to     = Column(Date, nullable=True)                          # 到期日

    # 金融條件
    total_value      = Column(Numeric(16, 2), nullable=True)                # 合約總金額
    currency         = Column(String(3), default="TWD")
    payment_terms    = Column(Text, nullable=True)                          # 付款條件

    # 自動續約
    auto_renew       = Column(Boolean, default=False, nullable=False)       # 是否自動續約
    reminder_days    = Column(Integer, default=30)                          # 到期前幾天提醒

    attachment_url   = Column(String(500), nullable=True)                   # 合約掃描檔

    created_by       = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    deleted_at       = Column(DateTime, nullable=True)
    created_at       = Column(DateTime, default=datetime.utcnow)
    updated_at       = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 關聯
    customer        = relationship("Customer", foreign_keys=[customer_id])
    supplier        = relationship("Supplier", foreign_keys=[supplier_id])
    creator         = relationship("User", foreign_keys=[created_by])
    pay_schedules   = relationship("ContractPaySchedule", back_populates="contract", cascade="all, delete-orphan")
    renewals        = relationship("ContractRenewal", back_populates="contract")


class ContractPaySchedule(Base):
    """合約付款排程"""
    __tablename__ = "contract_pay_schedules"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    contract_id = Column(UUID(as_uuid=True), ForeignKey("contracts.id"), nullable=False)
    due_date    = Column(Date, nullable=False)
    amount      = Column(Numeric(14, 2), nullable=False)
    description = Column(String(200), nullable=True)
    is_paid     = Column(Boolean, default=False, nullable=False)
    paid_at     = Column(DateTime, nullable=True)

    contract = relationship("Contract", back_populates="pay_schedules")


class ContractRenewal(Base):
    """合約續約紀錄"""
    __tablename__ = "contract_renewals"

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    contract_id      = Column(UUID(as_uuid=True), ForeignKey("contracts.id"), nullable=False)
    renewed_at       = Column(Date, nullable=False, default=date.today)
    new_effective_to = Column(Date, nullable=False)
    notes            = Column(Text, nullable=True)
    created_by       = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at       = Column(DateTime, default=datetime.utcnow)

    contract = relationship("Contract", back_populates="renewals")
    creator  = relationship("User", foreign_keys=[created_by])


# ─── K-01 公告 ────────────────────────────────────────────

class Announcement(Base):
    """公司公告管理"""
    __tablename__ = "announcements"
    __table_args__ = (
        CheckConstraint(
            "category IN ('general','policy','it','hr','urgent','safety','other')",
            name="ck_announcement_category",
        ),
        CheckConstraint(
            "priority IN ('low','normal','high','urgent')",
            name="ck_announcement_priority",
        ),
    )

    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title          = Column(String(300), nullable=False)                    # 公告標題
    content        = Column(Text, nullable=False)                           # 公告內容（Markdown）
    category       = Column(String(20), nullable=False, default="general")
    priority       = Column(String(10), nullable=False, default="normal")
    is_pinned      = Column(Boolean, default=False, nullable=False)         # 是否置頂
    is_published   = Column(Boolean, default=False, nullable=False)         # 是否已發布
    published_at   = Column(DateTime, nullable=True)                        # 發布時間
    expires_at     = Column(DateTime, nullable=True)                        # 到期時間
    target_roles   = Column(JSON, default=list)                             # 推播角色清單
    attachment_url = Column(String(500), nullable=True)                     # 附件
    view_count     = Column(Integer, default=0)                             # 瀏覽次數

    created_by     = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    deleted_at     = Column(DateTime, nullable=True)
    created_at     = Column(DateTime, default=datetime.utcnow)
    updated_at     = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    creator = relationship("User", foreign_keys=[created_by])


# ─── K-02 公司行事曆 ──────────────────────────────────────

class BusinessEvent(Base):
    """公司行事曆（展覽/協會/通路促銷/例行行政）"""
    __tablename__ = "business_events"
    __table_args__ = (
        CheckConstraint(
            "event_type IN ('exhibition','association','channel_promo','weekly_admin','promo','training','other')",
            name="ck_business_event_type",
        ),
        CheckConstraint(
            "status IN ('planning','confirmed','in_progress','completed','cancelled')",
            name="ck_business_event_status",
        ),
    )

    id                  = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_no            = Column(String(30), unique=True, nullable=False)   # EV-YYYYMMDD-XXX
    title               = Column(String(300), nullable=False)
    event_type          = Column(String(30), nullable=False)
    status              = Column(String(20), nullable=False, default="planning")

    start_date          = Column(Date, nullable=False)
    end_date            = Column(Date, nullable=False)
    all_day             = Column(Boolean, default=True)                     # 是否全天事件

    location            = Column(String(200), nullable=True)
    venue               = Column(String(200), nullable=True)                # 場館

    owner_user_id       = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    attendee_user_ids   = Column(JSON, default=list)                        # 出席人員 user_id 清單

    budget              = Column(Numeric(12, 2), nullable=True)             # 預算
    actual_cost         = Column(Numeric(12, 2), nullable=True)             # 實際費用
    currency            = Column(String(3), default="TWD")

    prep_checklist      = Column(JSON, default=list)                        # 準備清單 [{task, done}]
    tags                = Column(JSON, default=list)                        # 標籤

    notes               = Column(Text, nullable=True)
    created_by          = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    deleted_at          = Column(DateTime, nullable=True)
    created_at          = Column(DateTime, default=datetime.utcnow)
    updated_at          = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 關聯
    owner   = relationship("User", foreign_keys=[owner_user_id])
    creator = relationship("User", foreign_keys=[created_by])


# ─── K-03 大檔期行事曆 ────────────────────────────────────

class PromoCalendar(Base):
    """通路促銷大檔期管理"""
    __tablename__ = "promo_calendars"
    __table_args__ = (
        CheckConstraint(
            "promo_tier IN ('national_major','quarterly','monthly','flash_sale','regular')",
            name="ck_promo_tier",
        ),
        CheckConstraint(
            "current_phase IN ('preparation','negotiation','execution','live','review','completed')",
            name="ck_promo_phase",
        ),
    )

    id                    = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    promo_code            = Column(String(50), unique=True, nullable=False)  # PROMO-2026-Q1-UNIMART
    promo_name            = Column(String(300), nullable=False)               # 檔期名稱
    promo_tier            = Column(String(30), nullable=False)                # 檔期等級
    year                  = Column(Integer, nullable=False)

    # 時程
    event_start_date      = Column(Date, nullable=False)                      # 檔期開始
    event_end_date        = Column(Date, nullable=False)                      # 檔期結束
    prep_start_date       = Column(Date, nullable=True)                       # 準備開始
    nego_start_date       = Column(Date, nullable=True)                       # 談判開始
    exec_start_date       = Column(Date, nullable=True)                       # 執行開始

    current_phase         = Column(String(20), nullable=False, default="preparation")

    # 提醒設定
    reminder_days         = Column(JSON, default=list)                        # [90, 60, 30, 14, 7]
    reminder_sent_at      = Column(JSON, default=dict)                        # {"90": "2026-01-01", ...}

    # 業績
    revenue_target        = Column(Numeric(16, 2), nullable=True)
    revenue_actual        = Column(Numeric(16, 2), nullable=True)

    # 通路 / 品項
    target_channels       = Column(JSON, default=list)                        # ["全聯", "家樂福"]
    featured_skus         = Column(JSON, default=list)                        # SKU 清單

    responsible_user_id   = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    notes                 = Column(Text, nullable=True)
    deleted_at            = Column(DateTime, nullable=True)
    created_at            = Column(DateTime, default=datetime.utcnow)
    updated_at            = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 關聯
    responsible = relationship("User", foreign_keys=[responsible_user_id])


# ─── K-04 會議紀錄（含 K-06 AI 欄位）────────────────────

class MeetingRecord(Base):
    """會議紀錄（含 AI 逐字稿欄位預留）"""
    __tablename__ = "meeting_records"
    __table_args__ = (
        CheckConstraint(
            "meeting_type IN ('weekly_admin','channel_negotiation','supplier_meeting','internal','board','other')",
            name="ck_meeting_type",
        ),
        CheckConstraint(
            "status IN ('scheduled','in_progress','completed','cancelled')",
            name="ck_meeting_status",
        ),
    )

    id                   = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    meeting_no           = Column(String(30), unique=True, nullable=False)  # MT-YYYYMMDD-XXX
    title                = Column(String(300), nullable=False)
    meeting_type         = Column(String(30), nullable=False)
    status               = Column(String(20), nullable=False, default="scheduled")

    meeting_date         = Column(Date, nullable=False)
    start_time           = Column(String(5), nullable=True)                 # HH:MM
    end_time             = Column(String(5), nullable=True)
    location             = Column(String(200), nullable=True)
    is_online            = Column(Boolean, default=False)
    meeting_url          = Column(String(500), nullable=True)

    # 關聯活動
    business_event_id    = Column(UUID(as_uuid=True), ForeignKey("business_events.id"), nullable=True)
    customer_id          = Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=True)

    # 人員
    facilitator_id       = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    attendees            = Column(JSON, default=list)                        # [{user_id, name}]
    external_attendees   = Column(Text, nullable=True)                      # 外部出席者（文字）

    # 內容
    agenda               = Column(Text, nullable=True)                      # 議程
    summary              = Column(Text, nullable=True)                      # 會議摘要
    decisions            = Column(Text, nullable=True)                      # 決議事項
    photo_urls           = Column(JSON, default=list)                       # 會議照片

    # K-06 AI 欄位預留
    audio_file_url       = Column(String(500), nullable=True)               # 錄音檔案
    audio_duration_sec   = Column(Integer, nullable=True)                   # 錄音時長（秒）
    transcript_text      = Column(Text, nullable=True)                      # 逐字稿
    transcript_status    = Column(String(20), nullable=True)                # pending/processing/completed/failed
    ai_summary           = Column(Text, nullable=True)                      # AI 生成摘要
    ai_action_items      = Column(JSON, nullable=True)                      # AI 提取待辦事項
    ai_processed_at      = Column(DateTime, nullable=True)

    created_by           = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    deleted_at           = Column(DateTime, nullable=True)
    created_at           = Column(DateTime, default=datetime.utcnow)
    updated_at           = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 關聯
    facilitator    = relationship("User", foreign_keys=[facilitator_id])
    creator        = relationship("User", foreign_keys=[created_by])
    business_event = relationship("BusinessEvent", foreign_keys=[business_event_id])
    customer       = relationship("Customer", foreign_keys=[customer_id])
    action_items   = relationship("MeetingActionItem", back_populates="meeting", cascade="all, delete-orphan")


# ─── K-05 會議待辦事項 ────────────────────────────────────

class MeetingActionItem(Base):
    """會議決議待辦事項"""
    __tablename__ = "meeting_action_items"
    __table_args__ = (
        CheckConstraint(
            "status IN ('open','in_progress','done','cancelled')",
            name="ck_action_item_status",
        ),
        CheckConstraint(
            "priority IN ('low','medium','high','urgent')",
            name="ck_action_item_priority",
        ),
    )

    id                  = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    meeting_record_id   = Column(UUID(as_uuid=True), ForeignKey("meeting_records.id"), nullable=False)
    action_title        = Column(String(300), nullable=False)               # 待辦事項標題
    action_description  = Column(Text, nullable=True)                       # 詳細說明
    owner_user_id       = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    due_date            = Column(Date, nullable=True)
    status              = Column(String(20), nullable=False, default="open")
    priority            = Column(String(10), nullable=False, default="medium")
    completion_note     = Column(Text, nullable=True)
    completed_at        = Column(DateTime, nullable=True)
    created_at          = Column(DateTime, default=datetime.utcnow)
    updated_at          = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 關聯
    meeting = relationship("MeetingRecord", back_populates="action_items")
    owner   = relationship("User", foreign_keys=[owner_user_id])


# ─── L-01 客訴管理 ────────────────────────────────────────

class CustomerComplaint(Base):
    """客訴管理"""
    __tablename__ = "customer_complaints"
    __table_args__ = (
        CheckConstraint(
            "complaint_category IN ('quality','packaging','delivery','documentation','mislabeling','other')",
            name="ck_complaint_category",
        ),
        CheckConstraint(
            "severity IN ('critical','major','minor')",
            name="ck_complaint_severity",
        ),
        CheckConstraint(
            "status IN ('open','investigating','resolved','closed','rejected')",
            name="ck_complaint_status",
        ),
        CheckConstraint(
            "compensation_type IN ('credit_note','replacement','refund','discount','none')",
            name="ck_compensation_type",
        ),
    )

    id                     = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    complaint_no           = Column(String(30), unique=True, nullable=False)  # CMP-YYYYMMDD-XXX
    customer_id            = Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False)
    sales_order_id         = Column(UUID(as_uuid=True), ForeignKey("sales_orders.id"), nullable=True)
    shipment_id            = Column(UUID(as_uuid=True), ForeignKey("shipments.id"), nullable=True)

    complaint_date         = Column(Date, nullable=False, default=date.today)
    product_type_id        = Column(UUID(as_uuid=True), ForeignKey("product_types.id"), nullable=True)
    lot_number             = Column(String(100), nullable=True)               # 批次號碼

    complaint_category     = Column(String(30), nullable=False)
    description            = Column(Text, nullable=False)                     # 客訴描述
    severity               = Column(String(10), nullable=False, default="minor")
    photos_url             = Column(JSON, default=list)                       # 相片 URL
    sample_retained        = Column(Boolean, default=False)                   # 是否保留樣品

    # 調查處理
    root_cause_analysis    = Column(Text, nullable=True)                      # 根本原因分析
    corrective_action      = Column(Text, nullable=True)                      # 矯正措施
    preventive_action      = Column(Text, nullable=True)                      # 預防措施

    # 賠償
    compensation_type      = Column(String(20), nullable=True, default="none")
    compensation_amount    = Column(Numeric(12, 2), nullable=True)
    compensation_currency  = Column(String(3), default="TWD")

    status                 = Column(String(20), nullable=False, default="open")
    responsible_person_id  = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    target_resolution_date = Column(Date, nullable=True)                      # 預計解決日
    actual_resolution_date = Column(Date, nullable=True)                      # 實際解決日

    created_by             = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    deleted_at             = Column(DateTime, nullable=True)
    created_at             = Column(DateTime, default=datetime.utcnow)
    updated_at             = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 關聯
    customer            = relationship("Customer", foreign_keys=[customer_id])
    responsible_person  = relationship("User", foreign_keys=[responsible_person_id])
    creator             = relationship("User", foreign_keys=[created_by])


# ─── L-03 農藥殘留檢驗 ────────────────────────────────────

class PesticideResidueTest(Base):
    """農藥殘留檢驗報告主表"""
    __tablename__ = "pesticide_residue_tests"
    __table_args__ = (
        CheckConstraint(
            "test_method IN ('GC-MS','LC-MS','GC-FID','ELISA','other')",
            name="ck_pesticide_test_method",
        ),
        CheckConstraint(
            "overall_result IN ('pass','fail','conditional')",
            name="ck_pesticide_result",
        ),
    )

    id                  = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    qc_inspection_id    = Column(UUID(as_uuid=True), ForeignKey("qc_records.id"), nullable=True)
    product_type_id     = Column(UUID(as_uuid=True), ForeignKey("product_types.id"), nullable=True)
    lot_number          = Column(String(100), nullable=True)                # 批次號碼

    test_date           = Column(Date, nullable=False)                      # 檢驗日期
    lab_name            = Column(String(200), nullable=False)               # 檢驗機構
    lab_report_number   = Column(String(100), unique=True, nullable=False)  # 報告號碼
    sample_origin       = Column(String(200), nullable=True)                # 樣品來源描述
    test_method         = Column(String(20), nullable=True)                 # 檢測方法
    overall_result      = Column(String(20), nullable=False, default="pass")
    report_url          = Column(String(500), nullable=True)                # 報告 PDF URL

    created_by          = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    deleted_at          = Column(DateTime, nullable=True)
    created_at          = Column(DateTime, default=datetime.utcnow)

    # 關聯
    creator = relationship("User", foreign_keys=[created_by])
    items   = relationship("PesticideResidueTestItem", back_populates="test", cascade="all, delete-orphan")


class PesticideResidueTestItem(Base):
    """農藥殘留檢驗項目明細"""
    __tablename__ = "pesticide_residue_test_items"
    __table_args__ = (
        CheckConstraint(
            "result IN ('not_detected','within_limit','exceeded')",
            name="ck_pesticide_item_result",
        ),
    )

    id                   = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    test_id              = Column(UUID(as_uuid=True), ForeignKey("pesticide_residue_tests.id"), nullable=False)
    pesticide_name       = Column(String(100), nullable=False)              # 農藥名稱（中文）
    pesticide_name_en    = Column(String(100), nullable=True)               # 農藥名稱（英文）
    cas_number           = Column(String(50), nullable=True)                # CAS 登錄號
    detected_value       = Column(Numeric(10, 6), nullable=True)            # 檢出值
    detected_unit        = Column(String(20), default="mg/kg")              # 單位
    detection_limit      = Column(Numeric(10, 6), nullable=True)            # 偵測極限（LOD）
    quantification_limit = Column(Numeric(10, 6), nullable=True)            # 定量極限（LOQ）
    mrls                 = Column(Numeric(10, 6), nullable=True)            # 最高殘留限量（MRLs）
    result               = Column(String(20), nullable=False, default="not_detected")

    test = relationship("PesticideResidueTest", back_populates="items")
