"""
WP4：配送單 + 司機管理 API

司機：
  GET/POST     /drivers              - 列表 / 新增
  GET/PUT      /drivers/:id          - 詳情 / 更新

配送單：
  GET/POST     /delivery-orders      - 列表 / 新增（業務經理下單）
  GET/PUT      /delivery-orders/:id  - 詳情 / 更新
  PUT          /delivery-orders/:id/accept  - 司機接單
  PUT          /delivery-orders/:id/advance - 推進狀態
  POST         /delivery-orders/:id/items/:iid/deliver - 單站簽收
"""
from uuid import UUID
from typing import List, Optional
from datetime import datetime, date
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func

from database import get_db
from models.user import User
from models.logistics import (
    Driver, DeliveryOrder, DeliveryOrderItem, DeliveryProof,
    DELIVERY_STATUSES, DELIVERY_STATUS_NEXT,
)
from models.customer import Customer
from schemas.logistics import (
    DriverCreate, DriverUpdate, DriverOut,
    DeliveryOrderCreate, DeliveryOrderUpdate, DeliveryOrderOut,
    DeliveryOrderItemOut, DeliverItemPayload,
)
from utils.dependencies import check_permission

router = APIRouter(tags=["物流配送"])


def _gen_no(db, model, prefix, field):
    from sqlalchemy import text
    db.execute(text(f"SELECT pg_advisory_xact_lock(hashtext('do_order_no_{prefix}'))"))
    date_str = date.today().strftime("%Y%m%d")
    full_prefix = f"{prefix}-{date_str}-"
    count = db.query(func.count(model.id)).filter(field.like(f"{full_prefix}%")).scalar()
    return f"{full_prefix}{str(count + 1).zfill(3)}"


# ─── 司機 CRUD ──────────────────────────────────────────

@router.get("/drivers", response_model=List[DriverOut])
def list_drivers(
    is_active: Optional[bool] = Query(None),
    db:        Session = Depends(get_db),
    _:         User = Depends(check_permission("delivery", "view")),
):
    q = db.query(Driver)
    if is_active is not None:
        q = q.filter(Driver.is_active == is_active)
    return q.order_by(Driver.driver_code).all()


@router.post("/drivers", response_model=DriverOut, status_code=status.HTTP_201_CREATED)
def create_driver(
    payload: DriverCreate,
    db:      Session = Depends(get_db),
    _:       User = Depends(check_permission("delivery", "create")),
):
    driver = Driver(**payload.model_dump())
    db.add(driver)
    db.commit()
    db.refresh(driver)
    return driver


@router.get("/drivers/{driver_id}", response_model=DriverOut)
def get_driver(
    driver_id: UUID,
    db:        Session = Depends(get_db),
    _:         User = Depends(check_permission("delivery", "view")),
):
    driver = db.query(Driver).filter(Driver.id == driver_id).first()
    if not driver:
        raise HTTPException(status_code=404, detail="司機不存在")
    return driver


@router.put("/drivers/{driver_id}", response_model=DriverOut)
def update_driver(
    driver_id: UUID,
    payload:   DriverUpdate,
    db:        Session = Depends(get_db),
    _:         User = Depends(check_permission("delivery", "edit")),
):
    driver = db.query(Driver).filter(Driver.id == driver_id).first()
    if not driver:
        raise HTTPException(status_code=404, detail="司機不存在")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(driver, k, v)
    db.commit()
    db.refresh(driver)
    return driver


# ─── 配送單 CRUD ────────────────────────────────────────

def _load_delivery(db: Session, delivery_id: UUID) -> DeliveryOrder:
    d = (
        db.query(DeliveryOrder)
        .options(
            joinedload(DeliveryOrder.items).joinedload(DeliveryOrderItem.customer),
            joinedload(DeliveryOrder.driver),
            joinedload(DeliveryOrder.assigner),
        )
        .filter(DeliveryOrder.id == delivery_id)
        .first()
    )
    if not d:
        raise HTTPException(status_code=404, detail="配送單不存在")
    return d


