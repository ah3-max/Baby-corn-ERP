"""
WP8：每日摘要 API + 告警規則管理

  GET    /daily-summary/today        - 今日摘要
  GET    /daily-summary/history      - 歷史摘要列表
  POST   /daily-summary/generate     - 手動觸發生成

  GET    /alert-rules                - 告警規則列表
  POST   /alert-rules                - 新增規則
  PUT    /alert-rules/:id            - 更新規則
  DELETE /alert-rules/:id            - 刪除規則
"""
from uuid import UUID
from typing import List, Optional
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from database import get_db
from models.user import User
from models.daily_summary import DailySummarySnapshot, AlertRule
from utils.dependencies import check_permission
from pydantic import BaseModel

router = APIRouter(tags=["每日摘要"])


# ── Schemas ──────────────────────────────────────────────

class AlertRuleCreate(BaseModel):
    rule_code:      str
    rule_type:      str
    condition:      dict
    severity:       str = "warning"
    notify_roles:   Optional[list] = None
    notify_users:   Optional[list] = None
    cooldown_hours: int = 24

class AlertRuleUpdate(BaseModel):
    condition:      Optional[dict] = None
    severity:       Optional[str] = None
    notify_roles:   Optional[list] = None
    notify_users:   Optional[list] = None
    is_active:      Optional[bool] = None
    cooldown_hours: Optional[int] = None

class AlertRuleOut(BaseModel):
    id:               str
    rule_code:        str
    rule_type:        str
    condition:        dict
    severity:         str
    notify_roles:     Optional[list]
    notify_users:     Optional[list]
    is_active:        bool
    cooldown_hours:   int
    last_triggered_at: Optional[str]
    created_at:       str
    class Config: from_attributes = True


# ── 每日摘要 ────────────────────────────────────────────

@router.get("/daily-summary/today")
def get_today_summary(
    db: Session = Depends(get_db),
    _:  User = Depends(check_permission("system", "read")),
):
    """取得今日摘要（若尚未產生則自動生成）"""
    today = date.today()
    snapshot = db.query(DailySummarySnapshot).filter(
        DailySummarySnapshot.summary_date == today
    ).first()
    if snapshot:
        return snapshot.data

    # 自動生成
    from services.daily_summary_service import generate_daily_summary
    return generate_daily_summary(db)


@router.get("/daily-summary/history")
def list_summary_history(
    days: int = Query(30, le=365),
    db:   Session = Depends(get_db),
    _:    User = Depends(check_permission("system", "read")),
):
    """歷史摘要列表"""
    snapshots = (
        db.query(DailySummarySnapshot)
        .order_by(DailySummarySnapshot.summary_date.desc())
        .limit(days)
        .all()
    )
    return [
        {"date": str(s.summary_date), "data": s.data}
        for s in snapshots
    ]


@router.post("/daily-summary/generate")
def generate_summary(
    db: Session = Depends(get_db),
    _:  User = Depends(check_permission("system", "update")),
):
    """手動觸發生成今日摘要"""
    from services.daily_summary_service import generate_daily_summary
    data = generate_daily_summary(db)
    return {"message": "摘要已生成", "data": data}


# ── 告警規則 CRUD ───────────────────────────────────────

@router.get("/alert-rules", response_model=List[AlertRuleOut])
def list_alert_rules(
    db: Session = Depends(get_db),
    _:  User = Depends(check_permission("system", "read")),
):
    rules = db.query(AlertRule).order_by(AlertRule.rule_code).all()
    return [
        AlertRuleOut(
            id=str(r.id), rule_code=r.rule_code, rule_type=r.rule_type,
            condition=r.condition, severity=r.severity,
            notify_roles=r.notify_roles, notify_users=r.notify_users,
            is_active=r.is_active, cooldown_hours=r.cooldown_hours,
            last_triggered_at=str(r.last_triggered_at) if r.last_triggered_at else None,
            created_at=str(r.created_at),
        ) for r in rules
    ]


@router.post("/alert-rules", response_model=AlertRuleOut, status_code=status.HTTP_201_CREATED)
def create_alert_rule(
    payload: AlertRuleCreate,
    db:      Session = Depends(get_db),
    _:       User = Depends(check_permission("system", "update")),
):
    rule = AlertRule(
        rule_code=payload.rule_code,
        rule_type=payload.rule_type,
        condition=payload.condition,
        severity=payload.severity,
        notify_roles=payload.notify_roles or [],
        notify_users=payload.notify_users or [],
        cooldown_hours=payload.cooldown_hours,
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return AlertRuleOut(
        id=str(rule.id), rule_code=rule.rule_code, rule_type=rule.rule_type,
        condition=rule.condition, severity=rule.severity,
        notify_roles=rule.notify_roles, notify_users=rule.notify_users,
        is_active=rule.is_active, cooldown_hours=rule.cooldown_hours,
        last_triggered_at=None, created_at=str(rule.created_at),
    )


@router.put("/alert-rules/{rule_id}", response_model=AlertRuleOut)
def update_alert_rule(
    rule_id: UUID,
    payload: AlertRuleUpdate,
    db:      Session = Depends(get_db),
    _:       User = Depends(check_permission("system", "update")),
):
    rule = db.query(AlertRule).filter(AlertRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="告警規則不存在")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(rule, k, v)
    db.commit()
    db.refresh(rule)
    return AlertRuleOut(
        id=str(rule.id), rule_code=rule.rule_code, rule_type=rule.rule_type,
        condition=rule.condition, severity=rule.severity,
        notify_roles=rule.notify_roles, notify_users=rule.notify_users,
        is_active=rule.is_active, cooldown_hours=rule.cooldown_hours,
        last_triggered_at=str(rule.last_triggered_at) if rule.last_triggered_at else None,
        created_at=str(rule.created_at),
    )


@router.delete("/alert-rules/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_alert_rule(
    rule_id: UUID,
    db:      Session = Depends(get_db),
    _:       User = Depends(check_permission("system", "update")),
):
    rule = db.query(AlertRule).filter(AlertRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="告警規則不存在")
    db.delete(rule)
    db.commit()
