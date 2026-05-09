"""
CRM 進階 API 路由（E-06 ～ E-08 + F 段）

端點：
  GET  /crm/alerts                    — 7 項智慧告警
  GET  /crm/churn-alerts              — 流失預警清單
  GET  /crm/dashboard/manager         — 主管儀表板
  GET  /customers/visit-schedule      — 拜訪頻率提醒
  GET  /customers/funnel              — 開發漏斗分析
  PUT  /customers/{id}/dev-status     — 更新開發階段
  GET  /customers/reorder-cycle       — 訂單週期預測
  POST /customers/{id}/health-recalc  — 重算健康分數
  GET  /customers/{id}/health-score   — 查看健康分數
  POST /customers/predict-next-order  — 批次預測下次下單

  GET/POST   /crm/opportunities       — 銷售機會 CRUD
  GET/POST   /crm/follow-logs         — 跟進記錄 CRUD
  GET/POST   /crm/visit-records       — 拜訪紀錄 CRUD
  GET/POST   /crm/sales-targets       — KPI 目標管理
  GET/POST   /crm/quotations          — 報價單管理
  GET/POST   /crm/sample-requests     — 樣品申請管理
"""
import logging
from datetime import date, datetime, timedelta
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from database import get_db
from models.customer import Customer
from models.crm import (
    SalesTarget, SalesDailyReport, SalesOpportunity,
    FollowUpLog, VisitRecord, Quotation, QuotationItem, SampleRequest,
)
from utils.dependencies import get_current_user, check_permission
from utils.scope import apply_customer_scope

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/crm", tags=["CRM 進階"])


# ─── E-06 智慧告警 ─────────────────────────────────────────

@router.get("/alerts")
def get_crm_alerts(
    db: Session = Depends(get_db),
    current_user=Depends(check_permission("crm", "read")),
):
    """7 項統一 CRM 告警"""
    today = date.today()
    alerts = []

    # 基礎 query（依 scope 過濾）
    base_q = db.query(Customer).filter(
        Customer.is_active == True,
        Customer.deleted_at.is_(None),
    )
    base_q = apply_customer_scope(base_q, current_user)

    customers = base_q.all()

    for c in customers:
        # 1. 7 天以上未聯繫
        if c.last_contact_date and (today - c.last_contact_date).days >= 7:
            alerts.append({
                "type": "no_contact_7d",
                "level": "warning",
                "customer_id": str(c.id),
                "customer_name": c.name,
                "days": (today - c.last_contact_date).days,
                "message": f"已 {(today - c.last_contact_date).days} 天未聯繫",
            })

        # 2. 今天到期跟進
        if c.next_follow_up_date == today:
            alerts.append({
                "type": "follow_up_today",
                "level": "info",
                "customer_id": str(c.id),
                "customer_name": c.name,
                "message": "今天到期跟進",
            })

        # 3. 逾期跟進
        if c.next_follow_up_date and c.next_follow_up_date < today:
            days_overdue = (today - c.next_follow_up_date).days
            alerts.append({
                "type": "follow_up_overdue",
                "level": "urgent",
                "customer_id": str(c.id),
                "customer_name": c.name,
                "days_overdue": days_overdue,
                "message": f"跟進逾期 {days_overdue} 天",
            })

        # 4. 接近回購日（7 天內）
        if c.predicted_next_order:
            days_to_reorder = (c.predicted_next_order - today).days
            if 0 <= days_to_reorder <= 7:
                alerts.append({
                    "type": "reorder_approaching",
                    "level": "info",
                    "customer_id": str(c.id),
                    "customer_name": c.name,
                    "days_to_reorder": days_to_reorder,
                    "predicted_date": c.predicted_next_order.isoformat(),
                    "message": f"預計 {days_to_reorder} 天後回購",
                })

    # 5. 逾期報價未成交（>30 天）
    overdue_quotes = (
        db.query(Quotation)
        .filter(
            Quotation.status == "sent",
            Quotation.sent_at.isnot(None),
            Quotation.deleted_at.is_(None),
        )
        .all()
    )
    for q in overdue_quotes:
        if q.sent_at and (datetime.utcnow() - q.sent_at).days > 30:
            alerts.append({
                "type": "quote_overdue",
                "level": "warning",
                "quotation_id": str(q.id),
                "quotation_no": q.quotation_no,
                "customer_id": str(q.customer_id),
                "days": (datetime.utcnow() - q.sent_at).days,
                "message": f"報價單 {q.quotation_no} 逾期 {(datetime.utcnow() - q.sent_at).days} 天未成交",
            })

    # 6. 待回饋樣品（已寄出 > 14 天未收到反饋）
    pending_samples = (
        db.query(SampleRequest)
        .filter(
            SampleRequest.status == "sent",
            SampleRequest.sent_date.isnot(None),
            SampleRequest.deleted_at.is_(None),
        )
        .all()
    )
    for s in pending_samples:
        if s.sent_date and (today - s.sent_date).days > 14:
            alerts.append({
                "type": "sample_feedback_pending",
                "level": "info",
                "sample_id": str(s.id),
                "customer_id": str(s.customer_id),
                "days_since_sent": (today - s.sent_date).days,
                "message": f"樣品 {s.request_no} 已寄出 {(today - s.sent_date).days} 天，待客戶反饋",
            })

    # 按 level 排序
    level_order = {"urgent": 0, "warning": 1, "info": 2}
    alerts.sort(key=lambda x: level_order.get(x.get("level", "info"), 99))

    return {"total": len(alerts), "alerts": alerts}


