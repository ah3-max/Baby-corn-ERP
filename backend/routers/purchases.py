"""
採購管理 API 路由
GET    /purchases               - 列表（可篩選狀態）
POST   /purchases               - 建立採購單
GET    /purchases/:id           - 詳情
PUT    /purchases/:id           - 更新（到廠前）
PUT    /purchases/:id/status    - 更新狀態
POST   /purchases/:id/arrive    - 到廠確認（自動建立批次）
"""
from uuid import UUID
from typing import List, Optional
from datetime import datetime
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func

from database import get_db
from models.user import User
from models.purchase import PurchaseOrder
from models.batch import Batch
from models.supplier import Supplier
from schemas.purchase import (
    PurchaseOrderCreate, PurchaseOrderUpdate,
    ArrivalConfirm, PurchaseOrderOut, PURCHASE_STATUSES
)
from utils.dependencies import get_current_user, check_permission

router = APIRouter(prefix="/purchases", tags=["採購管理"])


def _generate_order_no(db: Session, order_date) -> str:
    """產生採購編號：PO-YYYYMMDD-XXX"""
    date_str = order_date.strftime("%Y%m%d")
    prefix = f"PO-{date_str}-"
    count = db.query(func.count(PurchaseOrder.id)).filter(
        PurchaseOrder.order_no.like(f"{prefix}%")
    ).scalar()
    return f"{prefix}{str(count + 1).zfill(3)}"


@router.get("", response_model=List[PurchaseOrderOut])
def list_purchases(
    status_filter: Optional[str] = Query(None, alias="status"),
    keyword:       Optional[str] = Query(None),
    skip:          int = 0,
    limit:         int = 100,
    db:            Session = Depends(get_db),
    _:             User = Depends(check_permission("purchase", "view")),
):
    """取得採購單列表"""
    q = db.query(PurchaseOrder).options(
        joinedload(PurchaseOrder.supplier),
        joinedload(PurchaseOrder.source_farmer),
    )
    if status_filter:
        q = q.filter(PurchaseOrder.status == status_filter)
    if keyword:
        q = q.join(Supplier, PurchaseOrder.supplier_id == Supplier.id).filter(
            Supplier.name.ilike(f"%{keyword}%")
        )
    return q.order_by(PurchaseOrder.created_at.desc()).offset(skip).limit(limit).all()


@router.post("", response_model=PurchaseOrderOut, status_code=status.HTTP_201_CREATED)
def create_purchase(
    payload:      PurchaseOrderCreate,
    db:           Session = Depends(get_db),
    current_user: User = Depends(check_permission("purchase", "create")),
):
    """建立採購單"""
    supplier = db.query(Supplier).filter(Supplier.id == payload.supplier_id).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="供應商不存在")

    order_no = _generate_order_no(db, payload.order_date)
    total = payload.estimated_weight * payload.unit_price

    po = PurchaseOrder(
        order_no=order_no,
        order_date=payload.order_date,
        supplier_id=payload.supplier_id,
        source_farmer_id=payload.source_farmer_id,
        estimated_weight=payload.estimated_weight,
        unit_price=payload.unit_price,
        total_amount=total,
        expected_arrival=payload.expected_arrival,
        note=payload.note,
        status="draft",
        created_by=current_user.id,
    )
    db.add(po)
    db.commit()
    db.refresh(po)
    # 重新載入關聯
    return db.query(PurchaseOrder).options(
        joinedload(PurchaseOrder.supplier),
        joinedload(PurchaseOrder.source_farmer),
    ).filter(PurchaseOrder.id == po.id).first()


@router.get("/{po_id}", response_model=PurchaseOrderOut)
def get_purchase(
    po_id: UUID,
    db:    Session = Depends(get_db),
    _:     User = Depends(check_permission("purchase", "view")),
):
    """取得採購單詳情"""
    po = db.query(PurchaseOrder).options(
        joinedload(PurchaseOrder.supplier),
        joinedload(PurchaseOrder.source_farmer),
    ).filter(PurchaseOrder.id == po_id).first()
    if not po:
        raise HTTPException(status_code=404, detail="採購單不存在")
    return po


