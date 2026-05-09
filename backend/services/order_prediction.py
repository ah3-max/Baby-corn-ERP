"""
客戶訂單預測服務

演算法：
  1. 取最近 20 筆訂單（排除 draft/cancelled）
  2. 計算訂單間隔的平均與標準差
  3. 趨勢偵測（比較前半段 vs 後半段間隔）
  4. 預測下次下單日 = 最後下單日 + 平均間隔
  5. 信心度 = ≥6筆 HIGH / ≥3筆 MEDIUM / <3筆 LOW

API：
  POST /customers/predict-next-order   → 單一客戶預測
  GET  /customers/reorder-cycle        → 所有客戶週期列表
"""
import logging
from datetime import date, timedelta
from statistics import mean, stdev
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import desc

logger = logging.getLogger(__name__)


def predict_next_order(
    db: Session,
    customer_id: UUID,
) -> dict:
    """
    預測客戶下次下單日期。

    Returns:
        {
            "customer_id": str,
            "avg_interval_days": float | None,
            "predicted_next_order": str (ISO date) | None,
            "confidence": "HIGH" | "MEDIUM" | "LOW",
            "order_trend": "GROWING" | "DECLINING" | "STABLE",
            "order_count": int,
        }
    """
    from models.sales import SalesOrder

    orders = (
        db.query(SalesOrder)
        .filter(
            SalesOrder.customer_id == customer_id,
            SalesOrder.status.notin_(["draft", "cancelled"]),
        )
        .order_by(desc(SalesOrder.order_date))
        .limit(20)
        .all()
    )

    result: dict = {
        "customer_id": str(customer_id),
        "avg_interval_days": None,
        "predicted_next_order": None,
        "confidence": "LOW",
        "order_trend": "STABLE",
        "order_count": len(orders),
    }

    if len(orders) < 2:
        return result

    # 計算間隔（天）
    dates = sorted([o.order_date for o in orders if o.order_date], reverse=True)
    intervals = [
        (dates[i] - dates[i + 1]).days
        for i in range(len(dates) - 1)
        if (dates[i] - dates[i + 1]).days > 0
    ]

    if not intervals:
        return result

    avg_interval = mean(intervals)
    result["avg_interval_days"] = round(avg_interval, 1)

    # 信心度
    if len(intervals) >= 6:
        result["confidence"] = "HIGH"
    elif len(intervals) >= 3:
        result["confidence"] = "MEDIUM"
    else:
        result["confidence"] = "LOW"

    # 趨勢偵測：比較前半段 vs 後半段平均間隔
    if len(intervals) >= 4:
        half = len(intervals) // 2
        recent_avg = mean(intervals[:half])    # 近期
        old_avg    = mean(intervals[half:])    # 較早
        if old_avg > 0:
            ratio = recent_avg / old_avg
            if ratio < 0.8:
                result["order_trend"] = "GROWING"    # 間隔縮短 = 訂購更頻繁
            elif ratio > 1.2:
                result["order_trend"] = "DECLINING"  # 間隔拉長 = 訂購減少
            else:
                result["order_trend"] = "STABLE"

    # 預測下次下單日
    last_date = dates[0]
    predicted = last_date + timedelta(days=round(avg_interval))
    result["predicted_next_order"] = predicted.isoformat()

    return result


def update_customer_prediction(db: Session, customer_id: UUID) -> None:
    """
    執行預測並將結果寫回 Customer model。
    """
    from models.customer import Customer
    from datetime import datetime

    prediction = predict_next_order(db, customer_id)
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        return

    # 更新 Customer 欄位
    if prediction["avg_interval_days"] is not None:
        customer.avg_order_interval = prediction["avg_interval_days"]

    if prediction["predicted_next_order"]:
        customer.predicted_next_order = date.fromisoformat(prediction["predicted_next_order"])

    customer.prediction_confidence = prediction["confidence"]
    customer.order_trend = prediction["order_trend"]


def get_reorder_cycle_list(db: Session) -> list[dict]:
    """
    取得所有活躍客戶的訂單週期列表。

    GET /customers/reorder-cycle
    """
    from models.customer import Customer

    customers = (
        db.query(Customer)
        .filter(
            Customer.is_active == True,
            Customer.deleted_at.is_(None),
        )
        .all()
    )

    results = []
    for customer in customers:
        pred = predict_next_order(db, customer.id)
        results.append({
            "customer_id": str(customer.id),
            "customer_name": customer.name,
            "avg_interval_days": pred["avg_interval_days"],
            "predicted_next_order": pred["predicted_next_order"],
            "confidence": pred["confidence"],
            "order_trend": pred["order_trend"],
            "order_count": pred["order_count"],
            "last_order_date": customer.last_order_date.isoformat() if customer.last_order_date else None,
        })

    # 依預測下次下單日升冪排列（最快要到期的在前）
    results.sort(
        key=lambda x: x["predicted_next_order"] or "9999-12-31"
    )
    return results
