"""
WP3：業務 CRM API

業務團隊：
  GET/POST     /crm/teams              - 團隊列表 / 建立
  GET/PUT      /crm/teams/:id          - 詳情 / 更新
  POST/DELETE  /crm/teams/:id/members  - 新增/移除成員

CRM 活動：
  GET/POST     /crm/activities         - 列表 / 新增
  PUT          /crm/activities/:id     - 更新

CRM 任務：
  GET/POST     /crm/tasks              - 列表 / 新增（經理指派）
  PUT          /crm/tasks/:id          - 更新狀態

業績分析：
  GET  /crm/dashboard                  - 業務總覽
  GET  /crm/team/:id/performance       - 團隊業績
  GET  /crm/user/:id/performance       - 個人業績
  GET  /crm/customers/360/:id          - 客戶 360 度檢視
  GET  /crm/ranking                    - 業務排行榜
"""
from uuid import UUID
from typing import List, Optional
from datetime import datetime, date
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_, extract

from database import get_db
from models.user import User
from models.customer import Customer
from models.sales import SalesOrder, SalesOrderItem
from models.daily_sale import DailySale, DailySaleItem
from models.payment import PaymentRecord
from models.sales_team import SalesTeam, SalesTeamMember
from models.crm_activity import CRMActivity, CRMTask
from schemas.crm import (
    SalesTeamCreate, SalesTeamUpdate, SalesTeamOut, SalesTeamMemberCreate, SalesTeamMemberOut,
    CRMActivityCreate, CRMActivityUpdate, CRMActivityOut,
    CRMTaskCreate, CRMTaskUpdate, CRMTaskOut,
)
from utils.dependencies import check_permission

router = APIRouter(prefix="/crm", tags=["業務 CRM"])


# ─── 工具函式 ────────────────────────────────────────────

def _gen_no(db: Session, model, prefix: str, field) -> str:
    from sqlalchemy import text
    db.execute(text(f"SELECT pg_advisory_xact_lock(hashtext('crm_no_{prefix}'))"))
    date_str = date.today().strftime("%Y%m%d")
    full_prefix = f"{prefix}-{date_str}-"
    count = db.query(func.count(model.id)).filter(field.like(f"{full_prefix}%")).scalar()
    return f"{full_prefix}{str(count + 1).zfill(3)}"


# ─── 業務團隊 CRUD ──────────────────────────────────────

@router.get("/teams", response_model=List[SalesTeamOut])
def list_teams(
    region: Optional[str] = Query(None),
    db:     Session = Depends(get_db),
    _:      User = Depends(check_permission("crm", "view")),
):
    q = db.query(SalesTeam).options(joinedload(SalesTeam.members))
    if region:
        q = q.filter(SalesTeam.region == region)
    teams = q.order_by(SalesTeam.team_code).all()
    result = []
    for t in teams:
        out = SalesTeamOut(
            id=str(t.id), team_code=t.team_code, team_name=t.team_name,
            region=t.region, manager_user_id=str(t.manager_user_id) if t.manager_user_id else None,
            description=t.description, is_active=t.is_active, created_at=t.created_at,
            members=[
                SalesTeamMemberOut(
                    id=str(m.id), team_id=str(m.team_id), user_id=str(m.user_id),
                    user_name=m.user.full_name if m.user else None,
                    role=m.role, target_monthly_twd=float(m.target_monthly_twd),
                    joined_at=m.joined_at, is_active=m.is_active,
                ) for m in t.members
            ],
        )
        result.append(out)
    return result


@router.post("/teams", response_model=SalesTeamOut, status_code=status.HTTP_201_CREATED)
def create_team(
    payload: SalesTeamCreate,
    db:      Session = Depends(get_db),
    _:       User = Depends(check_permission("crm", "create")),
):
    team = SalesTeam(**payload.model_dump())
    db.add(team)
    db.commit()
    db.refresh(team)
    return SalesTeamOut(
        id=str(team.id), team_code=team.team_code, team_name=team.team_name,
        region=team.region, manager_user_id=str(team.manager_user_id) if team.manager_user_id else None,
        description=team.description, is_active=team.is_active, created_at=team.created_at,
        members=[],
    )


