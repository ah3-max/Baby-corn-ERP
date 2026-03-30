"""
批次管理 API 路由
GET    /batches               - 列表（可篩選狀態）
POST   /batches               - 建立批次（需選已到廠採購單）
GET    /batches/:id           - 批次詳情
PUT    /batches/:id           - 更新備註 / 目前重量
PUT    /batches/:id/advance   - 推進狀態至下一個（含前置驗證）
POST   /batches/bulk-advance  - 批量推進狀態
"""
from uuid import UUID
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from pydantic import BaseModel

from database import get_db
from models.user import User
from models.batch import Batch, BATCH_STATUSES, STATUS_NEXT
from models.purchase import PurchaseOrder
from models.qc import QCRecord
from models.shipment import ShipmentBatch
from schemas.batch import BatchCreate, BatchUpdate, BatchOut
from utils.dependencies import get_current_user, check_permission
from utils.audit import write_audit_log

router = APIRouter(prefix="/batches", tags=["批次管理"])


def _generate_batch_no(db: Session) -> str:
    """產生批次編號：BT-YYYYMMDD-XXX"""
    from sqlalchemy import text
    db.execute(text("SELECT pg_advisory_xact_lock(hashtext('batch_no'))"))
    date_str = datetime.utcnow().strftime("%Y%m%d")
    prefix   = f"BT-{date_str}-"
    count    = db.query(func.count(Batch.id)).filter(
        Batch.batch_no.like(f"{prefix}%")
    ).scalar()
    return f"{prefix}{str(count + 1).zfill(3)}"


def _load_batch(db: Session, batch_id: UUID) -> Batch:
    """載入批次並預先載入關聯"""
    batch = (
        db.query(Batch)
        .options(
            joinedload(Batch.purchase_order).joinedload(PurchaseOrder.supplier)
        )
        .filter(Batch.id == batch_id)
        .first()
    )
    if not batch:
        raise HTTPException(status_code=404, detail="批次不存在")
    return batch


@router.get("", response_model=List[BatchOut])
def list_batches(
    status_filter:     Optional[str]  = Query(None, alias="status"),
    keyword:           Optional[str]  = Query(None),
    purchase_order_id: Optional[UUID] = Query(None),
    skip:              int = 0,
    limit:             int = 100,
    db:                Session = Depends(get_db),
    _:                 User = Depends(check_permission("batch", "view")),
):
    """取得批次列表，可依狀態、關鍵字、採購單篩選"""
    q = (
        db.query(Batch)
        .options(
            joinedload(Batch.purchase_order).joinedload(PurchaseOrder.supplier)
        )
    )
    if status_filter and status_filter in BATCH_STATUSES:
        q = q.filter(Batch.status == status_filter)
    if keyword:
        q = q.filter(Batch.batch_no.ilike(f"%{keyword}%"))
    if purchase_order_id:
        q = q.filter(Batch.purchase_order_id == purchase_order_id)
    return q.order_by(Batch.created_at.desc()).offset(skip).limit(limit).all()


@router.post("", response_model=BatchOut, status_code=status.HTTP_201_CREATED)
def create_batch(
    payload:      BatchCreate,
    db:           Session = Depends(get_db),
    current_user: User = Depends(check_permission("batch", "create")),
):
    """建立批次（採購單必須為已到廠狀態）"""
    po = db.query(PurchaseOrder).filter(PurchaseOrder.id == payload.purchase_order_id).first()
    if not po:
        raise HTTPException(status_code=404, detail="採購單不存在")
    if po.status != "arrived":
        raise HTTPException(status_code=400, detail="只能為已到廠的採購單建立批次")

    batch_no = _generate_batch_no(db)
    batch = Batch(
        batch_no          = batch_no,
        purchase_order_id = payload.purchase_order_id,
        initial_weight    = payload.initial_weight,
        current_weight    = payload.initial_weight,   # 初始時目前重量 = 初始重量
        status            = "processing",
        note              = payload.note,
        created_by        = current_user.id,
        harvest_datetime        = payload.harvest_datetime,
        harvest_location        = payload.harvest_location,
        harvest_temperature     = payload.harvest_temperature,
        harvest_weather         = payload.harvest_weather,
        transport_refrigerated  = payload.transport_refrigerated,
        shelf_life_days         = payload.shelf_life_days or 23,
    )
    db.add(batch)
    db.commit()
    db.refresh(batch)
    return _load_batch(db, batch.id)


@router.get("/{batch_id}", response_model=BatchOut)
def get_batch(
    batch_id: UUID,
    db:       Session = Depends(get_db),
    _:        User = Depends(check_permission("batch", "view")),
):
    """取得批次詳情"""
    return _load_batch(db, batch_id)


@router.put("/{batch_id}", response_model=BatchOut)
def update_batch(
    batch_id: UUID,
    payload:  BatchUpdate,
    db:       Session = Depends(get_db),
    _:        User = Depends(check_permission("batch", "edit")),
):
    """更新批次資料（備註、目前重量）"""
    batch = db.query(Batch).filter(Batch.id == batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="批次不存在")
    # 已出口後的批次資料不可修改（只允許在台灣入庫前的狀態編輯）
    _IMMUTABLE_STATUSES = {"exported", "in_transit_tw", "in_stock", "sold", "closed"}
    if batch.status in _IMMUTABLE_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"批次已進入「{batch.status}」狀態，不可修改",
        )

    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(batch, field, value)

    db.commit()
    return _load_batch(db, batch_id)


