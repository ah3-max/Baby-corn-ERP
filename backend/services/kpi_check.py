"""
KPI 里程碑自動連動服務

成交後自動觸發，計算業務本月達成率並在 50/80/100% 時發送通知。

使用方式：
    # 在銷售訂單確認後呼叫
    from services.kpi_check import check_kpi_milestone

    await check_kpi_milestone(db, user_id=order.created_by)
"""
import logging
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def _get_or_create_target(db: Session, user_id: UUID, target_month: date):
    """取得或建立本月 KPI 目標記錄（無目標時建立空白記錄）"""
    from models.crm import SalesTarget

    target = (
        db.query(SalesTarget)
        .filter(
            SalesTarget.user_id == user_id,
            SalesTarget.target_month == target_month,
        )
        .first()
    )
    if not target:
        target = SalesTarget(
            user_id=user_id,
            target_month=target_month,
        )
        db.add(target)
        db.flush()
    return target


def recalc_sales_actual(db: Session, user_id: UUID, target_month: date) -> dict:
    """重新計算業務本月實績（訂單數、金額）"""
    from models.sales import SalesOrder
    from sqlalchemy import func, and_

    # 本月第一天 ~ 最後一天
    first_day = target_month.replace(day=1)
    if target_month.month == 12:
        last_day = target_month.replace(year=target_month.year + 1, month=1, day=1)
    else:
        last_day = target_month.replace(month=target_month.month + 1, day=1)

    result = (
        db.query(
            func.count(SalesOrder.id).label("order_count"),
            func.sum(SalesOrder.total_amount_twd).label("revenue"),
        )
        .filter(
            SalesOrder.created_by == user_id,
            SalesOrder.status.notin_(["draft", "cancelled"]),
            SalesOrder.order_date >= first_day,
            SalesOrder.order_date < last_day,
        )
        .first()
    )

    return {
        "order_actual": result.order_count or 0,
        "revenue_actual": float(result.revenue or 0),
    }


def check_kpi_milestone(db: Session, user_id: UUID | None) -> None:
    """
    成交後觸發 KPI 里程碑檢查。
    達到 50/80/100% 時發送通知（每個里程碑僅發一次）。

    Args:
        db:      SQLAlchemy Session
        user_id: 業務人員 user_id（None 時跳過）
    """
    if user_id is None:
        return

    today = date.today()
    target_month = today.replace(day=1)

    try:
        target = _get_or_create_target(db, user_id, target_month)

        # 更新實績
        actual = recalc_sales_actual(db, user_id, target_month)
        target.order_actual = actual["order_actual"]
        target.revenue_actual = Decimal(str(actual["revenue_actual"]))

        # 計算達成率（以營收為主）
        if target.revenue_target and float(target.revenue_target) > 0:
            rate = float(target.revenue_actual) / float(target.revenue_target) * 100
        else:
            rate = 0.0

        target.achievement_rate = round(rate, 2)

        # 里程碑通知
        _check_and_notify_milestone(db, target, user_id, rate)

        db.flush()

    except Exception as exc:
        logger.warning("KPI 里程碑檢查失敗 user_id=%s: %s", user_id, exc)


def _check_and_notify_milestone(db: Session, target, user_id: UUID, rate: float) -> None:
    """檢查並發送里程碑通知（50/80/100%，各只發一次）"""
    from services.notification import notify

    milestones = [
        (100, "milestone_100_sent", "🎉 恭喜達成 100% 業績目標！"),
        (80,  "milestone_80_sent",  "💪 業績已達 80%，繼續加油！"),
        (50,  "milestone_50_sent",  "📈 業績已達 50%，保持節奏！"),
    ]

    for threshold, flag, title in milestones:
        if rate >= threshold and not getattr(target, flag, False):
            try:
                # 通知業務本人
                notify(
                    db,
                    [user_id],
                    title=title,
                    message={
                        "achievement_rate": round(rate, 1),
                        "revenue_actual": float(target.revenue_actual or 0),
                        "revenue_target": float(target.revenue_target or 0),
                        "month": target.target_month.isoformat(),
                    },
                    notification_type="kpi_milestone",
                    category="sales",
                    priority="high",
                )

                # 通知直屬主管
                from models.user import User
                user = db.query(User).filter(User.id == user_id).first()
                if user and user.reports_to_user_id:
                    notify(
                        db,
                        [user.reports_to_user_id],
                        title=f"🏆 {user.full_name} {title}",
                        message={
                            "sales_rep": user.full_name,
                            "achievement_rate": round(rate, 1),
                            "month": target.target_month.isoformat(),
                        },
                        notification_type="kpi_milestone",
                        category="sales",
                        priority="normal",
                    )

                setattr(target, flag, True)
            except Exception as exc:
                logger.warning("里程碑通知失敗 threshold=%d: %s", threshold, exc)
