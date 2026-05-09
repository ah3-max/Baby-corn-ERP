"""
客戶流失預警服務

風險因素（總計 100 分，分數越高 = 風險越大）：
  1. 下單新近度   35 分  ← 距最後下單天數
  2. 量降趨勢     30 分  ← 近 3 期與前 3 期訂單金額比較
  3. 下單頻率     15 分  ← 與平均下單間隔相比的延遲程度
  4. 互動斷層     15 分  ← 距最後聯繫天數
  5. 逾期跟進      5 分  ← next_follow_up_date 是否已過

流失風險等級：
  CRITICAL  ≥ 60
  HIGH      ≥ 40
  MEDIUM    ≥ 20
  LOW       <  20

API：GET /crm/churn-alerts
"""
import logging
from datetime import date, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import func

logger = logging.getLogger(__name__)


def _risk_recency(last_order_date: date | None) -> float:
    """下單新近度：距最後下單越久，風險越高"""
    if last_order_date is None:
        return 1.0  # 從未下單 = 最高風險
    days = (date.today() - last_order_date).days
    if days <= 30:
        return 0.0
    elif days <= 60:
        return 0.3
    elif days <= 90:
        return 0.6
    elif days <= 180:
        return 0.8
    return 1.0


def _risk_volume_trend(customer_id: UUID, db: Session) -> float:
    """量降趨勢：近 3 期 vs 前 3 期訂單金額比較"""
    try:
        from models.sales import SalesOrder
        from sqlalchemy import desc

        orders = (
            db.query(SalesOrder.total_amount_twd, SalesOrder.order_date)
            .filter(
                SalesOrder.customer_id == customer_id,
                SalesOrder.status.notin_(["draft", "cancelled"]),
            )
            .order_by(desc(SalesOrder.order_date))
            .limit(6)
            .all()
        )

        if len(orders) < 4:
            return 0.0  # 資料不足，不計入

        recent_3 = sum(float(o.total_amount_twd or 0) for o in orders[:3])
        prev_3   = sum(float(o.total_amount_twd or 0) for o in orders[3:6])

        if prev_3 == 0:
            return 0.0

        decline = (prev_3 - recent_3) / prev_3  # 正值 = 下降
        if decline <= 0:
            return 0.0
        elif decline <= 0.1:
            return 0.2
        elif decline <= 0.3:
            return 0.5
        elif decline <= 0.5:
            return 0.8
        return 1.0
    except Exception:
        return 0.0


def _risk_frequency(
    last_order_date: date | None,
    avg_order_interval: float | None,
) -> float:
    """下單頻率：超過平均間隔 1.5 倍才算異常"""
    if last_order_date is None or not avg_order_interval or avg_order_interval <= 0:
        return 0.3
    days_since = (date.today() - last_order_date).days
    ratio = days_since / avg_order_interval
    if ratio <= 1.0:
        return 0.0
    elif ratio <= 1.5:
        return 0.3
    elif ratio <= 2.0:
        return 0.6
    return 1.0


def _risk_engagement(last_contact_date: date | None) -> float:
    """互動斷層：距最後聯繫越久，風險越高"""
    if last_contact_date is None:
        return 0.5
    days = (date.today() - last_contact_date).days
    if days <= 30:
        return 0.0
    elif days <= 60:
        return 0.4
    elif days <= 90:
        return 0.7
    return 1.0


def _risk_overdue_followup(next_follow_up_date: date | None) -> float:
    """逾期跟進：next_follow_up_date 已過則風險最高"""
    if next_follow_up_date is None:
        return 0.0
    if next_follow_up_date < date.today():
        return 1.0
    return 0.0


def calculate_churn_risk(
    customer_id: UUID,
    last_order_date: date | None,
    last_contact_date: date | None,
    next_follow_up_date: date | None,
    avg_order_interval: float | None,
    db: Session,
) -> tuple[float, str]:
    """
    計算單一客戶的流失風險分數與等級。

    Returns:
        (score: float 0~100, level: CRITICAL/HIGH/MEDIUM/LOW)
    """
    r1 = _risk_recency(last_order_date)          * 35
    r2 = _risk_volume_trend(customer_id, db)     * 30
    r3 = _risk_frequency(last_order_date, avg_order_interval) * 15
    r4 = _risk_engagement(last_contact_date)     * 15
    r5 = _risk_overdue_followup(next_follow_up_date) * 5

    score = r1 + r2 + r3 + r4 + r5

    if score >= 60:
        level = "CRITICAL"
    elif score >= 40:
        level = "HIGH"
    elif score >= 20:
        level = "MEDIUM"
    else:
        level = "LOW"

    return round(score, 1), level


def get_churn_alerts(db: Session, min_level: str = "MEDIUM") -> list[dict]:
    """
    取得流失風險警報清單（風險等級 >= min_level）。

    API：GET /crm/churn-alerts

    Returns:
        List of dicts with customer_id, name, risk_score, risk_level, factors
    """
    from models.customer import Customer

    _level_order = {"CRITICAL": 3, "HIGH": 2, "MEDIUM": 1, "LOW": 0}
    min_threshold = _level_order.get(min_level, 1)

    customers = (
        db.query(Customer)
        .filter(
            Customer.is_active == True,
            Customer.deleted_at.is_(None),
            Customer.dev_status.notin_(["churned"]),
        )
        .all()
    )

    alerts = []
    for customer in customers:
        score, level = calculate_churn_risk(
            customer_id=customer.id,
            last_order_date=customer.last_order_date,
            last_contact_date=customer.last_contact_date,
            next_follow_up_date=customer.next_follow_up_date,
            avg_order_interval=customer.avg_order_interval,
            db=db,
        )

        if _level_order.get(level, 0) >= min_threshold:
            alerts.append({
                "customer_id": str(customer.id),
                "customer_name": customer.name,
                "risk_score": score,
                "risk_level": level,
                "last_order_date": customer.last_order_date.isoformat() if customer.last_order_date else None,
                "last_contact_date": customer.last_contact_date.isoformat() if customer.last_contact_date else None,
                "next_follow_up_date": customer.next_follow_up_date.isoformat() if customer.next_follow_up_date else None,
                "assigned_sales_user_id": str(customer.assigned_sales_user_id) if customer.assigned_sales_user_id else None,
            })

    # 依風險分數降冪排列
    alerts.sort(key=lambda x: x["risk_score"], reverse=True)
    return alerts
