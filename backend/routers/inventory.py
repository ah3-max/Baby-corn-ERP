"""
台灣庫存管理 API

倉庫管理：
  GET    /inventory/warehouses          - 倉庫列表
  POST   /inventory/warehouses          - 新增倉庫
  PUT    /inventory/warehouses/:id      - 編輯倉庫
  GET    /inventory/warehouses/:id/locations     - 庫位列表
  POST   /inventory/warehouses/:id/locations     - 新增庫位

庫存批次：
  GET    /inventory/lots                - 庫存列表（FIFO 排序）
  POST   /inventory/lots                - 入庫
  GET    /inventory/lots/:id            - 批次詳情
  POST   /inventory/lots/:id/scrap      - 報廢
  POST   /inventory/lots/:id/adjust     - 調整庫存

統計：
  GET    /inventory/summary             - 庫存總覽統計
"""
from uuid import UUID
from typing import List, Optional
from decimal import Decimal
from datetime import datetime, date, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func

from database import get_db
from models.user import User
from models.batch import Batch
from models.inventory import Warehouse, WarehouseLocation, InventoryLot, InventoryTransaction
from utils.dependencies import check_permission
from pydantic import BaseModel

router = APIRouter(prefix="/inventory", tags=["台灣庫存管理"])


# ─── Schemas ────────────────────────────────────────

class WarehouseCreate(BaseModel):
    name:    str
    address: Optional[str] = None
    notes:   Optional[str] = None

class WarehouseUpdate(BaseModel):
    name:      Optional[str] = None
    address:   Optional[str] = None
    notes:     Optional[str] = None
    is_active: Optional[bool] = None

class WarehouseOut(BaseModel):
    id:        str
    name:      str
    address:   Optional[str]
    notes:     Optional[str]
    is_active: bool
    class Config: from_attributes = True

class LocationCreate(BaseModel):
    name:  str
    notes: Optional[str] = None

class LocationOut(BaseModel):
    id:           str
    warehouse_id: str
    name:         str
    notes:        Optional[str]
    is_active:    bool
    class Config: from_attributes = True

class LotCreate(BaseModel):
    batch_id:          str
    warehouse_id:      str
    location_id:       Optional[str] = None
    spec:              Optional[str] = None
    received_date:     date
    initial_weight_kg: Decimal
    initial_boxes:     Optional[int] = None
    notes:             Optional[str] = None
    import_type:            Optional[str]  = None
    customs_declaration_no: Optional[str]  = None
    customs_clearance_date: Optional[date] = None
    inspection_result:      Optional[str]  = None
    received_by:            Optional[str]  = None
    shipment_id:            Optional[str]  = None
    # 報關費用欄位
    arrival_weight_kg:      Optional[Decimal] = None   # 實際到貨重量
    customs_fee_twd:        Optional[Decimal] = None   # 報關費
    quarantine_fee_twd:     Optional[Decimal] = None   # 檢疫費
    import_tax_twd:         Optional[Decimal] = None   # 關稅
    cold_chain_fee_twd:     Optional[Decimal] = None   # 冷鏈物流費
    tw_transport_fee_twd:   Optional[Decimal] = None   # 台灣內陸運費

class ScrapCreate(BaseModel):
    weight_kg: Decimal
    reason:    str

class AdjustCreate(BaseModel):
    weight_kg: Decimal   # 正數增加，負數減少
    boxes:     Optional[int] = None
    reason:    str

class TransactionOut(BaseModel):
    id:         str
    txn_type:   str
    weight_kg:  float
    boxes:      Optional[int]
    reference:  Optional[str]
    reason:     Optional[str]
    created_at: datetime
    class Config: from_attributes = True

class BatchSimple(BaseModel):
    id:       str
    batch_no: str
    status:   str
    class Config: from_attributes = True

