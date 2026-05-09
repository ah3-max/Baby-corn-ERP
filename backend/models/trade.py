"""
國際貿易文件模型（G-01 ~ G-05）

涵蓋：
1. TradeDocument       — 貿易文件總表（各類型文件統一管理）
2. LetterOfCredit      — 信用狀（L/C）
3. CertificateOfOrigin — 產地證明書（CO）
4. PackingList         — 裝箱單
5. BillOfLading        — 提單（B/L）
"""
import uuid
from datetime import datetime, date
from sqlalchemy import (
    Column, String, Boolean, DateTime, Date, Text, Numeric,
    Integer, ForeignKey, CheckConstraint, Index,
)
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.orm import relationship

from database import Base


# ─── G-01 貿易文件總表 ───────────────────────────────────

class TradeDocument(Base):
    """貿易文件總表 — 統一管理各類型跨境貿易文件"""
    __tablename__ = "trade_documents"
    __table_args__ = (
        CheckConstraint(
            "document_type IN ("
            "'commercial_invoice','packing_list','bill_of_lading',"
            "'certificate_of_origin','phytosanitary','health_certificate',"
            "'fumigation','export_declaration','import_declaration',"
            "'letter_of_credit','insurance_certificate','other')",
            name="ck_trade_doc_type",
        ),
        CheckConstraint(
            "status IN ('draft','pending_review','approved','sent','received','expired','rejected')",
            name="ck_trade_doc_status",
        ),
        Index("ix_trade_docs_type_status", "document_type", "status"),
        Index("ix_trade_docs_expiry", "expiry_date"),
        Index("ix_trade_docs_shipment", "shipment_id"),
    )

    id                   = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_type        = Column(String(50), nullable=False)                      # 文件類型
    document_number      = Column(String(100), nullable=True)                      # 文件號碼
    document_title       = Column(String(200), nullable=True)                      # 文件標題

    # 關聯業務實體
    shipment_id          = Column(UUID(as_uuid=True), ForeignKey("shipments.id"), nullable=True)
    sales_order_id       = Column(UUID(as_uuid=True), ForeignKey("sales_orders.id"), nullable=True)
    customer_id          = Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=True)
    supplier_id          = Column(UUID(as_uuid=True), ForeignKey("suppliers.id"), nullable=True)

    # 日期資訊
    issue_date           = Column(Date, nullable=True)                             # 簽發日期
    expiry_date          = Column(Date, nullable=True)                             # 到期日期
    submission_deadline  = Column(Date, nullable=True)                             # 提交截止日

    # 簽發資訊
    issuing_authority    = Column(String(200), nullable=True)                      # 簽發機構
    issuing_country      = Column(String(2), nullable=True)                        # 簽發國 ISO-3166
    destination_country  = Column(String(2), nullable=True)                        # 目的國 ISO-3166

    # 狀態與備註
    status               = Column(String(30), nullable=False, default="draft")
    notes                = Column(Text, nullable=True)
    file_path            = Column(String(500), nullable=True)                      # 掃描檔案路徑
    attachment_id        = Column(UUID(as_uuid=True), ForeignKey("attachments.id"), nullable=True)

    # 費用
    document_fee         = Column(Numeric(10, 2), nullable=True)                   # 文件費用
    document_fee_currency = Column(String(3), default="TWD")

    created_by           = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    deleted_at           = Column(DateTime, nullable=True)
    created_at           = Column(DateTime, default=datetime.utcnow)
    updated_at           = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 關聯
    shipment   = relationship("Shipment", foreign_keys=[shipment_id])
    sales_order = relationship("SalesOrder", foreign_keys=[sales_order_id])
    customer   = relationship("Customer", foreign_keys=[customer_id])
    supplier   = relationship("Supplier", foreign_keys=[supplier_id])
    creator    = relationship("User", foreign_keys=[created_by])
    attachment = relationship("Attachment", foreign_keys=[attachment_id])


# ─── G-02 信用狀（L/C）────────────────────────────────────

