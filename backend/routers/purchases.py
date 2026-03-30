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
    from sqlalchemy import text
    db.execute(text("SELECT pg_advisory_xact_lock(hashtext('po_order_no'))"))
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
        joinedload(PurchaseOrder.product_type),
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
        product_type_id=payload.product_type_id,
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
        joinedload(PurchaseOrder.product_type),
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
        joinedload(PurchaseOrder.product_type),
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
        joinedload(PurchaseOrder.product_type),
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
    # 自動帶入品項的保質期（若採購單有指定品項）
    default_shelf_life = 23
    if po.product_type_id:
        from models.product_type import ProductType
        pt = db.query(ProductType).filter(ProductType.id == po.product_type_id).first()
        if pt and pt.shelf_life_days:
            default_shelf_life = pt.shelf_life_days

    batch = Batch(
        batch_no          = batch_no,
        purchase_order_id = po.id,
        product_type_id   = po.product_type_id,  # 從採購單帶入品項
        initial_weight    = usable,
        current_weight    = usable,
        status            = "processing",
        note              = f"由採購單 {po.order_no} 到廠自動建立",
        created_by        = current_user.id,
        shelf_life_days   = default_shelf_life,
    )
    db.add(batch)
    db.flush()  # 取得 batch.id

    # ─── 自動建立 material 成本事件（採購成本）───
    from services.cost_automation import create_cost_event, get_system_exchange_rate
    ex_rate = get_system_exchange_rate(db)
    material_cost_thb = usable * po.unit_price  # 可用重量 × 單價
    create_cost_event(
        db=db,
        batch_id=batch.id,
        cost_layer="material",
        cost_type="purchase_price",
        description_zh=f"採購成本（{po.order_no}）",
        amount_thb=material_cost_thb,
        exchange_rate=ex_rate,
        quantity=usable,
        unit_cost=po.unit_price,
        unit_label="kg",
        notes=f"供應商: {db.query(Supplier).filter(Supplier.id == po.supplier_id).first().name if po.supplier_id else 'N/A'}",
        recorded_by=current_user.id,
        auto_source="po_arrival",
    )

    # ─── 自動建立應付帳款 AP ───
    from models.finance import AccountPayable
    from datetime import timedelta
    ap_date_str = datetime.utcnow().strftime("%Y%m%d")
    ap_prefix = f"AP-{ap_date_str}-"
    ap_count = db.query(func.count(AccountPayable.id)).filter(
        AccountPayable.ap_no.like(f"{ap_prefix}%")
    ).scalar()
    ap_no = f"{ap_prefix}{str(ap_count + 1).zfill(3)}"

    # 依供應商付款條件計算到期日
    sup = db.query(Supplier).filter(Supplier.id == po.supplier_id).first()
    sup_terms = sup.payment_terms if sup else "NET30"
    days_map = {"COD": 0, "NET7": 7, "NET15": 15, "NET30": 30, "NET60": 60}
    due_days = days_map.get(sup_terms, 30)

    ap = AccountPayable(
        ap_no=ap_no,
        supplier_id=po.supplier_id,
        source_type="purchase_order",
        source_id=po.id,
        original_amount_thb=po.total_amount,
        outstanding_amount_thb=po.total_amount,
        due_date=datetime.utcnow().date() + timedelta(days=due_days),
        payment_terms=sup_terms,
        note=f"採購單 {po.order_no} 到廠自動建立",
        created_by=current_user.id,
    )
    db.add(ap)

    db.commit()

    # 回傳包含自動建立的批次資訊
    po_out = db.query(PurchaseOrder).options(
        joinedload(PurchaseOrder.supplier),
        joinedload(PurchaseOrder.source_farmer),
        joinedload(PurchaseOrder.product_type),
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
