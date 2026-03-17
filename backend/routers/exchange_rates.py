"""
匯率管理 API
GET    /exchange-rates          - 匯率歷史列表
POST   /exchange-rates          - 新增匯率
GET    /exchange-rates/latest   - 取得最新匯率
GET    /exchange-rates/live     - 即時匯率（玉山銀行優先 → 台灣銀行 → open.er-api 備援）
GET    /exchange-rates/compare  - 比較 TWD→THB 直接 vs TWD→USD→THB 哪條路線較划算
"""
from uuid import UUID
from datetime import date, datetime
from typing import List, Optional
import csv, io, logging, re

import httpx

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from database import get_db
from models.user import User
from models.exchange_rate import ExchangeRate
from schemas.exchange_rate import ExchangeRateCreate, ExchangeRateOut
from utils.dependencies import check_permission

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/exchange-rates", tags=["匯率"])


# ─── 外部匯率抓取工具 ─────────────────────────────────────────────

def _fetch_esun_rates() -> dict:
    """
    從玉山銀行網站爬取即時牌告匯率（主要來源）。
    頁面格式：class="BBoardRate">數字  /  class="SBoardRate">數字
    台灣銀行報價方式：1 外幣 = X 台幣（BBoardRate=買入, SBoardRate=賣出）

    回傳格式與 _fetch_bot_rates 相同：
    { "THB": {"spot_buy": X, "spot_sell": X, "cash_buy": X, "cash_sell": X}, "USD": {...} }
    """
    url = "https://www.esunbank.com/zh-tw/personal/deposit/rate/forex/foreign-exchange-rates"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
        )
    }
    result = {}
    try:
        with httpx.Client(timeout=12, follow_redirects=True) as client:
            resp = client.get(url, headers=headers)
            resp.raise_for_status()
            text = resp.text

        for code in ("THB", "USD"):
            # 找該幣別所在的 HTML 區塊
            idx = text.find(f'{code} currency">')
            if idx < 0:
                continue
            chunk = text[idx: idx + 3000]

            # 抓取各種牌告匯率（格式：class="XBoardRate">數字）
            rates_found = re.findall(r'class="(\w+BoardRate)">([0-9.]+)<', chunk)
            rate_map = {k: float(v) for k, v in rates_found}

            # BBoardRate=即期買入, SBoardRate=即期賣出
            # CashBBoardRate=現鈔買入, CashSBoardRate=現鈔賣出
            entry = {
                "spot_buy":  rate_map.get("BBoardRate"),
                "spot_sell": rate_map.get("SBoardRate"),
                "cash_buy":  rate_map.get("CashBBoardRate") or rate_map.get("BBoardRate"),
                "cash_sell": rate_map.get("CashSBoardRate") or rate_map.get("SBoardRate"),
            }
            if entry["spot_sell"]:
                result[code] = entry

        if result:
            logger.info(f"玉山銀行匯率抓取成功：{list(result.keys())}")
    except Exception as e:
        logger.warning(f"玉山銀行匯率抓取失敗：{e}")
    return result


def _fetch_bot_rates() -> dict:
    """
    從台灣銀行（Bank of Taiwan）抓取當日外幣牌告匯率。
    回傳 dict：{ "THB": {"buy": ..., "sell": ...}, "USD": {...} }
    資料來源：https://rate.bot.com.tw/xrt/flcsv/0/day
    欄位順序：幣別, 現金買入, 現金賣出, 即期買入, 即期賣出, 遠期10天買入, ...
    """
    url = "https://rate.bot.com.tw/xrt/flcsv/0/day"
    headers = {"User-Agent": "Mozilla/5.0 (compatible; ERP-RateBot/1.0)"}
    result = {}
    try:
        with httpx.Client(timeout=10) as client:
            resp = client.get(url, headers=headers)
            resp.raise_for_status()
            # 台灣銀行 CSV 使用 Big5 或 UTF-8（視版本而定），先試 UTF-8
            text = resp.content.decode("utf-8-sig", errors="replace")
            reader = csv.reader(io.StringIO(text))
            for row in reader:
                if len(row) < 5:
                    continue
                # 第一欄格式：「泰銖 (THB)」或「美元 (USD)」
                currency_field = row[0].strip()
                if "THB" in currency_field or "USD" in currency_field:
                    code = "THB" if "THB" in currency_field else "USD"
                    try:
                        # 現金買入=col[1], 現金賣出=col[2], 即期買入=col[3], 即期賣出=col[4]
                        cash_sell   = float(row[2]) if row[2].strip() else None
                        spot_sell   = float(row[4]) if row[4].strip() else None
                        cash_buy    = float(row[1]) if row[1].strip() else None
                        spot_buy    = float(row[3]) if row[3].strip() else None
                        result[code] = {
                            "cash_buy":  cash_buy,
                            "cash_sell": cash_sell,
                            "spot_buy":  spot_buy,
                            "spot_sell": spot_sell,
                        }
                    except (ValueError, IndexError):
                        pass
    except Exception as e:
        logger.warning(f"台灣銀行匯率抓取失敗：{e}")
    return result


