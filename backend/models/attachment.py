"""
通用附件模型
支援多種實體類型的檔案上傳與標籤分類。
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, BigInteger, ForeignKey, CheckConstraint, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from database import Base


class Attachment(Base):
    """通用附件

    透過 entity_type + entity_id 實現多態關聯，
    任何實體（批次、供應商、QC 記錄等）都可附加檔案。
    """
    __tablename__ = "attachments"
    __table_args__ = (
        CheckConstraint(
            "entity_type IN ('batch','supplier','purchase_order','qc_record',"
            "'processing_order','shipment','inventory_lot','sales_order',"
            "'oem_factory','customer')",
            name="ck_attachments_entity_type",
        ),
        Index("ix_attachments_entity", "entity_type", "entity_id"),
    )

    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entity_type   = Column(String(30), nullable=False)              # 關聯實體類型
    entity_id     = Column(UUID(as_uuid=True), nullable=False)      # 關聯實體 ID
    file_name     = Column(String(255), nullable=False)             # 原始檔名
    file_size     = Column(BigInteger, nullable=True)               # 檔案大小（bytes）
    mime_type     = Column(String(100), nullable=True)              # MIME 類型
    storage_path  = Column(String(500), nullable=False)             # 儲存路徑
    uploaded_by   = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at    = Column(DateTime, default=datetime.utcnow)

    # 關聯
    uploader = relationship("User", foreign_keys=[uploaded_by])
    tags     = relationship("AttachmentTag", back_populates="attachment", cascade="all, delete-orphan")


class AttachmentTag(Base):
    """附件標籤

    每張附件可有多個標籤，用於分類照片用途（收貨照、QC 照、裝櫃照等）。
    """
    __tablename__ = "attachment_tags"
    __table_args__ = (
        CheckConstraint(
            "tag IN ('receiving_photo','qc_photo','packing_photo','loading_photo',"
            "'cold_storage_photo','temperature_photo','shipping_photo','document_scan')",
            name="ck_attachment_tags_tag",
        ),
    )

    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    attachment_id  = Column(
        UUID(as_uuid=True),
        ForeignKey("attachments.id", ondelete="CASCADE"),
        nullable=False,
    )
    tag            = Column(String(30), nullable=False)             # 標籤類型
    created_at     = Column(DateTime, default=datetime.utcnow)

    # 關聯
    attachment = relationship("Attachment", back_populates="tags")
