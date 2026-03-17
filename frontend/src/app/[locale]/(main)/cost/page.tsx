'use client';

/**
 * 成本 / 利潤分析儀表板 /cost
 * 功能：
 * - 4 大 KPI 摘要卡片
 * - 7 層成本結構視覺化（瀑布圖）
 * - CIF 計算器
 * - 批次成本明細表（含層級展開）
 * - 批次狀態分佈
 */
import { useEffect, useState, useMemo } from 'react';
import { useTranslations, useLocale } from 'next-intl';
import Link from 'next/link';
import {
  TrendingUp, TrendingDown, ShoppingBag, Package, BarChart3, RefreshCw,
  DollarSign, Layers, ChevronDown, ChevronRight, Calculator, Percent,
  Download, Mail
} from 'lucide-react';
import { analyticsApi } from '@/lib/api';

// ─── 型別 ──────────────────────────────────────────────────────

interface Summary {
  purchase_cost_thb:       number;
  total_cost_events_thb:   number;
  total_cost_events_twd:   number;
  sales_revenue_so_twd:    number;
  sales_revenue_ds_twd:    number;
  total_revenue_twd:       number;
  confirmed_payments_twd:  number;
  total_batches:           number;
  batch_by_status:         Record<string, number>;
  active_lots:             number;
  stock_weight_kg:         number;
}

interface CostByLayer {
  material:      number;
  processing:    number;
  th_logistics:  number;
  freight:       number;
  tw_customs:    number;
  tw_logistics:  number;
  market:        number;
}

interface BatchAnalytic {
  batch_id:          string;
  batch_no:          string;
  status:            string;
  initial_weight_kg: number;
  current_weight_kg: number;
  po_order_no:       string | null;
  cost_by_layer:     CostByLayer;
  total_cost_twd:    number;
  cost_per_kg_twd:   number;
  sales_revenue_twd: number;
  gross_profit_twd:  number;
  gross_margin_pct:  number | null;
}

// ─── 層級定義 ───────────────────────────────────────────────────

const COST_LAYERS: Array<{ key: keyof CostByLayer; color: string; barColor: string }> = [
  { key: 'material',      color: 'text-orange-700 bg-orange-100', barColor: 'bg-orange-400' },
  { key: 'processing',    color: 'text-amber-700 bg-amber-100',   barColor: 'bg-amber-400' },
  { key: 'th_logistics',  color: 'text-yellow-700 bg-yellow-100', barColor: 'bg-yellow-400' },
  { key: 'freight',       color: 'text-blue-700 bg-blue-100',     barColor: 'bg-blue-400' },
  { key: 'tw_customs',    color: 'text-indigo-700 bg-indigo-100', barColor: 'bg-indigo-400' },
  { key: 'tw_logistics',  color: 'text-teal-700 bg-teal-100',     barColor: 'bg-teal-400' },
  { key: 'market',        color: 'text-purple-700 bg-purple-100', barColor: 'bg-purple-400' },
];

// ─── 格式化工具 ──────────────────────────────────────────────────

const fmt = (v: number, prefix = 'NT$') =>
  v === 0 ? '—' : `${prefix}${v.toLocaleString(undefined, { maximumFractionDigits: 0 })}`;

const fmtPct = (v: number | null) =>
  v == null ? '—' : `${v.toFixed(1)}%`;

// ─── 主頁元件 ───────────────────────────────────────────────────

