"""
合規管理路由（J/K/L 段）

涵蓋：
  /compliance/contracts        — 合約 CRUD
  /compliance/announcements    — 公告 CRUD
  /compliance/meetings         — 會議記錄 CRUD + 行動事項
  /kpi/definitions             — KPI 定義 CRUD
  /kpi/values                  — KPI 值記錄
"""
import uuid
from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database import get_db
from utils.dependencies import check_permission

router = APIRouter(tags=["合規管理"])


# ──────────────────────────────────────────────────────────
# J-02  合約管理
# ──────────────────────────────────────────────────────────

@router.get("/compliance/contracts")
def list_contracts(
    contract_type: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = Query(default=50),
    db: Session = Depends(get_db),
    current_user=Depends(check_permission("contract", "read")),
):
    from models.compliance import Contract
    q = db.query(Contract).filter(Contract.deleted_at.is_(None))
    if contract_type:
        q = q.filter(Contract.contract_type == contract_type)
    if status:
        q = q.filter(Contract.status == status)
    items = q.order_by(Contract.effective_to.asc()).limit(limit).all()
    return {"items": [_to_dict(i) for i in items], "total": len(items)}


@router.post("/compliance/contracts", status_code=201)
def create_contract(
    data: dict,
    db: Session = Depends(get_db),
    current_user=Depends(check_permission("contract", "create")),
):
    from models.compliance import Contract
    from utils.seq import next_seq_no, make_daily_prefix
    prefix = make_daily_prefix("CT")
    contract_no = next_seq_no(db, Contract, Contract.contract_no, prefix)
    obj = Contract(**data, contract_no=contract_no, created_by=current_user.id)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return _to_dict(obj)


@router.get("/compliance/contracts/{cid}")
def get_contract(
    cid: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(check_permission("contract", "read")),
):
    from models.compliance import Contract
    obj = db.query(Contract).filter(Contract.id == cid).first()
    if not obj:
        raise HTTPException(status_code=404, detail="合約不存在")
    return _to_dict(obj)


# ──────────────────────────────────────────────────────────
# K-01  公告管理
# ──────────────────────────────────────────────────────────

@router.get("/compliance/announcements")
def list_announcements(
    priority: Optional[str] = None,
    limit: int = Query(default=30),
    db: Session = Depends(get_db),
    current_user=Depends(check_permission("announcement", "read")),
):
    from models.compliance import Announcement
    q = db.query(Announcement).filter(Announcement.deleted_at.is_(None))
    if priority:
        q = q.filter(Announcement.priority == priority)
    items = q.order_by(Announcement.is_pinned.desc(), Announcement.created_at.desc()).limit(limit).all()
    return {"items": [_to_dict(i) for i in items], "total": len(items)}


@router.post("/compliance/announcements", status_code=201)
def create_announcement(
    data: dict,
    db: Session = Depends(get_db),
    current_user=Depends(check_permission("announcement", "create")),
):
    from models.compliance import Announcement
    obj = Announcement(**data, created_by=current_user.id)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return _to_dict(obj)


# ──────────────────────────────────────────────────────────
# K-04  會議記錄
# ──────────────────────────────────────────────────────────

@router.get("/compliance/meetings")
def list_meetings(
    meeting_type: Optional[str] = None,
    limit: int = Query(default=30),
    db: Session = Depends(get_db),
    current_user=Depends(check_permission("meeting", "read")),
):
    from models.compliance import MeetingRecord
    q = db.query(MeetingRecord).filter(MeetingRecord.deleted_at.is_(None))
    if meeting_type:
        q = q.filter(MeetingRecord.meeting_type == meeting_type)
    items = q.order_by(MeetingRecord.meeting_date.desc()).limit(limit).all()
    return {"items": [_to_dict(i) for i in items], "total": len(items)}


@router.post("/compliance/meetings", status_code=201)
def create_meeting(
    data: dict,
    db: Session = Depends(get_db),
    current_user=Depends(check_permission("meeting", "create")),
):
    from models.compliance import MeetingRecord
    from utils.seq import next_seq_no, make_daily_prefix
    prefix = make_daily_prefix("MG")
    meeting_no = next_seq_no(db, MeetingRecord, MeetingRecord.meeting_no, prefix)
    obj = MeetingRecord(**data, meeting_no=meeting_no, created_by=current_user.id)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return _to_dict(obj)


@router.get("/compliance/meetings/{mid}")
def get_meeting(
    mid: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(check_permission("meeting", "read")),
):
    from models.compliance import MeetingRecord
    obj = db.query(MeetingRecord).filter(MeetingRecord.id == mid).first()
    if not obj:
        raise HTTPException(status_code=404, detail="會議不存在")
    return _to_dict(obj)


@router.get("/compliance/meetings/{mid}/actions")
def get_meeting_actions(
    mid: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(check_permission("meeting", "read")),
):
    from models.compliance import MeetingActionItem
    items = db.query(MeetingActionItem).filter(
        MeetingActionItem.meeting_record_id == mid
    ).order_by(MeetingActionItem.due_date.asc()).all()
    return {"items": [_to_dict(i) for i in items], "total": len(items)}


# ──────────────────────────────────────────────────────────
# O-01  KPI 定義
# ──────────────────────────────────────────────────────────

@router.get("/kpi/definitions")
def list_kpi_definitions(
    limit: int = Query(default=50),
    db: Session = Depends(get_db),
    current_user=Depends(check_permission("system", "read")),
):
    from models.kpi_dashboard import KPIDefinition
    items = db.query(KPIDefinition).filter(
        KPIDefinition.is_active.is_(True)
    ).order_by(KPIDefinition.kpi_code).limit(limit).all()
    return {"items": [_to_dict(i) for i in items], "total": len(items)}


@router.post("/kpi/definitions", status_code=201)
def create_kpi_definition(
    data: dict,
    db: Session = Depends(get_db),
    current_user=Depends(check_permission("system", "update")),
):
    from models.kpi_dashboard import KPIDefinition
    obj = KPIDefinition(**data)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return _to_dict(obj)


@router.get("/kpi/values/latest")
def get_latest_kpi_values(
    db: Session = Depends(get_db),
    current_user=Depends(check_permission("system", "read")),
):
    from models.kpi_dashboard import KPIValue
    from sqlalchemy import func
    # 每個 KPI 取最新一筆
    subq = db.query(
        KPIValue.kpi_id,
        func.max(KPIValue.period_date).label("max_date"),
    ).group_by(KPIValue.kpi_id).subquery()
    items = db.query(KPIValue).join(
        subq,
        (KPIValue.kpi_id == subq.c.kpi_id) & (KPIValue.period_date == subq.c.max_date)
    ).all()
    return {"items": [_to_dict(i) for i in items], "total": len(items)}


# ──────────────────────────────────────────────────────────
# 工具函數
# ──────────────────────────────────────────────────────────

def _to_dict(obj) -> dict:
    """SQLAlchemy 物件轉 dict（排除 _sa_instance_state）"""
    d = {k: v for k, v in obj.__dict__.items() if not k.startswith("_")}
    # UUID → str
    for k, v in d.items():
        if isinstance(v, uuid.UUID):
            d[k] = str(v)
        elif isinstance(v, datetime):
            d[k] = v.isoformat()
    return d
