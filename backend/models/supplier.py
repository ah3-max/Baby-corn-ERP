"""
供應商資料庫模型
類型：農民 / 中盤商 / 工廠 / 物流商 / 報關行 / 包材供應商
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, Date, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from database import Base


class Supplier(Base):
    """供應商主表"""
    __tablename__ = "suppliers"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code            = Column(String(10), unique=True, nullable=True)  # 供應商代碼（如 F001, B001）nullable 漸進遷移
    name            = Column(String(100), nullable=False)             # 供應商名稱
    name_en         = Column(String(100), nullable=True)              # 英文名稱
    name_th         = Column(String(100), nullable=True)              # 泰文名稱
    supplier_type   = Column(String(20), nullable=False)              # farmer / broker / factory / logistics / customs / packaging
    contact_name    = Column(String(100), nullable=True)              # 聯絡人
    phone           = Column(String(30), nullable=True)               # 電話
    line_id         = Column(String(50), nullable=True)               # LINE ID
    national_id     = Column(String(20), nullable=True)               # 泰國身分證號碼
    region          = Column(String(100), nullable=True)              # 地區 / 省份
    province        = Column(String(50), nullable=True)               # 省份（細分）
    district        = Column(String(50), nullable=True)               # 區域
    address         = Column(Text, nullable=True)                     # 地址
    payment_terms   = Column(String(100), nullable=True)              # 付款條件
    bank_account    = Column(String(200), nullable=True)              # 銀行帳戶
    gap_cert_no     = Column(String(50), nullable=True)               # GAP 認證號碼
    gap_cert_expiry = Column(Date, nullable=True)                     # GAP 認證到期日
    note            = Column(Text, nullable=True)                     # 備註
    is_active       = Column(Boolean, default=True, nullable=False)   # 啟用狀態
    deleted_at      = Column(DateTime, nullable=True)                 # 軟刪除時間
    created_by      = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at      = Column(DateTime, default=datetime.utcnow)
    updated_at      = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 關聯
    creator = relationship("User", foreign_keys=[created_by])
