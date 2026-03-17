'use client';

/**
 * 財務歷史模組 /finance
 * Tab 1：批次歷史存檔（closed/sold 批次完整 P&L）
 * Tab 2：每日銷售報表（日期範圍篩選）
 */
import { useEffect, useState } from 'react';
import { useLocale } from 'next-intl';
import Link from 'next/link';
import {
  Archive, BarChart3, TrendingUp, TrendingDown, RefreshCw,
  Calendar, ChevronDown, ChevronUp, Package
} from 'lucide-react';
import { analyticsApi, batchesApi } from '@/lib/api';

// ─── 型別 ─────────────────────────────────────────────────────

interface BatchAnalytic {
  batch_id:          string;
  batch_no:          string;
  status:            string;
  initial_weight_kg: number;
  current_weight_kg: number;
  po_order_no:       string | null;
  cost_by_layer:     Record<string, number>;
  total_cost_twd:    number;
  cost_per_kg_twd:   number;
  sales_revenue_twd: number;
  gross_profit_twd:  number;
  gross_margin_pct:  number | null;
}

interface DailyRow {
  sale_date:        string;
  market_code:      string;
  total_kg:         number;
  total_boxes:      number;
  total_amount_twd: number;
  sale_count:       number;
}

// ─── 工具 ─────────────────────────────────────────────────────

const CLOSED_STATUSES = ['sold', 'closed'];

const fmt = (v: number) =>
  v === 0 ? '—' : `NT$${Math.round(v).toLocaleString()}`;

const MARKET_LABELS: Record<string, string> = {
  taipei_first:  '台北一',
  taipei_second: '台北二',
  taichung:      '台中',
  tainan:        '台南',
  kaohsiung:     '高雄',
  other:         '其他',
};

// ─── 主頁 ─────────────────────────────────────────────────────

