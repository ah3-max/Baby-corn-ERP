"""
WP7：計劃模組 API

採購計劃：
  GET/POST  /plans/procurement        - 列表 / 新增
  GET/PUT   /plans/procurement/:id    - 詳情 / 更新
  PUT       /plans/procurement/:id/approve - 審批

天氣預報：
  GET/POST  /plans/weather            - 列表 / 新增

財務計劃：
  GET/POST  /plans/financial          - 列表 / 新增
  PUT       /plans/financial/:id      - 更新
  GET       /plans/financial/:month/vs-actual - 計劃 vs 實際
"""
from uuid import UUID
from typing import List, Optional
from datetime import datetime, date
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func

from database import get_db
from models.user import User
from models.planning import ProcurementPlan, ProcurementPlanItem, WeatherForecast, FinancialPlan
from models.sales import SalesOrder
from models.daily_sale import DailySale
from models.cost import CostEvent
from schemas.planning import (
    ProcurementPlanCreate, ProcurementPlanUpdate, ProcurementPlanOut, ProcurementPlanItemOut,
    WeatherForecastCreate, WeatherForecastOut,
    FinancialPlanCreate, FinancialPlanUpdate, FinancialPlanOut,
)
from utils.dependencies import check_permission

router = APIRouter(prefix="/plans", tags=["計劃管理"])


def _gen_no(db, model, prefix, field):
    from sqlalchemy import text
    db.execute(text(f"SELECT pg_advisory_xact_lock(hashtext('plan_no_{prefix}'))"))
    date_str = date.today().strftime("%Y%m")
    full_prefix = f"{prefix}-{date_str}-"
    count = db.query(func.count(model.id)).filter(field.like(f"{full_prefix}%")).scalar()
    return f"{full_prefix}{str(count + 1).zfill(3)}"


# ─── 採購計劃 ───────────────────────────────────────────

@router.get("/procurement", response_model=List[ProcurementPlanOut])
def list_procurement_plans(
    month:  Optional[str] = Query(None),  # YYYY-MM
    status_filter: Optional[str] = Query(None, alias="status"),
    db:     Session = Depends(get_db),
    _:      User = Depends(check_permission("plan", "view")),
):
    q = db.query(ProcurementPlan).options(joinedload(ProcurementPlan.items))
    if month:
        y, m = map(int, month.split("-"))
        q = q.filter(ProcurementPlan.plan_month == date(y, m, 1))
    if status_filter:
        q = q.filter(ProcurementPlan.status == status_filter)
    return q.order_by(ProcurementPlan.plan_month.desc()).all()


@router.post("/procurement", response_model=ProcurementPlanOut, status_code=status.HTTP_201_CREATED)
def create_procurement_plan(
    payload:      ProcurementPlanCreate,
    db:           Session = Depends(get_db),
    current_user: User = Depends(check_permission("plan", "create")),
):
    plan_no = _gen_no(db, ProcurementPlan, "PP", ProcurementPlan.plan_no)
    plan = ProcurementPlan(
        plan_no=plan_no,
        plan_month=payload.plan_month,
        product_type_id=payload.product_type_id,
        target_quantity_kg=payload.target_quantity_kg,
        target_budget_thb=payload.target_budget_thb,
        weather_risk_note=payload.weather_risk_note,
        season_note=payload.season_note,
        created_by=current_user.id,
    )
    db.add(plan)
    db.flush()

    if payload.items:
        for item_data in payload.items:
            db.add(ProcurementPlanItem(
                plan_id=plan.id,
                supplier_id=item_data.supplier_id,
                week_number=item_data.week_number,
                planned_quantity_kg=item_data.planned_quantity_kg,
                planned_price_per_kg_thb=item_data.planned_price_per_kg_thb,
                weather_condition=item_data.weather_condition,
                note=item_data.note,
            ))
    db.commit()
    return db.query(ProcurementPlan).options(joinedload(ProcurementPlan.items)).filter(ProcurementPlan.id == plan.id).first()


@router.get("/procurement/{plan_id}", response_model=ProcurementPlanOut)
def get_procurement_plan(
    plan_id: UUID,
    db:      Session = Depends(get_db),
    _:       User = Depends(check_permission("plan", "view")),
):
    plan = db.query(ProcurementPlan).options(joinedload(ProcurementPlan.items)).filter(ProcurementPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="採購計劃不存在")
    return plan


@router.put("/procurement/{plan_id}", response_model=ProcurementPlanOut)
def update_procurement_plan(
    plan_id: UUID,
    payload: ProcurementPlanUpdate,
    db:      Session = Depends(get_db),
    _:       User = Depends(check_permission("plan", "edit")),
):
    plan = db.query(ProcurementPlan).filter(ProcurementPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="採購計劃不存在")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(plan, k, v)
    db.commit()
    return db.query(ProcurementPlan).options(joinedload(ProcurementPlan.items)).filter(ProcurementPlan.id == plan_id).first()


@router.put("/procurement/{plan_id}/approve", response_model=ProcurementPlanOut)
def approve_procurement_plan(
    plan_id:      UUID,
    db:           Session = Depends(get_db),
    current_user: User = Depends(check_permission("plan", "approve")),
):
    plan = db.query(ProcurementPlan).filter(ProcurementPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="採購計劃不存在")
    if plan.status != "draft":
        raise HTTPException(status_code=400, detail="僅草稿可審批")
    plan.status = "approved"
    plan.approved_by = current_user.id
    db.commit()
    return db.query(ProcurementPlan).options(joinedload(ProcurementPlan.items)).filter(ProcurementPlan.id == plan_id).first()


