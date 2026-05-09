"""
Scope 集中管理 — 資料可視範圍控制

定義各角色的資料存取範圍，統一套用到 list API：
- FULL_ACCESS：可看所有資料（super_admin、admin、gm、finance、audit）
- TEAM_ACCESS：只看自己團隊的資料（sales_manager、th_manager）
- OWN_DATA：只看自己負責的資料（sales、cs）

使用方式：
    from utils.scope import apply_customer_scope

    @router.get("/customers")
    def list_customers(
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
    ):
        query = db.query(Customer)
        query = apply_customer_scope(query, current_user)
        return query.all()
"""
from typing import TypeVar
from sqlalchemy.orm import Session, Query

# 完整存取的角色代碼清單
_FULL_ACCESS_ROLES = frozenset({
    "admin", "super_admin", "gm", "finance", "audit",
    "system_admin",  # 向下相容舊代碼
})

# 團隊級存取（可見同一個 sales_team 下的資料）
_TEAM_ACCESS_ROLES = frozenset({
    "sales_manager", "th_manager", "tw_manager",
})

# 僅自己的資料
_OWN_DATA_ROLES = frozenset({
    "sales", "cs", "customer_service",
})


def _get_role_code(user) -> str:
    """安全取得 user.role.code，若無則回傳空字串"""
    if user.role and user.role.code:
        return user.role.code.lower()
    return ""


def apply_customer_scope(query: Query, user) -> Query:
    """
    套用客戶資料範圍過濾。

    - FULL_ACCESS：不過濾
    - TEAM_ACCESS：過濾 customer.sales_team_id == user 所在 team
    - OWN_DATA（預設）：過濾 customer.assigned_sales_user_id == user.id
    """
    from models.customer import Customer

    role_code = _get_role_code(user)

    if role_code in _FULL_ACCESS_ROLES or (user.role and user.role.is_system):
        return query

    if role_code in _TEAM_ACCESS_ROLES:
        # 找出此 manager 管理的所有 team_id
        from models.sales_team import SalesTeamMember
        team_ids = [
            m.team_id
            for m in user.role.users  # 走另一條路：直接取 sales team
        ] if hasattr(user, "sales_team_memberships") else []
        # 簡化：以 manager 本人帶出他管轄的 team
        if team_ids:
            return query.filter(Customer.sales_team_id.in_(team_ids))
        # fallback：看自己負責的客戶
        return query.filter(Customer.assigned_sales_user_id == user.id)

    # OWN_DATA（預設：未知角色也視為 own data，最嚴格）
    return query.filter(Customer.assigned_sales_user_id == user.id)


def apply_sales_order_scope(query: Query, user) -> Query:
    """
    套用銷售訂單範圍過濾。

    - FULL_ACCESS：不過濾
    - 其他：過濾 sales_order.created_by == user.id
    """
    from models.sales import SalesOrder

    role_code = _get_role_code(user)

    if role_code in _FULL_ACCESS_ROLES or (user.role and user.role.is_system):
        return query

    return query.filter(SalesOrder.created_by == user.id)


def apply_shipment_scope(query: Query, user) -> Query:
    """
    套用出口單範圍過濾。

    - FULL_ACCESS + TEAM_ACCESS：不過濾（物流可見全部）
    - OWN_DATA：過濾 shipment.created_by == user.id
    """
    from models.shipment import Shipment

    role_code = _get_role_code(user)

    if role_code in _FULL_ACCESS_ROLES | _TEAM_ACCESS_ROLES or (user.role and user.role.is_system):
        return query

    return query.filter(Shipment.created_by == user.id)


def apply_purchase_scope(query: Query, user) -> Query:
    """
    套用採購單範圍過濾。

    - FULL_ACCESS + TEAM_ACCESS（th_manager）：不過濾
    - 其他：過濾 purchase_order.created_by == user.id
    """
    from models.purchase import PurchaseOrder

    role_code = _get_role_code(user)

    if role_code in _FULL_ACCESS_ROLES | _TEAM_ACCESS_ROLES or (user.role and user.role.is_system):
        return query

    return query.filter(PurchaseOrder.created_by == user.id)
