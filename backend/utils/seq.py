"""
序號產生輔助函式 — 防止並行競爭重複序號

策略：
  next_seq_no() 使用 PostgreSQL 的 Advisory Lock（pg_advisory_xact_lock）
  確保同一前綴在同一 transaction 內序號不重複，並支援跨日自動重置。

  序號格式範例：SO-20260330-001

  跨日邏輯：
    prefix 通常包含日期（如 'SO-20260330-'），
    每天的 prefix 不同，count(*) 自然從 0 開始，不需額外重置。
    此函式透過 LIKE 比對當日 prefix，確保每天從 001 開始。

  並行安全：
    使用 pg_advisory_xact_lock(hashtext(prefix)) 鎖住同一前綴，
    確保高並行下同一時間只有一個 transaction 產生該前綴的序號。
    鎖在 transaction 結束後自動釋放。

  Caller pattern（處理極少數競爭情境的 fallback）：

    from sqlalchemy.exc import IntegrityError
    for _ in range(5):
        order_no = next_seq_no(db, SalesOrder, SalesOrder.order_no, prefix)
        obj.order_no = order_no
        try:
            db.flush()
            break
        except IntegrityError:
            db.rollback()
    else:
        raise HTTPException(500, "序號產生失敗，請重試")
"""
from datetime import date
from sqlalchemy.orm import Session
from sqlalchemy import func, text


def next_seq_no(
    db: Session,
    model,
    no_field,
    prefix: str,
    *,
    pad: int = 3,
) -> str:
    """
    以 Advisory Lock + COUNT(*) LIKE prefix% + 1 方式產生下一個序號字串。

    跨日重置：prefix 含日期時（如 'SO-20260330-'），每天自動從 001 起算。

    Args:
        db:       SQLAlchemy Session
        model:    SQLAlchemy Model class
        no_field: 序號欄位（Column）
        prefix:   前綴，例如 'SO-20260330-'（建議含日期確保跨日重置）
        pad:      數字補零位數（預設 3 → 001）

    Returns:
        序號字串，例如 'SO-20260330-001'
    """
    # Advisory Lock：鎖定此前綴，防止並行重複序號
    # hashtext() 將 prefix 字串轉為 bigint，transaction 結束自動釋放鎖
    db.execute(text("SELECT pg_advisory_xact_lock(hashtext(:prefix))"), {"prefix": prefix})

    count = db.query(func.count(model.id)).filter(
        no_field.like(f"{prefix}%")
    ).scalar() or 0
    return f"{prefix}{str(count + 1).zfill(pad)}"


def make_daily_prefix(doc_type: str, today: date | None = None) -> str:
    """
    產生含當日日期的序號前綴。

    Args:
        doc_type: 單據類型縮寫，如 'SO'（銷售單）、'PO'（採購單）、'SH'（出貨單）
        today:    指定日期（測試用），None 時使用今日

    Returns:
        前綴字串，例如 'SO-20260330-'
    """
    d = today or date.today()
    return f"{doc_type}-{d.strftime('%Y%m%d')}-"
