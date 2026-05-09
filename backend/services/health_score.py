"""
客戶健康分數計算服務

5 維度評分（總計 100 分）：
  1. 訂單新近度（Recency）  30 分  ← 距最後下單天數
  2. 逾期 AR（Overdue）     25 分  ← 有無逾期應收款
  3. 互動頻率（Engagement）  20 分  ← 距最後聯繫天數
  4. 客訴記錄（Complaints） 15 分  ← 近 90 天客訴次數
  5. 停供風險（Supply）      10 分  ← 主要供應商是否正常

健康等級：
  GREEN   80~100
  YELLOW  60~79
  ORANGE  40~59
  RED      0~39

APScheduler 每天 02:00 批次重算所有 active 客戶。

使用方式：
    from services.health_score import recalc_customer_health, recalc_all_customers

    # 單一客戶
    score, level = recalc_customer_health(db, customer_id)

    # 全量重算（APScheduler 排程用）
    recalc_all_customers(db)
"""
import logging
from datetime import datetime, date, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# ─── 分數維度權重 ─────────────────────────────────────────
_W_RECENCY     = 30  # 訂單新近度
_W_OVERDUE_AR  = 25  # 逾期 AR
_W_ENGAGEMENT  = 20  # 互動頻率
_W_COMPLAINTS  = 15  # 客訴
_W_SUPPLY      =  10  # 停供風險


def _score_recency(last_order_date: date | None) -> float:
    """訂單新近度：30 天內 100%，30-60 天 50%，>90 天 0%"""
    if last_order_date is None:
        return 0.0
    days = (date.today() - last_order_date).days
    if days <= 30:
        return 1.0
    elif days <= 60:
        return 0.5
    elif days <= 90:
        return 0.2
    return 0.0


def _score_overdue_ar(customer_id: UUID, db: Session) -> float:
    """逾期 AR：無逾期 100%，有逾期 0%"""
    try:
        from models.finance import AccountReceivable
        overdue = (
            db.query(AccountReceivable)
            .filter(
                AccountReceivable.customer_id == customer_id,
                AccountReceivable.due_date < date.today(),
                AccountReceivable.status.in_(["pending", "partial"]),
            )
            .first()
        )
        return 0.0 if overdue else 1.0
    except Exception:
        return 1.0  # 無法查詢時不扣分


def _score_engagement(last_contact_date: date | None) -> float:
    """互動頻率：14 天內 100%，14-30 天 50%，>60 天 0%"""
    if last_contact_date is None:
        return 0.3  # 未記錄時保守給 30%
    days = (date.today() - last_contact_date).days
    if days <= 14:
        return 1.0
    elif days <= 30:
        return 0.5
    elif days <= 60:
        return 0.2
    return 0.0


def _score_complaints(customer_id: UUID, db: Session) -> float:
    """客訴：近 90 天無客訴 100%，1 件 50%，≥2 件 0%"""
    try:
        from models.crm_activity import CRMActivity
        cutoff = datetime.utcnow() - timedelta(days=90)
        count = (
            db.query(CRMActivity)
            .filter(
                CRMActivity.customer_id == customer_id,
                CRMActivity.activity_type == "complaint",
                CRMActivity.created_at >= cutoff,
            )
            .count()
        )
        if count == 0:
            return 1.0
        elif count == 1:
            return 0.5
        return 0.0
    except Exception:
        return 1.0


def _score_supply(_customer_id: UUID, _db: Session) -> float:
    """停供風險：目前固定 100%（未來接 batch 庫存狀態）"""
    return 1.0


def calculate_health_score(
    customer_id: UUID,
    last_order_date: date | None,
    last_contact_date: date | None,
    db: Session,
) -> tuple[float, str]:
    """
    計算單一客戶的健康分數與等級。

    Returns:
        (score: float 0~100, level: str GREEN/YELLOW/ORANGE/RED)
    """
    r  = _score_recency(last_order_date) * _W_RECENCY
    ar = _score_overdue_ar(customer_id, db) * _W_OVERDUE_AR
    e  = _score_engagement(last_contact_date) * _W_ENGAGEMENT
    c  = _score_complaints(customer_id, db) * _W_COMPLAINTS
    s  = _score_supply(customer_id, db) * _W_SUPPLY

    score = r + ar + e + c + s  # 最大 100

    if score >= 80:
        level = "GREEN"
    elif score >= 60:
        level = "YELLOW"
    elif score >= 40:
        level = "ORANGE"
    else:
        level = "RED"

    return round(score, 1), level


def recalc_customer_health(db: Session, customer_id: UUID) -> tuple[float, str]:
    """重算單一客戶健康分數，並寫回 Customer model。"""
    from models.customer import Customer

    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        return 0.0, "RED"

    score, level = calculate_health_score(
        customer_id=customer_id,
        last_order_date=customer.last_order_date,
        last_contact_date=customer.last_contact_date,
        db=db,
    )

    customer.health_score = score
    customer.health_level = level
    customer.health_updated_at = datetime.utcnow()

    return score, level


def recalc_all_customers(db: Session) -> int:
    """
    全量重算所有 active 客戶的健康分數。
    由 APScheduler 每天 02:00 呼叫。

    Returns:
        更新筆數
    """
    from models.customer import Customer

    customers = (
        db.query(Customer)
        .filter(Customer.is_active == True, Customer.deleted_at.is_(None))
        .all()
    )

    count = 0
    for customer in customers:
        try:
            score, level = calculate_health_score(
                customer_id=customer.id,
                last_order_date=customer.last_order_date,
                last_contact_date=customer.last_contact_date,
                db=db,
            )
            customer.health_score = score
            customer.health_level = level
            customer.health_updated_at = datetime.utcnow()
            count += 1
        except Exception as exc:
            logger.warning("健康分數重算失敗 customer_id=%s: %s", customer.id, exc)

    try:
        db.commit()
        logger.info("客戶健康分數批次重算完成，共 %d 筆", count)
    except Exception as exc:
        db.rollback()
        logger.error("健康分數批次寫入失敗：%s", exc)

    return count
