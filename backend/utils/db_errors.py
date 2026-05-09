"""
SQLAlchemy / PostgreSQL 錯誤碼映射

將底層資料庫例外轉換為對前端友善的 HTTP 回應，
避免洩漏 SQL 細節，同時提供可操作的錯誤訊息。

PostgreSQL Error Codes 參考：
  https://www.postgresql.org/docs/current/errcodes-appendix.html

使用方式（在 router 中）：
    from utils.db_errors import handle_db_error

    try:
        db.commit()
    except Exception as exc:
        raise handle_db_error(exc)
"""
import logging
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError, OperationalError, DataError, ProgrammingError

logger = logging.getLogger(__name__)

# PostgreSQL 錯誤代碼 → (HTTP 狀態碼, 使用者訊息)
_PG_CODE_MAP: dict[str, tuple[int, str]] = {
    # Integrity errors
    "23000": (409, "資料完整性違反"),
    "23001": (409, "限制條件違反"),
    "23502": (422, "必填欄位不得為空"),
    "23503": (409, "關聯資料不存在，無法操作"),
    "23505": (409, "資料已存在，請勿重複建立"),
    "23514": (422, "欄位值不符合規則限制"),
    # Data errors
    "22001": (422, "欄位內容超過長度限制"),
    "22003": (422, "數值超出允許範圍"),
    "22007": (422, "日期格式錯誤"),
    "22008": (422, "時間格式錯誤"),
    "22012": (422, "除以零錯誤"),
    "22P02": (422, "無效的輸入格式"),
    # Operational
    "40001": (503, "資料庫交易衝突，請稍後重試"),
    "40P01": (503, "發生死鎖，請稍後重試"),
    "53300": (503, "資料庫連線數已滿，請稍後重試"),
    "57014": (504, "查詢超時，請稍後重試"),
}


def _extract_pg_code(exc: Exception) -> Optional[str]:
    """從 SQLAlchemy 例外中提取 PostgreSQL 錯誤碼。"""
    orig = getattr(exc, "orig", None)
    if orig is None:
        return None
    # psycopg2: orig.pgcode
    pgcode = getattr(orig, "pgcode", None)
    if pgcode:
        return str(pgcode)
    # 備用：從 pgerror 字串解析
    pgerror = getattr(orig, "pgerror", "") or ""
    if pgerror and len(pgerror) >= 5:
        return pgerror[:5]
    return None


def handle_db_error(exc: Exception, *, context: str = "") -> HTTPException:
    """
    將 SQLAlchemy 例外轉換為 HTTPException。

    Args:
        exc:     SQLAlchemy 或其他例外
        context: 操作描述（如 '建立銷售單'），用於日誌

    Returns:
        HTTPException（供 raise 使用）
    """
    prefix = f"[{context}] " if context else ""

    if isinstance(exc, IntegrityError):
        pg_code = _extract_pg_code(exc)
        if pg_code and pg_code in _PG_CODE_MAP:
            http_status, user_msg = _PG_CODE_MAP[pg_code]
            logger.warning("%sIntegrityError pgcode=%s msg=%s", prefix, pg_code, str(exc.orig)[:200])
            return HTTPException(status_code=http_status, detail=user_msg)
        # 未知 IntegrityError
        logger.warning("%sIntegrityError（未知 pgcode）: %s", prefix, str(exc)[:200])
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail="資料衝突，請確認後重試")

    if isinstance(exc, DataError):
        pg_code = _extract_pg_code(exc)
        if pg_code and pg_code in _PG_CODE_MAP:
            http_status, user_msg = _PG_CODE_MAP[pg_code]
            logger.warning("%sDataError pgcode=%s", prefix, pg_code)
            return HTTPException(status_code=http_status, detail=user_msg)
        logger.warning("%sDataError: %s", prefix, str(exc)[:200])
        return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="資料格式錯誤")

    if isinstance(exc, OperationalError):
        pg_code = _extract_pg_code(exc)
        if pg_code and pg_code in _PG_CODE_MAP:
            http_status, user_msg = _PG_CODE_MAP[pg_code]
            logger.error("%sOperationalError pgcode=%s", prefix, pg_code)
            return HTTPException(status_code=http_status, detail=user_msg)
        logger.error("%sOperationalError: %s", prefix, str(exc)[:200])
        return HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="資料庫暫時無法連線，請稍後重試")

    if isinstance(exc, ProgrammingError):
        logger.error("%sProgrammingError（可能是 schema 問題）: %s", prefix, str(exc)[:200])
        return HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="伺服器發生錯誤")

    # 其他例外
    logger.error("%s未知例外 %s: %s", prefix, type(exc).__name__, str(exc)[:200])
    return HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="伺服器發生錯誤，請聯絡管理員")
