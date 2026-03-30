"""
WP5：財務 Pydantic Schemas
"""
from datetime import datetime, date
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel


# ── AccountReceivable ────────────────────────────────────

class ARCreate(BaseModel):
    customer_id:         str
    source_type:         str = "manual"
    source_id:           Optional[str] = None
    original_amount_twd: Decimal
    due_date:            Optional[date] = None
    payment_terms:       Optional[str] = None
    note:                Optional[str] = None

class ARUpdate(BaseModel):
    paid_amount_twd:  Optional[Decimal] = None
    due_date:         Optional[date] = None
    status:           Optional[str] = None
    note:             Optional[str] = None

class AROut(BaseModel):
    id:                     str
    ar_no:                  str
    customer_id:            str
    customer_name:          Optional[str] = None
    source_type:            str
    source_id:              Optional[str]
    original_amount_twd:    float
    paid_amount_twd:        float
    outstanding_amount_twd: float
    due_date:               Optional[date]
    payment_terms:          Optional[str]
    status:                 str
    days_overdue:           Optional[int] = None
    last_payment_date:      Optional[date]
    note:                   Optional[str]
    created_at:             datetime
    class Config: from_attributes = True


# ── AccountPayable ───────────────────────────────────────

class APCreate(BaseModel):
    supplier_id:         str
    source_type:         str = "manual"
    source_id:           Optional[str] = None
    original_amount_thb: Optional[Decimal] = None
    original_amount_twd: Optional[Decimal] = None
    due_date:            Optional[date] = None
    payment_terms:       Optional[str] = None
    note:                Optional[str] = None

class APUpdate(BaseModel):
    paid_amount_thb:  Optional[Decimal] = None
    paid_amount_twd:  Optional[Decimal] = None
    due_date:         Optional[date] = None
    status:           Optional[str] = None
    note:             Optional[str] = None

class APOut(BaseModel):
    id:                     str
    ap_no:                  str
    supplier_id:            str
    supplier_name:          Optional[str] = None
    source_type:            str
    source_id:              Optional[str]
    original_amount_thb:    Optional[float]
    original_amount_twd:    Optional[float]
    paid_amount_thb:        Optional[float]
    paid_amount_twd:        Optional[float]
    outstanding_amount_thb: Optional[float]
    outstanding_amount_twd: Optional[float]
    due_date:               Optional[date]
    payment_terms:          Optional[str]
    status:                 str
    days_overdue:           Optional[int] = None
    last_payment_date:      Optional[date]
    note:                   Optional[str]
    created_at:             datetime
    class Config: from_attributes = True
