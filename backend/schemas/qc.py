"""QC 檢驗記錄 Schema"""
from uuid import UUID
from datetime import datetime
from decimal import Decimal
from typing import Optional, Any
from pydantic import BaseModel


class QCRecordCreate(BaseModel):
    batch_id:        UUID
    inspection_type: Optional[str] = None     # factory_incoming/pre_packing/post_packing/pre_export/pesticide
    inspector_name:  str
    checked_at:      Optional[datetime] = None
    result:          str                       # pass/fail/conditional_pass
    grade:           Optional[str] = None
    weight_checked:  Optional[Decimal] = None
    quality_data:    Optional[dict] = None     # 品質細項 JSON
    defect_rate_pct: Optional[Decimal] = None
    pesticide_name:  Optional[str] = None
    pesticide_value: Optional[Decimal] = None
    pesticide_limit: Optional[Decimal] = None
    notes:           Optional[str] = None


class QCRecordUpdate(BaseModel):
    inspection_type: Optional[str] = None
    inspector_name:  Optional[str] = None
    result:          Optional[str] = None
    grade:           Optional[str] = None
    weight_checked:  Optional[Decimal] = None
    quality_data:    Optional[dict] = None
    defect_rate_pct: Optional[Decimal] = None
    pesticide_name:  Optional[str] = None
    pesticide_value: Optional[Decimal] = None
    pesticide_limit: Optional[Decimal] = None
    photo_count:     Optional[int] = None
    notes:           Optional[str] = None


class QCRecordOut(BaseModel):
    id:              UUID
    batch_id:        UUID
    inspection_type: Optional[str]
    inspector_name:  str
    checked_at:      datetime
    result:          str
    grade:           Optional[str]
    weight_checked:  Optional[Decimal]
    quality_data:    Optional[Any]
    defect_rate_pct: Optional[Decimal]
    pesticide_name:  Optional[str]
    pesticide_value: Optional[Decimal]
    pesticide_limit: Optional[Decimal]
    photo_count:     int
    notes:           Optional[str]
    created_at:      datetime

    class Config:
        from_attributes = True
