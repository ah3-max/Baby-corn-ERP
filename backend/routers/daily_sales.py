"""
每日市場銷售 API
GET    /daily-sales                     - 銷售列表（可依日期、市場篩選）
POST   /daily-sales                     - 新增每日銷售
GET    /daily-sales/{id}                - 銷售詳情
PUT    /daily-sales/{id}                - 編輯銷售
DELETE /daily-sales/{id}                - 刪除銷售

GET    /market-prices                   - 市場行情列表
POST   /market-prices                   - 新增行情
"""
import re
from uuid import UUID
from datetime import date, timedelta
from decimal import Decimal
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func

from database import get_db
from models.user import User
from models.daily_sale import DailySale, DailySaleItem, MarketPrice
from models.inventory import InventoryLot, InventoryTransaction
from models.finance import AccountReceivable
from models.customer import Customer
from schemas.daily_sale import (
    DailySaleCreate, DailySaleUpdate, DailySaleOut,
    MarketPriceCreate, MarketPriceOut,
)
from utils.dependencies import check_permission

router = APIRouter(tags=["每日市場銷售"])


# ─── 每日銷售 ─────────────────────────────────────────

@router.get("/daily-sales", response_model=List[DailySaleOut])
def list_daily_sales(
    sale_date:   Optional[date] = Query(None),
    market_code: Optional[str]  = Query(None),
    customer_id: Optional[UUID] = Query(None),
    date_from:   Optional[date] = Query(None),
    date_to:     Optional[date] = Query(None),
    db: Session = Depends(get_db),
    _:  User    = Depends(check_permission("daily_sale", "read")),
):
    q = db.query(DailySale).options(
        joinedload(DailySale.items),
        joinedload(DailySale.customer),
    )
    if sale_date:
        q = q.filter(DailySale.sale_date == sale_date)
    if market_code:
        q = q.filter(DailySale.market_code == market_code)
    if customer_id:
        q = q.filter(DailySale.customer_id == customer_id)
    if date_from:
        q = q.filter(DailySale.sale_date >= date_from)
    if date_to:
        q = q.filter(DailySale.sale_date <= date_to)
    return q.order_by(DailySale.sale_date.desc(), DailySale.market_code).all()


@router.get("/daily-sales/{sale_id}", response_model=DailySaleOut)
def get_daily_sale(
    sale_id: UUID,
    db: Session = Depends(get_db),
    _:  User    = Depends(check_permission("daily_sale", "read")),
):
    sale = (
        db.query(DailySale)
        .options(joinedload(DailySale.items), joinedload(DailySale.customer))
        .filter(DailySale.id == sale_id)
        .first()
    )
    if not sale:
        raise HTTPException(status_code=404, detail="銷售記錄不存在")
    return sale


