"""
Request ID Middleware
- 每個 request 自動附加 X-Request-ID（若 header 沒帶則以 uuid4 生成）
- 將 request_id 綁定到 structlog contextvars，所有日誌自動帶入
- Response 帶回 X-Request-ID header，讓前端/Nginx 可關聯日誌
"""
import uuid
import time
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from utils.logger import get_logger, bind_contextvars, clear_contextvars

logger = get_logger("erp.access")


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        # 取用戶端帶來的 Request-ID 或自動生成
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())

        # 存入 request.state 供 route handler 取用
        request.state.request_id = request_id

        # 綁定到 structlog contextvars（此 request 的所有 log 自動帶入 request_id）
        clear_contextvars()
        bind_contextvars(request_id=request_id)

        start = time.monotonic()
        response: Response = await call_next(request)
        duration_ms = round((time.monotonic() - start) * 1000, 1)

        # 回傳 request_id 讓前端 / Nginx 可關聯
        response.headers["X-Request-ID"] = request_id

        # 結構化 access log（structlog JSON 格式）
        logger.info(
            "request",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            duration_ms=duration_ms,
        )

        clear_contextvars()
        return response
