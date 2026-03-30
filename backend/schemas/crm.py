"""
WP3：CRM Pydantic Schemas
"""
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List, Any
from pydantic import BaseModel


# ── SalesTeam ────────────────────────────────────────────

class SalesTeamCreate(BaseModel):
    team_code:       str
    team_name:       str
    region:          str  # thailand / taiwan
    manager_user_id: Optional[str] = None
    description:     Optional[str] = None

class SalesTeamUpdate(BaseModel):
    team_name:       Optional[str] = None
    manager_user_id: Optional[str] = None
    description:     Optional[str] = None
    is_active:       Optional[bool] = None

class SalesTeamMemberCreate(BaseModel):
    user_id:            str
    role:               str = "sales"  # manager / senior_sales / sales
    target_monthly_twd: Decimal = Decimal("0")

class SalesTeamMemberOut(BaseModel):
    id:                 str
    team_id:            str
    user_id:            str
    user_name:          Optional[str] = None
    role:               str
    target_monthly_twd: float
    joined_at:          datetime
    is_active:          bool
    class Config: from_attributes = True

class SalesTeamOut(BaseModel):
    id:              str
    team_code:       str
    team_name:       str
    region:          str
    manager_user_id: Optional[str]
    description:     Optional[str]
    is_active:       bool
    members:         List[SalesTeamMemberOut] = []
    created_at:      datetime
    class Config: from_attributes = True


# ── CRMActivity ──────────────────────────────────────────

class CRMActivityCreate(BaseModel):
    customer_id:        str
    activity_type:      str  # visit / call / email / meeting / sample / complaint
    activity_date:      Optional[datetime] = None
    duration_minutes:   Optional[int] = None
    summary:            Optional[str] = None
    detail:             Optional[str] = None
    follow_up_date:     Optional[date] = None
    follow_up_action:   Optional[str] = None
    result:             Optional[str] = None
    order_potential_twd: Optional[Decimal] = None

class CRMActivityUpdate(BaseModel):
    activity_type:      Optional[str] = None
    summary:            Optional[str] = None
    detail:             Optional[str] = None
    follow_up_date:     Optional[date] = None
    follow_up_action:   Optional[str] = None
    result:             Optional[str] = None
    order_potential_twd: Optional[Decimal] = None

class CRMActivityOut(BaseModel):
    id:                 str
    activity_no:        str
    customer_id:        str
    customer_name:      Optional[str] = None
    sales_user_id:      str
    sales_user_name:    Optional[str] = None
    activity_type:      str
    activity_date:      datetime
    duration_minutes:   Optional[int]
    summary:            Optional[str]
    detail:             Optional[str]
    follow_up_date:     Optional[date]
    follow_up_action:   Optional[str]
    result:             Optional[str]
    order_potential_twd: Optional[float]
    attachments:        Optional[Any]
    created_at:         datetime
    class Config: from_attributes = True


# ── CRMTask ──────────────────────────────────────────────

class CRMTaskCreate(BaseModel):
    assigned_to:  str
    customer_id:  Optional[str] = None
    task_type:    str = "other"
    title:        str
    description:  Optional[str] = None
    priority:     str = "normal"
    due_date:     Optional[date] = None

class CRMTaskUpdate(BaseModel):
    status:          Optional[str] = None
    priority:        Optional[str] = None
    due_date:        Optional[date] = None
    completion_note: Optional[str] = None

class CRMTaskOut(BaseModel):
    id:              str
    task_no:         str
    assigned_to:     str
    assignee_name:   Optional[str] = None
    assigned_by:     str
    assigner_name:   Optional[str] = None
    customer_id:     Optional[str]
    customer_name:   Optional[str] = None
    task_type:       str
    title:           str
    description:     Optional[str]
    priority:        str
    due_date:        Optional[date]
    status:          str
    completed_at:    Optional[datetime]
    completion_note: Optional[str]
    created_at:      datetime
    class Config: from_attributes = True
