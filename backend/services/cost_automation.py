"""
成本自動化服務 — WP1-1

提供自動建立 CostEvent 和自動重算 BatchCostSheet 的共用函數。
各路由在關鍵操作時呼叫這些函數，確保成本數據自動維護。
"""
from decimal import Decimal
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import func

from models.cost import CostEvent, BatchCostSheet, BatchCostSheetItem
from models.batch import Batch
from models.sales import SalesOrderItem
from models.daily_sale import DailySaleItem


def get_system_exchange_rate(db: Session) -> Decimal:
    """從系統設定取得預設匯率（THB→TWD）"""
    from models.system import SystemSetting
    setting = db.query(SystemSetting).filter(SystemSetting.key == "default_exchange_rate").first()
    if setting and setting.value and isinstance(setting.value, dict):
        return Decimal(str(setting.value.get("THB_TWD", "0.92")))
    return Decimal("0.92")


def create_cost_event(
    db: Session,
    batch_id: UUID,
    cost_layer: str,
    cost_type: str,
    description_zh: str,
    amount_thb: Optional[Decimal] = None,
    amount_twd: Optional[Decimal] = None,
    exchange_rate: Optional[Decimal] = None,
    quantity: Optional[Decimal] = None,
    unit_cost: Optional[Decimal] = None,
    unit_label: Optional[str] = None,
    notes: Optional[str] = None,
    recorded_by: Optional[UUID] = None,
    auto_source: Optional[str] = None,
) -> CostEvent:
    """建立成本事件並自動重算 BatchCostSheet

    參數:
        auto_source: 自動化來源標記，如 'po_arrival', 'lot_creation', 'shipment'
    """
    # 如果只有 THB 金額，自動計算 TWD
    if amount_thb and not amount_twd and exchange_rate:
        amount_twd = amount_thb * exchange_rate

    event = CostEvent(
        batch_id=batch_id,
        cost_layer=cost_layer,
        cost_type=cost_type,
        description_zh=description_zh,
        amount_thb=amount_thb,
        amount_twd=amount_twd,
        exchange_rate=exchange_rate,
        quantity=quantity,
        unit_cost=unit_cost,
        unit_label=unit_label,
        notes=f"[自動] {auto_source}: {notes}" if auto_source else notes,
        recorded_by=recorded_by,
    )
    db.add(event)
    db.flush()  # 取得 event.id

    # 自動重算成本彙總
    refresh_cost_sheet(db, batch_id)

    return event


def refresh_cost_sheet(db: Session, batch_id: UUID, exchange_rate: Optional[Decimal] = None):
    """重新計算並更新 BatchCostSheet 快取

    從 CostEvent 帳本重新計算七層成本彙總，
    並更新銷售收入與利潤數據。
    """
    batch = db.query(Batch).filter(Batch.id == batch_id).first()
    if not batch:
        return

    if not exchange_rate:
        exchange_rate = get_system_exchange_rate(db)

    # 取得所有成本事件
    events = (
        db.query(CostEvent)
        .filter(CostEvent.batch_id == batch_id)
        .order_by(CostEvent.recorded_at)
        .all()
    )

    # 逐層彙總（全部轉 TWD）
    layer_totals = {
        "material": Decimal("0"),
        "processing": Decimal("0"),
        "th_logistics": Decimal("0"),
        "freight": Decimal("0"),
        "tw_customs": Decimal("0"),
        "tw_logistics": Decimal("0"),
        "market": Decimal("0"),
    }

    for e in events:
        twd = Decimal("0")
        if e.amount_twd:
            twd = e.amount_twd
        elif e.amount_thb:
            rate = e.exchange_rate if e.exchange_rate else exchange_rate
            twd = e.amount_thb * rate
        if e.cost_layer in layer_totals:
            layer_totals[e.cost_layer] += twd

    total_cost = sum(layer_totals.values())
    weight = batch.current_weight if batch.current_weight and batch.current_weight > 0 else Decimal("1")
    cost_per_kg = total_cost / weight

    # 銷售收入
    so_revenue = db.query(
        func.coalesce(func.sum(SalesOrderItem.total_amount_twd), 0)
    ).filter(SalesOrderItem.batch_id == batch_id).scalar()
    ds_revenue = db.query(
        func.coalesce(func.sum(DailySaleItem.total_amount_twd), 0)
    ).filter(DailySaleItem.batch_id == batch_id).scalar()
    total_revenue = Decimal(str(so_revenue)) + Decimal(str(ds_revenue))

    # 已售重量
    so_sold = db.query(
        func.coalesce(func.sum(SalesOrderItem.quantity_kg), 0)
    ).filter(SalesOrderItem.batch_id == batch_id).scalar()
    ds_sold = db.query(
        func.coalesce(func.sum(DailySaleItem.quantity_kg), 0)
    ).filter(DailySaleItem.batch_id == batch_id).scalar()
    total_sold = Decimal(str(so_sold)) + Decimal(str(ds_sold))
    avg_sale_price = total_revenue / total_sold if total_sold > 0 else Decimal("0")

    # 利潤
    profit = total_revenue - total_cost
    profit_per_kg = profit / total_sold if total_sold > 0 else Decimal("0")
    margin_pct = (profit / total_revenue * 100) if total_revenue > 0 else Decimal("0")

    # 更新或建立 BatchCostSheet
    sheet = db.query(BatchCostSheet).filter(BatchCostSheet.batch_id == batch_id).first()
    if not sheet:
        sheet = BatchCostSheet(batch_id=batch_id)
        db.add(sheet)

    sheet.layer1_material_twd = layer_totals["material"]
    sheet.layer2_processing_twd = layer_totals["processing"]
    sheet.layer3_th_logistics_twd = layer_totals["th_logistics"]
    sheet.layer4_freight_twd = layer_totals["freight"]
    sheet.layer5_tw_customs_twd = layer_totals["tw_customs"]
    sheet.layer6_tw_logistics_twd = layer_totals["tw_logistics"]
    sheet.layer7_market_twd = layer_totals["market"]
    sheet.total_cost_twd = total_cost
    sheet.weight_kg = batch.current_weight
    sheet.cost_per_kg_twd = cost_per_kg
    sheet.total_revenue_twd = total_revenue
    sheet.total_sold_kg = total_sold
    sheet.avg_sale_price_twd = avg_sale_price
    sheet.profit_per_kg_twd = profit_per_kg
    sheet.margin_pct = margin_pct
    sheet.exchange_rate = exchange_rate
    sheet.cost_event_count = len(events)
    sheet.last_calculated_at = datetime.utcnow()

    db.flush()


def get_batch_cost_per_kg(db: Session, batch_id: UUID) -> Decimal:
    """取得批次的每公斤成本（用於銷售時鎖定成本快照）"""
    sheet = db.query(BatchCostSheet).filter(BatchCostSheet.batch_id == batch_id).first()
    if sheet and sheet.cost_per_kg_twd:
        return sheet.cost_per_kg_twd

    # 若無快取，即時計算
    exchange_rate = get_system_exchange_rate(db)
    events = db.query(CostEvent).filter(CostEvent.batch_id == batch_id).all()
    total_twd = Decimal("0")
    for e in events:
        if e.amount_twd:
            total_twd += e.amount_twd
        elif e.amount_thb:
            rate = e.exchange_rate if e.exchange_rate else exchange_rate
            total_twd += e.amount_thb * rate

    batch = db.query(Batch).filter(Batch.id == batch_id).first()
    if batch and batch.current_weight and batch.current_weight > 0:
        return total_twd / batch.current_weight
    return Decimal("0")
