"""
匯率歷史模型
記錄 THB→TWD 匯率，支援手動輸入或 API 抓取。
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Date, ForeignKey, Numeric, CheckConstraint, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from database import Base


class ExchangeRate(Base):
    """匯率歷史紀錄"""
    __tablename__ = "exchange_rates"
    __table_args__ = (
        UniqueConstraint(
            "from_currency", "to_currency", "effective_date",
            name="uq_exchange_rates_pair_date",
        ),
        CheckConstraint(
            "source IN ('manual','api')",
            name="ck_exchange_rates_source",
        ),
    )

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    from_currency   = Column(String(3), nullable=False, default="THB")      # 來源幣別
    to_currency     = Column(String(3), nullable=False, default="TWD")      # 目標幣別
    rate            = Column(Numeric(8, 4), nullable=False)                 # 匯率
    effective_date  = Column(Date, nullable=False)                          # 生效日期
    source          = Column(String(20), nullable=False, default="manual")  # manual/api
    recorded_by     = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at      = Column(DateTime, default=datetime.utcnow)

    # 關聯
    recorder = relationship("User", foreign_keys=[recorded_by])
