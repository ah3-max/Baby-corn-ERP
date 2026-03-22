"""
採購單相關 Pydantic Schema
"""
from uuid import UUID
from datetime import datetime, date
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, model_validator

from schemas.supplier import SupplierOut

PURCHASE_STATUSES = ["draft", "confirmed", "in_transit", "arrived", "closed"]


class PurchaseOrderCreate(BaseModel):
    order_date:       date
    supplier_id:      UUID
    source_farmer_id: Optional[UUID] = None
    product_type_id:  Optional[UUID] = None  # 品項類型
    estimated_weight: Decimal
    unit_price:       Decimal
    expected_arrival: Optional[datetime] = None
    note:             Optional[str] = None

    @model_validator(mode="after")
    def compute_total(self):
        self.total_amount = self.estimated_weight * self.unit_price
        return self

    total_amount: Optional[Decimal] = None


class PurchaseOrderUpdate(BaseModel):
    order_date:       Optional[date] = None
    supplier_id:      Optional[UUID] = None
    source_farmer_id: Optional[UUID] = None
    product_type_id:  Optional[UUID] = None
    estimated_weight: Optional[Decimal] = None
    unit_price:       Optional[Decimal] = None
    expected_arrival: Optional[datetime] = None
    note:             Optional[str] = None
    status:           Optional[str] = None


class ArrivalConfirm(BaseModel):
    """到廠確認資料"""
    arrived_at:      datetime
    received_weight: Decimal
    defect_weight:   Decimal = Decimal("0")
    arrival_note:    Optional[str] = None


class SupplierSimple(BaseModel):
    id:            UUID
    name:          str
    supplier_type: str

    class Config:
        from_attributes = True


class ProductTypeSimple(BaseModel):
    id:       UUID
    code:     str
    name_zh:  str

    class Config:
        from_attributes = True


class PurchaseOrderOut(BaseModel):
    id:               UUID
    order_no:         str
    order_date:       date
    supplier_id:      UUID
    supplier:         Optional[SupplierSimple]
    source_farmer_id: Optional[UUID]
    source_farmer:    Optional[SupplierSimple]
    product_type_id:  Optional[UUID]
    product_type:     Optional[ProductTypeSimple]
    estimated_weight: Decimal
    unit_price:       Decimal
    total_amount:     Decimal
    expected_arrival: Optional[datetime]
    status:           str
    arrived_at:       Optional[datetime]
    received_weight:  Optional[Decimal]
    defect_weight:    Optional[Decimal]
    usable_weight:    Optional[Decimal]
    defect_rate:      Optional[Decimal]
    arrival_note:     Optional[str]
    note:             Optional[str]
    created_at:       datetime
    updated_at:       datetime

    class Config:
        from_attributes = True
