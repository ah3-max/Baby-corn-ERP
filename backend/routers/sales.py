"""
銷售管理 API
GET  /sales         - 列表
POST /sales         - 建立銷售訂單（含品項）
GET  /sales/:id     - 詳情
PUT  /sales/:id     - 更新
"""
from uuid import UUID
from typing import List, Optional
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func

from database import get_db
from models.user import User
from models.sales import SalesOrder, SalesOrderItem, SALES_STATUSES
from models.customer import Customer
from models.batch import Batch
from models.inventory import InventoryLot, InventoryTransaction
from schemas.sales import SalesOrderCreate, SalesOrderUpdate, SalesOrderOut
from utils.dependencies import check_permission

router = APIRouter(prefix="/sales", tags=["銷售管理"])


def _generate_order_no(db: Session) -> str:
    from datetime import date
    date_str = date.today().strftime("%Y%m%d")
    prefix   = f"SO-{date_str}-"
    count    = db.query(func.count(SalesOrder.id)).filter(
        SalesOrder.order_no.like(f"{prefix}%")
    ).scalar()
    return f"{prefix}{str(count + 1).zfill(3)}"


def _load_order(db: Session, order_id: UUID) -> SalesOrder:
    o = (
        db.query(SalesOrder)
        .options(
            joinedload(SalesOrder.customer),
            joinedload(SalesOrder.items).joinedload(SalesOrderItem.batch),
        )
        .filter(SalesOrder.id == order_id)
        .first()
    )
    if not o:
        raise HTTPException(status_code=404, detail="銷售訂單不存在")
    return o


@router.get("", response_model=List[SalesOrderOut])
def list_sales(
    status_filter: Optional[str]  = Query(None, alias="status"),
    customer_id:   Optional[UUID] = Query(None),
    batch_id:      Optional[UUID] = Query(None),
    skip:          int = 0,
    limit:         int = 100,
    db:            Session = Depends(get_db),
    _:             User = Depends(check_permission("sales", "view")),
):
    q = (
        db.query(SalesOrder)
        .options(
            joinedload(SalesOrder.customer),
            joinedload(SalesOrder.items).joinedload(SalesOrderItem.batch),
        )
    )
    if status_filter:
        q = q.filter(SalesOrder.status == status_filter)
    if customer_id:
        q = q.filter(SalesOrder.customer_id == customer_id)
    if batch_id:
        # 篩選包含指定批次的銷售訂單
        q = q.filter(SalesOrder.items.any(SalesOrderItem.batch_id == batch_id))
    return q.order_by(SalesOrder.created_at.desc()).offset(skip).limit(limit).all()


@router.post("", response_model=SalesOrderOut, status_code=status.HTTP_201_CREATED)
def create_sales(
    payload:      SalesOrderCreate,
    db:           Session = Depends(get_db),
    current_user: User = Depends(check_permission("sales", "create")),
):
    if not db.query(Customer).filter(Customer.id == payload.customer_id).first():
        raise HTTPException(status_code=404, detail="客戶不存在")

    order_no    = _generate_order_no(db)
    total       = sum((item.quantity_kg * item.unit_price_twd) for item in payload.items)

    order = SalesOrder(
        order_no         = order_no,
        customer_id      = payload.customer_id,
        order_date       = payload.order_date,
        delivery_date    = payload.delivery_date,
        total_amount_twd = total,
        note             = payload.note,
        status           = "draft",
        created_by       = current_user.id,
    )
    db.add(order)
    db.flush()

    for item in payload.items:
        # 驗證批次存在且庫存足夠
        batch = db.query(Batch).filter(Batch.id == item.batch_id).first()
        if not batch:
            raise HTTPException(status_code=404, detail=f"批次不存在：{item.batch_id}")
        if float(batch.current_weight) < float(item.quantity_kg):
            raise HTTPException(
                status_code=400,
                detail=f"批次 {batch.batch_no} 現有重量 {float(batch.current_weight):.1f} kg，"
                       f"不足以銷售 {float(item.quantity_kg):.1f} kg"
            )

        db.add(SalesOrderItem(
            sales_order_id   = order.id,
            batch_id         = item.batch_id,
            quantity_kg      = item.quantity_kg,
            unit_price_twd   = item.unit_price_twd,
            total_amount_twd = item.quantity_kg * item.unit_price_twd,
            note             = item.note,
        ))

        # 扣減批次重量
        batch.current_weight = float(batch.current_weight) - float(item.quantity_kg)

    db.commit()
    return _load_order(db, order.id)