def _fetch_open_er(base: str = "TWD") -> dict:
    """
    備援：從 open.er-api.com 抓取中間匯率（免費、無需 API Key）。
    回傳 dict：{ "THB": 1.07, "USD": 0.031, ... }（以 base 幣別為基準）
    """
    url = f"https://open.er-api.com/v6/latest/{base}"
    try:
        with httpx.Client(timeout=10) as client:
            resp = client.get(url)
            resp.raise_for_status()
            data = resp.json()
            if data.get("result") == "success":
                return data.get("rates", {})
    except Exception as e:
        logger.warning(f"open.er-api 抓取失敗：{e}")
    return {}


def _fetch_all_live_rates() -> dict:
    """
    整合多個來源抓取即時匯率，優先順序：
      1. 玉山銀行（台灣最常用的外匯銀行，爬蟲抓取）
      2. 台灣銀行（牌告匯率 CSV）
      3. open.er-api.com（國際中間匯率，最後備援）

    回傳格式：
    {
      "twd_to_thb": { "rate": float, "sell_price_twd": float, "source": str },
      "twd_to_usd": { "rate": float, "sell_price_twd": float, "source": str },
      "usd_to_thb": { "rate": float, "source": str },
      "fetched_at": str,
    }
    注意：玉山銀行報價為「1 外幣 = X 台幣」，TWD→THB = 1 / sell_price
    """
    now = datetime.utcnow().isoformat() + "Z"
    result: dict = {"fetched_at": now}

    # ── Step 1：優先嘗試玉山銀行 ──────────────────────────────────
    esun = _fetch_esun_rates()
    bot  = {}
    if not esun:
        # 玉山失敗才抓台灣銀行
        bot = _fetch_bot_rates()

    bank_data = esun if esun else bot
    bank_name = "玉山銀行" if esun else "台灣銀行"

    # ── TWD → THB（用現鈔賣出：客戶在台灣銀行買泰銖）
    thb_data = bank_data.get("THB", {})
    thb_sell = thb_data.get("cash_sell") or thb_data.get("spot_sell")
    if thb_sell:
        result["twd_to_thb"] = {
            "rate":          round(1 / thb_sell, 6),   # 1 TWD 換多少 THB
            "sell_price_twd": thb_sell,                 # 買 1 THB 需花多少 TWD
            "buy_price_twd":  thb_data.get("cash_buy") or thb_data.get("spot_buy"),
            "source":        f"{bank_name}現鈔賣出",
        }
    else:
        # 備援 open.er-api
        er = _fetch_open_er("TWD")
        if "THB" in er:
            result["twd_to_thb"] = {
                "rate":          round(er["THB"], 6),
                "sell_price_twd": round(1 / er["THB"], 6) if er["THB"] else None,
                "buy_price_twd":  None,
                "source":        "open.er-api（中間匯率，僅供參考）",
            }

    # ── TWD → USD（用現鈔賣出：客戶在台灣買美元）
    usd_data = bank_data.get("USD", {})
    usd_sell = usd_data.get("cash_sell") or usd_data.get("spot_sell")
    if usd_sell:
        result["twd_to_usd"] = {
            "rate":          round(1 / usd_sell, 6),
            "sell_price_twd": usd_sell,
            "buy_price_twd":  usd_data.get("cash_buy") or usd_data.get("spot_buy"),
            "source":        f"{bank_name}現鈔賣出",
        }
    else:
        er = _fetch_open_er("TWD")
        if "USD" in er:
            result["twd_to_usd"] = {
                "rate":          round(er["USD"], 6),
                "sell_price_twd": round(1 / er["USD"], 6) if er["USD"] else None,
                "buy_price_twd":  None,
                "source":        "open.er-api（中間匯率，僅供參考）",
            }

    # ── USD → THB（在泰國兌換，用 open.er-api 國際中間匯率）
    er_usd = _fetch_open_er("USD")
    if "THB" in er_usd:
        result["usd_to_thb"] = {
            "rate":   round(er_usd["THB"], 6),
            "source": "open.er-api USD/THB（國際中間匯率，K Bank 實際牌告相近）",
        }

    return result


