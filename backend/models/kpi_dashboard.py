"""
KPI 定義、儀表板配置、自訂報表模型（O 段）

O-01  KPIDefinition / KPIValue — KPI 指標定義與歷史值
O-02  DashboardConfig          — 儀表板個人化配置
O-04  SavedReport              — 自訂報表定義
"""
import uuid
from datetime import datetime, date
from sqlalchemy import (
    Column, String, Boolean, DateTime, Date, Text, Numeric,
    Integer, ForeignKey, CheckConstraint, UniqueConstraint, Index,
)
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.orm import relationship

from database import Base


# ─── O-01 KPI 指標定義 ────────────────────────────────────

class KPIDefinition(Base):
    """KPI 指標定義（可客製）"""
    __tablename__ = "kpi_definitions"
    __table_args__ = (
        CheckConstraint(
            "direction IN ('higher_is_better','lower_is_better')",
            name="ck_kpi_direction",
        ),
        CheckConstraint(
            "update_frequency IN ('realtime','daily','weekly','monthly')",
            name="ck_kpi_update_freq",
        ),
    )

    id                     = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    kpi_code               = Column(String(50), unique=True, nullable=False)   # e.g. GROSS_MARGIN_PCT
    kpi_name               = Column(String(200), nullable=False)               # 指標名稱（繁中）
    kpi_name_en            = Column(String(200), nullable=True)                # 指標名稱（英文）
    kpi_category           = Column(String(50), nullable=True)                 # finance/sales/quality/logistics/supply

    calculation_formula    = Column(Text, nullable=True)                       # 計算公式說明
    data_source            = Column(String(200), nullable=True)                # 資料來源說明

    target_value           = Column(Numeric(16, 4), nullable=True)             # 目標值
    warning_threshold      = Column(Numeric(16, 4), nullable=True)             # 預警門檻
    critical_threshold     = Column(Numeric(16, 4), nullable=True)             # 嚴重門檻

    unit                   = Column(String(30), nullable=True)                 # 單位（%/TWD/kg）
    direction              = Column(String(20), nullable=False, default="higher_is_better")
    update_frequency       = Column(String(20), nullable=False, default="daily")
    owner_role             = Column(String(50), nullable=True)                 # 負責角色

    is_active              = Column(Boolean, default=True)
    created_at             = Column(DateTime, default=datetime.utcnow)
    updated_at             = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    values = relationship("KPIValue", back_populates="kpi")


class KPIValue(Base):
    """KPI 歷史數值記錄"""
    __tablename__ = "kpi_values"
    __table_args__ = (
        UniqueConstraint("kpi_id", "period_type", "period_date", name="uq_kpi_value_period"),
        CheckConstraint(
            "period_type IN ('daily','weekly','monthly','quarterly','yearly')",
            name="ck_kpi_period_type",
        ),
        CheckConstraint(
            "status IN ('on_track','warning','critical','unknown')",
            name="ck_kpi_value_status",
        ),
        Index("ix_kpi_values_kpi_period", "kpi_id", "period_date"),
    )

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    kpi_id           = Column(UUID(as_uuid=True), ForeignKey("kpi_definitions.id"), nullable=False)
    period_type      = Column(String(20), nullable=False)
    period_date      = Column(Date, nullable=False)                         # 期間起始日
    actual_value     = Column(Numeric(16, 4), nullable=True)                # 實際值
    target_value     = Column(Numeric(16, 4), nullable=True)                # 當期目標值
    achievement_pct  = Column(Numeric(7, 2), nullable=True)                 # 達成率%
    status           = Column(String(20), nullable=False, default="unknown")
    notes            = Column(Text, nullable=True)
    calculated_at    = Column(DateTime, default=datetime.utcnow)

    kpi = relationship("KPIDefinition", back_populates="values")


# ─── O-02 儀表板配置 ──────────────────────────────────────

class DashboardConfig(Base):
    """儀表板個人化配置"""
    __tablename__ = "dashboard_configs"
    __table_args__ = (
        CheckConstraint(
            "dashboard_type IN ('executive','sales','supply_chain','finance','quality','market_intel','risk','hr')",
            name="ck_dashboard_type",
        ),
    )

    id                       = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dashboard_code           = Column(String(50), nullable=False)           # EXEC_MAIN / SALES_REP_VIEW
    dashboard_name           = Column(String(200), nullable=False)
    dashboard_type           = Column(String(30), nullable=False)
    layout_config            = Column(JSON, default=dict)                   # Widget 佈局配置 JSON
    refresh_interval_seconds = Column(Integer, default=300)                 # 自動刷新間隔（秒）
    is_default               = Column(Boolean, default=False)               # 是否預設儀表板
    role_id                  = Column(UUID(as_uuid=True), ForeignKey("roles.id"), nullable=True)  # 角色預設
    user_id                  = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)  # 個人配置
    is_active                = Column(Boolean, default=True)
    created_by               = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at               = Column(DateTime, default=datetime.utcnow)
    updated_at               = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 關聯
    user    = relationship("User", foreign_keys=[user_id])
    creator = relationship("User", foreign_keys=[created_by])


# ─── O-04 自訂報表 ────────────────────────────────────────

class SavedReport(Base):
    """自訂報表定義（排程匯出）"""
    __tablename__ = "saved_reports"
    __table_args__ = (
        CheckConstraint(
            "output_format IN ('pdf','excel','csv','json')",
            name="ck_report_format",
        ),
    )

    id                = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    report_code       = Column(String(50), unique=True, nullable=False)    # RPT-SALES-MONTHLY
    report_name       = Column(String(200), nullable=False)
    report_category   = Column(String(50), nullable=True)                  # sales/finance/quality/logistics

    query_definition  = Column(JSON, default=dict)                         # 查詢定義 JSON
    filter_config     = Column(JSON, default=dict)                         # 篩選條件
    output_format     = Column(String(10), nullable=False, default="excel")
    schedule_cron     = Column(String(50), nullable=True)                  # cron 表達式（排程時間）
    recipients        = Column(JSON, default=list)                         # 收件人 email 清單
    last_run_at       = Column(DateTime, nullable=True)                    # 最後執行時間

    is_shared         = Column(Boolean, default=False)                     # 是否分享給他人
    created_by        = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    deleted_at        = Column(DateTime, nullable=True)
    created_at        = Column(DateTime, default=datetime.utcnow)
    updated_at        = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    creator = relationship("User", foreign_keys=[created_by])
