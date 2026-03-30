"""
Rate Limiter 共用實例（slowapi）
在 main.py 掛載到 app.state，在各 router 引用此實例。
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

# 以用戶端 IP 為限流 key
limiter = Limiter(key_func=get_remote_address)