class LetterOfCredit(Base):
    """信用狀管理"""
    __tablename__ = "letters_of_credit"
    __table_args__ = (
        CheckConstraint(
            "lc_type IN ('sight','usance','standby','revolving','red_clause','transferable')",
            name="ck_lc_type",
        ),
        CheckConstraint(
            "status IN ('draft','issued','amended','utilized','expired','cancelled')",
            name="ck_lc_status",
        ),
    )

    id                   = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lc_number            = Column(String(100), unique=True, nullable=False)        # 信用狀號碼
    lc_type              = Column(String(20), nullable=False, default="sight")     # 信用狀類型

    # 關聯
    sales_order_id       = Column(UUID(as_uuid=True), ForeignKey("sales_orders.id"), nullable=True)
    customer_id          = Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=True)

    # 開狀銀行資訊
    issuing_bank_name    = Column(String(200), nullable=True)                      # 開狀銀行
    issuing_bank_country = Column(String(2), nullable=True)                        # 開狀銀行國家
    advising_bank_name   = Column(String(200), nullable=True)                      # 通知銀行

    # 金額與條件
    lc_amount            = Column(Numeric(14, 2), nullable=False)                  # 信用狀金額
    lc_currency          = Column(String(3), default="USD")                        # 幣別
    tolerance_pct        = Column(Numeric(4, 1), default=5.0)                      # 允差 %（上下）

    # 日期
    issue_date           = Column(Date, nullable=True)                             # 開狀日期
    expiry_date          = Column(Date, nullable=False)                            # 到期日
    latest_shipment_date = Column(Date, nullable=True)                             # 最晚裝運日

    # 單據條件
    documents_required   = Column(JSON, default=list)                              # 需要哪些單據 ["B/L","CO","Invoice"...]
    port_of_loading      = Column(String(100), nullable=True)                      # 裝運港
    port_of_discharge    = Column(String(100), nullable=True)                      # 卸貨港
    partial_shipment     = Column(Boolean, default=False)                          # 允許分批裝運
    transhipment         = Column(Boolean, default=False)                          # 允許轉運

    status               = Column(String(20), nullable=False, default="issued")
    notes                = Column(Text, nullable=True)
    utilized_amount      = Column(Numeric(14, 2), default=0)                       # 已使用金額

    created_by           = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    deleted_at           = Column(DateTime, nullable=True)
    created_at           = Column(DateTime, default=datetime.utcnow)
    updated_at           = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 關聯
    sales_order = relationship("SalesOrder", foreign_keys=[sales_order_id])
    customer    = relationship("Customer", foreign_keys=[customer_id])
    creator     = relationship("User", foreign_keys=[created_by])


# ─── G-03 產地證明書（CO）────────────────────────────────────

