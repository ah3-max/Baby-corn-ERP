"""
CRM 進階模型（E-04 ～ E-08、F-01 ～ F-07）

包含：
1. SalesTarget       — 業務 KPI 目標 + 實績
2. SalesDailyReport  — 業務日報
3. SalesOpportunity  — 銷售機會（商機）
4. FollowUpLog       — 跟進記錄
5. VisitRecord       — 拜訪紀錄
6. Quotation         — 報價單
7. SampleRequest     — 樣品申請
"""
import uuid
from datetime import datetime, date
from sqlalchemy import (
    Column, String, Boolean, DateTime, Date, Text, Numeric,
    Integer, ForeignKey, UniqueConstraint, CheckConstraint,
)
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.orm import relationship

from database import Base


# ─── E-04 業務 KPI 目標 ──────────────────────────────────

class SalesTarget(Base):
    """業務月度 KPI 目標與實績追蹤"""
    __tablename__ = "sales_targets"
    __table_args__ = (
        UniqueConstraint("user_id", "target_month", name="uq_sales_target_user_month"),
    )

    id                   = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id              = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    target_month         = Column(Date, nullable=False)                          # 目標月份（每月第一天）

    # 目標值
    revenue_target       = Column(Numeric(14, 2), default=0)                     # 營收目標（TWD）
    order_target         = Column(Integer, default=0)                            # 訂單目標（筆數）
    visit_target         = Column(Integer, default=0)                            # 拜訪目標（次數）
    new_customer_target  = Column(Integer, default=0)                            # 新客戶目標（家數）

    # 實績（由觸發器或 APScheduler 自動更新）
    revenue_actual       = Column(Numeric(14, 2), default=0)
    order_actual         = Column(Integer, default=0)
    visit_actual         = Column(Integer, default=0)
    new_customer_actual  = Column(Integer, default=0)

    # 達成率（0~100）
    achievement_rate     = Column(Numeric(5, 2), default=0)                      # 綜合達成率

    # 里程碑通知追蹤（避免重複發送）
    milestone_50_sent    = Column(Boolean, default=False, nullable=False)
    milestone_80_sent    = Column(Boolean, default=False, nullable=False)
    milestone_100_sent   = Column(Boolean, default=False, nullable=False)

    created_at           = Column(DateTime, default=datetime.utcnow)
    updated_at           = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 關聯
    user = relationship("User", foreign_keys=[user_id])


# ─── E-05 業務日報 ──────────────────────────────────────

class SalesDailyReport(Base):
    """業務日報"""
    __tablename__ = "sales_daily_reports"
    __table_args__ = (
        UniqueConstraint("sales_rep_id", "report_date", name="uq_daily_report_rep_date"),
        CheckConstraint(
            "status IN ('draft','submitted')",
            name="ck_daily_report_status",
        ),
    )

    id                  = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sales_rep_id        = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    report_date         = Column(Date, nullable=False, default=date.today)

    # 今日數據
    visit_count         = Column(Integer, default=0)       # 拜訪數
    call_count          = Column(Integer, default=0)       # 電話數
    order_count         = Column(Integer, default=0)       # 成交數
    order_amount        = Column(Numeric(14, 2), default=0)  # 成交金額
    new_customer_count  = Column(Integer, default=0)       # 新客戶數
    quote_count         = Column(Integer, default=0)       # 報價數

    # 日報內容
    highlights          = Column(Text, nullable=True)      # 今日亮點
    obstacles           = Column(Text, nullable=True)      # 遇到的問題
    tomorrow_plan       = Column(Text, nullable=True)      # 明日計劃
    needs_help          = Column(Text, nullable=True)      # 需要支援

    status              = Column(String(10), nullable=False, default="draft")
    submitted_at        = Column(DateTime, nullable=True)

    # 主管審閱
    manager_comment     = Column(Text, nullable=True)
    reviewed_by         = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    reviewed_at         = Column(DateTime, nullable=True)

    created_at          = Column(DateTime, default=datetime.utcnow)
    updated_at          = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 關聯
    sales_rep = relationship("User", foreign_keys=[sales_rep_id])
    reviewer  = relationship("User", foreign_keys=[reviewed_by])