@router.get("/smart-route")
def smart_route_comparison(
    amount_twd: float = Query(100000.0, description="要換匯的台幣金額（元）"),
    _: User = Depends(check_permission("report", "view")),
):
    """
    智慧換匯路線比較：
    自動抓取玉山銀行即時匯率，計算以下所有路線哪條最划算：

    Route A：台灣玉山銀行（現鈔）換泰銖，帶現金去泰國
    Route B：台灣玉山銀行換美金現鈔 → 帶去泰國 Super Rich 換泰銖
    Route C：台灣玉山銀行換美金現鈔 → 帶去泰國 K Bank 換泰銖
    Route D：台灣銀行換美金現鈔 → 帶去泰國 Super Rich 換泰銖
    Route E：台灣玉山銀行網路銀行電匯 TWD → K Bank（含手續費）
    Route F：台灣玉山銀行網路銀行電匯 USD → K Bank（含手續費）

    Super Rich / K Bank 匯率以 open.er-api 國際中間匯率為基準：
    - Super Rich 通常比國際中間價好 0.5–1.5%（全泰最好匯率之一）
    - K Bank 零售窗口約等於國際中間匯率，有時略差 0.3–0.5%
    """
    rates = _fetch_all_live_rates()
    now   = rates.get("fetched_at", "")

    # ── 基礎匯率取出 ──────────────────────────────────────────────
    twd_to_thb = rates.get("twd_to_thb", {})
    twd_to_usd = rates.get("twd_to_usd", {})
    usd_to_thb = rates.get("usd_to_thb", {})

    # 玉山銀行 TWD→THB 現鈔賣出（直接換泰銖）
    esun_thb_sell  = twd_to_thb.get("sell_price_twd")   # 1 THB = X TWD
    # 玉山銀行 TWD→USD 現鈔賣出
    esun_usd_cash_sell = twd_to_usd.get("sell_price_twd")  # 1 USD = X TWD（現鈔）
    # 玉山銀行 TWD→USD 即期賣出（電匯用）
    esun_usd_spot_sell = twd_to_usd.get("sell_price_twd")   # 暫用同一數字（即期比現鈔便宜約0.2）
    # 台灣銀行 USD 現鈔賣出（比玉山貴約 0.1–0.2 TWD）
    bot_usd_cash_sell  = round((esun_usd_cash_sell or 32.5) + 0.15, 2)

    # 國際 USD/THB 中間匯率（open.er-api）
    intl_usd_thb = usd_to_thb.get("rate", 33.5)
    # Super Rich 匯率：比國際中間好 ~1.2%
    superrich_usd_thb = round(intl_usd_thb * 1.012, 4)
    # K Bank 零售窗口：約等於國際中間匯率（-0.3%）
    kbank_usd_thb = round(intl_usd_thb * 0.997, 4)

    # ── 電匯手續費設定 ──────────────────────────────────────────────
    # 玉山銀行電匯固定費：手續費 NT$200 + 電報費 NT$600 = NT$800（台幣）
    wire_fee_twd = 800
    # SWIFT 中間行手續費：約 USD 15（視路由而定，保守估計）
    swift_fee_usd = 15
    # K Bank 收款手續費：約 100–300 THB（忽略，對方帳戶可協商豁免）
    kbank_receive_fee_thb = 0

    routes = []

    # ── Route A：玉山換泰銖現鈔，帶去泰國 ─────────────────────────
    if esun_thb_sell:
        thb_a = round(amount_twd / esun_thb_sell, 0)
        cost_per_thb_a = round(esun_thb_sell, 4)
        routes.append({
            "id":    "A",
            "label": "玉山銀行換泰銖現鈔（直接帶去泰國）",
            "steps": [
                f"台灣玉山銀行現鈔換匯：1 THB = {esun_thb_sell} TWD",
                f"兌換 {amount_twd:,.0f} TWD → 取得約 {thb_a:,.0f} THB",
                "帶現鈔入境（建議 < 45,000 THB 免申報）",
            ],
            "thb_received":    thb_a,
            "fees_twd":        0,
            "cost_per_thb_twd": cost_per_thb_a,
            "source":          twd_to_thb.get("source", "玉山銀行"),
            "pros":  ["免手續費", "到手確定金額"],
            "cons":  ["需帶現金過海關", "泰銖現鈔較難在台灣找到"],
        })

    # ── Route B：玉山換美金現鈔 → Super Rich 換泰銖 ──────────────
    if esun_usd_cash_sell:
        usd_b = amount_twd / esun_usd_cash_sell
        thb_b = round(usd_b * superrich_usd_thb, 0)
        cost_per_thb_b = round(amount_twd / thb_b, 4) if thb_b else None
        routes.append({
            "id":    "B",
            "label": "玉山換美金現鈔 → 泰國 Super Rich 換泰銖（推薦）",
            "steps": [
                f"台灣玉山銀行買美金現鈔：1 USD = {esun_usd_cash_sell} TWD（現鈔賣出）",
                f"兌換 {amount_twd:,.0f} TWD → 取得約 {usd_b:,.2f} USD",
                f"Super Rich 換泰銖：1 USD ≈ {superrich_usd_thb} THB（比銀行好約 1.2%）",
                f"最終取得約 {thb_b:,.0f} THB",
            ],
            "thb_received":    thb_b,
            "fees_twd":        0,
            "cost_per_thb_twd": cost_per_thb_b,
            "source":          f"玉山銀行現鈔 + Super Rich 估算（國際中間 ×1.012）",
            "pros":  ["Super Rich 是全泰最好匯率之一", "美金現鈔通用性高", "免電匯手續費"],
            "cons":  ["需帶現金過海關", "兩次兌換略有匯差", "需找到 Super Rich 地點（曼谷最多）"],
        })

    # ── Route C：玉山換美金現鈔 → K Bank 換泰銖 ─────────────────
    if esun_usd_cash_sell:
        usd_c = amount_twd / esun_usd_cash_sell
        thb_c = round(usd_c * kbank_usd_thb, 0)
        cost_per_thb_c = round(amount_twd / thb_c, 4) if thb_c else None
        routes.append({
            "id":    "C",
            "label": "玉山換美金現鈔 → K Bank 換泰銖",
            "steps": [
                f"台灣玉山銀行買美金現鈔：1 USD = {esun_usd_cash_sell} TWD",
                f"兌換 {amount_twd:,.0f} TWD → 取得約 {usd_c:,.2f} USD",
                f"K Bank 零售換匯：1 USD ≈ {kbank_usd_thb} THB（約等於國際中間匯率）",
                f"最終取得約 {thb_c:,.0f} THB",
            ],
            "thb_received":    thb_c,
            "fees_twd":        0,
            "cost_per_thb_twd": cost_per_thb_c,
            "source":          f"玉山銀行現鈔 + K Bank 估算（國際中間 ×0.997）",
            "pros":  ["K Bank 分行多，方便", "免電匯手續費"],
            "cons":  ["K Bank 匯率通常不如 Super Rich", "需帶現金"],
        })

    # ── Route D：台灣銀行換美金現鈔 → Super Rich 換泰銖 ──────────
    if bot_usd_cash_sell:
        usd_d = amount_twd / bot_usd_cash_sell
        thb_d = round(usd_d * superrich_usd_thb, 0)
        cost_per_thb_d = round(amount_twd / thb_d, 4) if thb_d else None
        routes.append({
            "id":    "D",
            "label": "台灣銀行換美金現鈔 → Super Rich 換泰銖",
            "steps": [
                f"台灣銀行買美金現鈔：1 USD ≈ {bot_usd_cash_sell} TWD（比玉山貴約 0.15）",
                f"兌換 {amount_twd:,.0f} TWD → 取得約 {usd_d:,.2f} USD",
                f"Super Rich 換泰銖：1 USD ≈ {superrich_usd_thb} THB",
                f"最終取得約 {thb_d:,.0f} THB",
            ],
            "thb_received":    thb_d,
            "fees_twd":        0,
            "cost_per_thb_twd": cost_per_thb_d,
            "source":          "台灣銀行估算（玉山+0.15）+ Super Rich 估算",
            "pros":  ["台灣銀行分行多，方便"],
            "cons":  ["現鈔匯率較玉山差", "需帶現金"],
        })

    # ── Route E：電匯 TWD → K Bank THB ──────────────────────────
    if esun_thb_sell:
        # 扣除台幣手續費後的可用金額
        net_twd_e = amount_twd - wire_fee_twd
        # 電報費以即期匯率計，玉山電匯用即期匯率（比現鈔好約 0.1–0.2）
        esun_usd_spot = round((esun_usd_cash_sell or 32.5) - 0.2, 2)
        # 玉山電匯 TWD→THB 即期（比現鈔好約 0.04）
        esun_thb_spot = round(esun_thb_sell - 0.04, 4)
        thb_e = round(net_twd_e / esun_thb_spot, 0) if esun_thb_spot else 0
        cost_per_thb_e = round(amount_twd / thb_e, 4) if thb_e else None
        routes.append({
            "id":    "E",
            "label": "玉山網路銀行電匯 TWD → K Bank（直接匯泰銖）",
            "steps": [
                f"電匯手續費：約 NT${wire_fee_twd}（手續費 200 + 電報費 600）",
                f"可用金額：{net_twd_e:,.0f} TWD",
                f"玉山即期匯率 TWD→THB：1 THB ≈ {esun_thb_spot} TWD",
                f"最終匯達約 {thb_e:,.0f} THB（到賬約 1–3 個工作天）",
                "注意：K Bank 可能收取約 100–300 THB 收款手續費",
            ],
            "thb_received":    thb_e,
            "fees_twd":        wire_fee_twd,
            "cost_per_thb_twd": cost_per_thb_e,
            "source":          "玉山銀行即期匯率（估算）",
            "pros":  ["不需帶現金", "可從台灣直接操作", "金額不受限制"],
            "cons":  [
                f"電匯手續費 NT${wire_fee_twd}（台灣端）",
                "SWIFT 中間行可能再扣 USD 10–25",
                "K Bank 收款費 100–300 THB",
                "到賬需 1–3 個工作天",
                "匯率通常比現鈔差",
            ],
        })

    # ── Route F：電匯 USD → K Bank 換 THB ───────────────────────
    if esun_usd_cash_sell:
        # 先在台灣買即期美金（不是現鈔，較便宜）
        net_twd_f = amount_twd - wire_fee_twd
        esun_usd_spot = round((esun_usd_cash_sell or 32.5) - 0.2, 2)
        usd_f = (net_twd_f / esun_usd_spot)
        # SWIFT 手續費從 USD 中扣
        usd_f_net = usd_f - swift_fee_usd
        thb_f = round(usd_f_net * kbank_usd_thb, 0) if usd_f_net > 0 else 0
        cost_per_thb_f = round(amount_twd / thb_f, 4) if thb_f else None
        routes.append({
            "id":    "F",
            "label": "玉山網路銀行電匯 USD → K Bank（K Bank 再換泰銖）",
            "steps": [
                f"電匯手續費：約 NT${wire_fee_twd}（台灣端）",
                f"玉山即期賣出 USD：1 USD ≈ {esun_usd_spot} TWD",
                f"可匯出約 {usd_f:.2f} USD",
                f"SWIFT 中間行手續費：約 USD {swift_fee_usd}（保守估計）",
                f"實際到 K Bank：約 {usd_f_net:.2f} USD",
                f"K Bank 依牌告換泰銖（{kbank_usd_thb} THB/USD）",
                f"最終取得約 {thb_f:,.0f} THB",
            ],
            "thb_received":    thb_f,
            "fees_twd":        wire_fee_twd + round(swift_fee_usd * (esun_usd_cash_sell or 32), 0),
            "cost_per_thb_twd": cost_per_thb_f,
            "source":          "玉山即期估算 + K Bank 估算",
            "pros":  ["美元帳戶可直接轉"],
            "cons":  [
                f"電匯手續費 NT${wire_fee_twd}（台灣端）",
                f"SWIFT 中間行再扣約 USD {swift_fee_usd}（{round(swift_fee_usd*(esun_usd_cash_sell or 32)):,} TWD）",
                "K Bank 匯率不如 Super Rich",
                "費用最高，非常不划算",
            ],
        })

    # ── 排序（泰銖取得最多 = 最划算）──────────────────────────────
    routes.sort(key=lambda r: r["thb_received"] or 0, reverse=True)
    best = routes[0] if routes else None

    # ── 差額分析 ─────────────────────────────────────────────────
    if len(routes) >= 2:
        best_thb  = routes[0]["thb_received"] or 0
        worst_thb = routes[-1]["thb_received"] or 0
        diff_thb  = round(best_thb - worst_thb, 0)
    else:
        diff_thb = 0

    return {
        "amount_twd":     amount_twd,
        "fetched_at":     now,
        "best_route":     best["id"] if best else None,
        "best_label":     best["label"] if best else None,
        "thb_difference": diff_thb,
        "summary":        (
            f"換 {amount_twd:,.0f} 台幣，最佳路線（{best['id']}）"
            f"比最差路線多拿 {diff_thb:,.0f} 泰銖"
            if diff_thb > 0 else "所有路線相當"
        ),
        "wire_fee_note":  (
            f"電匯手續費固定成本：台灣端約 NT${wire_fee_twd}"
            f"+ SWIFT 約 USD{swift_fee_usd}，金額越大電匯划算度提升"
        ),
        "routes":         routes,
    }


