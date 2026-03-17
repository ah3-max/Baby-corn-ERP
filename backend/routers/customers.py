"""
客戶管理 API
"""
from uuid import UUID
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from database import get_db
from models.user import User
from models.customer import Customer
from schemas.customer import CustomerCreate, CustomerUpdate, CustomerOut
from utils.dependencies import check_permission

router = APIRouter(prefix="/customers", tags=["客戶管理"])


@router.get("", response_model=List[CustomerOut])
def list_customers(
    keyword:   Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    db:        Session = Depends(get_db),
    _:         User = Depends(check_permission("customer", "view")),
):
    q = db.query(Customer)
    if keyword:
        q = q.filter(Customer.name.ilike(f"%{keyword}%"))
    if is_active is not None:
        q = q.filter(Customer.is_active == is_active)
    return q.order_by(Customer.name).all()


@router.post("", response_model=CustomerOut, status_code=status.HTTP_201_CREATED)
def create_customer(
    payload: CustomerCreate,
    db:      Session = Depends(get_db),
    _:       User = Depends(check_permission("customer", "create")),
):
    customer = Customer(**payload.model_dump())
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer


@router.get("/{customer_id}", response_model=CustomerOut)
def get_customer(
    customer_id: UUID,
    db:          Session = Depends(get_db),
    _:           User = Depends(check_permission("customer", "view")),
):
    c = db.query(Customer).filter(Customer.id == customer_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="客戶不存在")
    return c


@router.put("/{customer_id}", response_model=CustomerOut)
def update_customer(
    customer_id: UUID,
    payload:     CustomerUpdate,
    db:          Session = Depends(get_db),
    _:           User = Depends(check_permission("customer", "edit")),
):
    c = db.query(Customer).filter(Customer.id == customer_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="客戶不存在")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(c, field, value)
    db.commit()
    db.refresh(c)
    return c
