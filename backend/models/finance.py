"""
WP5：財務模型

1. AccountReceivable — 應收帳款（客戶欠款）
2. AccountPayable    — 應付帳款（供應商/工廠欠款）
"""
import uuid
from datetime import datetime, date
from sqlalchemy import (
    Column, String, DateTime, Date, Text, ForeignKey,
    Numeric, Boolean, Integer,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from database import Base


# ── 1. 應收帳款 ──────────────────────────────────────────

AR_STATUSES = ["pending", "partial", "overdue", "settled", "bad_debt"]
AR_PAYMENT_TERMS = ["COD", "NET7", "NET15", "NET30", "NET60"]


class AccountReceivable(Base):
    """應收帳款 — 客戶欠款追蹤

    觸發來源：
    - SalesOrder → delivered 時自動建立
    - DailySale 建立時自動建立
    - 手動建立
    """
    __tablename__ = "account_receivables"

    id                   = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ar_no                = Column(String(30), unique=True, nullable=False)  # AR-YYYYMMDD-XXX
    customer_id          = Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False)
    source_type          = Column(String(20), nullable=False)  # sales_order / daily_sale / manual
    source_id            = Column(UUID(as_uuid=True), nullable=True)  # 關聯 SO 或 DS 的 ID
    original_amount_twd  = Column(Numeric(14, 2), nullable=False)
    paid_amount_twd      = Column(Numeric(14, 2), default=0, nullable=False)
    outstanding_amount_twd = Column(Numeric(14, 2), nullable=False)  # = original - paid
    due_date             = Column(Date, nullable=True)
    payment_terms        = Column(String(10), nullable=True)  # COD / NET7 / NET15 / NET30 / NET60
    status               = Column(String(10), nullable=False, default="pending")  # pending / partial / overdue / settled / bad_debt
    last_payment_date    = Column(Date, nullable=True)
    note                 = Column(Text, nullable=True)
    created_by           = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at           = Column(DateTime, default=datetime.utcnow)
    updated_at           = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 關聯
    customer = relationship("Customer", foreign_keys=[customer_id])
    creator  = relationship("User", foreign_keys=[created_by])


# ── 2. 應付帳款 ──────────────────────────────────────────

AP_STATUSES = ["pending", "partial", "overdue", "settled"]


class AccountPayable(Base):
    """應付帳款 — 供應商/工廠欠款追蹤

    觸發來源：
    - PurchaseOrder 到廠時自動建立
    - ProcessingOrder 完成時自動建立
    - Shipment 建立時自動建立（運費）
    - 手動建立
    """
    __tablename__ = "account_payables"

    id                   = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ap_no                = Column(String(30), unique=True, nullable=False)  # AP-YYYYMMDD-XXX
    supplier_id          = Column(UUID(as_uuid=True), ForeignKey("suppliers.id"), nullable=False)
    source_type          = Column(String(20), nullable=False)  # purchase_order / processing_order / shipment / manual
    source_id            = Column(UUID(as_uuid=True), nullable=True)
    original_amount_thb  = Column(Numeric(14, 2), nullable=True)
    original_amount_twd  = Column(Numeric(14, 2), nullable=True)
    paid_amount_thb      = Column(Numeric(14, 2), default=0)
    paid_amount_twd      = Column(Numeric(14, 2), default=0)
    outstanding_amount_thb = Column(Numeric(14, 2), nullable=True)
    outstanding_amount_twd = Column(Numeric(14, 2), nullable=True)
    due_date             = Column(Date, nullable=True)
    payment_terms        = Column(String(20), nullable=True)
    status               = Column(String(10), nullable=False, default="pending")
    last_payment_date    = Column(Date, nullable=True)
    note                 = Column(Text, nullable=True)
    created_by           = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at           = Column(DateTime, default=datetime.utcnow)
    updated_at           = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 關聯
    supplier = relationship("Supplier", foreign_keys=[supplier_id])
    creator  = relationship("User", foreign_keys=[created_by])
