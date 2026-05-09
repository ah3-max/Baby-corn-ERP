"""
財務擴充路由（I-04/05/06/07）

涵蓋：
  /finance/petty-cash/funds     — 零用金基金
  /finance/petty-cash/records   — 零用金記錄 CRUD
  /finance/bank-accounts        — 銀行帳戶
  /finance/bank-transactions    — 銀行交易記錄
"""
import uuid
from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database import get_db
from utils.dependencies import check_permission

router = APIRouter(tags=["財務擴充"])


# ──────────────────────────────────────────────────────────
# I-04/05  零用金
# ──────────────────────────────────────────────────────────

@router.get("/finance/petty-cash/funds")
def list_petty_cash_funds(
    db: Session = Depends(get_db),
    current_user=Depends(check_permission("finance", "read")),
):
    from models.finance_ext import PettyCashFund
    items = db.query(PettyCashFund).filter(PettyCashFund.is_active.is_(True)).all()
    return {"items": [_to_dict(i) for i in items], "total": len(items)}


@router.get("/finance/petty-cash/records")
def list_petty_cash_records(
    status: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = Query(default=50),
    db: Session = Depends(get_db),
    current_user=Depends(check_permission("finance", "read")),
):
    from models.finance_ext import PettyCashRecord
    q = db.query(PettyCashRecord)
    if status:
        q = q.filter(PettyCashRecord.status == status)
    if category:
        q = q.filter(PettyCashRecord.category == category)
    items = q.order_by(PettyCashRecord.expense_date.desc()).limit(limit).all()
    return {"items": [_to_dict(i) for i in items], "total": len(items)}


@router.post("/finance/petty-cash/records", status_code=201)
def create_petty_cash_record(
    data: dict,
    db: Session = Depends(get_db),
    current_user=Depends(check_permission("finance", "create")),
):
    from models.finance_ext import PettyCashRecord
    from utils.seq import next_seq_no, make_daily_prefix
    prefix = make_daily_prefix("PC")
    record_no = next_seq_no(db, PettyCashRecord, PettyCashRecord.record_no, prefix)
    obj = PettyCashRecord(
        **data,
        record_no=record_no,
        status="pending",
        submitted_by=current_user.id,
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return _to_dict(obj)


@router.post("/finance/petty-cash/records/{rid}/approve")
def approve_petty_cash(
    rid: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(check_permission("finance", "approve")),
):
    from models.finance_ext import PettyCashRecord
    obj = db.query(PettyCashRecord).filter(PettyCashRecord.id == rid).first()
    if not obj:
        raise HTTPException(status_code=404, detail="記錄不存在")
    obj.status = "confirmed"
    obj.reviewed_by = current_user.id
    obj.reviewed_at = datetime.utcnow()
    db.commit()
    db.refresh(obj)
    return _to_dict(obj)


# ──────────────────────────────────────────────────────────
# I-06  銀行帳戶
# ──────────────────────────────────────────────────────────

@router.get("/finance/bank-accounts")
def list_bank_accounts(
    db: Session = Depends(get_db),
    current_user=Depends(check_permission("finance", "read")),
):
    from models.finance_ext import BankAccount
    items = db.query(BankAccount).filter(BankAccount.is_active.is_(True)).all()
    return {"items": [_to_dict(i) for i in items], "total": len(items)}


# ──────────────────────────────────────────────────────────
# I-07  銀行交易記錄
# ──────────────────────────────────────────────────────────

@router.get("/finance/bank-transactions")
def list_bank_transactions(
    bank_account_id: Optional[UUID] = None,
    limit: int = Query(default=30),
    db: Session = Depends(get_db),
    current_user=Depends(check_permission("finance", "read")),
):
    from models.finance_ext import BankTransaction
    q = db.query(BankTransaction)
    if bank_account_id:
        q = q.filter(BankTransaction.bank_account_id == bank_account_id)
    items = q.order_by(BankTransaction.transaction_date.desc()).limit(limit).all()
    return {"items": [_to_dict(i) for i in items], "total": len(items)}


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
