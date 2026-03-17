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
    customer_id: Optional[UUID] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    db: Session = Depends(get_db),
    _:  User    = Depends(check_permission("payment", "read")),
):
    q = db.query(PaymentRecord)
    if customer_id:
        q = q.filter(PaymentRecord.customer_id == customer_id)
    if status_filter:
        q = q.filter(PaymentRecord.status == status_filter)
    return q.order_by(PaymentRecord.payment_date.desc()).all()


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
    db.commit()
    db.refresh(record)
    return record
