"""
出口發票 API
GET    /invoices                    - 發票列表
POST   /invoices                    - 新增發票（從出口單帶入資料）
GET    /invoices/:id                - 發票詳情
PUT    /invoices/:id                - 編輯發票
PUT    /invoices/:id/status         - 更新發票狀態
DELETE /invoices/:id                - 刪除草稿發票
GET    /invoices/:id/pdf            - 匯出 PDF
GET    /shipments/:id/invoices      - 某出口單的所有發票
"""
from uuid import UUID
from typing import List, Optional
from decimal import Decimal
from datetime import datetime, date
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from pydantic import BaseModel
import io

from database import get_db
from models.user import User
from models.shipment import Shipment, ShipmentBatch
from models.batch import Batch
from models.invoice import Invoice, InvoiceItem
from models.system import SystemSetting
from utils.dependencies import check_permission

router = APIRouter(prefix="/invoices", tags=["出口發票"])


# ─── Schemas ────────────────────────────────────────

class InvoiceItemCreate(BaseModel):
    batch_id:       Optional[str] = None
    description:    str
    hs_code:        Optional[str] = None
    quantity_kg:    Optional[Decimal] = None
    quantity_boxes: Optional[int] = None
    unit_price:     Optional[Decimal] = None
    amount:         Optional[Decimal] = None
    origin_country: str = "Thailand"
    notes:          Optional[str] = None


class InvoiceCreate(BaseModel):
    shipment_id:      str
    invoice_date:     date
    due_date:         Optional[date] = None
    # 賣方
    seller_name:      str
    seller_address:   Optional[str] = None
    seller_tax_id:    Optional[str] = None
    seller_contact:   Optional[str] = None
    seller_phone:     Optional[str] = None
    seller_email:     Optional[str] = None
    # 買方
    buyer_name:       str
    buyer_address:    Optional[str] = None
    buyer_tax_id:     Optional[str] = None
    buyer_contact:    Optional[str] = None
    buyer_phone:      Optional[str] = None
    buyer_email:      Optional[str] = None
    # 貿易條件
    currency:         str = "THB"
    incoterms:        Optional[str] = None
    payment_terms:    Optional[str] = None
    # 費用
    freight_charge:   Decimal = Decimal("0")
    insurance_charge: Decimal = Decimal("0")
    other_charge:     Decimal = Decimal("0")
    # 物流
    transport_mode:   Optional[str] = None
    bl_awb_no:        Optional[str] = None
    vessel_flight:    Optional[str] = None
    port_of_loading:  Optional[str] = None
    port_of_discharge:Optional[str] = None
    notes:            Optional[str] = None
    # 明細
    items:            List[InvoiceItemCreate]


class InvoiceUpdate(BaseModel):
    invoice_date:     Optional[date] = None
    due_date:         Optional[date] = None
    seller_name:      Optional[str] = None
    seller_address:   Optional[str] = None
    seller_tax_id:    Optional[str] = None
    seller_contact:   Optional[str] = None
    seller_phone:     Optional[str] = None
    seller_email:     Optional[str] = None
    buyer_name:       Optional[str] = None
    buyer_address:    Optional[str] = None
    buyer_tax_id:     Optional[str] = None
    buyer_contact:    Optional[str] = None
    buyer_phone:      Optional[str] = None
    buyer_email:      Optional[str] = None
    currency:         Optional[str] = None
    incoterms:        Optional[str] = None
    payment_terms:    Optional[str] = None
    freight_charge:   Optional[Decimal] = None
    insurance_charge: Optional[Decimal] = None
    other_charge:     Optional[Decimal] = None
    transport_mode:   Optional[str] = None
    bl_awb_no:        Optional[str] = None
    vessel_flight:    Optional[str] = None
    port_of_loading:  Optional[str] = None
    port_of_discharge:Optional[str] = None
    notes:            Optional[str] = None
    items:            Optional[List[InvoiceItemCreate]] = None


class InvoiceItemOut(BaseModel):
    id:             str
    batch_id:       Optional[str]
    description:    str
    hs_code:        Optional[str]
    quantity_kg:    Optional[float]
    quantity_boxes: Optional[int]
    unit_price:     Optional[float]
    amount:         Optional[float]
    origin_country: Optional[str]
    notes:          Optional[str]

    class Config:
        from_attributes = True