@router.post("/daily-sales", response_model=DailySaleOut, status_code=status.HTTP_201_CREATED)
def create_daily_sale(
    payload:      DailySaleCreate,
    db:           Session = Depends(get_db),
    current_user: User    = Depends(check_permission("daily_sale", "create")),
):
    """新增每日銷售，自動扣減庫存"""
    # 建立主表
    sale = DailySale(
        sale_date=payload.sale_date,
        market_code=payload.market_code,
        customer_id=payload.customer_id,
        consignee_name=payload.consignee_name,
        notes=payload.notes,
        created_by=current_user.id,
    )
    db.add(sale)
    db.flush()

    total_kg = Decimal("0")
    total_boxes = 0
    total_amount = Decimal("0")

    # 預先取得成本快照函數
    from services.cost_automation import get_batch_cost_per_kg, refresh_cost_sheet

    for item_data in payload.items:
        total_twd = item_data.quantity_kg * item_data.unit_price_twd
        # 鎖定成本快照
        cost_snapshot = get_batch_cost_per_kg(db, item_data.batch_id) if item_data.batch_id else None
        item = DailySaleItem(
            daily_sale_id=sale.id,
            batch_id=item_data.batch_id,
            lot_id=item_data.lot_id,
            size_grade=item_data.size_grade,
            quantity_boxes=item_data.quantity_boxes,
            quantity_kg=item_data.quantity_kg,
            unit_price_twd=item_data.unit_price_twd,
            total_amount_twd=total_twd,
            cost_per_kg_twd=cost_snapshot,
            notes=item_data.notes,
        )
        db.add(item)

        total_kg += item_data.quantity_kg
        total_boxes += (item_data.quantity_boxes or 0)
        total_amount += total_twd

        # 自動扣減庫存（如有指定 lot_id）
        if item_data.lot_id:
            lot = db.query(InventoryLot).filter(InventoryLot.id == item_data.lot_id).with_for_update().first()
            if lot:
                available = float(lot.current_weight_kg)
                deduct    = float(item_data.quantity_kg)
                if deduct > available:
                    raise HTTPException(
                        status_code=400,
                        detail=f"庫存不足：批號 {lot.id} 現有 {available:.3f} kg，"
                               f"無法扣減 {deduct:.3f} kg",
                    )
                lot.current_weight_kg = round(available - deduct, 3)
                lot.shipped_weight_kg = float(lot.shipped_weight_kg) + float(item_data.quantity_kg)
                if item_data.quantity_boxes and lot.current_boxes is not None:
                    lot.current_boxes -= item_data.quantity_boxes
                    lot.shipped_boxes = (lot.shipped_boxes or 0) + item_data.quantity_boxes
                if float(lot.current_weight_kg) <= 0:
                    lot.status = "depleted"
                elif float(lot.current_weight_kg) / float(lot.initial_weight_kg) < 0.2:
                    lot.status = "low_stock"

                db.add(InventoryTransaction(
                    lot_id=lot.id,
                    txn_type="out",
                    weight_kg=item_data.quantity_kg,
                    boxes=item_data.quantity_boxes,
                    reference=f"DS-{payload.sale_date}",
                    reason=f"每日銷售 {payload.market_code}",
                    created_by=current_user.id,
                ))

    sale.total_kg = total_kg
    sale.total_boxes = total_boxes
    sale.total_amount_twd = total_amount

    # 重算關聯批次的成本彙總（含銷售收入）
    batch_ids_set = {item_data.batch_id for item_data in payload.items if item_data.batch_id}
    for bid in batch_ids_set:
        refresh_cost_sheet(db, bid)

    # 自動建立 AR（有客戶且金額 > 0）
    if payload.customer_id and total_amount > 0:
        customer = db.query(Customer).filter(Customer.id == payload.customer_id).first()
        terms = (customer.payment_terms or "NET7").strip().upper() if customer else "NET7"
        net_match = re.match(r"NET(\d+)", terms)
        if net_match:
            due_date = payload.sale_date + timedelta(days=int(net_match.group(1)))
        else:
            due_date = payload.sale_date  # COD 或無法識別 → 當天到期

        date_str = payload.sale_date.strftime("%Y%m%d")
        prefix = f"AR-{date_str}-"
        count = db.query(func.count(AccountReceivable.id)).filter(
            AccountReceivable.ar_no.like(f"{prefix}%")
        ).scalar()
        ar_no = f"{prefix}{str(count + 1).zfill(3)}"

        ar = AccountReceivable(
            ar_no=ar_no,
            customer_id=payload.customer_id,
            source_type="daily_sale",
            source_id=sale.id,
            original_amount_twd=total_amount,
            paid_amount_twd=Decimal("0"),
            outstanding_amount_twd=total_amount,
            due_date=due_date,
            payment_terms=terms,
            status="pending",
            created_by=current_user.id,
        )
        db.add(ar)

    db.commit()
    return (
        db.query(DailySale)
        .options(joinedload(DailySale.items), joinedload(DailySale.customer))
        .filter(DailySale.id == sale.id)
        .first()
    )


