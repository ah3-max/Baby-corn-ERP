'use client';

/**
 * 即時匯率工具頁 — 智慧換匯路線比較
 * 資料來源：玉山銀行（主）→ 台灣銀行（備）→ open.er-api（備援）
 * 比較六條換匯路線，自動標示最划算方案
 */
import { useState, useCallback } from 'react';
import {
  RefreshCw, TrendingUp, Info, CheckCircle,
  ArrowRight, Zap, AlertTriangle, ThumbsUp, ThumbsDown,
} from 'lucide-react';
import { exchangeRatesApi } from '@/lib/api';

// ── 型別 ──────────────────────────────────────────────────────
interface RateInfo {
  rate: number;
  sell_price_twd?: number;
  buy_price_twd?: number;
  source: string;
}
interface LiveRates {
  fetched_at: string;
  twd_to_thb?: RateInfo;
  twd_to_usd?: RateInfo;
  usd_to_thb?: RateInfo;
}
interface RouteItem {
  id: string;
  label: string;
  steps: string[];
  thb_received: number;
  fees_twd: number;
  cost_per_thb_twd: number | null;
  source: string;
  pros: string[];
  cons: string[];
}
interface SmartResult {
  amount_twd: number;
  fetched_at: string;
  best_route: string;
  best_label: string;
  thb_difference: number;
  summary: string;
  wire_fee_note: string;
  routes: RouteItem[];
}

// ── 路線顏色配置 ─────────────────────────────────────────────
const ROUTE_COLORS: Record<string, { bg: string; border: string; badge: string; text: string; num: string }> = {
  A: { bg: 'bg-emerald-50', border: 'border-emerald-400', badge: 'bg-emerald-500', text: 'text-emerald-700', num: 'bg-emerald-100 text-emerald-700' },
  B: { bg: 'bg-blue-50',    border: 'border-blue-400',    badge: 'bg-blue-500',    text: 'text-blue-700',    num: 'bg-blue-100 text-blue-700' },
  C: { bg: 'bg-cyan-50',    border: 'border-cyan-400',    badge: 'bg-cyan-500',    text: 'text-cyan-700',    num: 'bg-cyan-100 text-cyan-700' },
  D: { bg: 'bg-purple-50',  border: 'border-purple-400',  badge: 'bg-purple-500',  text: 'text-purple-700',  num: 'bg-purple-100 text-purple-700' },
  E: { bg: 'bg-orange-50',  border: 'border-orange-300',  badge: 'bg-orange-400',  text: 'text-orange-700',  num: 'bg-orange-100 text-orange-700' },
  F: { bg: 'bg-red-50',     border: 'border-red-300',     badge: 'bg-red-400',     text: 'text-red-700',     num: 'bg-red-100 text-red-700' },
};

