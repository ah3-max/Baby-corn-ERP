'use client';

/**
 * O-03 財務儀表板
 */
import { useTranslations } from 'next-intl';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api';
import { DollarSign, TrendingUp, TrendingDown, CreditCard, PieChart as PieIcon } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';
import { clsx } from 'clsx';

const PIE_COLORS = ['#ef4444', '#f59e0b', '#22c55e', '#6366f1'];

export default function FinanceDashboard() {
  const t = useTranslations('dashboardFinance');

  const { data: finData }  = useQuery({ queryKey: ['fin-dash-summary'], queryFn: async () => (await apiClient.get('/finance/summary')).data });
  const { data: arData }   = useQuery({ queryKey: ['fin-dash-ar'],      queryFn: async () => (await apiClient.get('/finance/ar',  { params: { limit: 20 } })).data });
  const { data: apData }   = useQuery({ queryKey: ['fin-dash-ap'],      queryFn: async () => (await apiClient.get('/finance/ap',  { params: { limit: 20 } })).data });
  const { data: pnlData }  = useQuery({ queryKey: ['fin-dash-pnl'],     queryFn: async () => (await apiClient.get('/finance/pnl')).data });
  const { data: bankData } = useQuery({ queryKey: ['fin-dash-banks'],   queryFn: async () => (await apiClient.get('/finance/bank-accounts', { params: { is_active: true } })).data });

  const monthRevenue  = finData?.month_revenue_twd ?? 0;
  const arTotal       = finData?.ar_total_twd ?? 0;
  const arOverdue     = finData?.ar_overdue_twd ?? 0;
  const grossMargin   = finData?.gross_margin_pct ?? 0;
  const arItems       = arData?.items ?? arData ?? [];
  const apItems       = apData?.items ?? apData ?? [];
  const bankAccounts  = bankData?.items ?? bankData ?? [];

  // AR 帳齡分析
  const today = new Date().toISOString().split('T')[0];
  const arAging = { current: 0, d30: 0, d60: 0, d60plus: 0 };
  (Array.isArray(arItems) ? arItems : []).forEach((ar: any) => {
    const remaining = ar.remaining_amount_twd || 0;
    if (!ar.due_date) { arAging.current += remaining; return; }
    const days = Math.ceil((new Date(today).getTime() - new Date(ar.due_date).getTime()) / 86400000);
    if (days <= 0)       arAging.current += remaining;
    else if (days <= 30) arAging.d30     += remaining;
    else if (days <= 60) arAging.d60     += remaining;
    else                 arAging.d60plus += remaining;
  });
  const agingChart = (Object.keys(arAging) as Array<keyof typeof arAging>).map(k => ({
    label: t(`arAgingLabels.${k}`),
    value: Math.round(arAging[k] / 1000),
  }));

  // PnL 趨勢
  const pnlRows = pnlData?.rows ?? [];
  const pnlTrend = (Array.isArray(pnlRows) ? pnlRows : []).slice(-6).map((r: any) => ({
    month:   (r.period || '').slice(5, 7),
    revenue: Math.round((r.revenue_twd || 0) / 1000),
    cost:    Math.round((r.cost_twd || 0) / 1000),
  }));

  const totalBankBalance = (Array.isArray(bankAccounts) ? bankAccounts : [])
    .filter((b: any) => b.currency === 'TWD')
    .reduce((s: number, b: any) => s + (b.current_balance || 0), 0);

  return (
    <div className="p-6 space-y-6 max-w-7xl">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
          <DollarSign className="text-emerald-600" size={24} />
          {t('title')}
        </h1>
        <p className="text-sm text-gray-500 mt-1">{t('subtitle')}</p>
      </div>

      {/* 核心 KPI */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <FinCard icon={<TrendingUp size={20} />}  color="green"
          label={t('kpiRevenue')} value={`NT$${Math.round(monthRevenue/1000)}K`} sub={t('kpiRevenueSubLabel')} />
        <FinCard icon={<PieIcon size={20} />}      color="indigo"
          label={t('kpiMargin')}  value={`${grossMargin.toFixed(1)}%`}            sub={t('kpiMarginSubLabel')} />
        <FinCard icon={<CreditCard size={20} />}   color={arOverdue > 0 ? 'red' : 'blue'}
          label={t('kpiArOverdue')} value={`NT$${Math.round(arOverdue/1000)}K`}
          sub={t('kpiArTotal', { amount: Math.round(arTotal/1000) })} alert={arOverdue > 0} />
        <FinCard icon={<DollarSign size={20} />}   color="teal"
          label={t('kpiBankBalance')} value={`NT$${Math.round(totalBankBalance/1000)}K`}
          sub={t('kpiBankAccounts', { count: Array.isArray(bankAccounts) ? bankAccounts.length : 0 })} />
      </div>

      {/* PnL 趨勢 + AR 帳齡 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-xl border p-5">
          <h2 className="text-sm font-semibold text-gray-600 mb-4">{t('pnlTrend')}</h2>
          {pnlTrend.length > 0 ? (
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={pnlTrend}>
                <XAxis dataKey="month" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip />
                <Bar dataKey="revenue" name={t('pnlRevenue')} fill="#6366f1" radius={[4,4,0,0]} />
                <Bar dataKey="cost"    name={t('pnlCost')}    fill="#f87171" radius={[4,4,0,0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-48 flex items-center justify-center text-gray-300 text-sm">{t('pnlNoData')}</div>
          )}
        </div>

        <div className="bg-white rounded-xl border p-5">
          <h2 className="text-sm font-semibold text-gray-600 mb-4">{t('arAging')}</h2>
          {agingChart.some(a => a.value > 0) ? (
            <div className="flex items-center gap-4">
              <ResponsiveContainer width="50%" height={180}>
                <PieChart>
                  <Pie data={agingChart} dataKey="value" cx="50%" cy="50%" outerRadius={70} paddingAngle={2}>
                    {agingChart.map((_, i) => <Cell key={i} fill={PIE_COLORS[i]} />)}
                  </Pie>
                  <Tooltip formatter={(v: any) => [`NT$${v}K`]} />
                </PieChart>
              </ResponsiveContainer>
              <div className="space-y-2">
                {agingChart.map((a, i) => (
                  <div key={i} className="flex items-center gap-2 text-xs">
                    <div className="w-3 h-3 rounded-sm flex-shrink-0" style={{ background: PIE_COLORS[i] }} />
                    <span className="text-gray-600 w-16">{a.label}</span>
                    <span className="font-bold text-gray-800">NT${a.value}K</span>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="h-44 flex items-center justify-center text-gray-300 text-sm">{t('arNoData')}</div>
          )}
        </div>
      </div>

      {/* AP 到期 + 銀行帳戶 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-xl border overflow-hidden">
          <div className="px-5 py-4 border-b">
            <h2 className="text-sm font-semibold text-gray-600 flex items-center gap-2">
              <TrendingDown size={16} /> {t('apTitle')}
            </h2>
          </div>
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
              <tr>
                <th className="px-4 py-2 text-left">{t('apColSupplier')}</th>
                <th className="px-4 py-2 text-left">{t('apColDueDate')}</th>
                <th className="px-4 py-2 text-right">{t('apColAmount')}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {(Array.isArray(apItems) ? apItems : [])
                .filter((a: any) => a.status === 'unpaid' || a.status === 'partial')
                .slice(0, 5)
                .map((ap: any) => (
                  <tr key={ap.id} className="hover:bg-gray-50">
                    <td className="px-4 py-2.5 text-gray-900 truncate max-w-[140px]">{ap.supplier?.name || ap.supplier_name || '—'}</td>
                    <td className={clsx('px-4 py-2.5', ap.due_date < today ? 'text-red-600 font-medium' : 'text-gray-600')}>
                      {ap.due_date || '—'}
                    </td>
                    <td className="px-4 py-2.5 text-right font-mono text-gray-700">
                      {ap.remaining_amount_twd ? `NT$${Math.round(ap.remaining_amount_twd).toLocaleString()}` : '—'}
                    </td>
                  </tr>
                ))}
              {(Array.isArray(apItems) ? apItems : []).filter((a: any) => a.status === 'unpaid' || a.status === 'partial').length === 0 && (
                <tr><td colSpan={3} className="px-4 py-6 text-center text-gray-400">{t('apNoData')}</td></tr>
              )}
            </tbody>
          </table>
        </div>

        <div className="bg-white rounded-xl border p-5">
          <h2 className="text-sm font-semibold text-gray-600 mb-4">{t('bankTitle')}</h2>
          {(Array.isArray(bankAccounts) ? bankAccounts : []).length === 0 ? (
            <p className="text-sm text-gray-400 text-center py-8">{t('bankNoData')}</p>
          ) : (
            <div className="space-y-3">
              {(Array.isArray(bankAccounts) ? bankAccounts : []).slice(0, 5).map((b: any) => (
                <div key={b.id} className="flex items-center justify-between py-2 border-b last:border-0">
                  <div>
                    <p className="text-sm font-medium text-gray-800">{b.bank_name} {b.account_name || ''}</p>
                    <p className="text-xs text-gray-400">{b.currency} · {b.account_type || ''}</p>
                  </div>
                  <p className="text-sm font-bold text-gray-900">
                    {b.currency} {Number(b.current_balance || 0).toLocaleString()}
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function FinCard({ icon, color, label, value, sub, alert }: {
  icon: React.ReactNode; color: string; label: string; value: string; sub: string; alert?: boolean;
}) {
  const colors: Record<string, string> = {
    green: 'bg-green-50 text-green-600', indigo: 'bg-indigo-50 text-indigo-600',
    red:   'bg-red-50 text-red-600',     blue:   'bg-blue-50 text-blue-600',
    teal:  'bg-teal-50 text-teal-600',
  };
  return (
    <div className={`bg-white rounded-xl border p-4 ${alert ? 'border-red-200' : ''}`}>
      <div className={`w-9 h-9 rounded-lg flex items-center justify-center mb-3 ${colors[color] || 'bg-gray-50 text-gray-400'}`}>{icon}</div>
      <p className="text-2xl font-bold text-gray-900">{value}</p>
      <p className="text-xs font-medium text-gray-600 mt-0.5">{label}</p>
      <p className={`text-xs mt-1 ${alert ? 'text-red-500' : 'text-gray-400'}`}>{sub}</p>
    </div>
  );
}
