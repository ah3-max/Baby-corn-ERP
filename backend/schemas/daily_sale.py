"""每日市場銷售 Schema"""
from uuid import UUID
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List, Any
from pydantic import BaseModel, Field, model_validator


class DailySaleItemCreate(BaseModel):
    batch_id:        UUID
    lot_id:          Optional[UUID] = None
    size_grade:      Optional[str] = None
    quantity_boxes:  Optional[int] = Field(None, ge=0)
    quantity_kg:     Decimal = Field(gt=0, description="銷售重量（kg），必須大於 0")
    unit_price_twd:  Decimal = Field(gt=0, description="單價（TWD/kg），必須大於 0")
    notes:           Optional[str] = None

    @model_validator(mode="after")
    def compute_total(self):
        self.total_amount_twd = self.quantity_kg * self.unit_price_twd
        return self

    total_amount_twd: Optional[Decimal] = None


class DailySaleCreate(BaseModel):
    sale_date:       date
    market_code:     str = Field(min_length=1)  # TPE_M1 / TPE_M2 / OTHER
    customer_id:     Optional[UUID] = None
    consignee_name:  Optional[str] = None
    notes:           Optional[str] = None
    items:           List[DailySaleItemCreate] = []


class DailySaleUpdate(BaseModel):
    sale_date:          Optional[date] = None
    market_code:        Optional[str] = None
    customer_id:        Optional[UUID] = None
    consignee_name:     Optional[str] = None
    settlement_status:  Optional[str] = None   # unsettled/partial/settled
    notes:              Optional[str] = None
    items:              Optional[List[DailySaleItemCreate]] = None


class DailySaleItemOut(BaseModel):
    id:              UUID
    batch_id:        UUID
    lot_id:          Optional[UUID]
    size_grade:      Optional[str]
    quantity_boxes:  Optional[int]
    quantity_kg:     float
    unit_price_twd:  float
    total_amount_twd: float
    cost_per_kg_twd: Optional[float]
    notes:           Optional[str]

    class Config:
        from_attributes = True


class CustomerSimple(BaseModel):
    id:   UUID
    name: str
    code: Optional[str] = None

    class Config:
        from_attributes = True


class DailySaleOut(BaseModel):
    id:                UUID
    sale_date:         date
    market_code:       str
    customer_id:       Optional[UUID]
    customer:          Optional[CustomerSimple] = None
    consignee_name:    Optional[str]
    total_boxes:       int
    total_kg:          float
    total_amount_twd:  float
    settlement_status: str
    notes:             Optional[str]
    items:             List[DailySaleItemOut] = []
    created_at:        datetime
    updated_at:        datetime

    class Config:
        from_attributes = True


# ── 市場行情 ──────────────────────────────────────────

class MarketPriceCreate(BaseModel):
    price_date:    date
    market_code:   str
    product_code:  str = "baby_corn"
    size_grade:    Optional[str] = None
    avg_price_twd: Optional[Decimal] = None
    high_price_twd: Optional[Decimal] = None
    low_price_twd:  Optional[Decimal] = None
    volume_kg:      Optional[Decimal] = None
    source:         str = "manual"
    notes:          Optional[str] = None


class MarketPriceOut(BaseModel):
    id:             UUID
    price_date:     date
    market_code:    str
    product_code:   str
    size_grade:     Optional[str]
    avg_price_twd:  Optional[float]
    high_price_twd: Optional[float]
    low_price_twd:  Optional[float]
    volume_kg:      Optional[float]
    source:         str
    notes:          Optional[str]
    created_at:     datetime

    class Config:
        from_attributes = True
