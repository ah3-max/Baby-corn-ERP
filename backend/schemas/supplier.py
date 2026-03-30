"""
供應商相關 Pydantic Schema
"""
from uuid import UUID
from datetime import datetime, date
from typing import Optional
from pydantic import BaseModel

# 供應商類型選項
SUPPLIER_TYPES = ["farmer", "broker", "factory", "logistics", "customs", "packaging"]


class SupplierCreate(BaseModel):
    """建立供應商"""
    code:            Optional[str] = None
    name:            str
    name_en:         Optional[str] = None
    name_th:         Optional[str] = None
    supplier_type:   str
    contact_name:    Optional[str] = None
    phone:           Optional[str] = None
    line_id:         Optional[str] = None
    national_id:     Optional[str] = None
    region:          Optional[str] = None
    province:        Optional[str] = None
    district:        Optional[str] = None
    address:         Optional[str] = None
    payment_terms:   Optional[str] = None
    bank_account:    Optional[str] = None
    gap_cert_no:     Optional[str] = None
    gap_cert_expiry: Optional[date] = None
    note:            Optional[str] = None


class SupplierUpdate(BaseModel):
    """更新供應商"""
    code:            Optional[str] = None
    name:            Optional[str] = None
    name_en:         Optional[str] = None
    name_th:         Optional[str] = None
    supplier_type:   Optional[str] = None
    contact_name:    Optional[str] = None
    phone:           Optional[str] = None
    line_id:         Optional[str] = None
    national_id:     Optional[str] = None
    region:          Optional[str] = None
    province:        Optional[str] = None
    district:        Optional[str] = None
    address:         Optional[str] = None
    payment_terms:   Optional[str] = None
    bank_account:    Optional[str] = None
    gap_cert_no:     Optional[str] = None
    gap_cert_expiry: Optional[date] = None
    note:            Optional[str] = None
    is_active:       Optional[bool] = None


class SupplierOut(BaseModel):
    """供應商輸出"""
    id:              UUID
    code:            Optional[str]
    name:            str
    name_en:         Optional[str]
    name_th:         Optional[str]
    supplier_type:   str
    contact_name:    Optional[str]
    phone:           Optional[str]
    line_id:         Optional[str]
    national_id:     Optional[str]
    region:          Optional[str]
    province:        Optional[str]
    district:        Optional[str]
    address:         Optional[str]
    payment_terms:   Optional[str]
    bank_account:    Optional[str]
    gap_cert_no:     Optional[str]
    gap_cert_expiry: Optional[date]
    note:            Optional[str]
    is_active:       bool
    created_at:      datetime
    updated_at:      datetime

    class Config:
        from_attributes = True
