"""
認證 API 路由
POST /auth/login     - 登入
POST /auth/refresh   - 換發 Token
POST /auth/logout    - 登出
GET  /auth/me        - 取得目前使用者資訊
PUT  /auth/me/password - 修改密碼
"""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from database import get_db
from models.user import User
from schemas.auth import LoginRequest, TokenResponse, RefreshRequest, ChangePasswordRequest
from schemas.user import UserMe
from services.auth import authenticate_user, create_tokens, refresh_access_token, revoke_refresh_token, get_user_permissions
from utils.dependencies import get_current_user
from utils.security import verify_password, hash_password
from utils.audit import write_audit_log
from utils.limiter import limiter, LOGIN_LIMIT

router = APIRouter(prefix="/auth", tags=["認證"])


@router.post("/login", response_model=TokenResponse)
@limiter.limit(LOGIN_LIMIT)
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)):
    """使用者登入，回傳 JWT Token"""
    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")

    user = authenticate_user(db, payload.email, payload.password)
    if not user:
        # 記錄登入失敗（user_id 為 None），單獨 commit 後再拋例外
        write_audit_log(db, "login_failed",
                        changes={"email": payload.email},
                        ip_address=ip, user_agent=ua)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="帳號或密碼錯誤",
        )
    # 記錄登入成功，與 RefreshToken 一起 commit
    write_audit_log(db, "login",
                    user_id=user.id,
                    entity_type="user", entity_id=user.id,
                    ip_address=ip, user_agent=ua)
    result = create_tokens(db, user)  # flush only
    db.commit()
    return result


@router.post("/refresh", response_model=TokenResponse)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)):
    """用 Refresh Token 換發新的 Access Token + Refresh Token（Token Rotation）"""
    result = refresh_access_token(db, payload.refresh_token)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh Token 無效或已過期",
        )
    return result


@router.post("/logout")
def logout(
    payload: RefreshRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """登出，撤銷 Refresh Token"""
    write_audit_log(db, "logout",
                    user_id=current_user.id,
                    entity_type="user", entity_id=current_user.id,
                    ip_address=request.client.host if request.client else None,
                    user_agent=request.headers.get("user-agent"))
    revoke_refresh_token(db, payload.refresh_token)  # flush only
    db.commit()  # AuditLog + RefreshToken 刪除 一起提交
    return {"message": "已成功登出"}


@router.get("/me", response_model=UserMe)
def get_me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """取得目前登入使用者資訊與權限列表"""
    permissions = get_user_permissions(current_user)
    return {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "preferred_language": current_user.preferred_language,
        "role": current_user.role,
        "permissions": permissions,
    }


@router.put("/me/password")
def change_password(
    payload: ChangePasswordRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """修改目前使用者的密碼"""
    if not verify_password(payload.old_password, current_user.password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="舊密碼不正確")

    current_user.password_hash = hash_password(payload.new_password)
    write_audit_log(db, "password_change",
                    user_id=current_user.id,
                    entity_type="user", entity_id=current_user.id,
                    ip_address=request.client.host if request.client else None,
                    user_agent=request.headers.get("user-agent"))
    db.commit()
    return {"message": "密碼已更新"}


@router.put("/me/language")
def update_language(
    language: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """更新使用者偏好語言"""
    if language not in ["zh-TW", "en", "th"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="不支援的語言代碼")
    current_user.preferred_language = language
    db.commit()
    return {"message": "語言設定已更新", "language": language}