class InvoiceOut(BaseModel):
    id:               str
    invoice_no:       str
    shipment_id:      str
    invoice_date:     date
    due_date:         Optional[date]
    # 賣方
    seller_name:      str
    seller_address:   Optional[str]
    seller_tax_id:    Optional[str]
    seller_contact:   Optional[str]
    seller_phone:     Optional[str]
    seller_email:     Optional[str]
    # 買方
    buyer_name:       str
    buyer_address:    Optional[str]
    buyer_tax_id:     Optional[str]
    buyer_contact:    Optional[str]
    buyer_phone:      Optional[str]
    buyer_email:      Optional[str]
    # 貿易條件
    currency:         str
    incoterms:        Optional[str]
    payment_terms:    Optional[str]
    # 金額
    subtotal:         Optional[float]
    freight_charge:   Optional[float]
    insurance_charge: Optional[float]
    other_charge:     Optional[float]
    total_amount:     Optional[float]
    # 物流
    transport_mode:   Optional[str]
    bl_awb_no:        Optional[str]
    vessel_flight:    Optional[str]
    port_of_loading:  Optional[str]
    port_of_discharge:Optional[str]
    # 狀態
    status:           str
    notes:            Optional[str]
    items:            List[InvoiceItemOut]
    created_at:       datetime

    class Config:
        from_attributes = True


# ─── 工具函式 ────────────────────────────────────────

def _generate_invoice_no(db: Session, invoice_date: date) -> str:
    """產生發票號碼：INV-YYYYMMDD-XXX"""
    date_str = invoice_date.strftime("%Y%m%d")
    prefix = f"INV-{date_str}-"
    count = db.query(func.count(Invoice.id)).filter(
        Invoice.invoice_no.like(f"{prefix}%")
    ).scalar()
    return f"{prefix}{str(count + 1).zfill(3)}"


def _invoice_to_out(inv: Invoice) -> InvoiceOut:
    """Invoice ORM → InvoiceOut"""
    return InvoiceOut(
        id=str(inv.id),
        invoice_no=inv.invoice_no,
        shipment_id=str(inv.shipment_id),
        invoice_date=inv.invoice_date,
        due_date=inv.due_date,
        seller_name=inv.seller_name,
        seller_address=inv.seller_address,
        seller_tax_id=inv.seller_tax_id,
        seller_contact=inv.seller_contact,
        seller_phone=inv.seller_phone,
        seller_email=inv.seller_email,
        buyer_name=inv.buyer_name,
        buyer_address=inv.buyer_address,
        buyer_tax_id=inv.buyer_tax_id,
        buyer_contact=inv.buyer_contact,
        buyer_phone=inv.buyer_phone,
        buyer_email=inv.buyer_email,
        currency=inv.currency,
        incoterms=inv.incoterms,
        payment_terms=inv.payment_terms,
        subtotal=float(inv.subtotal) if inv.subtotal else None,
        freight_charge=float(inv.freight_charge) if inv.freight_charge else None,
        insurance_charge=float(inv.insurance_charge) if inv.insurance_charge else None,
        other_charge=float(inv.other_charge) if inv.other_charge else None,
        total_amount=float(inv.total_amount) if inv.total_amount else None,
        transport_mode=inv.transport_mode,
        bl_awb_no=inv.bl_awb_no,
        vessel_flight=inv.vessel_flight,
        port_of_loading=inv.port_of_loading,
        port_of_discharge=inv.port_of_discharge,
        status=inv.status,
        notes=inv.notes,
        items=[
            InvoiceItemOut(
                id=str(it.id),
                batch_id=str(it.batch_id) if it.batch_id else None,
                description=it.description,
                hs_code=it.hs_code,
                quantity_kg=float(it.quantity_kg) if it.quantity_kg else None,
                quantity_boxes=it.quantity_boxes,
                unit_price=float(it.unit_price) if it.unit_price else None,
                amount=float(it.amount) if it.amount else None,
                origin_country=it.origin_country,
                notes=it.notes,
            ) for it in (inv.items or [])
        ],
        created_at=inv.created_at,
    )


def _get_company_settings(db: Session) -> dict:
    """從系統設定讀取公司資訊"""
    result = {}
    for key in ["seller_company", "buyer_company"]:
        setting = db.query(SystemSetting).filter(SystemSetting.key == key).first()
        if setting and setting.value:
            import json
            result[key] = json.loads(setting.value) if isinstance(setting.value, str) else setting.value
    return result


# ─── 路由 ────────────────────────────────────────────

@router.get("", response_model=List[InvoiceOut])
def list_invoices(
    shipment_id: Optional[UUID] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    _: User = Depends(check_permission("shipment", "read")),
):
    """發票列表"""
    q = db.query(Invoice).options(joinedload(Invoice.items))
    if shipment_id:
        q = q.filter(Invoice.shipment_id == shipment_id)
    if status_filter:
        q = q.filter(Invoice.status == status_filter)
    invoices = q.order_by(Invoice.created_at.desc()).offset(skip).limit(limit).all()
    return [_invoice_to_out(inv) for inv in invoices]


