"""
WP7：計劃模組模型

1. ProcurementPlan     — 採購計劃（月度）
2. ProcurementPlanItem — 計劃明細（週次 × 供應商）
3. WeatherForecast     — 天氣記錄/預報
4. FinancialPlan       — 財務計劃（月度預算 vs 實際）
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


class ProcurementPlan(Base):
    """月度採購計劃"""
    __tablename__ = "procurement_plans"

    id                  = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plan_no             = Column(String(30), unique=True, nullable=False)  # PP-YYYYMM-XXX
    plan_month          = Column(Date, nullable=False)                      # 計劃月份（每月第一天）
    product_type_id     = Column(UUID(as_uuid=True), ForeignKey("product_types.id"), nullable=True)
    target_quantity_kg  = Column(Numeric(12, 2), nullable=True)
    target_budget_thb   = Column(Numeric(14, 2), nullable=True)
    actual_quantity_kg  = Column(Numeric(12, 2), default=0)   # 自動計算
    actual_cost_thb     = Column(Numeric(14, 2), default=0)   # 自動計算
    weather_risk_note   = Column(Text, nullable=True)
    season_note         = Column(Text, nullable=True)
    status              = Column(String(15), nullable=False, default="draft")  # draft / approved / in_progress / completed
    approved_by         = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_by          = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    updated_by          = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    deleted_at          = Column(DateTime, nullable=True)
    created_at          = Column(DateTime, default=datetime.utcnow)
    updated_at          = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    product_type = relationship("ProductType", foreign_keys=[product_type_id])
    approver     = relationship("User", foreign_keys=[approved_by])
    creator      = relationship("User", foreign_keys=[created_by])
    items        = relationship("ProcurementPlanItem", back_populates="plan", cascade="all, delete-orphan")


class ProcurementPlanItem(Base):
    """採購計劃明細 — 週次 × 供應商"""
    __tablename__ = "procurement_plan_items"

    id                       = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plan_id                  = Column(UUID(as_uuid=True), ForeignKey("procurement_plans.id"), nullable=False)
    supplier_id              = Column(UUID(as_uuid=True), ForeignKey("suppliers.id"), nullable=True)
    week_number              = Column(Integer, nullable=False)     # 1-5
    planned_quantity_kg      = Column(Numeric(10, 2), nullable=True)
    planned_price_per_kg_thb = Column(Numeric(10, 2), nullable=True)
    actual_purchase_order_id = Column(UUID(as_uuid=True), ForeignKey("purchase_orders.id"), nullable=True)
    weather_condition        = Column(String(20), nullable=True)   # sunny / cloudy / rainy / storm
    note                     = Column(Text, nullable=True)
    created_at               = Column(DateTime, default=datetime.utcnow)

    plan     = relationship("ProcurementPlan", back_populates="items")
    supplier = relationship("Supplier", foreign_keys=[supplier_id])
    purchase_order = relationship("PurchaseOrder", foreign_keys=[actual_purchase_order_id])


class WeatherForecast(Base):
    """天氣記錄/預報"""
    __tablename__ = "weather_forecasts"

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    forecast_date    = Column(Date, nullable=False)
    region           = Column(String(30), nullable=False)  # nakhon_pathom / kanchanaburi / ratchaburi / other
    condition        = Column(String(20), nullable=False)   # sunny / cloudy / rainy / storm / flood
    temperature_high = Column(Numeric(4, 1), nullable=True)
    temperature_low  = Column(Numeric(4, 1), nullable=True)
    rainfall_mm      = Column(Numeric(6, 1), nullable=True)
    impact_level     = Column(String(10), nullable=True)    # none / low / medium / high
    impact_note      = Column(Text, nullable=True)
    source           = Column(String(20), default="manual") # manual / api / tmd
    created_at       = Column(DateTime, default=datetime.utcnow)


class FinancialPlan(Base):
    """月度財務計劃"""
    __tablename__ = "financial_plans"

    id                          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plan_month                  = Column(Date, nullable=False, unique=True)
    planned_revenue_twd         = Column(Numeric(14, 2), nullable=True)
    planned_cogs_twd            = Column(Numeric(14, 2), nullable=True)
    planned_gross_profit_twd    = Column(Numeric(14, 2), nullable=True)
    planned_operating_expense_twd = Column(Numeric(14, 2), nullable=True)
    planned_net_profit_twd      = Column(Numeric(14, 2), nullable=True)
    exchange_rate_assumption    = Column(Numeric(8, 4), nullable=True)
    actual_revenue_twd          = Column(Numeric(14, 2), default=0)
    actual_cogs_twd             = Column(Numeric(14, 2), default=0)
    variance_pct                = Column(Numeric(6, 2), nullable=True)
    note                        = Column(Text, nullable=True)
    status                      = Column(String(15), default="draft")
    created_by                  = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at                  = Column(DateTime, default=datetime.utcnow)
    updated_at                  = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    creator = relationship("User", foreign_keys=[created_by])
