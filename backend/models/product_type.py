"""
品項類型模型
定義不同農產品的品質檢查欄位、規格分級、加工步驟與儲存要求。
未來擴展新品項時只需新增一筆 ProductType 記錄。
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Boolean, Integer
from sqlalchemy.dialects.postgresql import UUID, JSON

from database import Base


class ProductType(Base):
    """品項類型

    每種農產品（如 baby_corn）對應一筆記錄，
    批次透過 product_type_id FK 指向此表。
    """
    __tablename__ = "product_types"

    id                = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code              = Column(String(20), unique=True, nullable=False)    # 品項代碼，如 'baby_corn'
    batch_prefix      = Column(String(5), unique=True, nullable=False)     # 批號前綴，如 'BC'
    name_zh           = Column(String(50), nullable=False)                 # 繁體中文名稱
    name_en           = Column(String(50), nullable=True)                  # 英文名稱
    name_th           = Column(String(50), nullable=True)                  # 泰文名稱
    quality_schema    = Column(JSON, default=list)                         # 品質檢查欄位定義
    size_grades       = Column(JSON, default=list)                         # 規格分級，如 ['S','M','L','XL']
    processing_steps  = Column(JSON, default=list)                         # 加工步驟定義
    storage_req       = Column(JSON, default=dict)                         # 儲存要求，如 {"temp_min": 2, "temp_max": 5}
    shelf_life_days   = Column(Integer, nullable=True)                     # 預設保存天數
    is_active         = Column(Boolean, default=True, nullable=False)
    created_at        = Column(DateTime, default=datetime.utcnow)
    updated_at        = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
