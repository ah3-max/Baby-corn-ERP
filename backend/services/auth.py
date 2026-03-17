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
    同時將 Refresh Token 存入資料庫
    """
    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})

    # 儲存 Refresh Token
    expires_at = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    db_token = RefreshToken(
        user_id=user.id,
        token=refresh_token,
        expires_at=expires_at,
    )
    db.add(db_token)
    db.commit()

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


def refresh_access_token(db: Session, refresh_token: str) -> Optional[dict]:
    """
    用 Refresh Token 換發新的 Access Token
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

    new_access_token = create_access_token(data={"sub": str(user.id)})
    return {"access_token": new_access_token, "token_type": "bearer"}


def revoke_refresh_token(db: Session, refresh_token: str) -> bool:
    """
    撤銷 Refresh Token（登出）
    """
    db_token = db.query(RefreshToken).filter(RefreshToken.token == refresh_token).first()
    if db_token:
        db.delete(db_token)
        db.commit()
        return True
    return False


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
