"""
QC 管理 API
GET  /qc?batch_id=xxx   - 取得指定批次的 QC 記錄
POST /qc                - 建立 QC 記錄
DELETE /qc/:id          - 刪除 QC 記錄
GET  /factory/batches   - 取得工廠待處理批次（processing/qc_pending/qc_done/packaging）
"""
from uuid import UUID
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload

from database import get_db
from models.user import User
from models.qc import QCRecord, QC_RESULTS
from models.batch import Batch
from schemas.qc import QCRecordCreate, QCRecordOut
from utils.dependencies import get_current_user, check_permission

router = APIRouter(tags=["工廠 / QC"])

FACTORY_STATUSES = ["processing", "qc_pending", "qc_done", "packaging", "ready_to_export"]


@router.get("/factory/batches", response_model=List[dict])
def list_factory_batches(
    db: Session = Depends(get_db),
    _:  User = Depends(check_permission("qc", "view")),
):
    """取得工廠待處理批次"""
    from models.purchase import PurchaseOrder
    batches = (
        db.query(Batch)
        .options(
            joinedload(Batch.purchase_order).joinedload(PurchaseOrder.supplier)
        )
        .filter(Batch.status.in_(FACTORY_STATUSES))
        .order_by(Batch.created_at.desc())
        .all()
    )
    result = []
    for b in batches:
        qc_count = db.query(QCRecord).filter(QCRecord.batch_id == b.id).count()
        result.append({
            "id":             str(b.id),
            "batch_no":       b.batch_no,
            "status":         b.status,
            "current_weight": float(b.current_weight),
            "initial_weight": float(b.initial_weight),
            "qc_count":       qc_count,
            "purchase_order": {
                "order_no": b.purchase_order.order_no if b.purchase_order else None,
                "supplier_name": b.purchase_order.supplier.name if (b.purchase_order and b.purchase_order.supplier) else None,
            } if b.purchase_order else None,
        })
    return result


@router.get("/qc", response_model=List[QCRecordOut])
def list_qc_records(
    batch_id: Optional[UUID] = Query(None),
    db:       Session = Depends(get_db),
    _:        User = Depends(check_permission("qc", "view")),
):
    """取得 QC 記錄列表"""
    q = db.query(QCRecord)
    if batch_id:
        q = q.filter(QCRecord.batch_id == batch_id)
    return q.order_by(QCRecord.checked_at.desc()).all()


@router.post("/qc", response_model=QCRecordOut, status_code=status.HTTP_201_CREATED)
def create_qc_record(
    payload:      QCRecordCreate,
    db:           Session = Depends(get_db),
    current_user: User = Depends(check_permission("qc", "create")),
):
    """建立 QC 記錄"""
    if payload.result not in QC_RESULTS:
        raise HTTPException(status_code=400, detail=f"無效的檢驗結果：{payload.result}")

    batch = db.query(Batch).filter(Batch.id == payload.batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="批次不存在")

    record = QCRecord(
        batch_id        = payload.batch_id,
        inspector_name  = payload.inspector_name,
        inspection_type = payload.inspection_type,
        checked_at      = payload.checked_at or datetime.utcnow(),
        result          = payload.result,
        grade           = payload.grade,
        weight_checked  = payload.weight_checked,
        notes           = payload.notes,
        created_by      = current_user.id,
    )
    db.add(record)

    # QC 通過時自動將批次從 qc_pending 推進至 qc_done
    if payload.result == "pass" and batch.status == "qc_pending":
        batch.status = "qc_done"

    db.commit()
    db.refresh(record)
    return record


@router.delete("/qc/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_qc_record(
    record_id: UUID,
    db:        Session = Depends(get_db),
    _:         User = Depends(check_permission("qc", "delete")),
):
    """刪除 QC 記錄"""
    record = db.query(QCRecord).filter(QCRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="記錄不存在")
    db.delete(record)
    db.commit()