@router.put("/teams/{team_id}", response_model=SalesTeamOut)
def update_team(
    team_id: UUID,
    payload: SalesTeamUpdate,
    db:      Session = Depends(get_db),
    _:       User = Depends(check_permission("crm", "edit")),
):
    team = db.query(SalesTeam).filter(SalesTeam.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="團隊不存在")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(team, k, v)
    db.commit()
    return list_teams(db=db, _=_, region=None)[0]  # 簡化回傳


@router.post("/teams/{team_id}/members", response_model=SalesTeamMemberOut, status_code=status.HTTP_201_CREATED)
def add_team_member(
    team_id: UUID,
    payload: SalesTeamMemberCreate,
    db:      Session = Depends(get_db),
    _:       User = Depends(check_permission("crm", "edit")),
):
    team = db.query(SalesTeam).filter(SalesTeam.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="團隊不存在")
    member = SalesTeamMember(
        team_id=team_id,
        user_id=payload.user_id,
        role=payload.role,
        target_monthly_twd=payload.target_monthly_twd,
    )
    db.add(member)
    db.commit()
    db.refresh(member)
    user = db.query(User).filter(User.id == member.user_id).first()
    return SalesTeamMemberOut(
        id=str(member.id), team_id=str(member.team_id), user_id=str(member.user_id),
        user_name=user.full_name if user else None,
        role=member.role, target_monthly_twd=float(member.target_monthly_twd),
        joined_at=member.joined_at, is_active=member.is_active,
    )


@router.delete("/teams/{team_id}/members/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_team_member(
    team_id:   UUID,
    member_id: UUID,
    db:        Session = Depends(get_db),
    _:         User = Depends(check_permission("crm", "edit")),
):
    member = db.query(SalesTeamMember).filter(
        SalesTeamMember.id == member_id, SalesTeamMember.team_id == team_id,
    ).first()
    if not member:
        raise HTTPException(status_code=404, detail="成員不存在")
    db.delete(member)
    db.commit()


# ─── CRM 活動 ───────────────────────────────────────────

@router.get("/activities", response_model=List[CRMActivityOut])
def list_activities(
    customer_id: Optional[UUID] = Query(None),
    user_id:     Optional[UUID] = Query(None),
    date_from:   Optional[date] = Query(None),
    date_to:     Optional[date] = Query(None),
    limit:       int = 50,
    db:          Session = Depends(get_db),
    _:           User = Depends(check_permission("crm", "view")),
):
    q = db.query(CRMActivity).options(
        joinedload(CRMActivity.customer), joinedload(CRMActivity.sales_user),
    )
    if customer_id:
        q = q.filter(CRMActivity.customer_id == customer_id)
    if user_id:
        q = q.filter(CRMActivity.sales_user_id == user_id)
    if date_from:
        q = q.filter(CRMActivity.activity_date >= datetime.combine(date_from, datetime.min.time()))
    if date_to:
        q = q.filter(CRMActivity.activity_date <= datetime.combine(date_to, datetime.max.time()))
    activities = q.order_by(CRMActivity.activity_date.desc()).limit(limit).all()
    return [
        CRMActivityOut(
            id=str(a.id), activity_no=a.activity_no,
            customer_id=str(a.customer_id), customer_name=a.customer.name if a.customer else None,
            sales_user_id=str(a.sales_user_id), sales_user_name=a.sales_user.full_name if a.sales_user else None,
            activity_type=a.activity_type, activity_date=a.activity_date,
            duration_minutes=a.duration_minutes, summary=a.summary, detail=a.detail,
            follow_up_date=a.follow_up_date, follow_up_action=a.follow_up_action,
            result=a.result, order_potential_twd=float(a.order_potential_twd) if a.order_potential_twd else None,
            attachments=a.attachments, created_at=a.created_at,
        ) for a in activities
    ]