@router.get("", response_model=List[ExchangeRateOut])
def list_exchange_rates(
    from_currency: str = Query("THB"),
    to_currency:   str = Query("TWD"),
    limit:         int = Query(30, le=365),
    db: Session = Depends(get_db),
    _:  User    = Depends(check_permission("report", "view")),
):
    """取得匯率歷史（預設最近 30 筆）"""
    return (
        db.query(ExchangeRate)
        .filter(
            ExchangeRate.from_currency == from_currency,
            ExchangeRate.to_currency == to_currency,
        )
        .order_by(ExchangeRate.effective_date.desc())
        .limit(limit)
        .all()
    )


@router.get("/latest", response_model=ExchangeRateOut)
def get_latest_rate(
    from_currency: str = Query("THB"),
    to_currency:   str = Query("TWD"),
    db: Session = Depends(get_db),
    _:  User    = Depends(check_permission("report", "view")),
):
    """取得最新匯率"""
    rate = (
        db.query(ExchangeRate)
        .filter(
            ExchangeRate.from_currency == from_currency,
            ExchangeRate.to_currency == to_currency,
        )
        .order_by(ExchangeRate.effective_date.desc())
        .first()
    )
    if not rate:
        raise HTTPException(status_code=404, detail="尚無匯率資料")
    return rate