class LotOut(BaseModel):
    id:                 str
    lot_no:             str
    batch_id:           str
    batch:              Optional[BatchSimple]
    warehouse_id:       str
    warehouse:          Optional[WarehouseOut]
    location_id:        Optional[str]
    location:           Optional[LocationOut]
    spec:               Optional[str]
    received_date:      date
    initial_weight_kg:  float
    initial_boxes:      Optional[int]
    current_weight_kg:  float
    current_boxes:      Optional[int]
    shipped_weight_kg:  float
    shipped_boxes:      Optional[int]
    scrapped_weight_kg: float
    status:             str
    notes:              Optional[str]
    age_days:           int          # 庫齡（動態計算）
    created_at:         datetime
    transactions:       List[TransactionOut] = []
    import_type:            Optional[str]  = None
    customs_declaration_no: Optional[str]  = None
    customs_clearance_date: Optional[date] = None
    inspection_result:      Optional[str]  = None
    received_by:            Optional[str]  = None
    shipment_id:            Optional[str]  = None
    arrival_weight_kg:      Optional[float] = None
    customs_fee_twd:        Optional[float] = None
    quarantine_fee_twd:     Optional[float] = None
    import_tax_twd:         Optional[float] = None
    cold_chain_fee_twd:     Optional[float] = None
    tw_transport_fee_twd:   Optional[float] = None
    class Config: from_attributes = True


# ─── 工具函式 ─────────────────────────────────────────

def _generate_lot_no(db: Session) -> str:
    date_str = date.today().strftime("%Y%m%d")
    prefix   = f"LOT-{date_str}-"
    count    = db.query(func.count(InventoryLot.id)).filter(
        InventoryLot.lot_no.like(f"{prefix}%")
    ).scalar()
    return f"{prefix}{str(count + 1).zfill(3)}"


def _lot_to_out(lot: InventoryLot) -> LotOut:
    age = (date.today() - lot.received_date).days
    return LotOut(
        id                 = str(lot.id),
        lot_no             = lot.lot_no,
        batch_id           = str(lot.batch_id),
        batch              = BatchSimple(
            id=str(lot.batch.id), batch_no=lot.batch.batch_no, status=lot.batch.status
        ) if lot.batch else None,
        warehouse_id       = str(lot.warehouse_id),
        warehouse          = WarehouseOut(
            id=str(lot.warehouse.id), name=lot.warehouse.name,
            address=lot.warehouse.address, notes=lot.warehouse.notes,
            is_active=lot.warehouse.is_active,
        ) if lot.warehouse else None,
        location_id        = str(lot.location_id) if lot.location_id else None,
        location           = LocationOut(
            id=str(lot.location.id), warehouse_id=str(lot.location.warehouse_id),
            name=lot.location.name, notes=lot.location.notes, is_active=lot.location.is_active,
        ) if lot.location else None,
        spec               = lot.spec,
        received_date      = lot.received_date,
        initial_weight_kg  = float(lot.initial_weight_kg),
        initial_boxes      = lot.initial_boxes,
        current_weight_kg  = float(lot.current_weight_kg),
        current_boxes      = lot.current_boxes,
        shipped_weight_kg  = float(lot.shipped_weight_kg),
        shipped_boxes      = lot.shipped_boxes,
        scrapped_weight_kg = float(lot.scrapped_weight_kg),
        status             = lot.status,
        notes              = lot.notes,
        age_days           = age,
        created_at         = lot.created_at,
        import_type            = lot.import_type,
        customs_declaration_no = lot.customs_declaration_no,
        customs_clearance_date = lot.customs_clearance_date,
        inspection_result      = lot.inspection_result,
        received_by            = lot.received_by,
        shipment_id            = str(lot.shipment_id) if lot.shipment_id else None,
        arrival_weight_kg      = float(lot.arrival_weight_kg) if lot.arrival_weight_kg else None,
        customs_fee_twd        = float(lot.customs_fee_twd) if lot.customs_fee_twd else None,
        quarantine_fee_twd     = float(lot.quarantine_fee_twd) if lot.quarantine_fee_twd else None,
        import_tax_twd         = float(lot.import_tax_twd) if lot.import_tax_twd else None,
        cold_chain_fee_twd     = float(lot.cold_chain_fee_twd) if lot.cold_chain_fee_twd else None,
        tw_transport_fee_twd   = float(lot.tw_transport_fee_twd) if lot.tw_transport_fee_twd else None,
        transactions       = [
            TransactionOut(
                id=str(t.id), txn_type=t.txn_type,
                weight_kg=float(t.weight_kg), boxes=t.boxes,
                reference=t.reference, reason=t.reason, created_at=t.created_at,
            ) for t in (lot.transactions or [])
        ],
    )


# ─── 倉庫管理 ─────────────────────────────────────────

def _wh_to_out(w: Warehouse) -> WarehouseOut:
    """倉庫 ORM → WarehouseOut（UUID 轉 str）"""
    return WarehouseOut(
        id=str(w.id), name=w.name, address=w.address,
        notes=w.notes, is_active=w.is_active,
    )


