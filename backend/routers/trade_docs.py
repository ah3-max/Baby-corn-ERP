"""
國際貿易文件 API（G-01 ~ G-05）

端點：
  POST   /trade-documents/               新增貿易文件
  GET    /trade-documents/               查詢貿易文件清單
  GET    /trade-documents/{id}           取得貿易文件詳情
  PATCH  /trade-documents/{id}           更新貿易文件
  DELETE /trade-documents/{id}           軟刪除貿易文件

  POST   /trade-documents/letters-of-credit/    新增信用狀
  GET    /trade-documents/letters-of-credit/    查詢信用狀
  PATCH  /trade-documents/letters-of-credit/{id}  更新信用狀

  POST   /trade-documents/certificates-of-origin/   新增產地證
  GET    /trade-documents/certificates-of-origin/   查詢產地證
  PATCH  /trade-documents/certificates-of-origin/{id}  更新產地證

  POST   /trade-documents/packing-lists/    新增裝箱單
  GET    /trade-documents/packing-lists/    查詢裝箱單
  PATCH  /trade-documents/packing-lists/{id}  更新裝箱單

  POST   /trade-documents/bills-of-lading/    新增提單
  GET    /trade-documents/bills-of-lading/    查詢提單
  PATCH  /trade-documents/bills-of-lading/{id}  更新提單

  GET    /trade-documents/expiry-alerts/      即將到期文件提醒
"""
import logging
from datetime import date, timedelta
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
from models.trade import (
    TradeDocument, LetterOfCredit, CertificateOfOrigin,
    PackingList, BillOfLading,
    CustomsDeclaration, MRLStandard, Certification, Incoterm, HSCode, Port,
)
from utils.dependencies import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/trade-documents", tags=["貿易文件"])


# ═══════════════════════════════════════════════════
# Pydantic Schemas
# ═══════════════════════════════════════════════════

class TradeDocumentCreate(BaseModel):
    document_type:        str
    document_number:      Optional[str]  = None
    document_title:       Optional[str]  = None
    shipment_id:          Optional[UUID] = None
    sales_order_id:       Optional[UUID] = None
    customer_id:          Optional[UUID] = None
    supplier_id:          Optional[UUID] = None
    issue_date:           Optional[date] = None
    expiry_date:          Optional[date] = None
    submission_deadline:  Optional[date] = None
    issuing_authority:    Optional[str]  = None
    issuing_country:      Optional[str]  = None
    destination_country:  Optional[str]  = None
    status:               str            = "draft"
    notes:                Optional[str]  = None
    document_fee:         Optional[float] = None
    document_fee_currency: str           = "TWD"


class TradeDocumentUpdate(BaseModel):
    document_number:     Optional[str]  = None
    document_title:      Optional[str]  = None
    issue_date:          Optional[date] = None
    expiry_date:         Optional[date] = None
    submission_deadline: Optional[date] = None
    issuing_authority:   Optional[str]  = None
    status:              Optional[str]  = None
    notes:               Optional[str]  = None
    document_fee:        Optional[float] = None
    file_path:           Optional[str]  = None


class LCCreate(BaseModel):
    lc_number:            str
    lc_type:              str            = "sight"
    sales_order_id:       Optional[UUID] = None
    customer_id:          Optional[UUID] = None
    issuing_bank_name:    Optional[str]  = None
    issuing_bank_country: Optional[str]  = None
    advising_bank_name:   Optional[str]  = None
    lc_amount:            float
    lc_currency:          str            = "USD"
    tolerance_pct:        float          = 5.0
    issue_date:           Optional[date] = None
    expiry_date:          date
    latest_shipment_date: Optional[date] = None
    documents_required:   list           = Field(default_factory=list)
    port_of_loading:      Optional[str]  = None
    port_of_discharge:    Optional[str]  = None
    partial_shipment:     bool           = False
    transhipment:         bool           = False
    notes:                Optional[str]  = None


