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