@router.get("/churn-alerts")
def get_churn_alerts(
    min_level: str = Query(default="MEDIUM", regex="^(CRITICAL|HIGH|MEDIUM|LOW)$"),
    db: Session = Depends(get_db),
    current_user=Depends(check_permission("crm", "read")),
):
    """流失預警清單"""
    from services.churn_detection import get_churn_alerts as _get_alerts
    return _get_alerts(db, min_level=min_level)


# ─── E-07 主管儀表板 ─────────────────────────────────────

@router.get("/dashboard/manager")
def get_manager_dashboard(
    db: Session = Depends(get_db),
    current_user=Depends(check_permission("crm", "view_performance")),
):
    """主管儀表板 — 今日指標 + Pipeline 漏斗 + 業務排名"""
    from models.sales import SalesOrder
    from models.user import User, Role
    from sqlalchemy import func

    today = date.today()
    month_start = today.replace(day=1)

    # 本月累計
    month_revenue = (
        db.query(func.sum(SalesOrder.total_amount_twd))
        .filter(
            SalesOrder.status.notin_(["draft", "cancelled"]),
            SalesOrder.order_date >= month_start,
        )
        .scalar() or 0
    )

    month_orders = (
        db.query(func.count(SalesOrder.id))
        .filter(
            SalesOrder.status.notin_(["draft", "cancelled"]),
            SalesOrder.order_date >= month_start,
        )
        .scalar() or 0
    )

    # Pipeline 漏斗：各 dev_status 數量
    funnel_data = (
        db.query(Customer.dev_status, func.count(Customer.id).label("count"))
        .filter(Customer.is_active == True, Customer.deleted_at.is_(None))
        .group_by(Customer.dev_status)
        .all()
    )
    funnel = {row.dev_status: row.count for row in funnel_data}

    # 業務排名（本月）
    sales_rank = (
        db.query(
            SalesOrder.created_by,
            func.count(SalesOrder.id).label("order_count"),
            func.sum(SalesOrder.total_amount_twd).label("revenue"),
        )
        .filter(
            SalesOrder.status.notin_(["draft", "cancelled"]),
            SalesOrder.order_date >= month_start,
        )
        .group_by(SalesOrder.created_by)
        .order_by(func.sum(SalesOrder.total_amount_twd).desc())
        .limit(10)
        .all()
    )

    rank_list = []
    for row in sales_rank:
        user = db.query(User).filter(User.id == row.created_by).first()
        rank_list.append({
            "user_id": str(row.created_by) if row.created_by else None,
            "name": user.full_name if user else "未知",
            "order_count": row.order_count,
            "revenue": float(row.revenue or 0),
        })

    # 今日待辦：逾期跟進數
    overdue_followup_count = (
        db.query(func.count(Customer.id))
        .filter(
            Customer.is_active == True,
            Customer.next_follow_up_date < today,
            Customer.deleted_at.is_(None),
        )
        .scalar() or 0
    )

    return {
        "month_summary": {
            "revenue": float(month_revenue),
            "orders": int(month_orders),
        },
        "pipeline_funnel": funnel,
        "sales_ranking": rank_list,
        "overdue_followup_count": overdue_followup_count,
    }