class LCUpdate(BaseModel):
    status:               Optional[str]  = None
    utilized_amount:      Optional[float] = None
    notes:                Optional[str]  = None
    latest_shipment_date: Optional[date] = None
    expiry_date:          Optional[date] = None


class COCreate(BaseModel):
    co_number:            Optional[str]  = None
    co_type:              str            = "general"
    shipment_id:          Optional[UUID] = None
    trade_document_id:    Optional[UUID] = None
    exporter_name:        Optional[str]  = None
    exporter_country:     Optional[str]  = None
    importer_name:        Optional[str]  = None
    importer_country:     Optional[str]  = None
    country_of_origin:    Optional[str]  = None
    destination_country:  Optional[str]  = None
    commodity_description: Optional[str] = None
    hs_code:              Optional[str]  = None
    gross_weight_kg:      Optional[float] = None
    net_weight_kg:        Optional[float] = None
    quantity_packages:    Optional[int]  = None
    invoice_no:           Optional[str]  = None
    invoice_date:         Optional[date] = None
    issuing_authority:    Optional[str]  = None
    issue_date:           Optional[date] = None
    notes:                Optional[str]  = None


class COUpdate(BaseModel):
    co_number:         Optional[str]  = None
    status:            Optional[str]  = None
    issue_date:        Optional[date] = None
    notes:             Optional[str]  = None


class PackingListCreate(BaseModel):
    packing_list_no:      str
    shipment_id:          Optional[UUID] = None
    sales_order_id:       Optional[UUID] = None
    trade_document_id:    Optional[UUID] = None
    exporter_name:        Optional[str]  = None
    importer_name:        Optional[str]  = None
    commodity_description: Optional[str] = None
    total_packages:       Optional[int]  = None
    total_gross_weight_kg: Optional[float] = None
    total_net_weight_kg:  Optional[float] = None
    total_cbm:            Optional[float] = None
    container_no:         Optional[str]  = None
    seal_no:              Optional[str]  = None
    vessel_name:          Optional[str]  = None
    voyage_no:            Optional[str]  = None
    port_of_loading:      Optional[str]  = None
    port_of_discharge:    Optional[str]  = None
    etd:                  Optional[date] = None
    eta:                  Optional[date] = None
    line_items:           list           = Field(default_factory=list)
    issue_date:           Optional[date] = None
    notes:                Optional[str]  = None


class PackingListUpdate(BaseModel):
    total_packages:       Optional[int]   = None
    total_gross_weight_kg: Optional[float] = None
    total_net_weight_kg:  Optional[float] = None
    total_cbm:            Optional[float] = None
    container_no:         Optional[str]   = None
    seal_no:              Optional[str]   = None
    line_items:           Optional[list]  = None
    notes:                Optional[str]   = None


class BLCreate(BaseModel):
    bl_number:            str
    bl_type:              str            = "ocean"
    shipment_id:          Optional[UUID] = None
    packing_list_id:      Optional[UUID] = None
    trade_document_id:    Optional[UUID] = None
    shipper_name:         Optional[str]  = None
    consignee_name:       Optional[str]  = None
    notify_party:         Optional[str]  = None
    carrier_name:         Optional[str]  = None
    vessel_name:          Optional[str]  = None
    voyage_no:            Optional[str]  = None
    container_nos:        list           = Field(default_factory=list)
    port_of_loading:      Optional[str]  = None
    port_of_discharge:    Optional[str]  = None
    place_of_delivery:    Optional[str]  = None
    onboard_date:         Optional[date] = None
    etd:                  Optional[date] = None
    eta:                  Optional[date] = None
    commodity_description: Optional[str] = None
    total_packages:       Optional[int]  = None
    total_gross_weight_kg: Optional[float] = None
    total_net_weight_kg:  Optional[float] = None
    total_cbm:            Optional[float] = None
    freight_amount:       Optional[float] = None
    freight_currency:     str            = "USD"
    freight_terms:        Optional[str]  = None
    original_copies:      int            = 3
    notes:                Optional[str]  = None


