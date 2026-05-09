"""
全球定價引擎 API（N-03）+ 市場情報 API（M 段部分）

N-03  POST /pricing/calculate     — 動態定價計算
      POST /pricing/price-lists/  — 新增價目表
      GET  /pricing/price-lists/  — 查詢價目表

M     GET  /market/prices/        — 市場價格查詢
      POST /market/prices/        — 新增市場價格
      GET  /market/alerts/        — 價格告警清單
      GET  /market/freight/       — 運價指數
      POST /market/competitors/   — 新增競爭對手
      GET  /market/buyers/        — 全球買家資料庫
"""
import logging
from datetime import date
from decimal import Decimal
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
from models.market_intel import (
    MarketPriceSource, MarketPriceData, MarketPriceAlert,
    CompetitorProfile, CompetitorPrice,
    FreightIndex, GlobalBuyerDirectory,
    PriceList, PriceListItem, PricingRule,
)
from utils.dependencies import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(tags=["定價引擎與市場情報"])


# ═══════════════════════════════════════════════════
# N-03 動態定價計算
# ═══════════════════════════════════════════════════

class PricingRequest(BaseModel):
    customer_id:        Optional[UUID] = None
    product_type_id:    Optional[UUID] = None
    product_name:       str
    quantity_kg:        float
    currency:           str            = "TWD"
    incoterm:           Optional[str]  = None
    target_market:      Optional[str]  = None