# ─── 天氣預報 ───────────────────────────────────────────

@router.get("/weather", response_model=List[WeatherForecastOut])
def list_weather(
    region:    Optional[str]  = Query(None),
    date_from: Optional[date] = Query(None),
    date_to:   Optional[date] = Query(None),
    limit:     int = 30,
    db:        Session = Depends(get_db),
    _:         User = Depends(check_permission("plan", "view")),
):
    q = db.query(WeatherForecast)
    if region:
        q = q.filter(WeatherForecast.region == region)
    if date_from:
        q = q.filter(WeatherForecast.forecast_date >= date_from)
    if date_to:
        q = q.filter(WeatherForecast.forecast_date <= date_to)
    return q.order_by(WeatherForecast.forecast_date.desc()).limit(limit).all()


@router.post("/weather", response_model=WeatherForecastOut, status_code=status.HTTP_201_CREATED)
def create_weather(
    payload: WeatherForecastCreate,
    db:      Session = Depends(get_db),
    _:       User = Depends(check_permission("plan", "create")),
):
    wf = WeatherForecast(**payload.model_dump())
    db.add(wf)
    db.commit()
    db.refresh(wf)
    return wf


# ─── 財務計劃 ───────────────────────────────────────────

@router.get("/financial", response_model=List[FinancialPlanOut])
def list_financial_plans(
    month: Optional[str] = Query(None),
    db:    Session = Depends(get_db),
    _:     User = Depends(check_permission("plan", "view")),
):
    q = db.query(FinancialPlan)
    if month:
        y, m = map(int, month.split("-"))
        q = q.filter(FinancialPlan.plan_month == date(y, m, 1))
    return q.order_by(FinancialPlan.plan_month.desc()).all()


@router.post("/financial", response_model=FinancialPlanOut, status_code=status.HTTP_201_CREATED)
def create_financial_plan(
    payload:      FinancialPlanCreate,
    db:           Session = Depends(get_db),
    current_user: User = Depends(check_permission("plan", "create")),
):
    fp = FinancialPlan(**payload.model_dump(), created_by=current_user.id)
    db.add(fp)
    db.commit()
    db.refresh(fp)
    return fp


@router.put("/financial/{plan_id}", response_model=FinancialPlanOut)
def update_financial_plan(
    plan_id: UUID,
    payload: FinancialPlanUpdate,
    db:      Session = Depends(get_db),
    _:       User = Depends(check_permission("plan", "edit")),
):
    fp = db.query(FinancialPlan).filter(FinancialPlan.id == plan_id).first()
    if not fp:
        raise HTTPException(status_code=404, detail="財務計劃不存在")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(fp, k, v)
    db.commit()
    db.refresh(fp)
    return fp


@router.get("/financial/{month}/vs-actual")
def financial_vs_actual(
    month: str,  # YYYY-MM
    db:    Session = Depends(get_db),
    _:     User = Depends(check_permission("plan", "view")),
):
    """財務計劃 vs 實際對比"""
    y, m = map(int, month.split("-"))
    month_start = date(y, m, 1)
    if m == 12:
        month_end = date(y + 1, 1, 1)
    else:
        month_end = date(y, m + 1, 1)

    fp = db.query(FinancialPlan).filter(FinancialPlan.plan_month == month_start).first()

    # 實際收入
    so_rev = db.query(func.coalesce(func.sum(SalesOrder.total_amount_twd), 0)).filter(
        SalesOrder.order_date >= month_start, SalesOrder.order_date < month_end
    ).scalar()
    ds_rev = db.query(func.coalesce(func.sum(DailySale.total_amount_twd), 0)).filter(
        DailySale.sale_date >= month_start, DailySale.sale_date < month_end
    ).scalar()
    actual_revenue = float(so_rev) + float(ds_rev)

    # 實際成本
    from services.cost_automation import get_system_exchange_rate
    ex_rate = float(get_system_exchange_rate(db))
    cost_result = db.query(
        func.sum(CostEvent.amount_twd).label("twd"),
        func.sum(CostEvent.amount_thb).label("thb"),
    ).filter(
        CostEvent.recorded_at >= datetime.combine(month_start, datetime.min.time()),
        CostEvent.recorded_at < datetime.combine(month_end, datetime.min.time()),
    ).first()
    actual_cost = float(cost_result.twd or 0) + float(cost_result.thb or 0) * ex_rate

    result = {
        "month": month,
        "actual_revenue_twd": round(actual_revenue, 2),
        "actual_cost_twd": round(actual_cost, 2),
        "actual_gross_profit_twd": round(actual_revenue - actual_cost, 2),
    }

    if fp:
        planned_rev = float(fp.planned_revenue_twd or 0)
        result["planned_revenue_twd"] = planned_rev
        result["planned_cogs_twd"] = float(fp.planned_cogs_twd or 0)
        result["planned_gross_profit_twd"] = float(fp.planned_gross_profit_twd or 0)
        result["revenue_variance_pct"] = round((actual_revenue - planned_rev) / planned_rev * 100, 1) if planned_rev > 0 else 0
        # 更新 fp 的實際值
        fp.actual_revenue_twd = actual_revenue
        fp.actual_cogs_twd = actual_cost
        fp.variance_pct = result["revenue_variance_pct"]
        db.commit()
    else:
        result["planned_revenue_twd"] = None
        result["note"] = "此月份尚無財務計劃"

    return result
