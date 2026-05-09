"""
台灣客戶模型
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Date, Text, Boolean, ForeignKey, CheckConstraint, Numeric, Float, Integer
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.orm import relationship

from database import Base


class Customer(Base):
    """台灣銷售客戶"""
    __tablename__ = "customers"
    __table_args__ = (
        CheckConstraint(
            "customer_type IN ('wholesaler','retailer','consignee','agent','potential')",
            name="ck_customers_customer_type",
        ),
        CheckConstraint(
            "credit_status IN ('good','warning','blocked')",
            name="ck_customers_credit_status",
        ),
    )

    id                     = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code                   = Column(String(20), unique=True, nullable=True)      # 客戶代碼（如 C001）nullable 漸進遷移
    name                   = Column(String(200), nullable=False)
    customer_type          = Column(String(20), nullable=True)                   # 客戶類型（nullable 漸進遷移）
    contact_name           = Column(String(100), nullable=True)
    phone                  = Column(String(50), nullable=True)
    email                  = Column(String(200), nullable=True)
    region                 = Column(String(100), nullable=True)                  # 地區（縣市）
    market_code            = Column(String(10), nullable=True)                   # 市場代碼（TPE_M1, TPE_M2）
    address                = Column(Text, nullable=True)
    payment_terms          = Column(String(200), nullable=True)                  # 付款條件
    preferred_specs        = Column(JSON, default=list)                          # 常買規格
    credit_status          = Column(String(10), default="good", nullable=False)  # 信用狀態
    assigned_sales_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)  # 負責業務
    # WP3：CRM 擴展欄位
    channel_type           = Column(String(20), nullable=True)     # chain_store/distributor/wholesaler/restaurant/consignee/direct/th_supplier
    tier                   = Column(String(10), nullable=True)     # vip/a/b/c/potential
    credit_limit_twd       = Column(Numeric(14, 2), nullable=True)  # 信用額度（TWD）
    current_ar_balance_twd = Column(Numeric(14, 2), default=0)      # 目前應收餘額（快取）
    sales_team_id          = Column(UUID(as_uuid=True), ForeignKey("sales_teams.id"), nullable=True)
    # ── 全球化欄位（B-03）────────────────────────────────────────────────
    country_code           = Column(String(2), default="TW", nullable=False)   # ISO 3166-1 alpha-2（TW/TH/JP/SG...）
    tax_id                 = Column(String(50), nullable=True)                  # 統一編號 / Tax ID
    default_currency       = Column(String(3), default="TWD", nullable=False)  # 預設交易幣別
    website                = Column(String(200), nullable=True)                 # 公司網站
    # ── CRM 健康追蹤欄位（D-01）──────────────────────────────────────────
    dev_status             = Column(String(30), default="potential", nullable=True)
    # potential→contacted→visited→negotiating→trial→closed→stable_repurchase→dormant→churned
    grade                  = Column(String(5), nullable=True)                          # A/B/C/D（業績分級）
    health_score           = Column(Float, default=100.0, nullable=True)               # 0~100 健康分數（由 APScheduler 每日更新）
    health_level           = Column(String(10), default="GREEN", nullable=True)        # GREEN/YELLOW/ORANGE/RED
    health_updated_at      = Column(DateTime, nullable=True)                           # 健康分數最後更新時間
    last_order_date        = Column(Date, nullable=True)                               # 最後下單日期（快取）
    last_contact_date      = Column(Date, nullable=True)                               # 最後聯繫日期
    next_follow_up_date    = Column(Date, nullable=True)                               # 下次跟進日期
    is_follow_up           = Column(Boolean, default=True, nullable=False)             # 是否需要跟進
    is_key_account         = Column(Boolean, default=False, nullable=False)            # 是否為重點客戶
    visit_frequency_days   = Column(Integer, nullable=True)                            # 建議拜訪頻率（天）
    avg_order_interval     = Column(Float, nullable=True)                              # 平均下單間隔（天）
    lifetime_value         = Column(Numeric(14, 2), default=0, nullable=True)          # 累計消費金額（TWD）
    predicted_next_order   = Column(Date, nullable=True)                               # AI 預測下次下單日
    prediction_confidence  = Column(String(10), nullable=True)                         # HIGH/MEDIUM/LOW
    order_trend            = Column(String(10), nullable=True)                         # GROWING/DECLINING/STABLE
    # 流失追蹤
    churn_reason           = Column(String(200), nullable=True)                        # 流失原因
    churn_date             = Column(Date, nullable=True)                               # 流失日期
    churn_note             = Column(Text, nullable=True)                               # 流失備註
    # 國際貿易偏好
    default_incoterm       = Column(String(10), nullable=True)                         # 預設貿易條件
    default_payment_method = Column(String(30), nullable=True)                         # 預設付款方式
    note                   = Column(Text, nullable=True)
    is_active              = Column(Boolean, default=True, nullable=False)
    deleted_at             = Column(DateTime, nullable=True)                     # 軟刪除時間
    created_by             = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    updated_by             = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)   # 最後更新者
    created_at             = Column(DateTime, default=datetime.utcnow)
    updated_at             = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 關聯
    assigned_sales = relationship("User", foreign_keys=[assigned_sales_user_id])
    creator        = relationship("User", foreign_keys=[created_by])
    updater        = relationship("User", foreign_keys=[updated_by])
    sales_team     = relationship("SalesTeam", foreign_keys=[sales_team_id])
    sales_orders   = relationship("SalesOrder", back_populates="customer")
    payments       = relationship("PaymentRecord", back_populates="customer")
    contacts       = relationship("CustomerContact", back_populates="customer", cascade="all, delete-orphan")
    addresses      = relationship("CustomerAddress", back_populates="customer", cascade="all, delete-orphan")


# ─── D-02 客戶聯絡人 ─────────────────────────────────────────

class CustomerContact(Base):
    """客戶多聯絡人（一客戶可有多個聯絡人）"""
    __tablename__ = "customer_contacts"

    id                   = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id          = Column(UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False)
    contact_name         = Column(String(100), nullable=False)                     # 聯絡人姓名
    contact_title        = Column(String(100), nullable=True)                      # 職稱
    department           = Column(String(100), nullable=True)                      # 部門
    phone                = Column(String(30), nullable=True)                       # 公司電話
    mobile               = Column(String(30), nullable=True)                       # 手機
    email                = Column(String(200), nullable=True)                      # 電子信箱
    line_id              = Column(String(50), nullable=True)                       # LINE ID
    wechat_id            = Column(String(50), nullable=True)                       # WeChat ID
    is_primary           = Column(Boolean, default=False, nullable=False)          # 是否為主要聯絡人
    is_decision_maker    = Column(Boolean, default=False, nullable=False)          # 是否為決策者
    preferred_language   = Column(String(5), default="zh-TW")                     # 偏好語言
    notes                = Column(Text, nullable=True)
    is_active            = Column(Boolean, default=True, nullable=False)
    created_at           = Column(DateTime, default=datetime.utcnow)
    updated_at           = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    customer = relationship("Customer", back_populates="contacts")


# ─── D-03 客戶多地址 ─────────────────────────────────────────

class CustomerAddress(Base):
    """客戶多地址（帳單/送貨/倉庫）"""
    __tablename__ = "customer_addresses"

    id                   = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id          = Column(UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False)
    address_type         = Column(String(20), nullable=False, default="shipping")  # billing/shipping/warehouse
    address_line_1       = Column(String(200), nullable=False)                     # 地址第一行
    address_line_2       = Column(String(200), nullable=True)                      # 地址第二行
    city                 = Column(String(100), nullable=True)                      # 城市
    state                = Column(String(100), nullable=True)                      # 州/省/縣市
    postal_code          = Column(String(20), nullable=True)                       # 郵遞區號
    country_code         = Column(String(2), default="TW", nullable=False)         # 國家
    is_default           = Column(Boolean, default=False, nullable=False)          # 是否為預設地址
    special_instructions = Column(Text, nullable=True)                             # 特殊配送指示
    created_at           = Column(DateTime, default=datetime.utcnow)
    updated_at           = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    customer = relationship("Customer", back_populates="addresses")
