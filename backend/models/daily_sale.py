"""
每日市場銷售模型

DailySale      — 每日銷售主表（一天一個市場一筆）
DailySaleItem  — 銷售明細行（每筆明細對應一個批次/規格）
MarketPrice    — 每日市場行情紀錄
"""
import uuid
from datetime import datetime, date as date_type
from sqlalchemy import (
    Column, String, DateTime, Date, Text, ForeignKey,
    Numeric, Integer, CheckConstraint, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from database import Base


class DailySale(Base):
    """每日市場銷售主表

    每天每個市場/承銷人一筆記錄，
    下面掛多筆 DailySaleItem 明細。
    """
    __tablename__ = "daily_sales"
    __table_args__ = (
        UniqueConstraint("sale_date", "market_code", "customer_id",
                         name="uq_daily_sales_date_market_customer"),
    )

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sale_date       = Column(Date, nullable=False)                              # 銷售日期
    market_code     = Column(String(10), nullable=False)                        # 市場代碼（TPE_M1 北農一市, TPE_M2 二市, OTHER）
    customer_id     = Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=True)  # 承銷人/客戶
    consignee_name  = Column(String(100), nullable=True)                        # 承銷人名稱（快速輸入用）
    total_boxes     = Column(Integer, default=0)                                # 總箱數
    total_kg        = Column(Numeric(10, 2), default=0)                         # 總公斤數
    total_amount_twd = Column(Numeric(12, 2), default=0)                        # 總金額 TWD
    settlement_status = Column(String(15), default="unsettled", nullable=False) # unsettled/partial/settled
    notes           = Column(Text, nullable=True)
    created_by      = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at      = Column(DateTime, default=datetime.utcnow)
    updated_at      = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 關聯
    customer = relationship("Customer", foreign_keys=[customer_id])
    creator  = relationship("User", foreign_keys=[created_by])
    items    = relationship("DailySaleItem", back_populates="daily_sale", cascade="all, delete-orphan")


class DailySaleItem(Base):
    """每日銷售明細行

    每一行代表一個批次/規格的銷售量，
    自動從庫存 FIFO 扣減。
    """
    __tablename__ = "daily_sale_items"
    __table_args__ = (
        CheckConstraint("quantity_kg > 0", name="ck_daily_sale_items_kg_positive"),
    )

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    daily_sale_id   = Column(UUID(as_uuid=True), ForeignKey("daily_sales.id", ondelete="CASCADE"), nullable=False)
    batch_id        = Column(UUID(as_uuid=True), ForeignKey("batches.id"), nullable=False)
    lot_id          = Column(UUID(as_uuid=True), ForeignKey("inventory_lots.id"), nullable=True)  # 從哪個庫存批次扣
    size_grade      = Column(String(5), nullable=True)                          # S/M/L
    quantity_boxes  = Column(Integer, nullable=True)                            # 箱數
    quantity_kg     = Column(Numeric(10, 2), nullable=False)                    # 公斤數
    unit_price_twd  = Column(Numeric(10, 2), nullable=False)                   # 每公斤單價 TWD
    total_amount_twd = Column(Numeric(12, 2), nullable=False)                   # 小計 TWD
    cost_per_kg_twd = Column(Numeric(10, 4), nullable=True)                    # 凍結成本快照
    notes           = Column(Text, nullable=True)

    # 關聯
    daily_sale = relationship("DailySale", back_populates="items")
    batch      = relationship("Batch", foreign_keys=[batch_id])
    lot        = relationship("InventoryLot", foreign_keys=[lot_id])


class MarketPrice(Base):
    """每日市場行情

    記錄北農或其他市場的每日成交價格，
    用於分析和定價參考。
    """
    __tablename__ = "market_prices"
    __table_args__ = (
        UniqueConstraint("price_date", "market_code", "product_code", "size_grade",
                         name="uq_market_prices_date_market_product_grade"),
    )

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    price_date      = Column(Date, nullable=False)                              # 日期
    market_code     = Column(String(10), nullable=False)                        # 市場代碼
    product_code    = Column(String(20), nullable=False, default="baby_corn")   # 品項代碼
    size_grade      = Column(String(5), nullable=True)                          # 規格
    avg_price_twd   = Column(Numeric(10, 2), nullable=True)                    # 平均價（TWD/kg）
    high_price_twd  = Column(Numeric(10, 2), nullable=True)                    # 最高價
    low_price_twd   = Column(Numeric(10, 2), nullable=True)                    # 最低價
    volume_kg       = Column(Numeric(10, 2), nullable=True)                    # 成交量 kg
    source          = Column(String(20), default="manual")                      # manual/api/crawl
    notes           = Column(Text, nullable=True)
    recorded_by     = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at      = Column(DateTime, default=datetime.utcnow)

    # 關聯
    recorder = relationship("User", foreign_keys=[recorded_by])