# ─── E-08 開發階段 ────────────────────────────────────────

@router.put("/customers/{customer_id}/dev-status")
def update_dev_status(
    customer_id: UUID,
    new_status: str,
    db: Session = Depends(get_db),
    current_user=Depends(check_permission("customer", "update")),
):
    """更新客戶開發階段"""
    valid_statuses = [
        "potential", "contacted", "visited", "negotiating",
        "trial", "closed", "stable_repurchase", "dormant", "churned",
    ]
    if new_status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"無效的開發階段：{new_status}")

    customer = db.query(Customer).filter(
        Customer.id == customer_id,
        Customer.deleted_at.is_(None),
    ).first()
    if not customer:
        raise HTTPException(status_code=404, detail="客戶不存在")

    customer.dev_status = new_status
    customer.updated_by = current_user.id
    db.commit()
    return {"customer_id": str(customer_id), "dev_status": new_status}


@router.get("/customers/funnel")
def get_customer_funnel(
    db: Session = Depends(get_db),
    current_user=Depends(check_permission("customer", "read")),
):
    """客戶開發漏斗分析"""
    from sqlalchemy import func

    stage_order = [
        "potential", "contacted", "visited", "negotiating",
        "trial", "closed", "stable_repurchase",
    ]

    funnel_data = (
        db.query(Customer.dev_status, func.count(Customer.id).label("count"))
        .filter(Customer.is_active == True, Customer.deleted_at.is_(None))
        .group_by(Customer.dev_status)
        .all()
    )
    counts = {row.dev_status: row.count for row in funnel_data}

    # 轉化率計算
    result = []
    prev_count = None
    for stage in stage_order:
        count = counts.get(stage, 0)
        conv_rate = round(count / prev_count * 100, 1) if prev_count and prev_count > 0 else None
        result.append({
            "stage": stage,
            "count": count,
            "conversion_rate_from_prev": conv_rate,
        })
        if count > 0:
            prev_count = count

    dormant  = counts.get("dormant", 0)
    churned  = counts.get("churned", 0)

    return {
        "funnel": result,
        "dormant": dormant,
        "churned": churned,
        "total_active": sum(counts.get(s, 0) for s in stage_order),
    }


# ─── 健康分數 API ─────────────────────────────────────────

@router.get("/customers/{customer_id}/health-score")
def get_customer_health_score(
    customer_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(check_permission("customer", "read")),
):
    """查看客戶健康分數"""
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="客戶不存在")
    return {
        "customer_id": str(customer_id),
        "health_score": customer.health_score,
        "health_level": customer.health_level,
        "health_updated_at": customer.health_updated_at.isoformat() if customer.health_updated_at else None,
    }


@router.post("/customers/{customer_id}/health-recalc")
def recalc_health_score(
    customer_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(check_permission("customer", "update")),
):
    """手動觸發健康分數重算"""
    from services.health_score import recalc_customer_health
    score, level = recalc_customer_health(db, customer_id)
    db.commit()
    return {"customer_id": str(customer_id), "health_score": score, "health_level": level}


# ─── 訂單週期預測 API ─────────────────────────────────────

@router.get("/customers/reorder-cycle")
def get_reorder_cycle(
    db: Session = Depends(get_db),
    current_user=Depends(check_permission("customer", "read")),
):
    """所有客戶訂單週期預測"""
    from services.order_prediction import get_reorder_cycle_list
    return get_reorder_cycle_list(db)


@router.post("/customers/{customer_id}/predict-next-order")
def predict_single_customer(
    customer_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(check_permission("customer", "read")),
):
    """單一客戶下次下單預測"""
    from services.order_prediction import predict_next_order
    return predict_next_order(db, customer_id)


# ─── 銷售機會 CRUD ────────────────────────────────────────

@router.get("/opportunities")
def list_opportunities(
    stage: Optional[str] = None,
    customer_id: Optional[UUID] = None,
    db: Session = Depends(get_db),
    current_user=Depends(check_permission("opportunity", "read")),
):
    """銷售機會清單"""
    q = db.query(SalesOpportunity).filter(SalesOpportunity.deleted_at.is_(None))
    if stage:
        q = q.filter(SalesOpportunity.stage == stage)
    if customer_id:
        q = q.filter(SalesOpportunity.customer_id == customer_id)
    return q.order_by(SalesOpportunity.created_at.desc()).all()


