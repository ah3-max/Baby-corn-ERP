"""
稽核日誌輔助函式 — Append-Only

設計原則：
- 稽核日誌寫入失敗「絕不」中斷業務流程
- 失敗時最多重試 2 次（使用新 Session），最終仍失敗則 logger.error 記錄
- 支援 IP（含 X-Forwarded-For / X-Real-IP）與 User-Agent 自動擷取
"""
import logging
from typing import Any, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from models.audit import AuditLog

logger = logging.getLogger(__name__)

_MAX_RETRY = 2


def write_audit_log(
    db: Session,
    action: str,
    *,
    user_id: Optional[UUID] = None,
    entity_type: Optional[str] = None,
    entity_id: Optional[UUID] = None,
    changes: Optional[Any] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> None:
    """將一筆稽核紀錄加入 Session（不 commit）。

    寫入失敗時以新 Session 重試最多 2 次；
    全部失敗則以 logger.error 記錄，不拋例外。

    Args:
        db:          SQLAlchemy Session（呼叫端的交易 Session）
        action:      操作類型：login / logout / create / update / delete /
                     status_change / password_change / export
        user_id:     操作使用者 ID（登入失敗時可為 None）
        entity_type: 實體類型，如 'batch', 'user', 'sales_order'
        entity_id:   實體 ID
        changes:     變更內容 dict，如 {'old_status': 'processing', 'new_status': 'qc_pending'}
        ip_address:  用戶端 IP（支援 IPv6）
        user_agent:  瀏覽器 User-Agent
    """
    log_kwargs = dict(
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        changes=changes,
        ip_address=ip_address,
        user_agent=user_agent,
    )

    # 第一次：直接加入呼叫端 Session（與業務流程同一 transaction）
    try:
        db.add(AuditLog(**log_kwargs))
        return
    except Exception as exc:
        logger.warning("稽核日誌寫入失敗（第 1 次，嘗試重試）：%s", exc)

    # 重試：使用獨立 Session，與主交易隔離
    for attempt in range(1, _MAX_RETRY + 1):
        try:
            from database import SessionLocal
            with SessionLocal() as retry_db:
                retry_db.add(AuditLog(**log_kwargs))
                retry_db.commit()
            return
        except Exception as exc:
            logger.warning("稽核日誌重試第 %d 次失敗：%s", attempt, exc)

    # 所有嘗試失敗 → error 層級記錄，保留關鍵資訊
    logger.error(
        "稽核日誌寫入徹底失敗，action=%s entity_type=%s entity_id=%s user_id=%s ip=%s",
        action, entity_type, entity_id, user_id, ip_address,
    )


def get_client_ip(request) -> Optional[str]:
    """從 FastAPI Request 取得真實 IP，依序嘗試：
    X-Forwarded-For → X-Real-IP → request.client.host
    """
    xff = request.headers.get("X-Forwarded-For")
    if xff:
        # X-Forwarded-For 可能含多個 IP，取最左邊（最原始來源）
        return xff.split(",")[0].strip()
    xri = request.headers.get("X-Real-IP")
    if xri:
        return xri.strip()
    if request.client:
        return request.client.host
    return None


def get_user_agent(request) -> Optional[str]:
    """從 FastAPI Request 取得 User-Agent，截斷至 500 字元。"""
    ua = request.headers.get("User-Agent", "")
    return ua[:500] if ua else None
