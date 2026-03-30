"""收付款相關 Pydantic Schema"""
from uuid import UUID
from datetime import datetime, date
from typing import Optional
from decimal import Decimal
from pydantic import BaseModel


class PaymentCreate(BaseModel):
    customer_id: UUID
    sales_order_id: Optional[UUID] = None
    payment_date: date
    amount_twd: Decimal
    payment_method: str         # cash/transfer/check
    reference_no: Optional[str] = None
    notes: Optional[str] = None


class PaymentUpdate(BaseModel):
    payment_date: Optional[date] = None
    amount_twd: Optional[Decimal] = None
    payment_method: Optional[str] = None
    reference_no: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None


class PaymentOut(BaseModel):
    id: UUID
    customer_id: UUID
    sales_order_id: Optional[UUID]
    payment_date: date
    amount_twd: float
    payment_method: str
    reference_no: Optional[str]
    status: str
    confirmed_by: Optional[UUID]
    confirmed_at: Optional[datetime]
    notes: Optional[str]
    created_by: Optional[UUID]
    created_at: datetime

    class Config:
        from_attributes = True
