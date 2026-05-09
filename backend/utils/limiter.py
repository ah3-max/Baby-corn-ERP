"""
Rate Limiter（slowapi）— 多層級限流

限流策略：
- 一般 API：60 次/分鐘（預設）
- 登入端點：10 次/15分鐘（防暴力破解）

IP 偵測優先序：
  X-Forwarded-For（最左側 IP）→ X-Real-IP → request.client.host

使用方式：
    from utils.limiter import limiter, DEFAULT_LIMIT, LOGIN_LIMIT

    # 一般 API（通常不需標注，由全域中介層控制）
    @limiter.limit(DEFAULT_LIMIT)
    async def some_api(request: Request): ...

    # 登入端點
    @limiter.limit(LOGIN_LIMIT)
    async def login(request: Request): ...
"""
from typing import Optional

from starlette.requests import Request
from slowapi import Limiter

# ─── 限流常數 ────────────────────────────────────────────
DEFAULT_LIMIT = "60/minute"    # 一般 API：60 次/分鐘
LOGIN_LIMIT = "10/15minutes"   # 登入端點：10 次/15 分鐘


def _get_real_ip(request: Request) -> str:
    """
    取得真實用戶端 IP，支援反向代理。

    優先序：
    1. X-Forwarded-For（取最左側，即最原始來源）
    2. X-Real-IP
    3. request.client.host（直連 IP）
    """
    xff: Optional[str] = request.headers.get("X-Forwarded-For")
    if xff:
        return xff.split(",")[0].strip()
    xri: Optional[str] = request.headers.get("X-Real-IP")
    if xri:
        return xri.strip()
    if request.client:
        return request.client.host
    return "unknown"


# 以真實 IP 為限流 key
limiter = Limiter(key_func=_get_real_ip, default_limits=[DEFAULT_LIMIT])
