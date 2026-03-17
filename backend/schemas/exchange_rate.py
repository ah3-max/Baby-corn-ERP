"""匯率相關 Pydantic Schema"""
from uuid import UUID
from datetime import datetime, date
from typing import Optional
from decimal import Decimal
from pydantic import BaseModel


class ExchangeRateCreate(BaseModel):
    from_currency: str = "THB"
    to_currency: str = "TWD"
    rate: Decimal
    effective_date: date
    source: str = "manual"


class ExchangeRateOut(BaseModel):
    id: UUID
    from_currency: str
    to_currency: str
    rate: float
    effective_date: date
    source: str
    recorded_by: Optional[UUID]
    created_at: datetime

    class Config:
        from_attributes = True
