"""
成本管理 API（基於 CostEvent append-only 帳本）
GET    /batches/{batch_id}/costs         - 取得批次所有成本事件
POST   /batches/{batch_id}/costs         - 新增成本事件
POST   /batches/{batch_id}/costs/{id}/void - 沖銷成本事件
GET    /batches/{batch_id}/cost-summary  - 取得批次完整落地成本計算
"""
from uuid import UUID
from typing import List, Optional
from decimal import Decimal
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel

from database import get_db
from models.user import User
from models.batch import Batch
from models.cost import CostEvent, BatchCostSheet
from models.purchase import PurchaseOrder
from models.shipment import Shipment, ShipmentBatch
from models.sales import SalesOrderItem
from models.daily_sale import DailySaleItem
from utils.dependencies import check_permission

router = APIRouter(tags=["成本管理"])


# ─── Schemas ─────────────────────────────────────────

class CostEventCreate(BaseModel):
    cost_layer:     str                     # material/processing/th_logistics/freight/tw_customs/tw_logistics/market
    cost_type:      str                     # purchase_price, oem_fee, freight_sea ...
    description_zh: Optional[str] = None
    amount_thb:     Optional[Decimal] = None
    amount_twd:     Optional[Decimal] = None
    exchange_rate:  Optional[float] = None
    quantity:       Optional[Decimal] = None
    unit_cost:      Optional[Decimal] = None
    unit_label:     Optional[str] = None
    notes:          Optional[str] = None


class CostEventOut(BaseModel):
    id:              str
    batch_id:        str
    cost_layer:      str
    cost_type:       str
    description_zh:  Optional[str]
    amount_thb:      Optional[float]
    amount_twd:      Optional[float]
    exchange_rate:   Optional[float]
    quantity:        Optional[float]
    unit_cost:       Optional[float]
    unit_label:      Optional[str]
    is_adjustment:   bool
    adjustment_ref:  Optional[str]
    notes:           Optional[str]
    recorded_at:     datetime

    class Config:
        from_attributes = True


class BatchCostSummary(BaseModel):
    batch_id:           str
    batch_no:           str
    initial_weight_kg:  float
    current_weight_kg:  float

    # 七層成本（TWD）
    layer_material_twd:     float
    layer_processing_twd:   float
    layer_th_logistics_twd: float
    layer_freight_twd:      float
    layer_tw_customs_twd:   float
    layer_tw_logistics_twd: float
    layer_market_twd:       float

    # 彙總
    total_cost_twd:     float
    cost_per_kg_twd:    float

    # 銷售
    sales_revenue_twd:  float
    gross_profit_twd:   float
    gross_margin_pct:   Optional[float]

    # 成本事件明細
    cost_events:        List[CostEventOut]
    event_count:        int
    exchange_rate:      float


# ─── 工具函式 ─────────────────────────────────────────

def _event_to_out(e: CostEvent) -> CostEventOut:
    return CostEventOut(
        id=str(e.id), batch_id=str(e.batch_id),
        cost_layer=e.cost_layer, cost_type=e.cost_type,
        description_zh=e.description_zh,
        amount_thb=float(e.amount_thb) if e.amount_thb else None,
        amount_twd=float(e.amount_twd) if e.amount_twd else None,
        exchange_rate=float(e.exchange_rate) if e.exchange_rate else None,
        quantity=float(e.quantity) if e.quantity else None,
        unit_cost=float(e.unit_cost) if e.unit_cost else None,
        unit_label=e.unit_label,
        is_adjustment=e.is_adjustment,
        adjustment_ref=str(e.adjustment_ref) if e.adjustment_ref else None,
        notes=e.notes, recorded_at=e.recorded_at,
    )


LAYER_MAP = {
    "material": "layer_material_twd",
    "processing": "layer_processing_twd",
    "th_logistics": "layer_th_logistics_twd",
    "freight": "layer_freight_twd",
    "tw_customs": "layer_tw_customs_twd",
    "tw_logistics": "layer_tw_logistics_twd",
    "market": "layer_market_twd",
}