# ─── F-01 銷售機會 ───────────────────────────────────────

OPPORTUNITY_STAGES = ["lead", "qualified", "proposal", "negotiation", "won", "lost"]

class SalesOpportunity(Base):
    """銷售機會（商機）追蹤"""
    __tablename__ = "sales_opportunities"
    __table_args__ = (
        CheckConstraint(
            "stage IN ('lead','qualified','proposal','negotiation','won','lost')",
            name="ck_opportunity_stage",
        ),
    )

    id                  = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    opportunity_name    = Column(String(200), nullable=False)                   # 商機名稱
    customer_id         = Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=True)
    source              = Column(String(50), nullable=True)                     # trade_show/referral/website/cold_call/buyer_directory
    stage               = Column(String(20), nullable=False, default="lead")    # 階段
    probability_pct     = Column(Integer, default=0)                            # 成交機率 0~100
    expected_amount     = Column(Numeric(14, 2), nullable=True)                 # 預估金額
    expected_currency   = Column(String(3), default="TWD")                     # 幣別
    expected_close_date = Column(Date, nullable=True)                           # 預計成交日
    actual_close_date   = Column(Date, nullable=True)                           # 實際成交日
    product_interest    = Column(Text, nullable=True)                           # 感興趣的產品
    competitor_info     = Column(Text, nullable=True)                           # 競爭對手資訊
    loss_reason         = Column(Text, nullable=True)                           # 流失原因
    assigned_to         = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_by          = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    deleted_at          = Column(DateTime, nullable=True)
    created_at          = Column(DateTime, default=datetime.utcnow)
    updated_at          = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 關聯
    customer    = relationship("Customer", foreign_keys=[customer_id])
    assignee    = relationship("User", foreign_keys=[assigned_to])
    creator     = relationship("User", foreign_keys=[created_by])
    follow_logs = relationship("FollowUpLog", back_populates="opportunity")


# ─── F-02 跟進記錄 ───────────────────────────────────────

class FollowUpLog(Base):
    """統一跟進記錄（電話/LINE/Email/拜訪/展會）"""
    __tablename__ = "follow_up_logs"

    id                   = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id          = Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False)
    created_by           = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    log_date             = Column(Date, nullable=False, default=date.today)

    log_type             = Column(String(30), nullable=False)                   # call/line/email/meeting/first_visit/second_visit/delivery/expo/other
    method               = Column(String(20), nullable=True)                    # phone/line/email/onsite/video
    content              = Column(Text, nullable=False)                         # 跟進內容（必填）
    result               = Column(Text, nullable=True)                          # 跟進結果
    customer_reaction    = Column(String(20), nullable=True)                    # positive/neutral/negative/no_response

    next_follow_up_date  = Column(Date, nullable=True)                          # 下次跟進日
    next_action          = Column(Text, nullable=True)                          # 下次行動

    has_sample           = Column(Boolean, default=False)                       # 是否涉及樣品
    has_quote            = Column(Boolean, default=False)                       # 是否涉及報價
    has_order            = Column(Boolean, default=False)                       # 是否涉及訂單
    is_follow_up         = Column(Boolean, default=True)                        # 是否需要後續跟進

    opportunity_id       = Column(UUID(as_uuid=True), ForeignKey("sales_opportunities.id"), nullable=True)

    created_at           = Column(DateTime, default=datetime.utcnow)
    updated_at           = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 關聯
    customer    = relationship("Customer", foreign_keys=[customer_id])
    creator     = relationship("User", foreign_keys=[created_by])
    opportunity = relationship("SalesOpportunity", back_populates="follow_logs")


# ─── F-03 拜訪紀錄 ───────────────────────────────────────