class BLUpdate(BaseModel):
    status:              Optional[str]  = None
    onboard_date:        Optional[date] = None
    telex_release_date:  Optional[date] = None
    freight_amount:      Optional[float] = None
    notes:               Optional[str]  = None


# ═══════════════════════════════════════════════════
# 輔助函數
# ═══════════════════════════════════════════════════

def _doc_to_dict(doc: TradeDocument) -> dict:
    return {
        "id":                   str(doc.id),
        "document_type":        doc.document_type,
        "document_number":      doc.document_number,
        "document_title":       doc.document_title,
        "shipment_id":          str(doc.shipment_id) if doc.shipment_id else None,
        "sales_order_id":       str(doc.sales_order_id) if doc.sales_order_id else None,
        "customer_id":          str(doc.customer_id) if doc.customer_id else None,
        "issue_date":           doc.issue_date.isoformat() if doc.issue_date else None,
        "expiry_date":          doc.expiry_date.isoformat() if doc.expiry_date else None,
        "submission_deadline":  doc.submission_deadline.isoformat() if doc.submission_deadline else None,
        "issuing_authority":    doc.issuing_authority,
        "issuing_country":      doc.issuing_country,
        "destination_country":  doc.destination_country,
        "status":               doc.status,
        "notes":                doc.notes,
        "document_fee":         float(doc.document_fee) if doc.document_fee else None,
        "document_fee_currency": doc.document_fee_currency,
        "created_at":           doc.created_at.isoformat() if doc.created_at else None,
    }


def _lc_to_dict(lc: LetterOfCredit) -> dict:
    return {
        "id":                   str(lc.id),
        "lc_number":            lc.lc_number,
        "lc_type":              lc.lc_type,
        "sales_order_id":       str(lc.sales_order_id) if lc.sales_order_id else None,
        "customer_id":          str(lc.customer_id) if lc.customer_id else None,
        "issuing_bank_name":    lc.issuing_bank_name,
        "issuing_bank_country": lc.issuing_bank_country,
        "advising_bank_name":   lc.advising_bank_name,
        "lc_amount":            float(lc.lc_amount),
        "lc_currency":          lc.lc_currency,
        "tolerance_pct":        float(lc.tolerance_pct),
        "issue_date":           lc.issue_date.isoformat() if lc.issue_date else None,
        "expiry_date":          lc.expiry_date.isoformat() if lc.expiry_date else None,
        "latest_shipment_date": lc.latest_shipment_date.isoformat() if lc.latest_shipment_date else None,
        "documents_required":   lc.documents_required,
        "port_of_loading":      lc.port_of_loading,
        "port_of_discharge":    lc.port_of_discharge,
        "partial_shipment":     lc.partial_shipment,
        "transhipment":         lc.transhipment,
        "status":               lc.status,
        "utilized_amount":      float(lc.utilized_amount or 0),
        "remaining_amount":     float(lc.lc_amount) - float(lc.utilized_amount or 0),
        "notes":                lc.notes,
    }


# ═══════════════════════════════════════════════════
# G-01：貿易文件總表
# ═══════════════════════════════════════════════════

