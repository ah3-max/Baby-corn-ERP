"""
WP2：溫度記錄 API + 加工步驟記錄 API

溫度記錄：
  GET    /temperature-logs             - 列表
  POST   /temperature-logs             - 新增（手動）
  POST   /temperature-logs/bulk        - 批量新增（IoT Phase 3）

加工步驟記錄：
  GET    /processing-orders/:id/steps  - 列表
  POST   /processing-orders/:id/steps  - 新增
  PUT    /processing-orders/:id/steps/:sid - 更新
"""
from uuid import UUID
from typing import List, Optional
from datetime import datetime, date
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from database import get_db
from models.user import User
from models.qc_enhanced import TemperatureLog, ProcessingStepLog
from schemas.qc_enhanced import (
    TemperatureLogCreate, TemperatureLogOut,
    ProcessingStepLogCreate, ProcessingStepLogOut,
)
from utils.dependencies import check_permission

router = APIRouter(tags=["溫度記錄 / 加工步驟"])


# ─── 溫度記錄 ────────────────────────────────────────────

@router.get("/temperature-logs", response_model=List[TemperatureLogOut])
def list_temperature_logs(
    entity_type: Optional[str]  = Query(None),
    entity_id:   Optional[UUID] = Query(None),
    date_from:   Optional[date] = Query(None),
    date_to:     Optional[date] = Query(None),
    limit:       int            = 200,
    db:          Session = Depends(get_db),
    _:           User = Depends(check_permission("qc", "view")),
):
    q = db.query(TemperatureLog)
    if entity_type:
        q = q.filter(TemperatureLog.entity_type == entity_type)
    if entity_id:
        q = q.filter(TemperatureLog.entity_id == entity_id)
    if date_from:
        q = q.filter(TemperatureLog.recorded_at >= datetime.combine(date_from, datetime.min.time()))
    if date_to:
        q = q.filter(TemperatureLog.recorded_at <= datetime.combine(date_to, datetime.max.time()))
    return q.order_by(TemperatureLog.recorded_at.desc()).limit(limit).all()


@router.post("/temperature-logs", response_model=TemperatureLogOut, status_code=status.HTTP_201_CREATED)
def create_temperature_log(
    payload: TemperatureLogCreate,
    db:      Session = Depends(get_db),
    _:       User = Depends(check_permission("qc", "create")),
):
    log = TemperatureLog(
        entity_type=payload.entity_type,
        entity_id=payload.entity_id,
        log_source=payload.log_source,
        sensor_id=payload.sensor_id,
        temperature_c=payload.temperature_c,
        humidity_pct=payload.humidity_pct,
        location_description=payload.location_description,
        is_alert=payload.is_alert,
        alert_reason=payload.alert_reason,
        recorded_at=payload.recorded_at or datetime.utcnow(),
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


@router.post("/temperature-logs/bulk", status_code=status.HTTP_201_CREATED)
def bulk_create_temperature_logs(
    payloads: List[TemperatureLogCreate],
    db:       Session = Depends(get_db),
    _:        User = Depends(check_permission("qc", "create")),
):
    """Phase 3 IoT 批量上傳溫度記錄"""
    logs = []
    for p in payloads:
        log = TemperatureLog(
            entity_type=p.entity_type,
            entity_id=p.entity_id,
            log_source=p.log_source,
            sensor_id=p.sensor_id,
            temperature_c=p.temperature_c,
            humidity_pct=p.humidity_pct,
            location_description=p.location_description,
            is_alert=p.is_alert,
            alert_reason=p.alert_reason,
            recorded_at=p.recorded_at or datetime.utcnow(),
        )
        db.add(log)
        logs.append(log)
    db.commit()
    return {"created": len(logs)}


# ─── 加工步驟記錄 ────────────────────────────────────────

@router.get("/processing-orders/{order_id}/steps", response_model=List[ProcessingStepLogOut])
def list_processing_steps(
    order_id: UUID,
    db:       Session = Depends(get_db),
    _:        User = Depends(check_permission("qc", "view")),
):
    return (
        db.query(ProcessingStepLog)
        .filter(ProcessingStepLog.processing_order_id == order_id)
        .order_by(ProcessingStepLog.step_sequence)
        .all()
    )


@router.post("/processing-orders/{order_id}/steps", response_model=ProcessingStepLogOut, status_code=status.HTTP_201_CREATED)
def create_processing_step(
    order_id: UUID,
    payload:  ProcessingStepLogCreate,
    db:       Session = Depends(get_db),
    _:        User = Depends(check_permission("qc", "create")),
):
    from models.processing import ProcessingOrder
    order = db.query(ProcessingOrder).filter(ProcessingOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="加工單不存在")

    step = ProcessingStepLog(
        processing_order_id=order_id,
        **payload.model_dump(),
    )
    db.add(step)
    db.commit()
    db.refresh(step)
    return step


@router.put("/processing-orders/{order_id}/steps/{step_id}", response_model=ProcessingStepLogOut)
def update_processing_step(
    order_id: UUID,
    step_id:  UUID,
    payload:  ProcessingStepLogCreate,
    db:       Session = Depends(get_db),
    _:        User = Depends(check_permission("qc", "edit")),
):
    step = db.query(ProcessingStepLog).filter(
        ProcessingStepLog.id == step_id,
        ProcessingStepLog.processing_order_id == order_id,
    ).first()
    if not step:
        raise HTTPException(status_code=404, detail="步驟記錄不存在")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(step, field, value)
    db.commit()
    db.refresh(step)
    return step
