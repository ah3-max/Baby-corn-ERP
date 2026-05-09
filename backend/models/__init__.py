# 匯入所有 Model，讓 Alembic 自動偵測
from models.user import User, Role, Permission, RolePermission, RefreshToken
from models.supplier import Supplier
from models.product_type import ProductType
from models.purchase import PurchaseOrder
from models.batch import Batch
from models.qc import QCRecord
from models.oem_factory import OEMFactory
from models.processing import ProcessingOrder, ProcessingBatchLink
from models.shipment import Shipment, ShipmentBatch
from models.invoice import Invoice, InvoiceItem
from models.customer import Customer, CustomerContact, CustomerAddress
from models.sales import SalesOrder, SalesOrderItem, SaleBatchAllocation
from models.daily_sale import DailySale, DailySaleItem, MarketPrice
from models.cost import CostEvent, BatchCostSheet, BatchCostSheetItem
from models.inventory import Warehouse, WarehouseLocation, InventoryLot, InventoryTransaction
from models.payment import PaymentRecord
from models.exchange_rate import ExchangeRate
from models.attachment import Attachment, AttachmentTag
from models.notification import Notification
from models.system import SystemSetting, I18nOverride
from models.audit import DomainEvent, AuditLog
# WP8：每日摘要
from models.daily_summary import DailySummarySnapshot, AlertRule
# WP7：計劃
from models.planning import ProcurementPlan, ProcurementPlanItem, WeatherForecast, FinancialPlan
# WP5：財務
from models.finance import AccountReceivable, AccountPayable
# WP4：物流派遣
from models.logistics import (
    Driver, DeliveryOrder, DeliveryOrderItem, DeliveryProof,
    OutboundOrder, OutboundOrderItem,
)
# WP3：業務 CRM
from models.sales_team import SalesTeam, SalesTeamMember
from models.crm_activity import CRMActivity, CRMTask
# C 段：HR 人事模組
from models.hr import Department, EmployeeProfile, Appointment, Attendance, PayrollRecord
# D/E/F 段：CRM 進階
from models.crm import (
    SalesTarget, SalesDailyReport,
    SalesOpportunity, FollowUpLog, VisitRecord,
    Quotation, QuotationItem, SampleRequest,
    SalesSchedule, QuotationApproval,
)
# G：國際貿易文件
from models.trade import (
    TradeDocument, LetterOfCredit, CertificateOfOrigin,
    PackingList, BillOfLading,
    CustomsDeclaration, MRLStandard, Certification,
    Incoterm, HSCode, Port,
)
# H：泰國端物流與生產
from models.thai_ops import (
    ContainerTemperatureLog,
    Vehicle, VehicleMaintenance,
    DeliveryTrip,
    ReturnOrder, ReturnOrderItem,
    ContractFarming, SupplierEvaluation,
)
# I：財務擴充
from models.finance_ext import (
    PettyCashFund, PettyCashRecord,
    BankAccount, BankTransaction, Cheque,
    Budget, CashFlowPlan,
)
# J/K/L：合約、公告、行事曆、會議、客訴、品質追溯
from models.compliance import (
    Contract, ContractPaySchedule, ContractRenewal,
    Announcement,
    BusinessEvent, PromoCalendar,
    MeetingRecord, MeetingActionItem,
    CustomerComplaint,
    PesticideResidueTest, PesticideResidueTestItem,
)
# M/N：全球市場情報 + 定價引擎
from models.market_intel import (
    MarketPriceSource, MarketPriceData, MarketPriceAlert,
    CompetitorProfile, CompetitorPrice,
    GlobalTradeStatistics,
    WeatherAlert,
    FreightIndex, SupplyDemandIndicator,
    GlobalBuyerDirectory,
    PriceList, PriceListItem, PricingRule,
)
# O：KPI + 儀表板配置 + 自訂報表
from models.kpi_dashboard import (
    KPIDefinition, KPIValue,
    DashboardConfig,
    SavedReport,
)
# WP2：QC 品質管理強化
from models.qc_enhanced import (
    QCSamplingRule, QCInspection, QCPhoto, QCScoreCard,
    ChannelQCStandard, ProcessingStepLog, TemperatureLog,
    FactoryAutomationLog, ShelfLifePrediction,
)