class VisitRecord(Base):
    """客戶拜訪紀錄"""
    __tablename__ = "visit_records"

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id      = Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False)
    visited_by       = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    visit_date       = Column(Date, nullable=False, default=date.today)
    visit_method     = Column(String(20), nullable=True)                    # onsite/phone/video/other
    purpose          = Column(String(30), nullable=True)                    # first_visit/follow_up/service/training/signing
    participants     = Column(Text, nullable=True)                          # 出席人員
    content          = Column(Text, nullable=True)                          # 拜訪內容
    customer_needs   = Column(Text, nullable=True)                          # 客戶需求
    next_action      = Column(Text, nullable=True)                          # 後續行動
    next_visit_date  = Column(Date, nullable=True)                          # 下次拜訪日
    photo_urls       = Column(JSON, default=list)                           # 拜訪照片 URL 清單
    created_at       = Column(DateTime, default=datetime.utcnow)
    updated_at       = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 關聯
    customer  = relationship("Customer", foreign_keys=[customer_id])
    visitor   = relationship("User", foreign_keys=[visited_by])


# ─── F-04 報價單 ─────────────────────────────────────────

QUOTATION_STATUSES = ["draft", "sent", "accepted", "rejected", "expired", "converted"]

class Quotation(Base):
    """報價單"""
    __tablename__ = "quotations"
    __table_args__ = (
        CheckConstraint(
            "status IN ('draft','sent','accepted','rejected','expired','converted')",
            name="ck_quotation_status",
        ),
    )

    id                 = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    quotation_no       = Column(String(30), unique=True, nullable=False)       # QT-YYYYMMDD-XXX
    customer_id        = Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False)
    opportunity_id     = Column(UUID(as_uuid=True), ForeignKey("sales_opportunities.id"), nullable=True)
    quotation_date     = Column(Date, nullable=False, default=date.today)
    valid_until        = Column(Date, nullable=True)                            # 有效期限
    currency           = Column(String(3), default="TWD")                      # 幣別
    incoterm           = Column(String(10), nullable=True)                      # 貿易條件
    total_amount       = Column(Numeric(14, 2), default=0)                      # 總金額
    discount_rate      = Column(Numeric(5, 2), default=0)                       # 折扣率 %
    final_amount       = Column(Numeric(14, 2), default=0)                      # 折扣後金額
    payment_terms      = Column(String(200), nullable=True)                     # 付款條件
    delivery_terms     = Column(Text, nullable=True)                            # 交貨條件
    notes              = Column(Text, nullable=True)
    status             = Column(String(20), nullable=False, default="draft")
    sent_at            = Column(DateTime, nullable=True)
    converted_order_id = Column(UUID(as_uuid=True), ForeignKey("sales_orders.id"), nullable=True)  # 轉成銷售單
    created_by         = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    deleted_at         = Column(DateTime, nullable=True)
    created_at         = Column(DateTime, default=datetime.utcnow)
    updated_at         = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 關聯
    customer        = relationship("Customer", foreign_keys=[customer_id])
    opportunity     = relationship("SalesOpportunity", foreign_keys=[opportunity_id])
    converted_order = relationship("SalesOrder", foreign_keys=[converted_order_id])
    creator         = relationship("User", foreign_keys=[created_by])
    items           = relationship("QuotationItem", back_populates="quotation", cascade="all, delete-orphan")


class QuotationItem(Base):
    """報價單明細"""
    __tablename__ = "quotation_items"

    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    quotation_id   = Column(UUID(as_uuid=True), ForeignKey("quotations.id"), nullable=False)
    product_name   = Column(String(200), nullable=False)                        # 品名
    spec           = Column(String(100), nullable=True)                         # 規格
    quantity_kg    = Column(Numeric(10, 2), nullable=False)                     # 數量（kg）
    unit_price     = Column(Numeric(10, 4), nullable=False)                     # 單價
    amount         = Column(Numeric(12, 2), nullable=False)                     # 小計
    notes          = Column(Text, nullable=True)

    quotation = relationship("Quotation", back_populates="items")


# ─── F-05 樣品申請 ───────────────────────────────────────