export default function CostPage() {
  const t      = useTranslations('cost');
  const tc     = useTranslations('common');
  const tb     = useTranslations('batches');
  const locale = useLocale();

  const [summary, setSummary]             = useState<Summary | null>(null);
  const [batches, setBatches]             = useState<BatchAnalytic[]>([]);
  const [loading, setLoading]             = useState(true);
  const [exchangeRate, setExchangeRate]   = useState(0.92);
  const [reloading, setReloading]         = useState(false);
  const [expandedBatch, setExpandedBatch] = useState<string | null>(null);

  // CIF 計算器狀態
  const [cifPct, setCifPct]               = useState(70); // CIF 報關 % 比率

  // Email Modal 狀態
  const [showEmailModal, setShowEmailModal] = useState(false);        // 是否顯示 Email Modal
  const [emailTo, setEmailTo]               = useState('');           // 收件人（逗號分隔）
  const [emailSubject, setEmailSubject]     = useState('玉米筍批次成本利潤報表'); // 主旨
  const [emailSending, setEmailSending]     = useState(false);        // 發送中狀態
  const [emailResult, setEmailResult]       = useState<'success' | 'error' | null>(null); // 發送結果

  const loadAll = async (rate = exchangeRate) => {
    setReloading(true);
    try {
      const [sumRes, batchRes] = await Promise.all([
        analyticsApi.summary(),
        analyticsApi.batches(rate),
      ]);
      setSummary(sumRes.data);
      setBatches(batchRes.data);
    } catch (e) {
      console.error(e);
    } finally {
      setReloading(false);
      setLoading(false);
    }
  };

  useEffect(() => { loadAll(); }, []);

  /** 發送成本利潤報表 Email：擷取頁面 HTML 後呼叫後端 API */
  const handleSendEmail = async () => {
    const toList = emailTo.split(',').map(e => e.trim()).filter(Boolean);
    if (toList.length === 0) return;

    setEmailSending(true);
    setEmailResult(null);
    try {
      // 擷取報表區域的 HTML，若找不到則使用整個 body
      const reportEl = document.getElementById('cost-report-content');
      const html = reportEl ? reportEl.innerHTML : document.body.innerHTML;

      await analyticsApi.sendCostReport({
        to_emails:    toList,
        subject:      emailSubject,
        html_content: `
          <html>
            <head>
              <meta charset="utf-8" />
              <style>
                body { font-family: sans-serif; color: #333; }
                table { border-collapse: collapse; width: 100%; }
                th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
                th { background: #f5f5f5; }
              </style>
            </head>
            <body>${html}</body>
          </html>
        `,
      });
      setEmailResult('success');
    } catch (e) {
      setEmailResult('error');
    } finally {
      setEmailSending(false);
    }
  };

  // ─── 聚合計算 ─────────────────────────────────────────

  const agg = useMemo(() => {
    if (batches.length === 0) return null;

    // 各層級總計
    const layerTotals: CostByLayer = {
      material: 0, processing: 0, th_logistics: 0,
      freight: 0, tw_customs: 0, tw_logistics: 0, market: 0,
    };
    let totalCost = 0;
    let totalRevenue = 0;
    let totalWeight = 0;

    batches.forEach(b => {
      if (b.cost_by_layer) {
        (Object.keys(layerTotals) as (keyof CostByLayer)[]).forEach(k => {
          layerTotals[k] += b.cost_by_layer[k] ?? 0;
        });
      }
      totalCost    += b.total_cost_twd;
      totalRevenue += b.sales_revenue_twd;
      totalWeight  += b.current_weight_kg;
    });

    const grossProfit = totalRevenue - totalCost;
    const marginPct   = totalRevenue > 0 ? (grossProfit / totalRevenue) * 100 : null;
    const costPerKg   = totalWeight > 0 ? totalCost / totalWeight : 0;

    return { layerTotals, totalCost, totalRevenue, totalWeight, grossProfit, marginPct, costPerKg };
  }, [batches]);

  // CIF 計算（整體）
  const cifValue = useMemo(() => {
    if (!agg) return 0;
    // CIF = (material + processing + th_logistics + freight) * cifPct%
    const fobCost = agg.layerTotals.material + agg.layerTotals.processing +
                    agg.layerTotals.th_logistics + agg.layerTotals.freight;
    return fobCost * (cifPct / 100);
  }, [agg, cifPct]);

  if (loading) {
    return <div className="text-center py-20 text-gray-400">{tc('loading')}</div>;
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">{t('title')}</h1>
          <p className="text-sm text-gray-400 mt-0.5">{t('subtitle')}</p>
        </div>
        {/* 右側操作區：PDF 匯出、Email 發送、匯率控制 */}
        <div className="flex items-center gap-2 no-print">
          {/* PDF 匯出按鈕：使用瀏覽器列印功能 */}
          <button
            onClick={() => window.print()}
            className="flex items-center gap-1.5 btn-secondary text-sm py-1.5"
          >
            <Download size={13} />
            匯出 PDF
          </button>

          {/* 發送 Email 按鈕：開啟 Email Modal */}
          <button
            onClick={() => { setShowEmailModal(true); setEmailResult(null); }}
            className="flex items-center gap-1.5 btn-secondary text-sm py-1.5"
          >
            <Mail size={13} />
            發送報表
          </button>

          <span className="text-xs text-gray-400">THB→TWD</span>
          <input
            type="number"
            value={exchangeRate}
            onChange={(e) => setExchangeRate(parseFloat(e.target.value) || 0.92)}
            step="0.01"
            min="0.1"
            max="2"
            className="input w-20 py-1.5 text-sm text-right"
          />
          <button
            onClick={() => loadAll(exchangeRate)}
            disabled={reloading}
            className="flex items-center gap-1.5 btn-secondary text-sm py-1.5"
          >
            <RefreshCw size={13} className={reloading ? 'animate-spin' : ''} />
            {t('recalculate')}
          </button>
        </div>
      </div>

      {/* ── Email 發送 Modal（inline，不需要獨立元件） ── */}
      {showEmailModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 no-print">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-md p-6 mx-4">
            <h3 className="text-base font-semibold text-gray-800 mb-4 flex items-center gap-2">
              <Mail size={16} className="text-primary-500" />
              發送成本利潤報表 Email
            </h3>

            {/* 收件人輸入 */}
            <div className="mb-3">
              <label className="block text-xs font-medium text-gray-500 mb-1">
                收件人（多個 email 用逗號分隔）
              </label>
              <input
                type="text"
                value={emailTo}
                onChange={e => setEmailTo(e.target.value)}
                placeholder="finance@example.com, cfo@example.com"
                className="input w-full text-sm"
              />
            </div>

            {/* 主旨輸入 */}
            <div className="mb-4">
              <label className="block text-xs font-medium text-gray-500 mb-1">
                信件主旨
              </label>
              <input
                type="text"
                value={emailSubject}
                onChange={e => setEmailSubject(e.target.value)}
                className="input w-full text-sm"
              />
            </div>

            {/* 發送結果提示 */}
            {emailResult === 'success' && (
              <p className="text-sm text-green-600 bg-green-50 rounded-lg px-3 py-2 mb-3">
                Email 已成功發送！
              </p>
            )}
            {emailResult === 'error' && (
              <p className="text-sm text-red-600 bg-red-50 rounded-lg px-3 py-2 mb-3">
                發送失敗，請確認 SMTP 設定是否正確。
              </p>
            )}

            {/* 操作按鈕 */}
            <div className="flex gap-2 justify-end">
              <button
                onClick={() => setShowEmailModal(false)}
                className="btn-secondary text-sm px-4 py-1.5"
                disabled={emailSending}
              >
                取消
              </button>
              <button
                onClick={handleSendEmail}
                disabled={emailSending || !emailTo.trim()}
                className="btn-primary text-sm px-4 py-1.5"
              >
                {emailSending ? '發送中...' : '確認送出'}
              </button>
            </div>
          </div>
        </div>
      )}


      {/* ── 報表主體（id 供 Email 擷取 HTML 用） ── */}
      <div id="cost-report-content">

      {/* ── 1. KPI 摘要卡片 ── */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <KpiCard
          label={t('totalCost')}
          value={fmt(agg?.totalCost ?? 0)}
          sub={t('costPerKg', { value: agg ? agg.costPerKg.toFixed(1) : '0' })}
          gradient="from-red-50 to-orange-50 border-red-200"
          iconBg="bg-red-100"
          icon={<DollarSign size={20} className="text-red-600" />}
        />
        <KpiCard
          label={t('totalRevenue')}
          value={fmt(summary?.total_revenue_twd ?? 0)}
          sub={`${t('soRevenue')}: ${fmt(summary?.sales_revenue_so_twd ?? 0)} · ${t('dsRevenue')}: ${fmt(summary?.sales_revenue_ds_twd ?? 0)}`}
          gradient="from-green-50 to-emerald-50 border-green-200"
          iconBg="bg-green-100"
          icon={<TrendingUp size={20} className="text-green-600" />}
        />
        <KpiCard
          label={t('grossProfit')}
          value={fmt(agg?.grossProfit ?? 0)}
          sub={`${t('margin')}: ${fmtPct(agg?.marginPct ?? null)}`}
          gradient={(agg?.grossProfit ?? 0) >= 0
            ? 'from-emerald-50 to-teal-50 border-emerald-200'
            : 'from-red-50 to-pink-50 border-red-200'}
          iconBg={(agg?.grossProfit ?? 0) >= 0 ? 'bg-emerald-100' : 'bg-red-100'}
          icon={(agg?.grossProfit ?? 0) >= 0
            ? <TrendingUp size={20} className="text-emerald-600" />
            : <TrendingDown size={20} className="text-red-600" />}
        />
        <KpiCard
          label={t('inventory')}
          value={`${(summary?.stock_weight_kg ?? 0).toLocaleString()} kg`}
          sub={`${summary?.active_lots ?? 0} ${t('lots')} · ${summary?.total_batches ?? 0} ${t('totalBatchesShort')}`}
          gradient="from-blue-50 to-indigo-50 border-blue-200"
          iconBg="bg-blue-100"
          icon={<Package size={20} className="text-blue-600" />}
        />
      </div>

      {/* ── 2. 七層成本瀑布圖 ── */}
      {agg && agg.totalCost > 0 && (
        <div className="card p-6 mb-6">
          <div className="flex items-center gap-2 mb-5">
            <Layers size={16} className="text-gray-400" />
            <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wider">
              {t('layerBreakdown')}
            </h2>
            <span className="ml-auto text-xs text-gray-400">
              {t('totalBatchCount', { count: batches.length })}
            </span>
          </div>

          <div className="space-y-3">
            {COST_LAYERS.map(({ key, color, barColor }) => {
              const val = agg.layerTotals[key];
              const pct = agg.totalCost > 0 ? (val / agg.totalCost) * 100 : 0;
              const perKg = agg.totalWeight > 0 ? val / agg.totalWeight : 0;
              return (
                <div key={key} className="flex items-center gap-3">
                  <div className="w-28 flex-shrink-0">
                    <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${color}`}>
                      {t(`layers.${key}` as any)}
                    </span>
                  </div>
                  <div className="flex-1">
                    <div className="w-full bg-gray-100 rounded-full h-5 overflow-hidden">
                      <div
                        className={`h-full rounded-full ${barColor} transition-all duration-500 flex items-center justify-end pr-2`}
                        style={{ width: `${Math.max(pct, 2)}%` }}
                      >
                        {pct > 8 && (
                          <span className="text-[10px] text-white font-bold">{pct.toFixed(1)}%</span>
                        )}
                      </div>
                    </div>
                  </div>
                  <div className="w-24 text-right text-sm font-semibold text-gray-700 flex-shrink-0">
                    {fmt(val)}
                  </div>
                  <div className="w-20 text-right text-xs text-gray-400 flex-shrink-0">
                    {perKg > 0 ? `${perKg.toFixed(1)}/kg` : '—'}
                  </div>
                </div>
              );
            })}
            {/* 總計行 */}
            <div className="flex items-center gap-3 border-t border-gray-200 pt-3 mt-2">
              <div className="w-28 flex-shrink-0">
                <span className="text-sm font-bold text-gray-700">{t('totalLanded')}</span>
              </div>
              <div className="flex-1" />
              <div className="w-24 text-right text-base font-bold text-gray-900 flex-shrink-0">
                {fmt(agg.totalCost)}
              </div>
              <div className="w-20 text-right text-sm font-bold text-primary-700 flex-shrink-0">
                {agg.costPerKg.toFixed(1)}/kg
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── 3. CIF 計算器 ── */}
      {agg && agg.totalCost > 0 && (
        <div className="card p-6 mb-6 border-l-4 border-l-indigo-400">
          <div className="flex items-center gap-2 mb-4">
            <Calculator size={16} className="text-indigo-500" />
            <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wider">
              {t('cifCalculator')}
            </h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* FOB 基礎 */}
            <div className="bg-gray-50 rounded-xl p-4">
              <p className="text-xs text-gray-400 mb-1">{t('fobBase')}</p>
              <p className="text-lg font-bold text-gray-800">
                {fmt(agg.layerTotals.material + agg.layerTotals.processing +
                     agg.layerTotals.th_logistics + agg.layerTotals.freight)}
              </p>
              <p className="text-xs text-gray-400 mt-1">
                {t('fobComponents')}
              </p>
            </div>

            {/* CIF % 調整 */}
            <div className="bg-indigo-50 rounded-xl p-4">
              <p className="text-xs text-gray-400 mb-1">{t('cifPercent')}</p>
              <div className="flex items-center gap-2">
                <input
                  type="number"
                  value={cifPct}
                  onChange={e => setCifPct(parseFloat(e.target.value) || 70)}
                  min="1"
                  max="200"
                  step="5"
                  className="input w-20 py-1.5 text-lg font-bold text-center"
                />
                <Percent size={16} className="text-gray-400" />
              </div>
              <p className="text-xs text-gray-400 mt-1">
                {t('cifPercentHint')}
              </p>
            </div>

            {/* CIF 報關金額 */}
            <div className="bg-green-50 rounded-xl p-4">
              <p className="text-xs text-gray-400 mb-1">{t('cifDeclared')}</p>
              <p className="text-2xl font-bold text-green-700">
                {fmt(cifValue)}
              </p>
              <p className="text-xs text-gray-400 mt-1">
                {t('cifPerKg')}: {agg.totalWeight > 0
                  ? `NT$${(cifValue / agg.totalWeight).toFixed(1)}/kg`
                  : '—'}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* ── 4. 批次狀態分佈 ── */}
      {summary && summary.batch_by_status && (
        <div className="card p-5 mb-6">
          <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-3">
            {t('statusDistribution')}
          </h2>
          <div className="flex flex-wrap gap-2">
            {Object.entries(summary.batch_by_status)
              .filter(([, count]) => count > 0)
              .map(([status, count]) => (
                <Link
                  key={status}
                  href={`/${locale}/batches?status=${status}`}
                  className="flex items-center gap-1.5 px-3 py-1.5 bg-gray-100 hover:bg-primary-50 hover:text-primary-700 rounded-lg text-xs font-medium text-gray-600 transition-colors"
                >
                  <span className="font-semibold text-gray-800">{count}</span>
                  {tb(`status.${status}` as any)}
                </Link>
              ))
            }
          </div>
        </div>
      )}

      {/* ── 5. 批次成本明細表 ── */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-base font-semibold text-gray-700">{t('batchAnalysis')}</h2>
        </div>

        {batches.length === 0 ? (
          <div className="text-center py-16 text-gray-400 bg-white rounded-2xl border border-gray-200">
            <BarChart3 size={36} className="mx-auto mb-3 opacity-30" />
            <p>{t('noData')}</p>
          </div>
        ) : (
          <div className="bg-white rounded-2xl border border-gray-200 overflow-x-auto">
            <table className="w-full text-sm min-w-[900px]">
              <thead>
                <tr className="bg-gray-50 border-b border-gray-200 text-xs font-semibold text-gray-500 uppercase tracking-wider">
                  <th className="text-left px-4 py-3 w-8" />
                  <th className="text-left px-3 py-3">{t('batchNo')}</th>
                  <th className="text-left px-3 py-3">{t('status')}</th>
                  <th className="text-right px-3 py-3">{t('weightKg')}</th>
                  <th className="text-right px-3 py-3">{t('landedCost')}</th>
                  <th className="text-right px-3 py-3">{t('perKg')}</th>
                  <th className="text-right px-3 py-3">{t('salesRevenueTWD')}</th>
                  <th className="text-right px-4 py-3">{t('marginPct')}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {batches.map((b) => {
                  const margin      = b.gross_margin_pct;
                  const marginColor = margin == null ? 'text-gray-300'
                    : margin >= 20 ? 'text-green-600'
                    : margin >= 0  ? 'text-yellow-600'
                    : 'text-red-600';
                  const isExpanded  = expandedBatch === b.batch_id;

                  return (
                    <BatchRow
                      key={b.batch_id}
                      b={b}
                      isExpanded={isExpanded}
                      onToggle={() => setExpandedBatch(isExpanded ? null : b.batch_id)}
                      marginColor={marginColor}
                      locale={locale}
                      t={t}
                      tb={tb}
                    />
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      </div>{/* 結束 cost-report-content */}
    </div>
  );
}

// ─── KPI 卡片元件 ──────────────────────────────────────────────

function KpiCard({ label, value, sub, gradient, iconBg, icon }: {
  label: string; value: string; sub: string;
  gradient: string; iconBg: string; icon: React.ReactNode;
}) {
  return (
    <div className={`card bg-gradient-to-br ${gradient} p-5`}>
      <div className="flex items-start gap-3">
        <div className={`w-10 h-10 rounded-lg ${iconBg} flex items-center justify-center flex-shrink-0`}>
          {icon}
        </div>
        <div className="min-w-0">
          <p className="text-xs text-gray-500 font-medium">{label}</p>
          <p className="text-xl font-bold text-gray-800 mt-0.5 truncate">{value}</p>
          {sub && <p className="text-[11px] text-gray-400 mt-0.5 leading-tight">{sub}</p>}
        </div>
      </div>
    </div>
  );
}

// ─── 批次行（含展開） ───────────────────────────────────────────

function BatchRow({ b, isExpanded, onToggle, marginColor, locale, t, tb }: {
  b: BatchAnalytic; isExpanded: boolean; onToggle: () => void;
  marginColor: string; locale: string;
  t: ReturnType<typeof useTranslations>; tb: ReturnType<typeof useTranslations>;
}) {
  const margin    = b.gross_margin_pct;
  const hasLayers = b.cost_by_layer && Object.values(b.cost_by_layer).some(v => v > 0);

  return (
    <>
      <tr
        className="hover:bg-gray-50 transition-colors cursor-pointer"
        onClick={hasLayers ? onToggle : undefined}
      >
        <td className="px-4 py-3.5">
          {hasLayers ? (
            isExpanded
              ? <ChevronDown size={14} className="text-gray-400" />
              : <ChevronRight size={14} className="text-gray-400" />
          ) : <span className="w-3.5" />}
        </td>
        <td className="px-3 py-3.5">
          <Link
            href={`/${locale}/batches/${b.batch_id}`}
            className="font-mono font-semibold text-primary-600 hover:underline"
            onClick={e => e.stopPropagation()}
          >
            {b.batch_no}
          </Link>
          {b.po_order_no && (
            <span className="text-xs text-gray-400 ml-2 font-mono">{b.po_order_no}</span>
          )}
        </td>
        <td className="px-3 py-3.5">
          <span className="px-2 py-0.5 rounded-full text-xs bg-gray-100 text-gray-600">
            {tb(`status.${b.status}` as any)}
          </span>
        </td>
        <td className="px-3 py-3.5 text-right text-gray-700">
          {Number(b.current_weight_kg).toLocaleString()} kg
        </td>
        <td className="px-3 py-3.5 text-right font-semibold text-gray-800">
          {b.total_cost_twd > 0
            ? fmt(b.total_cost_twd)
            : <span className="text-gray-300">—</span>}
        </td>
        <td className="px-3 py-3.5 text-right text-primary-700 font-semibold">
          {b.cost_per_kg_twd > 0
            ? `${b.cost_per_kg_twd.toFixed(1)}`
            : <span className="text-gray-300">—</span>}
        </td>
        <td className="px-3 py-3.5 text-right">
          {b.sales_revenue_twd > 0 ? (
            <span className="font-semibold text-green-700">{fmt(b.sales_revenue_twd)}</span>
          ) : (
            <span className="text-gray-300">—</span>
          )}
        </td>
        <td className="px-4 py-3.5 text-right">
          {margin != null ? (
            <span className={`font-bold flex items-center justify-end gap-1 ${marginColor}`}>
              {margin >= 0 ? <TrendingUp size={13} /> : <TrendingDown size={13} />}
              {margin.toFixed(1)}%
            </span>
          ) : (
            <span className="text-gray-300">—</span>
          )}
        </td>
      </tr>

      {/* 展開行：顯示 7 層成本明細 */}
      {isExpanded && hasLayers && (
        <tr>
          <td colSpan={8} className="px-4 py-0">
            <div className="py-3 pl-10 pr-4 bg-gray-50/50 rounded-lg mb-2">
              <div className="grid grid-cols-7 gap-2">
                {COST_LAYERS.map(({ key, color }) => {
                  const val   = b.cost_by_layer[key] ?? 0;
                  const perKg = b.current_weight_kg > 0 ? val / b.current_weight_kg : 0;
                  return (
                    <div key={key} className="text-center">
                      <span className={`inline-block px-1.5 py-0.5 rounded text-[10px] font-medium ${color} mb-1`}>
                        {t(`layers.${key}` as any)}
                      </span>
                      <p className="text-sm font-semibold text-gray-700">
                        {val > 0 ? fmt(val) : '—'}
                      </p>
                      <p className="text-[10px] text-gray-400">
                        {perKg > 0 ? `${perKg.toFixed(1)}/kg` : ''}
                      </p>
                    </div>
                  );
                })}
              </div>
            </div>
          </td>
        </tr>
      )}
    </>
  );
}