@router.get("/{order_id}", response_model=SalesOrderOut)
def get_sales(
    order_id: UUID,
    db:       Session = Depends(get_db),
    _:        User = Depends(check_permission("sales", "view")),
):
    return _load_order(db, order_id)


@router.put("/{order_id}", response_model=SalesOrderOut)
def update_sales(
    order_id: UUID,
    payload:  SalesOrderUpdate,
    db:       Session = Depends(get_db),
    _:        User = Depends(check_permission("sales", "edit")),
):
    o = db.query(SalesOrder).filter(SalesOrder.id == order_id).first()
    if not o:
        raise HTTPException(status_code=404, detail="銷售訂單不存在")
    if o.status not in ("draft", "confirmed"):
        raise HTTPException(status_code=400, detail="僅草稿或已確認的訂單可修改")

    # ── 更新基本欄位 ──
    basic_fields = {"customer_id", "order_date", "delivery_date", "note"}
    for field, value in payload.model_dump(exclude_unset=True).items():
        if field in basic_fields:
            setattr(o, field, value)

    # ── 替換品項（若有傳入） ──
    if payload.items is not None:
        # 1. 還原舊品項扣減的批次重量
        old_items = db.query(SalesOrderItem).filter(SalesOrderItem.sales_order_id == order_id).all()
        for old in old_items:
            batch = db.query(Batch).filter(Batch.id == old.batch_id).first()
            if batch:
                batch.current_weight = float(batch.current_weight) + float(old.quantity_kg)
            db.delete(old)
        db.flush()

        # 2. 驗證並建立新品項
        valid_items = [i for i in payload.items if i.batch_id and i.quantity_kg and i.unit_price_twd]
        if not valid_items:
            raise HTTPException(status_code=400, detail="至少需要一個訂單品項")

        total = 0
        for item in valid_items:
            batch = db.query(Batch).filter(Batch.id == item.batch_id).first()
            if not batch:
                raise HTTPException(status_code=404, detail=f"批次不存在：{item.batch_id}")
            if float(batch.current_weight) < float(item.quantity_kg):
                raise HTTPException(
                    status_code=400,
                    detail=f"批次 {batch.batch_no} 現有重量 {float(batch.current_weight):.1f} kg，"
                           f"不足以銷售 {float(item.quantity_kg):.1f} kg"
                )
            db.add(SalesOrderItem(
                sales_order_id   = o.id,
                batch_id         = item.batch_id,
                quantity_kg      = item.quantity_kg,
                unit_price_twd   = item.unit_price_twd,
                total_amount_twd = item.quantity_kg * item.unit_price_twd,
                note             = item.note,
            ))
            batch.current_weight = float(batch.current_weight) - float(item.quantity_kg)
            total += float(item.quantity_kg) * float(item.unit_price_twd)

        o.total_amount_twd = total

    db.commit()
    return _load_order(db, order_id)


STATUS_NEXT = {
    "draft":     "confirmed",
    "confirmed": "delivered",
    "delivered": "invoiced",
    "invoiced":  "closed",
}


@router.delete("/{order_id}", status_code=204)
def delete_sales(
    order_id: UUID,
    db:       Session = Depends(get_db),
    _:        User = Depends(check_permission("sales", "delete")),
):
    """
    刪除銷售訂單（僅允許 draft 或 confirmed 狀態）。
    刪除時還原已扣減的批次重量。
    """
    o = db.query(SalesOrder).options(
        joinedload(SalesOrder.items)
    ).filter(SalesOrder.id == order_id).first()
    if not o:
        raise HTTPException(status_code=404, detail="銷售訂單不存在")
    if o.status not in ("draft", "confirmed"):
        raise HTTPException(
            status_code=400,
            detail="僅可刪除草稿或已確認的訂單，已出貨/已開票/已結案的訂單無法刪除",
        )

    # 還原批次重量
    for item in o.items:
        batch = db.query(Batch).filter(Batch.id == item.batch_id).first()
        if batch:
            batch.current_weight = float(batch.current_weight) + float(item.quantity_kg)

    db.delete(o)
    db.commit()