class CertificateOfOrigin(Base):
    """產地證明書"""
    __tablename__ = "certificates_of_origin"
    __table_args__ = (
        CheckConstraint(
            "co_type IN ('form_a','form_d','form_e','form_ai','general','other')",
            name="ck_co_type",
        ),
        CheckConstraint(
            "status IN ('draft','applied','issued','rejected','expired')",
            name="ck_co_status",
        ),
    )

    id                   = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    co_number            = Column(String(100), unique=True, nullable=True)         # 產地證書號碼
    co_type              = Column(String(20), nullable=False, default="general")   # 產地證類型

    # 關聯
    shipment_id          = Column(UUID(as_uuid=True), ForeignKey("shipments.id"), nullable=True)
    trade_document_id    = Column(UUID(as_uuid=True), ForeignKey("trade_documents.id"), nullable=True)

    # 貿易資訊
    exporter_name        = Column(String(200), nullable=True)                      # 出口商名稱
    exporter_country     = Column(String(2), nullable=True)                        # 出口國
    importer_name        = Column(String(200), nullable=True)                      # 進口商名稱
    importer_country     = Column(String(2), nullable=True)                        # 進口國
    country_of_origin    = Column(String(2), nullable=True)                        # 原產地
    destination_country  = Column(String(2), nullable=True)                        # 目的地

    # 商品資訊
    commodity_description = Column(Text, nullable=True)                            # 商品描述
    hs_code              = Column(String(20), nullable=True)                       # HS 稅則號
    gross_weight_kg      = Column(Numeric(10, 2), nullable=True)                   # 毛重 kg
    net_weight_kg        = Column(Numeric(10, 2), nullable=True)                   # 淨重 kg
    quantity_packages    = Column(Integer, nullable=True)                          # 包裝件數
    invoice_no           = Column(String(100), nullable=True)                      # 發票號碼
    invoice_date         = Column(Date, nullable=True)                             # 發票日期

    # 簽發資訊
    issuing_authority    = Column(String(200), nullable=True)                      # 簽發機構
    issue_date           = Column(Date, nullable=True)                             # 簽發日期
    status               = Column(String(20), nullable=False, default="draft")
    notes                = Column(Text, nullable=True)

    created_by           = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    deleted_at           = Column(DateTime, nullable=True)
    created_at           = Column(DateTime, default=datetime.utcnow)
    updated_at           = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 關聯
    shipment       = relationship("Shipment", foreign_keys=[shipment_id])
    trade_document = relationship("TradeDocument", foreign_keys=[trade_document_id])
    creator        = relationship("User", foreign_keys=[created_by])


# ─── G-04 裝箱單 ─────────────────────────────────────────

class PackingList(Base):
    """裝箱單"""
    __tablename__ = "packing_lists"

    id                   = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    packing_list_no      = Column(String(100), unique=True, nullable=False)        # 裝箱單號碼

    # 關聯
    shipment_id          = Column(UUID(as_uuid=True), ForeignKey("shipments.id"), nullable=True)
    sales_order_id       = Column(UUID(as_uuid=True), ForeignKey("sales_orders.id"), nullable=True)
    trade_document_id    = Column(UUID(as_uuid=True), ForeignKey("trade_documents.id"), nullable=True)

    # 出口商 / 進口商
    exporter_name        = Column(String(200), nullable=True)
    importer_name        = Column(String(200), nullable=True)

    # 貨物資訊
    commodity_description = Column(Text, nullable=True)                            # 品名描述
    total_packages       = Column(Integer, nullable=True)                          # 總件數
    total_gross_weight_kg = Column(Numeric(10, 2), nullable=True)                  # 總毛重
    total_net_weight_kg  = Column(Numeric(10, 2), nullable=True)                   # 總淨重
    total_cbm            = Column(Numeric(8, 3), nullable=True)                    # 總體積 m³

    # 運輸資訊
    container_no         = Column(String(50), nullable=True)                       # 貨櫃號碼
    seal_no              = Column(String(50), nullable=True)                       # 鉛封號碼
    vessel_name          = Column(String(100), nullable=True)                      # 船名
    voyage_no            = Column(String(50), nullable=True)                       # 航次
    port_of_loading      = Column(String(100), nullable=True)                      # 裝運港
    port_of_discharge    = Column(String(100), nullable=True)                      # 卸貨港
    etd                  = Column(Date, nullable=True)                             # 預計出發
    eta                  = Column(Date, nullable=True)                             # 預計到達

    # 明細（JSON 格式存儲各批次/品項）
    line_items           = Column(JSON, default=list)                              # [{product, spec, packages, gross_kg, net_kg, cbm}]

    issue_date           = Column(Date, nullable=True)
    notes                = Column(Text, nullable=True)

    created_by           = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    deleted_at           = Column(DateTime, nullable=True)
    created_at           = Column(DateTime, default=datetime.utcnow)
    updated_at           = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 關聯
    shipment       = relationship("Shipment", foreign_keys=[shipment_id])
    sales_order    = relationship("SalesOrder", foreign_keys=[sales_order_id])
    trade_document = relationship("TradeDocument", foreign_keys=[trade_document_id])
    creator        = relationship("User", foreign_keys=[created_by])


