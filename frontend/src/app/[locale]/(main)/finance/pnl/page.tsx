'use client';

/**
 * P-06 跨幣別損益報表頁面（I-08）
 */
import { useState } from 'react';
import { useTranslations } from 'next-intl';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api';
import { LineChart, TrendingUp, DollarSign, Activity } from 'lucide-react';
import {
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis,
  CartesianGrid, Tooltip, Legend,
} from 'recharts';

export default function PnlReportPage() {
  const t = useTranslations('financePnl');
  const today = new Date();
  const [year, setYear] = useState(today.getFullYear());
  const [month, setMonth] = useState(today.getMonth() + 1);
  const [trendMonths, setTrendMonths] = useState(6);

  const { data: pnl, isLoading } = useQuery({
    queryKey: ['pnl', year, month],
    queryFn: async () => {
      const res = await apiClient.get('/finance/pnl', { params: { year, month } });
      return res.data;
    },
  });

  const { data: trend } = useQuery({
    queryKey: ['pnl-trend', trendMonths],
    queryFn: async () => {
      const res = await apiClient.get('/finance/pnl/monthly-trend', { params: { months: trendMonths } });
      return res.data;
    },
  });

  const { data: taxCalc } = useQuery({
    queryKey: ['thai-tax-demo'],
    queryFn: async () => {
      const res = await apiClient.get('/finance/thai-tax', { params: { amount_thb: 100000 } });
      return res.data;
    },
  });

  const trendData = (trend?.trend || []).map((item: any) => ({
    name: item.label,
    revenue: item.revenue_twd ? Math.round(item.revenue_twd / 1000) : 0,
    grossProfit: item.gross_profit_twd ? Math.round(item.gross_profit_twd / 1000) : 0,
    margin: item.gross_margin_pct || 0,
  }));

  return (
    <div className="p-6 space-y-6">
      {/* 頁頭 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <LineChart className="text-primary-600" size={24} />
            {t('title')}
          </h1>
          <p className="text-sm text-gray-500 mt-1">{t('subtitle')}</p>
        </div>
        {/* 月份選擇 */}
        <div className="flex items-center gap-2">
          <select
            value={year}
            onChange={e => setYear(Number(e.target.value))}
            className="border rounded-lg px-3 py-1.5 text-sm"
          >
            {[2024, 2025, 2026, 2027].map(y => (
              <option key={y} value={y}>{t('yearSuffix', { year: y })}</option>
            ))}
          </select>
          <select
            value={month}
            onChange={e => setMonth(Number(e.target.value))}
            className="border rounded-lg px-3 py-1.5 text-sm"
          >
            {Array.from({ length: 12 }, (_, i) => i + 1).map(m => (
              <option key={m} value={m}>{t('monthSuffix', { month: m })}</option>
            ))}
          </select>
        </div>
      </div>

      {/* 本月損益卡片 */}
      {isLoading ? (
        <div className="text-center py-8 text-gray-400">{t('loading')}</div>
      ) : pnl && (
        <div className="grid grid-cols-4 gap-4">
          {[
            {
              labelKey: 'kpiRevenue',
              value: `$${(pnl.revenue_twd / 1000).toFixed(0)}K`,
              sub: 'TWD',
              color: 'text-primary-600',
              bg: 'bg-primary-50',
              icon: DollarSign,
            },
            {
              labelKey: 'kpiCost',
              value: pnl.purchase_cost_twd != null
                ? `$${(pnl.purchase_cost_twd / 1000).toFixed(0)}K`
                : `฿${(pnl.purchase_cost_thb / 1000).toFixed(0)}K`,
              sub: pnl.purchase_cost_twd != null ? 'TWD' : 'THB',
              color: 'text-red-600',
              bg: 'bg-red-50',
              icon: TrendingUp,
            },
            {
              labelKey: 'kpiProfit',
              value: pnl.gross_profit_twd != null
                ? `$${(pnl.gross_profit_twd / 1000).toFixed(0)}K`
                : '—',
              sub: 'TWD',
              color: pnl.gross_profit_twd > 0 ? 'text-green-600' : 'text-red-600',
              bg: 'bg-green-50',
              icon: Activity,
            },
            {
              labelKey: 'kpiMargin',
              value: pnl.gross_margin_pct != null
                ? `${pnl.gross_margin_pct.toFixed(1)}%`
                : '—',
              sub: pnl.monthly_avg_rate
                ? t('avgRate', { rate: pnl.monthly_avg_rate })
                : t('avgRateNoData'),
              color: 'text-indigo-600',
              bg: 'bg-indigo-50',
              icon: Activity,
            },
          ].map((card, idx) => (
            <div key={idx} className="bg-white rounded-xl border p-5">
              <div className="flex items-center gap-3 mb-3">
                <div className={`w-9 h-9 rounded-lg flex items-center justify-center ${card.bg}`}>
                  <card.icon size={18} className={card.color} />
                </div>
                <p className="text-sm text-gray-500">{t(card.labelKey as any)}</p>
              </div>
              <p className={`text-2xl font-bold ${card.color}`}>{card.value}</p>
              <p className="text-xs text-gray-400 mt-1">{card.sub}</p>
            </div>
          ))}
        </div>
      )}

      {/* 趨勢圖 */}
      <div className="bg-white rounded-xl border p-5">
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-semibold text-gray-900">{t('trendTitle')}</h2>
          <select
            value={trendMonths}
            onChange={e => setTrendMonths(Number(e.target.value))}
            className="border rounded-lg px-2 py-1 text-sm"
          >
            <option value={3}>{t('trendMonths3')}</option>
            <option value={6}>{t('trendMonths6')}</option>
            <option value={12}>{t('trendMonths12')}</option>
          </select>
        </div>
        <ResponsiveContainer width="100%" height={260}>
          <BarChart data={trendData} margin={{ top: 4, right: 16, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} />
            <XAxis dataKey="name" tick={{ fontSize: 12 }} />
            <YAxis tick={{ fontSize: 12 }} unit="K" />
            <Tooltip formatter={(v: number) => `$${v}K TWD`} />
            <Legend />
            <Bar dataKey="revenue" name={t('trendRevenue')} fill="#6366f1" radius={[4, 4, 0, 0]} />
            <Bar dataKey="grossProfit" name={t('trendProfit')} fill="#10b981" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* 泰國稅務試算 */}
      {taxCalc && (
        <div className="bg-white rounded-xl border p-5">
          <h2 className="font-semibold text-gray-900 mb-4">{t('taxTitle')}</h2>
          <div className="grid grid-cols-3 gap-4 text-sm">
            <div className="bg-gray-50 rounded-lg p-4">
              <p className="text-gray-500">{t('taxPreVat')}</p>
              <p className="text-xl font-bold text-gray-900 mt-1">฿{taxCalc.amount_thb?.toLocaleString()}</p>
            </div>
            <div className="bg-orange-50 rounded-lg p-4">
              <p className="text-gray-500">{t('taxVat')}</p>
              <p className="text-xl font-bold text-orange-600 mt-1">฿{taxCalc.vat_amount?.toLocaleString()}</p>
            </div>
            <div className="bg-blue-50 rounded-lg p-4">
              <p className="text-gray-500">{t('taxWht', { rate: taxCalc.wht_rate_pct })}</p>
              <p className="text-xl font-bold text-blue-600 mt-1">฿{taxCalc.wht_amount?.toLocaleString()}</p>
            </div>
          </div>
          <div className="mt-4 p-4 bg-green-50 rounded-lg flex items-center justify-between">
            <p className="text-gray-700 font-medium">{t('taxNetPayable')}</p>
            <p className="text-2xl font-bold text-green-600">฿{taxCalc.net_payable?.toLocaleString()}</p>
          </div>
          {taxCalc.note && <p className="text-xs text-gray-400 mt-2">{taxCalc.note}</p>}
        </div>
      )}
    </div>
  );
}
