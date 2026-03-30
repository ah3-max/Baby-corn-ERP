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
from models.customer import Customer
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
# WP2：QC 品質管理強化
from models.qc_enhanced import (
    QCSamplingRule, QCInspection, QCPhoto, QCScoreCard,
    ChannelQCStandard, ProcessingStepLog, TemperatureLog,
    FactoryAutomationLog, ShelfLifePrediction,
)