@router.post("/", summary="新增貿易文件")
def create_trade_doc(
    payload: TradeDocumentCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    from datetime import datetime
    doc = TradeDocument(**payload.model_dump(), created_by=current_user.id)
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return _doc_to_dict(doc)


@router.get("/", summary="查詢貿易文件清單")
def list_trade_docs(
    document_type: Optional[str] = Query(None),
    shipment_id:   Optional[UUID] = Query(None),
    status:        Optional[str] = Query(None),
    expiring_days: Optional[int] = Query(None, description="N 天內到期"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    q = db.query(TradeDocument).filter(TradeDocument.deleted_at.is_(None))
    if document_type:
        q = q.filter(TradeDocument.document_type == document_type)
    if shipment_id:
        q = q.filter(TradeDocument.shipment_id == shipment_id)
    if status:
        q = q.filter(TradeDocument.status == status)
    if expiring_days is not None:
        threshold = date.today() + timedelta(days=expiring_days)
        q = q.filter(
            TradeDocument.expiry_date.isnot(None),
            TradeDocument.expiry_date <= threshold,
            TradeDocument.expiry_date >= date.today(),
        )
    total = q.count()
    docs = q.order_by(TradeDocument.created_at.desc()).offset(skip).limit(limit).all()
    return {"total": total, "items": [_doc_to_dict(d) for d in docs]}


@router.get("/expiry-alerts", summary="即將到期文件提醒")
def expiry_alerts(
    days: int = Query(30, description="提前幾天預警"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """回傳 N 天內到期的所有貿易文件（跨所有類型）"""
    threshold = date.today() + timedelta(days=days)
    today = date.today()

    # 貿易文件
    docs = (
        db.query(TradeDocument)
        .filter(
            TradeDocument.deleted_at.is_(None),
            TradeDocument.expiry_date.isnot(None),
            TradeDocument.expiry_date >= today,
            TradeDocument.expiry_date <= threshold,
        )
        .all()
    )

    # 信用狀
    lcs = (
        db.query(LetterOfCredit)
        .filter(
            LetterOfCredit.deleted_at.is_(None),
            LetterOfCredit.expiry_date >= today,
            LetterOfCredit.expiry_date <= threshold,
            LetterOfCredit.status.notin_(["expired", "cancelled"]),
        )
        .all()
    )

    alerts = []
    for doc in docs:
        days_left = (doc.expiry_date - today).days
        alerts.append({
            "type": "trade_document",
            "doc_type": doc.document_type,
            "id": str(doc.id),
            "document_number": doc.document_number,
            "expiry_date": doc.expiry_date.isoformat(),
            "days_left": days_left,
            "status": doc.status,
        })

    for lc in lcs:
        days_left = (lc.expiry_date - today).days
        alerts.append({
            "type": "letter_of_credit",
            "doc_type": "letter_of_credit",
            "id": str(lc.id),
            "document_number": lc.lc_number,
            "expiry_date": lc.expiry_date.isoformat(),
            "days_left": days_left,
            "status": lc.status,
            "lc_amount": float(lc.lc_amount),
            "lc_currency": lc.lc_currency,
        })

    alerts.sort(key=lambda x: x["days_left"])
    return {"total": len(alerts), "items": alerts}


@router.get("/{doc_id}", summary="取得貿易文件詳情")
def get_trade_doc(
    doc_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    doc = db.query(TradeDocument).filter(
        TradeDocument.id == doc_id,
        TradeDocument.deleted_at.is_(None),
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="文件不存在")
    return _doc_to_dict(doc)


@router.patch("/{doc_id}", summary="更新貿易文件")
def update_trade_doc(
    doc_id: UUID,
    payload: TradeDocumentUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    doc = db.query(TradeDocument).filter(
        TradeDocument.id == doc_id,
        TradeDocument.deleted_at.is_(None),
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="文件不存在")
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(doc, field, value)
    db.commit()
    db.refresh(doc)
    return _doc_to_dict(doc)


@router.delete("/{doc_id}", summary="刪除貿易文件")
def delete_trade_doc(
    doc_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    from datetime import datetime
    doc = db.query(TradeDocument).filter(
        TradeDocument.id == doc_id,
        TradeDocument.deleted_at.is_(None),
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="文件不存在")
    doc.deleted_at = datetime.utcnow()
    db.commit()
    return {"message": "已刪除"}


# ═══════════════════════════════════════════════════
# G-02：信用狀（L/C）
# ═══════════════════════════════════════════════════

@router.post("/letters-of-credit/", summary="新增信用狀")
def create_lc(
    payload: LCCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    lc = LetterOfCredit(**payload.model_dump(), created_by=current_user.id)
    db.add(lc)
    db.commit()
    db.refresh(lc)
    return _lc_to_dict(lc)


@router.get("/letters-of-credit/", summary="查詢信用狀清單")
def list_lcs(
    customer_id: Optional[UUID] = Query(None),
    status:      Optional[str]  = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    q = db.query(LetterOfCredit).filter(LetterOfCredit.deleted_at.is_(None))
    if customer_id:
        q = q.filter(LetterOfCredit.customer_id == customer_id)
    if status:
        q = q.filter(LetterOfCredit.status == status)
    total = q.count()
    items = q.order_by(LetterOfCredit.expiry_date.asc()).offset(skip).limit(limit).all()
    return {"total": total, "items": [_lc_to_dict(lc) for lc in items]}


@router.patch("/letters-of-credit/{lc_id}", summary="更新信用狀")
def update_lc(
    lc_id: UUID,
    payload: LCUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    lc = db.query(LetterOfCredit).filter(
        LetterOfCredit.id == lc_id,
        LetterOfCredit.deleted_at.is_(None),
    ).first()
    if not lc:
        raise HTTPException(status_code=404, detail="信用狀不存在")
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(lc, field, value)
    db.commit()
    db.refresh(lc)
    return _lc_to_dict(lc)


# ═══════════════════════════════════════════════════
# G-03：產地證明書
# ═══════════════════════════════════════════════════

def _co_to_dict(co: CertificateOfOrigin) -> dict:
    return {
        "id":                  str(co.id),
        "co_number":           co.co_number,
        "co_type":             co.co_type,
        "shipment_id":         str(co.shipment_id) if co.shipment_id else None,
        "exporter_name":       co.exporter_name,
        "importer_name":       co.importer_name,
        "country_of_origin":   co.country_of_origin,
        "destination_country": co.destination_country,
        "commodity_description": co.commodity_description,
        "hs_code":             co.hs_code,
        "gross_weight_kg":     float(co.gross_weight_kg) if co.gross_weight_kg else None,
        "net_weight_kg":       float(co.net_weight_kg) if co.net_weight_kg else None,
        "quantity_packages":   co.quantity_packages,
        "invoice_no":          co.invoice_no,
        "invoice_date":        co.invoice_date.isoformat() if co.invoice_date else None,
        "issuing_authority":   co.issuing_authority,
        "issue_date":          co.issue_date.isoformat() if co.issue_date else None,
        "status":              co.status,
        "notes":               co.notes,
    }


@router.post("/certificates-of-origin/", summary="新增產地證明書")
def create_co(
    payload: COCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    co = CertificateOfOrigin(**payload.model_dump(), created_by=current_user.id)
    db.add(co)
    db.commit()
    db.refresh(co)
    return _co_to_dict(co)


@router.get("/certificates-of-origin/", summary="查詢產地證清單")
def list_cos(
    shipment_id: Optional[UUID] = Query(None),
    status:      Optional[str]  = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    q = db.query(CertificateOfOrigin).filter(CertificateOfOrigin.deleted_at.is_(None))
    if shipment_id:
        q = q.filter(CertificateOfOrigin.shipment_id == shipment_id)
    if status:
        q = q.filter(CertificateOfOrigin.status == status)
    total = q.count()
    items = q.order_by(CertificateOfOrigin.created_at.desc()).offset(skip).limit(limit).all()
    return {"total": total, "items": [_co_to_dict(co) for co in items]}


@router.patch("/certificates-of-origin/{co_id}", summary="更新產地證")
def update_co(
    co_id: UUID,
    payload: COUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    co = db.query(CertificateOfOrigin).filter(
        CertificateOfOrigin.id == co_id,
        CertificateOfOrigin.deleted_at.is_(None),
    ).first()
    if not co:
        raise HTTPException(status_code=404, detail="產地證不存在")
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(co, field, value)
    db.commit()
    db.refresh(co)
    return _co_to_dict(co)


# ═══════════════════════════════════════════════════
# G-04：裝箱單
# ═══════════════════════════════════════════════════

def _pl_to_dict(pl: PackingList) -> dict:
    return {
        "id":                    str(pl.id),
        "packing_list_no":       pl.packing_list_no,
        "shipment_id":           str(pl.shipment_id) if pl.shipment_id else None,
        "sales_order_id":        str(pl.sales_order_id) if pl.sales_order_id else None,
        "exporter_name":         pl.exporter_name,
        "importer_name":         pl.importer_name,
        "commodity_description": pl.commodity_description,
        "total_packages":        pl.total_packages,
        "total_gross_weight_kg": float(pl.total_gross_weight_kg) if pl.total_gross_weight_kg else None,
        "total_net_weight_kg":   float(pl.total_net_weight_kg) if pl.total_net_weight_kg else None,
        "total_cbm":             float(pl.total_cbm) if pl.total_cbm else None,
        "container_no":          pl.container_no,
        "seal_no":               pl.seal_no,
        "vessel_name":           pl.vessel_name,
        "voyage_no":             pl.voyage_no,
        "port_of_loading":       pl.port_of_loading,
        "port_of_discharge":     pl.port_of_discharge,
        "etd":                   pl.etd.isoformat() if pl.etd else None,
        "eta":                   pl.eta.isoformat() if pl.eta else None,
        "line_items":            pl.line_items or [],
        "issue_date":            pl.issue_date.isoformat() if pl.issue_date else None,
        "notes":                 pl.notes,
    }


@router.post("/packing-lists/", summary="新增裝箱單")
def create_packing_list(
    payload: PackingListCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    pl = PackingList(**payload.model_dump(), created_by=current_user.id)
    db.add(pl)
    db.commit()
    db.refresh(pl)
    return _pl_to_dict(pl)


@router.get("/packing-lists/", summary="查詢裝箱單清單")
def list_packing_lists(
    shipment_id:    Optional[UUID] = Query(None),
    sales_order_id: Optional[UUID] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    q = db.query(PackingList).filter(PackingList.deleted_at.is_(None))
    if shipment_id:
        q = q.filter(PackingList.shipment_id == shipment_id)
    if sales_order_id:
        q = q.filter(PackingList.sales_order_id == sales_order_id)
    total = q.count()
    items = q.order_by(PackingList.created_at.desc()).offset(skip).limit(limit).all()
    return {"total": total, "items": [_pl_to_dict(pl) for pl in items]}


@router.patch("/packing-lists/{pl_id}", summary="更新裝箱單")
def update_packing_list(
    pl_id: UUID,
    payload: PackingListUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    pl = db.query(PackingList).filter(
        PackingList.id == pl_id,
        PackingList.deleted_at.is_(None),
    ).first()
    if not pl:
        raise HTTPException(status_code=404, detail="裝箱單不存在")
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(pl, field, value)
    db.commit()
    db.refresh(pl)
    return _pl_to_dict(pl)


# ═══════════════════════════════════════════════════
# G-05：提單（B/L）
# ═══════════════════════════════════════════════════

def _bl_to_dict(bl: BillOfLading) -> dict:
    return {
        "id":                    str(bl.id),
        "bl_number":             bl.bl_number,
        "bl_type":               bl.bl_type,
        "shipment_id":           str(bl.shipment_id) if bl.shipment_id else None,
        "shipper_name":          bl.shipper_name,
        "consignee_name":        bl.consignee_name,
        "notify_party":          bl.notify_party,
        "carrier_name":          bl.carrier_name,
        "vessel_name":           bl.vessel_name,
        "voyage_no":             bl.voyage_no,
        "container_nos":         bl.container_nos or [],
        "port_of_loading":       bl.port_of_loading,
        "port_of_discharge":     bl.port_of_discharge,
        "place_of_delivery":     bl.place_of_delivery,
        "onboard_date":          bl.onboard_date.isoformat() if bl.onboard_date else None,
        "etd":                   bl.etd.isoformat() if bl.etd else None,
        "eta":                   bl.eta.isoformat() if bl.eta else None,
        "commodity_description": bl.commodity_description,
        "total_packages":        bl.total_packages,
        "total_gross_weight_kg": float(bl.total_gross_weight_kg) if bl.total_gross_weight_kg else None,
        "total_net_weight_kg":   float(bl.total_net_weight_kg) if bl.total_net_weight_kg else None,
        "total_cbm":             float(bl.total_cbm) if bl.total_cbm else None,
        "freight_amount":        float(bl.freight_amount) if bl.freight_amount else None,
        "freight_currency":      bl.freight_currency,
        "freight_terms":         bl.freight_terms,
        "status":                bl.status,
        "original_copies":       bl.original_copies,
        "telex_release_date":    bl.telex_release_date.isoformat() if bl.telex_release_date else None,
        "notes":                 bl.notes,
    }


@router.post("/bills-of-lading/", summary="新增提單")
def create_bl(
    payload: BLCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    bl = BillOfLading(**payload.model_dump(), created_by=current_user.id)
    db.add(bl)
    db.commit()
    db.refresh(bl)
    return _bl_to_dict(bl)


@router.get("/bills-of-lading/", summary="查詢提單清單")
def list_bls(
    shipment_id: Optional[UUID] = Query(None),
    status:      Optional[str]  = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    q = db.query(BillOfLading).filter(BillOfLading.deleted_at.is_(None))
    if shipment_id:
        q = q.filter(BillOfLading.shipment_id == shipment_id)
    if status:
        q = q.filter(BillOfLading.status == status)
    total = q.count()
    items = q.order_by(BillOfLading.created_at.desc()).offset(skip).limit(limit).all()
    return {"total": total, "items": [_bl_to_dict(bl) for bl in items]}


@router.patch("/bills-of-lading/{bl_id}", summary="更新提單")
def update_bl(
    bl_id: UUID,
    payload: BLUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    bl = db.query(BillOfLading).filter(
        BillOfLading.id == bl_id,
        BillOfLading.deleted_at.is_(None),
    ).first()
    if not bl:
        raise HTTPException(status_code=404, detail="提單不存在")
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(bl, field, value)
    db.commit()
    db.refresh(bl)
    return _bl_to_dict(bl)


# ─── G-03 報關單 ─────────────────────────────────────────

@router.get("/customs-declarations", summary="報關單列表")
def list_customs_declarations(
    shipment_id: Optional[UUID] = Query(None),
    status: Optional[str] = Query(None),
    declaration_type: Optional[str] = Query(None),
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    q = db.query(CustomsDeclaration).filter(CustomsDeclaration.deleted_at.is_(None))
    if shipment_id:
        q = q.filter(CustomsDeclaration.shipment_id == shipment_id)
    if status:
        q = q.filter(CustomsDeclaration.status == status)
    if declaration_type:
        q = q.filter(CustomsDeclaration.declaration_type == declaration_type)
    total = q.count()
    items = q.order_by(CustomsDeclaration.declaration_date.desc()).offset(skip).limit(limit).all()
    return {"total": total, "items": [_obj_to_dict(i) for i in items]}


@router.post("/customs-declarations", status_code=201, summary="建立報關單")
def create_customs_declaration(
    data: dict,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    obj = CustomsDeclaration(**data, created_by=current_user.id)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return _obj_to_dict(obj)


@router.patch("/customs-declarations/{decl_id}", summary="更新報關單狀態")
def patch_customs_declaration(
    decl_id: UUID,
    data: dict,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    from fastapi import HTTPException
    obj = db.query(CustomsDeclaration).filter(CustomsDeclaration.id == decl_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="報關單不存在")
    for k, v in data.items():
        if hasattr(obj, k):
            setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    return _obj_to_dict(obj)


# ─── G-04 農藥殘留標準 ────────────────────────────────────

@router.get("/mrl-standards", summary="MRL 標準列表")
def list_mrl_standards(
    country_code: Optional[str] = Query(None),
    product_category: Optional[str] = Query(None),
    pesticide_name: Optional[str] = Query(None),
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    q = db.query(MRLStandard).filter(MRLStandard.is_active.is_(True))
    if country_code:
        q = q.filter(MRLStandard.country_code == country_code)
    if product_category:
        q = q.filter(MRLStandard.product_category.ilike(f"%{product_category}%"))
    if pesticide_name:
        q = q.filter(
            MRLStandard.pesticide_name.ilike(f"%{pesticide_name}%") |
            MRLStandard.pesticide_name_en.ilike(f"%{pesticide_name}%")
        )
    items = q.order_by(MRLStandard.country_code, MRLStandard.pesticide_name).limit(limit).all()
    return {"items": [_obj_to_dict(i) for i in items], "total": len(items)}


@router.post("/mrl-standards", status_code=201, summary="新增 MRL 標準")
def create_mrl_standard(
    data: dict,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    obj = MRLStandard(**data)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return _obj_to_dict(obj)


@router.get("/certifications", summary="認證管理列表")
def list_certifications(
    certification_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    expiring_days: Optional[int] = Query(None),
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    from datetime import date, timedelta
    q = db.query(Certification).filter(Certification.deleted_at.is_(None))
    if certification_type:
        q = q.filter(Certification.certification_type == certification_type)
    if status:
        q = q.filter(Certification.status == status)
    if expiring_days is not None:
        threshold = date.today() + timedelta(days=expiring_days)
        q = q.filter(
            Certification.expiry_date.isnot(None),
            Certification.expiry_date <= threshold,
            Certification.expiry_date >= date.today(),
        )
    items = q.order_by(Certification.expiry_date.asc()).limit(limit).all()
    return {"items": [_obj_to_dict(i) for i in items], "total": len(items)}


@router.post("/certifications", status_code=201, summary="新增認證")
def create_certification(
    data: dict,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    obj = Certification(**data, created_by=current_user.id)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return _obj_to_dict(obj)


# ─── G-05 基礎主檔 ───────────────────────────────────────

@router.get("/incoterms", summary="國貿條件列表")
def list_incoterms(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    items = db.query(Incoterm).order_by(Incoterm.code).all()
    return {"items": [_obj_to_dict(i) for i in items]}


@router.get("/hs-codes", summary="HS 代碼查詢")
def list_hs_codes(
    keyword: Optional[str] = Query(None),
    level: Optional[int] = Query(None),
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    q = db.query(HSCode).filter(HSCode.is_active.is_(True))
    if level:
        q = q.filter(HSCode.level == level)
    if keyword:
        q = q.filter(
            HSCode.hs_code.ilike(f"%{keyword}%") |
            HSCode.description_zh.ilike(f"%{keyword}%") |
            HSCode.description.ilike(f"%{keyword}%")
        )
    items = q.order_by(HSCode.hs_code).limit(limit).all()
    return {"items": [_obj_to_dict(i) for i in items], "total": len(items)}


@router.get("/ports", summary="港口主檔查詢")
def list_ports(
    country_code: Optional[str] = Query(None),
    port_type: Optional[str] = Query(None),
    keyword: Optional[str] = Query(None),
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    q = db.query(Port).filter(Port.is_active.is_(True))
    if country_code:
        q = q.filter(Port.country_code == country_code)
    if port_type:
        q = q.filter(Port.port_type == port_type)
    if keyword:
        q = q.filter(
            Port.port_name.ilike(f"%{keyword}%") |
            Port.port_code.ilike(f"%{keyword}%") |
            Port.city.ilike(f"%{keyword}%")
        )
    items = q.order_by(Port.country_code, Port.port_name).limit(limit).all()
    return {"items": [_obj_to_dict(i) for i in items], "total": len(items)}


def _obj_to_dict(obj) -> dict:
    """通用 SQLAlchemy → dict 轉換"""
    import uuid as _uuid
    from datetime import datetime as _dt, date as _d
    d = {k: v for k, v in obj.__dict__.items() if not k.startswith("_")}
    for k, v in d.items():
        if isinstance(v, _uuid.UUID):
            d[k] = str(v)
        elif isinstance(v, (_dt, _d)):
            d[k] = v.isoformat()
    return d