@router.get("/company-defaults")
def get_company_defaults(
    db: Session = Depends(get_db),
    _: User = Depends(check_permission("shipment", "read")),
):
    """取得預設公司資訊（自動帶入發票）"""
    return _get_company_settings(db)


@router.post("", response_model=InvoiceOut, status_code=201)
def create_invoice(
    payload: InvoiceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_permission("shipment", "create")),
):
    """新增發票"""
    shipment = db.query(Shipment).filter(Shipment.id == payload.shipment_id).first()
    if not shipment:
        raise HTTPException(status_code=404, detail="出口單不存在")

    invoice_no = _generate_invoice_no(db, payload.invoice_date)

    # 計算小計與總金額
    subtotal = Decimal("0")
    items = []
    for it in payload.items:
        item_amount = it.amount
        if not item_amount and it.quantity_kg and it.unit_price:
            item_amount = it.quantity_kg * it.unit_price
        if item_amount:
            subtotal += item_amount

        items.append(InvoiceItem(
            batch_id=UUID(it.batch_id) if it.batch_id else None,
            description=it.description,
            hs_code=it.hs_code,
            quantity_kg=it.quantity_kg,
            quantity_boxes=it.quantity_boxes,
            unit_price=it.unit_price,
            amount=item_amount,
            origin_country=it.origin_country,
            notes=it.notes,
        ))

    total = subtotal + (payload.freight_charge or 0) + (payload.insurance_charge or 0) + (payload.other_charge or 0)

    inv = Invoice(
        invoice_no=invoice_no,
        shipment_id=UUID(payload.shipment_id),
        invoice_date=payload.invoice_date,
        due_date=payload.due_date,
        seller_name=payload.seller_name,
        seller_address=payload.seller_address,
        seller_tax_id=payload.seller_tax_id,
        seller_contact=payload.seller_contact,
        seller_phone=payload.seller_phone,
        seller_email=payload.seller_email,
        buyer_name=payload.buyer_name,
        buyer_address=payload.buyer_address,
        buyer_tax_id=payload.buyer_tax_id,
        buyer_contact=payload.buyer_contact,
        buyer_phone=payload.buyer_phone,
        buyer_email=payload.buyer_email,
        currency=payload.currency,
        incoterms=payload.incoterms,
        payment_terms=payload.payment_terms,
        subtotal=subtotal,
        freight_charge=payload.freight_charge,
        insurance_charge=payload.insurance_charge,
        other_charge=payload.other_charge,
        total_amount=total,
        transport_mode=payload.transport_mode or shipment.transport_mode,
        bl_awb_no=payload.bl_awb_no or shipment.awb_no or shipment.bl_no,
        vessel_flight=payload.vessel_flight or shipment.vessel_name,
        port_of_loading=payload.port_of_loading or shipment.port_of_loading,
        port_of_discharge=payload.port_of_discharge or shipment.port_of_discharge,
        notes=payload.notes,
        status="draft",
        created_by=current_user.id,
    )
    inv.items = items
    db.add(inv)
    db.commit()

    return _invoice_to_out(
        db.query(Invoice).options(joinedload(Invoice.items))
        .filter(Invoice.id == inv.id).first()
    )


@router.get("/{invoice_id}", response_model=InvoiceOut)
def get_invoice(
    invoice_id: UUID,
    db: Session = Depends(get_db),
    _: User = Depends(check_permission("shipment", "read")),
):
    """取得發票詳情"""
    inv = db.query(Invoice).options(joinedload(Invoice.items)).filter(Invoice.id == invoice_id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="發票不存在")
    return _invoice_to_out(inv)


