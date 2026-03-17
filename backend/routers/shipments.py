"""
出口物流 API
GET    /shipments           - 列表
POST   /shipments           - 建立出口單（含批次 IDs）
GET    /shipments/:id       - 詳情
PUT    /shipments/:id       - 更新
PUT    /shipments/:id/advance - 推進狀態
"""
from uuid import UUID
from typing import List, Optional
from decimal import Decimal
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func

from database import get_db
from models.user import User
from models.shipment import Shipment, ShipmentBatch, SHIPMENT_STATUSES, SHIPMENT_STATUS_NEXT
from models.batch import Batch
from schemas.shipment import ShipmentCreate, ShipmentUpdate, ShipmentOut
from utils.dependencies import check_permission

router = APIRouter(prefix="/shipments", tags=["出口物流"])


def _generate_shipment_no(db: Session) -> str:
    from datetime import date
    date_str = date.today().strftime("%Y%m%d")
    prefix   = f"SH-{date_str}-"
    count    = db.query(func.count(Shipment.id)).filter(
        Shipment.shipment_no.like(f"{prefix}%")
    ).scalar()
    return f"{prefix}{str(count + 1).zfill(3)}"


def _load_shipment(db: Session, shipment_id: UUID) -> Shipment:
    s = (
        db.query(Shipment)
        .options(
            joinedload(Shipment.shipment_batches).joinedload(ShipmentBatch.batch)
        )
        .filter(Shipment.id == shipment_id)
        .first()
    )
    if not s:
        raise HTTPException(status_code=404, detail="出口單不存在")
    return s


@router.get("", response_model=List[ShipmentOut])
def list_shipments(
    status_filter: Optional[str] = Query(None, alias="status"),
    skip:          int = 0,
    limit:         int = 100,
    db:            Session = Depends(get_db),
    _:             User = Depends(check_permission("shipment", "view")),
):
    q = (
        db.query(Shipment)
        .options(joinedload(Shipment.shipment_batches).joinedload(ShipmentBatch.batch))
    )
    if status_filter:
        q = q.filter(Shipment.status == status_filter)
    return q.order_by(Shipment.created_at.desc()).offset(skip).limit(limit).all()


@router.post("", response_model=ShipmentOut, status_code=status.HTTP_201_CREATED)
def create_shipment(
    payload:      ShipmentCreate,
    db:           Session = Depends(get_db),
    current_user: User = Depends(check_permission("shipment", "create")),
):
    shipment_no = _generate_shipment_no(db)
    shipment = Shipment(
        shipment_no          = shipment_no,
        export_date          = payload.export_date,
        transport_mode       = payload.transport_mode,
        shipped_boxes        = payload.shipped_boxes,
        shipper_name         = payload.shipper_name,
        carrier              = payload.carrier,
        vessel_name          = payload.vessel_name,
        bl_no                = payload.bl_no,
        estimated_arrival_tw = payload.estimated_arrival_tw,
        freight_cost         = payload.freight_cost,
        customs_cost         = payload.customs_cost,
        insurance_cost       = payload.insurance_cost,
        handling_cost        = payload.handling_cost,
        other_cost           = payload.other_cost,
        awb_no               = payload.awb_no,
        flight_no            = payload.flight_no,
        airline              = payload.airline,
        container_no         = payload.container_no,
        port_of_loading      = payload.port_of_loading,
        port_of_discharge    = payload.port_of_discharge,
        notes                = payload.notes,
        status               = "preparing",
        created_by           = current_user.id,
    )
    db.add(shipment)
    db.flush()  # 取得 shipment.id

    # 關聯批次並計算總重
    total_weight = Decimal("0")
    for batch_id in payload.batch_ids:
        batch = db.query(Batch).filter(Batch.id == batch_id).first()
        if batch:
            db.add(ShipmentBatch(shipment_id=shipment.id, batch_id=batch_id))
            total_weight += batch.current_weight or Decimal("0")

    shipment.total_weight = total_weight
    db.commit()
    return _load_shipment(db, shipment.id)


@router.get("/{shipment_id}", response_model=ShipmentOut)
def get_shipment(
    shipment_id: UUID,
    db:          Session = Depends(get_db),
    _:           User = Depends(check_permission("shipment", "view")),
):
    return _load_shipment(db, shipment_id)


@router.put("/{shipment_id}", response_model=ShipmentOut)
def update_shipment(
    shipment_id: UUID,
    payload:     ShipmentUpdate,
    db:          Session = Depends(get_db),
    _:           User = Depends(check_permission("shipment", "edit")),
):
    s = db.query(Shipment).filter(Shipment.id == shipment_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="出口單不存在")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(s, field, value)

    db.commit()
    return _load_shipment(db, shipment_id)


@router.put("/{shipment_id}/advance", response_model=ShipmentOut)
def advance_shipment(
    shipment_id: UUID,
    db:          Session = Depends(get_db),
    _:           User = Depends(check_permission("shipment", "edit")),
):
    s = (
        db.query(Shipment)
        .options(joinedload(Shipment.shipment_batches).joinedload(ShipmentBatch.batch))
        .filter(Shipment.id == shipment_id)
        .first()
    )
    if not s:
        raise HTTPException(status_code=404, detail="出口單不存在")

    next_status = SHIPMENT_STATUS_NEXT.get(s.status)
    if not next_status:
        raise HTTPException(status_code=400, detail="已是終態，無法繼續推進")

    # 出貨單狀態 → 對應批次自動推進規則
    # preparing  → customs_th : 批次 ready_to_export → exported
    # customs_th → in_transit : 批次 exported        → in_transit_tw
    # customs_tw → arrived_tw : 批次 in_transit_tw   → in_stock（記錄實際到台日期）
    BATCH_SYNC: dict = {
        "customs_th": ("ready_to_export", "exported"),
        "in_transit": ("exported",        "in_transit_tw"),
        "arrived_tw": ("in_transit_tw",   "in_stock"),
    }

    if next_status in BATCH_SYNC:
        from_status, to_status = BATCH_SYNC[next_status]
        for sb in s.shipment_batches:
            batch = sb.batch
            if batch and batch.status == from_status:
                batch.status = to_status

    # 到達台灣時：記錄實際到港日期（庫存入庫由倉管人員在「入庫作業」頁面手動確認）
    if next_status == "arrived_tw":
        from datetime import date
        today = date.today()
        s.actual_arrival_tw = s.actual_arrival_tw or today

    s.status = next_status
    db.commit()
    return _load_shipment(db, shipment_id)


@router.delete("/{shipment_id}", status_code=204)
def delete_shipment(
    shipment_id: UUID,
    db: Session = Depends(get_db),
    _: User = Depends(check_permission("shipment", "delete")),
):
    """刪除出口單（僅允許 preparing 狀態）"""
    s = db.query(Shipment).filter(Shipment.id == shipment_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="出口單不存在")
    if s.status != "preparing":
        raise HTTPException(status_code=400, detail="僅可刪除備貨中的出口單，已送出的出口單無法刪除")
    db.delete(s)
    db.commit()
