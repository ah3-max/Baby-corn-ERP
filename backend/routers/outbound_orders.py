"""
WP4：出庫單 API

  GET/POST     /outbound-orders           - 列表 / 新增
  GET          /outbound-orders/:id       - 詳情
  PUT          /outbound-orders/:id/approve - 審批
  PUT          /outbound-orders/:id/pick    - 揀貨完成
  PUT          /outbound-orders/:id/ship    - 出庫
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
from models.logistics import OutboundOrder, OutboundOrderItem, OUTBOUND_STATUS_NEXT
from models.inventory import InventoryLot, InventoryTransaction
from schemas.logistics import (
    OutboundOrderCreate, OutboundOrderOut, OutboundOrderItemOut,
)
from utils.dependencies import check_permission

router = APIRouter(prefix="/outbound-orders", tags=["出庫管理"])


def _gen_no(db, model, prefix, field):
    from sqlalchemy import text
    db.execute(text(f"SELECT pg_advisory_xact_lock(hashtext('ob_order_no_{prefix}'))"))
    date_str = date.today().strftime("%Y%m%d")
    full_prefix = f"{prefix}-{date_str}-"
    count = db.query(func.count(model.id)).filter(field.like(f"{full_prefix}%")).scalar()
    return f"{full_prefix}{str(count + 1).zfill(3)}"


def _load_outbound(db: Session, oid: UUID) -> OutboundOrder:
    o = (
        db.query(OutboundOrder)
        .options(joinedload(OutboundOrder.items))
        .filter(OutboundOrder.id == oid)
        .first()
    )
    if not o:
        raise HTTPException(status_code=404, detail="出庫單不存在")
    return o


def _outbound_to_out(o: OutboundOrder) -> OutboundOrderOut:
    return OutboundOrderOut(
        id=str(o.id), outbound_no=o.outbound_no, outbound_type=o.outbound_type,
        delivery_order_id=str(o.delivery_order_id) if o.delivery_order_id else None,
        warehouse_id=str(o.warehouse_id) if o.warehouse_id else None,
        approved_by=str(o.approved_by) if o.approved_by else None,
        status=o.status,
        total_weight_kg=float(o.total_weight_kg or 0),
        total_boxes=o.total_boxes or 0,
        pick_started_at=o.pick_started_at, pick_completed_at=o.pick_completed_at,
        shipped_at=o.shipped_at, note=o.note,
        items=[
            OutboundOrderItemOut(
                id=str(i.id), lot_id=str(i.lot_id),
                batch_id=str(i.batch_id) if i.batch_id else None,
                quantity_kg=float(i.quantity_kg), quantity_boxes=i.quantity_boxes,
                actual_picked_kg=float(i.actual_picked_kg) if i.actual_picked_kg else None,
                actual_picked_boxes=i.actual_picked_boxes,
                location_id=str(i.location_id) if i.location_id else None,
                picked_by=str(i.picked_by) if i.picked_by else None,
                picked_at=i.picked_at, status=i.status,
            ) for i in o.items
        ],
        created_at=o.created_at,
    )


@router.get("", response_model=List[OutboundOrderOut])
def list_outbound_orders(
    status_filter: Optional[str]  = Query(None, alias="status"),
    warehouse_id:  Optional[UUID] = Query(None),
    skip:          int = 0,
    limit:         int = 50,
    db:            Session = Depends(get_db),
    _:             User = Depends(check_permission("outbound", "view")),
):
    q = db.query(OutboundOrder).options(joinedload(OutboundOrder.items))
    if status_filter:
        q = q.filter(OutboundOrder.status == status_filter)
    if warehouse_id:
        q = q.filter(OutboundOrder.warehouse_id == warehouse_id)
    orders = q.order_by(OutboundOrder.created_at.desc()).offset(skip).limit(limit).all()
    return [_outbound_to_out(o) for o in orders]


@router.post("", response_model=OutboundOrderOut, status_code=status.HTTP_201_CREATED)
def create_outbound_order(
    payload:      OutboundOrderCreate,
    db:           Session = Depends(get_db),
    current_user: User = Depends(check_permission("outbound", "create")),
):
    outbound_no = _gen_no(db, OutboundOrder, "OUT", OutboundOrder.outbound_no)
    order = OutboundOrder(
        outbound_no=outbound_no,
        outbound_type=payload.outbound_type,
        delivery_order_id=payload.delivery_order_id,
        warehouse_id=payload.warehouse_id,
        note=payload.note,
        status="draft",
        created_by=current_user.id,
    )
    db.add(order)
    db.flush()

    total_kg = Decimal("0")
    total_boxes = 0
    for item_data in payload.items:
        item = OutboundOrderItem(
            outbound_order_id=order.id,
            lot_id=item_data.lot_id,
            batch_id=item_data.batch_id,
            quantity_kg=item_data.quantity_kg,
            quantity_boxes=item_data.quantity_boxes,
            location_id=item_data.location_id,
        )
        db.add(item)
        total_kg += item_data.quantity_kg
        total_boxes += (item_data.quantity_boxes or 0)

    order.total_weight_kg = total_kg
    order.total_boxes = total_boxes
    db.commit()
    return _outbound_to_out(_load_outbound(db, order.id))


@router.get("/{order_id}", response_model=OutboundOrderOut)
def get_outbound_order(
    order_id: UUID,
    db:       Session = Depends(get_db),
    _:        User = Depends(check_permission("outbound", "view")),
):
    return _outbound_to_out(_load_outbound(db, order_id))


@router.put("/{order_id}/approve", response_model=OutboundOrderOut)
def approve_outbound(
    order_id:     UUID,
    db:           Session = Depends(get_db),
    current_user: User = Depends(check_permission("outbound", "approve")),
):
    """審批出庫單"""
    order = db.query(OutboundOrder).filter(OutboundOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="出庫單不存在")
    if order.status != "draft":
        raise HTTPException(status_code=400, detail="僅草稿狀態可審批")
    order.status = "approved"
    order.approved_by = current_user.id
    db.commit()
    return _outbound_to_out(_load_outbound(db, order_id))


@router.put("/{order_id}/pick", response_model=OutboundOrderOut)
def pick_outbound(
    order_id:     UUID,
    db:           Session = Depends(get_db),
    current_user: User = Depends(check_permission("outbound", "pick")),
):
    """揀貨完成 — 記錄實際揀貨量"""
    order = db.query(OutboundOrder).filter(OutboundOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="出庫單不存在")
    if order.status != "approved":
        raise HTTPException(status_code=400, detail="僅已審批狀態可揀貨")

    order.status = "picked"
    order.pick_started_at = order.pick_started_at or datetime.utcnow()
    order.pick_completed_at = datetime.utcnow()

    # 更新每筆明細的揀貨狀態
    items = db.query(OutboundOrderItem).filter(OutboundOrderItem.outbound_order_id == order_id).all()
    for item in items:
        if not item.actual_picked_kg:
            item.actual_picked_kg = item.quantity_kg
            item.actual_picked_boxes = item.quantity_boxes
        item.picked_by = current_user.id
        item.picked_at = datetime.utcnow()
        item.status = "picked"

    db.commit()
    return _outbound_to_out(_load_outbound(db, order_id))


@router.put("/{order_id}/ship", response_model=OutboundOrderOut)
def ship_outbound(
    order_id:     UUID,
    db:           Session = Depends(get_db),
    current_user: User = Depends(check_permission("outbound", "ship")),
):
    """出庫 — 扣減庫存並建立交易記錄"""
    order = db.query(OutboundOrder).filter(OutboundOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="出庫單不存在")
    if order.status != "picked":
        raise HTTPException(status_code=400, detail="僅已揀貨狀態可出庫")

    items = db.query(OutboundOrderItem).filter(OutboundOrderItem.outbound_order_id == order_id).all()
    for item in items:
        picked_kg = float(item.actual_picked_kg or item.quantity_kg)
        lot = db.query(InventoryLot).filter(InventoryLot.id == item.lot_id).with_for_update().first()
        if lot:
            lot.current_weight_kg = max(0, float(lot.current_weight_kg) - picked_kg)
            lot.shipped_weight_kg = float(lot.shipped_weight_kg) + picked_kg
            if item.actual_picked_boxes and lot.current_boxes is not None:
                lot.current_boxes = max(0, lot.current_boxes - item.actual_picked_boxes)
                lot.shipped_boxes = (lot.shipped_boxes or 0) + item.actual_picked_boxes
            if float(lot.current_weight_kg) <= 0:
                lot.status = "depleted"
            elif float(lot.initial_weight_kg) > 0 and float(lot.current_weight_kg) / float(lot.initial_weight_kg) < 0.2:
                lot.status = "low_stock"

            db.add(InventoryTransaction(
                lot_id=lot.id,
                txn_type="out",
                weight_kg=picked_kg,
                boxes=item.actual_picked_boxes,
                reference=order.outbound_no,
                reason=f"出庫單 {order.outbound_no}",
                created_by=current_user.id,
            ))

    order.status = "shipped"
    order.shipped_at = datetime.utcnow()
    db.commit()
    return _outbound_to_out(_load_outbound(db, order_id))
