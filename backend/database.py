"""
資料庫連線設定
使用 SQLAlchemy 同步連線，含連線池與 rollback 保護
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from config import settings

# 建立同步引擎，配置連線池避免高負載時耗盡連線
engine = create_engine(
    settings.DATABASE_URL,
    pool_size=10,           # 基本連線池大小
    max_overflow=20,        # 超出 pool_size 後最多可額外開啟的連線數
    pool_recycle=3600,      # 連線閒置 1 小時後自動回收，避免 DB 端主動斷線
    pool_timeout=30,        # 等待可用連線的超時秒數
    pool_pre_ping=True,     # 每次取出連線前先 ping，確保連線有效
)

# 建立 Session 工廠
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 所有 Model 的基底類別
Base = declarative_base()


def get_db():
    """
    FastAPI 依賴注入用的資料庫 Session 生成器。
    - 正常結束：由各 router 負責呼叫 db.commit()
    - 例外發生：自動 rollback，確保 partial write 不會殘留
    - 結束後：無論成功或失敗都關閉連線歸還連線池
    """
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
