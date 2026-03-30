"""
WP5：應付帳款 API

  GET    /finance/ap                - AP 列表
  POST   /finance/ap                - 建立 AP
  GET    /finance/ap/:id            - AP 詳情
  PUT    /finance/ap/:id            - 更新 AP（付款）
  GET    /finance/ap/aging          - 帳齡分析
"""
from uuid import UUID
from typing import List, Optional
from datetime import date
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func

from database import get_db
from models.user import User
from models.supplier import Supplier
from models.finance import AccountPayable, AP_STATUSES
from schemas.finance import APCreate, APUpdate, APOut
from utils.dependencies import check_permission

router = APIRouter(prefix="/finance", tags=["財務管理"])


def _gen_ap_no(db: Session) -> str:
    date_str = date.today().strftime("%Y%m%d")
    prefix = f"AP-{date_str}-"
    count = db.query(func.count(AccountPayable.id)).filter(
        AccountPayable.ap_no.like(f"{prefix}%")
    ).scalar()
    return f"{prefix}{str(count + 1).zfill(3)}"


def _ap_to_out(ap: AccountPayable) -> APOut:
    days_overdue = None
    if ap.due_date and ap.status != "settled":
        diff = (date.today() - ap.due_date).days
        days_overdue = max(0, diff)
    return APOut(
        id=str(ap.id), ap_no=ap.ap_no,
        supplier_id=str(ap.supplier_id),
        supplier_name=ap.supplier.name if ap.supplier else None,
        source_type=ap.source_type,
        source_id=str(ap.source_id) if ap.source_id else None,
        original_amount_thb=float(ap.original_amount_thb) if ap.original_amount_thb else None,
        original_amount_twd=float(ap.original_amount_twd) if ap.original_amount_twd else None,
        paid_amount_thb=float(ap.paid_amount_thb) if ap.paid_amount_thb else None,
        paid_amount_twd=float(ap.paid_amount_twd) if ap.paid_amount_twd else None,
        outstanding_amount_thb=float(ap.outstanding_amount_thb) if ap.outstanding_amount_thb else None,
        outstanding_amount_twd=float(ap.outstanding_amount_twd) if ap.outstanding_amount_twd else None,
        due_date=ap.due_date, payment_terms=ap.payment_terms,
        status=ap.status, days_overdue=days_overdue,
        last_payment_date=ap.last_payment_date,
        note=ap.note, created_at=ap.created_at,
    )


@router.get("/ap", response_model=List[APOut])
def list_ap(
    status_filter: Optional[str]  = Query(None, alias="status"),
    supplier_id:   Optional[UUID] = Query(None),
    skip:          int = 0,
    limit:         int = 100,
    db:            Session = Depends(get_db),
    _:             User = Depends(check_permission("ap", "view")),
):
    q = db.query(AccountPayable).options(joinedload(AccountPayable.supplier))
    if status_filter:
        q = q.filter(AccountPayable.status == status_filter)
    if supplier_id:
        q = q.filter(AccountPayable.supplier_id == supplier_id)
    aps = q.order_by(AccountPayable.created_at.desc()).offset(skip).limit(limit).all()
    return [_ap_to_out(ap) for ap in aps]


@router.post("/ap", response_model=APOut, status_code=status.HTTP_201_CREATED)
def create_ap(
    payload:      APCreate,
    db:           Session = Depends(get_db),
    current_user: User = Depends(check_permission("ap", "create")),
):
    ap_no = _gen_ap_no(db)
    ap = AccountPayable(
        ap_no=ap_no,
        supplier_id=payload.supplier_id,
        source_type=payload.source_type,
        source_id=payload.source_id,
        original_amount_thb=payload.original_amount_thb,
        original_amount_twd=payload.original_amount_twd,
        outstanding_amount_thb=payload.original_amount_thb,
        outstanding_amount_twd=payload.original_amount_twd,
        due_date=payload.due_date,
        payment_terms=payload.payment_terms,
        note=payload.note,
        created_by=current_user.id,
    )
    db.add(ap)
    db.commit()
    db.refresh(ap)
    ap = db.query(AccountPayable).options(joinedload(AccountPayable.supplier)).filter(AccountPayable.id == ap.id).first()
    return _ap_to_out(ap)


@router.get("/ap/{ap_id}", response_model=APOut)
def get_ap(
    ap_id: UUID,
    db:    Session = Depends(get_db),
    _:     User = Depends(check_permission("ap", "view")),
):
    ap = db.query(AccountPayable).options(joinedload(AccountPayable.supplier)).filter(AccountPayable.id == ap_id).first()
    if not ap:
        raise HTTPException(status_code=404, detail="應付帳款不存在")
    return _ap_to_out(ap)


@router.put("/ap/{ap_id}", response_model=APOut)
def update_ap(
    ap_id:   UUID,
    payload: APUpdate,
    db:      Session = Depends(get_db),
    _:       User = Depends(check_permission("ap", "edit")),
):
    ap = db.query(AccountPayable).filter(AccountPayable.id == ap_id).first()
    if not ap:
        raise HTTPException(status_code=404, detail="應付帳款不存在")

    if payload.paid_amount_thb is not None:
        ap.paid_amount_thb = payload.paid_amount_thb
        if ap.original_amount_thb:
            ap.outstanding_amount_thb = ap.original_amount_thb - payload.paid_amount_thb
        ap.last_payment_date = date.today()
    if payload.paid_amount_twd is not None:
        ap.paid_amount_twd = payload.paid_amount_twd
        if ap.original_amount_twd:
            ap.outstanding_amount_twd = ap.original_amount_twd - payload.paid_amount_twd
        ap.last_payment_date = date.today()

    # 自動判斷結清
    thb_settled = (ap.outstanding_amount_thb is None or float(ap.outstanding_amount_thb or 0) <= 0)
    twd_settled = (ap.outstanding_amount_twd is None or float(ap.outstanding_amount_twd or 0) <= 0)
    if thb_settled and twd_settled:
        ap.status = "settled"
    elif float(ap.paid_amount_thb or 0) > 0 or float(ap.paid_amount_twd or 0) > 0:
        ap.status = "partial"

    if payload.due_date is not None:
        ap.due_date = payload.due_date
    if payload.status is not None:
        ap.status = payload.status
    if payload.note is not None:
        ap.note = payload.note

    db.commit()
    ap = db.query(AccountPayable).options(joinedload(AccountPayable.supplier)).filter(AccountPayable.id == ap_id).first()
    return _ap_to_out(ap)


@router.get("/ap/aging")
def ap_aging(
    db: Session = Depends(get_db),
    _:  User = Depends(check_permission("ap", "view")),
):
    """應付帳款帳齡分析"""
    today = date.today()
    aps = db.query(AccountPayable).options(
        joinedload(AccountPayable.supplier)
    ).filter(
        AccountPayable.status.in_(["pending", "partial", "overdue"])
    ).all()

    buckets = {"current": 0, "1_30": 0, "31_60": 0, "61_90": 0, "over_90": 0}
    for ap in aps:
        outstanding = float(ap.outstanding_amount_thb or ap.outstanding_amount_twd or 0)
        if ap.due_date:
            days = (today - ap.due_date).days
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

    return {
        "buckets": {k: round(v, 2) for k, v in buckets.items()},
        "total_outstanding": round(sum(buckets.values()), 2),
        "count": len(aps),
    }
