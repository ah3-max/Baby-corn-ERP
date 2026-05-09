"""
WP8：排程引擎 — 使用 APScheduler

排程任務：
- 每天 08:00 — 日報表
- 每天 09:00 — 庫存告警
- 每天 17:00 — 應收帳款逾期檢查
- 每週一 08:00 — 週報

注意：由 main.py on_startup 啟動，on_shutdown 停止。
若 APScheduler 未安裝，排程功能會被跳過（不影響 API 運作）。
"""
import logging

logger = logging.getLogger(__name__)

_scheduler = None


def start_scheduler():
    """啟動排程引擎"""
    global _scheduler
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.cron import CronTrigger
    except ImportError:
        logger.warning("APScheduler 未安裝，排程功能跳過。執行 pip install apscheduler 安裝。")
        return

    _scheduler = BackgroundScheduler()

    # 每天 08:00 — 日報表
    _scheduler.add_job(
        _daily_summary_job,
        CronTrigger(hour=8, minute=0),
        id="daily_summary",
        name="每日營運摘要",
        replace_existing=True,
    )

    # 每天 17:00 — AR 逾期檢查
    _scheduler.add_job(
        _ar_overdue_job,
        CronTrigger(hour=17, minute=0),
        id="ar_overdue_check",
        name="應收帳款逾期檢查",
        replace_existing=True,
    )

    # 每天 02:00 — 客戶健康分 + 訂單預測重算
    _scheduler.add_job(
        _customer_health_job,
        CronTrigger(hour=2, minute=0),
        id="customer_health_recalc",
        name="客戶健康分 / 訂單預測重算",
        replace_existing=True,
    )

    # 每天 03:00 — 貿易文件到期提醒
    _scheduler.add_job(
        _trade_doc_expiry_job,
        CronTrigger(hour=3, minute=0),
        id="trade_doc_expiry_check",
        name="貿易文件到期提醒",
        replace_existing=True,
    )

    # 每天 06:00 — 合約到期提醒
    _scheduler.add_job(
        _contract_expiry_job,
        CronTrigger(hour=6, minute=0),
        id="contract_expiry_check",
        name="合約到期提醒",
        replace_existing=True,
    )

    _scheduler.start()
    logger.info("排程引擎已啟動")


def stop_scheduler():
    """停止排程引擎"""
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        logger.info("排程引擎已停止")


def _daily_summary_job():
    """每日摘要排程任務"""
    from database import SessionLocal
    db = SessionLocal()
    try:
        from services.daily_summary_service import generate_daily_summary
        generate_daily_summary(db)
        logger.info("每日摘要已自動生成")
    except Exception as e:
        logger.error(f"每日摘要生成失敗: {e}")
    finally:
        db.close()


def _customer_health_job():
    """每日客戶健康分 + 訂單預測重算"""
    from database import SessionLocal
    db = SessionLocal()
    try:
        from services.health_score import recalc_all_customers
        from services.order_prediction import update_customer_prediction
        from models.customer import Customer

        recalc_all_customers(db)

        customers = db.query(Customer).filter(
            Customer.is_active == True,
            Customer.deleted_at.is_(None),
        ).all()
        for c in customers:
            try:
                update_customer_prediction(db, c.id)
            except Exception:
                pass
        db.commit()
        logger.info("客戶健康分 / 訂單預測重算完成")
    except Exception as e:
        logger.error(f"客戶健康分重算失敗: {e}")
    finally:
        db.close()


def _trade_doc_expiry_job():
    """貿易文件到期提醒（30 天內）"""
    from datetime import date, timedelta
    from database import SessionLocal
    db = SessionLocal()
    try:
        from models.trade import TradeDocument
        from services.notification import notify_by_role

        threshold = date.today() + timedelta(days=30)
        docs = db.query(TradeDocument).filter(
            TradeDocument.deleted_at.is_(None),
            TradeDocument.expiry_date.isnot(None),
            TradeDocument.expiry_date >= date.today(),
            TradeDocument.expiry_date <= threshold,
        ).all()

        if docs:
            notify_by_role(
                db,
                roles=["admin", "ops_manager"],
                title=f"⚠️ 有 {len(docs)} 份貿易文件將於 30 天內到期",
                message={"count": len(docs), "date": date.today().isoformat()},
                notification_type="system_alert",
                category="trade",
                priority="high",
            )
            logger.info(f"貿易文件到期提醒：{len(docs)} 份")
    except Exception as e:
        logger.error(f"貿易文件到期提醒失敗: {e}")
    finally:
        db.close()


def _contract_expiry_job():
    """合約到期提醒（依各合約 reminder_days 設定）"""
    from datetime import date, timedelta
    from database import SessionLocal
    db = SessionLocal()
    try:
        from models.compliance import Contract
        from services.notification import notify_by_role

        today = date.today()
        # 取未終止 / 到期的合約
        contracts = db.query(Contract).filter(
            Contract.deleted_at.is_(None),
            Contract.status == "active",
            Contract.effective_to.isnot(None),
        ).all()

        expiring = []
        for c in contracts:
            days_left = (c.effective_to - today).days
            if 0 <= days_left <= (c.reminder_days or 30):
                expiring.append(c)

        if expiring:
            notify_by_role(
                db,
                roles=["admin", "finance"],
                title=f"📋 有 {len(expiring)} 份合約即將到期",
                message={"count": len(expiring), "date": today.isoformat()},
                notification_type="system_alert",
                category="finance",
                priority="normal",
            )
            logger.info(f"合約到期提醒：{len(expiring)} 份")
    except Exception as e:
        logger.error(f"合約到期提醒失敗: {e}")
    finally:
        db.close()


def _ar_overdue_job():
    """AR 逾期自動標記"""
    from datetime import date
    from database import SessionLocal
    from models.finance import AccountReceivable
    db = SessionLocal()
    try:
        today = date.today()
        overdue_ars = db.query(AccountReceivable).filter(
            AccountReceivable.status.in_(["pending", "partial"]),
            AccountReceivable.due_date < today,
        ).all()
        count = 0
        for ar in overdue_ars:
            if ar.status != "overdue":
                ar.status = "overdue"
                count += 1
        if count > 0:
            db.commit()
            logger.info(f"已標記 {count} 筆應收帳款為逾期")
    except Exception as e:
        logger.error(f"AR 逾期檢查失敗: {e}")
    finally:
        db.close()
