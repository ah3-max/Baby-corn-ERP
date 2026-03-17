"""
系統設定 API
GET    /system-settings          - 所有設定
POST   /system-settings          - 新增設定
GET    /system-settings/{key}    - 取得單一設定
PUT    /system-settings/{key}    - 更新設定
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from models.user import User
from models.system import SystemSetting
from schemas.system_setting import SystemSettingCreate, SystemSettingUpdate, SystemSettingOut
from utils.dependencies import check_permission

router = APIRouter(prefix="/system-settings", tags=["系統設定"])


@router.get("", response_model=List[SystemSettingOut])
def list_settings(
    db: Session = Depends(get_db),
    _:  User    = Depends(check_permission("system", "read")),
):
    return db.query(SystemSetting).order_by(SystemSetting.key).all()


@router.get("/{key}", response_model=SystemSettingOut)
def get_setting(
    key: str,
    db:  Session = Depends(get_db),
    _:   User    = Depends(check_permission("system", "read")),
):
    s = db.query(SystemSetting).filter(SystemSetting.key == key).first()
    if not s:
        raise HTTPException(status_code=404, detail=f"設定 '{key}' 不存在")
    return s


@router.post("", response_model=SystemSettingOut, status_code=status.HTTP_201_CREATED)
def create_setting(
    payload:      SystemSettingCreate,
    db:           Session = Depends(get_db),
    current_user: User    = Depends(check_permission("system", "update")),
):
    existing = db.query(SystemSetting).filter(SystemSetting.key == payload.key).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"設定 '{payload.key}' 已存在")
    s = SystemSetting(**payload.model_dump(), updated_by=current_user.id)
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


@router.put("/{key}", response_model=SystemSettingOut)
def update_setting(
    key:          str,
    payload:      SystemSettingUpdate,
    db:           Session = Depends(get_db),
    current_user: User    = Depends(check_permission("system", "update")),
):
    s = db.query(SystemSetting).filter(SystemSetting.key == key).first()
    if not s:
        raise HTTPException(status_code=404, detail=f"設定 '{key}' 不存在")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(s, k, v)
    s.updated_by = current_user.id
    db.commit()
    db.refresh(s)
    return s
