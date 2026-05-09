"""
人事資源管理（HR）模型

模組：
1. Department        — 部門
2. EmployeeProfile   — 員工人事檔案
3. Appointment       — 職務異動記錄
4. Attendance        — 出勤記錄
5. PayrollRecord     — 薪資記錄
"""
import uuid
from datetime import datetime, date
from sqlalchemy import (
    Column, String, Boolean, DateTime, Date, Text, Numeric,
    Integer, ForeignKey, UniqueConstraint, CheckConstraint,
)
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.orm import relationship

from database import Base
from utils.encryption import EncryptedString


# ─── 1. 部門 ─────────────────────────────────────────────

class Department(Base):
    """部門表（支援上下層級結構）"""
    __tablename__ = "departments"

    id                    = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    department_code       = Column(String(20), unique=True, nullable=False)    # 部門代碼，如 'TH_FACTORY'
    department_name       = Column(String(100), nullable=False)                # 部門名稱（繁中）
    department_name_en    = Column(String(100), nullable=True)                 # 英文名稱
    department_name_th    = Column(String(100), nullable=True)                 # 泰文名稱
    parent_department_id  = Column(UUID(as_uuid=True), ForeignKey("departments.id"), nullable=True)  # 上級部門
    manager_user_id       = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)         # 部門主管
    cost_center_code      = Column(String(20), nullable=True)                  # 成本中心代碼
    country_code          = Column(String(2), default="TW", nullable=False)    # 所在國家
    is_active             = Column(Boolean, default=True, nullable=False)
    created_at            = Column(DateTime, default=datetime.utcnow)
    updated_at            = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 關聯
    parent_department = relationship("Department", foreign_keys=[parent_department_id], remote_side="Department.id")
    manager           = relationship("User", foreign_keys=[manager_user_id])


# ─── 2. 員工人事檔案 ─────────────────────────────────────

class EmployeeProfile(Base):
    """員工詳細人事檔案（與 User 一對一）"""
    __tablename__ = "employee_profiles"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_employee_profiles_user_id"),
    )

    id                       = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id                  = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    employee_code            = Column(String(20), unique=True, nullable=False)      # 員工編號，如 'EMP-TH-001'

    # 個人資料
    national_id              = Column(EncryptedString, nullable=True)               # 身分證/護照（加密）
    birthday                 = Column(Date, nullable=True)                          # 出生日期
    gender                   = Column(String(10), nullable=True)                    # male/female/other
    marital_status           = Column(String(20), nullable=True)                    # single/married/divorced/widowed
    emergency_contact_name   = Column(String(100), nullable=True)                  # 緊急聯絡人
    emergency_contact_phone  = Column(String(30), nullable=True)                   # 緊急聯絡電話

    # 薪資帳戶（加密）
    bank_name                = Column(String(100), nullable=True)                   # 銀行名稱
    bank_account             = Column(EncryptedString, nullable=True)               # 帳戶號碼（加密）
    bank_branch              = Column(String(100), nullable=True)                   # 分行

    # 勞保健保
    labor_insurance_date     = Column(Date, nullable=True)                          # 勞保加入日
    health_insurance_date    = Column(Date, nullable=True)                          # 健保加入日

    # 學歷與認證
    education                = Column(String(50), nullable=True)                    # 最高學歷
    certifications           = Column(JSON, default=list)                           # 專業認證清單 JSON

    # 工作設定
    work_location            = Column(String(30), nullable=True)                    # thailand_factory/taiwan_hq/overseas
    country_code             = Column(String(2), default="TW", nullable=False)      # 員工所在國家
    hire_date                = Column(Date, nullable=True)                          # 入職日期
    resignation_date         = Column(Date, nullable=True)                          # 離職日期
    employment_type          = Column(String(20), default="full_time")              # full_time/part_time/contract

    note                     = Column(Text, nullable=True)
    created_at               = Column(DateTime, default=datetime.utcnow)
    updated_at               = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 關聯
    user = relationship("User", foreign_keys=[user_id])


# ─── 3. 職務異動記錄 ─────────────────────────────────────