@router.put("/{invoice_id}", response_model=InvoiceOut)
def update_invoice(
    invoice_id: UUID,
    payload: InvoiceUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(check_permission("shipment", "update")),
):
    """編輯發票"""
    inv = db.query(Invoice).options(joinedload(Invoice.items)).filter(Invoice.id == invoice_id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="發票不存在")
    if inv.status not in ("draft", "confirmed"):
        raise HTTPException(status_code=400, detail="只有草稿或已確認的發票可以編輯")

    data = payload.model_dump(exclude_unset=True)

    # 更新明細
    if "items" in data:
        # 清除舊明細
        for old_item in inv.items:
            db.delete(old_item)
        db.flush()

        subtotal = Decimal("0")
        new_items = []
        for it_data in data.pop("items"):
            it = InvoiceItemCreate(**it_data) if isinstance(it_data, dict) else it_data
            item_amount = it.amount
            if not item_amount and it.quantity_kg and it.unit_price:
                item_amount = it.quantity_kg * it.unit_price
            if item_amount:
                subtotal += item_amount

            new_items.append(InvoiceItem(
                invoice_id=inv.id,
                batch_id=UUID(it.batch_id) if it.batch_id else None,
                description=it.description,
                hs_code=it.hs_code,
                quantity_kg=it.quantity_kg,
                quantity_boxes=it.quantity_boxes,
                unit_price=it.unit_price,
                amount=item_amount,
                origin_country=it.origin_country,
                notes=it.notes,
            ))
        for ni in new_items:
            db.add(ni)
        inv.subtotal = subtotal

    # 更新其他欄位
    for k, v in data.items():
        setattr(inv, k, v)

    # 重算總金額
    inv.total_amount = (
        (inv.subtotal or 0) +
        (inv.freight_charge or 0) +
        (inv.insurance_charge or 0) +
        (inv.other_charge or 0)
    )

    db.commit()
    return _invoice_to_out(
        db.query(Invoice).options(joinedload(Invoice.items))
        .filter(Invoice.id == inv.id).first()
    )


@router.put("/{invoice_id}/status")
def update_invoice_status(
    invoice_id: UUID,
    new_status: str = Query(..., alias="status"),
    db: Session = Depends(get_db),
    _: User = Depends(check_permission("shipment", "update")),
):
    """更新發票狀態"""
    valid = ["draft", "confirmed", "sent", "paid"]
    if new_status not in valid:
        raise HTTPException(status_code=400, detail=f"無效狀態，可用：{valid}")

    inv = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="發票不存在")
    inv.status = new_status
    db.commit()
    return {"message": "狀態已更新", "status": new_status}


@router.delete("/{invoice_id}")
def delete_invoice(
    invoice_id: UUID,
    db: Session = Depends(get_db),
    _: User = Depends(check_permission("shipment", "delete")),
):
    """刪除草稿發票"""
    inv = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="發票不存在")
    if inv.status != "draft":
        raise HTTPException(status_code=400, detail="只有草稿發票可以刪除")
    db.delete(inv)
    db.commit()
    return {"message": "發票已刪除"}


@router.get("/{invoice_id}/html")
def get_invoice_html(
    invoice_id: UUID,
    db: Session = Depends(get_db),
    _: User = Depends(check_permission("shipment", "read")),
):
    """產生發票 HTML（可直接列印或轉 PDF）"""
    inv = db.query(Invoice).options(joinedload(Invoice.items)).filter(Invoice.id == invoice_id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="發票不存在")

    # 發票 HTML 模板
    items_html = ""
    for i, it in enumerate(inv.items or [], 1):
        items_html += f"""
        <tr>
            <td style="padding:6px 8px;border:1px solid #ddd;text-align:center">{i}</td>
            <td style="padding:6px 8px;border:1px solid #ddd">{it.description}</td>
            <td style="padding:6px 8px;border:1px solid #ddd;text-align:center">{it.hs_code or '—'}</td>
            <td style="padding:6px 8px;border:1px solid #ddd;text-align:center">{it.origin_country or 'Thailand'}</td>
            <td style="padding:6px 8px;border:1px solid #ddd;text-align:right">{float(it.quantity_kg or 0):,.2f}</td>
            <td style="padding:6px 8px;border:1px solid #ddd;text-align:right">{it.quantity_boxes or '—'}</td>
            <td style="padding:6px 8px;border:1px solid #ddd;text-align:right">{float(it.unit_price or 0):,.2f}</td>
            <td style="padding:6px 8px;border:1px solid #ddd;text-align:right"><strong>{float(it.amount or 0):,.2f}</strong></td>
        </tr>"""

    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Invoice {inv.invoice_no}</title>
