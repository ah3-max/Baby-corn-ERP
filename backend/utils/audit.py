"""
稽核日誌輔助函式 — Append-Only
呼叫端只需 add()，由呼叫端的交易統一 commit；
若寫入失敗則靜默忽略，不阻斷業務流程。
"""
from typing import Any, Optional
from uuid import UUID
from sqlalchemy.orm import Session

from models.audit import AuditLog


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

    Args:
        db:          SQLAlchemy Session
        action:      操作類型：login / logout / create / update / delete /
                     status_change / password_change / export
        user_id:     操作使用者 ID（登入失敗時可為 None）
        entity_type: 實體類型，如 'batch', 'user', 'sales_order'
        entity_id:   實體 ID
        changes:     變更內容 dict，如 {'old_status': 'processing', 'new_status': 'qc_pending'}
        ip_address:  用戶端 IP（支援 IPv6）
        user_agent:  瀏覽器 User-Agent
    """
    try:
        log = AuditLog(
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            changes=changes,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        db.add(log)
    except Exception:
        # 稽核日誌寫入失敗不應中斷業務流程
        pass