def _validate_advance(db: Session, batch: Batch) -> Optional[str]:
    """
    驗證批次是否可以推進到下一個狀態。
    回傳 None 表示可以推進，回傳字串表示不可推進的原因。
    """
    current = batch.status
    next_status = STATUS_NEXT.get(current)

    if next_status is None:
        return "此批次已是終態（結案），無法繼續推進"

    # qc_pending → qc_done：必須至少有 1 筆通過的 QC 紀錄
    if current == "qc_pending":
        qc_count = db.query(func.count(QCRecord.id)).filter(
            QCRecord.batch_id == batch.id,
            QCRecord.result.in_(["pass", "conditional_pass"]),
        ).scalar()
        if qc_count == 0:
            return "無法推進：此批次尚未有通過的 QC 紀錄，請先完成 QC 檢驗"

    # ready_to_export → exported：必須已關聯出口單
    if current == "ready_to_export":
        shipment_count = db.query(func.count(ShipmentBatch.id)).filter(
            ShipmentBatch.batch_id == batch.id,
        ).scalar()
        if shipment_count == 0:
            return "無法推進：此批次尚未關聯任何出口單，請先建立或加入出口單"

    # exported → in_transit_tw 和 in_transit_tw → in_stock 由出口單推進自動觸發
    if current in ("exported", "in_transit_tw"):
        return f"此狀態由出口單推進時自動觸發，請至出口單頁面操作"

    return None


@router.put("/{batch_id}/advance", response_model=BatchOut)
def advance_batch_status(
    batch_id:     UUID,
    db:           Session = Depends(get_db),
    current_user: User = Depends(check_permission("batch", "edit")),
):
    """推進批次至下一個狀態（含前置驗證）"""
    batch = db.query(Batch).filter(Batch.id == batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="批次不存在")

    error = _validate_advance(db, batch)
    if error:
        raise HTTPException(status_code=400, detail=error)

    old_status = batch.status
    batch.status = STATUS_NEXT[batch.status]
    write_audit_log(db, "status_change",
                    user_id=current_user.id,
                    entity_type="batch", entity_id=batch.id,
                    changes={"old_status": old_status, "new_status": batch.status})
    db.commit()
    return _load_batch(db, batch_id)


@router.delete("/{batch_id}", status_code=204)
def delete_batch(
    batch_id:     UUID,
    force:        bool = False,   # ?force=true 允許強制刪除任何狀態（需 delete 權限）
    db:           Session = Depends(get_db),
    current_user: User = Depends(check_permission("batch", "delete")),
):
    """
    刪除批次。
    - 預設只允許刪除尚未出口的批次（processing/qc_pending/qc_done/packaging/ready_to_export）
    - ?force=true 可強制刪除任何狀態（用於測試資料或報廢整批）
    - 同時清除關聯的 QC 記錄、成本事件、庫存批次
    """
    batch = db.query(Batch).filter(Batch.id == batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="批次不存在")

    # 非強制時：已出口的批次（exported 以後）不可刪除
    late_statuses = {"exported", "in_transit_tw", "in_stock", "sold", "closed"}
    if not force and batch.status in late_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"批次已進入「{batch.status}」狀態，無法直接刪除。"
                   "若確認要刪除，請使用 ?force=true 參數（管理員操作）",
        )

    write_audit_log(db, "delete",
                    user_id=current_user.id,
                    entity_type="batch", entity_id=batch.id,
                    changes={"batch_no": batch.batch_no, "status": batch.status, "force": force})
    db.delete(batch)
    db.commit()


# ─── 批量操作 ─────────────────────────────────────────

class BulkAdvanceRequest(BaseModel):
    batch_ids: List[UUID]


@router.post("/bulk-advance")
def bulk_advance(
    payload: BulkAdvanceRequest,
    db:      Session = Depends(get_db),
    _:       User = Depends(check_permission("batch", "edit")),
):
    """批量推進多個批次至下一個狀態"""
    results = []
    for bid in payload.batch_ids:
        batch = db.query(Batch).filter(Batch.id == bid).first()
        if not batch:
            results.append({"batch_id": str(bid), "success": False, "error": "批次不存在"})
            continue

        error = _validate_advance(db, batch)
        if error:
            results.append({"batch_id": str(bid), "batch_no": batch.batch_no, "success": False, "error": error})
            continue

        batch.status = STATUS_NEXT[batch.status]
        results.append({"batch_id": str(bid), "batch_no": batch.batch_no, "success": True, "new_status": batch.status})

    db.commit()

    success_count = sum(1 for r in results if r["success"])
    return {
        "total":   len(payload.batch_ids),
        "success": success_count,
        "failed":  len(payload.batch_ids) - success_count,
        "results": results,
    }
