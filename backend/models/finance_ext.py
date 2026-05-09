"""
財務擴充模型（I-04 ~ I-07, I-10）

涵蓋：
I-04  PettyCashFund    — 零用金帳戶
I-05  PettyCashRecord  — 零用金記錄
I-06  BankAccount      — 銀行帳戶
I-07  BankTransaction  — 銀行交易流水 / Cheque — 票據
I-10  Budget           — 預算 / CashFlowPlan — 現金流計劃

注意：I-01（匯率強化）/ I-02（AP 強化）/ I-03（AR 強化）為既有模型欄位補充，
      已在 migrate 或業務邏輯層處理。
      I-08（損益表）/ I-09（泰國稅務）為 API 端點，無需新 Model。
"""
import uuid
from datetime import datetime, date
from sqlalchemy import (
    Column, String, Boolean, DateTime, Date, Text, Numeric,
    Integer, ForeignKey, CheckConstraint, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.orm import relationship

from database import Base


# ─── I-04 零用金帳戶 ──────────────────────────────────────

class PettyCashFund(Base):
    """零用金帳戶（部門現金備用金）"""
    __tablename__ = "petty_cash_funds"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    fund_name       = Column(String(100), nullable=False)                  # 基金名稱
    holder_name     = Column(String(100), nullable=True)                   # 持有人姓名
    holder_user_id  = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    department      = Column(String(100), nullable=True)                   # 所屬部門
    balance         = Column(Numeric(12, 2), default=0)                    # 目前餘額
    fund_limit      = Column(Numeric(12, 2), default=5000)                 # 上限
    currency        = Column(String(3), default="TWD")                     # 幣別 THB/TWD
    is_active       = Column(Boolean, default=True, nullable=False)
    notes           = Column(Text, nullable=True)
    created_at      = Column(DateTime, default=datetime.utcnow)
    updated_at      = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 關聯
    holder  = relationship("User", foreign_keys=[holder_user_id])
    records = relationship("PettyCashRecord", back_populates="fund")


# ─── I-05 零用金記錄 ──────────────────────────────────────

class PettyCashRecord(Base):
    """零用金收支記錄"""
    __tablename__ = "petty_cash_records"
    __table_args__ = (
        CheckConstraint(
            "category IN ('fuel','meal','transport','office','maintenance','postage','cleaning','entertainment','other')",
            name="ck_petty_cash_category",
        ),
        CheckConstraint(
            "status IN ('pending','confirmed','rejected','reimbursed')",
            name="ck_petty_cash_status",
        ),
    )

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    fund_id          = Column(UUID(as_uuid=True), ForeignKey("petty_cash_funds.id"), nullable=False)
    record_no        = Column(String(30), unique=True, nullable=False)    # PC-YYYYMMDD-XXX

    record_date      = Column(Date, nullable=False, default=date.today)
    category         = Column(String(30), nullable=False)                  # 費用類別
    description      = Column(Text, nullable=False)                        # 說明
    amount           = Column(Numeric(10, 2), nullable=False)              # 金額
    vendor           = Column(String(200), nullable=True)                  # 廠商/對象

    receipt_no       = Column(String(100), nullable=True)                  # 發票/收據號碼
    receipt_photos   = Column(JSON, default=list)                          # 收據照片 URLs
    has_receipt      = Column(Boolean, default=False, nullable=False)      # 是否有收據

    status           = Column(String(20), nullable=False, default="pending")
    reviewed_by      = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    reviewed_at      = Column(DateTime, nullable=True)
    review_note      = Column(Text, nullable=True)
    submitted_by     = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    created_at       = Column(DateTime, default=datetime.utcnow)
    updated_at       = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 關聯
    fund     = relationship("PettyCashFund", back_populates="records")
    reviewer = relationship("User", foreign_keys=[reviewed_by])
    submitter = relationship("User", foreign_keys=[submitted_by])


# ─── I-06 銀行帳戶 ────────────────────────────────────────

class BankAccount(Base):
    """公司銀行帳戶管理"""
    __tablename__ = "bank_accounts"
    __table_args__ = (
        CheckConstraint(
            "account_type IN ('checking','savings','credit_card','fx','other')",
            name="ck_bank_account_type",
        ),
    )

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_name     = Column(String(200), nullable=False)                 # 帳戶名稱
    account_no       = Column(String(50), nullable=False)                  # 帳號
    bank_name        = Column(String(200), nullable=False)                 # 銀行名稱
    bank_code        = Column(String(20), nullable=True)                   # 銀行代碼
    swift_code       = Column(String(20), nullable=True)                   # SWIFT BIC
    account_type     = Column(String(20), nullable=False, default="checking")
    currency         = Column(String(3), default="TWD")                    # 帳戶幣別
    country_code     = Column(String(2), nullable=True)                    # 國家 ISO-3166

    opening_balance  = Column(Numeric(16, 2), default=0)                   # 期初餘額
    current_balance  = Column(Numeric(16, 2), default=0)                   # 目前餘額
    credit_limit     = Column(Numeric(16, 2), nullable=True)               # 信用額度（信用卡）
    statement_day    = Column(Integer, nullable=True)                      # 對帳單日（1-31）
    payment_day      = Column(Integer, nullable=True)                      # 繳款截止日（1-31）

    is_active        = Column(Boolean, default=True, nullable=False)
    notes            = Column(Text, nullable=True)
    created_at       = Column(DateTime, default=datetime.utcnow)
    updated_at       = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 關聯
    transactions = relationship("BankTransaction", back_populates="bank_account")


# ─── I-07 銀行交易流水 ────────────────────────────────────

class BankTransaction(Base):
    """銀行帳戶交易記錄"""
    __tablename__ = "bank_transactions"
    __table_args__ = (
        CheckConstraint(
            "direction IN ('debit','credit')",
            name="ck_bank_tx_direction",
        ),
    )

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bank_account_id  = Column(UUID(as_uuid=True), ForeignKey("bank_accounts.id"), nullable=False)
    tx_date          = Column(Date, nullable=False)                        # 交易日期
    description      = Column(String(500), nullable=True)                  # 交易說明
    direction        = Column(String(10), nullable=False)                  # debit/credit
    amount           = Column(Numeric(16, 2), nullable=False)              # 交易金額
    balance          = Column(Numeric(16, 2), nullable=True)               # 交易後餘額
    reference_no     = Column(String(100), nullable=True)                  # 參考號碼
    category         = Column(String(50), nullable=True)                   # 交易分類
    is_reconciled    = Column(Boolean, default=False, nullable=False)      # 是否已對帳
    reconciled_at    = Column(DateTime, nullable=True)
    created_at       = Column(DateTime, default=datetime.utcnow)

    # 關聯
    bank_account = relationship("BankAccount", back_populates="transactions")


class Cheque(Base):
    """票據管理（應收票據 / 應付票據）"""
    __tablename__ = "cheques"
    __table_args__ = (
        CheckConstraint(
            "cheque_type IN ('receivable','payable')",
            name="ck_cheque_type",
        ),
        CheckConstraint(
            "status IN ('holding','deposited','cleared','bounced','cancelled')",
            name="ck_cheque_status",
        ),
        CheckConstraint(
            "party_type IN ('customer','supplier','other')",
            name="ck_cheque_party_type",
        ),
    )

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cheque_no    = Column(String(50), unique=True, nullable=False)          # 票號
    cheque_type  = Column(String(20), nullable=False)                       # receivable/payable
    bank_name    = Column(String(200), nullable=True)                       # 付款銀行
    amount       = Column(Numeric(14, 2), nullable=False)                   # 票面金額
    currency     = Column(String(3), default="TWD")
    issue_date   = Column(Date, nullable=True)                              # 發票日
    due_date     = Column(Date, nullable=False)                             # 到期日
    status       = Column(String(20), nullable=False, default="holding")
    party_name   = Column(String(200), nullable=True)                       # 對方名稱
    party_type   = Column(String(20), nullable=True)                        # customer/supplier

    notes        = Column(Text, nullable=True)
    created_by   = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at   = Column(DateTime, default=datetime.utcnow)
    updated_at   = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    creator = relationship("User", foreign_keys=[created_by])


# ─── I-10 預算 / 現金流計劃 ──────────────────────────────

class Budget(Base):
    """年度 / 月度預算"""
    __tablename__ = "budgets"
    __table_args__ = (
        UniqueConstraint("budget_year", "budget_month", "category", "department",
                         name="uq_budget_year_month_cat_dept"),
        CheckConstraint(
            "category IN ('revenue','cogs','opex','capex','hr','marketing','logistics','other')",
            name="ck_budget_category",
        ),
        CheckConstraint(
            "status IN ('draft','approved','locked')",
            name="ck_budget_status",
        ),
    )

    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    budget_year    = Column(Integer, nullable=False)                        # 預算年度
    budget_month   = Column(Integer, nullable=True)                         # 預算月份（NULL = 年度預算）
    department     = Column(String(100), nullable=True)                     # 部門
    category       = Column(String(30), nullable=False)                     # 費用類別
    budget_amount  = Column(Numeric(16, 2), default=0)                      # 預算金額
    actual_amount  = Column(Numeric(16, 2), default=0)                      # 實際金額
    currency       = Column(String(3), default="TWD")
    status         = Column(String(20), nullable=False, default="draft")
    notes          = Column(Text, nullable=True)
    approved_by    = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at     = Column(DateTime, default=datetime.utcnow)
    updated_at     = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    approver = relationship("User", foreign_keys=[approved_by])


class CashFlowPlan(Base):
    """月度現金流計劃"""
    __tablename__ = "cash_flow_plans"
    __table_args__ = (
        CheckConstraint(
            "flow_type IN ('inflow','outflow')",
            name="ck_cashflow_type",
        ),
        CheckConstraint(
            "category IN ('sales_receipt','ar_collection','payment','salary','rent','tax',"
            "'dividend','loan_in','loan_out','capex','other')",
            name="ck_cashflow_category",
        ),
    )

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plan_year       = Column(Integer, nullable=False)                       # 計劃年度
    plan_month      = Column(Integer, nullable=False)                       # 計劃月份 1~12
    flow_type       = Column(String(10), nullable=False)                    # inflow/outflow
    category        = Column(String(30), nullable=False)                    # 現金流類別
    planned_amount  = Column(Numeric(16, 2), default=0)                     # 計劃金額
    actual_amount   = Column(Numeric(16, 2), default=0)                     # 實際金額
    currency        = Column(String(3), default="TWD")
    notes           = Column(Text, nullable=True)
    created_at      = Column(DateTime, default=datetime.utcnow)
    updated_at      = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
