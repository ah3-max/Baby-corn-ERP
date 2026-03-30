"""
OEM 工廠管理 API
GET    /oem-factories          - 工廠列表
POST   /oem-factories          - 新增工廠
GET    /oem-factories/{id}     - 工廠詳情
PUT    /oem-factories/{id}     - 編輯工廠
"""
from uuid import UUID
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from models.user import User
from models.oem_factory import OEMFactory
from schemas.oem_factory import OEMFactoryCreate, OEMFactoryUpdate, OEMFactoryOut
from utils.dependencies import check_permission

router = APIRouter(prefix="/oem-factories", tags=["OEM工廠"])


@router.get("", response_model=List[OEMFactoryOut])
def list_oem_factories(
    db: Session = Depends(get_db),
    _:  User    = Depends(check_permission("oem_factory", "read")),
):
    """取得所有啟用中的 OEM 工廠"""
    return db.query(OEMFactory).filter(OEMFactory.is_active == True).order_by(OEMFactory.code).all()


@router.get("/{factory_id}", response_model=OEMFactoryOut)
def get_oem_factory(
    factory_id: UUID,
    db: Session = Depends(get_db),
    _:  User    = Depends(check_permission("oem_factory", "read")),
):
    factory = db.query(OEMFactory).filter(OEMFactory.id == factory_id).first()
    if not factory:
        raise HTTPException(status_code=404, detail="OEM 工廠不存在")
    return factory


@router.post("", response_model=OEMFactoryOut, status_code=status.HTTP_201_CREATED)
def create_oem_factory(
    payload: OEMFactoryCreate,
    db:      Session = Depends(get_db),
    _:       User    = Depends(check_permission("oem_factory", "create")),
):
    factory = OEMFactory(**payload.model_dump())
    db.add(factory)
    db.commit()
    db.refresh(factory)
    return factory


@router.put("/{factory_id}", response_model=OEMFactoryOut)
def update_oem_factory(
    factory_id: UUID,
    payload:    OEMFactoryUpdate,
    db:         Session = Depends(get_db),
    _:          User    = Depends(check_permission("oem_factory", "update")),
):
    factory = db.query(OEMFactory).filter(OEMFactory.id == factory_id).first()
    if not factory:
        raise HTTPException(status_code=404, detail="OEM 工廠不存在")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(factory, k, v)
    db.commit()
    db.refresh(factory)
    return factory
