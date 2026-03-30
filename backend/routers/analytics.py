"""
成本 / 利潤分析 API
GET  /analytics/summary          - 全局統計摘要
GET  /analytics/batches          - 各批次成本與收入明細（含落地成本）
GET  /analytics/daily            - 每日銷售匯總
POST /analytics/send-cost-report - 發送成本利潤報表 Email
"""
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import date
from typing import Optional, List
from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func

from database import get_db
from models.user import User
from models.purchase import PurchaseOrder
from models.batch import Batch
from models.cost import CostEvent
from models.shipment import Shipment, ShipmentBatch
from models.sales import SalesOrder, SalesOrderItem
from models.daily_sale import DailySale, DailySaleItem
from models.inventory import InventoryLot
from models.payment import PaymentRecord
from utils.dependencies import check_permission
from config import settings

router = APIRouter(prefix="/analytics", tags=["成本分析"])


@router.get("/summary")
def get_summary(
    db: Session = Depends(get_db),
    _:  User = Depends(check_permission("report", "view")),
):
    """全局摘要統計"""
    # 採購成本（已到廠 + 已結案的採購單）
    purchase_cost = db.query(
        func.coalesce(func.sum(PurchaseOrder.total_amount), 0)
    ).filter(PurchaseOrder.status.in_(["arrived", "closed"])).scalar()

    # 銷售收入（訂單）
    so_revenue = db.query(
        func.coalesce(func.sum(SalesOrder.total_amount_twd), 0)
    ).filter(SalesOrder.status.in_(["confirmed", "delivered", "invoiced", "closed"])).scalar()

    # 每日銷售收入
    ds_revenue = db.query(
        func.coalesce(func.sum(DailySale.total_amount_twd), 0)
    ).scalar()

    total_revenue = float(so_revenue) + float(ds_revenue)

    # 總成本（CostEvent）
    total_cost_thb = db.query(
        func.coalesce(func.sum(CostEvent.amount_thb), 0)
    ).scalar()
    total_cost_twd = db.query(
        func.coalesce(func.sum(CostEvent.amount_twd), 0)
    ).scalar()

    # 回款
    confirmed_payments = db.query(
        func.coalesce(func.sum(PaymentRecord.amount_twd), 0)
    ).filter(PaymentRecord.status == "confirmed").scalar()

    # 批次統計
    batch_stats = {}
    for s in ["processing", "qc_pending", "qc_done", "packaging",
              "ready_to_export", "exported", "in_transit_tw",
              "in_stock", "sold", "closed"]:
        batch_stats[s] = db.query(func.count(Batch.id)).filter(Batch.status == s).scalar()

    # 庫存統計
    active_lots = db.query(func.count(InventoryLot.id)).filter(
        InventoryLot.status.in_(["active", "low_stock"])
    ).scalar()
    stock_weight = db.query(
        func.coalesce(func.sum(InventoryLot.current_weight_kg), 0)
    ).filter(InventoryLot.status.in_(["active", "low_stock"])).scalar()

    return {
        "purchase_cost_thb":     float(purchase_cost),
        "total_cost_events_thb": float(total_cost_thb),
        "total_cost_events_twd": float(total_cost_twd),
        "sales_revenue_so_twd":  float(so_revenue),
        "sales_revenue_ds_twd":  float(ds_revenue),
        "total_revenue_twd":     total_revenue,
        "confirmed_payments_twd": float(confirmed_payments),
        "total_batches":         sum(batch_stats.values()),
        "batch_by_status":       batch_stats,
        "active_lots":           active_lots,
        "stock_weight_kg":       float(stock_weight),
    }