class SampleRequest(Base):
    """樣品申請單"""
    __tablename__ = "sample_requests"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending','approved','sent','feedback_received','closed','rejected')",
            name="ck_sample_status",
        ),
    )

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    request_no       = Column(String(30), unique=True, nullable=False)           # SR-YYYYMMDD-XXX
    customer_id      = Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False)
    request_date     = Column(Date, nullable=False, default=date.today)
    product_name     = Column(String(200), nullable=False)                       # 樣品品名
    spec             = Column(String(100), nullable=True)                        # 規格
    quantity_kg      = Column(Numeric(6, 2), nullable=True)                      # 樣品重量
    purpose          = Column(Text, nullable=True)                               # 用途說明
    shipping_address = Column(Text, nullable=True)                               # 寄送地址
    courier_name     = Column(String(100), nullable=True)                        # 快遞業者
    tracking_no      = Column(String(100), nullable=True)                        # 追蹤號碼
    sent_date        = Column(Date, nullable=True)                               # 寄出日期
    feedback_date    = Column(Date, nullable=True)                               # 反饋日期
    feedback_result  = Column(Text, nullable=True)                               # 客戶反饋
    feedback_rating  = Column(Integer, nullable=True)                            # 評分 1-5
    status           = Column(String(30), nullable=False, default="pending")
    approved_by      = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_by       = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    deleted_at       = Column(DateTime, nullable=True)
    created_at       = Column(DateTime, default=datetime.utcnow)
    updated_at       = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 關聯
    customer  = relationship("Customer", foreign_keys=[customer_id])
    approver  = relationship("User", foreign_keys=[approved_by])
    creator   = relationship("User", foreign_keys=[created_by])


# ─── F-06 業務行程 ───────────────────────────────────────

class SalesSchedule(Base):
    """業務行程安排"""
    __tablename__ = "sales_schedules"
    __table_args__ = (
        CheckConstraint(
            "schedule_type IN ('first_visit','second_visit','payment_collect','delivery','expo','follow_up','meeting','other')",
            name="ck_schedule_type",
        ),
    )

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sales_rep_id     = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)    # 負責業務
    customer_id      = Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=True) # 相關客戶

    schedule_date    = Column(Date, nullable=False)                                           # 行程日期
    start_time       = Column(String(5), nullable=True)                                       # HH:MM
    end_time         = Column(String(5), nullable=True)                                       # HH:MM
    location         = Column(String(200), nullable=True)                                     # 地點

    schedule_type    = Column(String(30), nullable=False, default="other")                    # 行程類型
    title            = Column(String(200), nullable=False)                                    # 行程標題
    description      = Column(Text, nullable=True)                                            # 行程說明

    pre_reminder     = Column(Boolean, default=True)                                          # 是否提前提醒
    reminder_hours   = Column(Integer, default=24)                                            # 提醒時間（小時前）

    is_completed     = Column(Boolean, default=False, nullable=False)                         # 是否完成
    post_result      = Column(Text, nullable=True)                                            # 完成後的結果記錄

    created_by       = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    deleted_at       = Column(DateTime, nullable=True)
    created_at       = Column(DateTime, default=datetime.utcnow)
    updated_at       = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 關聯
    sales_rep = relationship("User", foreign_keys=[sales_rep_id])
    customer  = relationship("Customer", foreign_keys=[customer_id])
    creator   = relationship("User", foreign_keys=[created_by])


# ─── F-07 報價審批 ───────────────────────────────────────

class QuotationApproval(Base):
    """報價單審批流程"""
    __tablename__ = "quotation_approvals"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending','approved','rejected')",
            name="ck_quotation_approval_status",
        ),
        CheckConstraint(
            "approval_level IN (1, 2, 3)",
            name="ck_quotation_approval_level",
        ),
    )

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    quotation_id     = Column(UUID(as_uuid=True), ForeignKey("quotations.id"), nullable=False)
    approval_level   = Column(Integer, nullable=False)                            # 1=主管, 2=總監, 3=總經理
    approver_role    = Column(String(50), nullable=True)                          # 需要哪個角色審批
    approver_id      = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)  # 實際審批人

    trigger_reason   = Column(Text, nullable=True)                                # 觸發審批原因（如折扣超過30%）
    status           = Column(String(20), nullable=False, default="pending")
    comment          = Column(Text, nullable=True)                                # 審批意見
    decided_at       = Column(DateTime, nullable=True)                            # 決定時間

    created_at       = Column(DateTime, default=datetime.utcnow)
    updated_at       = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 關聯
    quotation = relationship("Quotation", foreign_keys=[quotation_id])
    approver  = relationship("User", foreign_keys=[approver_id])