@router.post("/opportunities", status_code=201)
def create_opportunity(
    data: dict,
    db: Session = Depends(get_db),
    current_user=Depends(check_permission("opportunity", "create")),
):
    """建立銷售機會"""
    opp = SalesOpportunity(**data, created_by=current_user.id)
    db.add(opp)
    db.commit()
    db.refresh(opp)
    return opp


# ─── 跟進記錄 CRUD ────────────────────────────────────────

@router.get("/follow-logs")
def list_follow_logs(
    customer_id: Optional[UUID] = None,
    db: Session = Depends(get_db),
    current_user=Depends(check_permission("crm", "read")),
):
    """跟進記錄清單"""
    q = db.query(FollowUpLog)
    if customer_id:
        q = q.filter(FollowUpLog.customer_id == customer_id)
    return q.order_by(FollowUpLog.log_date.desc()).limit(200).all()


@router.post("/follow-logs", status_code=201)
def create_follow_log(
    data: dict,
    db: Session = Depends(get_db),
    current_user=Depends(check_permission("crm", "create")),
):
    """新增跟進記錄"""
    log = FollowUpLog(**data, created_by=current_user.id)
    db.add(log)

    # 更新客戶的最後聯繫日
    if log.customer_id:
        customer = db.query(Customer).filter(Customer.id == log.customer_id).first()
        if customer:
            customer.last_contact_date = log.log_date or date.today()
            if log.next_follow_up_date:
                customer.next_follow_up_date = log.next_follow_up_date

    db.commit()
    db.refresh(log)
    return log


# ─── 拜訪紀錄 CRUD ────────────────────────────────────────

@router.get("/visit-records")
def list_visit_records(
    customer_id: Optional[UUID] = None,
    db: Session = Depends(get_db),
    current_user=Depends(check_permission("visit", "read")),
):
    """拜訪紀錄清單"""
    q = db.query(VisitRecord)
    if customer_id:
        q = q.filter(VisitRecord.customer_id == customer_id)
    return q.order_by(VisitRecord.visit_date.desc()).limit(200).all()


@router.post("/visit-records", status_code=201)
def create_visit_record(
    data: dict,
    db: Session = Depends(get_db),
    current_user=Depends(check_permission("visit", "create")),
):
    """新增拜訪紀錄"""
    record = VisitRecord(**data, visited_by=current_user.id)
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


# ─── 拜訪頻率提醒 ─────────────────────────────────────────

@router.get("/customers/visit-schedule")
def get_visit_schedule(
    db: Session = Depends(get_db),
    current_user=Depends(check_permission("customer", "read")),
):
    """拜訪頻率提醒（A 級 14 天 / B 級 30 天 / C 級 60 天）"""
    freq_map = {"A": 14, "B": 30, "C": 60, "D": 90}
    today = date.today()

    base_q = db.query(Customer).filter(
        Customer.is_active == True,
        Customer.deleted_at.is_(None),
    )
    base_q = apply_customer_scope(base_q, current_user)
    customers = base_q.all()

    overdue = []
    for c in customers:
        freq = freq_map.get(c.grade or "D", 90)
        last = c.last_contact_date or c.created_at.date() if hasattr(c.created_at, "date") else today
        days_since = (today - last).days if last else 999
        if days_since >= freq:
            overdue.append({
                "customer_id": str(c.id),
                "customer_name": c.name,
                "grade": c.grade,
                "days_since_contact": days_since,
                "recommended_frequency_days": freq,
                "overdue_days": days_since - freq,
                "last_contact_date": last.isoformat() if last else None,
            })

    overdue.sort(key=lambda x: x["overdue_days"], reverse=True)
    return {"total": len(overdue), "items": overdue}


# ─── KPI 目標管理 ─────────────────────────────────────────

@router.get("/sales-targets")
def list_sales_targets(
    year: Optional[int] = None,
    month: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user=Depends(check_permission("crm", "read")),
):
    """KPI 目標清單"""
    q = db.query(SalesTarget)
    if year and month:
        target_month = date(year, month, 1)
        q = q.filter(SalesTarget.target_month == target_month)
    return q.order_by(SalesTarget.target_month.desc()).all()


@router.post("/sales-targets", status_code=201)
def create_sales_target(
    data: dict,
    db: Session = Depends(get_db),
    current_user=Depends(check_permission("crm", "create")),
):
    """設定 KPI 目標"""
    target = SalesTarget(**data)
    db.add(target)
    db.commit()
    db.refresh(target)
    return target


