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

# 這些 role.code 被視為「有限範圍」，只能看自己負責的客戶
_SCOPED_ROLE_CODES = {"sales", "sales_rep", "account_manager", "業務員"}


def _is_scoped(user: User) -> bool:
    """True 表示此使用者應只看自己負責的資料（非管理員）"""
    if not user.role:
        return True  # 保守：無角色則限制
    if user.role.is_system:
        return False  # 系統管理員看全部
    code = (user.role.code or "").lower()
    return code in _SCOPED_ROLE_CODES


@router.get("", response_model=List[CustomerOut])
def list_customers(
    keyword:   Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    skip:      int = 0,
    limit:     int = Query(100, le=500),
    db:        Session = Depends(get_db),
    current_user: User = Depends(check_permission("customer", "view")),
):
    q = db.query(Customer)
    # 資料範圍控制：業務員只看自己負責的客戶
    if _is_scoped(current_user):
        q = q.filter(Customer.assigned_sales_user_id == current_user.id)
    if keyword:
        q = q.filter(Customer.name.ilike(f"%{keyword}%"))
    if is_active is not None:
        q = q.filter(Customer.is_active == is_active)
    return q.order_by(Customer.name).offset(skip).limit(limit).all()


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