export default function ExchangeRatesPage() {
  const [liveRates,  setLiveRates]  = useState<LiveRates | null>(null);
  const [smartResult, setSmartResult] = useState<SmartResult | null>(null);
  const [loading,    setLoading]    = useState(false);
  const [amountTwd,  setAmountTwd]  = useState('100000');
  const [error,      setError]      = useState('');

  // ── 查詢即時匯率 + 智慧路線 ──────────────────────────────────
  const fetchAll = useCallback(async () => {
    setLoading(true);
    setError('');
    const amount = parseFloat(amountTwd) || 100000;
    try {
      const [liveRes, smartRes] = await Promise.all([
        exchangeRatesApi.getLive(),
        exchangeRatesApi.smartRoute(amount),
      ]);
      setLiveRates(liveRes.data);
      setSmartResult(smartRes.data);
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? '無法取得即時匯率，請確認網路連線後再試');
    } finally {
      setLoading(false);
    }
  }, [amountTwd]);

  // ── 格式化工具 ───────────────────────────────────────────────
  const fmt    = (n: number, dec = 4) => n?.toLocaleString('zh-TW', { minimumFractionDigits: dec, maximumFractionDigits: dec }) ?? '—';
  const fmtTHB = (n: number) => Math.round(n).toLocaleString('zh-TW');
  const fmtTime = (iso: string) => {
    try { return new Date(iso).toLocaleString('zh-TW', { timeZone: 'Asia/Taipei' }); }
    catch { return iso; }
  };

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-6">

      {/* ── 標題 ── */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">智慧換匯路線比較</h1>
        <p className="text-sm text-gray-500 mt-1">
          即時抓取玉山銀行匯率，自動比較六條換匯路線（含手續費），找出最划算方案
        </p>
      </div>

      {/* ── 輸入區 ── */}
      <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-5">
        <div className="flex flex-col sm:flex-row items-start sm:items-end gap-4">
          <div className="flex-1">
            <label className="text-sm font-medium text-gray-700 mb-1.5 block">
              要換匯的台幣金額（元）
            </label>
            <div className="relative">
              <span className="absolute left-3 top-1/2 -translate-y-1/2 text-sm text-gray-400 font-medium">NT$</span>
              <input
                type="number"
                value={amountTwd}
                onChange={e => setAmountTwd(e.target.value)}
                placeholder="100000"
                min="1000"
                step="10000"
                className="input pl-10 text-lg font-semibold w-full"
              />
            </div>
          </div>
          <button
            onClick={fetchAll}
            disabled={loading}
            className="btn-primary flex items-center gap-2 px-6 py-2.5 whitespace-nowrap"
          >
            <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
            {loading ? '查詢中...' : '查詢即時匯率'}
          </button>
        </div>

        {error && (
          <div className="mt-3 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-600 flex items-center gap-2">
            <AlertTriangle size={14} /> {error}
          </div>
        )}
        {liveRates?.fetched_at && (
          <p className="text-xs text-gray-400 mt-3">
            資料時間：{fmtTime(liveRates.fetched_at)}（台灣時間）｜來源：玉山銀行
          </p>
        )}
      </div>

      {/* ── 即時匯率三格 ── */}
      {liveRates && (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-4">
            <p className="text-xs text-gray-500 mb-1">台幣 → 泰銖（現鈔）</p>
            <p className="text-2xl font-bold text-emerald-600">
              {liveRates.twd_to_thb ? `1 TWD = ${fmt(liveRates.twd_to_thb.rate, 4)} THB` : '—'}
            </p>
            {liveRates.twd_to_thb?.sell_price_twd && (
              <p className="text-xs text-gray-400 mt-1">買 1 THB = {fmt(liveRates.twd_to_thb.sell_price_twd, 4)} TWD</p>
            )}
            <p className="text-[11px] text-gray-300 mt-1.5 truncate">{liveRates.twd_to_thb?.source}</p>
          </div>
          <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-4">
            <p className="text-xs text-gray-500 mb-1">台幣 → 美金（現鈔）</p>
            <p className="text-2xl font-bold text-blue-600">
              {liveRates.twd_to_usd ? `1 USD = ${fmt(liveRates.twd_to_usd.sell_price_twd ?? 0, 2)} TWD` : '—'}
            </p>
            {liveRates.twd_to_usd?.buy_price_twd && (
              <p className="text-xs text-gray-400 mt-1">
                買入 {fmt(liveRates.twd_to_usd.buy_price_twd, 2)} ／ 賣出 {fmt(liveRates.twd_to_usd.sell_price_twd ?? 0, 2)}
              </p>
            )}
            <p className="text-[11px] text-gray-300 mt-1.5 truncate">{liveRates.twd_to_usd?.source}</p>
          </div>
          <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-4">
            <p className="text-xs text-gray-500 mb-1">美金 → 泰銖（國際匯率）</p>
            <p className="text-2xl font-bold text-purple-600">
              {liveRates.usd_to_thb ? `1 USD = ${fmt(liveRates.usd_to_thb.rate, 2)} THB` : '—'}
            </p>
            <p className="text-xs text-gray-400 mt-1">Super Rich 約 ×1.012，K Bank 約 ×0.997</p>
            <p className="text-[11px] text-gray-300 mt-1.5 truncate">{liveRates.usd_to_thb?.source}</p>
          </div>
        </div>
      )}

      {/* ── 智慧路線比較 ── */}
      {smartResult && (
        <>
          {/* 總結橫幅 */}
          <div className="bg-gradient-to-r from-emerald-500 to-teal-500 rounded-2xl p-5 text-white flex items-center gap-4">
            <TrendingUp size={32} className="flex-shrink-0 opacity-80" />
            <div>
              <p className="font-bold text-lg">最佳路線：{smartResult.best_route} — {smartResult.best_label}</p>
              <p className="text-emerald-100 text-sm mt-0.5">{smartResult.summary}</p>
              {smartResult.thb_difference > 0 && (
                <p className="text-emerald-200 text-xs mt-1">最佳 vs 最差相差 {fmtTHB(smartResult.thb_difference)} THB</p>
              )}
            </div>
          </div>

          {/* 六條路線卡片 */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {smartResult.routes.map((route, rank) => {
              const c = ROUTE_COLORS[route.id] ?? ROUTE_COLORS['A'];
              const isBest = route.id === smartResult.best_route;
              return (
                <div
                  key={route.id}
                  className={`rounded-2xl border-2 p-5 relative ${
                    isBest ? `${c.border} ${c.bg}` : 'border-gray-200 bg-white'
                  }`}
                >
                  {/* 排名標籤 */}
                  {isBest && (
                    <span className={`absolute -top-3 left-4 ${c.badge} text-white text-xs font-bold px-3 py-1 rounded-full flex items-center gap-1`}>
                      <CheckCircle size={12} /> 最划算 #{rank + 1}
                    </span>
                  )}
                  {!isBest && rank === smartResult.routes.length - 1 && (
                    <span className="absolute -top-3 left-4 bg-gray-400 text-white text-xs font-bold px-3 py-1 rounded-full">
                      最貴 #{rank + 1}
                    </span>
                  )}
                  {!isBest && rank > 0 && rank < smartResult.routes.length - 1 && (
                    <span className="absolute -top-3 left-4 bg-gray-300 text-white text-xs px-2 py-1 rounded-full">
                      #{rank + 1}
                    </span>
                  )}

                  {/* 路線標題 */}
                  <h3 className="font-semibold text-gray-800 mb-3 flex items-center gap-2 mt-2">
                    <span className={`w-6 h-6 rounded-full text-xs font-bold flex items-center justify-center flex-shrink-0 ${c.num}`}>
                      {route.id}
                    </span>
                    <span className="text-sm leading-tight">{route.label}</span>
                  </h3>

                  {/* 步驟 */}
                  <div className="space-y-1 mb-4">
                    {route.steps.map((step, i) => (
                      <p key={i} className="text-xs text-gray-500">• {step}</p>
                    ))}
                  </div>

                  {/* 手續費提示 */}
                  {route.fees_twd > 0 && (
                    <div className="mb-3 px-2 py-1.5 bg-red-50 rounded-lg border border-red-100 text-xs text-red-600">
                      ⚠ 手續費：約 NT${route.fees_twd.toLocaleString()}（已計入）
                    </div>
                  )}

                  {/* 可換到的泰銖 */}
                  <div className="pt-3 border-t border-gray-100">
                    <p className="text-xs text-gray-500">可換到</p>
                    <p className={`text-3xl font-bold mt-0.5 ${isBest ? c.text : 'text-gray-700'}`}>
                      {fmtTHB(route.thb_received)} <span className="text-base font-medium text-gray-500">THB</span>
                    </p>
                    {route.cost_per_thb_twd && (
                      <p className="text-xs text-gray-400 mt-1">
                        每泰銖成本：{fmt(route.cost_per_thb_twd, 4)} TWD
                      </p>
                    )}
                  </div>

                  {/* 優缺點 */}
                  <div className="mt-3 space-y-1">
                    {route.pros.slice(0, 2).map((p, i) => (
                      <p key={i} className="text-xs text-emerald-600 flex items-center gap-1">
                        <ThumbsUp size={10} /> {p}
                      </p>
                    ))}
                    {route.cons.slice(0, 2).map((c2, i) => (
                      <p key={i} className="text-xs text-red-500 flex items-center gap-1">
                        <ThumbsDown size={10} /> {c2}
                      </p>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>

          {/* 手續費說明 */}
          <div className="bg-amber-50 border border-amber-200 rounded-2xl p-4 text-sm text-amber-700 space-y-1.5">
            <p className="font-semibold flex items-center gap-1.5"><Info size={14} /> 重要說明</p>
            <p>• <strong>電匯手續費</strong>：{smartResult.wire_fee_note}</p>
            <p>• <strong>Super Rich</strong>：曼谷著名換匯所，USD→THB 匯率通常優於銀行 1–2%，需親至門市。</p>
            <p>• <strong>K Bank 匯率</strong>：以國際中間匯率估算，實際牌告以現場為準。</p>
            <p>• <strong>現金帶入泰國</strong>：超過 450,000 THB 等值需向泰國海關申報。</p>
            <p>• 所有匯率均為估算值，以實際銀行/換匯所當日牌告為準。</p>
          </div>
        </>
      )}

      {/* 尚未查詢提示 */}
      {!liveRates && !loading && (
        <div className="text-center py-20 text-gray-400">
          <Zap size={40} className="mx-auto mb-3 opacity-30" />
          <p className="text-sm">輸入金額後點擊「查詢即時匯率」</p>
          <p className="text-xs mt-1 opacity-70">資料來源：玉山銀行（主）、台灣銀行（備）、open.er-api（備援）</p>
        </div>
      )}
    </div>
  );
}
