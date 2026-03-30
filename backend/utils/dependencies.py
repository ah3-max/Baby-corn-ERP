"""
FastAPI 依賴注入函數
用於從 JWT Token 取得目前登入使用者
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from database import get_db
from models.user import User
from utils.security import decode_token

# Bearer Token 解析器
bearer_scheme = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """
    從 Authorization Header 解析 JWT，回傳目前登入使用者
    若 Token 無效或使用者不存在則拋出 401
    """
    token = credentials.credentials
    payload = decode_token(token)

    if payload is None or payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="無效的 Token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id: str = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="無效的 Token")

    user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="使用者不存在或已停用")

    return user


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """
    要求使用者為系統管理員
    用於使用者管理、角色管理等敏感操作
    """
    if not current_user.role or current_user.role.name != "系統管理員":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="此操作需要管理員權限",
        )
    return current_user


def check_permission(module: str, action: str):
    """
    動態產生權限檢查依賴
    用法：Depends(check_permission("supplier", "create"))
    """
    def _check(current_user: User = Depends(get_current_user)) -> User:
        if not current_user.role:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="無存取權限")

        # 系統管理員直接通過
        if current_user.role.is_system:
            return current_user

        # 檢查角色是否有對應權限
        has_permission = any(
            rp.permission.module == module and rp.permission.action == action
            for rp in current_user.role.role_permissions
        )
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"無 {module}:{action} 權限",
            )
        return current_user

    return _check