def _fifo_deduct_inventory(db: Session, order: SalesOrder, user_id) -> list[str]:
    """
    FIFO 扣庫存 — 當銷售訂單推進至 delivered 時觸發。
    依每筆品項的批次，從最舊的庫存批號（received_date ASC）開始扣減，
    產生 out 異動記錄，並更新庫存批次狀態。
    回傳警告訊息列表（例如庫存不足時）。
    """
    from sqlalchemy import and_

    warnings: list[str] = []
    items = db.query(SalesOrderItem).filter(
        SalesOrderItem.sales_order_id == order.id
    ).all()

    for item in items:
        remaining = float(item.quantity_kg)

        # 取該批次所有有效庫存批號，FIFO 排序
        lots = (
            db.query(InventoryLot)
            .filter(
                and_(
                    InventoryLot.batch_id == item.batch_id,
                    InventoryLot.status.in_(["active", "low_stock"]),
                )
            )
            .order_by(InventoryLot.received_date.asc(), InventoryLot.created_at.asc())
            .all()
        )

        for lot in lots:
            if remaining <= 0:
                break

            available = float(lot.current_weight_kg)
            deduct    = min(available, remaining)

            # 扣減庫存批次
            lot.current_weight_kg = round(available - deduct, 3)
            lot.shipped_weight_kg = round(float(lot.shipped_weight_kg) + deduct, 3)

            # 更新批次狀態
            if float(lot.current_weight_kg) <= 0:
                lot.status = "depleted"
            elif float(lot.initial_weight_kg) > 0 and \
                 float(lot.current_weight_kg) / float(lot.initial_weight_kg) < 0.2:
                lot.status = "low_stock"

            # 產生 out 異動記錄
            db.add(InventoryTransaction(
                lot_id     = lot.id,
                txn_type   = "out",
                weight_kg  = deduct,
                reference  = order.order_no,
                reason     = f"銷售出貨 {order.order_no}",
                created_by = user_id,
            ))

            remaining -= deduct

        # 若庫存批次不足以涵蓋出貨量（貨物尚未正式入庫），記錄警告但不阻擋
        if remaining > 0.001:
            batch = db.query(Batch).filter(Batch.id == item.batch_id).first()
            batch_no = batch.batch_no if batch else str(item.batch_id)
            warnings.append(
                f"批次 {batch_no} 庫存批號不足，有 {remaining:.1f} kg 未能從庫存扣減（貨物可能尚未入庫）"
            )

    return warnings


@router.put("/{order_id}/advance", response_model=SalesOrderOut)
def advance_sales(
    order_id:     UUID,
    db:           Session = Depends(get_db),
    current_user: User = Depends(check_permission("sales", "edit")),
):
    o = db.query(SalesOrder).filter(SalesOrder.id == order_id).first()
    if not o:
        raise HTTPException(status_code=404, detail="銷售訂單不存在")
    next_status = STATUS_NEXT.get(o.status)
    if not next_status:
        raise HTTPException(status_code=400, detail="此訂單已無法再推進狀態")

    # 推進至 delivered → 觸發 FIFO 庫存扣減，並自動將清空的批次設為 sold
    if next_status == "delivered":
        _fifo_deduct_inventory(db, o, current_user.id)

        # 若批次重量已清零，自動將批次狀態推進至 sold
        items = db.query(SalesOrderItem).filter(
            SalesOrderItem.sales_order_id == o.id
        ).all()
        for item in items:
            batch = db.query(Batch).filter(Batch.id == item.batch_id).first()
            if batch and float(batch.current_weight) <= 0 and batch.status == "in_stock":
                batch.status = "sold"

    o.status = next_status
    db.commit()
    return _load_order(db, order_id)