def _loc_to_out(loc: WarehouseLocation) -> LocationOut:
    """庫位 ORM → LocationOut（UUID 轉 str）"""
    return LocationOut(
        id=str(loc.id), warehouse_id=str(loc.warehouse_id),
        name=loc.name, notes=loc.notes, is_active=loc.is_active,
    )


@router.get("/warehouses", response_model=List[WarehouseOut])
def list_warehouses(
    db: Session = Depends(get_db),
    _:  User    = Depends(check_permission("stock", "read")),
):
    rows = db.query(Warehouse).filter(Warehouse.is_active == True).order_by(Warehouse.name).all()
    return [_wh_to_out(w) for w in rows]


@router.post("/warehouses", response_model=WarehouseOut, status_code=201)
def create_warehouse(
    payload: WarehouseCreate,
    db:      Session = Depends(get_db),
    _:       User    = Depends(check_permission("stock", "create")),
):
    w = Warehouse(**payload.model_dump())
    db.add(w)
    db.commit()
    db.refresh(w)
    return _wh_to_out(w)


@router.put("/warehouses/{warehouse_id}", response_model=WarehouseOut)
def update_warehouse(
    warehouse_id: UUID,
    payload:      WarehouseUpdate,
    db:           Session = Depends(get_db),
    _:            User    = Depends(check_permission("stock", "update")),
):
    w = db.query(Warehouse).filter(Warehouse.id == warehouse_id).first()
    if not w:
        raise HTTPException(status_code=404, detail="倉庫不存在")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(w, k, v)
    db.commit()
    db.refresh(w)
    return _wh_to_out(w)


@router.get("/warehouses/{warehouse_id}/locations", response_model=List[LocationOut])
def list_locations(
    warehouse_id: UUID,
    db:           Session = Depends(get_db),
    _:            User    = Depends(check_permission("stock", "read")),
):
    rows = (
        db.query(WarehouseLocation)
        .filter(WarehouseLocation.warehouse_id == warehouse_id, WarehouseLocation.is_active == True)
        .order_by(WarehouseLocation.name)
        .all()
    )
    return [_loc_to_out(loc) for loc in rows]


@router.post("/warehouses/{warehouse_id}/locations", response_model=LocationOut, status_code=201)
def create_location(
    warehouse_id: UUID,
    payload:      LocationCreate,
    db:           Session = Depends(get_db),
    _:            User    = Depends(check_permission("stock", "create")),
):
    if not db.query(Warehouse).filter(Warehouse.id == warehouse_id).first():
        raise HTTPException(status_code=404, detail="倉庫不存在")
    loc = WarehouseLocation(warehouse_id=warehouse_id, **payload.model_dump())
    db.add(loc)
    db.commit()
    db.refresh(loc)
    return _loc_to_out(loc)


# ─── 庫存批次 ─────────────────────────────────────────

@router.get("/lots", response_model=List[LotOut])
def list_lots(
    warehouse_id: Optional[UUID] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    batch_id:      Optional[UUID] = Query(None),
    db:            Session = Depends(get_db),
    _:             User    = Depends(check_permission("stock", "read")),
):
    """FIFO 排序（依入庫日由舊到新）"""
    q = (
        db.query(InventoryLot)
        .options(
            joinedload(InventoryLot.batch),
            joinedload(InventoryLot.warehouse),
            joinedload(InventoryLot.location),
            joinedload(InventoryLot.transactions),
        )
    )
    if warehouse_id:
        q = q.filter(InventoryLot.warehouse_id == warehouse_id)
    if status_filter and status_filter != "all":
        q = q.filter(InventoryLot.status == status_filter)
    elif not status_filter:
        # 預設只顯示 active（非已耗盡/報廢）
        q = q.filter(InventoryLot.status.in_(["active", "low_stock"]))
    # status="all" 時不加任何 status 篩選，顯示全部
    if batch_id:
        q = q.filter(InventoryLot.batch_id == batch_id)

    lots = q.order_by(InventoryLot.received_date.asc(), InventoryLot.created_at.asc()).all()
    return [_lot_to_out(lot) for lot in lots]