@router.get("/live")
def get_live_rates(
    db: Session = Depends(get_db),
    _: User = Depends(check_permission("report", "view")),
):
    """
    即時抓取匯率：
    - 主要來源：玉山銀行牌告匯率（現鈔賣出）
    - 備援來源：台灣銀行 CSV → open.er-api.com 中間匯率
    回傳 TWD/THB、TWD/USD、USD/THB 三組匯率
    並自動將今日 THB→TWD 即期賣出匯率存入資料庫（每日只存一筆）
    """
    rates = _fetch_all_live_rates()
    if not rates.get("twd_to_thb") and not rates.get("twd_to_usd"):
        raise HTTPException(status_code=503, detail="目前無法取得即時匯率，請稍後再試")

    # 自動儲存今日 THB→TWD 匯率（若今天尚無記錄）
    today = date.today()
    twd_to_thb = rates.get("twd_to_thb", {})
    sell_price = twd_to_thb.get("sell_price_twd")  # 1 THB = X TWD（現鈔賣出）
    if sell_price:
        exists = db.query(ExchangeRate).filter(
            ExchangeRate.from_currency == "THB",
            ExchangeRate.to_currency  == "TWD",
            ExchangeRate.effective_date == today,
        ).first()
        if not exists:
            db.add(ExchangeRate(
                from_currency  = "THB",
                to_currency    = "TWD",
                rate           = sell_price,   # 1 THB = X TWD（現鈔賣出牌告）
                effective_date = today,
                source         = "api",
            ))
            db.commit()
            logger.info(f"已儲存今日匯率：1 THB = {sell_price} TWD（{twd_to_thb.get('source')}）")

    return rates


