"""客戶 Schema"""
from uuid import UUID
from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel


class CustomerCreate(BaseModel):
    code:                   Optional[str] = None
    name:                   str
    customer_type:          Optional[str] = None    # wholesaler/retailer/consignee/agent/potential
    contact_name:           Optional[str] = None
    phone:                  Optional[str] = None
    email:                  Optional[str] = None
    region:                 Optional[str] = None
    market_code:            Optional[str] = None    # TPE_M1, TPE_M2, OTHER
    address:                Optional[str] = None
    payment_terms:          Optional[str] = None
    preferred_specs:        Optional[list] = None
    credit_status:          Optional[str] = None    # good/warning/blocked
    assigned_sales_user_id: Optional[UUID] = None
    note:                   Optional[str] = None


class CustomerUpdate(BaseModel):
    code:                   Optional[str] = None
    name:                   Optional[str] = None
    customer_type:          Optional[str] = None
    contact_name:           Optional[str] = None
    phone:                  Optional[str] = None
    email:                  Optional[str] = None
    region:                 Optional[str] = None
    market_code:            Optional[str] = None
    address:                Optional[str] = None
    payment_terms:          Optional[str] = None
    preferred_specs:        Optional[list] = None
    credit_status:          Optional[str] = None
    assigned_sales_user_id: Optional[UUID] = None
    note:                   Optional[str] = None
    is_active:              Optional[bool] = None


class CustomerOut(BaseModel):
    id:                     UUID
    code:                   Optional[str]
    name:                   str
    customer_type:          Optional[str]
    contact_name:           Optional[str]
    phone:                  Optional[str]
    email:                  Optional[str]
    region:                 Optional[str]
    market_code:            Optional[str]
    address:                Optional[str]
    payment_terms:          Optional[str]
    preferred_specs:        Optional[Any]
    credit_status:          str
    assigned_sales_user_id: Optional[UUID]
    note:                   Optional[str]
    is_active:              bool
    created_at:             datetime
    updated_at:             datetime

    class Config:
        from_attributes = True
