"""銷售訂單 Schema"""
from uuid import UUID
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel, Field, model_validator


class CustomerSimple(BaseModel):
    id:   UUID
    name: str

    class Config:
        from_attributes = True


class BatchSimple(BaseModel):
    id:       UUID
    batch_no: str

    class Config:
        from_attributes = True


class SalesItemCreate(BaseModel):
    batch_id:       UUID
    quantity_kg:    Decimal = Field(gt=0, description="銷售重量（kg），必須大於 0")
    unit_price_twd: Decimal = Field(gt=0, description="單價（TWD/kg），必須大於 0")
    note:           Optional[str] = None

    @model_validator(mode="after")
    def compute_total(self):
        self.total_amount_twd = self.quantity_kg * self.unit_price_twd
        return self

    total_amount_twd: Optional[Decimal] = None


class SalesOrderCreate(BaseModel):
    customer_id:   UUID
    order_date:    date
    delivery_date: Optional[date] = None
    note:          Optional[str] = None
    items:         List[SalesItemCreate] = []


class SalesOrderUpdate(BaseModel):
    customer_id:   Optional[UUID] = None
    order_date:    Optional[date] = None
    delivery_date: Optional[date] = None
    status:        Optional[str] = None
    note:          Optional[str] = None
    items:         Optional[List[SalesItemCreate]] = None  # 有傳就全部替換


class SalesItemOut(BaseModel):
    id:               UUID
    batch_id:         UUID
    batch:            Optional[BatchSimple] = None
    quantity_kg:      Decimal
    unit_price_twd:   Decimal
    total_amount_twd: Decimal
    note:             Optional[str]

    class Config:
        from_attributes = True


class SalesOrderOut(BaseModel):
    id:               UUID
    order_no:         str
    customer_id:      UUID
    customer:         Optional[CustomerSimple] = None
    order_date:       date
    delivery_date:    Optional[date]
    total_amount_twd: Decimal
    status:           str
    note:             Optional[str]
    items:            List[SalesItemOut] = []
    created_at:       datetime
    updated_at:       datetime

    class Config:
        from_attributes = True