@router.post("/lots", response_model=LotOut, status_code=201)
def create_lot(
    payload:      LotCreate,
    db:           Session = Depends(get_db),
    current_user: User    = Depends(check_permission("stock", "create")),
):
    """入庫"""
    batch = db.query(Batch).filter(Batch.id == payload.batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="批次不存在")
    if not db.query(Warehouse).filter(Warehouse.id == payload.warehouse_id).first():
        raise HTTPException(status_code=404, detail="倉庫不存在")

    lot_no = _generate_lot_no(db)
    lot = InventoryLot(
        lot_no             = lot_no,
        batch_id           = payload.batch_id,
        warehouse_id       = payload.warehouse_id,
        location_id        = payload.location_id,
        spec               = payload.spec,
        received_date      = payload.received_date,
        initial_weight_kg  = payload.initial_weight_kg,
        initial_boxes      = payload.initial_boxes,
        current_weight_kg  = payload.initial_weight_kg,
        current_boxes      = payload.initial_boxes,
        shipped_weight_kg  = 0,
        shipped_boxes      = 0,
        scrapped_weight_kg = 0,
        status             = "active",
        notes              = payload.notes,
        import_type            = payload.import_type,
        customs_declaration_no = payload.customs_declaration_no,
        customs_clearance_date = payload.customs_clearance_date,
        inspection_result      = payload.inspection_result,
        received_by            = payload.received_by,
        shipment_id            = UUID(payload.shipment_id) if payload.shipment_id else None,
        arrival_weight_kg      = payload.arrival_weight_kg,
        customs_fee_twd        = payload.customs_fee_twd,
        quarantine_fee_twd     = payload.quarantine_fee_twd,
        import_tax_twd         = payload.import_tax_twd,
        cold_chain_fee_twd     = payload.cold_chain_fee_twd,
        tw_transport_fee_twd   = payload.tw_transport_fee_twd,
        created_by         = current_user.id,
    )
    db.add(lot)
    db.flush()

    # 記錄入庫異動
    db.add(InventoryTransaction(
        lot_id     = lot.id,
        txn_type   = "in",
        weight_kg  = payload.initial_weight_kg,
        boxes      = payload.initial_boxes,
        reason     = "入庫",
        created_by = current_user.id,
    ))

    # ─── 自動建立進口成本事件（報關費、檢疫費、關稅、冷鏈費、內陸運費）───
    from services.cost_automation import create_cost_event
    cost_items = [
        (payload.customs_fee_twd,      "tw_customs",   "customs_duty",     "報關費"),
        (payload.quarantine_fee_twd,   "tw_customs",   "quarantine_fee",   "檢疫費"),
        (payload.import_tax_twd,       "tw_customs",   "import_tax",       "進口關稅"),
        (payload.cold_chain_fee_twd,   "tw_logistics", "cold_chain_fee",   "冷鏈物流費"),
        (payload.tw_transport_fee_twd, "tw_logistics", "tw_transport_fee", "台灣內陸運費"),
    ]
    for amount, layer, cost_type, desc in cost_items:
        if amount and amount > 0:
            create_cost_event(
                db=db,
                batch_id=UUID(payload.batch_id),
                cost_layer=layer,
                cost_type=cost_type,
                description_zh=f"{desc}（{lot.lot_no}）",
                amount_twd=amount,
                quantity=payload.initial_weight_kg,
                unit_label="kg",
                notes=f"入庫批號: {lot.lot_no}",
                recorded_by=current_user.id,
                auto_source="lot_creation",
            )

    db.commit()
    return _lot_to_out(
        db.query(InventoryLot)
        .options(
            joinedload(InventoryLot.batch), joinedload(InventoryLot.warehouse),
            joinedload(InventoryLot.location), joinedload(InventoryLot.transactions),
        )
        .filter(InventoryLot.id == lot.id).first()
    )


@router.get("/lots/{lot_id}", response_model=LotOut)
def get_lot(
    lot_id: UUID,
    db:     Session = Depends(get_db),
    _:      User    = Depends(check_permission("stock", "read")),
):
    lot = (
        db.query(InventoryLot)
        .options(
            joinedload(InventoryLot.batch), joinedload(InventoryLot.warehouse),
            joinedload(InventoryLot.location), joinedload(InventoryLot.transactions),
        )
        .filter(InventoryLot.id == lot_id).first()
    )
    if not lot:
        raise HTTPException(status_code=404, detail="庫存批次不存在")
    return _lot_to_out(lot)


