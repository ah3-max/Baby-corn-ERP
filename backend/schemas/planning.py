"""
WP7：計劃模組 Pydantic Schemas
"""
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List, Any
from pydantic import BaseModel


# ── ProcurementPlan ──────────────────────────────────────

class ProcurementPlanItemCreate(BaseModel):
    supplier_id:              Optional[str] = None
    week_number:              int
    planned_quantity_kg:      Optional[Decimal] = None
    planned_price_per_kg_thb: Optional[Decimal] = None
    weather_condition:        Optional[str] = None
    note:                     Optional[str] = None

class ProcurementPlanCreate(BaseModel):
    plan_month:          date
    product_type_id:     Optional[str] = None
    target_quantity_kg:  Optional[Decimal] = None
    target_budget_thb:   Optional[Decimal] = None
    weather_risk_note:   Optional[str] = None
    season_note:         Optional[str] = None
    items:               Optional[List[ProcurementPlanItemCreate]] = None

class ProcurementPlanUpdate(BaseModel):
    target_quantity_kg:  Optional[Decimal] = None
    target_budget_thb:   Optional[Decimal] = None
    weather_risk_note:   Optional[str] = None
    season_note:         Optional[str] = None
    status:              Optional[str] = None

class ProcurementPlanItemOut(BaseModel):
    id:                       str
    supplier_id:              Optional[str]
    week_number:              int
    planned_quantity_kg:      Optional[float]
    planned_price_per_kg_thb: Optional[float]
    actual_purchase_order_id: Optional[str]
    weather_condition:        Optional[str]
    note:                     Optional[str]
    class Config: from_attributes = True

class ProcurementPlanOut(BaseModel):
    id:                  str
    plan_no:             str
    plan_month:          date
    product_type_id:     Optional[str]
    target_quantity_kg:  Optional[float]
    target_budget_thb:   Optional[float]
    actual_quantity_kg:  Optional[float]
    actual_cost_thb:     Optional[float]
    weather_risk_note:   Optional[str]
    season_note:         Optional[str]
    status:              str
    items:               List[ProcurementPlanItemOut] = []
    created_at:          datetime
    class Config: from_attributes = True


# ── WeatherForecast ──────────────────────────────────────

class WeatherForecastCreate(BaseModel):
    forecast_date:    date
    region:           str
    condition:        str
    temperature_high: Optional[Decimal] = None
    temperature_low:  Optional[Decimal] = None
    rainfall_mm:      Optional[Decimal] = None
    impact_level:     Optional[str] = None
    impact_note:      Optional[str] = None
    source:           str = "manual"

class WeatherForecastOut(BaseModel):
    id:               str
    forecast_date:    date
    region:           str
    condition:        str
    temperature_high: Optional[float]
    temperature_low:  Optional[float]
    rainfall_mm:      Optional[float]
    impact_level:     Optional[str]
    impact_note:      Optional[str]
    source:           str
    created_at:       datetime
    class Config: from_attributes = True


# ── FinancialPlan ────────────────────────────────────────

class FinancialPlanCreate(BaseModel):
    plan_month:                    date
    planned_revenue_twd:           Optional[Decimal] = None
    planned_cogs_twd:              Optional[Decimal] = None
    planned_gross_profit_twd:      Optional[Decimal] = None
    planned_operating_expense_twd: Optional[Decimal] = None
    planned_net_profit_twd:        Optional[Decimal] = None
    exchange_rate_assumption:      Optional[Decimal] = None
    note:                          Optional[str] = None

class FinancialPlanUpdate(BaseModel):
    planned_revenue_twd:           Optional[Decimal] = None
    planned_cogs_twd:              Optional[Decimal] = None
    planned_gross_profit_twd:      Optional[Decimal] = None
    planned_operating_expense_twd: Optional[Decimal] = None
    planned_net_profit_twd:        Optional[Decimal] = None
    exchange_rate_assumption:      Optional[Decimal] = None
    note:                          Optional[str] = None
    status:                        Optional[str] = None

class FinancialPlanOut(BaseModel):
    id:                            str
    plan_month:                    date
    planned_revenue_twd:           Optional[float]
    planned_cogs_twd:              Optional[float]
    planned_gross_profit_twd:      Optional[float]
    planned_operating_expense_twd: Optional[float]
    planned_net_profit_twd:        Optional[float]
    exchange_rate_assumption:      Optional[float]
    actual_revenue_twd:            Optional[float]
    actual_cogs_twd:               Optional[float]
    variance_pct:                  Optional[float]
    note:                          Optional[str]
    status:                        str
    created_at:                    datetime
    class Config: from_attributes = True
