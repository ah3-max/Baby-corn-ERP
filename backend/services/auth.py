"""
認證業務邏輯
"""
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session

from config import settings
from models.user import User, RefreshToken
from utils.security import verify_password, create_access_token, create_refresh_token, decode_token


def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
    """
    驗證使用者帳號密碼
    成功回傳 User，失敗回傳 None
    """
    user = db.query(User).filter(User.email == email, User.is_active == True).first()
    if not user:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


def create_tokens(db: Session, user: User) -> dict:
    """
    為使用者建立 Access Token + Refresh Token
    同時將 Refresh Token 存入資料庫。
    注意：只呼叫 flush() 不 commit()，由 caller 統一 commit，
    確保 AuditLog 與 RefreshToken 在同一個 transaction 中。
    """
    tv = user.token_version or 0
    access_token = create_access_token(data={"sub": str(user.id)}, token_version=tv)
    refresh_token = create_refresh_token(data={"sub": str(user.id)})

    # 儲存 Refresh Token
    expires_at = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    db_token = RefreshToken(
        user_id=user.id,
        token=refresh_token,
        expires_at=expires_at,
    )
    db.add(db_token)
    db.flush()  # 取得 ID 但不 commit，由 caller 統一提交

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


def refresh_access_token(db: Session, refresh_token: str) -> Optional[dict]:
    """
    用 Refresh Token 換發新的 Access Token + 新的 Refresh Token（Token Rotation）。

    Rotation 策略：
    - 廢止舊 Refresh Token（刪除）
    - 簽發全新的 Refresh Token（延長有效期）
    - 若舊 Token 不存在或已過期，回傳 None
    """
    payload = decode_token(refresh_token)
    if not payload or payload.get("type") != "refresh":
        return None

    # 確認 Token 存在於資料庫且未過期
    db_token = db.query(RefreshToken).filter(
        RefreshToken.token == refresh_token,
        RefreshToken.expires_at > datetime.utcnow(),
    ).first()

    if not db_token:
        return None

    user = db.query(User).filter(User.id == db_token.user_id, User.is_active == True).first()
    if not user:
        return None

    # Rotation：廢止舊 token
    db.delete(db_token)

    # 簽發新 Access Token + 新 Refresh Token（帶入最新 token_version）
    tv = user.token_version or 0
    new_access_token  = create_access_token(data={"sub": str(user.id)}, token_version=tv)
    new_refresh_token = create_refresh_token(data={"sub": str(user.id)})

    expires_at = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    db.add(RefreshToken(
        user_id=user.id,
        token=new_refresh_token,
        expires_at=expires_at,
    ))
    db.commit()

    return {
        "access_token":  new_access_token,
        "refresh_token": new_refresh_token,
        "token_type":    "bearer",
    }


def revoke_refresh_token(db: Session, refresh_token: str) -> bool:
    """
    撤銷單一 Refresh Token（登出）。
    只呼叫 flush()，由 caller 統一 commit。
    """
    db_token = db.query(RefreshToken).filter(RefreshToken.token == refresh_token).first()
    if db_token:
        db.delete(db_token)
        db.flush()
        return True
    return False


def revoke_all_tokens(db: Session, user: User) -> None:
    """
    撤銷所有 Refresh Token 並遞增 token_version。
    用於：登出所有裝置、修改密碼、重設密碼、強制踢出。

    token_version +1 後，所有現有的 Access Token 驗證時會因版本不符而失效，
    即使 Access Token 尚未到期也無法使用（15 分鐘內完全清場）。
    只呼叫 flush()，由 caller 統一 commit。
    """
    db.query(RefreshToken).filter(RefreshToken.user_id == user.id).delete(synchronize_session=False)
    user.token_version = (user.token_version or 0) + 1
    db.flush()


def get_user_permissions(user: User) -> list[str]:
    """
    取得使用者所有權限字串列表
    格式：["module:action", ...]  例如 ["supplier:view", "batch:create"]
    """
    if not user.role:
        return []
    return [
        f"{rp.permission.module}:{rp.permission.action}"
        for rp in user.role.role_permissions
    ]
