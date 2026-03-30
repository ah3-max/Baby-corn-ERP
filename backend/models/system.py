"""
系統設定與多語系覆寫模型
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, ForeignKey, CheckConstraint, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.orm import relationship

from database import Base


class SystemSetting(Base):
    """系統設定

    key-value 形式儲存全域設定，如預設匯率、通知閾值等。
    value 為 JSON 格式，可存任意結構。
    """
    __tablename__ = "system_settings"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key         = Column(String(100), unique=True, nullable=False)    # 設定鍵，如 'default_exchange_rate'
    value       = Column(JSON, nullable=True)                         # 設定值（JSON）
    description = Column(Text, nullable=True)                         # 說明
    updated_by  = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at  = Column(DateTime, default=datetime.utcnow)
    updated_at  = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 關聯
    updater = relationship("User", foreign_keys=[updated_by])


class I18nOverride(Base):
    """多語系覆寫

    允許管理員在資料庫層覆寫前端的翻譯文字，
    不需要重新部署即可修改 UI 用語。
    """
    __tablename__ = "i18n_overrides"
    __table_args__ = (
        UniqueConstraint(
            "locale", "namespace", "key",
            name="uq_i18n_overrides_locale_ns_key",
        ),
        CheckConstraint(
            "locale IN ('zh-TW','en','th')",
            name="ck_i18n_overrides_locale",
        ),
    )

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    locale      = Column(String(5), nullable=False)                   # 語系：zh-TW / en / th
    namespace   = Column(String(30), nullable=False)                  # 命名空間，如 'common', 'batch', 'qc'
    key         = Column(String(200), nullable=False)                 # 翻譯鍵
    value       = Column(Text, nullable=False)                        # 翻譯值
    updated_by  = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at  = Column(DateTime, default=datetime.utcnow)
    updated_at  = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 關聯
    updater = relationship("User", foreign_keys=[updated_by])