# ─── G-05 提單（B/L）────────────────────────────────────────

class BillOfLading(Base):
    """提單（Bill of Lading）"""
    __tablename__ = "bills_of_lading"
    __table_args__ = (
        CheckConstraint(
            "bl_type IN ('ocean','air_waybill','multimodal','inland')",
            name="ck_bl_type",
        ),
        CheckConstraint(
            "status IN ('draft','original_issued','telex_released','seaway_bill','surrendered','expired')",
            name="ck_bl_status",
        ),
    )

    id                   = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bl_number            = Column(String(100), unique=True, nullable=False)        # 提單號碼
    bl_type              = Column(String(20), nullable=False, default="ocean")     # 提單類型

    # 關聯
    shipment_id          = Column(UUID(as_uuid=True), ForeignKey("shipments.id"), nullable=True)
    packing_list_id      = Column(UUID(as_uuid=True), ForeignKey("packing_lists.id"), nullable=True)
    trade_document_id    = Column(UUID(as_uuid=True), ForeignKey("trade_documents.id"), nullable=True)

    # 運輸資訊
    shipper_name         = Column(String(200), nullable=True)                      # 託運人
    consignee_name       = Column(String(200), nullable=True)                      # 收貨人
    notify_party         = Column(String(200), nullable=True)                      # 被通知人
    carrier_name         = Column(String(200), nullable=True)                      # 承運人（船公司）
    vessel_name          = Column(String(100), nullable=True)                      # 船名
    voyage_no            = Column(String(50), nullable=True)                       # 航次
    container_nos        = Column(JSON, default=list)                              # 貨櫃號碼清單

    # 港口 & 日期
    port_of_loading      = Column(String(100), nullable=True)                      # 裝運港
    port_of_discharge    = Column(String(100), nullable=True)                      # 卸貨港
    place_of_delivery    = Column(String(100), nullable=True)                      # 最終交貨地
    onboard_date         = Column(Date, nullable=True)                             # 裝船日期
    etd                  = Column(Date, nullable=True)                             # 預計出發
    eta                  = Column(Date, nullable=True)                             # 預計到達

    # 貨物描述
    commodity_description = Column(Text, nullable=True)
    total_packages       = Column(Integer, nullable=True)
    total_gross_weight_kg = Column(Numeric(10, 2), nullable=True)
    total_net_weight_kg  = Column(Numeric(10, 2), nullable=True)
    total_cbm            = Column(Numeric(8, 3), nullable=True)

    # 費用
    freight_amount       = Column(Numeric(12, 2), nullable=True)                   # 海運費
    freight_currency     = Column(String(3), default="USD")
    freight_terms        = Column(String(20), nullable=True)                       # prepaid/collect

    # 狀態
    status               = Column(String(30), nullable=False, default="draft")
    original_copies      = Column(Integer, default=3)                              # 正本份數
    telex_release_date   = Column(Date, nullable=True)                             # 電放日期
    notes                = Column(Text, nullable=True)

    created_by           = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    deleted_at           = Column(DateTime, nullable=True)
    created_at           = Column(DateTime, default=datetime.utcnow)
    updated_at           = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 關聯
    shipment       = relationship("Shipment", foreign_keys=[shipment_id])
    packing_list   = relationship("PackingList", foreign_keys=[packing_list_id])
    trade_document = relationship("TradeDocument", foreign_keys=[trade_document_id])
    creator        = relationship("User", foreign_keys=[created_by])


# ─── G-03 報關單 ─────────────────────────────────────────