@router.post("/activities", response_model=CRMActivityOut, status_code=status.HTTP_201_CREATED)
def create_activity(
    payload:      CRMActivityCreate,
    db:           Session = Depends(get_db),
    current_user: User = Depends(check_permission("crm", "create")),
):
    activity_no = _gen_no(db, CRMActivity, "ACT", CRMActivity.activity_no)
    activity = CRMActivity(
        activity_no=activity_no,
        customer_id=payload.customer_id,
        sales_user_id=current_user.id,
        activity_type=payload.activity_type,
        activity_date=payload.activity_date or datetime.utcnow(),
        duration_minutes=payload.duration_minutes,
        summary=payload.summary,
        detail=payload.detail,
        follow_up_date=payload.follow_up_date,
        follow_up_action=payload.follow_up_action,
        result=payload.result,
        order_potential_twd=payload.order_potential_twd,
    )
    db.add(activity)
    db.commit()
    db.refresh(activity)
    customer = db.query(Customer).filter(Customer.id == activity.customer_id).first()
    return CRMActivityOut(
        id=str(activity.id), activity_no=activity.activity_no,
        customer_id=str(activity.customer_id), customer_name=customer.name if customer else None,
        sales_user_id=str(activity.sales_user_id), sales_user_name=current_user.full_name,
        activity_type=activity.activity_type, activity_date=activity.activity_date,
        duration_minutes=activity.duration_minutes, summary=activity.summary, detail=activity.detail,
        follow_up_date=activity.follow_up_date, follow_up_action=activity.follow_up_action,
        result=activity.result, order_potential_twd=float(activity.order_potential_twd) if activity.order_potential_twd else None,
        attachments=activity.attachments, created_at=activity.created_at,
    )


@router.put("/activities/{activity_id}", response_model=CRMActivityOut)
def update_activity(
    activity_id: UUID,
    payload:     CRMActivityUpdate,
    db:          Session = Depends(get_db),
    _:           User = Depends(check_permission("crm", "edit")),
):
    activity = db.query(CRMActivity).filter(CRMActivity.id == activity_id).first()
    if not activity:
        raise HTTPException(status_code=404, detail="活動記錄不存在")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(activity, k, v)
    db.commit()
    # 簡化回傳
    return list_activities(customer_id=None, user_id=None, date_from=None, date_to=None, limit=1, db=db, _=_)[0]


# ─── CRM 任務 ───────────────────────────────────────────

@router.get("/tasks", response_model=List[CRMTaskOut])
def list_tasks(
    assigned_to: Optional[UUID] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    limit:       int = 50,
    db:          Session = Depends(get_db),
    _:           User = Depends(check_permission("crm", "view")),
):
    q = db.query(CRMTask).options(
        joinedload(CRMTask.assignee), joinedload(CRMTask.assigner), joinedload(CRMTask.customer),
    )
    if assigned_to:
        q = q.filter(CRMTask.assigned_to == assigned_to)
    if status_filter:
        q = q.filter(CRMTask.status == status_filter)
    tasks = q.order_by(CRMTask.created_at.desc()).limit(limit).all()
    return [
        CRMTaskOut(
            id=str(t.id), task_no=t.task_no,
            assigned_to=str(t.assigned_to), assignee_name=t.assignee.full_name if t.assignee else None,
            assigned_by=str(t.assigned_by), assigner_name=t.assigner.full_name if t.assigner else None,
            customer_id=str(t.customer_id) if t.customer_id else None,
            customer_name=t.customer.name if t.customer else None,
            task_type=t.task_type, title=t.title, description=t.description,
            priority=t.priority, due_date=t.due_date, status=t.status,
            completed_at=t.completed_at, completion_note=t.completion_note, created_at=t.created_at,
        ) for t in tasks
    ]


