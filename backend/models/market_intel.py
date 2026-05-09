"""
全球市場情報模型（M 段）+ 全球定價引擎（N 段）

M-01  MarketPriceSource     — 市場資料來源管理
M-02  MarketPriceData       — 市場價格數據
M-03  MarketPriceAlert      — 價格異常警報
M-04  CompetitorProfile / CompetitorPrice — 競爭對手資訊
M-05  GlobalTradeStatistics — 全球貿易統計
M-06  WeatherAlert          — 天氣異常警報（WeatherForecast 強化另在 migration 處理）
M-07  FreightIndex / SupplyDemandIndicator — 運價指數 / 供需指標
M-08  GlobalBuyerDirectory  — 全球買家資料庫

N-01  PriceList / PriceListItem — 價目表
N-02  PricingRule          — 定價規則引擎
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


# ═══════════════════════════════════════════════════
# M-01 市場資料來源
# ═══════════════════════════════════════════════════

class MarketPriceSource(Base):
    """市場價格資料來源管理"""
    __tablename__ = "market_price_sources"
    __table_args__ = (
        CheckConstraint(
            "source_type IN ('government','exchange','private','association','custom')",
            name="ck_market_source_type",
        ),
    )

    id                 = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_code        = Column(String(50), unique=True, nullable=False)    # 來源代碼 e.g. TW_TAIPEI_WHOLESALE
    source_name        = Column(String(200), nullable=False)                # 來源名稱
    source_type        = Column(String(20), nullable=False)                 # 資料類型
    country_code       = Column(String(2), nullable=True)                   # 國家 ISO-3166
    url                = Column(String(500), nullable=True)                 # 資料來源網址
    api_endpoint       = Column(String(500), nullable=True)                 # API 端點
    data_format        = Column(String(50), nullable=True)                  # json/csv/html
    update_frequency   = Column(String(50), nullable=True)                  # daily/weekly/monthly
    is_active          = Column(Boolean, default=True, nullable=False)
    last_fetched_at    = Column(DateTime, nullable=True)                    # 最後抓取時間
    notes              = Column(Text, nullable=True)
    created_at         = Column(DateTime, default=datetime.utcnow)
    updated_at         = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    prices = relationship("MarketPriceData", back_populates="source")


# ═══════════════════════════════════════════════════
# M-02 市場價格數據
# ═══════════════════════════════════════════════════

class MarketPriceData(Base):
    """市場價格數據（批發市場、交易所）"""
    __tablename__ = "market_price_data"
    __table_args__ = (
        CheckConstraint(
            "price_trend IN ('up','down','stable','unknown')",
            name="ck_market_price_trend",
        ),
    )

    id                = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id         = Column(UUID(as_uuid=True), ForeignKey("market_price_sources.id"), nullable=True)
    price_date        = Column(Date, nullable=False)                        # 報價日期

    product_category  = Column(String(100), nullable=False)                 # 品類 e.g. "玉米筍"
    product_name      = Column(String(200), nullable=True)                  # 品名
    product_variety   = Column(String(100), nullable=True)                  # 品種
    market_name       = Column(String(200), nullable=True)                  # 市場名稱
    country_code      = Column(String(2), nullable=True)
    city              = Column(String(100), nullable=True)

    price_low         = Column(Numeric(10, 4), nullable=True)               # 最低價
    price_high        = Column(Numeric(10, 4), nullable=True)               # 最高價
    price_avg         = Column(Numeric(10, 4), nullable=True)               # 平均價
    price_modal       = Column(Numeric(10, 4), nullable=True)               # 眾數價（最多成交）
    price_currency    = Column(String(3), default="TWD")
    price_unit        = Column(String(30), nullable=True)                   # 元/kg、元/箱
    volume_traded     = Column(Numeric(14, 2), nullable=True)               # 成交量
    volume_unit       = Column(String(20), nullable=True)                   # kg/箱/噸
    price_trend       = Column(String(10), nullable=True, default="stable")

    created_at        = Column(DateTime, default=datetime.utcnow)

    # 關聯
    source = relationship("MarketPriceSource", back_populates="prices")


# ═══════════════════════════════════════════════════
# M-03 價格異常警報
# ═══════════════════════════════════════════════════

class MarketPriceAlert(Base):
    """市場價格異常警報"""
    __tablename__ = "market_price_alerts"
    __table_args__ = (
        CheckConstraint(
            "alert_type IN ('price_spike','price_drop','new_high','new_low','abnormal_volume')",
            name="ck_price_alert_type",
        ),
        CheckConstraint(
            "severity IN ('info','warning','critical')",
            name="ck_price_alert_severity",
        ),
    )

    id                  = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    alert_type          = Column(String(30), nullable=False)
    product_category    = Column(String(100), nullable=False)
    market_name         = Column(String(200), nullable=True)
    country_code        = Column(String(2), nullable=True)
    trigger_condition   = Column(String(200), nullable=True)                # 觸發條件描述
    trigger_value       = Column(Numeric(10, 4), nullable=True)             # 設定閾值
    actual_value        = Column(Numeric(10, 4), nullable=True)             # 實際數值
    alert_date          = Column(Date, nullable=False, default=date.today)
    severity            = Column(String(10), nullable=False, default="warning")
    is_acknowledged     = Column(Boolean, default=False, nullable=False)    # 是否已確認
    acknowledged_by     = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    acknowledged_at     = Column(DateTime, nullable=True)
    created_at          = Column(DateTime, default=datetime.utcnow)

    ack_user = relationship("User", foreign_keys=[acknowledged_by])


# ═══════════════════════════════════════════════════
# M-04 競爭對手分析
# ═══════════════════════════════════════════════════

class CompetitorProfile(Base):
    """競爭對手公司資料"""
    __tablename__ = "competitor_profiles"
    __table_args__ = (
        CheckConstraint(
            "business_type IN ('producer','exporter','importer','distributor','retailer','processor')",
            name="ck_competitor_biz_type",
        ),
    )

    id                         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    competitor_name            = Column(String(200), nullable=False)
    country_code               = Column(String(2), nullable=True)
    business_type              = Column(String(30), nullable=True)
    main_products              = Column(Text, nullable=True)                 # 主要產品
    annual_revenue_estimate    = Column(Numeric(16, 2), nullable=True)       # 估計年營收
    market_share_estimate      = Column(Numeric(5, 2), nullable=True)        # 市場份額 %
    key_markets                = Column(JSON, default=list)                  # 主要市場 ["TW","JP"]
    key_customers              = Column(JSON, default=list)                  # 主要客戶名稱
    strengths                  = Column(Text, nullable=True)                 # 優勢
    weaknesses                 = Column(Text, nullable=True)                 # 劣勢
    website                    = Column(String(300), nullable=True)
    source_info                = Column(Text, nullable=True)                 # 資料來源說明
    is_active                  = Column(Boolean, default=True)
    deleted_at                 = Column(DateTime, nullable=True)
    created_at                 = Column(DateTime, default=datetime.utcnow)
    updated_at                 = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    prices = relationship("CompetitorPrice", back_populates="competitor")


class CompetitorPrice(Base):
    """競爭對手報價觀察"""
    __tablename__ = "competitor_prices"
    __table_args__ = (
        CheckConstraint(
            "source IN ('store_visit','online','trade_show','intel','catalog')",
            name="ck_competitor_price_source",
        ),
    )

    id                = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    competitor_id     = Column(UUID(as_uuid=True), ForeignKey("competitor_profiles.id"), nullable=False)
    product_category  = Column(String(100), nullable=False)
    product_name      = Column(String(200), nullable=True)
    market_country    = Column(String(2), nullable=True)
    channel_type      = Column(String(50), nullable=True)                   # supermarket/wholesale/export
    observed_price    = Column(Numeric(10, 4), nullable=False)
    price_currency    = Column(String(3), default="TWD")
    price_unit        = Column(String(30), nullable=True)
    observed_date     = Column(Date, nullable=False, default=date.today)
    source            = Column(String(20), nullable=True)
    observer_name     = Column(String(100), nullable=True)                  # 觀察者姓名
    photo_url         = Column(String(500), nullable=True)
    notes             = Column(Text, nullable=True)
    created_at        = Column(DateTime, default=datetime.utcnow)

    competitor = relationship("CompetitorProfile", back_populates="prices")


# ═══════════════════════════════════════════════════
# M-05 全球貿易統計
# ═══════════════════════════════════════════════════

class GlobalTradeStatistics(Base):
    """全球農產品貿易統計（UN Comtrade / 海關資料）"""
    __tablename__ = "global_trade_statistics"
    __table_args__ = (
        CheckConstraint(
            "trade_flow IN ('import','export','re_export')",
            name="ck_trade_flow",
        ),
    )

    id                    = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    data_source           = Column(String(50), nullable=True)               # UN_Comtrade/national_customs
    reporting_country     = Column(String(2), nullable=False)               # 報告國
    partner_country       = Column(String(2), nullable=True)                # 貿易對象國
    trade_flow            = Column(String(10), nullable=False)              # import/export
    hs_code               = Column(String(20), nullable=True)               # HS 稅則號

    period_year           = Column(Integer, nullable=False)
    period_month          = Column(Integer, nullable=True)                  # NULL = 年度資料

    value_usd             = Column(Numeric(18, 2), nullable=True)           # 貿易值（USD）
    quantity_kg           = Column(Numeric(18, 2), nullable=True)           # 數量（kg）
    unit_value_usd_per_kg = Column(Numeric(10, 4), nullable=True)           # 單位價值
    yoy_value_change_pct  = Column(Numeric(7, 2), nullable=True)            # 值 YoY%
    yoy_qty_change_pct    = Column(Numeric(7, 2), nullable=True)            # 量 YoY%

    created_at            = Column(DateTime, default=datetime.utcnow)


# ═══════════════════════════════════════════════════
# M-06 天氣異常警報
# ═══════════════════════════════════════════════════

class WeatherAlert(Base):
    """天氣異常警報（颱風/洪水/乾旱影響農業生產）"""
    __tablename__ = "weather_alerts"
    __table_args__ = (
        CheckConstraint(
            "alert_type IN ('typhoon','flood','drought','frost','heatwave','storm','other')",
            name="ck_weather_alert_type",
        ),
        CheckConstraint(
            "severity IN ('watch','warning','emergency')",
            name="ck_weather_alert_severity",
        ),
    )

    id                    = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    alert_type            = Column(String(20), nullable=False)
    affected_region       = Column(String(200), nullable=True)              # 影響地區
    country_code          = Column(String(2), nullable=True)
    severity              = Column(String(20), nullable=False, default="watch")
    start_date            = Column(Date, nullable=False)
    end_date              = Column(Date, nullable=True)
    description           = Column(Text, nullable=True)
    potential_crop_impact = Column(Text, nullable=True)                     # 對農作物影響評估
    source                = Column(String(200), nullable=True)              # 資料來源
    source_url            = Column(String(500), nullable=True)
    is_active             = Column(Boolean, default=True, nullable=False)
    created_at            = Column(DateTime, default=datetime.utcnow)
    updated_at            = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ═══════════════════════════════════════════════════
# M-07 運價指數 / 供需指標
# ═══════════════════════════════════════════════════

class FreightIndex(Base):
    """貨運運價指數（SCFI/WCI/BDI 等）"""
    __tablename__ = "freight_indices"

    id                  = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    index_name          = Column(String(50), nullable=False)                # SCFI/WCI/BDI/custom
    route_origin        = Column(String(100), nullable=True)                # 起運地
    route_destination   = Column(String(100), nullable=True)                # 目的地
    container_type      = Column(String(20), nullable=True)                 # 20RF/40HC/bulk
    index_date          = Column(Date, nullable=False)
    index_value         = Column(Numeric(12, 2), nullable=False)
    index_unit          = Column(String(50), nullable=True)                 # USD/TEU、points
    wow_change_pct      = Column(Numeric(7, 2), nullable=True)              # 週比%
    yoy_change_pct      = Column(Numeric(7, 2), nullable=True)              # 年比%
    source              = Column(String(200), nullable=True)
    created_at          = Column(DateTime, default=datetime.utcnow)


class SupplyDemandIndicator(Base):
    """供需指標（產量預測 / 庫存水位）"""
    __tablename__ = "supply_demand_indicators"
    __table_args__ = (
        CheckConstraint(
            "indicator_type IN ('production_forecast','import_forecast','export_forecast',"
            "'inventory_level','planting_area','demand_estimate')",
            name="ck_supply_demand_type",
        ),
        CheckConstraint(
            "confidence_level IN ('high','medium','low')",
            name="ck_supply_demand_confidence",
        ),
    )

    id                 = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    indicator_type     = Column(String(30), nullable=False)
    product_category   = Column(String(100), nullable=False)
    country_code       = Column(String(2), nullable=True)
    region             = Column(String(100), nullable=True)
    period_year        = Column(Integer, nullable=False)
    period_month       = Column(Integer, nullable=True)
    value              = Column(Numeric(18, 4), nullable=False)
    value_unit         = Column(String(50), nullable=True)                  # kg/ton/rai/USD
    yoy_change_pct     = Column(Numeric(7, 2), nullable=True)
    source             = Column(String(200), nullable=True)
    confidence_level   = Column(String(10), nullable=True, default="medium")
    created_at         = Column(DateTime, default=datetime.utcnow)


# ═══════════════════════════════════════════════════
# M-08 全球買家資料庫
# ═══════════════════════════════════════════════════

class GlobalBuyerDirectory(Base):
    """全球潛在買家 / 合作方資料庫"""
    __tablename__ = "global_buyer_directory"
    __table_args__ = (
        CheckConstraint(
            "business_type IN ('importer','distributor','retailer','processor','foodservice','trader')",
            name="ck_buyer_biz_type",
        ),
        CheckConstraint(
            "company_size IN ('small','medium','large','enterprise')",
            name="ck_buyer_company_size",
        ),
        CheckConstraint(
            "interest_level IN ('hot','warm','cold','none')",
            name="ck_buyer_interest",
        ),
        CheckConstraint(
            "data_source IN ('trade_show','directory','referral','web_scraping','cold_outreach','other')",
            name="ck_buyer_data_source",
        ),
    )

    id                         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_name               = Column(String(300), nullable=False)
    country_code               = Column(String(2), nullable=True)
    city                       = Column(String(100), nullable=True)
    business_type              = Column(String(30), nullable=True)
    main_import_products       = Column(Text, nullable=True)                # 主要進口產品
    annual_import_volume_estimate = Column(Numeric(14, 2), nullable=True)  # 估計年進口量 kg
    key_source_countries       = Column(JSON, default=list)                 # 主要採購來源國

    # 聯絡資訊
    contact_name               = Column(String(100), nullable=True)
    contact_email              = Column(String(200), nullable=True)
    contact_phone              = Column(String(50), nullable=True)
    website                    = Column(String(300), nullable=True)

    company_size               = Column(String(20), nullable=True)
    data_source                = Column(String(30), nullable=True)
    credit_rating              = Column(String(20), nullable=True)          # A/B/C/D/unknown
    verified_status            = Column(Boolean, default=False)             # 是否已驗證

    last_contacted_date        = Column(Date, nullable=True)
    interest_level             = Column(String(10), nullable=True, default="cold")
    assigned_sales_rep_id      = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    notes                      = Column(Text, nullable=True)
    is_active                  = Column(Boolean, default=True)
    deleted_at                 = Column(DateTime, nullable=True)
    created_at                 = Column(DateTime, default=datetime.utcnow)
    updated_at                 = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    assigned_rep = relationship("User", foreign_keys=[assigned_sales_rep_id])


# ═══════════════════════════════════════════════════
# N-01 價目表
# ═══════════════════════════════════════════════════

class PriceList(Base):
    """價目表主表（標準/合約/促銷）"""
    __tablename__ = "price_lists"
    __table_args__ = (
        CheckConstraint(
            "price_list_type IN ('standard','contract','promotional','export','internal')",
            name="ck_price_list_type",
        ),
        CheckConstraint(
            "status IN ('draft','active','expired')",
            name="ck_price_list_status",
        ),
    )

    id                = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    price_list_code   = Column(String(50), unique=True, nullable=False)     # PL-2026-STD-TWD
    price_list_name   = Column(String(200), nullable=False)
    price_list_type   = Column(String(20), nullable=False, default="standard")

    # 適用條件
    customer_id       = Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=True)
    customer_tier     = Column(String(20), nullable=True)                   # key_account/regular/new
    channel_type      = Column(String(50), nullable=True)                   # supermarket/wholesale/export
    market_region     = Column(String(50), nullable=True)                   # TW/TH/JP/EU

    # 幣別與條件
    currency_code     = Column(String(3), default="TWD")
    incoterm          = Column(String(10), nullable=True)

    # 有效期
    effective_date    = Column(Date, nullable=False)
    expiry_date       = Column(Date, nullable=True)
    status            = Column(String(10), nullable=False, default="draft")
    approved_by       = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    approved_at       = Column(DateTime, nullable=True)

    created_by        = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    deleted_at        = Column(DateTime, nullable=True)
    created_at        = Column(DateTime, default=datetime.utcnow)
    updated_at        = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 關聯
    customer  = relationship("Customer", foreign_keys=[customer_id])
    approver  = relationship("User", foreign_keys=[approved_by])
    creator   = relationship("User", foreign_keys=[created_by])
    items     = relationship("PriceListItem", back_populates="price_list", cascade="all, delete-orphan")


class PriceListItem(Base):
    """價目表明細"""
    __tablename__ = "price_list_items"

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    price_list_id    = Column(UUID(as_uuid=True), ForeignKey("price_lists.id"), nullable=False)
    product_type_id  = Column(UUID(as_uuid=True), ForeignKey("product_types.id"), nullable=True)
    packaging_spec   = Column(String(100), nullable=True)                  # 包裝規格

    unit_price       = Column(Numeric(10, 4), nullable=False)              # 單位售價
    price_uom        = Column(String(20), default="kg")                    # 計價單位

    min_qty          = Column(Numeric(10, 2), nullable=True)               # 最小訂購量
    max_qty          = Column(Numeric(10, 2), nullable=True)               # 最大訂購量
    discount_pct     = Column(Numeric(5, 2), default=0)                    # 折扣率 %
    floor_price      = Column(Numeric(10, 4), nullable=True)               # 底價（不能低於此）
    cost_reference   = Column(Numeric(10, 4), nullable=True)               # 成本參考
    target_margin_pct = Column(Numeric(5, 2), nullable=True)               # 目標利潤率 %

    price_list = relationship("PriceList", back_populates="items")


# ═══════════════════════════════════════════════════
# N-02 定價規則引擎
# ═══════════════════════════════════════════════════

class PricingRule(Base):
    """動態定價規則（量折、提前付款、季節、組合）"""
    __tablename__ = "pricing_rules"
    __table_args__ = (
        CheckConstraint(
            "rule_type IN ('volume_discount','early_payment','seasonal','bundle','customer_tier','channel')",
            name="ck_pricing_rule_type",
        ),
        CheckConstraint(
            "action_type IN ('discount_pct','fixed_price','adjustment_amount')",
            name="ck_pricing_action_type",
        ),
    )

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rule_name        = Column(String(200), nullable=False)
    rule_type        = Column(String(30), nullable=False)
    priority         = Column(Integer, default=100)                        # 數字越小優先級越高
    conditions       = Column(JSON, default=dict)                          # 觸發條件 JSON
    action_type      = Column(String(30), nullable=False)                  # 折扣類型
    action_value     = Column(Numeric(10, 4), nullable=False)              # 折扣值（% 或固定值）
    effective_date   = Column(Date, nullable=True)
    expiry_date      = Column(Date, nullable=True)
    is_active        = Column(Boolean, default=True, nullable=False)
    notes            = Column(Text, nullable=True)
    created_by       = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at       = Column(DateTime, default=datetime.utcnow)
    updated_at       = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    creator = relationship("User", foreign_keys=[created_by])
