"""
結構化 JSON Logger（structlog）

設計原則：
- 正式環境輸出 JSON（方便 ELK / Loki / CloudWatch 解析）
- 開發環境輸出人類可讀的彩色格式
- 自動綁定 request_id（由 RequestIDMiddleware 注入 contextvars）

使用方式：
    from utils.logger import get_logger

    log = get_logger(__name__)
    log.info("銷售單建立", order_no="SO-20260330-001", customer_id=str(cid))
    log.error("加密失敗", exc_info=True)

初始化：
    在 main.py 啟動時呼叫 setup_logging()：
        from utils.logger import setup_logging
        setup_logging()
"""
import logging
import sys
from typing import Any

import structlog

# contextvars 綁定：用於自動帶入 request_id
from structlog.contextvars import merge_contextvars, bind_contextvars, clear_contextvars

__all__ = ["setup_logging", "get_logger", "bind_contextvars", "clear_contextvars"]


def setup_logging(json_logs: bool = True, log_level: str = "INFO") -> None:
    """
    初始化 structlog + stdlib logging。

    Args:
        json_logs:  True → JSON 格式（正式環境）；False → 彩色 console（開發）
        log_level:  最低記錄等級，預設 "INFO"
    """
    shared_processors: list[Any] = [
        merge_contextvars,                          # 自動綁定 contextvars（request_id 等）
        structlog.stdlib.add_logger_name,           # logger 名稱
        structlog.stdlib.add_log_level,             # 等級
        structlog.processors.TimeStamper(fmt="iso", utc=True),  # UTC ISO 時間戳
        structlog.processors.StackInfoRenderer(),
    ]

    if json_logs:
        # 正式環境：輸出 JSON
        structlog.configure(
            processors=shared_processors + [
                structlog.processors.dict_tracebacks,       # 例外轉 dict（JSON 友善）
                structlog.processors.JSONRenderer(),
            ],
            wrapper_class=structlog.make_filtering_bound_logger(
                getattr(logging, log_level.upper(), logging.INFO)
            ),
            context_class=dict,
            logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
            cache_logger_on_first_use=True,
        )
    else:
        # 開發環境：彩色可讀格式
        structlog.configure(
            processors=shared_processors + [
                structlog.dev.ConsoleRenderer(colors=True),
            ],
            wrapper_class=structlog.make_filtering_bound_logger(
                getattr(logging, log_level.upper(), logging.INFO)
            ),
            context_class=dict,
            logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
            cache_logger_on_first_use=True,
        )

    # 將 stdlib logging 也導向 structlog
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper(), logging.INFO),
    )
    # 靜音 SQLAlchemy engine 查詢（太吵）
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


def get_logger(name: str) -> structlog.BoundLogger:
    """取得 structlog logger，綁定模組名稱。"""
    return structlog.get_logger(name)