@router.post("/lots/{lot_id}/scrap", response_model=LotOut)
def scrap_lot(
    lot_id:       UUID,
    payload:      ScrapCreate,
    db:           Session = Depends(get_db),
    current_user: User    = Depends(check_permission("stock", "update")),
):
    """報廢部分或全部庫存"""
    lot = db.query(InventoryLot).filter(InventoryLot.id == lot_id).first()
    if not lot:
        raise HTTPException(status_code=404, detail="庫存批次不存在")
    if float(payload.weight_kg) > float(lot.current_weight_kg):
        raise HTTPException(status_code=400, detail=f"報廢量不能超過目前庫存 {float(lot.current_weight_kg):.1f} kg")

    lot.current_weight_kg  = float(lot.current_weight_kg) - float(payload.weight_kg)
    lot.scrapped_weight_kg = float(lot.scrapped_weight_kg) + float(payload.weight_kg)
    if float(lot.current_weight_kg) <= 0:
        lot.status = "scrapped"

    db.add(InventoryTransaction(
        lot_id     = lot.id,
        txn_type   = "scrap",
        weight_kg  = payload.weight_kg,
        reason     = payload.reason,
        created_by = current_user.id,
    ))
    db.commit()
    return _lot_to_out(
        db.query(InventoryLot)
        .options(
            joinedload(InventoryLot.batch), joinedload(InventoryLot.warehouse),
            joinedload(InventoryLot.location), joinedload(InventoryLot.transactions),
        )
        .filter(InventoryLot.id == lot.id).first()
    )


@router.post("/lots/{lot_id}/adjust", response_model=LotOut)
def adjust_lot(
    lot_id:       UUID,
    payload:      AdjustCreate,
    db:           Session = Depends(get_db),
    current_user: User    = Depends(check_permission("stock", "update")),
):
    """手動調整庫存（正數增加、負數減少）"""
    lot = db.query(InventoryLot).filter(InventoryLot.id == lot_id).first()
    if not lot:
        raise HTTPException(status_code=404, detail="庫存批次不存在")
    new_weight = float(lot.current_weight_kg) + float(payload.weight_kg)
    if new_weight < 0:
        raise HTTPException(status_code=400, detail="調整後庫存不能為負數")

    lot.current_weight_kg = new_weight
    if payload.boxes is not None and lot.current_boxes is not None:
        lot.current_boxes = lot.current_boxes + payload.boxes
    if float(lot.current_weight_kg) <= 0:
        lot.status = "depleted"
    elif float(lot.current_weight_kg) / float(lot.initial_weight_kg) < 0.2:
        lot.status = "low_stock"
    else:
        lot.status = "active"

    db.add(InventoryTransaction(
        lot_id     = lot.id,
        txn_type   = "adjust",
        weight_kg  = payload.weight_kg,
        boxes      = payload.boxes,
        reason     = payload.reason,
        created_by = current_user.id,
    ))
    db.commit()
    return _lot_to_out(
        db.query(InventoryLot)
        .options(
            joinedload(InventoryLot.batch), joinedload(InventoryLot.warehouse),
            joinedload(InventoryLot.location), joinedload(InventoryLot.transactions),
        )
        .filter(InventoryLot.id == lot.id).first()
    )


# ─── 統計總覽 ─────────────────────────────────────────

@router.get("/summary")
def get_summary(
    db: Session = Depends(get_db),
    _:  User    = Depends(check_permission("stock", "read")),
):
    """庫存總覽統計"""
    active_lots = (
        db.query(InventoryLot)
        .filter(InventoryLot.status.in_(["active", "low_stock"]))
        .all()
    )
    today = date.today()

    total_weight = sum(float(l.current_weight_kg) for l in active_lots)
    total_boxes  = sum((l.current_boxes or 0) for l in active_lots)
    lot_count    = len(active_lots)

    # 庫齡分布（玉米筍保存期限短，以 7/14 天為門檻）
    age_ok      = sum(1 for l in active_lots if (today - l.received_date).days <= 7)
    age_warning = sum(1 for l in active_lots if 7 < (today - l.received_date).days <= 14)
    age_alert   = sum(1 for l in active_lots if (today - l.received_date).days > 14)

    return {
        "total_weight_kg": round(total_weight, 2),
        "total_boxes":     total_boxes,
        "lot_count":       lot_count,
        "age_ok":          age_ok,       # ≤7 天（新鮮）
        "age_warning":     age_warning,  # 8–14 天（注意）
        "age_alert":       age_alert,    # >14 天（危險）
    }