@router.post("/pricing/calculate", summary="動態定價計算")
def calculate_price(
    payload: PricingRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    N-03 動態定價引擎：
    1. 取成本基礎（採購 + 加工 + 物流 + 關稅）
    2. 套用目標利潤率（預設 25%）
    3. 查詢適用定價規則（量折 / 客戶等級 / 季節）
    4. 與市場行情比較
    5. 底價檢查（低於底價需審核）
    """
    from models.product_type import ProductType
    from models.customer import Customer

    # 取適用價目表
    price_list_item = None
    if payload.product_type_id:
        active_pl = (
            db.query(PriceList)
            .filter(
                PriceList.status == "active",
                PriceList.currency_code == payload.currency,
                PriceList.effective_date <= date.today(),
            )
        )
        if payload.customer_id:
            active_pl = active_pl.filter(
                (PriceList.customer_id == payload.customer_id) |
                (PriceList.customer_id.is_(None))
            )
        pl = active_pl.order_by(PriceList.effective_date.desc()).first()
        if pl:
            price_list_item = (
                db.query(PriceListItem)
                .filter(
                    PriceListItem.price_list_id == pl.id,
                    PriceListItem.product_type_id == payload.product_type_id,
                )
                .first()
            )

    # 基礎售價（來自價目表或預設值）
    if price_list_item:
        base_price  = float(price_list_item.unit_price)
        floor_price = float(price_list_item.floor_price or 0)
    else:
        base_price  = 0.0
        floor_price = 0.0

    # 查詢適用定價規則
    rules = (
        db.query(PricingRule)
        .filter(
            PricingRule.is_active == True,
            (PricingRule.effective_date <= date.today()) | (PricingRule.effective_date.is_(None)),
            (PricingRule.expiry_date >= date.today()) | (PricingRule.expiry_date.is_(None)),
        )
        .order_by(PricingRule.priority.asc())
        .all()
    )

    total_discount_pct = 0.0
    applied_rules = []
    for rule in rules:
        if rule.rule_type == "volume_discount":
            min_qty = rule.conditions.get("min_qty", 0)
            if payload.quantity_kg >= min_qty:
                if rule.action_type == "discount_pct":
                    total_discount_pct += float(rule.action_value)
                    applied_rules.append({
                        "rule_name":    rule.rule_name,
                        "rule_type":    rule.rule_type,
                        "discount_pct": float(rule.action_value),
                    })

    # 計算折扣後建議售價
    discount_multiplier = 1 - (total_discount_pct / 100)
    suggested_price = base_price * discount_multiplier

    # 底價檢查
    needs_approval = floor_price > 0 and suggested_price < floor_price

    # 對比近期市場行情
    recent_market = (
        db.query(MarketPriceData)
        .filter(
            MarketPriceData.product_category.contains("玉米筍"),
        )
        .order_by(MarketPriceData.price_date.desc())
        .first()
    )

    market_reference = None
    if recent_market:
        market_reference = {
            "market_name":   recent_market.market_name,
            "price_date":    recent_market.price_date.isoformat(),
            "price_avg":     float(recent_market.price_avg or 0),
            "price_currency": recent_market.price_currency,
        }

    return {
        "product_name":       payload.product_name,
        "quantity_kg":        payload.quantity_kg,
        "currency":           payload.currency,
        "base_price_per_kg":  round(base_price, 4),
        "total_discount_pct": round(total_discount_pct, 2),
        "suggested_price_per_kg": round(suggested_price, 4),
        "suggested_total":    round(suggested_price * payload.quantity_kg, 2),
        "floor_price_per_kg": round(floor_price, 4),
        "needs_approval":     needs_approval,
        "applied_rules":      applied_rules,
        "market_reference":   market_reference,
        "price_list_found":   price_list_item is not None,
    }


# ═══════════════════════════════════════════════════
# 價目表 CRUD
# ═══════════════════════════════════════════════════

class PriceListCreate(BaseModel):
    price_list_code:  str
    price_list_name:  str
    price_list_type:  str            = "standard"
    customer_id:      Optional[UUID] = None
    customer_tier:    Optional[str]  = None
    currency_code:    str            = "TWD"
    incoterm:         Optional[str]  = None
    effective_date:   date
    expiry_date:      Optional[date] = None


@router.post("/pricing/price-lists/", summary="新增價目表")
def create_price_list(
    payload: PriceListCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    pl = PriceList(**payload.model_dump(), created_by=current_user.id)
    db.add(pl)
    db.commit()
    db.refresh(pl)
    return {"id": str(pl.id), "price_list_code": pl.price_list_code}


@router.get("/pricing/price-lists/", summary="查詢價目表清單")
def list_price_lists(
    status:      Optional[str]  = Query(None),
    currency:    Optional[str]  = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    q = db.query(PriceList).filter(PriceList.deleted_at.is_(None))
    if status:
        q = q.filter(PriceList.status == status)
    if currency:
        q = q.filter(PriceList.currency_code == currency)
    total = q.count()
    items = q.order_by(PriceList.effective_date.desc()).offset(skip).limit(limit).all()
    return {
        "total": total,
        "items": [{
            "id":               str(pl.id),
            "price_list_code":  pl.price_list_code,
            "price_list_name":  pl.price_list_name,
            "price_list_type":  pl.price_list_type,
            "currency_code":    pl.currency_code,
            "effective_date":   pl.effective_date.isoformat(),
            "expiry_date":      pl.expiry_date.isoformat() if pl.expiry_date else None,
            "status":           pl.status,
        } for pl in items],
    }


# ═══════════════════════════════════════════════════
# M 市場情報 API
# ═══════════════════════════════════════════════════

class MarketPriceCreate(BaseModel):
    source_id:        Optional[UUID] = None
    price_date:       date
    product_category: str
    product_name:     Optional[str]  = None
    market_name:      Optional[str]  = None
    country_code:     Optional[str]  = None
    city:             Optional[str]  = None
    price_low:        Optional[float] = None
    price_high:       Optional[float] = None
    price_avg:        Optional[float] = None
    price_currency:   str            = "TWD"
    price_unit:       Optional[str]  = None
    volume_traded:    Optional[float] = None
    price_trend:      str            = "stable"


@router.post("/market/prices/", summary="新增市場價格數據")
def create_market_price(
    payload: MarketPriceCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    mp = MarketPriceData(**payload.model_dump())
    db.add(mp)
    db.commit()
    db.refresh(mp)
    return {"id": str(mp.id), "message": "市場價格已新增"}


@router.get("/market/prices/", summary="查詢市場價格數據")
def list_market_prices(
    product_category: Optional[str]  = Query(None),
    country_code:     Optional[str]  = Query(None),
    market_name:      Optional[str]  = Query(None),
    date_from:        Optional[date]  = Query(None),
    date_to:          Optional[date]  = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, le=500),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    q = db.query(MarketPriceData)
    if product_category:
        q = q.filter(MarketPriceData.product_category.contains(product_category))
    if country_code:
        q = q.filter(MarketPriceData.country_code == country_code)
    if market_name:
        q = q.filter(MarketPriceData.market_name.contains(market_name))
    if date_from:
        q = q.filter(MarketPriceData.price_date >= date_from)
    if date_to:
        q = q.filter(MarketPriceData.price_date <= date_to)
    total = q.count()
    items = q.order_by(MarketPriceData.price_date.desc()).offset(skip).limit(limit).all()
    return {
        "total": total,
        "items": [{
            "id":              str(mp.id),
            "price_date":      mp.price_date.isoformat(),
            "product_category": mp.product_category,
            "market_name":     mp.market_name,
            "country_code":    mp.country_code,
            "price_low":       float(mp.price_low) if mp.price_low else None,
            "price_high":      float(mp.price_high) if mp.price_high else None,
            "price_avg":       float(mp.price_avg) if mp.price_avg else None,
            "price_currency":  mp.price_currency,
            "price_unit":      mp.price_unit,
            "volume_traded":   float(mp.volume_traded) if mp.volume_traded else None,
            "price_trend":     mp.price_trend,
        } for mp in items],
    }


@router.get("/market/alerts/", summary="價格異常告警清單")
def list_market_alerts(
    unacknowledged_only: bool = Query(False),
    severity: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    q = db.query(MarketPriceAlert)
    if unacknowledged_only:
        q = q.filter(MarketPriceAlert.is_acknowledged == False)
    if severity:
        q = q.filter(MarketPriceAlert.severity == severity)
    total = q.count()
    items = q.order_by(MarketPriceAlert.alert_date.desc()).offset(skip).limit(limit).all()
    return {
        "total": total,
        "items": [{
            "id":               str(a.id),
            "alert_type":       a.alert_type,
            "product_category": a.product_category,
            "market_name":      a.market_name,
            "actual_value":     float(a.actual_value) if a.actual_value else None,
            "severity":         a.severity,
            "alert_date":       a.alert_date.isoformat(),
            "is_acknowledged":  a.is_acknowledged,
        } for a in items],
    }


@router.post("/market/alerts/{alert_id}/acknowledge", summary="確認價格告警")
def acknowledge_alert(
    alert_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    from datetime import datetime
    alert = db.query(MarketPriceAlert).filter(MarketPriceAlert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="告警不存在")
    alert.is_acknowledged = True
    alert.acknowledged_by = current_user.id
    alert.acknowledged_at = datetime.utcnow()
    db.commit()
    return {"message": "已確認告警"}


@router.get("/market/freight/", summary="運價指數查詢")
def list_freight_indices(
    index_name:  Optional[str] = Query(None, description="SCFI/WCI/BDI"),
    date_from:   Optional[date] = Query(None),
    date_to:     Optional[date] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, le=500),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    q = db.query(FreightIndex)
    if index_name:
        q = q.filter(FreightIndex.index_name == index_name)
    if date_from:
        q = q.filter(FreightIndex.index_date >= date_from)
    if date_to:
        q = q.filter(FreightIndex.index_date <= date_to)
    total = q.count()
    items = q.order_by(FreightIndex.index_date.desc()).offset(skip).limit(limit).all()
    return {
        "total": total,
        "items": [{
            "id":           str(f.id),
            "index_name":   f.index_name,
            "route_origin": f.route_origin,
            "route_dest":   f.route_destination,
            "index_date":   f.index_date.isoformat(),
            "index_value":  float(f.index_value),
            "index_unit":   f.index_unit,
            "wow_change_pct": float(f.wow_change_pct) if f.wow_change_pct else None,
            "yoy_change_pct": float(f.yoy_change_pct) if f.yoy_change_pct else None,
        } for f in items],
    }


class FreightIndexCreate(BaseModel):
    index_name:        str
    route_origin:      Optional[str] = None
    route_destination: Optional[str] = None
    container_type:    Optional[str] = None
    index_date:        date
    index_value:       float
    index_unit:        Optional[str] = None
    wow_change_pct:    Optional[float] = None
    yoy_change_pct:    Optional[float] = None
    source:            Optional[str] = None


@router.post("/market/freight/", summary="新增運價指數")
def create_freight_index(
    payload: FreightIndexCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    fi = FreightIndex(**payload.model_dump())
    db.add(fi)
    db.commit()
    db.refresh(fi)
    return {"id": str(fi.id), "message": "運價指數已新增"}


@router.get("/market/buyers/", summary="全球買家資料庫查詢")
def list_buyers(
    country_code:   Optional[str] = Query(None),
    business_type:  Optional[str] = Query(None),
    interest_level: Optional[str] = Query(None),
    keyword:        Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    q = db.query(GlobalBuyerDirectory).filter(
        GlobalBuyerDirectory.deleted_at.is_(None),
        GlobalBuyerDirectory.is_active == True,
    )
    if country_code:
        q = q.filter(GlobalBuyerDirectory.country_code == country_code)
    if business_type:
        q = q.filter(GlobalBuyerDirectory.business_type == business_type)
    if interest_level:
        q = q.filter(GlobalBuyerDirectory.interest_level == interest_level)
    if keyword:
        q = q.filter(GlobalBuyerDirectory.company_name.ilike(f"%{keyword}%"))
    total = q.count()
    items = q.order_by(GlobalBuyerDirectory.created_at.desc()).offset(skip).limit(limit).all()
    return {
        "total": total,
        "items": [{
            "id":            str(b.id),
            "company_name":  b.company_name,
            "country_code":  b.country_code,
            "city":          b.city,
            "business_type": b.business_type,
            "interest_level": b.interest_level,
            "contact_name":  b.contact_name,
            "contact_email": b.contact_email,
            "last_contacted_date": b.last_contacted_date.isoformat() if b.last_contacted_date else None,
        } for b in items],
    }


class BuyerCreate(BaseModel):
    company_name:                  str
    country_code:                  Optional[str]  = None
    city:                          Optional[str]  = None
    business_type:                 Optional[str]  = None
    main_import_products:          Optional[str]  = None
    annual_import_volume_estimate: Optional[float] = None
    key_source_countries:          list           = Field(default_factory=list)
    contact_name:                  Optional[str]  = None
    contact_email:                 Optional[str]  = None
    contact_phone:                 Optional[str]  = None
    website:                       Optional[str]  = None
    company_size:                  Optional[str]  = None
    data_source:                   Optional[str]  = None
    interest_level:                str            = "cold"
    notes:                         Optional[str]  = None


@router.post("/market/buyers/", summary="新增全球買家")
def create_buyer(
    payload: BuyerCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    buyer = GlobalBuyerDirectory(
        **payload.model_dump(),
        assigned_sales_rep_id=current_user.id,
    )
    db.add(buyer)
    db.commit()
    db.refresh(buyer)
    return {"id": str(buyer.id), "company_name": buyer.company_name}
