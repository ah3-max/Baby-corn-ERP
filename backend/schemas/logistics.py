"""
WP4：物流派遣 Pydantic Schemas
"""
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List, Any
from pydantic import BaseModel


# ── Driver ───────────────────────────────────────────────

class DriverCreate(BaseModel):
    driver_code:   str
    name:          str
    phone:         Optional[str] = None
    line_id:       Optional[str] = None
    vehicle_type:  Optional[str] = None
    vehicle_plate: Optional[str] = None
    license_no:    Optional[str] = None
    max_load_kg:   Optional[Decimal] = None
    note:          Optional[str] = None

class DriverUpdate(BaseModel):
    name:          Optional[str] = None
    phone:         Optional[str] = None
    line_id:       Optional[str] = None
    vehicle_type:  Optional[str] = None
    vehicle_plate: Optional[str] = None
    max_load_kg:   Optional[Decimal] = None
    is_active:     Optional[bool] = None
    note:          Optional[str] = None

class DriverOut(BaseModel):
    id:            str
    driver_code:   str
    user_id:       Optional[str]
    name:          str
    phone:         Optional[str]
    line_id:       Optional[str]
    vehicle_type:  Optional[str]
    vehicle_plate: Optional[str]
    license_no:    Optional[str]
    max_load_kg:   Optional[float]
    is_active:     bool
    note:          Optional[str]
    created_at:    datetime
    class Config: from_attributes = True


# ── DeliveryOrderItem ────────────────────────────────────

class DeliveryOrderItemCreate(BaseModel):
    customer_id:       str
    sales_order_id:    Optional[str] = None
    daily_sale_id:     Optional[str] = None
    lot_id:            Optional[str] = None
    quantity_kg:       Decimal
    quantity_boxes:    Optional[int] = None
    delivery_address:  Optional[str] = None
    delivery_sequence: int = 0
    note:              Optional[str] = None

class DeliveryOrderItemOut(BaseModel):
    id:                  str
    customer_id:         str
    customer_name:       Optional[str] = None
    sales_order_id:      Optional[str]
    daily_sale_id:       Optional[str]
    lot_id:              Optional[str]
    quantity_kg:         float
    quantity_boxes:      Optional[int]
    delivery_address:    Optional[str]
    delivery_sequence:   int
    status:              str
    delivered_at:        Optional[datetime]
    received_by:         Optional[str]
    signature_photo_url: Optional[str]
    rejection_reason:    Optional[str]
    note:                Optional[str]
    class Config: from_attributes = True


# ── DeliveryOrder ────────────────────────────────────────

class DeliveryOrderCreate(BaseModel):
    order_type:        str = "sales_delivery"
    driver_id:         Optional[str] = None
    dispatch_date:     date
    route_description: Optional[str] = None
    items:             List[DeliveryOrderItemCreate]

class DeliveryOrderUpdate(BaseModel):
    driver_id:              Optional[str] = None
    dispatch_date:          Optional[date] = None
    route_description:      Optional[str] = None
    vehicle_temp_departure: Optional[Decimal] = None
    vehicle_temp_arrival:   Optional[Decimal] = None
    fuel_cost_twd:          Optional[Decimal] = None
    toll_cost_twd:          Optional[Decimal] = None
    other_cost_twd:         Optional[Decimal] = None
    driver_note:            Optional[str] = None

class DeliveryOrderOut(BaseModel):
    id:                     str
    delivery_no:            str
    order_type:             str
    driver_id:              Optional[str]
    driver_name:            Optional[str] = None
    assigned_by:            str
    assigner_name:          Optional[str] = None
    dispatch_date:          date
    route_description:      Optional[str]
    status:                 str
    total_weight_kg:        float
    total_boxes:            int
    departure_time:         Optional[datetime]
    return_time:            Optional[datetime]
    vehicle_temp_departure: Optional[float]
    vehicle_temp_arrival:   Optional[float]
    fuel_cost_twd:          Optional[float]
    toll_cost_twd:          Optional[float]
    other_cost_twd:         Optional[float]
    driver_note:            Optional[str]
    items:                  List[DeliveryOrderItemOut] = []
    created_at:             datetime
    class Config: from_attributes = True


# ── DeliverItem（簽收） ──────────────────────────────────

class DeliverItemPayload(BaseModel):
    status:         str = "delivered"  # delivered / rejected / partial
    received_by:    Optional[str] = None
    rejection_reason: Optional[str] = None


# ── OutboundOrderItem ────────────────────────────────────

class OutboundOrderItemCreate(BaseModel):
    lot_id:         str
    batch_id:       Optional[str] = None
    quantity_kg:    Decimal
    quantity_boxes: Optional[int] = None
    location_id:    Optional[str] = None

class OutboundOrderItemOut(BaseModel):
    id:                  str
    lot_id:              str
    batch_id:            Optional[str]
    quantity_kg:         float
    quantity_boxes:      Optional[int]
    actual_picked_kg:    Optional[float]
    actual_picked_boxes: Optional[int]
    location_id:         Optional[str]
    picked_by:           Optional[str]
    picked_at:           Optional[datetime]
    status:              str
    class Config: from_attributes = True


# ── OutboundOrder ────────────────────────────────────────

class OutboundOrderCreate(BaseModel):
    outbound_type:     str = "delivery"
    delivery_order_id: Optional[str] = None
    warehouse_id:      Optional[str] = None
    note:              Optional[str] = None
    items:             List[OutboundOrderItemCreate]

class OutboundOrderOut(BaseModel):
    id:                str
    outbound_no:       str
    outbound_type:     str
    delivery_order_id: Optional[str]
    warehouse_id:      Optional[str]
    approved_by:       Optional[str]
    status:            str
    total_weight_kg:   float
    total_boxes:       int
    pick_started_at:   Optional[datetime]
    pick_completed_at: Optional[datetime]
    shipped_at:        Optional[datetime]
    note:              Optional[str]
    items:             List[OutboundOrderItemOut] = []
    created_at:        datetime
    class Config: from_attributes = True