@router.put("/{po_id}", response_model=PurchaseOrderOut)
def update_purchase(
    po_id:   UUID,
    payload: PurchaseOrderUpdate,
    db:      Session = Depends(get_db),
    _:       User = Depends(check_permission("purchase", "edit")),
):
    """更新採購單（已到廠後不可編輯主資料）"""
    po = db.query(PurchaseOrder).filter(PurchaseOrder.id == po_id).first()
    if not po:
        raise HTTPException(status_code=404, detail="採購單不存在")
    if po.status in ("arrived", "closed"):
        raise HTTPException(status_code=400, detail="已到廠或結案的採購單不可修改")

    data = payload.model_dump(exclude_unset=True)
    # 若重量或單價有變動，重新計算總金額
    new_weight = data.get("estimated_weight", po.estimated_weight)
    new_price  = data.get("unit_price", po.unit_price)
    data["total_amount"] = Decimal(str(new_weight)) * Decimal(str(new_price))

    for field, value in data.items():
        setattr(po, field, value)

    db.commit()
    db.refresh(po)
    return db.query(PurchaseOrder).options(
        joinedload(PurchaseOrder.supplier),
        joinedload(PurchaseOrder.source_farmer),
    ).filter(PurchaseOrder.id == po_id).first()


@router.put("/{po_id}/status")
def update_status(
    po_id:  UUID,
    status_val: str = Query(..., alias="status"),
    db:     Session = Depends(get_db),
    _:      User = Depends(check_permission("purchase", "edit")),
):
    """更新採購單狀態"""
    if status_val not in PURCHASE_STATUSES:
        raise HTTPException(status_code=400, detail=f"無效的狀態：{status_val}")
    po = db.query(PurchaseOrder).filter(PurchaseOrder.id == po_id).first()
    if not po:
        raise HTTPException(status_code=404, detail="採購單不存在")
    po.status = status_val
    db.commit()
    return {"message": "狀態已更新", "status": status_val}


def _generate_batch_no(db: Session) -> str:
    """產生批次編號：BT-YYYYMMDD-XXX"""
    date_str = datetime.utcnow().strftime("%Y%m%d")
    prefix   = f"BT-{date_str}-"
    count    = db.query(func.count(Batch.id)).filter(
        Batch.batch_no.like(f"{prefix}%")
    ).scalar()
    return f"{prefix}{str(count + 1).zfill(3)}"


@router.post("/{po_id}/arrive")
def confirm_arrival(
    po_id:        UUID,
    payload:      ArrivalConfirm,
    db:           Session = Depends(get_db),
    current_user: User = Depends(check_permission("purchase", "edit")),
):
    """到廠確認：填入實際重量、計算不良率、自動建立批次"""
    po = db.query(PurchaseOrder).filter(PurchaseOrder.id == po_id).first()
    if not po:
        raise HTTPException(status_code=404, detail="採購單不存在")
    if po.status == "arrived":
        raise HTTPException(status_code=400, detail="此採購單已完成到廠確認")

    usable = payload.received_weight - payload.defect_weight
    defect_rate = (
        (payload.defect_weight / payload.received_weight * 100)
        if payload.received_weight > 0 else Decimal("0")
    )

    po.status          = "arrived"
    po.arrived_at      = payload.arrived_at
    po.received_weight = payload.received_weight
    po.defect_weight   = payload.defect_weight
    po.usable_weight   = usable
    po.defect_rate     = round(defect_rate, 2)
    po.arrival_note    = payload.arrival_note

    # ─── 自動建立批次（一條龍：到廠即建批次，省去手動步驟）───
    batch_no = _generate_batch_no(db)
    batch = Batch(
        batch_no          = batch_no,
        purchase_order_id = po.id,
        initial_weight    = usable,        # 直接使用可用重量
        current_weight    = usable,
        status            = "processing",
        note              = f"由採購單 {po.order_no} 到廠自動建立",
        created_by        = current_user.id,
        shelf_life_days   = 23,            # 預設保質期
    )
    db.add(batch)
    db.flush()  # 取得 batch.id

    db.commit()

    # 回傳包含自動建立的批次資訊
    po_out = db.query(PurchaseOrder).options(
        joinedload(PurchaseOrder.supplier),
        joinedload(PurchaseOrder.source_farmer),
    ).filter(PurchaseOrder.id == po_id).first()

    return {
        "purchase_order": PurchaseOrderOut.model_validate(po_out),
        "auto_created_batch": {
            "id":       str(batch.id),
            "batch_no": batch.batch_no,
            "initial_weight": float(batch.initial_weight),
            "status":   batch.status,
        },
    }