@router.get("/batches")
def get_batch_analytics(
    exchange_rate: float = Query(default=0.92, description="THB→TWD 匯率"),
    db: Session = Depends(get_db),
    _:  User = Depends(check_permission("report", "view")),
):
    """各批次成本與銷售收入明細"""
    batches = db.query(Batch).all()
    if not batches:
        return []

    batch_ids = [b.id for b in batches]

    # 一次撈採購單
    po_map = {}
    pos = db.query(PurchaseOrder).filter(
        PurchaseOrder.id.in_([b.purchase_order_id for b in batches if b.purchase_order_id])
    ).all()
    for po in pos:
        po_map[po.id] = po

    # 成本事件依批次分組
    cost_rows = db.query(
        CostEvent.batch_id,
        CostEvent.cost_layer,
        func.sum(
            func.coalesce(CostEvent.amount_twd, 0)
            + func.coalesce(CostEvent.amount_thb, 0) * exchange_rate
        ).label("total_twd"),
    ).filter(CostEvent.batch_id.in_(batch_ids)).group_by(
        CostEvent.batch_id, CostEvent.cost_layer
    ).all()

    cost_map = {}  # batch_id -> {layer: twd}
    for r in cost_rows:
        cost_map.setdefault(r.batch_id, {})[r.cost_layer] = float(r.total_twd)

    # 銷售收入（SalesOrderItem）
    so_rows = db.query(
        SalesOrderItem.batch_id,
        func.coalesce(func.sum(SalesOrderItem.total_amount_twd), 0).label("revenue"),
    ).filter(SalesOrderItem.batch_id.in_(batch_ids)).group_by(SalesOrderItem.batch_id).all()
    so_map = {r.batch_id: float(r.revenue) for r in so_rows}

    # 每日銷售收入
    ds_rows = db.query(
        DailySaleItem.batch_id,
        func.coalesce(func.sum(DailySaleItem.total_amount_twd), 0).label("revenue"),
    ).filter(DailySaleItem.batch_id.in_(batch_ids)).group_by(DailySaleItem.batch_id).all()
    ds_map = {r.batch_id: float(r.revenue) for r in ds_rows}

    result = []
    for batch in batches:
        po = po_map.get(batch.purchase_order_id)
        layers = cost_map.get(batch.id, {})
        total_cost = sum(layers.values())
        weight = float(batch.current_weight) if float(batch.current_weight) > 0 else 1
        revenue = so_map.get(batch.id, 0) + ds_map.get(batch.id, 0)
        profit = revenue - total_cost
        margin = (profit / revenue * 100) if revenue > 0 else None

        result.append({
            "batch_id":          str(batch.id),
            "batch_no":          batch.batch_no,
            "status":            batch.status,
            "initial_weight_kg": float(batch.initial_weight),
            "current_weight_kg": float(batch.current_weight),
            "po_order_no":       po.order_no if po else None,
            "cost_by_layer":     {k: round(v, 2) for k, v in layers.items()},
            "total_cost_twd":    round(total_cost, 0),
            "cost_per_kg_twd":   round(total_cost / weight, 1),
            "sales_revenue_twd": round(revenue, 0),
            "gross_profit_twd":  round(profit, 0),
            "gross_margin_pct":  round(margin, 1) if margin is not None else None,
        })

    return result


@router.get("/daily")
def get_daily_summary(
    date_from: Optional[date] = Query(None),
    date_to:   Optional[date] = Query(None),
    db: Session = Depends(get_db),
    _:  User = Depends(check_permission("report", "view")),
):
    """每日銷售匯總"""
    q = db.query(
        DailySale.sale_date,
        DailySale.market_code,
        func.sum(DailySale.total_kg).label("total_kg"),
        func.sum(DailySale.total_boxes).label("total_boxes"),
        func.sum(DailySale.total_amount_twd).label("total_amount_twd"),
        func.count(DailySale.id).label("sale_count"),
    )
    if date_from:
        q = q.filter(DailySale.sale_date >= date_from)
    if date_to:
        q = q.filter(DailySale.sale_date <= date_to)

    rows = q.group_by(DailySale.sale_date, DailySale.market_code).order_by(
        DailySale.sale_date.desc(), DailySale.market_code
    ).all()

    return [{
        "sale_date":        str(r.sale_date),
        "market_code":      r.market_code,
        "total_kg":         float(r.total_kg),
        "total_boxes":      r.total_boxes,
        "total_amount_twd": float(r.total_amount_twd),
        "sale_count":       r.sale_count,
    } for r in rows]


# ─── Email 發送請求 Schema ────────────────────────────────────

class SendCostReportRequest(BaseModel):
    """發送成本利潤報表 Email 的請求體"""
    to_emails:    List[str]        # 收件人 email 列表
    subject:      str = "批次成本利潤報表"  # 信件主旨
    batch_ids:    List[str] = []   # 要包含的批次 IDs（空則發全部）
    html_content: str              # 前端傳來的 HTML 報表內容


@router.post("/send-cost-report")
def send_cost_report(
    payload: SendCostReportRequest,
    _: User = Depends(check_permission("report", "view")),
):
    """
    發送成本利潤報表 Email。
    前端負責生成 HTML 報表內容，後端直接放入 email body 並透過 SMTP 發送。
    若 SMTP 設定未完成（SMTP_HOST 為空），回傳 400 錯誤。
    """
    # 驗證 SMTP 是否已設定
    if not settings.SMTP_HOST:
        raise HTTPException(
            status_code=400,
            detail="SMTP 尚未設定，請在環境變數中設定 SMTP_HOST / SMTP_USER / SMTP_PASSWORD",
        )
    if not payload.to_emails:
        raise HTTPException(status_code=400, detail="收件人 email 列表不可為空")

    # 組裝 MIME 信件
    msg = MIMEMultipart("alternative")
    msg["Subject"] = payload.subject
    msg["From"]    = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM or settings.SMTP_USER}>"
    msg["To"]      = ", ".join(payload.to_emails)

    # 設定 HTML 正文
    html_part = MIMEText(payload.html_content, "html", "utf-8")
    msg.attach(html_part)

    # 透過 smtplib 發送（使用 STARTTLS）
    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15) as server:
            server.ehlo()
            server.starttls()          # 啟用 TLS 加密
            server.ehlo()
            if settings.SMTP_USER and settings.SMTP_PASSWORD:
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(
                from_addr=settings.SMTP_FROM or settings.SMTP_USER,
                to_addrs=payload.to_emails,
                msg=msg.as_string(),
            )
    except smtplib.SMTPException as e:
        raise HTTPException(status_code=500, detail=f"Email 發送失敗：{str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"連線 SMTP 失敗：{str(e)}")

    return {"sent": True, "to": payload.to_emails}
