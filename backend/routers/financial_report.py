"""
財務報表 API（I-08 跨幣別損益表、I-09 泰國稅務）

端點：
  GET /finance/pnl                — 跨幣別月度損益表
  GET /finance/pnl/monthly-trend — 月度損益趨勢（最近 N 個月）
  GET /finance/fx-gain-loss       — 匯兌損益明細
  GET /finance/thai-tax           — 泰國稅務計算（WHT + VAT）
  GET /finance/wht-report         — 預扣稅報表
  GET /exchange-rates/monthly-avg — 月均匯率
"""
import logging
from calendar import monthrange
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from database import get_db
from utils.dependencies import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/finance", tags=["財務報表"])


# ═══════════════════════════════════════════════════
# I-01 月均匯率（掛在 exchange-rates 子路由）
# ═══════════════════════════════════════════════════

@router.get("/exchange-rates/monthly-avg", tags=["匯率"], summary="月均匯率查詢")
def get_monthly_avg_rate(
    year:      int = Query(..., description="年度"),
    month:     int = Query(..., description="月份 1-12"),
    from_curr: str = Query("THB", description="來源幣別"),
    to_curr:   str = Query("TWD", description="目標幣別"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """計算該月所有匯率記錄的平均值"""
    from models.exchange_rate import ExchangeRate
    from decimal import Decimal

    first_day = date(year, month, 1)
    last_day  = date(year, month, monthrange(year, month)[1])

    rows = (
        db.query(ExchangeRate)
        .filter(
            ExchangeRate.from_currency == from_curr,
            ExchangeRate.to_currency   == to_curr,
            ExchangeRate.effective_date >= first_day,
            ExchangeRate.effective_date <= last_day,
        )
        .all()
    )

    if not rows:
        return {
            "year": year,
            "month": month,
            "from_currency": from_curr,
            "to_currency": to_curr,
            "avg_rate": None,
            "data_points": 0,
            "message": "本月無匯率資料",
        }

    rates = [float(r.rate) for r in rows]
    avg_rate = sum(rates) / len(rates)

    return {
        "year": year,
        "month": month,
        "from_currency": from_curr,
        "to_currency": to_curr,
        "avg_rate": round(avg_rate, 4),
        "min_rate": round(min(rates), 4),
        "max_rate": round(max(rates), 4),
        "data_points": len(rows),
        "period": f"{first_day.isoformat()} ~ {last_day.isoformat()}",
    }


# ═══════════════════════════════════════════════════
# I-08 跨幣別損益表
# ═══════════════════════════════════════════════════

@router.get("/pnl", summary="跨幣別月度損益表")
def get_monthly_pnl(
    year:  int = Query(..., description="年度"),
    month: int = Query(..., description="月份 1-12"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    月度損益表：
    - 營收（TWD）= 已確認銷售訂單金額
    - 採購成本（THB × 月均匯率 → TWD）
    - 物流成本（TWD）
    - 其他成本（TWD）
    - 毛利 = 營收 - 採購成本 - 物流成本
    - 匯兌損益（快照匯率 vs 月均匯率差異）
    """
    from models.sales import SalesOrder
    from models.purchase import PurchaseOrder
    from models.cost import CostEvent
    from models.exchange_rate import ExchangeRate
    from sqlalchemy import func

    first_day = date(year, month, 1)
    last_day  = date(year, month, monthrange(year, month)[1])

    # 1. 營收（TWD）— 本月確認的銷售訂單
    revenue_row = (
        db.query(func.sum(SalesOrder.total_amount_twd).label("revenue"))
        .filter(
            SalesOrder.status.notin_(["draft", "cancelled"]),
            SalesOrder.order_date >= first_day,
            SalesOrder.order_date <= last_day,
        )
        .first()
    )
    revenue_twd = float(revenue_row.revenue or 0)

    # 2. 月均匯率 THB→TWD
    rate_rows = (
        db.query(ExchangeRate)
        .filter(
            ExchangeRate.from_currency == "THB",
            ExchangeRate.to_currency   == "TWD",
            ExchangeRate.effective_date >= first_day,
            ExchangeRate.effective_date <= last_day,
        )
        .all()
    )
    if rate_rows:
        monthly_avg_rate = sum(float(r.rate) for r in rate_rows) / len(rate_rows)
    else:
        monthly_avg_rate = None

    # 3. 採購成本（THB）
    po_row = (
        db.query(func.sum(PurchaseOrder.total_amount_thb).label("po_thb"))
        .filter(
            PurchaseOrder.status.notin_(["draft", "cancelled"]),
            PurchaseOrder.order_date >= first_day,
            PurchaseOrder.order_date <= last_day,
        )
        .first()
    )
    po_thb = float(po_row.po_thb or 0)
    po_twd = po_thb * monthly_avg_rate if monthly_avg_rate else None

    # 4. 其他成本事件（TWD）
    cost_row = (
        db.query(func.sum(CostEvent.amount_twd).label("cost_twd"))
        .filter(
            CostEvent.event_date >= first_day,
            CostEvent.event_date <= last_day,
        )
        .first()
    )
    other_cost_twd = float(cost_row.cost_twd or 0)

    # 5. 毛利計算
    gross_profit = None
    gross_margin_pct = None
    if po_twd is not None:
        gross_profit = revenue_twd - po_twd - other_cost_twd
        gross_margin_pct = (gross_profit / revenue_twd * 100) if revenue_twd > 0 else 0

    return {
        "year":  year,
        "month": month,
        "period": f"{first_day.isoformat()} ~ {last_day.isoformat()}",
        "revenue_twd":         round(revenue_twd, 2),
        "purchase_cost_thb":   round(po_thb, 2),
        "monthly_avg_rate":    round(monthly_avg_rate, 4) if monthly_avg_rate else None,
        "purchase_cost_twd":   round(po_twd, 2) if po_twd is not None else None,
        "other_cost_twd":      round(other_cost_twd, 2),
        "total_cost_twd":      round((po_twd or 0) + other_cost_twd, 2),
        "gross_profit_twd":    round(gross_profit, 2) if gross_profit is not None else None,
        "gross_margin_pct":    round(gross_margin_pct, 2) if gross_margin_pct is not None else None,
        "note": "匯率資料不足，採購成本無法換算" if monthly_avg_rate is None else None,
    }


@router.get("/pnl/monthly-trend", summary="月度損益趨勢")
def get_pnl_trend(
    months: int = Query(6, ge=1, le=24, description="回顧月數"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """回傳最近 N 個月的損益摘要"""
    today = date.today()
    results = []

    # 從今月往前回溯（不用 dateutil，手動計算月份）
    year  = today.year
    month = today.month
    periods = []
    for _ in range(months):
        periods.append((year, month))
        month -= 1
        if month == 0:
            month = 12
            year -= 1
    periods.reverse()

    for y, m in periods:
        pnl = get_monthly_pnl(y, m, db=db, current_user=current_user)
        results.append({
            "year":  y,
            "month": m,
            "label": f"{y}/{m:02d}",
            "revenue_twd":      pnl["revenue_twd"],
            "gross_profit_twd": pnl["gross_profit_twd"],
            "gross_margin_pct": pnl["gross_margin_pct"],
        })

    return {"months": months, "trend": results}


@router.get("/fx-gain-loss", summary="匯兌損益明細")
def get_fx_gain_loss(
    year:  int = Query(...),
    month: int = Query(...),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    計算本月匯兌損益：
    以銷售訂單成交匯率 vs 月均匯率計算理論匯兌損益
    """
    from models.sales import SalesOrder
    from models.exchange_rate import ExchangeRate

    first_day = date(year, month, 1)
    last_day  = date(year, month, monthrange(year, month)[1])

    # 月均匯率
    rate_rows = (
        db.query(ExchangeRate)
        .filter(
            ExchangeRate.from_currency == "THB",
            ExchangeRate.to_currency   == "TWD",
            ExchangeRate.effective_date >= first_day,
            ExchangeRate.effective_date <= last_day,
        )
        .all()
    )
    monthly_avg = (sum(float(r.rate) for r in rate_rows) / len(rate_rows)) if rate_rows else None

    if not monthly_avg:
        return {"message": "本月無匯率資料，無法計算匯兌損益"}

    # 取有 exchange_rate 快照的銷售訂單
    orders = (
        db.query(SalesOrder)
        .filter(
            SalesOrder.status.notin_(["draft", "cancelled"]),
            SalesOrder.order_date >= first_day,
            SalesOrder.order_date <= last_day,
            SalesOrder.exchange_rate.isnot(None),
        )
        .all()
    )

    total_fx_gain_loss = 0.0
    details = []
    for order in orders:
        if order.currency != "THB":
            continue
        snap_rate = float(order.exchange_rate)
        amount_thb = float(order.total_amount_twd or 0) / snap_rate if snap_rate else 0
        fx_delta = (snap_rate - monthly_avg) * amount_thb
        total_fx_gain_loss += fx_delta
        details.append({
            "order_id":     str(order.id),
            "order_date":   order.order_date.isoformat(),
            "currency":     order.currency,
            "snap_rate":    round(snap_rate, 4),
            "monthly_avg_rate": round(monthly_avg, 4),
            "estimated_fx_pnl_twd": round(fx_delta, 2),
        })

    return {
        "year":  year,
        "month": month,
        "monthly_avg_rate":        round(monthly_avg, 4),
        "total_fx_gain_loss_twd":  round(total_fx_gain_loss, 2),
        "order_count": len(details),
        "details": details,
    }


# ═══════════════════════════════════════════════════
# I-09 泰國稅務（WHT + VAT）
# ═══════════════════════════════════════════════════

# 泰國預扣稅率表（依供應商類型）
WHT_RATES = {
    "farmer":      0.01,   # 農民 1%
    "sme":         0.02,   # 中小企業 2%
    "corporate":   0.03,   # 公司 3%
    "service":     0.03,   # 服務業 3%
    "professional": 0.03,  # 專業服務 3%
    "rental":      0.05,   # 租金 5%
    "dividend":    0.10,   # 股息 10%
}

THAILAND_VAT_RATE = 0.07  # 泰國 VAT 7%


@router.get("/thai-tax", summary="泰國稅務計算試算")
def calc_thai_tax(
    amount_thb: float = Query(..., description="稅前金額（THB）"),
    supplier_type: str = Query("corporate", description=f"供應商類型: {list(WHT_RATES.keys())}"),
    include_vat: bool = Query(True, description="是否含 VAT"),
    current_user=Depends(get_current_user),
):
    """
    泰國稅務試算：
    - WHT（預扣稅）：依供應商類型 1~10%
    - VAT 7%（進項稅額）
    """
    wht_rate = WHT_RATES.get(supplier_type, 0.03)

    vat_amount    = amount_thb * THAILAND_VAT_RATE if include_vat else 0
    wht_amount    = amount_thb * wht_rate
    gross_amount  = amount_thb + vat_amount
    net_payable   = gross_amount - wht_amount

    return {
        "amount_thb":     round(amount_thb, 2),
        "supplier_type":  supplier_type,
        "vat_rate_pct":   THAILAND_VAT_RATE * 100 if include_vat else 0,
        "vat_amount":     round(vat_amount, 2),
        "wht_rate_pct":   wht_rate * 100,
        "wht_amount":     round(wht_amount, 2),
        "gross_amount":   round(gross_amount, 2),
        "net_payable":    round(net_payable, 2),
        "note": "WHT 由付款方扣繳並代繳國稅局，VAT 憑進項發票申報退稅",
    }


@router.get("/wht-report", summary="預扣稅月報")
def get_wht_report(
    year:  int = Query(...),
    month: int = Query(...),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    本月應付款項的 WHT 彙總報表
    （從 AccountPayable 的 THB 金額計算）
    """
    from models.finance import AccountPayable
    from models.supplier import Supplier

    first_day = date(year, month, 1)
    last_day  = date(year, month, monthrange(year, month)[1])

    ap_records = (
        db.query(AccountPayable)
        .filter(
            AccountPayable.currency == "THB",
            AccountPayable.due_date >= first_day,
            AccountPayable.due_date <= last_day,
            AccountPayable.status.notin_(["cancelled"]),
        )
        .all()
    )

    total_base   = 0.0
    total_wht    = 0.0
    total_vat    = 0.0
    items        = []

    for ap in ap_records:
        amount = float(ap.amount or 0)
        # 預設 corporate 3%（可在 Supplier 擴充 supplier_tax_type 欄位）
        wht_rate = 0.03
        wht_amount = amount * wht_rate
        vat_amount = amount * THAILAND_VAT_RATE

        total_base += amount
        total_wht  += wht_amount
        total_vat  += vat_amount

        items.append({
            "ap_id":      str(ap.id),
            "due_date":   ap.due_date.isoformat() if ap.due_date else None,
            "amount_thb": round(amount, 2),
            "wht_rate":   f"{wht_rate*100:.0f}%",
            "wht_amount": round(wht_amount, 2),
            "vat_amount": round(vat_amount, 2),
            "net_payable": round(amount + vat_amount - wht_amount, 2),
        })

    return {
        "year":  year,
        "month": month,
        "total_base_thb":  round(total_base, 2),
        "total_wht_thb":   round(total_wht, 2),
        "total_vat_thb":   round(total_vat, 2),
        "net_payable_thb": round(total_base + total_vat - total_wht, 2),
        "record_count": len(items),
        "items": items,
    }