<style>
  body {{ font-family: Arial, sans-serif; font-size: 12px; color: #333; margin: 30px; }}
  h1 {{ text-align: center; font-size: 22px; margin-bottom: 5px; }}
  .header {{ display: flex; justify-content: space-between; margin-bottom: 20px; }}
  .party {{ width: 48%; }}
  .party h3 {{ font-size: 13px; color: #666; border-bottom: 1px solid #ddd; padding-bottom: 4px; }}
  .info-grid {{ display: flex; justify-content: space-between; margin-bottom: 15px; }}
  .info-grid div {{ width: 30%; }}
  .info-grid label {{ font-weight: bold; display: block; font-size: 11px; color: #666; }}
  table {{ width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 11px; }}
  th {{ background: #f5f5f5; padding: 8px; border: 1px solid #ddd; text-align: center; font-size: 11px; }}
  .totals {{ margin-top: 15px; text-align: right; }}
  .totals table {{ width: 300px; margin-left: auto; }}
  .totals td {{ padding: 4px 8px; }}
  .grand-total {{ font-size: 16px; font-weight: bold; color: #1a5276; }}
  .footer {{ margin-top: 40px; display: flex; justify-content: space-between; }}
  .sig {{ width: 200px; text-align: center; border-top: 1px solid #333; padding-top: 5px; }}
  @media print {{ body {{ margin: 15px; }} }}
</style>
</head>
<body>
<h1>COMMERCIAL INVOICE</h1>
<p style="text-align:center;color:#666;margin-bottom:20px">商業發票</p>

<div class="info-grid">
  <div><label>Invoice No. 發票號碼</label>{inv.invoice_no}</div>
  <div><label>Date 日期</label>{inv.invoice_date}</div>
  <div><label>Due Date 到期日</label>{inv.due_date or '—'}</div>
</div>

<div class="header">
  <div class="party">
    <h3>SELLER 賣方</h3>
    <p><strong>{inv.seller_name}</strong></p>
    <p>{inv.seller_address or ''}</p>
    <p>Tax ID: {inv.seller_tax_id or '—'}</p>
    <p>Contact: {inv.seller_contact or '—'} / {inv.seller_phone or ''}</p>
    <p>Email: {inv.seller_email or '—'}</p>
  </div>
  <div class="party">
    <h3>BUYER 買方</h3>
    <p><strong>{inv.buyer_name}</strong></p>
    <p>{inv.buyer_address or ''}</p>
    <p>Tax ID / 統一編號: {inv.buyer_tax_id or '—'}</p>
    <p>Contact: {inv.buyer_contact or '—'} / {inv.buyer_phone or ''}</p>
    <p>Email: {inv.buyer_email or '—'}</p>
  </div>
</div>

<div class="info-grid">
  <div><label>Currency 幣別</label>{inv.currency}</div>
  <div><label>Incoterms 貿易條件</label>{inv.incoterms or '—'}</div>
  <div><label>Payment Terms 付款條件</label>{inv.payment_terms or '—'}</div>
</div>
<div class="info-grid">
  <div><label>Transport 運輸方式</label>{'Air 空運' if inv.transport_mode == 'air' else 'Sea 海運' if inv.transport_mode == 'sea' else '—'}</div>
  <div><label>BL/AWB No.</label>{inv.bl_awb_no or '—'}</div>
  <div><label>Vessel/Flight</label>{inv.vessel_flight or '—'}</div>
</div>
<div class="info-grid">
  <div><label>Port of Loading 裝貨港</label>{inv.port_of_loading or '—'}</div>
  <div><label>Port of Discharge 卸貨港</label>{inv.port_of_discharge or '—'}</div>
  <div></div>
</div>

<table>
  <thead>
    <tr>
      <th style="width:30px">No.</th>
      <th>Description 品名</th>
      <th>HS Code</th>
      <th>Origin 產地</th>
      <th>Qty (kg)</th>
      <th>Boxes 箱數</th>
      <th>Unit Price 單價</th>
      <th>Amount 金額</th>
    </tr>
  </thead>
  <tbody>
    {items_html}
  </tbody>
</table>

<div class="totals">
  <table>
    <tr><td>Subtotal 小計</td><td class="grand-total" style="font-size:12px">{inv.currency} {float(inv.subtotal or 0):,.2f}</td></tr>
    <tr><td>Freight 運費</td><td>{inv.currency} {float(inv.freight_charge or 0):,.2f}</td></tr>
    <tr><td>Insurance 保險</td><td>{inv.currency} {float(inv.insurance_charge or 0):,.2f}</td></tr>
    <tr><td>Other 其他</td><td>{inv.currency} {float(inv.other_charge or 0):,.2f}</td></tr>
    <tr style="border-top:2px solid #333"><td><strong>TOTAL 總金額</strong></td><td class="grand-total">{inv.currency} {float(inv.total_amount or 0):,.2f}</td></tr>
  </table>
</div>

{f'<p style="margin-top:15px;color:#666"><strong>Notes 備註:</strong> {inv.notes}</p>' if inv.notes else ''}

<div class="footer">
  <div class="sig">Authorized Signature<br>賣方簽章</div>
  <div class="sig">Received By<br>買方簽收</div>
</div>
</body>
</html>"""

    return StreamingResponse(
        io.BytesIO(html.encode("utf-8")),
        media_type="text/html",
        headers={"Content-Disposition": f'inline; filename="invoice_{inv.invoice_no}.html"'}
    )