# ─── 報價單管理 ───────────────────────────────────────────

@router.get("/quotations")
def list_quotations(
    customer_id: Optional[UUID] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user=Depends(check_permission("quotation", "read")),
):
    """報價單清單"""
    q = db.query(Quotation).filter(Quotation.deleted_at.is_(None))
    if customer_id:
        q = q.filter(Quotation.customer_id == customer_id)
    if status:
        q = q.filter(Quotation.status == status)
    return q.order_by(Quotation.created_at.desc()).all()


@router.post("/quotations", status_code=201)
def create_quotation(
    data: dict,
    db: Session = Depends(get_db),
    current_user=Depends(check_permission("quotation", "create")),
):
    """建立報價單"""
    from utils.seq import next_seq_no, make_daily_prefix
    items_data = data.pop("items", [])
    prefix = make_daily_prefix("QT")
    quotation_no = next_seq_no(db, Quotation, Quotation.quotation_no, prefix)
    q = Quotation(**data, quotation_no=quotation_no, created_by=current_user.id)
    db.add(q)
    db.flush()
    for item in items_data:
        db.add(QuotationItem(**item, quotation_id=q.id))
    db.commit()
    db.refresh(q)
    return q


# ─── 樣品申請管理 ─────────────────────────────────────────

@router.get("/sample-requests")
def list_sample_requests(
    customer_id: Optional[UUID] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user=Depends(check_permission("sample", "read")),
):
    """樣品申請清單"""
    q = db.query(SampleRequest).filter(SampleRequest.deleted_at.is_(None))
    if customer_id:
        q = q.filter(SampleRequest.customer_id == customer_id)
    if status:
        q = q.filter(SampleRequest.status == status)
    return q.order_by(SampleRequest.created_at.desc()).all()


@router.post("/sample-requests", status_code=201)
def create_sample_request(
    data: dict,
    db: Session = Depends(get_db),
    current_user=Depends(check_permission("sample", "create")),
):
    """建立樣品申請"""
    from utils.seq import next_seq_no, make_daily_prefix
    prefix = make_daily_prefix("SR")
    request_no = next_seq_no(db, SampleRequest, SampleRequest.request_no, prefix)
    sr = SampleRequest(**data, request_no=request_no, created_by=current_user.id)
    db.add(sr)
    db.commit()
    db.refresh(sr)
    return sr


# ─── 健康分警報 API（P-04 前端所需路徑）────────────────────

@router.get("/alerts/health-score")
def get_health_score_alerts(
    min_level: str = Query(default="YELLOW"),
    limit: int = Query(default=50),
    db: Session = Depends(get_db),
    current_user=Depends(check_permission("crm", "read")),
):
    """客戶健康分等級警報（min_level: YELLOW/ORANGE/RED）"""
    from services.health_score import recalc_all_customers
    level_order = {"GREEN": 0, "YELLOW": 1, "ORANGE": 2, "RED": 3}
    min_idx = level_order.get(min_level, 1)

    customers = db.query(Customer).filter(Customer.deleted_at.is_(None)).limit(200).all()
    results = []
    for c in customers:
        hl = c.health_level or "GREEN"
        if level_order.get(hl, 0) >= min_idx:
            results.append({
                "customer_id":   str(c.id),
                "customer_name": c.company_name,
                "health_level":  hl,
                "health_score":  float(c.health_score) if c.health_score else None,
            })
    results.sort(key=lambda x: level_order.get(x["health_level"], 0), reverse=True)
    return {"items": results[:limit], "total": len(results)}


@router.get("/alerts/churn")
def get_churn_score_alerts(
    min_level: str = Query(default="MEDIUM"),
    limit: int = Query(default=50),
    db: Session = Depends(get_db),
    current_user=Depends(check_permission("crm", "read")),
):
    """流失風險警報（min_level: MEDIUM/HIGH/CRITICAL）"""
    churn_order = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}
    min_idx = churn_order.get(min_level, 1)

    customers = db.query(Customer).filter(Customer.deleted_at.is_(None)).limit(200).all()
    results = []
    for c in customers:
        cl = c.churn_level or "LOW"
        if churn_order.get(cl, 0) >= min_idx:
            results.append({
                "customer_id":   str(c.id),
                "customer_name": c.company_name,
                "churn_level":   cl,
                "churn_score":   float(c.churn_score) if c.churn_score else None,
            })
    results.sort(key=lambda x: churn_order.get(x["churn_level"], 0), reverse=True)
    return {"items": results[:limit], "total": len(results)}


