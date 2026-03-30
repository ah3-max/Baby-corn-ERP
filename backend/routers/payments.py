"""
收付款管理 API
GET    /payments          - 付款列表
POST   /payments          - 新增付款
GET    /payments/{id}     - 付款詳情
POST   /payments/{id}/confirm - 確認付款
"""
from uuid import UUID
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from database import get_db
from models.user import User
from models.payment import PaymentRecord
from schemas.payment import PaymentCreate, PaymentUpdate, PaymentOut
from utils.dependencies import check_permission

router = APIRouter(prefix="/payments", tags=["收付款"])


@router.get("", response_model=List[PaymentOut])
def list_payments(
    customer_id:   Optional[UUID] = Query(None),
    status_filter: Optional[str]  = Query(None, alias="status"),
    skip:          int = 0,
    limit:         int = Query(100, le=500),
    db: Session = Depends(get_db),
    _:  User    = Depends(check_permission("payment", "read")),
):
    q = db.query(PaymentRecord)
    if customer_id:
        q = q.filter(PaymentRecord.customer_id == customer_id)
    if status_filter:
        q = q.filter(PaymentRecord.status == status_filter)
    return q.order_by(PaymentRecord.payment_date.desc()).offset(skip).limit(limit).all()


@router.get("/{payment_id}", response_model=PaymentOut)
def get_payment(
    payment_id: UUID,
    db: Session = Depends(get_db),
    _:  User    = Depends(check_permission("payment", "read")),
):
    record = db.query(PaymentRecord).filter(PaymentRecord.id == payment_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="付款記錄不存在")
    return record


@router.post("", response_model=PaymentOut, status_code=status.HTTP_201_CREATED)
def create_payment(
    payload:      PaymentCreate,
    db:           Session = Depends(get_db),
    current_user: User    = Depends(check_permission("payment", "create")),
):
    record = PaymentRecord(**payload.model_dump(), created_by=current_user.id)
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.post("/{payment_id}/confirm", response_model=PaymentOut)
def confirm_payment(
    payment_id:   UUID,
    db:           Session = Depends(get_db),
    current_user: User    = Depends(check_permission("payment", "update")),
):
    """確認付款"""
    record = db.query(PaymentRecord).filter(PaymentRecord.id == payment_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="付款記錄不存在")
    if record.status == "confirmed":
        raise HTTPException(status_code=400, detail="此付款已確認")
    record.status = "confirmed"
    record.confirmed_by = current_user.id
    record.confirmed_at = datetime.utcnow()

    # ─── 自動沖銷關聯客戶的最舊未結 AR ───
    from models.finance import AccountReceivable
    from datetime import date
    if record.customer_id:
        pending_ars = (
            db.query(AccountReceivable)
            .filter(
                AccountReceivable.customer_id == record.customer_id,
                AccountReceivable.status.in_(["pending", "partial", "overdue"]),
            )
            .order_by(AccountReceivable.due_date.asc().nullslast(), AccountReceivable.created_at.asc())
            .all()
        )
        remaining_payment = float(record.amount_twd)
        for ar in pending_ars:
            if remaining_payment <= 0:
                break
            outstanding = float(ar.outstanding_amount_twd)
            apply_amount = min(remaining_payment, outstanding)
            ar.paid_amount_twd = float(ar.paid_amount_twd) + apply_amount
            ar.outstanding_amount_twd = float(ar.outstanding_amount_twd) - apply_amount
            ar.last_payment_date = date.today()
            if ar.outstanding_amount_twd <= 0:
                ar.status = "settled"
            elif float(ar.paid_amount_twd) > 0:
                ar.status = "partial"
            remaining_payment -= apply_amount

    db.commit()
    db.refresh(record)
    return record
