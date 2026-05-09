"""
OEM 加工廠模型
管理合作的代工廠基本資料、證照與預設加工費用。
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Date, Text, Numeric, Boolean, Integer
from sqlalchemy.dialects.postgresql import UUID

from database import Base


class OEMFactory(Base):
    """OEM 加工廠

    每間代工廠一筆記錄，加工單透過 oem_factory_id FK 指向此表。
    """
    __tablename__ = "oem_factories"

    id                      = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code                    = Column(String(10), unique=True, nullable=False)   # 工廠代碼，如 'OEM01'
    name                    = Column(String(100), nullable=False)               # 工廠名稱
    name_en                 = Column(String(100), nullable=True)                # 英文名稱
    contact_name            = Column(String(50), nullable=True)                 # 聯絡人
    contact_phone           = Column(String(30), nullable=True)                 # 聯絡電話
    address                 = Column(Text, nullable=True)                       # 地址
    province                = Column(String(50), nullable=True)                 # 省份
    license_no              = Column(String(50), nullable=True)                 # 食品加工許可證
    gmp_cert_no             = Column(String(50), nullable=True)                 # GMP 認證號碼
    processing_fee_per_kg   = Column(Numeric(8, 2), nullable=True)             # 預設加工費 THB/kg
    notes                   = Column(Text, nullable=True)                       # 備註
    # ── B-05 認證欄位 ─────────────────────────────────────────────────
    country_code            = Column(String(2), default="TH", nullable=False)  # 工廠所在國家
    haccp_cert_no           = Column(String(50), nullable=True)                # HACCP 認證號碼
    haccp_cert_expiry       = Column(Date, nullable=True)                      # HACCP 認證到期日
    iso22000_cert_no        = Column(String(50), nullable=True)                # ISO22000 認證號碼
    capacity_per_day_kg     = Column(Numeric(10, 2), nullable=True)            # 日產能（kg）
    lead_time_days          = Column(Integer, nullable=True)                   # 生產前置時間（天）

    is_active               = Column(Boolean, default=True, nullable=False)
    deleted_at              = Column(DateTime, nullable=True)
    created_at              = Column(DateTime, default=datetime.utcnow)
    updated_at              = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