@router.put("/daily-sales/{sale_id}", response_model=DailySaleOut)
def update_daily_sale(
    sale_id: UUID,
    payload: DailySaleUpdate,
    db:      Session = Depends(get_db),
    _:       User    = Depends(check_permission("daily_sale", "update")),
):
    sale = db.query(DailySale).filter(DailySale.id == sale_id).first()
    if not sale:
        raise HTTPException(status_code=404, detail="銷售記錄不存在")
    for k, v in payload.model_dump(exclude_unset=True, exclude={"items"}).items():
        setattr(sale, k, v)
    db.commit()
    return (
        db.query(DailySale)
        .options(joinedload(DailySale.items), joinedload(DailySale.customer))
        .filter(DailySale.id == sale.id)
        .first()
    )


@router.delete("/daily-sales/{sale_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_daily_sale(
    sale_id: UUID,
    db: Session = Depends(get_db),
    _:  User    = Depends(check_permission("daily_sale", "delete")),
):
    sale = db.query(DailySale).options(
        joinedload(DailySale.items)
    ).filter(DailySale.id == sale_id).first()
    if not sale:
        raise HTTPException(status_code=404, detail="銷售記錄不存在")

    # ─── 回滾庫存扣減 ───
    from services.cost_automation import refresh_cost_sheet
    batch_ids_to_refresh = set()
    for item in sale.items:
        if item.lot_id:
            lot = db.query(InventoryLot).filter(InventoryLot.id == item.lot_id).first()
            if lot:
                lot.current_weight_kg = float(lot.current_weight_kg) + float(item.quantity_kg)
                lot.shipped_weight_kg = max(0, float(lot.shipped_weight_kg) - float(item.quantity_kg))
                if item.quantity_boxes and lot.current_boxes is not None:
                    lot.current_boxes += item.quantity_boxes
                    lot.shipped_boxes = max(0, (lot.shipped_boxes or 0) - item.quantity_boxes)
                # 恢復狀態
                if lot.status in ("depleted", "low_stock"):
                    if float(lot.current_weight_kg) > 0:
                        ratio = float(lot.current_weight_kg) / float(lot.initial_weight_kg) if float(lot.initial_weight_kg) > 0 else 1
                        lot.status = "low_stock" if ratio < 0.2 else "active"
                # 刪除對應的 out 異動記錄
                db.query(InventoryTransaction).filter(
                    InventoryTransaction.lot_id == lot.id,
                    InventoryTransaction.reference == f"DS-{sale.sale_date}",
                    InventoryTransaction.txn_type == "out",
                ).delete()
        if item.batch_id:
            batch_ids_to_refresh.add(item.batch_id)

    db.delete(sale)

    # 重算關聯批次的成本彙總
    for bid in batch_ids_to_refresh:
        refresh_cost_sheet(db, bid)

    db.commit()


# ─── 市場行情 ─────────────────────────────────────────

@router.get("/market-prices", response_model=List[MarketPriceOut])
def list_market_prices(
    market_code: Optional[str]  = Query(None),
    date_from:   Optional[date] = Query(None),
    date_to:     Optional[date] = Query(None),
    limit:       int            = Query(30, le=365),
    db: Session = Depends(get_db),
    _:  User    = Depends(check_permission("daily_sale", "read")),
):
    q = db.query(MarketPrice)
    if market_code:
        q = q.filter(MarketPrice.market_code == market_code)
    if date_from:
        q = q.filter(MarketPrice.price_date >= date_from)
    if date_to:
        q = q.filter(MarketPrice.price_date <= date_to)
    return q.order_by(MarketPrice.price_date.desc()).limit(limit).all()


@router.post("/market-prices", response_model=MarketPriceOut, status_code=status.HTTP_201_CREATED)
def create_market_price(
    payload:      MarketPriceCreate,
    db:           Session = Depends(get_db),
    current_user: User    = Depends(check_permission("daily_sale", "create")),
):
    price = MarketPrice(**payload.model_dump(), recorded_by=current_user.id)
    db.add(price)
    db.commit()
    db.refresh(price)
    return price
