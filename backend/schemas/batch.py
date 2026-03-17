"""
批次相關 Pydantic Schema
"""
from uuid import UUID
from datetime import datetime, date as date_type
from decimal import Decimal
from typing import Optional, Any
from pydantic import BaseModel, model_validator


class BatchSupplierSimple(BaseModel):
    id:   UUID
    name: str

    class Config:
        from_attributes = True


class BatchPOOut(BaseModel):
    """嵌入在 BatchOut 中的採購單摘要"""
    id:       UUID
    order_no: str
    supplier: Optional[BatchSupplierSimple] = None

    class Config:
        from_attributes = True


class BatchCreate(BaseModel):
    """建立批次"""
    purchase_order_id:     UUID
    initial_weight:        Decimal
    product_type_id:       Optional[UUID]     = None
    size_grade:            Optional[str]      = None
    quality_data:          Optional[dict]     = None
    region_code:           Optional[str]      = None
    note:                  Optional[str]      = None
    harvest_datetime:      Optional[datetime] = None
    harvest_location:      Optional[str]      = None
    harvest_temperature:   Optional[Decimal]  = None
    harvest_weather:       Optional[str]      = None
    transport_refrigerated: Optional[bool]    = None
    shelf_life_days:       Optional[int]      = None


class BatchUpdate(BaseModel):
    """更新批次（備註 / 重量 / 鮮度里程碑）"""
    current_weight:          Optional[Decimal]  = None
    note:                    Optional[str]      = None
    product_type_id:         Optional[UUID]     = None
    size_grade:              Optional[str]      = None
    quality_data:            Optional[dict]     = None
    region_code:             Optional[str]      = None
    # 田間採摘
    harvest_datetime:        Optional[datetime] = None
    harvest_location:        Optional[str]      = None
    harvest_temperature:     Optional[Decimal]  = None
    harvest_weather:         Optional[str]      = None
    transport_refrigerated:  Optional[bool]     = None
    # 工廠里程碑
    factory_arrival_dt:      Optional[datetime] = None
    factory_temp_on_arrival: Optional[Decimal]  = None
    factory_complete_dt:     Optional[datetime] = None
    cold_storage_temp:       Optional[Decimal]  = None
    # 包裝出口
    packed_dt:               Optional[datetime] = None
    container_loaded_dt:     Optional[datetime] = None
    # 有效期
    shelf_life_days:         Optional[int]      = None


class BatchOut(BaseModel):
    id:                UUID
    batch_no:          str
    purchase_order_id: UUID
    purchase_order:    Optional[BatchPOOut] = None
    product_type_id:   Optional[UUID]      = None
    size_grade:        Optional[str]       = None
    quality_data:      Optional[Any]       = None
    region_code:       Optional[str]       = None
    initial_weight:    Decimal
    current_weight:    Decimal
    status:            str
    note:              Optional[str]
    created_at:        datetime
    updated_at:        datetime

    # 生鮮時效追蹤欄位
    harvest_datetime:        Optional[datetime] = None
    harvest_location:        Optional[str]      = None
    harvest_temperature:     Optional[Decimal]  = None
    harvest_weather:         Optional[str]      = None
    transport_refrigerated:  Optional[bool]     = None
    factory_arrival_dt:      Optional[datetime] = None
    factory_temp_on_arrival: Optional[Decimal]  = None
    factory_complete_dt:     Optional[datetime] = None
    cold_storage_temp:       Optional[Decimal]  = None
    packed_dt:               Optional[datetime] = None
    container_loaded_dt:     Optional[datetime] = None
    shelf_life_days:         Optional[int]      = None

    # 計算欄位（動態，不存 DB）
    hours_since_harvest: Optional[float] = None
    days_since_harvest:  Optional[int]   = None
    remaining_days:      Optional[int]   = None
    freshness_status:    Optional[str]   = None   # fresh / warning / critical / expired

    @model_validator(mode='after')
    def _compute_freshness(self) -> 'BatchOut':
        if self.harvest_datetime:
            now   = datetime.utcnow()
            delta = now - self.harvest_datetime
            hours = delta.total_seconds() / 3600
            days  = delta.days
            self.hours_since_harvest = round(hours, 1)
            self.days_since_harvest  = days
            shelf = self.shelf_life_days or 23
            self.remaining_days = shelf - days
            if self.remaining_days <= 0:
                self.freshness_status = 'expired'
            elif days >= 20:
                self.freshness_status = 'critical'
            elif days >= 15:
                self.freshness_status = 'warning'
            else:
                self.freshness_status = 'fresh'
        return self

    class Config:
        from_attributes = True
