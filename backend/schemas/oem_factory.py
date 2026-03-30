"""OEM 工廠相關 Pydantic Schema"""
from uuid import UUID
from datetime import datetime
from typing import Optional
from decimal import Decimal
from pydantic import BaseModel


class OEMFactoryCreate(BaseModel):
    code: str
    name: str
    name_en: Optional[str] = None
    contact_name: Optional[str] = None
    contact_phone: Optional[str] = None
    address: Optional[str] = None
    province: Optional[str] = None
    license_no: Optional[str] = None
    gmp_cert_no: Optional[str] = None
    processing_fee_per_kg: Optional[Decimal] = None
    notes: Optional[str] = None


class OEMFactoryUpdate(BaseModel):
    name: Optional[str] = None
    name_en: Optional[str] = None
    contact_name: Optional[str] = None
    contact_phone: Optional[str] = None
    address: Optional[str] = None
    province: Optional[str] = None
    license_no: Optional[str] = None
    gmp_cert_no: Optional[str] = None
    processing_fee_per_kg: Optional[Decimal] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None


class OEMFactoryOut(BaseModel):
    id: UUID
    code: str
    name: str
    name_en: Optional[str]
    contact_name: Optional[str]
    contact_phone: Optional[str]
    address: Optional[str]
    province: Optional[str]
    license_no: Optional[str]
    gmp_cert_no: Optional[str]
    processing_fee_per_kg: Optional[float]
    notes: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
