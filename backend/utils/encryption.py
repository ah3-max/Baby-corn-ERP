"""
敏感欄位加解密工具（Fernet 對稱加密）

使用方式：
    在 SQLAlchemy Model 中以 EncryptedString 取代 String：
        national_id = Column(EncryptedString, nullable=True)

設定：
    .env 中設定 ENCRYPTION_KEY（Fernet 格式，44 字元 base64url）
    若 ENCRYPTION_KEY 為空，欄位以明文儲存（相容舊資料或開發環境）。
"""
from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy.types import TypeDecorator, Text

logger = logging.getLogger(__name__)

# 延遲初始化，避免 circular import（config 在 models 之後載入）
_fernet = None


def _get_fernet():
    global _fernet
    if _fernet is not None:
        return _fernet
    try:
        from config import settings
        if not settings.ENCRYPTION_KEY:
            return None
        from cryptography.fernet import Fernet
        _fernet = Fernet(settings.ENCRYPTION_KEY.encode())
    except Exception as exc:
        logger.warning("無法初始化 Fernet：%s，敏感欄位將以明文儲存", exc)
        return None
    return _fernet


def encrypt_value(plaintext: Optional[str]) -> Optional[str]:
    """將明文字串加密，若 ENCRYPTION_KEY 未設定則回傳原文。"""
    if plaintext is None:
        return None
    fernet = _get_fernet()
    if fernet is None:
        return plaintext
    return fernet.encrypt(plaintext.encode()).decode()


def decrypt_value(ciphertext: Optional[str]) -> Optional[str]:
    """將密文解密，若解密失敗（舊明文資料）則直接回傳原文。"""
    if ciphertext is None:
        return None
    fernet = _get_fernet()
    if fernet is None:
        return ciphertext
    try:
        return fernet.decrypt(ciphertext.encode()).decode()
    except Exception:
        # 舊有明文資料解密失敗 → 直接回傳，不拋例外
        return ciphertext


class EncryptedString(TypeDecorator):
    """SQLAlchemy 欄位類型：寫入時自動加密，讀取時自動解密。

    - 資料庫底層儲存為 TEXT（密文長度遠超 VARCHAR(20/200)）
    - 相容舊明文資料：解密失敗時回傳原文
    - ENCRYPTION_KEY 未設定時：透明傳遞（不加密）
    """
    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        """寫入 DB 前加密"""
        return encrypt_value(value)

    def process_result_value(self, value, dialect):
        """從 DB 讀出後解密"""
        return decrypt_value(value)
