"""
使用者管理 API 路由（僅管理員可操作）
GET    /users          - 使用者列表
POST   /users          - 建立使用者
GET    /users/:id      - 使用者詳情
PUT    /users/:id      - 更新使用者
DELETE /users/:id      - 停用使用者
"""
from uuid import UUID
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from models.user import User
from schemas.user import UserCreate, UserUpdate, UserOut
from utils.dependencies import require_admin
from utils.security import hash_password

router = APIRouter(prefix="/users", tags=["使用者管理"])


@router.get("", response_model=List[UserOut])
def list_users(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    """取得使用者列表"""
    users = db.query(User).offset(skip).limit(limit).all()
    return users


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    """建立新使用者"""
    # 檢查 Email 是否已存在
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="此 Email 已被使用")

    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        full_name=payload.full_name,
        role_id=payload.role_id,
        preferred_language=payload.preferred_language,
        note=payload.note,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.get("/{user_id}", response_model=UserOut)
def get_user(
    user_id: UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    """取得使用者詳情"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="使用者不存在")
    return user


@router.put("/{user_id}", response_model=UserOut)
def update_user(
    user_id: UUID,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    """更新使用者資料"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="使用者不存在")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)

    db.commit()
    db.refresh(user)
    return user


@router.delete("/{user_id}")
def deactivate_user(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """停用使用者（不實際刪除）"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="使用者不存在")
    if user.id == current_user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="無法停用自己的帳號")

    user.is_active = False
    db.commit()
    return {"message": "使用者已停用"}
