"""
WP6：庫存智慧分析 API

  GET /inventory/analytics/aging              - 庫齡分佈
  GET /inventory/analytics/turnover           - 庫存周轉率
  GET /inventory/analytics/depletion-forecast - 預估耗盡日期
  GET /inventory/analytics/reorder-suggestion - 建議下單時間與數量
"""
from typing import Optional
from datetime import date, datetime, timedelta
from decimal import Decimal
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from database import get_db
from models.user import User
from models.inventory import InventoryLot, InventoryTransaction
from models.daily_sale import DailySaleItem
from models.sales import SalesOrderItem
from models.batch import Batch
from models.system import SystemSetting
from utils.dependencies import check_permission

router = APIRouter(prefix="/inventory/analytics", tags=["庫存智慧分析"])


# ─── 庫齡分佈 ───────────────────────────────────────────

@router.get("/aging")
def aging_analysis(
    warehouse_id: Optional[str] = Query(None),
    db:           Session = Depends(get_db),
    _:            User = Depends(check_permission("stock", "read")),
):
    """庫齡分佈分析（0-7d, 8-14d, 15-21d, 21d+）"""
    today = date.today()
    q = db.query(InventoryLot).filter(InventoryLot.status.in_(["active", "low_stock"]))
    if warehouse_id:
        q = q.filter(InventoryLot.warehouse_id == warehouse_id)
    lots = q.all()

    buckets = {
        "0_7":   {"count": 0, "weight_kg": 0, "boxes": 0},
        "8_14":  {"count": 0, "weight_kg": 0, "boxes": 0},
        "15_21": {"count": 0, "weight_kg": 0, "boxes": 0},
        "22_plus": {"count": 0, "weight_kg": 0, "boxes": 0},
    }
    details = []

    for lot in lots:
        age = (today - lot.received_date).days
        w = float(lot.current_weight_kg)
        b = lot.current_boxes or 0

        if age <= 7:
            key = "0_7"
        elif age <= 14:
            key = "8_14"
        elif age <= 21:
            key = "15_21"
        else:
            key = "22_plus"

        buckets[key]["count"] += 1
        buckets[key]["weight_kg"] += w
        buckets[key]["boxes"] += b

        details.append({
            "lot_no": lot.lot_no,
            "batch_id": str(lot.batch_id),
            "age_days": age,
            "weight_kg": round(w, 2),
            "boxes": b,
            "warehouse_id": str(lot.warehouse_id),
            "received_date": str(lot.received_date),
        })

    for v in buckets.values():
        v["weight_kg"] = round(v["weight_kg"], 2)

    return {
        "date": str(today),
        "total_lots": len(lots),
        "total_weight_kg": round(sum(v["weight_kg"] for v in buckets.values()), 2),
        "buckets": buckets,
        "critical_lots": sorted(
            [d for d in details if d["age_days"] > 14],
            key=lambda x: -x["age_days"]
        )[:10],
    }


# ─── 庫存周轉率 ─────────────────────────────────────────

@router.get("/turnover")
def turnover_rate(
    days: int = Query(30, description="計算天數"),
    db:   Session = Depends(get_db),
    _:    User = Depends(check_permission("stock", "read")),
):
    """庫存周轉率 = 期間出庫量 / 平均庫存量"""
    today = date.today()
    start_date = today - timedelta(days=days)

    # 期間出庫量（out 交易）
    out_total = db.query(
        func.coalesce(func.sum(InventoryTransaction.weight_kg), 0)
    ).filter(
        InventoryTransaction.txn_type == "out",
        InventoryTransaction.created_at >= datetime.combine(start_date, datetime.min.time()),
    ).scalar()

    # 目前庫存
    current_stock = db.query(
        func.coalesce(func.sum(InventoryLot.current_weight_kg), 0)
    ).filter(InventoryLot.status.in_(["active", "low_stock"])).scalar()

    # 期間入庫量
    in_total = db.query(
        func.coalesce(func.sum(InventoryTransaction.weight_kg), 0)
    ).filter(
        InventoryTransaction.txn_type == "in",
        InventoryTransaction.created_at >= datetime.combine(start_date, datetime.min.time()),
    ).scalar()

    avg_stock = (float(current_stock) + float(current_stock) - float(in_total) + float(out_total)) / 2
    avg_stock = max(avg_stock, 1)  # 避免除以零

    turnover = float(out_total) / avg_stock
    days_on_hand = avg_stock / (float(out_total) / max(days, 1)) if float(out_total) > 0 else 999

    return {
        "period_days": days,
        "out_total_kg": round(float(out_total), 2),
        "in_total_kg": round(float(in_total), 2),
        "current_stock_kg": round(float(current_stock), 2),
        "avg_stock_kg": round(avg_stock, 2),
        "turnover_rate": round(turnover, 2),
        "avg_days_on_hand": round(days_on_hand, 1),
    }


# ─── 耗盡預測 ───────────────────────────────────────────