class CustomsDeclaration(Base):
    """報關單 — 出口/進口報關記錄"""
    __tablename__ = "customs_declarations"
    __table_args__ = (
        CheckConstraint(
            "declaration_type IN ('export','import','re_export','transit')",
            name="ck_customs_decl_type",
        ),
        CheckConstraint(
            "status IN ('preparing','submitted','inspecting','cleared','rejected','cancelled')",
            name="ck_customs_decl_status",
        ),
        Index("ix_customs_decl_shipment", "shipment_id"),
        Index("ix_customs_decl_status_date", "status", "declaration_date"),
    )

    id                   = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    declaration_number   = Column(String(100), nullable=True)                      # 報關單號
    declaration_type     = Column(String(20), nullable=False, default="export")    # 報關類型
    shipment_id          = Column(UUID(as_uuid=True), ForeignKey("shipments.id"), nullable=True)
    customs_broker_id    = Column(UUID(as_uuid=True), ForeignKey("suppliers.id"), nullable=True)  # 報關行

    declaration_date     = Column(Date, nullable=True)                             # 申報日
    country_code         = Column(String(2), nullable=True)                        # 申報國
    port_of_entry        = Column(String(100), nullable=True)                      # 申報港口

    # 申報金額
    total_declared_value = Column(Numeric(16, 2), nullable=True)
    declared_currency    = Column(String(3), default="USD")
    hs_code              = Column(String(20), nullable=True)                       # 稅則號列

    # 稅費
    duty_rate_pct        = Column(Numeric(6, 3), nullable=True)                    # 關稅率%
    duty_amount          = Column(Numeric(14, 2), nullable=True)                   # 關稅金額
    vat_rate_pct         = Column(Numeric(6, 3), nullable=True)                    # 增值稅率%
    vat_amount           = Column(Numeric(14, 2), nullable=True)                   # 增值稅金額
    other_charges        = Column(Numeric(14, 2), nullable=True)                   # 其他費用

    # 狀態
    status               = Column(String(20), nullable=False, default="preparing")
    clearance_date       = Column(Date, nullable=True)                             # 放行日期
    inspection_required  = Column(Boolean, default=False, nullable=False)          # 是否驗貨
    notes                = Column(Text, nullable=True)

    created_by           = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    deleted_at           = Column(DateTime, nullable=True)
    created_at           = Column(DateTime, default=datetime.utcnow)
    updated_at           = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    shipment        = relationship("Shipment", foreign_keys=[shipment_id])
    customs_broker  = relationship("Supplier", foreign_keys=[customs_broker_id])
    creator         = relationship("User", foreign_keys=[created_by])


# ─── G-04 農藥殘留標準 ────────────────────────────────────

class MRLStandard(Base):
    """各國農藥殘留最大限量標準（Maximum Residue Levels）"""
    __tablename__ = "mrl_standards"
    __table_args__ = (
        Index("ix_mrl_country_product", "country_code", "product_category"),
        Index("ix_mrl_pesticide", "cas_number"),
    )

    id                   = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    country_code         = Column(String(2), nullable=False)                       # ISO 3166-1
    regulation_name      = Column(String(200), nullable=True)                      # 法規名稱
    product_category     = Column(String(100), nullable=False)                     # 產品分類（玉米筍）
    pesticide_name       = Column(String(200), nullable=False)                     # 農藥名稱（中文）
    pesticide_name_en    = Column(String(200), nullable=True)                      # 農藥名稱（英文）
    cas_number           = Column(String(30), nullable=True)                       # CAS 號碼
    mrl_value            = Column(Numeric(10, 4), nullable=True)                   # 限量值
    mrl_unit             = Column(String(20), default="mg/kg")                     # 單位
    effective_date       = Column(Date, nullable=True)                             # 生效日期
    source_url           = Column(String(500), nullable=True)                      # 法規來源
    is_active            = Column(Boolean, default=True, nullable=False)
    notes                = Column(Text, nullable=True)
    created_at           = Column(DateTime, default=datetime.utcnow)
    updated_at           = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Certification(Base):
    """認證管理（GLOBALG.A.P. / BRC / HACCP 等）"""
    __tablename__ = "certifications"
    __table_args__ = (
        CheckConstraint(
            "certification_type IN ('GLOBALGAP','BRC','IFS','HACCP','ORGANIC','HALAL','KOSHER','ISO22000','other')",
            name="ck_cert_type",
        ),
        CheckConstraint(
            "certified_entity_type IN ('company','supplier','farm','factory')",
            name="ck_cert_entity_type",
        ),
        CheckConstraint(
            "status IN ('active','expired','suspended','pending')",
            name="ck_cert_status",
        ),
        Index("ix_cert_expiry_status", "expiry_date", "status"),
    )

    id                        = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    certification_type        = Column(String(30), nullable=False)
    certificate_number        = Column(String(100), nullable=True, unique=True)
    issuing_body              = Column(String(200), nullable=True)                 # 發證機構
    scope_description         = Column(Text, nullable=True)                        # 認證範圍說明
    certified_entity_type     = Column(String(20), nullable=False)
    certified_entity_id       = Column(UUID(as_uuid=True), nullable=True)          # 對應的實體 ID
    certified_entity_name     = Column(String(300), nullable=True)                 # 顯示用名稱
    issue_date                = Column(Date, nullable=True)
    expiry_date               = Column(Date, nullable=True)
    status                    = Column(String(20), nullable=False, default="active")
    document_url              = Column(String(500), nullable=True)
    reminder_days_before_expiry = Column(Integer, default=60)
    created_by                = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    deleted_at                = Column(DateTime, nullable=True)
    created_at                = Column(DateTime, default=datetime.utcnow)
    updated_at                = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    creator = relationship("User", foreign_keys=[created_by])


