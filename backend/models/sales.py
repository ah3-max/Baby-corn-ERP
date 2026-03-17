"""
銷售訂單模型
一個銷售訂單可包含多個批次的銷售品項。
SaleBatchAllocation 實現 FIFO 銷售配對，凍結成本與售價快照。
"""
import uuid
from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import Column, String, DateTime, Date, Text, ForeignKey, Numeric, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from database import Base

SALES_STATUSES = ["draft", "confirmed", "delivered", "invoiced", "closed"]


class SalesOrder(Base):
    """銷售訂單主表"""
    __tablename__ = "sales_orders"

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_no         = Column(String(30), unique=True, nullable=False)           # 銷售單號 SO-YYYYMMDD-XXX
    customer_id      = Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False)
    order_date       = Column(Date, nullable=False, default=date.today)
    delivery_date    = Column(Date, nullable=True)                              # 預計交貨日期
    total_amount_twd = Column(Numeric(14, 2), nullable=False, default=Decimal("0"))  # 總金額（TWD）
    status           = Column(String(20), nullable=False, default="draft")
    note             = Column(Text, nullable=True)
    created_by       = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at       = Column(DateTime, default=datetime.utcnow)
    updated_at       = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    customer = relationship("Customer", back_populates="sales_orders", foreign_keys=[customer_id])
    items    = relationship("SalesOrderItem", back_populates="sales_order", cascade="all, delete-orphan")
    payments = relationship("PaymentRecord", back_populates="sales_order")
    creator  = relationship("User", foreign_keys=[created_by])


class SalesOrderItem(Base):
    """銷售訂單品項（關聯批次）"""
    __tablename__ = "sales_order_items"

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sales_order_id   = Column(UUID(as_uuid=True), ForeignKey("sales_orders.id"), nullable=False)
    batch_id         = Column(UUID(as_uuid=True), ForeignKey("batches.id"), nullable=False)
    quantity_kg      = Column(Numeric(10, 2), nullable=False)                  # 數量（kg）
    unit_price_twd   = Column(Numeric(10, 2), nullable=False)                  # 單價（TWD/kg）
    total_amount_twd = Column(Numeric(12, 2), nullable=False)                  # 小計（TWD）
    note             = Column(Text, nullable=True)

    sales_order = relationship("SalesOrder", back_populates="items")
    batch       = relationship("Batch")
    allocations = relationship("SaleBatchAllocation", back_populates="sales_order_item",
                               cascade="all, delete-orphan")


class SaleBatchAllocation(Base):
    """銷售批次 FIFO 配對

    將銷售品項拆分到具體批次，凍結當時的成本與售價快照，
    用於計算每批次的實際利潤。
    """
    __tablename__ = "sale_batch_allocations"
    __table_args__ = (
        CheckConstraint("allocated_kg > 0", name="ck_sale_batch_alloc_kg_positive"),
    )

    id                     = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sales_order_item_id    = Column(UUID(as_uuid=True), ForeignKey("sales_order_items.id"), nullable=False)
    batch_id               = Column(UUID(as_uuid=True), ForeignKey("batches.id"), nullable=False)
    stock_position_id      = Column(UUID(as_uuid=True), ForeignKey("inventory_lots.id"), nullable=True)
    allocated_kg           = Column(Numeric(10, 3), nullable=False)                     # 配對重量
    cost_per_kg_twd        = Column(Numeric(10, 4), default=0)                          # 凍結成本快照
    sale_price_per_kg_twd  = Column(Numeric(10, 4), default=0)                          # 凍結售價快照
    allocated_revenue_twd  = Column(Numeric(12, 2), nullable=True)                      # = kg × 售價
    allocated_cost_twd     = Column(Numeric(12, 2), nullable=True)                      # = kg × 成本
    allocated_profit_twd   = Column(Numeric(12, 2), nullable=True)                      # = revenue - cost
    created_at             = Column(DateTime, default=datetime.utcnow)

    # 關聯
    sales_order_item = relationship("SalesOrderItem", back_populates="allocations")
    batch            = relationship("Batch", foreign_keys=[batch_id])
    stock_position   = relationship("InventoryLot", foreign_keys=[stock_position_id])