@router.get("/depletion-forecast")
def depletion_forecast(
    db: Session = Depends(get_db),
    _:  User = Depends(check_permission("stock", "read")),
):
    """預估每個活躍庫存批次的耗盡日期"""
    today = date.today()
    start_30d = today - timedelta(days=30)

    # 過去 30 天每日平均出庫量
    daily_out = db.query(
        func.coalesce(func.sum(InventoryTransaction.weight_kg), 0)
    ).filter(
        InventoryTransaction.txn_type == "out",
        InventoryTransaction.created_at >= datetime.combine(start_30d, datetime.min.time()),
    ).scalar()
    avg_daily_out = float(daily_out) / 30

    # 每個活躍 lot 的預估耗盡
    lots = db.query(InventoryLot).filter(
        InventoryLot.status.in_(["active", "low_stock"])
    ).order_by(InventoryLot.received_date.asc()).all()

    forecasts = []
    total_stock = 0
    for lot in lots:
        w = float(lot.current_weight_kg)
        total_stock += w
        days_left = int(w / avg_daily_out) if avg_daily_out > 0 else 999
        depletion_date = today + timedelta(days=days_left)

        forecasts.append({
            "lot_no": lot.lot_no,
            "batch_id": str(lot.batch_id),
            "current_weight_kg": round(w, 2),
            "age_days": (today - lot.received_date).days,
            "estimated_days_left": days_left,
            "estimated_depletion_date": str(depletion_date),
            "urgency": "critical" if days_left <= 3 else "warning" if days_left <= 7 else "ok",
        })

    # 全部庫存耗盡日
    total_days = int(total_stock / avg_daily_out) if avg_daily_out > 0 else 999

    return {
        "avg_daily_consumption_kg": round(avg_daily_out, 2),
        "total_stock_kg": round(total_stock, 2),
        "total_estimated_days": total_days,
        "total_depletion_date": str(today + timedelta(days=total_days)),
        "lots": sorted(forecasts, key=lambda x: x["estimated_days_left"]),
    }


# ─── 建議下單 ───────────────────────────────────────────

@router.get("/reorder-suggestion")
def reorder_suggestion(
    db: Session = Depends(get_db),
    _:  User = Depends(check_permission("stock", "read")),
):
    """建議下單時間與數量

    邏輯：
    1. 過去 30 天平均日銷量
    2. 目前庫存可供天數
    3. 供應鏈前置時間（系統設定，預設 7 天）
    4. 安全庫存天數（系統設定，預設 3 天）
    5. 若 days_of_stock <= lead_time + safety → 建議立即下單
    """
    today = date.today()
    start_30d = today - timedelta(days=30)

    # 1. 過去 30 天平均日銷量
    so_sold = db.query(
        func.coalesce(func.sum(SalesOrderItem.quantity_kg), 0)
    ).filter(
        SalesOrderItem.sales_order.has(
            and_(
                # 只算已出貨的訂單
            )
        )
    ).scalar()
    ds_sold = db.query(
        func.coalesce(func.sum(DailySaleItem.quantity_kg), 0)
    ).join(DailySaleItem.daily_sale).filter(
        DailySaleItem.daily_sale.has(
            and_()
        )
    ).scalar()

    # 用出庫交易更準確
    out_30d = db.query(
        func.coalesce(func.sum(InventoryTransaction.weight_kg), 0)
    ).filter(
        InventoryTransaction.txn_type == "out",
        InventoryTransaction.created_at >= datetime.combine(start_30d, datetime.min.time()),
    ).scalar()
    avg_daily_sales_kg = float(out_30d) / 30

    # 2. 目前庫存
    current_stock = db.query(
        func.coalesce(func.sum(InventoryLot.current_weight_kg), 0)
    ).filter(InventoryLot.status.in_(["active", "low_stock"])).scalar()
    current_stock_kg = float(current_stock)

    # 3. 可供天數
    days_of_stock = int(current_stock_kg / avg_daily_sales_kg) if avg_daily_sales_kg > 0 else 999

    # 4. 系統設定
    lead_time_days = 7
    safety_stock_days = 3
    lt_setting = db.query(SystemSetting).filter(SystemSetting.key == "supply_chain_lead_time_days").first()
    if lt_setting and lt_setting.value:
        lead_time_days = int(lt_setting.value) if isinstance(lt_setting.value, (int, float)) else 7
    ss_setting = db.query(SystemSetting).filter(SystemSetting.key == "safety_stock_days").first()
    if ss_setting and ss_setting.value:
        safety_stock_days = int(ss_setting.value) if isinstance(ss_setting.value, (int, float)) else 3

    # 5. 建議
    reorder_point_days = lead_time_days + safety_stock_days
    should_reorder = days_of_stock <= reorder_point_days
    suggested_quantity = avg_daily_sales_kg * (lead_time_days + safety_stock_days * 2) if should_reorder else 0

    if should_reorder:
        suggested_order_date = str(today)
        urgency = "immediate" if days_of_stock <= safety_stock_days else "soon"
    else:
        order_in_days = days_of_stock - reorder_point_days
        suggested_order_date = str(today + timedelta(days=order_in_days))
        urgency = "ok"

    return {
        "avg_daily_sales_kg": round(avg_daily_sales_kg, 2),
        "current_stock_kg": round(current_stock_kg, 2),
        "days_of_stock": days_of_stock,
        "lead_time_days": lead_time_days,
        "safety_stock_days": safety_stock_days,
        "reorder_point_days": reorder_point_days,
        "should_reorder": should_reorder,
        "urgency": urgency,
        "suggested_quantity_kg": round(suggested_quantity, 1),
        "suggested_order_date": suggested_order_date,
    }
