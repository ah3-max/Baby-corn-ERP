"""
序號產生輔助函式 — 防止並行競爭重複序號

策略：
  generate_seq_no() 產生序號後，由 caller 嘗試 INSERT。
  若資料庫回傳 UniqueViolation（並行衝突），
  caller 可 catch IntegrityError，重新呼叫此函式即可取得更大的序號。

  更安全的 caller pattern（見各 router 的 _create_* 函式）：

    from sqlalchemy.exc import IntegrityError
    for _ in range(5):
        order_no = _generate_order_no(db)
        obj.order_no = order_no
        try:
            db.flush()
            break
        except IntegrityError:
            db.rollback()
    else:
        raise HTTPException(500, "序號產生失敗，請重試")
"""
from sqlalchemy.orm import Session
from sqlalchemy import func


def next_seq_no(
    db: Session,
    model,
    no_field,
    prefix: str,
    *,
    pad: int = 3,
) -> str:
    """
    以 COUNT(*) LIKE prefix% + 1 方式產生下一個序號字串。

    Args:
        db:       SQLAlchemy Session
        model:    SQLAlchemy Model class
        no_field: 序號欄位（Column）
        prefix:   前綴，例如 'SO-20260330-'
        pad:      數字補零位數（預設 3 → 001）

    Returns:
        序號字串，例如 'SO-20260330-001'
    """
    count = db.query(func.count(model.id)).filter(
        no_field.like(f"{prefix}%")
    ).scalar() or 0
    return f"{prefix}{str(count + 1).zfill(pad)}"
