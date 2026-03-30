"""Initial baseline — 標記現有資料庫 schema 為 Alembic 起始點

此 migration 為「空白 baseline」，不執行任何 DDL。
目的是讓已存在的 PostgreSQL 資料庫（由 migrations.py 建立）
正式納入 Alembic 版本管理，後續所有 schema 變更改由 Alembic 管理。

執行方式（首次部署 Alembic 到已存在的 DB）：
    cd backend/
    alembic stamp b1a2c3d4e5f6   # 直接標記此版本為已執行，不跑 upgrade()

後續新增 migration：
    alembic revision --autogenerate -m "add column xxx"
    alembic upgrade head

Revision ID: b1a2c3d4e5f6
Revises:
Create Date: 2026-03-22 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "b1a2c3d4e5f6"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Baseline migration — 不執行任何 DDL。
    資料庫已由 migrations.py 的 run_migrations() 完整建立。

    若在「全新空白 DB」上執行（例如整合測試環境），
    所有資料表已在 main.py on_startup 透過 Base.metadata.create_all() 建立，
    此處同樣不需要額外 DDL。
    """
    pass


def downgrade() -> None:
    """
    Baseline 無法降版。
    若需要完全清除資料庫，請直接 DROP DATABASE 並重建。
    """
    raise NotImplementedError(
        "Baseline migration 不支援 downgrade。"
        "若需重置資料庫，請執行 DROP DATABASE 並重新初始化。"
    )