def _delivery_to_out(d: DeliveryOrder) -> DeliveryOrderOut:
    return DeliveryOrderOut(
        id=str(d.id), delivery_no=d.delivery_no, order_type=d.order_type,
        driver_id=str(d.driver_id) if d.driver_id else None,
        driver_name=d.driver.name if d.driver else None,
        assigned_by=str(d.assigned_by),
        assigner_name=d.assigner.full_name if d.assigner else None,
        dispatch_date=d.dispatch_date, route_description=d.route_description,
        status=d.status,
        total_weight_kg=float(d.total_weight_kg or 0),
        total_boxes=d.total_boxes or 0,
        departure_time=d.departure_time, return_time=d.return_time,
        vehicle_temp_departure=float(d.vehicle_temp_departure) if d.vehicle_temp_departure else None,
        vehicle_temp_arrival=float(d.vehicle_temp_arrival) if d.vehicle_temp_arrival else None,
        fuel_cost_twd=float(d.fuel_cost_twd) if d.fuel_cost_twd else None,
        toll_cost_twd=float(d.toll_cost_twd) if d.toll_cost_twd else None,
        other_cost_twd=float(d.other_cost_twd) if d.other_cost_twd else None,
        driver_note=d.driver_note,
        items=[
            DeliveryOrderItemOut(
                id=str(i.id), customer_id=str(i.customer_id),
                customer_name=i.customer.name if i.customer else None,
                sales_order_id=str(i.sales_order_id) if i.sales_order_id else None,
                daily_sale_id=str(i.daily_sale_id) if i.daily_sale_id else None,
                lot_id=str(i.lot_id) if i.lot_id else None,
                quantity_kg=float(i.quantity_kg), quantity_boxes=i.quantity_boxes,
                delivery_address=i.delivery_address, delivery_sequence=i.delivery_sequence,
                status=i.status, delivered_at=i.delivered_at,
                received_by=i.received_by, signature_photo_url=i.signature_photo_url,
                rejection_reason=i.rejection_reason, note=i.note,
            ) for i in sorted(d.items, key=lambda x: x.delivery_sequence)
        ],
        created_at=d.created_at,
    )


@router.get("/delivery-orders", response_model=List[DeliveryOrderOut])
def list_delivery_orders(
    status_filter: Optional[str]  = Query(None, alias="status"),
    driver_id:     Optional[UUID] = Query(None),
    dispatch_date: Optional[date] = Query(None),
    skip:          int = 0,
    limit:         int = 50,
    db:            Session = Depends(get_db),
    _:             User = Depends(check_permission("delivery", "view")),
):
    q = db.query(DeliveryOrder).options(
        joinedload(DeliveryOrder.items).joinedload(DeliveryOrderItem.customer),
        joinedload(DeliveryOrder.driver),
        joinedload(DeliveryOrder.assigner),
    )
    if status_filter:
        q = q.filter(DeliveryOrder.status == status_filter)
    if driver_id:
        q = q.filter(DeliveryOrder.driver_id == driver_id)
    if dispatch_date:
        q = q.filter(DeliveryOrder.dispatch_date == dispatch_date)
    orders = q.order_by(DeliveryOrder.created_at.desc()).offset(skip).limit(limit).all()
    return [_delivery_to_out(d) for d in orders]


@router.post("/delivery-orders", response_model=DeliveryOrderOut, status_code=status.HTTP_201_CREATED)
def create_delivery_order(
    payload:      DeliveryOrderCreate,
    db:           Session = Depends(get_db),
    current_user: User = Depends(check_permission("delivery", "create")),
):
    """業務經理建立配送單"""
    delivery_no = _gen_no(db, DeliveryOrder, "DEL", DeliveryOrder.delivery_no)
    order = DeliveryOrder(
        delivery_no=delivery_no,
        order_type=payload.order_type,
        driver_id=payload.driver_id,
        assigned_by=current_user.id,
        dispatch_date=payload.dispatch_date,
        route_description=payload.route_description,
        status="pending",
        created_by=current_user.id,
    )
    db.add(order)
    db.flush()

    total_kg = Decimal("0")
    total_boxes = 0
    for item_data in payload.items:
        item = DeliveryOrderItem(
            delivery_order_id=order.id,
            customer_id=item_data.customer_id,
            sales_order_id=item_data.sales_order_id,
            daily_sale_id=item_data.daily_sale_id,
            lot_id=item_data.lot_id,
            quantity_kg=item_data.quantity_kg,
            quantity_boxes=item_data.quantity_boxes,
            delivery_address=item_data.delivery_address,
            delivery_sequence=item_data.delivery_sequence,
            note=item_data.note,
        )
        db.add(item)
        total_kg += item_data.quantity_kg
        total_boxes += (item_data.quantity_boxes or 0)

    order.total_weight_kg = total_kg
    order.total_boxes = total_boxes
    db.commit()
    return _delivery_to_out(_load_delivery(db, order.id))