@router.post("/tasks", response_model=CRMTaskOut, status_code=status.HTTP_201_CREATED)
def create_task(
    payload:      CRMTaskCreate,
    db:           Session = Depends(get_db),
    current_user: User = Depends(check_permission("crm", "create")),
):
    """經理指派任務給業務"""
    task_no = _gen_no(db, CRMTask, "TSK", CRMTask.task_no)
    task = CRMTask(
        task_no=task_no,
        assigned_to=payload.assigned_to,
        assigned_by=current_user.id,
        customer_id=payload.customer_id,
        task_type=payload.task_type,
        title=payload.title,
        description=payload.description,
        priority=payload.priority,
        due_date=payload.due_date,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    assignee = db.query(User).filter(User.id == task.assigned_to).first()
    customer = db.query(Customer).filter(Customer.id == task.customer_id).first() if task.customer_id else None
    return CRMTaskOut(
        id=str(task.id), task_no=task.task_no,
        assigned_to=str(task.assigned_to), assignee_name=assignee.full_name if assignee else None,
        assigned_by=str(task.assigned_by), assigner_name=current_user.full_name,
        customer_id=str(task.customer_id) if task.customer_id else None,
        customer_name=customer.name if customer else None,
        task_type=task.task_type, title=task.title, description=task.description,
        priority=task.priority, due_date=task.due_date, status=task.status,
        completed_at=task.completed_at, completion_note=task.completion_note, created_at=task.created_at,
    )


@router.put("/tasks/{task_id}", response_model=CRMTaskOut)
def update_task(
    task_id: UUID,
    payload: CRMTaskUpdate,
    db:      Session = Depends(get_db),
    _:       User = Depends(check_permission("crm", "edit")),
):
    task = db.query(CRMTask).filter(CRMTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任務不存在")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(task, k, v)
    if payload.status == "completed" and not task.completed_at:
        task.completed_at = datetime.utcnow()
    db.commit()
    db.refresh(task)
    assignee = db.query(User).filter(User.id == task.assigned_to).first()
    assigner = db.query(User).filter(User.id == task.assigned_by).first()
    customer = db.query(Customer).filter(Customer.id == task.customer_id).first() if task.customer_id else None
    return CRMTaskOut(
        id=str(task.id), task_no=task.task_no,
        assigned_to=str(task.assigned_to), assignee_name=assignee.full_name if assignee else None,
        assigned_by=str(task.assigned_by), assigner_name=assigner.full_name if assigner else None,
        customer_id=str(task.customer_id) if task.customer_id else None,
        customer_name=customer.name if customer else None,
        task_type=task.task_type, title=task.title, description=task.description,
        priority=task.priority, due_date=task.due_date, status=task.status,
        completed_at=task.completed_at, completion_note=task.completion_note, created_at=task.created_at,
    )


# ─── 業績分析 ───────────────────────────────────────────

@router.get("/dashboard")
def crm_dashboard(
    db:           Session = Depends(get_db),
    current_user: User = Depends(check_permission("crm", "view")),
):
    """業務總覽 — 本月摘要"""
    today = date.today()
    month_start = today.replace(day=1)

    # 本月銷售額（SalesOrder）
    so_revenue = db.query(
        func.coalesce(func.sum(SalesOrder.total_amount_twd), 0)
    ).filter(SalesOrder.order_date >= month_start).scalar()

    # 本月每日銷售額（DailySale）
    ds_revenue = db.query(
        func.coalesce(func.sum(DailySale.total_amount_twd), 0)
    ).filter(DailySale.sale_date >= month_start).scalar()

    # 本月回款
    payments = db.query(
        func.coalesce(func.sum(PaymentRecord.amount_twd), 0)
    ).filter(PaymentRecord.payment_date >= month_start, PaymentRecord.status == "confirmed").scalar()

    # 活躍客戶數
    active_customers = db.query(func.count(Customer.id)).filter(Customer.is_active == True).scalar()

    # 本月新客戶
    new_customers = db.query(func.count(Customer.id)).filter(
        Customer.created_at >= datetime.combine(month_start, datetime.min.time())
    ).scalar()

    # 待完成任務
    pending_tasks = db.query(func.count(CRMTask.id)).filter(
        CRMTask.status.in_(["pending", "in_progress"])
    ).scalar()

    # 本月活動次數
    activity_count = db.query(func.count(CRMActivity.id)).filter(
        CRMActivity.activity_date >= datetime.combine(month_start, datetime.min.time())
    ).scalar()

    return {
        "month": today.strftime("%Y-%m"),
        "total_revenue_twd": float(so_revenue) + float(ds_revenue),
        "so_revenue_twd": float(so_revenue),
        "ds_revenue_twd": float(ds_revenue),
        "confirmed_payments_twd": float(payments),
        "active_customers": active_customers,
        "new_customers": new_customers,
        "pending_tasks": pending_tasks,
        "activity_count": activity_count,
    }


@router.get("/user/{user_id}/performance")
def user_performance(
    user_id:   UUID,
    month:     Optional[str] = Query(None),  # YYYY-MM 格式
    db:        Session = Depends(get_db),
    _:         User = Depends(check_permission("crm", "view")),
):
    """個人業績"""
    if month:
        year, mon = map(int, month.split("-"))
        month_start = date(year, mon, 1)
    else:
        today = date.today()
        month_start = today.replace(day=1)

    # 銷售額
    so_revenue = db.query(
        func.coalesce(func.sum(SalesOrder.total_amount_twd), 0)
    ).filter(SalesOrder.created_by == user_id, SalesOrder.order_date >= month_start).scalar()

    ds_revenue = db.query(
        func.coalesce(func.sum(DailySale.total_amount_twd), 0)
    ).filter(DailySale.created_by == user_id, DailySale.sale_date >= month_start).scalar()

    # 客戶拜訪
    visits = db.query(func.count(CRMActivity.id)).filter(
        CRMActivity.sales_user_id == user_id,
        CRMActivity.activity_date >= datetime.combine(month_start, datetime.min.time()),
    ).scalar()

    # 完成任務
    completed_tasks = db.query(func.count(CRMTask.id)).filter(
        CRMTask.assigned_to == user_id, CRMTask.status == "completed",
        CRMTask.completed_at >= datetime.combine(month_start, datetime.min.time()),
    ).scalar()

    # 目標額
    member = db.query(SalesTeamMember).filter(
        SalesTeamMember.user_id == user_id, SalesTeamMember.is_active == True,
    ).first()
    target = float(member.target_monthly_twd) if member else 0
    actual = float(so_revenue) + float(ds_revenue)

    user = db.query(User).filter(User.id == user_id).first()

    return {
        "user_id": str(user_id),
        "user_name": user.full_name if user else None,
        "month": month_start.strftime("%Y-%m"),
        "target_twd": target,
        "actual_twd": actual,
        "achievement_pct": round(actual / target * 100, 1) if target > 0 else 0,
        "so_revenue_twd": float(so_revenue),
        "ds_revenue_twd": float(ds_revenue),
        "visit_count": visits,
        "completed_tasks": completed_tasks,
    }


@router.get("/customers/360/{customer_id}")
def customer_360(
    customer_id: UUID,
    db:          Session = Depends(get_db),
    _:           User = Depends(check_permission("crm", "view")),
):
    """客戶 360 度檢視"""
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="客戶不存在")

    # 銷售訂單歷史
    orders = db.query(SalesOrder).filter(
        SalesOrder.customer_id == customer_id
    ).order_by(SalesOrder.order_date.desc()).limit(10).all()

    # 每日銷售歷史
    daily_sales = db.query(DailySale).filter(
        DailySale.customer_id == customer_id
    ).order_by(DailySale.sale_date.desc()).limit(10).all()

    # 付款歷史
    payments = db.query(PaymentRecord).filter(
        PaymentRecord.customer_id == customer_id
    ).order_by(PaymentRecord.payment_date.desc()).limit(10).all()

    # CRM 活動
    activities = db.query(CRMActivity).filter(
        CRMActivity.customer_id == customer_id
    ).order_by(CRMActivity.activity_date.desc()).limit(10).all()

    # 統計
    total_so = db.query(func.coalesce(func.sum(SalesOrder.total_amount_twd), 0)).filter(
        SalesOrder.customer_id == customer_id).scalar()
    total_ds = db.query(func.coalesce(func.sum(DailySale.total_amount_twd), 0)).filter(
        DailySale.customer_id == customer_id).scalar()
    total_paid = db.query(func.coalesce(func.sum(PaymentRecord.amount_twd), 0)).filter(
        PaymentRecord.customer_id == customer_id, PaymentRecord.status == "confirmed").scalar()

    total_revenue = float(total_so) + float(total_ds)
    ar_balance = total_revenue - float(total_paid)

    return {
        "customer": {
            "id": str(customer.id),
            "name": customer.name,
            "code": customer.code,
            "customer_type": customer.customer_type,
            "contact_name": customer.contact_name,
            "phone": customer.phone,
            "email": customer.email,
            "region": customer.region,
            "credit_status": customer.credit_status,
            "payment_terms": customer.payment_terms,
        },
        "summary": {
            "total_revenue_twd": total_revenue,
            "total_paid_twd": float(total_paid),
            "ar_balance_twd": ar_balance,
            "order_count": len(orders),
            "daily_sale_count": len(daily_sales),
        },
        "recent_orders": [
            {"id": str(o.id), "order_no": o.order_no, "date": str(o.order_date),
             "amount": float(o.total_amount_twd), "status": o.status}
            for o in orders
        ],
        "recent_daily_sales": [
            {"id": str(d.id), "date": str(d.sale_date), "market": d.market_code,
             "amount": float(d.total_amount_twd)}
            for d in daily_sales
        ],
        "recent_payments": [
            {"id": str(p.id), "date": str(p.payment_date), "amount": float(p.amount_twd),
             "method": p.payment_method, "status": p.status}
            for p in payments
        ],
        "recent_activities": [
            {"id": str(a.id), "type": a.activity_type, "date": str(a.activity_date),
             "summary": a.summary, "result": a.result}
            for a in activities
        ],
    }


@router.get("/ranking")
def sales_ranking(
    month: Optional[str] = Query(None),  # YYYY-MM
    db:    Session = Depends(get_db),
    _:     User = Depends(check_permission("crm", "view")),
):
    """業務排行榜"""
    if month:
        year, mon = map(int, month.split("-"))
        month_start = date(year, mon, 1)
    else:
        today = date.today()
        month_start = today.replace(day=1)

    # 從 SalesOrder + DailySale 計算每位業務的銷售額
    so_by_user = dict(
        db.query(SalesOrder.created_by, func.sum(SalesOrder.total_amount_twd))
        .filter(SalesOrder.order_date >= month_start)
        .group_by(SalesOrder.created_by)
        .all()
    )
    ds_by_user = dict(
        db.query(DailySale.created_by, func.sum(DailySale.total_amount_twd))
        .filter(DailySale.sale_date >= month_start)
        .group_by(DailySale.created_by)
        .all()
    )

    all_user_ids = set(so_by_user.keys()) | set(ds_by_user.keys())
    ranking = []
    for uid in all_user_ids:
        if uid is None:
            continue
        user = db.query(User).filter(User.id == uid).first()
        so_amt = float(so_by_user.get(uid, 0))
        ds_amt = float(ds_by_user.get(uid, 0))
        total = so_amt + ds_amt

        # 目標
        member = db.query(SalesTeamMember).filter(
            SalesTeamMember.user_id == uid, SalesTeamMember.is_active == True,
        ).first()
        target = float(member.target_monthly_twd) if member else 0

        ranking.append({
            "user_id": str(uid),
            "user_name": user.full_name if user else "N/A",
            "so_revenue_twd": so_amt,
            "ds_revenue_twd": ds_amt,
            "total_revenue_twd": total,
            "target_twd": target,
            "achievement_pct": round(total / target * 100, 1) if target > 0 else 0,
        })

    ranking.sort(key=lambda x: -x["total_revenue_twd"])
    for i, r in enumerate(ranking):
        r["rank"] = i + 1

    return {"month": month_start.strftime("%Y-%m"), "ranking": ranking}