# ─── Routes ──────────────────────────────────────────

@router.get("/batches/{batch_id}/costs", response_model=List[CostEventOut])
def list_cost_events(
    batch_id: UUID,
    db:       Session = Depends(get_db),
    _:        User = Depends(check_permission("cost", "view")),
):
    batch = db.query(Batch).filter(Batch.id == batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="批次不存在")
    events = (
        db.query(CostEvent)
        .filter(CostEvent.batch_id == batch_id)
        .order_by(CostEvent.recorded_at)
        .all()
    )
    return [_event_to_out(e) for e in events]


@router.post("/batches/{batch_id}/costs", response_model=CostEventOut, status_code=status.HTTP_201_CREATED)
def create_cost_event(
    batch_id:     UUID,
    payload:      CostEventCreate,
    db:           Session = Depends(get_db),
    current_user: User = Depends(check_permission("cost", "create")),
):
    batch = db.query(Batch).filter(Batch.id == batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="批次不存在")
    if not payload.amount_thb and not payload.amount_twd:
        raise HTTPException(status_code=400, detail="amount_thb 和 amount_twd 至少填一個")

    event = CostEvent(
        batch_id=batch_id,
        cost_layer=payload.cost_layer,
        cost_type=payload.cost_type,
        description_zh=payload.description_zh,
        amount_thb=payload.amount_thb,
        amount_twd=payload.amount_twd,
        exchange_rate=payload.exchange_rate,
        quantity=payload.quantity,
        unit_cost=payload.unit_cost,
        unit_label=payload.unit_label,
        notes=payload.notes,
        recorded_by=current_user.id,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return _event_to_out(event)


@router.post("/batches/{batch_id}/costs/{event_id}/void", response_model=CostEventOut, status_code=status.HTTP_201_CREATED)
def void_cost_event(
    batch_id:     UUID,
    event_id:     UUID,
    db:           Session = Depends(get_db),
    current_user: User = Depends(check_permission("cost", "edit")),
):
    """沖銷成本事件（新增一筆反向記錄，不刪除原始記錄）"""
    original = db.query(CostEvent).filter(
        CostEvent.id == event_id, CostEvent.batch_id == batch_id,
    ).first()
    if not original:
        raise HTTPException(status_code=404, detail="成本事件不存在")
    if original.is_adjustment:
        raise HTTPException(status_code=400, detail="沖銷記錄不可再沖銷")

    void_event = CostEvent(
        batch_id=batch_id,
        cost_layer=original.cost_layer,
        cost_type=original.cost_type,
        description_zh=f"[沖銷] {original.description_zh or ''}",
        amount_thb=-original.amount_thb if original.amount_thb else None,
        amount_twd=-original.amount_twd if original.amount_twd else None,
        exchange_rate=original.exchange_rate,
        is_adjustment=True,
        adjustment_ref=original.id,
        notes=f"沖銷原始記錄 {original.id}",
        recorded_by=current_user.id,
    )
    db.add(void_event)
    db.commit()
    db.refresh(void_event)
    return _event_to_out(void_event)


@router.get("/costs/recent-values")
def get_recent_cost_values(
    db: Session = Depends(get_db),
    _: User = Depends(check_permission("cost", "view")),
):
    """
    取得每個成本類型最近一次使用的金額，用於新增成本時自動帶入建議值。
    回傳格式：{ "cost_layer__cost_type": { amount_thb, amount_twd, unit_cost, unit_label, quantity, exchange_rate, description_zh } }
    """
    # subquery：取每個 (cost_layer, cost_type) 組合最新的記錄時間
    subq = (
        db.query(
            CostEvent.cost_type,
            CostEvent.cost_layer,
            func.max(CostEvent.recorded_at).label("latest_at"),
        )
        .filter(CostEvent.is_adjustment == False)
        .group_by(CostEvent.cost_type, CostEvent.cost_layer)
        .subquery()
    )

    events = (
        db.query(CostEvent)
        .join(
            subq,
            (CostEvent.cost_type == subq.c.cost_type)
            & (CostEvent.cost_layer == subq.c.cost_layer)
            & (CostEvent.recorded_at == subq.c.latest_at)
            & (CostEvent.is_adjustment == False),
        )
        .all()
    )

    return {
        f"{e.cost_layer}__{e.cost_type}": {
            "cost_layer":    e.cost_layer,
            "cost_type":     e.cost_type,
            "amount_thb":    float(e.amount_thb)    if e.amount_thb    else None,
            "amount_twd":    float(e.amount_twd)    if e.amount_twd    else None,
            "unit_cost":     float(e.unit_cost)     if e.unit_cost     else None,
            "unit_label":    e.unit_label,
            "quantity":      float(e.quantity)      if e.quantity      else None,
            "exchange_rate": float(e.exchange_rate) if e.exchange_rate else None,
            "description_zh": e.description_zh,
        }
        for e in events
    }


@router.get("/batches/{batch_id}/cost-summary", response_model=BatchCostSummary)
def get_cost_summary(
    batch_id:      UUID,
    exchange_rate: float = 0.92,
    db:            Session = Depends(get_db),
    _:             User = Depends(check_permission("cost", "view")),
):
    """計算批次完整落地成本（基於 CostEvent 帳本）"""
    batch = db.query(Batch).filter(Batch.id == batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="批次不存在")

    events = (
        db.query(CostEvent)
        .filter(CostEvent.batch_id == batch_id)
        .order_by(CostEvent.recorded_at)
        .all()
    )

    # 逐層彙總（全部轉 TWD）
    layer_totals = {k: 0.0 for k in LAYER_MAP.keys()}
    for e in events:
        twd = 0.0
        if e.amount_twd:
            twd = float(e.amount_twd)
        elif e.amount_thb:
            rate = float(e.exchange_rate) if e.exchange_rate else exchange_rate
            twd = float(e.amount_thb) * rate
        layer_totals[e.cost_layer] = layer_totals.get(e.cost_layer, 0.0) + twd

    total_cost = sum(layer_totals.values())
    weight = float(batch.current_weight) if float(batch.current_weight) > 0 else 1
    cost_per_kg = total_cost / weight

    # 銷售收入（SalesOrderItem + DailySaleItem）
    so_revenue = db.query(
        func.coalesce(func.sum(SalesOrderItem.total_amount_twd), 0)
    ).filter(SalesOrderItem.batch_id == batch_id).scalar()
    ds_revenue = db.query(
        func.coalesce(func.sum(DailySaleItem.total_amount_twd), 0)
    ).filter(DailySaleItem.batch_id == batch_id).scalar()
    sales_revenue = float(so_revenue) + float(ds_revenue)

    gross_profit = sales_revenue - total_cost
    gross_margin = (gross_profit / sales_revenue * 100) if sales_revenue > 0 else None

    return BatchCostSummary(
        batch_id=str(batch.id),
        batch_no=batch.batch_no,
        initial_weight_kg=float(batch.initial_weight),
        current_weight_kg=float(batch.current_weight),
        layer_material_twd=round(layer_totals["material"], 2),
        layer_processing_twd=round(layer_totals["processing"], 2),
        layer_th_logistics_twd=round(layer_totals["th_logistics"], 2),
        layer_freight_twd=round(layer_totals["freight"], 2),
        layer_tw_customs_twd=round(layer_totals["tw_customs"], 2),
        layer_tw_logistics_twd=round(layer_totals["tw_logistics"], 2),
        layer_market_twd=round(layer_totals["market"], 2),
        total_cost_twd=round(total_cost, 2),
        cost_per_kg_twd=round(cost_per_kg, 2),
        sales_revenue_twd=round(sales_revenue, 2),
        gross_profit_twd=round(gross_profit, 2),
        gross_margin_pct=round(gross_margin, 1) if gross_margin is not None else None,
        cost_events=[_event_to_out(e) for e in events],
        event_count=len(events),
        exchange_rate=exchange_rate,
    )