class Appointment(Base):
    """職務異動記錄（聘用/晉升/調動/離職/終止）"""
    __tablename__ = "appointments"

    id                  = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id             = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    effective_date      = Column(Date, nullable=False)                         # 生效日期
    appointment_type    = Column(String(20), nullable=False)                   # hire/promote/transfer/resign/terminate
    from_role_id        = Column(UUID(as_uuid=True), ForeignKey("roles.id"), nullable=True)
    to_role_id          = Column(UUID(as_uuid=True), ForeignKey("roles.id"), nullable=True)
    from_department_id  = Column(UUID(as_uuid=True), ForeignKey("departments.id"), nullable=True)
    to_department_id    = Column(UUID(as_uuid=True), ForeignKey("departments.id"), nullable=True)
    from_title          = Column(String(100), nullable=True)                   # 原職稱
    to_title            = Column(String(100), nullable=True)                   # 新職稱
    reason              = Column(Text, nullable=True)                          # 異動原因
    approved_by         = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    approved_at         = Column(DateTime, nullable=True)
    created_at          = Column(DateTime, default=datetime.utcnow)

    # 關聯
    user             = relationship("User", foreign_keys=[user_id])
    from_role        = relationship("Role", foreign_keys=[from_role_id])
    to_role          = relationship("Role", foreign_keys=[to_role_id])
    from_department  = relationship("Department", foreign_keys=[from_department_id])
    to_department    = relationship("Department", foreign_keys=[to_department_id])
    approver         = relationship("User", foreign_keys=[approved_by])


# ─── 4. 出勤記錄 ─────────────────────────────────────────

class Attendance(Base):
    """員工每日出勤記錄"""
    __tablename__ = "attendances"
    __table_args__ = (
        UniqueConstraint("user_id", "attendance_date", name="uq_attendance_user_date"),
        CheckConstraint(
            "status IN ('present','absent','late','leave','holiday')",
            name="ck_attendance_status",
        ),
    )

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id          = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    attendance_date  = Column(Date, nullable=False)                             # 出勤日期
    clock_in         = Column(DateTime, nullable=True)                          # 打卡上班
    clock_out        = Column(DateTime, nullable=True)                          # 打卡下班
    status           = Column(String(20), nullable=False, default="present")    # 出勤狀態
    leave_type       = Column(String(20), nullable=True)                        # annual/sick/personal/official/bereavement/marriage
    overtime_hours   = Column(Numeric(4, 1), default=0)                         # 加班時數
    notes            = Column(Text, nullable=True)
    created_at       = Column(DateTime, default=datetime.utcnow)
    updated_at       = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 關聯
    user = relationship("User", foreign_keys=[user_id])


# ─── 5. 薪資記錄 ─────────────────────────────────────────

class PayrollRecord(Base):
    """月度薪資記錄"""
    __tablename__ = "payroll_records"
    __table_args__ = (
        UniqueConstraint("user_id", "period_year", "period_month", name="uq_payroll_user_period"),
        CheckConstraint(
            "status IN ('draft','confirmed','paid')",
            name="ck_payroll_status",
        ),
    )

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id          = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    period_year      = Column(Integer, nullable=False)                          # 薪資年份
    period_month     = Column(Integer, nullable=False)                          # 薪資月份（1-12）

    # 薪資項目
    currency         = Column(String(3), default="TWD", nullable=False)         # 幣別（TWD/THB）
    base_salary      = Column(Numeric(12, 2), nullable=False)                   # 底薪
    allowances       = Column(Numeric(12, 2), default=0)                        # 各項津貼
    overtime_pay     = Column(Numeric(12, 2), default=0)                        # 加班費
    bonus            = Column(Numeric(12, 2), default=0)                        # 獎金
    commission       = Column(Numeric(12, 2), default=0)                        # 業務佣金

    # 扣除項目
    deductions       = Column(Numeric(12, 2), default=0)                        # 其他扣款
    labor_insurance  = Column(Numeric(10, 2), default=0)                        # 勞保費
    health_insurance = Column(Numeric(10, 2), default=0)                        # 健保費
    tax              = Column(Numeric(10, 2), default=0)                        # 所得稅預扣

    # 實領
    net_pay          = Column(Numeric(12, 2), nullable=False)                   # 實領薪資

    status           = Column(String(10), nullable=False, default="draft")      # 狀態
    paid_at          = Column(DateTime, nullable=True)                          # 實際發薪時間
    approved_by      = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    note             = Column(Text, nullable=True)
    created_at       = Column(DateTime, default=datetime.utcnow)
    updated_at       = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 關聯
    user     = relationship("User", foreign_keys=[user_id])
    approver = relationship("User", foreign_keys=[approved_by])
