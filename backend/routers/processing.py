"""
加工管理 API
GET    /processing-orders          - 加工單列表
POST   /processing-orders          - 新增加工單
GET    /processing-orders/{id}     - 加工單詳情
PUT    /processing-orders/{id}     - 編輯加工單
"""
from uuid import UUID
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload

from database import get_db
from models.user import User
from models.processing import ProcessingOrder, ProcessingBatchLink
from schemas.processing import ProcessingOrderCreate, ProcessingOrderUpdate, ProcessingOrderOut
from utils.dependencies import check_permission

router = APIRouter(prefix="/processing-orders", tags=["加工管理"])


@router.get("", response_model=List[ProcessingOrderOut])
def list_processing_orders(
    status_filter: Optional[str] = Query(None, alias="status"),
    db: Session = Depends(get_db),
    _:  User    = Depends(check_permission("processing", "read")),
):
    q = db.query(ProcessingOrder).options(joinedload(ProcessingOrder.batch_links))
    if status_filter:
        q = q.filter(ProcessingOrder.status == status_filter)
    return q.order_by(ProcessingOrder.process_date.desc()).all()


@router.get("/{order_id}", response_model=ProcessingOrderOut)
def get_processing_order(
    order_id: UUID,
    db: Session = Depends(get_db),
    _:  User    = Depends(check_permission("processing", "read")),
):
    order = (
        db.query(ProcessingOrder)
        .options(joinedload(ProcessingOrder.batch_links))
        .filter(ProcessingOrder.id == order_id)
        .first()
    )
    if not order:
        raise HTTPException(status_code=404, detail="加工單不存在")
    return order


@router.post("", response_model=ProcessingOrderOut, status_code=status.HTTP_201_CREATED)
def create_processing_order(
    payload:      ProcessingOrderCreate,
    db:           Session = Depends(get_db),
    current_user: User    = Depends(check_permission("processing", "create")),
):
    data = payload.model_dump(exclude={"batch_links"})
    order = ProcessingOrder(**data, created_by=current_user.id)
    db.add(order)
    db.flush()

    # 建立批次關聯
    for link in payload.batch_links:
        db.add(ProcessingBatchLink(
            processing_order_id=order.id,
            batch_id=link.batch_id,
            direction=link.direction,
            weight_kg=link.weight_kg,
        ))

    db.commit()
    db.refresh(order)
    return (
        db.query(ProcessingOrder)
        .options(joinedload(ProcessingOrder.batch_links))
        .filter(ProcessingOrder.id == order.id)
        .first()
    )


@router.put("/{order_id}", response_model=ProcessingOrderOut)
def update_processing_order(
    order_id: UUID,
    payload:  ProcessingOrderUpdate,
    db:       Session = Depends(get_db),
    _:        User    = Depends(check_permission("processing", "update")),
):
    order = db.query(ProcessingOrder).filter(ProcessingOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="加工單不存在")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(order, k, v)
    db.commit()
    db.refresh(order)
    return (
        db.query(ProcessingOrder)
        .options(joinedload(ProcessingOrder.batch_links))
        .filter(ProcessingOrder.id == order.id)
        .first()
    )
