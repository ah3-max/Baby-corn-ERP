"""
出口發票（Commercial Invoice）模型
每張出口單可對應一張或多張發票，用於台灣海關報關及會計做帳
"""
import uuid
from datetime import datetime, date
from sqlalchemy import Column, String, DateTime, Date, Text, ForeignKey, Numeric, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from database import Base


class Invoice(Base):
    """出口發票主表"""
    __tablename__ = "invoices"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    invoice_no      = Column(String(30), unique=True, nullable=False)   # 發票號碼 INV-YYYYMMDD-XXX
    shipment_id     = Column(UUID(as_uuid=True), ForeignKey("shipments.id"), nullable=False)  # 對應出口單
    invoice_date    = Column(Date, nullable=False, default=date.today)  # 發票日期
    due_date        = Column(Date, nullable=True)                       # 付款到期日

    # ── 賣方（泰方公司）────────────────────────────────────
    seller_name     = Column(String(200), nullable=False)               # 公司名稱
    seller_address  = Column(Text, nullable=True)                       # 地址
    seller_tax_id   = Column(String(50), nullable=True)                 # Tax ID
    seller_contact  = Column(String(100), nullable=True)                # 聯絡人
    seller_phone    = Column(String(50), nullable=True)                 # 電話
    seller_email    = Column(String(100), nullable=True)                # Email

    # ── 買方（台方公司）────────────────────────────────────
    buyer_name      = Column(String(200), nullable=False)               # 公司名稱
    buyer_address   = Column(Text, nullable=True)                       # 地址
    buyer_tax_id    = Column(String(50), nullable=True)                 # 統一編號
    buyer_contact   = Column(String(100), nullable=True)                # 聯絡人
    buyer_phone     = Column(String(50), nullable=True)                 # 電話
    buyer_email     = Column(String(100), nullable=True)                # Email

    # ── 貿易條件 ──────────────────────────────────────────
    currency        = Column(String(5), nullable=False, default="THB")  # 幣別 THB/USD/TWD
    incoterms       = Column(String(10), nullable=True)                 # 貿易條件 FOB/CIF/CFR/EXW
    payment_terms   = Column(String(200), nullable=True)                # 付款條件

    # ── 金額 ──────────────────────────────────────────────
    subtotal        = Column(Numeric(14, 2), nullable=True)             # 商品小計
    freight_charge  = Column(Numeric(12, 2), nullable=True, default=0)  # 運費
    insurance_charge= Column(Numeric(12, 2), nullable=True, default=0)  # 保險費
    other_charge    = Column(Numeric(12, 2), nullable=True, default=0)  # 其他費用
    total_amount    = Column(Numeric(14, 2), nullable=True)             # 發票總金額

    # ── 物流資訊（從出口單帶入或手動填寫）───────────────────
    transport_mode  = Column(String(10), nullable=True)                 # air/sea
    bl_awb_no       = Column(String(100), nullable=True)                # 提單/空運單號
    vessel_flight   = Column(String(100), nullable=True)                # 船名/航班
    port_of_loading = Column(String(100), nullable=True)                # 裝貨港
    port_of_discharge = Column(String(100), nullable=True)              # 卸貨港

    # ── 狀態與備註 ────────────────────────────────────────
    status          = Column(String(20), nullable=False, default="draft")  # draft/confirmed/sent/paid
    notes           = Column(Text, nullable=True)                       # 備註（海關備註等）

    created_by      = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at      = Column(DateTime, default=datetime.utcnow)
    updated_at      = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 關聯
    shipment     = relationship("Shipment", foreign_keys=[shipment_id])
    items        = relationship("InvoiceItem", back_populates="invoice", cascade="all, delete-orphan")
    creator      = relationship("User", foreign_keys=[created_by])


class InvoiceItem(Base):
    """發票商品明細"""
    __tablename__ = "invoice_items"

    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    invoice_id     = Column(UUID(as_uuid=True), ForeignKey("invoices.id"), nullable=False)
    batch_id       = Column(UUID(as_uuid=True), ForeignKey("batches.id"), nullable=True)  # 關聯批次

    description    = Column(String(300), nullable=False)                # 品名描述
    hs_code        = Column(String(20), nullable=True)                  # HS Code（海關稅則號列）
    quantity_kg    = Column(Numeric(10, 2), nullable=True)              # 數量(kg)
    quantity_boxes = Column(Integer, nullable=True)                      # 箱數
    unit_price     = Column(Numeric(10, 2), nullable=True)              # 單價
    amount         = Column(Numeric(14, 2), nullable=True)              # 小計
    origin_country = Column(String(50), nullable=True, default="Thailand")  # 原產國
    notes          = Column(Text, nullable=True)

    # 關聯
    invoice = relationship("Invoice", back_populates="items")
    batch   = relationship("Batch")