# ─── PATCH opportunity stage ─────────────────────────────

@router.patch("/opportunities/{opp_id}")
def patch_opportunity(
    opp_id: UUID,
    data: dict,
    db: Session = Depends(get_db),
    current_user=Depends(check_permission("crm", "update")),
):
    """更新商機階段或欄位"""
    opp = db.query(SalesOpportunity).filter(
        SalesOpportunity.id == opp_id,
        SalesOpportunity.deleted_at.is_(None),
    ).first()
    if not opp:
        raise HTTPException(status_code=404, detail="商機不存在")
    for k, v in data.items():
        if hasattr(opp, k):
            setattr(opp, k, v)
    db.commit()
    db.refresh(opp)
    return opp


# ─── 業務排程 (F-06) ─────────────────────────────────────

@router.get("/schedules")
def list_schedules(
    schedule_date: Optional[str] = None,
    limit: int = Query(default=50),
    db: Session = Depends(get_db),
    current_user=Depends(check_permission("crm", "read")),
):
    """業務排程列表"""
    from models.crm import SalesSchedule
    q = db.query(SalesSchedule).filter(SalesSchedule.deleted_at.is_(None))
    if schedule_date:
        from datetime import date as dtdate
        q = q.filter(SalesSchedule.schedule_date == dtdate.fromisoformat(schedule_date))
    items = q.order_by(SalesSchedule.schedule_date.desc()).limit(limit).all()
    return {"items": [i.__dict__ for i in items], "total": len(items)}


@router.post("/schedules", status_code=201)
def create_schedule(
    data: dict,
    db: Session = Depends(get_db),
    current_user=Depends(check_permission("crm", "create")),
):
    """建立業務排程"""
    from models.crm import SalesSchedule
    sched = SalesSchedule(**data, sales_rep_id=current_user.id, created_by=current_user.id)
    db.add(sched)
    db.commit()
    db.refresh(sched)
    return sched


@router.patch("/schedules/{sched_id}")
def patch_schedule(
    sched_id: UUID,
    data: dict,
    db: Session = Depends(get_db),
    current_user=Depends(check_permission("crm", "update")),
):
    """更新排程（例如標記完成）"""
    from models.crm import SalesSchedule
    sched = db.query(SalesSchedule).filter(
        SalesSchedule.id == sched_id,
        SalesSchedule.deleted_at.is_(None),
    ).first()
    if not sched:
        raise HTTPException(status_code=404, detail="排程不存在")
    for k, v in data.items():
        if hasattr(sched, k):
            setattr(sched, k, v)
    db.commit()
    db.refresh(sched)
    return sched


# ─── 報價審批 (F-07) ─────────────────────────────────────

@router.get("/quotation-approvals")
def list_quotation_approvals(
    status: Optional[str] = None,
    limit: int = Query(default=50),
    db: Session = Depends(get_db),
    current_user=Depends(check_permission("quotation", "approve")),
):
    """報價核准列表"""
    from models.crm import QuotationApproval
    q = db.query(QuotationApproval)
    if status:
        q = q.filter(QuotationApproval.status == status)
    items = q.order_by(QuotationApproval.created_at.desc()).limit(limit).all()
    return {"items": [i.__dict__ for i in items], "total": len(items)}


@router.post("/quotation-approvals/{approval_id}/decide")
def decide_quotation_approval(
    approval_id: UUID,
    data: dict,
    db: Session = Depends(get_db),
    current_user=Depends(check_permission("quotation", "approve")),
):
    """核准或拒絕報價"""
    from models.crm import QuotationApproval
    from datetime import datetime
    approval = db.query(QuotationApproval).filter(QuotationApproval.id == approval_id).first()
    if not approval:
        raise HTTPException(status_code=404, detail="審批記錄不存在")
    decision = data.get("decision")
    if decision not in ("approved", "rejected"):
        raise HTTPException(status_code=422, detail="decision 必須為 approved 或 rejected")
    approval.status     = decision
    approval.approver_id = current_user.id
    approval.comment    = data.get("comment")
    approval.decided_at = datetime.utcnow()
    db.commit()
    db.refresh(approval)
    return approval