@router.get("/delivery-orders/{order_id}", response_model=DeliveryOrderOut)
def get_delivery_order(
    order_id: UUID,
    db:       Session = Depends(get_db),
    _:        User = Depends(check_permission("delivery", "view")),
):
    return _delivery_to_out(_load_delivery(db, order_id))


@router.put("/delivery-orders/{order_id}", response_model=DeliveryOrderOut)
def update_delivery_order(
    order_id: UUID,
    payload:  DeliveryOrderUpdate,
    db:       Session = Depends(get_db),
    _:        User = Depends(check_permission("delivery", "edit")),
):
    order = db.query(DeliveryOrder).filter(DeliveryOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="配送單不存在")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(order, k, v)
    db.commit()
    return _delivery_to_out(_load_delivery(db, order_id))


@router.put("/delivery-orders/{order_id}/accept", response_model=DeliveryOrderOut)
def accept_delivery_order(
    order_id:     UUID,
    db:           Session = Depends(get_db),
    current_user: User = Depends(check_permission("delivery", "edit")),
):
    """司機接單"""
    order = db.query(DeliveryOrder).filter(DeliveryOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="配送單不存在")
    if order.status != "pending":
        raise HTTPException(status_code=400, detail="僅待派單狀態可接單")
    order.status = "accepted"
    db.commit()
    return _delivery_to_out(_load_delivery(db, order_id))


@router.put("/delivery-orders/{order_id}/advance", response_model=DeliveryOrderOut)
def advance_delivery_order(
    order_id:     UUID,
    db:           Session = Depends(get_db),
    current_user: User = Depends(check_permission("delivery", "edit")),
):
    """推進配送單狀態"""
    order = db.query(DeliveryOrder).filter(DeliveryOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="配送單不存在")
    next_status = DELIVERY_STATUS_NEXT.get(order.status)
    if not next_status:
        raise HTTPException(status_code=400, detail="已是終態或無法推進")

    # 裝車時記錄出發時間
    if next_status == "in_transit" and not order.departure_time:
        order.departure_time = datetime.utcnow()

    # 完成時記錄回車時間，並檢查所有站是否完成
    if next_status == "delivered":
        order.return_time = datetime.utcnow()
        # 若有任何站未完成，改為 partial_delivered
        items = db.query(DeliveryOrderItem).filter(
            DeliveryOrderItem.delivery_order_id == order_id
        ).all()
        has_pending = any(i.status == "pending" for i in items)
        if has_pending:
            next_status = "partial_delivered"

    order.status = next_status
    db.commit()
    return _delivery_to_out(_load_delivery(db, order_id))


@router.post("/delivery-orders/{order_id}/items/{item_id}/deliver")
def deliver_item(
    order_id: UUID,
    item_id:  UUID,
    payload:  DeliverItemPayload,
    db:       Session = Depends(get_db),
    _:        User = Depends(check_permission("delivery", "edit")),
):
    """單站簽收/拒收"""
    item = db.query(DeliveryOrderItem).filter(
        DeliveryOrderItem.id == item_id,
        DeliveryOrderItem.delivery_order_id == order_id,
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="配送明細不存在")

    item.status = payload.status
    item.delivered_at = datetime.utcnow()
    item.received_by = payload.received_by
    item.rejection_reason = payload.rejection_reason
    db.commit()

    return {"message": "簽收狀態已更新", "status": item.status}
