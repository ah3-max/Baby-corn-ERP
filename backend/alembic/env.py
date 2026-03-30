"""
Alembic 環境設定
- 從 config.settings 取得 DATABASE_URL（讀取 .env 環境變數）
- 載入所有 SQLAlchemy Model，讓 autogenerate 可比對完整 metadata
- 支援 online（連線資料庫）與 offline（產生 SQL 檔）兩種模式
"""
import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool, create_engine
from alembic import context

# ── 確保 backend/ 目錄在 sys.path 中（讓 import 找得到 config / models）──
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ── 載入 Alembic ini 設定（提供 logger 設定）──────────────────────────
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ── 載入 settings，取得真實 DATABASE_URL ──────────────────────────────
from config import settings  # noqa: E402

# 覆寫 ini 中的 placeholder URL
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# ── 載入所有 Model，讓 Base.metadata 包含完整 schema ────────────────
import models  # noqa: F401,E402  確保所有 ORM Model 已註冊到 Base.metadata

from database import Base  # noqa: E402

target_metadata = Base.metadata


# ── Offline 模式：輸出 SQL 腳本（不連線 DB）──────────────────────────
def run_migrations_offline() -> None:
    """在不連線資料庫的情況下，將 migration SQL 輸出到標準輸出。

    適用於：
    - 需要人工審核 SQL 後再執行
    - 只有 SQL client，沒有 Python 環境的部署情境
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        # 比較欄位預設值，避免誤判差異
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


# ── Online 模式：直接連線 DB 執行 migration ──────────────────────────
def run_migrations_online() -> None:
    """連線 PostgreSQL，執行待執行的 migration。

    使用 NullPool 避免 Alembic CLI 執行完後有殘留連線。
    """
    connectable = create_engine(
        settings.DATABASE_URL,
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_server_default=True,
            # 讓 autogenerate 能偵測欄位型別變更
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