export default function FinancePage() {
  const locale = useLocale();
  const [tab, setTab] = useState<'history' | 'daily'>('history');

  // ── 批次歷史 ──
  const [batches, setBatches]         = useState<BatchAnalytic[]>([]);
  const [histLoading, setHistLoading] = useState(true);
  const [expanded, setExpanded]       = useState<string | null>(null);
  const [exchangeRate, setExchangeRate] = useState(0.92);

  // ── 每日銷售 ──
  const [dailyRows, setDailyRows]     = useState<DailyRow[]>([]);
  const [dailyLoading, setDailyLoad]  = useState(false);
  const [dateFrom, setDateFrom]       = useState('');
  const [dateTo, setDateTo]           = useState('');

  // 載入批次歷史（只顯示 sold/closed）
  const loadHistory = async (rate = exchangeRate) => {
    setHistLoading(true);
    try {
      const { data } = await analyticsApi.batches(rate);
      const closed = (data as BatchAnalytic[]).filter(b =>
        CLOSED_STATUSES.includes(b.status)
      );
      // 依毛利率降序排列
      closed.sort((a, b) => (b.gross_profit_twd ?? 0) - (a.gross_profit_twd ?? 0));
      setBatches(closed);
    } catch (e) {
      console.error(e);
    } finally {
      setHistLoading(false);
    }
  };

  // 載入每日銷售
  const loadDaily = async () => {
    setDailyLoad(true);
    try {
      const params: Record<string, string> = {};
      if (dateFrom) params.date_from = dateFrom;
      if (dateTo)   params.date_to   = dateTo;
      const { data } = await analyticsApi.daily(params);
      setDailyRows(data as DailyRow[]);
    } catch (e) {
      console.error(e);
    } finally {
      setDailyLoad(false);
    }
  };

  useEffect(() => { loadHistory(); }, []);
  useEffect(() => { if (tab === 'daily') loadDaily(); }, [tab]);

  // ── 摘要統計 ──
  const totalRevenue = batches.reduce((s, b) => s + b.sales_revenue_twd, 0);
  const totalCost    = batches.reduce((s, b) => s + b.total_cost_twd,    0);
  const totalProfit  = totalRevenue - totalCost;
  const avgMargin    = totalRevenue > 0 ? (totalProfit / totalRevenue * 100) : 0;

  const dailyTotal   = dailyRows.reduce((s, r) => s + r.total_amount_twd, 0);
  const dailyKg      = dailyRows.reduce((s, r) => s + r.total_kg, 0);

  return (
    <div>
      {/* 頁首 */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">財務歷史</h1>
          <p className="text-sm text-gray-400 mt-0.5">已結案批次存檔 &amp; 每日銷售報表</p>
        </div>
      </div>

      {/* Tab 切換 */}
      <div className="flex gap-1 mb-6 bg-gray-100 p-1 rounded-lg w-fit">
        <button
          onClick={() => setTab('history')}
          className={`flex items-center gap-2 px-4 py-1.5 rounded-md text-sm font-medium transition-colors ${
            tab === 'history' ? 'bg-white text-gray-800 shadow-sm' : 'text-gray-500 hover:text-gray-700'
          }`}
        >
          <Archive size={15} /> 批次歷史存檔
        </button>
        <button
          onClick={() => setTab('daily')}
          className={`flex items-center gap-2 px-4 py-1.5 rounded-md text-sm font-medium transition-colors ${
            tab === 'daily' ? 'bg-white text-gray-800 shadow-sm' : 'text-gray-500 hover:text-gray-700'
          }`}
        >
          <BarChart3 size={15} /> 每日銷售報表
        </button>
      </div>

      {/* ── 批次歷史存檔 ── */}
      {tab === 'history' && (
        <>
          {/* 匯率控制 + 重新載入 */}
          <div className="flex items-center gap-3 mb-5">
            <label className="text-sm text-gray-600 flex items-center gap-2">
              THB→TWD 匯率：
              <input
                type="number"
                value={exchangeRate}
                step={0.01}
                min={0.1}
                max={5}
                onChange={e => setExchangeRate(Number(e.target.value))}
                className="input w-24"
              />
            </label>
            <button
              onClick={() => loadHistory(exchangeRate)}
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-gray-100 text-gray-600 rounded-md hover:bg-gray-200"
            >
              <RefreshCw size={14} /> 套用
            </button>
          </div>

          {/* KPI 摘要 */}
          {batches.length > 0 && (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
              <div className="card p-4">
                <p className="text-xs text-gray-400 mb-1">已結案批次</p>
                <p className="text-2xl font-bold text-gray-800">{batches.length}</p>
              </div>
              <div className="card p-4">
                <p className="text-xs text-gray-400 mb-1">總銷售收入</p>
                <p className="text-xl font-bold text-gray-800">{fmt(totalRevenue)}</p>
              </div>
              <div className="card p-4">
                <p className="text-xs text-gray-400 mb-1">總毛利</p>
                <p className={`text-xl font-bold ${totalProfit >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                  {totalProfit >= 0 ? '+' : ''}{fmt(totalProfit)}
                </p>
              </div>
              <div className="card p-4">
                <p className="text-xs text-gray-400 mb-1">平均毛利率</p>
                <p className={`text-xl font-bold ${avgMargin >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                  {avgMargin.toFixed(1)}%
                </p>
              </div>
            </div>
          )}

          {/* 批次列表 */}
          {histLoading ? (
            <div className="text-center py-16 text-gray-400">載入中…</div>
          ) : batches.length === 0 ? (
            <div className="flex flex-col items-center py-20 text-gray-400">
              <Package size={40} className="mb-3 opacity-30" />
              <p>尚無已結案批次</p>
            </div>
          ) : (
            <div className="bg-white rounded-2xl border border-gray-200 overflow-hidden">
              {/* 表頭 */}
              <div className="grid grid-cols-7 gap-3 px-5 py-3 bg-gray-50 border-b text-xs font-semibold text-gray-500 uppercase tracking-wider">
                <div>批次</div>
                <div>狀態</div>
                <div className="text-right">初始重量</div>
                <div className="text-right">總成本</div>
                <div className="text-right">銷售收入</div>
                <div className="text-right">毛利</div>
                <div className="text-right">毛利率</div>
              </div>

              {batches.map((b, idx) => {
                const isExpanded = expanded === b.batch_id;
                const layerEntries = Object.entries(b.cost_by_layer ?? {}).filter(([, v]) => v > 0);

                return (
                  <div key={b.batch_id}>
                    <div
                      className={`grid grid-cols-7 gap-3 px-5 py-3.5 items-center hover:bg-gray-50 cursor-pointer transition-colors ${
                        idx < batches.length - 1 ? 'border-b border-gray-100' : ''
                      }`}
                      onClick={() => setExpanded(isExpanded ? null : b.batch_id)}
                    >
                      <div>
                        <Link
                          href={`/${locale}/batches/${b.batch_id}`}
                          className="font-mono text-sm font-semibold text-primary-600 hover:underline"
                          onClick={e => e.stopPropagation()}
                        >
                          {b.batch_no}
                        </Link>
                        {b.po_order_no && (
                          <p className="text-xs text-gray-400 font-mono">{b.po_order_no}</p>
                        )}
                      </div>
                      <div>
                        <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                          b.status === 'closed' ? 'bg-gray-100 text-gray-500' : 'bg-emerald-100 text-emerald-700'
                        }`}>
                          {b.status === 'closed' ? '已結案' : '已售出'}
                        </span>
                      </div>
                      <div className="text-right text-sm text-gray-600">
                        {b.initial_weight_kg.toLocaleString()} kg
                      </div>
                      <div className="text-right text-sm font-medium text-gray-700">
                        {fmt(b.total_cost_twd)}
                      </div>
                      <div className="text-right text-sm font-medium text-gray-700">
                        {fmt(b.sales_revenue_twd)}
                      </div>
                      <div className={`text-right text-sm font-semibold ${
                        b.gross_profit_twd >= 0 ? 'text-green-600' : 'text-red-600'
                      }`}>
                        {b.gross_profit_twd >= 0 ? '+' : ''}{fmt(b.gross_profit_twd)}
                      </div>
                      <div className="flex items-center justify-end gap-1">
                        <span className={`text-sm font-semibold ${
                          (b.gross_margin_pct ?? 0) >= 0 ? 'text-green-600' : 'text-red-600'
                        }`}>
                          {b.gross_margin_pct != null ? `${b.gross_margin_pct.toFixed(1)}%` : '—'}
                        </span>
                        {isExpanded ? <ChevronUp size={14} className="text-gray-400" /> : <ChevronDown size={14} className="text-gray-400" />}
                      </div>
                    </div>

                    {/* 展開：成本層級明細 */}
                    {isExpanded && layerEntries.length > 0 && (
                      <div className="bg-gray-50 border-b border-gray-100 px-5 py-3">
                        <p className="text-xs font-semibold text-gray-500 mb-2">成本結構明細</p>
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                          {layerEntries.map(([layer, amt]) => (
                            <div key={layer} className="bg-white rounded-lg px-3 py-2 border border-gray-200">
                              <p className="text-xs text-gray-400">{layer}</p>
                              <p className="text-sm font-semibold text-gray-700">{fmt(amt)}</p>
                            </div>
                          ))}
                        </div>
                        <div className="mt-2 text-xs text-gray-500">
                          每公斤成本：NT${b.cost_per_kg_twd.toLocaleString()} / kg
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </>
      )}

      {/* ── 每日銷售報表 ── */}
      {tab === 'daily' && (
        <>
          {/* 日期範圍篩選 */}
          <div className="flex items-center gap-3 mb-5">
            <Calendar size={16} className="text-gray-400" />
            <input
              type="date"
              value={dateFrom}
              onChange={e => setDateFrom(e.target.value)}
              className="input w-40 text-sm"
              placeholder="起始日期"
            />
            <span className="text-gray-400">—</span>
            <input
              type="date"
              value={dateTo}
              onChange={e => setDateTo(e.target.value)}
              className="input w-40 text-sm"
              placeholder="結束日期"
            />
            <button
              onClick={loadDaily}
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-primary-50 text-primary-700 border border-primary-200 rounded-md hover:bg-primary-100"
            >
              <RefreshCw size={14} /> 查詢
            </button>
          </div>

          {/* 彙總 */}
          {dailyRows.length > 0 && (
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mb-5">
              <div className="card p-4">
                <p className="text-xs text-gray-400 mb-1">期間銷售收入</p>
                <p className="text-xl font-bold text-gray-800">{fmt(dailyTotal)}</p>
              </div>
              <div className="card p-4">
                <p className="text-xs text-gray-400 mb-1">期間銷售量</p>
                <p className="text-xl font-bold text-gray-800">{dailyKg.toLocaleString()} kg</p>
              </div>
              <div className="card p-4">
                <p className="text-xs text-gray-400 mb-1">筆數</p>
                <p className="text-xl font-bold text-gray-800">{dailyRows.length}</p>
              </div>
            </div>
          )}

          {/* 表格 */}
          {dailyLoading ? (
            <div className="text-center py-16 text-gray-400">載入中…</div>
          ) : dailyRows.length === 0 ? (
            <div className="flex flex-col items-center py-20 text-gray-400">
              <BarChart3 size={40} className="mb-3 opacity-30" />
              <p>查無每日銷售資料</p>
              <p className="text-xs mt-1">請選擇日期範圍後點選查詢</p>
            </div>
          ) : (
            <div className="bg-white rounded-2xl border border-gray-200 overflow-hidden">
              {/* 表頭 */}
              <div className="grid grid-cols-6 gap-3 px-5 py-3 bg-gray-50 border-b text-xs font-semibold text-gray-500 uppercase tracking-wider">
                <div>日期</div>
                <div>市場</div>
                <div className="text-right">銷售量 (kg)</div>
                <div className="text-right">箱數</div>
                <div className="text-right">銷售金額</div>
                <div className="text-right">筆數</div>
              </div>

              {dailyRows.map((r, idx) => (
                <div
                  key={`${r.sale_date}-${r.market_code}`}
                  className={`grid grid-cols-6 gap-3 px-5 py-3.5 items-center hover:bg-gray-50 ${
                    idx < dailyRows.length - 1 ? 'border-b border-gray-100' : ''
                  }`}
                >
                  <div className="text-sm font-medium text-gray-700">{r.sale_date}</div>
                  <div className="text-sm text-gray-600">
                    {MARKET_LABELS[r.market_code] ?? r.market_code}
                  </div>
                  <div className="text-right text-sm text-gray-700">
                    {r.total_kg.toLocaleString()} kg
                  </div>
                  <div className="text-right text-sm text-gray-700">{r.total_boxes}</div>
                  <div className="text-right text-sm font-semibold text-gray-800">
                    {fmt(r.total_amount_twd)}
                  </div>
                  <div className="text-right text-sm text-gray-500">{r.sale_count}</div>
                </div>
              ))}

              {/* 合計列 */}
              <div className="grid grid-cols-6 gap-3 px-5 py-3 bg-gray-50 border-t text-sm font-semibold text-gray-700">
                <div className="col-span-2 text-gray-500">合計</div>
                <div className="text-right">{dailyKg.toLocaleString()} kg</div>
                <div className="text-right">
                  {dailyRows.reduce((s, r) => s + r.total_boxes, 0)}
                </div>
                <div className="text-right text-primary-700">{fmt(dailyTotal)}</div>
                <div className="text-right">
                  {dailyRows.reduce((s, r) => s + r.sale_count, 0)}
                </div>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
