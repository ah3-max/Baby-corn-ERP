"""
品項管理 API
GET    /product-types          - 品項列表
POST   /product-types          - 新增品項
PUT    /product-types/:id      - 編輯品項
GET    /product-types/:id      - 品項詳情
"""
from uuid import UUID
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from database import get_db
from models.user import User
from models.product_type import ProductType
from utils.dependencies import check_permission

router = APIRouter(prefix="/product-types", tags=["品項管理"])


# ─── Schemas ────────────────────────────────────────

class ProductTypeCreate(BaseModel):
    code:             str
    batch_prefix:     str
    name_zh:          str
    name_en:          Optional[str] = None
    name_th:          Optional[str] = None
    quality_schema:   list = []       # QC 檢查欄位定義
    size_grades:      list = []       # 尺寸分級
    processing_steps: list = []       # 加工步驟
    storage_req:      dict = {}       # 儲藏條件
    shelf_life_days:  Optional[int] = None


class ProductTypeUpdate(BaseModel):
    code:             Optional[str] = None
    batch_prefix:     Optional[str] = None
    name_zh:          Optional[str] = None
    name_en:          Optional[str] = None
    name_th:          Optional[str] = None
    quality_schema:   Optional[list] = None
    size_grades:      Optional[list] = None
    processing_steps: Optional[list] = None
    storage_req:      Optional[dict] = None
    shelf_life_days:  Optional[int] = None
    is_active:        Optional[bool] = None


class ProductTypeOut(BaseModel):
    id:               str
    code:             str
    batch_prefix:     str
    name_zh:          str
    name_en:          Optional[str]
    name_th:          Optional[str]
    quality_schema:   list
    size_grades:      list
    processing_steps: list
    storage_req:      dict
    shelf_life_days:  Optional[int]
    is_active:        bool

    class Config:
        from_attributes = True


def _to_out(pt: ProductType) -> ProductTypeOut:
    """ORM → ProductTypeOut（UUID 轉 str）"""
    return ProductTypeOut(
        id=str(pt.id),
        code=pt.code,
        batch_prefix=pt.batch_prefix,
        name_zh=pt.name_zh,
        name_en=pt.name_en,
        name_th=pt.name_th,
        quality_schema=pt.quality_schema or [],
        size_grades=pt.size_grades or [],
        processing_steps=pt.processing_steps or [],
        storage_req=pt.storage_req or {},
        shelf_life_days=pt.shelf_life_days,
        is_active=pt.is_active,
    )


# ─── 路由 ────────────────────────────────────────────

@router.get("", response_model=List[ProductTypeOut])
def list_product_types(
    db: Session = Depends(get_db),
    _:  User    = Depends(check_permission("system", "read")),
):
    """取得所有品項"""
    rows = db.query(ProductType).filter(
        ProductType.is_active == True
    ).order_by(ProductType.name_zh).all()
    return [_to_out(pt) for pt in rows]


@router.get("/all", response_model=List[ProductTypeOut])
def list_all_product_types(
    db: Session = Depends(get_db),
    _:  User    = Depends(check_permission("system", "read")),
):
    """取得所有品項（含停用）"""
    rows = db.query(ProductType).order_by(ProductType.name_zh).all()
    return [_to_out(pt) for pt in rows]


@router.get("/{pt_id}", response_model=ProductTypeOut)
def get_product_type(
    pt_id: UUID,
    db:    Session = Depends(get_db),
    _:     User    = Depends(check_permission("system", "read")),
):
    """取得品項詳情"""
    pt = db.query(ProductType).filter(ProductType.id == pt_id).first()
    if not pt:
        raise HTTPException(status_code=404, detail="品項不存在")
    return _to_out(pt)


@router.post("", response_model=ProductTypeOut, status_code=201)
def create_product_type(
    payload: ProductTypeCreate,
    db:      Session = Depends(get_db),
    _:       User    = Depends(check_permission("system", "update")),
):
    """新增品項"""
    # 檢查 code 和 batch_prefix 唯一性
    if db.query(ProductType).filter(ProductType.code == payload.code).first():
        raise HTTPException(status_code=400, detail=f"品項代碼 '{payload.code}' 已存在")
    if db.query(ProductType).filter(ProductType.batch_prefix == payload.batch_prefix).first():
        raise HTTPException(status_code=400, detail=f"批次前綴 '{payload.batch_prefix}' 已存在")

    pt = ProductType(**payload.model_dump())
    db.add(pt)
    db.commit()
    db.refresh(pt)
    return _to_out(pt)


@router.put("/{pt_id}", response_model=ProductTypeOut)
def update_product_type(
    pt_id:   UUID,
    payload: ProductTypeUpdate,
    db:      Session = Depends(get_db),
    _:       User    = Depends(check_permission("system", "update")),
):
    """編輯品項"""
    pt = db.query(ProductType).filter(ProductType.id == pt_id).first()
    if not pt:
        raise HTTPException(status_code=404, detail="品項不存在")

    data = payload.model_dump(exclude_unset=True)

    # 唯一性檢查
    if "code" in data and data["code"] != pt.code:
        if db.query(ProductType).filter(ProductType.code == data["code"]).first():
            raise HTTPException(status_code=400, detail=f"品項代碼 '{data['code']}' 已存在")
    if "batch_prefix" in data and data["batch_prefix"] != pt.batch_prefix:
        if db.query(ProductType).filter(ProductType.batch_prefix == data["batch_prefix"]).first():
            raise HTTPException(status_code=400, detail=f"批次前綴 '{data['batch_prefix']}' 已存在")

    for k, v in data.items():
        setattr(pt, k, v)
    db.commit()
    db.refresh(pt)
    return _to_out(pt)
