"""
供應商管理 API 路由
GET    /suppliers          - 列表（可篩選類型、關鍵字、啟用狀態）
POST   /suppliers          - 建立
GET    /suppliers/:id      - 詳情
PUT    /suppliers/:id      - 更新
DELETE /suppliers/:id      - 停用
"""
from uuid import UUID
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from database import get_db
from models.user import User
from models.supplier import Supplier
from schemas.supplier import SupplierCreate, SupplierUpdate, SupplierOut, SUPPLIER_TYPES
from utils.dependencies import get_current_user, check_permission

router = APIRouter(prefix="/suppliers", tags=["供應商管理"])


@router.get("", response_model=List[SupplierOut])
def list_suppliers(
    supplier_type: Optional[str] = Query(None, description="篩選類型"),
    keyword:       Optional[str] = Query(None, description="關鍵字搜尋（名稱/聯絡人）"),
    is_active:     Optional[bool] = Query(None, description="啟用狀態"),
    skip:          int = 0,
    limit:         int = 100,
    db:            Session = Depends(get_db),
    _:             User = Depends(check_permission("supplier", "view")),
):
    """取得供應商列表，支援類型、關鍵字、啟用狀態篩選"""
    q = db.query(Supplier)

    if supplier_type:
        q = q.filter(Supplier.supplier_type == supplier_type)
    if is_active is not None:
        q = q.filter(Supplier.is_active == is_active)
    if keyword:
        q = q.filter(
            Supplier.name.ilike(f"%{keyword}%") |
            Supplier.contact_name.ilike(f"%{keyword}%")
        )

    return q.order_by(Supplier.created_at.desc()).offset(skip).limit(limit).all()


@router.post("", response_model=SupplierOut, status_code=status.HTTP_201_CREATED)
def create_supplier(
    payload:      SupplierCreate,
    db:           Session = Depends(get_db),
    current_user: User = Depends(check_permission("supplier", "create")),
):
    """建立新供應商"""
    if payload.supplier_type not in SUPPLIER_TYPES:
        raise HTTPException(status_code=400, detail=f"不支援的供應商類型：{payload.supplier_type}")

    supplier = Supplier(**payload.model_dump(), created_by=current_user.id)
    db.add(supplier)
    db.commit()
    db.refresh(supplier)
    return supplier


@router.get("/{supplier_id}", response_model=SupplierOut)
def get_supplier(
    supplier_id: UUID,
    db:          Session = Depends(get_db),
    _:           User = Depends(check_permission("supplier", "view")),
):
    """取得供應商詳情"""
    supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="供應商不存在")
    return supplier


@router.put("/{supplier_id}", response_model=SupplierOut)
def update_supplier(
    supplier_id: UUID,
    payload:     SupplierUpdate,
    db:          Session = Depends(get_db),
    _:           User = Depends(check_permission("supplier", "edit")),
):
    """更新供應商資料"""
    supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="供應商不存在")

    if payload.supplier_type and payload.supplier_type not in SUPPLIER_TYPES:
        raise HTTPException(status_code=400, detail=f"不支援的供應商類型：{payload.supplier_type}")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(supplier, field, value)

    db.commit()
    db.refresh(supplier)
    return supplier


@router.delete("/{supplier_id}")
def deactivate_supplier(
    supplier_id: UUID,
    db:          Session = Depends(get_db),
    _:           User = Depends(check_permission("supplier", "delete")),
):
    """停用供應商（不實際刪除）"""
    supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="供應商不存在")

    supplier.is_active = False
    db.commit()
    return {"message": "供應商已停用"}
