"""
WP5：應收帳款 API

  GET    /finance/ar                - AR 列表
  POST   /finance/ar                - 建立 AR
  GET    /finance/ar/:id            - AR 詳情
  PUT    /finance/ar/:id            - 更新 AR（收款）
  GET    /finance/ar/aging          - 帳齡分析
  GET    /finance/summary           - 財務摘要
  GET    /finance/profit-loss       - 損益表
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
from models.customer import Customer
from models.finance import AccountReceivable, AR_STATUSES
from models.sales import SalesOrder, SalesOrderItem
from models.daily_sale import DailySale, DailySaleItem
from models.payment import PaymentRecord
from models.cost import CostEvent
from models.purchase import PurchaseOrder
from schemas.finance import ARCreate, ARUpdate, AROut
from utils.dependencies import check_permission

router = APIRouter(prefix="/finance", tags=["財務管理"])


def _gen_ar_no(db: Session) -> str:
    date_str = date.today().strftime("%Y%m%d")
    prefix = f"AR-{date_str}-"
    count = db.query(func.count(AccountReceivable.id)).filter(
        AccountReceivable.ar_no.like(f"{prefix}%")
    ).scalar()
    return f"{prefix}{str(count + 1).zfill(3)}"


def _ar_to_out(ar: AccountReceivable) -> AROut:
    days_overdue = None
    if ar.due_date and ar.status != "settled":
        diff = (date.today() - ar.due_date).days
        days_overdue = max(0, diff)
    return AROut(
        id=str(ar.id), ar_no=ar.ar_no,
        customer_id=str(ar.customer_id),
        customer_name=ar.customer.name if ar.customer else None,
        source_type=ar.source_type,
        source_id=str(ar.source_id) if ar.source_id else None,
        original_amount_twd=float(ar.original_amount_twd),
        paid_amount_twd=float(ar.paid_amount_twd),
        outstanding_amount_twd=float(ar.outstanding_amount_twd),
        due_date=ar.due_date, payment_terms=ar.payment_terms,
        status=ar.status, days_overdue=days_overdue,
        last_payment_date=ar.last_payment_date,
        note=ar.note, created_at=ar.created_at,
    )


# ─── AR CRUD ────────────────────────────────────────────

@router.get("/ar", response_model=List[AROut])
def list_ar(
    status_filter: Optional[str]  = Query(None, alias="status"),
    customer_id:   Optional[UUID] = Query(None),
    overdue:       Optional[bool] = Query(None),
    skip:          int = 0,
    limit:         int = 100,
    db:            Session = Depends(get_db),
    _:             User = Depends(check_permission("ar", "view")),
):
    q = db.query(AccountReceivable).options(joinedload(AccountReceivable.customer))
    if status_filter:
        q = q.filter(AccountReceivable.status == status_filter)
    if customer_id:
        q = q.filter(AccountReceivable.customer_id == customer_id)
    if overdue:
        q = q.filter(AccountReceivable.due_date < date.today(), AccountReceivable.status.in_(["pending", "partial"]))
    ars = q.order_by(AccountReceivable.created_at.desc()).offset(skip).limit(limit).all()
    return [_ar_to_out(ar) for ar in ars]


@router.post("/ar", response_model=AROut, status_code=status.HTTP_201_CREATED)
def create_ar(
    payload:      ARCreate,
    db:           Session = Depends(get_db),
    current_user: User = Depends(check_permission("ar", "create")),
):
    ar_no = _gen_ar_no(db)
    ar = AccountReceivable(
        ar_no=ar_no,
        customer_id=payload.customer_id,
        source_type=payload.source_type,
        source_id=payload.source_id,
        original_amount_twd=payload.original_amount_twd,
        outstanding_amount_twd=payload.original_amount_twd,
        due_date=payload.due_date,
        payment_terms=payload.payment_terms,
        note=payload.note,
        created_by=current_user.id,
    )
    db.add(ar)
    db.commit()
    db.refresh(ar)
    ar = db.query(AccountReceivable).options(joinedload(AccountReceivable.customer)).filter(AccountReceivable.id == ar.id).first()
    return _ar_to_out(ar)


@router.get("/ar/{ar_id}", response_model=AROut)
def get_ar(
    ar_id: UUID,
    db:    Session = Depends(get_db),
    _:     User = Depends(check_permission("ar", "view")),
):
    ar = db.query(AccountReceivable).options(joinedload(AccountReceivable.customer)).filter(AccountReceivable.id == ar_id).first()
    if not ar:
        raise HTTPException(status_code=404, detail="應收帳款不存在")
    return _ar_to_out(ar)


@router.put("/ar/{ar_id}", response_model=AROut)
def update_ar(
    ar_id:   UUID,
    payload: ARUpdate,
    db:      Session = Depends(get_db),
    _:       User = Depends(check_permission("ar", "edit")),
):
    ar = db.query(AccountReceivable).filter(AccountReceivable.id == ar_id).first()
    if not ar:
        raise HTTPException(status_code=404, detail="應收帳款不存在")

    if payload.paid_amount_twd is not None:
        ar.paid_amount_twd = payload.paid_amount_twd
        ar.outstanding_amount_twd = ar.original_amount_twd - payload.paid_amount_twd
        ar.last_payment_date = date.today()
        # 自動更新狀態
        if ar.outstanding_amount_twd <= 0:
            ar.status = "settled"
        elif float(ar.paid_amount_twd) > 0:
            ar.status = "partial"

    if payload.due_date is not None:
        ar.due_date = payload.due_date
    if payload.status is not None:
        ar.status = payload.status
    if payload.note is not None:
        ar.note = payload.note

    db.commit()
    ar = db.query(AccountReceivable).options(joinedload(AccountReceivable.customer)).filter(AccountReceivable.id == ar_id).first()
    return _ar_to_out(ar)


# ─── 帳齡分析 ───────────────────────────────────────────

@router.get("/ar/aging")
def ar_aging(
    db: Session = Depends(get_db),
    _:  User = Depends(check_permission("ar", "view")),
):
    """應收帳款帳齡分析"""
    today = date.today()
    ars = db.query(AccountReceivable).options(
        joinedload(AccountReceivable.customer)
    ).filter(
        AccountReceivable.status.in_(["pending", "partial", "overdue"])
    ).all()

    buckets = {"current": 0, "1_30": 0, "31_60": 0, "61_90": 0, "over_90": 0}
    details = []

    for ar in ars:
        outstanding = float(ar.outstanding_amount_twd)
        if ar.due_date:
            days = (today - ar.due_date).days
            if days <= 0:
                buckets["current"] += outstanding
            elif days <= 30:
                buckets["1_30"] += outstanding
            elif days <= 60:
                buckets["31_60"] += outstanding
            elif days <= 90:
                buckets["61_90"] += outstanding
            else:
                buckets["over_90"] += outstanding
        else:
            buckets["current"] += outstanding

        details.append({
            "ar_no": ar.ar_no,
            "customer_name": ar.customer.name if ar.customer else None,
            "original": float(ar.original_amount_twd),
            "outstanding": outstanding,
            "due_date": str(ar.due_date) if ar.due_date else None,
            "days_overdue": max(0, (today - ar.due_date).days) if ar.due_date else 0,
        })

    return {
        "buckets": {k: round(v, 2) for k, v in buckets.items()},
        "total_outstanding": round(sum(buckets.values()), 2),
        "count": len(ars),
        "details": sorted(details, key=lambda x: -x["outstanding"])[:20],
    }


# ─── 財務摘要 ───────────────────────────────────────────

@router.get("/summary")
def finance_summary(
    db: Session = Depends(get_db),
    _:  User = Depends(check_permission("ar", "view")),
):
    """財務摘要"""
    today = date.today()
    month_start = today.replace(day=1)

    # AR 總額
    ar_total = db.query(func.coalesce(func.sum(AccountReceivable.outstanding_amount_twd), 0)).filter(
        AccountReceivable.status.in_(["pending", "partial", "overdue"])
    ).scalar()

    # AR 逾期
    ar_overdue = db.query(func.coalesce(func.sum(AccountReceivable.outstanding_amount_twd), 0)).filter(
        AccountReceivable.status.in_(["pending", "partial"]),
        AccountReceivable.due_date < today,
    ).scalar()

    # AP 總額
    from models.finance import AccountPayable
    ap_total_thb = db.query(func.coalesce(func.sum(AccountPayable.outstanding_amount_thb), 0)).filter(
        AccountPayable.status.in_(["pending", "partial", "overdue"])
    ).scalar()
    ap_total_twd = db.query(func.coalesce(func.sum(AccountPayable.outstanding_amount_twd), 0)).filter(
        AccountPayable.status.in_(["pending", "partial", "overdue"])
    ).scalar()

    # 本月銷售收入
    so_revenue = db.query(func.coalesce(func.sum(SalesOrder.total_amount_twd), 0)).filter(
        SalesOrder.order_date >= month_start
    ).scalar()
    ds_revenue = db.query(func.coalesce(func.sum(DailySale.total_amount_twd), 0)).filter(
        DailySale.sale_date >= month_start
    ).scalar()

    # 本月已確認收款
    confirmed_payments = db.query(func.coalesce(func.sum(PaymentRecord.amount_twd), 0)).filter(
        PaymentRecord.payment_date >= month_start, PaymentRecord.status == "confirmed"
    ).scalar()

    # 本月採購成本
    purchase_cost = db.query(func.coalesce(func.sum(PurchaseOrder.total_amount), 0)).filter(
        PurchaseOrder.order_date >= month_start
    ).scalar()

    return {
        "ar_outstanding_twd": float(ar_total),
        "ar_overdue_twd": float(ar_overdue),
        "ap_outstanding_thb": float(ap_total_thb),
        "ap_outstanding_twd": float(ap_total_twd),
        "month_revenue_twd": float(so_revenue) + float(ds_revenue),
        "month_confirmed_payments_twd": float(confirmed_payments),
        "month_purchase_cost_thb": float(purchase_cost),
    }


# ─── 損益表 ─────────────────────────────────────────────

@router.get("/profit-loss")
def profit_loss(
    date_from: Optional[date] = Query(None),
    date_to:   Optional[date] = Query(None),
    db:        Session = Depends(get_db),
    _:         User = Depends(check_permission("ar", "view")),
):
    """簡易損益表"""
    if not date_from:
        date_from = date.today().replace(day=1)
    if not date_to:
        date_to = date.today()

    # 收入
    so_revenue = db.query(func.coalesce(func.sum(SalesOrder.total_amount_twd), 0)).filter(
        SalesOrder.order_date.between(date_from, date_to)
    ).scalar()
    ds_revenue = db.query(func.coalesce(func.sum(DailySale.total_amount_twd), 0)).filter(
        DailySale.sale_date.between(date_from, date_to)
    ).scalar()
    total_revenue = float(so_revenue) + float(ds_revenue)

    # 成本（按 cost_layer 分組）
    from services.cost_automation import get_system_exchange_rate
    ex_rate = float(get_system_exchange_rate(db))

    cost_by_layer = {}
    events = db.query(
        CostEvent.cost_layer,
        func.sum(CostEvent.amount_twd).label("twd"),
        func.sum(CostEvent.amount_thb).label("thb"),
    ).filter(
        CostEvent.recorded_at.between(
            datetime.combine(date_from, datetime.min.time()),
            datetime.combine(date_to, datetime.max.time()),
        )
    ).group_by(CostEvent.cost_layer).all()

    total_cost = 0
    for layer, twd, thb in events:
        layer_twd = float(twd or 0) + float(thb or 0) * ex_rate
        cost_by_layer[layer] = round(layer_twd, 2)
        total_cost += layer_twd

    gross_profit = total_revenue - total_cost
    margin_pct = round(gross_profit / total_revenue * 100, 1) if total_revenue > 0 else 0

    return {
        "period": {"from": str(date_from), "to": str(date_to)},
        "revenue": {
            "sales_orders_twd": float(so_revenue),
            "daily_sales_twd": float(ds_revenue),
            "total_twd": total_revenue,
        },
        "cost_of_goods": cost_by_layer,
        "total_cost_twd": round(total_cost, 2),
        "gross_profit_twd": round(gross_profit, 2),
        "gross_margin_pct": margin_pct,
    }
