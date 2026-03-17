"""
資料庫連線設定
使用 SQLAlchemy 非同步連線
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from config import settings

# 建立同步引擎
engine = create_engine(settings.DATABASE_URL)

# 建立 Session 工廠
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 所有 Model 的基底類別
Base = declarative_base()


def get_db():
    """
    FastAPI 依賴注入用的資料庫 Session 生成器
    每個請求結束後自動關閉連線
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