@router.get("/compare")
def compare_routes(
    amount_twd: float = Query(100000.0, description="要兌換的台幣金額（元）"),
    _: User = Depends(check_permission("report", "view")),
):
    """
    比較兩條兌換路線，哪條可以換到更多泰銖：
    - Route A：TWD → THB 直接購買（台灣銀行現鈔賣出）
    - Route B：TWD → USD → THB（先買美元，再在泰國換泰銖）
    """
    rates = _fetch_all_live_rates()

    twd_to_thb = rates.get("twd_to_thb")
    twd_to_usd = rates.get("twd_to_usd")
    usd_to_thb = rates.get("usd_to_thb")

    result: dict = {
        "amount_twd":  amount_twd,
        "fetched_at":  rates.get("fetched_at"),
        "route_a":     None,
        "route_b":     None,
        "recommendation": None,
    }

    # Route A：TWD → THB 直接
    if twd_to_thb:
        thb_a = round(amount_twd * twd_to_thb["rate"], 2)
        result["route_a"] = {
            "label":         "直接兌換 TWD → THB",
            "steps":         [f"台灣買泰銖，現鈔賣出價 {twd_to_thb['sell_price_twd']} TWD/THB"],
            "thb_received":  thb_a,
            "rate_used":     twd_to_thb["rate"],
            "source":        twd_to_thb["source"],
            "note":          "資料來源為玉山銀行牌告匯率（即時抓取），台灣銀行備援",
        }

    # Route B：TWD → USD → THB
    if twd_to_usd and usd_to_thb:
        usd_received = amount_twd * twd_to_usd["rate"]
        thb_b = round(usd_received * usd_to_thb["rate"], 2)
        result["route_b"] = {
            "label":         "間接兌換 TWD → USD → THB",
            "steps":         [
                f"台灣買美元，現鈔賣出價 {twd_to_usd['sell_price_twd']} TWD/USD → 取得 {round(usd_received, 2)} USD",
                f"美元換泰銖（K Bank / 國際匯率）{usd_to_thb['rate']} THB/USD → 取得 {thb_b} THB",
            ],
            "usd_intermediate": round(usd_received, 4),
            "thb_received":  thb_b,
            "rate_a_twd_usd": twd_to_usd["rate"],
            "rate_b_usd_thb": usd_to_thb["rate"],
            "source":        f"{twd_to_usd['source']} + {usd_to_thb['source']}",
            "note":          "實際兌換時 K Bank 可能另收手續費，請現場確認",
        }

    # 比較與建議
    thb_a = result["route_a"]["thb_received"] if result["route_a"] else None
    thb_b = result["route_b"]["thb_received"] if result["route_b"] else None

    if thb_a is not None and thb_b is not None:
        diff = round(thb_b - thb_a, 2)
        diff_pct = round((thb_b - thb_a) / thb_a * 100, 3)
        if diff > 0:
            result["recommendation"] = {
                "winner":      "Route B（TWD → USD → THB）較划算",
                "thb_diff":    diff,
                "diff_pct":    diff_pct,
                "summary":     f"每 {int(amount_twd):,} 台幣，走 USD 路線多換 {diff:,.0f} 泰銖（多 {diff_pct}%）",
            }
        elif diff < 0:
            result["recommendation"] = {
                "winner":      "Route A（直接 TWD → THB）較划算",
                "thb_diff":    abs(diff),
                "diff_pct":    abs(diff_pct),
                "summary":     f"每 {int(amount_twd):,} 台幣，直接換泰銖多換 {abs(diff):,.0f} 泰銖（多 {abs(diff_pct)}%）",
            }
        else:
            result["recommendation"] = {
                "winner":      "兩條路線相同",
                "thb_diff":    0,
                "diff_pct":    0,
                "summary":     "匯率條件相當，任選皆可",
            }
    elif thb_a:
        result["recommendation"] = {"winner": "僅 Route A 有資料", "summary": "直接換泰銖"}
    elif thb_b:
        result["recommendation"] = {"winner": "僅 Route B 有資料", "summary": "USD 中轉換泰銖"}

    return result


@router.post("", response_model=ExchangeRateOut, status_code=status.HTTP_201_CREATED)
def create_exchange_rate(
    payload:      ExchangeRateCreate,
    db:           Session = Depends(get_db),
    current_user: User    = Depends(check_permission("report", "view")),
):
    rate = ExchangeRate(**payload.model_dump(), recorded_by=current_user.id)
    db.add(rate)
    db.commit()
    db.refresh(rate)
    return rate
