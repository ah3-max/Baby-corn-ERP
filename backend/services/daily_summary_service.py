"""
WP8：每日摘要生成服務

由排程引擎每天呼叫，產生 DailySummarySnapshot 並推送通知。
"""
from datetime import date, datetime, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import func

from models.daily_summary import DailySummarySnapshot
from models.notification import Notification
from models.user import User, Role
from models.batch import Batch
from models.inventory import InventoryLot
from models.sales import SalesOrder
from models.daily_sale import DailySale
from models.payment import PaymentRecord
from models.finance import AccountReceivable, AccountPayable
from models.shipment import Shipment


def generate_daily_summary(db: Session) -> dict:
    """產生每日營運摘要"""
    today = date.today()

    # 避免重複產生
    existing = db.query(DailySummarySnapshot).filter(
        DailySummarySnapshot.summary_date == today
    ).first()
    if existing:
        return existing.data

    # ── 批次狀態 ──
    batch_counts = {}
    for status_val, count in db.query(Batch.status, func.count(Batch.id)).group_by(Batch.status).all():
        batch_counts[status_val] = count

    # ── 庫存 ──
    active_lots = db.query(InventoryLot).filter(
        InventoryLot.status.in_(["active", "low_stock"])
    ).all()
    total_weight = sum(float(l.current_weight_kg) for l in active_lots)
    total_boxes = sum((l.current_boxes or 0) for l in active_lots)
    age_ok = sum(1 for l in active_lots if (today - l.received_date).days <= 7)
    age_warning = sum(1 for l in active_lots if 7 < (today - l.received_date).days <= 14)
    age_alert = sum(1 for l in active_lots if (today - l.received_date).days > 14)

    # ── 今日銷售 ──
    so_today = db.query(
        func.coalesce(func.sum(SalesOrder.total_amount_twd), 0)
    ).filter(SalesOrder.order_date == today).scalar()
    ds_today = db.query(
        func.coalesce(func.sum(DailySale.total_amount_twd), 0)
    ).filter(DailySale.sale_date == today).scalar()
    so_count = db.query(func.count(SalesOrder.id)).filter(SalesOrder.order_date == today).scalar()
    ds_count = db.query(func.count(DailySale.id)).filter(DailySale.sale_date == today).scalar()

    # ── 出口中 ──
    pending_shipments = db.query(func.count(Shipment.id)).filter(
        Shipment.status.in_(["preparing", "customs_th", "in_transit", "customs_tw"])
    ).scalar()

    # ── AR 逾期 ──
    ar_overdue = db.query(
        func.coalesce(func.sum(AccountReceivable.outstanding_amount_twd), 0)
    ).filter(
        AccountReceivable.status.in_(["pending", "partial"]),
        AccountReceivable.due_date < today,
    ).scalar()

    # ── AP 本週到期 ──
    week_end = today + timedelta(days=7)
    ap_due_week = db.query(
        func.coalesce(func.sum(AccountPayable.outstanding_amount_thb), 0)
    ).filter(
        AccountPayable.status.in_(["pending", "partial"]),
        AccountPayable.due_date.between(today, week_end),
    ).scalar()

    # ── 鮮度告急（超過 20 天） ──
    freshness_alerts = []
    for lot in active_lots:
        age = (today - lot.received_date).days
        if age > 14:
            freshness_alerts.append({
                "lot_no": lot.lot_no,
                "age_days": age,
                "weight_kg": round(float(lot.current_weight_kg), 2),
            })

    # ── 下單建議 ──
    from routers.inventory_analytics import reorder_suggestion as _reorder
    # 簡化：只取關鍵欄位
    from models.inventory import InventoryTransaction
    out_30d = db.query(
        func.coalesce(func.sum(InventoryTransaction.weight_kg), 0)
    ).filter(
        InventoryTransaction.txn_type == "out",
        InventoryTransaction.created_at >= datetime.combine(today - timedelta(days=30), datetime.min.time()),
    ).scalar()
    avg_daily = float(out_30d) / 30
    days_of_stock = int(total_weight / avg_daily) if avg_daily > 0 else 999

    summary_data = {
        "date": str(today),
        "batches_by_status": batch_counts,
        "inventory": {
            "total_weight_kg": round(total_weight, 2),
            "total_boxes": total_boxes,
            "lot_count": len(active_lots),
            "age_ok": age_ok,
            "age_warning": age_warning,
            "age_alert": age_alert,
        },
        "sales_today": {
            "total_twd": float(so_today) + float(ds_today),
            "so_count": so_count,
            "ds_count": ds_count,
        },
        "pending_shipments": pending_shipments,
        "ar_overdue_twd": float(ar_overdue),
        "ap_due_this_week_thb": float(ap_due_week),
        "freshness_alerts": freshness_alerts[:5],
        "reorder": {
            "avg_daily_sales_kg": round(avg_daily, 2),
            "days_of_stock": days_of_stock,
            "should_reorder": days_of_stock <= 10,
        },
    }

    # 儲存快照
    snapshot = DailySummarySnapshot(
        summary_date=today,
        data=summary_data,
    )
    db.add(snapshot)

    # 推送通知給管理員
    admins = (
        db.query(User)
        .join(Role, User.role_id == Role.id)
        .filter(User.is_active == True, Role.is_system == True)
        .all()
    )
    sent_ids = []
    for admin in admins:
        db.add(Notification(
            recipient_user_id=admin.id,
            notification_type="stock_age_warning",
            title=f"每日營運摘要 {today}",
            message=summary_data,
        ))
        sent_ids.append(str(admin.id))
    snapshot.sent_to = sent_ids

    db.commit()
    return summary_data
