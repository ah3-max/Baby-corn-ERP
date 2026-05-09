"""
敏感欄位加解密工具（AES-256-GCM）

使用方式：
    在 SQLAlchemy Model 中以 EncryptedString 取代 String：
        national_id = Column(EncryptedString, nullable=True)

設定：
    .env 中設定 ENCRYPTION_KEY（64 字元 hex = 32 bytes）
    若 ENCRYPTION_KEY 為空，欄位以明文儲存（相容舊資料或開發環境）。

儲存格式：
    base64(iv):base64(tag):base64(ciphertext)

向下相容：
    - 若解密失敗（舊 Fernet 密文或明文），直接回傳原值不拋例外
    - 舊 Fernet 值以 'gAAAAA' 開頭，可偵測後嘗試 Fernet 解密
"""
from __future__ import annotations

import base64
import logging
import os
from typing import Optional

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from sqlalchemy.types import TypeDecorator, Text

logger = logging.getLogger(__name__)

# 延遲初始化，避免 circular import
_aes_key: Optional[bytes] = None
_key_loaded = False


def _get_key() -> Optional[bytes]:
    """取得 AES-256 金鑰（32 bytes），從 64 字元 hex 字串解碼。"""
    global _aes_key, _key_loaded
    if _key_loaded:
        return _aes_key
    _key_loaded = True
    try:
        from config import settings
        raw = getattr(settings, "ENCRYPTION_KEY", None) or ""
        if not raw:
            return None
        key_bytes = bytes.fromhex(raw.strip())
        if len(key_bytes) != 32:
            logger.warning("ENCRYPTION_KEY 長度錯誤（需 64 hex 字元 = 32 bytes），敏感欄位將以明文儲存")
            return None
        _aes_key = key_bytes
    except Exception as exc:
        logger.warning("無法初始化 AES-256-GCM 金鑰：%s，敏感欄位將以明文儲存", exc)
        return None
    return _aes_key


def encrypt_value(plaintext: Optional[str]) -> Optional[str]:
    """
    將明文字串以 AES-256-GCM 加密。

    回傳格式：base64(iv):base64(tag):base64(ciphertext)
    若 ENCRYPTION_KEY 未設定則回傳原文。
    """
    if plaintext is None:
        return None
    key = _get_key()
    if key is None:
        return plaintext
    try:
        iv = os.urandom(12)  # 96-bit nonce（GCM 標準）
        aesgcm = AESGCM(key)
        # AESGCM.encrypt 回傳 ciphertext + tag（最後 16 bytes）
        ct_with_tag = aesgcm.encrypt(iv, plaintext.encode("utf-8"), None)
        ciphertext = ct_with_tag[:-16]
        tag = ct_with_tag[-16:]
        return (
            base64.b64encode(iv).decode()
            + ":"
            + base64.b64encode(tag).decode()
            + ":"
            + base64.b64encode(ciphertext).decode()
        )
    except Exception as exc:
        logger.error("AES-256-GCM 加密失敗：%s", exc)
        return plaintext


def decrypt_value(ciphertext: Optional[str]) -> Optional[str]:
    """
    將密文解密。

    支援：
    1. 新格式（iv:tag:ciphertext）→ AES-256-GCM 解密
    2. 舊 Fernet 格式（gAAAAA 開頭）→ 嘗試 Fernet 解密，失敗回傳原文
    3. 明文 → 直接回傳

    若 ENCRYPTION_KEY 未設定則回傳原文。
    """
    if ciphertext is None:
        return None
    key = _get_key()
    if key is None:
        return ciphertext

    # 偵測新格式：iv:tag:ciphertext（含兩個冒號）
    parts = ciphertext.split(":")
    if len(parts) == 3:
        try:
            iv = base64.b64decode(parts[0])
            tag = base64.b64decode(parts[1])
            ct = base64.b64decode(parts[2])
            aesgcm = AESGCM(key)
            plaintext = aesgcm.decrypt(iv, ct + tag, None)
            return plaintext.decode("utf-8")
        except Exception:
            # 格式符合但解密失敗 → 回傳原值（防止意外資料炸掉）
            return ciphertext

    # 偵測舊 Fernet 格式（base64url 開頭為 'gAAAAA'）
    if ciphertext.startswith("gAAAAA"):
        try:
            from cryptography.fernet import Fernet
            from config import settings
            fernet = Fernet(settings.ENCRYPTION_KEY.encode())
            return fernet.decrypt(ciphertext.encode()).decode()
        except Exception:
            # Fernet 解密失敗（可能是不同金鑰或已是明文），直接回傳
            return ciphertext

    # 其他情況視為舊明文資料，直接回傳
    return ciphertext


class EncryptedString(TypeDecorator):
    """SQLAlchemy 欄位類型：寫入時自動加密，讀取時自動解密。

    - 資料庫底層儲存為 TEXT（密文長度遠超 VARCHAR）
    - 相容舊明文與 Fernet 資料：解密失敗時回傳原文
    - ENCRYPTION_KEY 未設定時：透明傳遞（不加密）
    - 加密格式：base64(iv):base64(tag):base64(ciphertext)
    """
    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        """寫入 DB 前加密"""
        return encrypt_value(value)

    def process_result_value(self, value, dialect):
        """從 DB 讀出後解密"""
        return decrypt_value(value)
