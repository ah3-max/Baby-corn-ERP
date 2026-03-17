"""
角色與權限管理 API 路由（僅管理員可操作）
GET    /roles              - 角色列表
POST   /roles              - 建立角色
GET    /roles/:id          - 角色詳情
PUT    /roles/:id          - 更新角色（含權限）
DELETE /roles/:id          - 刪除角色
GET    /permissions        - 所有可用權限列表
"""
from uuid import UUID
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from models.user import User, Role, Permission, RolePermission
from schemas.user import RoleCreate, RoleUpdate, RoleOut, PermissionOut
from utils.dependencies import require_admin

router = APIRouter(tags=["角色管理"])


@router.get("/permissions", response_model=List[PermissionOut])
def list_permissions(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    """取得所有可用權限項目"""
    return db.query(Permission).all()


@router.get("/roles", response_model=List[RoleOut])
def list_roles(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    """取得所有角色列表"""
    return db.query(Role).all()


@router.post("/roles", response_model=RoleOut, status_code=status.HTTP_201_CREATED)
def create_role(
    payload: RoleCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    """建立新角色"""
    if db.query(Role).filter(Role.name == payload.name).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="角色名稱已存在")

    role = Role(name=payload.name, description=payload.description)
    db.add(role)
    db.flush()

    # 設定角色權限
    for perm_id in payload.permission_ids:
        perm = db.query(Permission).filter(Permission.id == perm_id).first()
        if perm:
            db.add(RolePermission(role_id=role.id, permission_id=perm.id))

    db.commit()
    db.refresh(role)
    return role


@router.get("/roles/{role_id}", response_model=RoleOut)
def get_role(
    role_id: UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    """取得角色詳情"""
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="角色不存在")
    return role


@router.put("/roles/{role_id}", response_model=RoleOut)
def update_role(
    role_id: UUID,
    payload: RoleUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    """更新角色資料與權限"""
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="角色不存在")

    if payload.name is not None:
        role.name = payload.name
    if payload.description is not None:
        role.description = payload.description

    # 更新權限：先清空再重設
    if payload.permission_ids is not None:
        db.query(RolePermission).filter(RolePermission.role_id == role_id).delete()
        for perm_id in payload.permission_ids:
            perm = db.query(Permission).filter(Permission.id == perm_id).first()
            if perm:
                db.add(RolePermission(role_id=role.id, permission_id=perm.id))

    db.commit()
    db.refresh(role)
    return role


@router.delete("/roles/{role_id}")
def delete_role(
    role_id: UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    """刪除角色（系統預設角色不可刪除）"""
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="角色不存在")
    if role.is_system:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="系統預設角色不可刪除")
    if role.users:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="此角色尚有使用者，無法刪除")

    db.delete(role)
    db.commit()
    return {"message": "角色已刪除"}
