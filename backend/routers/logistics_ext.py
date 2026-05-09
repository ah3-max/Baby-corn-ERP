"""
物流擴充路由（H 段）

涵蓋：
  /logistics/vehicles            — 車輛 CRUD
  /logistics/vehicle-maintenance — 保養記錄 CRUD
  /logistics/returns             — 退貨單 CRUD
"""
import uuid
from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database import get_db
from utils.dependencies import check_permission

router = APIRouter(tags=["物流擴充"])


# ──────────────────────────────────────────────────────────
# H-03  車輛管理
# ──────────────────────────────────────────────────────────

@router.get("/logistics/vehicles")
def list_vehicles(
    vehicle_type: Optional[str] = None,
    limit: int = Query(default=50),
    db: Session = Depends(get_db),
    current_user=Depends(check_permission("delivery", "read")),
):
    from models.thai_ops import Vehicle
    q = db.query(Vehicle).filter(Vehicle.deleted_at.is_(None))
    if vehicle_type:
        q = q.filter(Vehicle.vehicle_type == vehicle_type)
    items = q.order_by(Vehicle.plate_no).limit(limit).all()
    return {"items": [_to_dict(i) for i in items], "total": len(items)}


@router.post("/logistics/vehicles", status_code=201)
def create_vehicle(
    data: dict,
    db: Session = Depends(get_db),
    current_user=Depends(check_permission("delivery", "create")),
):
    from models.thai_ops import Vehicle
    obj = Vehicle(**data)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return _to_dict(obj)


@router.get("/logistics/vehicles/{vid}")
def get_vehicle(
    vid: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(check_permission("delivery", "read")),
):
    from models.thai_ops import Vehicle
    obj = db.query(Vehicle).filter(Vehicle.id == vid).first()
    if not obj:
        raise HTTPException(status_code=404, detail="車輛不存在")
    return _to_dict(obj)


@router.patch("/logistics/vehicles/{vid}")
def patch_vehicle(
    vid: UUID,
    data: dict,
    db: Session = Depends(get_db),
    current_user=Depends(check_permission("delivery", "update")),
):
    from models.thai_ops import Vehicle
    obj = db.query(Vehicle).filter(Vehicle.id == vid).first()
    if not obj:
        raise HTTPException(status_code=404, detail="車輛不存在")
    for k, v in data.items():
        if hasattr(obj, k):
            setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    return _to_dict(obj)


# ──────────────────────────────────────────────────────────
# H-04  車輛保養記錄
# ──────────────────────────────────────────────────────────

@router.get("/logistics/vehicle-maintenance")
def list_maintenance(
    vehicle_id: Optional[UUID] = None,
    limit: int = Query(default=20),
    db: Session = Depends(get_db),
    current_user=Depends(check_permission("delivery", "read")),
):
    from models.thai_ops import VehicleMaintenance
    q = db.query(VehicleMaintenance)
    if vehicle_id:
        q = q.filter(VehicleMaintenance.vehicle_id == vehicle_id)
    items = q.order_by(VehicleMaintenance.service_date.desc()).limit(limit).all()
    return {"items": [_to_dict(i) for i in items], "total": len(items)}


@router.post("/logistics/vehicle-maintenance", status_code=201)
def create_maintenance(
    data: dict,
    db: Session = Depends(get_db),
    current_user=Depends(check_permission("delivery", "create")),
):
    from models.thai_ops import VehicleMaintenance
    obj = VehicleMaintenance(**data)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return _to_dict(obj)


# ──────────────────────────────────────────────────────────
# J-01  退貨管理
# ──────────────────────────────────────────────────────────

@router.get("/logistics/returns")
def list_returns(
    status: Optional[str] = None,
    return_type: Optional[str] = None,
    limit: int = Query(default=50),
    db: Session = Depends(get_db),
    current_user=Depends(check_permission("delivery", "read")),
):
    from models.thai_ops import ReturnOrder
    q = db.query(ReturnOrder).filter(ReturnOrder.deleted_at.is_(None))
    if status:
        q = q.filter(ReturnOrder.status == status)
    if return_type:
        q = q.filter(ReturnOrder.return_type == return_type)
    items = q.order_by(ReturnOrder.created_at.desc()).limit(limit).all()
    return {"items": [_to_dict(i) for i in items], "total": len(items)}


@router.post("/logistics/returns", status_code=201)
def create_return(
    data: dict,
    db: Session = Depends(get_db),
    current_user=Depends(check_permission("delivery", "create")),
):
    from models.thai_ops import ReturnOrder
    from utils.seq import next_seq_no, make_daily_prefix
    prefix = make_daily_prefix("RT")
    return_no = next_seq_no(db, ReturnOrder, ReturnOrder.return_no, prefix)
    obj = ReturnOrder(**data, return_no=return_no, created_by=current_user.id)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return _to_dict(obj)


@router.patch("/logistics/returns/{rid}")
def patch_return(
    rid: UUID,
    data: dict,
    db: Session = Depends(get_db),
    current_user=Depends(check_permission("delivery", "update")),
):
    from models.thai_ops import ReturnOrder
    obj = db.query(ReturnOrder).filter(ReturnOrder.id == rid).first()
    if not obj:
        raise HTTPException(status_code=404, detail="退貨單不存在")
    for k, v in data.items():
        if hasattr(obj, k):
            setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    return _to_dict(obj)


# ──────────────────────────────────────────────────────────
# 工具函數
# ──────────────────────────────────────────────────────────

def _to_dict(obj) -> dict:
    d = {k: v for k, v in obj.__dict__.items() if not k.startswith("_")}
    for k, v in d.items():
        if isinstance(v, uuid.UUID):
            d[k] = str(v)
        elif isinstance(v, datetime):
            d[k] = v.isoformat()
    return d
