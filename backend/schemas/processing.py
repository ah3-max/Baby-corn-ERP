"""加工管理相關 Pydantic Schema"""
from uuid import UUID
from datetime import datetime, date
from typing import Optional, List
from decimal import Decimal
from pydantic import BaseModel


class ProcessingBatchLinkCreate(BaseModel):
    batch_id: UUID
    direction: str          # 'in' 或 'out'
    weight_kg: Decimal


class ProcessingBatchLinkOut(BaseModel):
    id: UUID
    processing_order_id: UUID
    batch_id: UUID
    direction: str
    weight_kg: float

    class Config:
        from_attributes = True


class ProcessingOrderCreate(BaseModel):
    order_code: str
    oem_factory_id: UUID
    process_date: date
    total_input_kg: Optional[Decimal] = None
    total_output_kg: Optional[Decimal] = None
    waste_kg: Optional[Decimal] = None
    yield_pct: Optional[Decimal] = None
    fee_per_kg_thb: Optional[Decimal] = None
    total_fee_thb: Optional[Decimal] = None
    notes: Optional[str] = None
    batch_links: List[ProcessingBatchLinkCreate] = []


class ProcessingOrderUpdate(BaseModel):
    process_date: Optional[date] = None
    total_input_kg: Optional[Decimal] = None
    total_output_kg: Optional[Decimal] = None
    waste_kg: Optional[Decimal] = None
    yield_pct: Optional[Decimal] = None
    fee_per_kg_thb: Optional[Decimal] = None
    total_fee_thb: Optional[Decimal] = None
    status: Optional[str] = None
    notes: Optional[str] = None


class ProcessingOrderOut(BaseModel):
    id: UUID
    order_code: str
    oem_factory_id: UUID
    process_date: date
    total_input_kg: Optional[float]
    total_output_kg: Optional[float]
    waste_kg: Optional[float]
    yield_pct: Optional[float]
    fee_per_kg_thb: Optional[float]
    total_fee_thb: Optional[float]
    status: str
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime
    batch_links: List[ProcessingBatchLinkOut] = []

    class Config:
        from_attributes = True
