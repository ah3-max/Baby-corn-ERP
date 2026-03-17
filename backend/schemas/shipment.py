"""出口物流 Schema — Module J"""
from uuid import UUID
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel


class BatchSimple(BaseModel):
    id:             UUID
    batch_no:       str
    current_weight: Decimal
    status:         str

    class Config:
        from_attributes = True


class ShipmentCreate(BaseModel):
    export_date:          date
    transport_mode:       Optional[str] = None   # air / sea
    carrier:              Optional[str] = None
    vessel_name:          Optional[str] = None
    bl_no:                Optional[str] = None
    shipped_boxes:        Optional[int] = None
    shipper_name:         Optional[str] = None
    estimated_arrival_tw: Optional[date] = None
    freight_cost:         Optional[Decimal] = None
    customs_cost:         Optional[Decimal] = None
    insurance_cost:       Optional[Decimal] = None
    handling_cost:        Optional[Decimal] = None
    other_cost:           Optional[Decimal] = None
    # 空運欄位
    awb_no:               Optional[str] = None
    flight_no:            Optional[str] = None
    airline:              Optional[str] = None
    # 海運欄位
    container_no:         Optional[str] = None
    port_of_loading:      Optional[str] = None
    port_of_discharge:    Optional[str] = None
    notes:                Optional[str] = None
    batch_ids:            List[UUID] = []


class ShipmentUpdate(BaseModel):
    export_date:          Optional[date] = None
    transport_mode:       Optional[str] = None
    carrier:              Optional[str] = None
    vessel_name:          Optional[str] = None
    bl_no:                Optional[str] = None
    shipped_boxes:        Optional[int] = None
    shipper_name:         Optional[str] = None
    export_customs_no:    Optional[str] = None
    phyto_cert_no:        Optional[str] = None
    phyto_cert_date:      Optional[date] = None
    actual_departure_dt:  Optional[datetime] = None
    estimated_arrival_tw: Optional[date] = None
    actual_arrival_tw:    Optional[date] = None
    freight_cost:         Optional[Decimal] = None
    customs_cost:         Optional[Decimal] = None
    insurance_cost:       Optional[Decimal] = None
    handling_cost:        Optional[Decimal] = None
    other_cost:           Optional[Decimal] = None
    # 空運欄位
    awb_no:               Optional[str] = None
    flight_no:            Optional[str] = None
    airline:              Optional[str] = None
    # 海運欄位
    container_no:         Optional[str] = None
    port_of_loading:      Optional[str] = None
    port_of_discharge:    Optional[str] = None
    notes:                Optional[str] = None


class ShipmentBatchOut(BaseModel):
    batch_id: UUID
    batch:    Optional[BatchSimple] = None

    class Config:
        from_attributes = True


class ShipmentOut(BaseModel):
    id:                   UUID
    shipment_no:          str
    export_date:          date
    transport_mode:       Optional[str]
    carrier:              Optional[str]
    vessel_name:          Optional[str]
    bl_no:                Optional[str]
    shipped_boxes:        Optional[int]
    shipper_name:         Optional[str]
    export_customs_no:    Optional[str]
    phyto_cert_no:        Optional[str]
    phyto_cert_date:      Optional[date]
    actual_departure_dt:  Optional[datetime]
    estimated_arrival_tw: Optional[date]
    actual_arrival_tw:    Optional[date]
    status:               str
    total_weight:         Optional[Decimal]
    freight_cost:         Optional[Decimal]
    customs_cost:         Optional[Decimal]
    insurance_cost:       Optional[Decimal]
    handling_cost:        Optional[Decimal]
    other_cost:           Optional[Decimal]
    # 空運欄位
    awb_no:               Optional[str]
    flight_no:            Optional[str]
    airline:              Optional[str]
    # 海運欄位
    container_no:         Optional[str]
    port_of_loading:      Optional[str]
    port_of_discharge:    Optional[str]
    notes:                Optional[str]
    shipment_batches:     List[ShipmentBatchOut] = []
    created_at:           datetime
    updated_at:           datetime

    class Config:
        from_attributes = True