# ─── G-05 基礎主檔 ────────────────────────────────────────

class Incoterm(Base):
    """國際貿易條件（Incoterms）主檔"""
    __tablename__ = "incoterms"

    id                   = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code                 = Column(String(5), unique=True, nullable=False)           # FOB/CIF/CFR/EXW/DDP
    name                 = Column(String(100), nullable=False)                      # Free On Board
    description          = Column(Text, nullable=True)
    risk_transfer_point  = Column(String(200), nullable=True)                      # 風險轉移地點
    cost_responsibility  = Column(Text, nullable=True)                             # 費用負擔說明
    version_year         = Column(Integer, default=2020)                           # Incoterms 版本年


class HSCode(Base):
    """HS 關稅商品分類代碼"""
    __tablename__ = "hs_codes"
    __table_args__ = (
        Index("ix_hs_code_level", "hs_code", "level"),
    )

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    hs_code          = Column(String(12), nullable=False)                          # 稅則號列
    level            = Column(Integer, nullable=False)                             # 2/4/6/8/10 位數
    description      = Column(Text, nullable=True)                                 # 英文說明
    description_zh   = Column(Text, nullable=True)                                 # 中文說明
    parent_id        = Column(UUID(as_uuid=True), ForeignKey("hs_codes.id"), nullable=True)
    is_active        = Column(Boolean, default=True)
    created_at       = Column(DateTime, default=datetime.utcnow)

    parent   = relationship("HSCode", remote_side="HSCode.id", foreign_keys=[parent_id])
    children = relationship("HSCode", back_populates="parent", foreign_keys=[parent_id])


class Port(Base):
    """港口主檔（UN/LOCODE）"""
    __tablename__ = "ports"
    __table_args__ = (
        CheckConstraint(
            "port_type IN ('sea','air','inland','road','rail')",
            name="ck_port_type",
        ),
        Index("ix_port_country_type", "country_code", "port_type"),
    )

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    port_code        = Column(String(10), unique=True, nullable=False)             # TWTPE / THBKK
    port_name        = Column(String(200), nullable=False)
    port_name_zh     = Column(String(200), nullable=True)
    port_type        = Column(String(10), nullable=False, default="sea")
    country_code     = Column(String(2), nullable=False)
    city             = Column(String(100), nullable=True)
    timezone         = Column(String(50), nullable=True)                           # Asia/Taipei
    is_active        = Column(Boolean, default=True)
    created_at       = Column(DateTime, default=datetime.utcnow)
