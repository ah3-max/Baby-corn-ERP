"""
通知管理 API
GET    /notifications              - 我的通知列表
POST   /notifications              - 新增通知
GET    /notifications/{id}         - 通知詳情
POST   /notifications/{id}/read    - 標記已讀
POST   /notifications/read-all     - 全部標記已讀
"""
from uuid import UUID
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from database import get_db
from models.user import User
from models.notification import Notification
from schemas.notification import NotificationCreate, NotificationOut
from utils.dependencies import check_permission

router = APIRouter(prefix="/notifications", tags=["通知"])


@router.get("", response_model=List[NotificationOut])
def list_notifications(
    unread_only: bool = Query(False),
    db:          Session = Depends(get_db),
    current_user: User   = Depends(check_permission("notification", "read")),
):
    """取得目前使用者的通知"""
    q = db.query(Notification).filter(Notification.recipient_user_id == current_user.id)
    if unread_only:
        q = q.filter(Notification.is_read == False)
    return q.order_by(Notification.created_at.desc()).limit(100).all()


@router.get("/{notification_id}", response_model=NotificationOut)
def get_notification(
    notification_id: UUID,
    db:              Session = Depends(get_db),
    current_user:    User    = Depends(check_permission("notification", "read")),
):
    n = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.recipient_user_id == current_user.id,
    ).first()
    if not n:
        raise HTTPException(status_code=404, detail="通知不存在")
    return n


@router.post("", response_model=NotificationOut, status_code=status.HTTP_201_CREATED)
def create_notification(
    payload: NotificationCreate,
    db:      Session = Depends(get_db),
    _:       User    = Depends(check_permission("notification", "update")),
):
    """手動建立通知（管理員用）"""
    n = Notification(**payload.model_dump())
    db.add(n)
    db.commit()
    db.refresh(n)
    return n


@router.post("/{notification_id}/read", response_model=NotificationOut)
def mark_as_read(
    notification_id: UUID,
    db:              Session = Depends(get_db),
    current_user:    User    = Depends(check_permission("notification", "read")),
):
    n = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.recipient_user_id == current_user.id,
    ).first()
    if not n:
        raise HTTPException(status_code=404, detail="通知不存在")
    n.is_read = True
    n.read_at = datetime.utcnow()
    db.commit()
    db.refresh(n)
    return n


@router.post("/read-all", status_code=status.HTTP_204_NO_CONTENT)
def mark_all_as_read(
    db:           Session = Depends(get_db),
    current_user: User    = Depends(check_permission("notification", "read")),
):
    """將目前使用者所有未讀通知標記為已讀"""
    db.query(Notification).filter(
        Notification.recipient_user_id == current_user.id,
        Notification.is_read == False,
    ).update({"is_read": True, "read_at": datetime.utcnow()})
    db.commit()
