'use client';

/**
 * O-03 CEO 戰略儀表板
 */
import { useTranslations } from 'next-intl';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api';
import { TrendingUp, DollarSign, Globe, AlertTriangle, Package, Users, BarChart3, Target } from 'lucide-react';
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';

const COLORS = ['#6366f1', '#22c55e', '#f59e0b', '#ef4444', '#8b5cf6'];

export default function ExecutiveDashboard() {
  const t = useTranslations('dashboardExecutive');

  const { data: finData } = useQuery({
    queryKey: ['exec-finance'],
    queryFn: async () => (await apiClient.get('/finance/summary')).data,
  });

  const { data: kpiData } = useQuery({
    queryKey: ['exec-kpi'],
    queryFn: async () => (await apiClient.get('/kpi/values/latest')).data,
  });

  const { data: salesData } = useQuery({
    queryKey: ['exec-sales'],
    queryFn: async () => (await apiClient.get('/sales/orders', { params: { limit: 50 } })).data,
  });

  const { data: invData } = useQuery({
    queryKey: ['exec-inventory'],
    queryFn: async () => (await apiClient.get('/inventory/summary')).data,
  });

  const { data: marketData } = useQuery({
    queryKey: ['exec-market'],
    queryFn: async () => (await apiClient.get('/market-intel/prices', { params: { limit: 10 } })).data,
  });

  const monthRevenue  = finData?.month_revenue_twd ?? 0;
  const arTotal       = finData?.ar_total_twd ?? 0;
  const arOverdue     = finData?.ar_overdue_twd ?? 0;
  const grossMarginPct = finData?.gross_margin_pct ?? 0;
  const kpiItems      = kpiData?.items ?? [];
  const salesItems    = salesData?.items ?? salesData ?? [];
  const totalStock    = invData?.total_weight_kg ?? 0;
  const ageAlert      = invData?.age_alert ?? 0;

  // 月別銷售趨勢
  const revenueByMonth: Record<string, number> = {};
  (Array.isArray(salesItems) ? salesItems : []).forEach((s: any) => {
    const mo = (s.order_date || s.created_at || '').slice(0, 7);
    if (mo) revenueByMonth[mo] = (revenueByMonth[mo] || 0) + (s.total_amount_twd || 0);
  });
  const revTrend = Object.entries(revenueByMonth).sort().slice(-6).map(([m, v]) => ({
    month: m.slice(5),
    revenue: Math.round(v / 1000),
  }));

  return (
    <div className="p-6 space-y-6 max-w-7xl">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
          <Target className="text-indigo-600" size={24} />
          {t('title')}
        </h1>
        <p className="text-sm text-gray-500 mt-1">{t('subtitle')}</p>
      </div>

      {/* KPI 核心指標 */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard icon={<DollarSign size={20} />} color="indigo"
          label={t('kpiRevenue')} value={`NT$${Math.round(monthRevenue / 1000)}K`} subLabel={t('kpiRevenueSubLabel')} />
        <KpiCard icon={<TrendingUp size={20} />} color="green"
          label={t('kpiMargin')} value={`${grossMarginPct.toFixed(1)}%`} subLabel={t('kpiMarginSubLabel')} />
        <KpiCard icon={<Package size={20} />} color="blue"
          label={t('kpiStock')} value={`${Math.round(totalStock).toLocaleString()} kg`}
          subLabel={ageAlert > 0 ? t('kpiStockOverage', { count: ageAlert }) : t('kpiStockOk')}
          alert={ageAlert > 0} />
        <KpiCard icon={<AlertTriangle size={20} />} color={arOverdue > 0 ? 'red' : 'gray'}
          label={t('kpiArOverdue')} value={`NT$${Math.round(arOverdue / 1000)}K`}
          subLabel={t('kpiArTotal', { amount: Math.round(arTotal / 1000) })}
          alert={arOverdue > 0} />
      </div>

      {/* 營收趨勢 + KPI */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 bg-white rounded-xl border p-5">
          <h2 className="text-sm font-semibold text-gray-600 mb-4 flex items-center gap-2">
            <BarChart3 size={16} /> {t('revenueTrend')}
          </h2>
          {revTrend.length > 0 ? (
            <ResponsiveContainer width="100%" height={200}>
              <AreaChart data={revTrend}>
                <XAxis dataKey="month" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip formatter={(v: any) => [`NT$${v}K`, t('revenueTrendTooltip')]} />
                <Area type="monotone" dataKey="revenue" stroke="#6366f1" fill="#e0e7ff" strokeWidth={2} />
              </AreaChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-48 flex items-center justify-center text-gray-300 text-sm">{t('revenueTrendNoData')}</div>
          )}
        </div>

        <div className="bg-white rounded-xl border p-5">
          <h2 className="text-sm font-semibold text-gray-600 mb-4 flex items-center gap-2">
            <Target size={16} /> {t('kpiAchievement')}
          </h2>
          {kpiItems.length === 0 ? (
            <p className="text-sm text-gray-400 text-center py-8">{t('kpiNoData')}</p>
          ) : (
            <div className="space-y-3">
              {kpiItems.slice(0, 6).map((k: any) => {
                const pct = k.target_value ? Math.min(100, Math.round((k.actual_value / k.target_value) * 100)) : 0;
                return (
                  <div key={k.id}>
                    <div className="flex justify-between text-xs mb-1">
                      <span className="text-gray-600 truncate max-w-[140px]">{k.kpi_name || k.kpi_code}</span>
                      <span className={pct >= 100 ? 'text-green-600 font-bold' : pct >= 80 ? 'text-yellow-600' : 'text-red-600'}>{pct}%</span>
                    </div>
                    <div className="w-full bg-gray-100 rounded-full h-1.5">
                      <div className={`h-1.5 rounded-full ${pct >= 100 ? 'bg-green-500' : pct >= 80 ? 'bg-yellow-400' : 'bg-red-400'}`} style={{ width: `${pct}%` }} />
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* 市場快訊 + 供應鏈健康 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-xl border p-5">
          <h2 className="text-sm font-semibold text-gray-600 mb-4 flex items-center gap-2">
            <Globe size={16} /> {t('marketNews')}
          </h2>
          {(marketData?.items || []).length === 0 ? (
            <p className="text-sm text-gray-400 text-center py-8">{t('marketNoData')}</p>
          ) : (
            <div className="space-y-2">
              {(marketData?.items || []).slice(0, 5).map((m: any, i: number) => (
                <div key={i} className="flex items-center justify-between py-2 border-b last:border-0">
                  <div>
                    <p className="text-sm font-medium text-gray-800">{m.market_name || m.source_name}</p>
                    <p className="text-xs text-gray-400">{m.price_date || m.recorded_at?.split('T')[0]}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-bold text-indigo-700">{m.price} {m.currency || 'TWD'}</p>
                    <p className="text-xs text-gray-400">/{m.unit || 'kg'}</p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="bg-white rounded-xl border p-5">
          <h2 className="text-sm font-semibold text-gray-600 mb-4 flex items-center gap-2">
            <Users size={16} /> {t('supplyChainHealth')}
          </h2>
          <div className="grid grid-cols-2 gap-3">
            <HealthMetric label={t('healthLotCount')} value={invData?.lot_count ?? '—'} unit={t('healthLotUnit')} color="green" />
            <HealthMetric label={t('healthWeight')} value={totalStock ? `${Math.round(totalStock / 1000)}t` : '—'} unit="" color="blue" />
            <HealthMetric label={t('healthAgeAlert')} value={ageAlert || 0} unit={t('healthLotUnit')} color={ageAlert > 0 ? 'red' : 'green'} />
            <HealthMetric label={t('healthArOverdueRate')} value={arTotal > 0 ? `${Math.round((arOverdue / arTotal) * 100)}%` : '0%'} unit="" color={arOverdue / arTotal > 0.1 ? 'red' : 'green'} />
          </div>
        </div>
      </div>
    </div>
  );
}

function KpiCard({ icon, color, label, value, subLabel, alert }: {
  icon: React.ReactNode; color: string; label: string; value: string; subLabel: string; alert?: boolean;
}) {
  const colors: Record<string, string> = {
    indigo: 'bg-indigo-50 text-indigo-600', green: 'bg-green-50 text-green-600',
    blue: 'bg-blue-50 text-blue-600', red: 'bg-red-50 text-red-600', gray: 'bg-gray-50 text-gray-400',
  };
  return (
    <div className={`bg-white rounded-xl border p-4 ${alert ? 'border-red-200' : ''}`}>
      <div className={`w-9 h-9 rounded-lg flex items-center justify-center mb-3 ${colors[color]}`}>{icon}</div>
      <p className="text-2xl font-bold text-gray-900">{value}</p>
      <p className="text-xs font-medium text-gray-600 mt-0.5">{label}</p>
      <p className={`text-xs mt-1 ${alert ? 'text-red-500' : 'text-gray-400'}`}>{subLabel}</p>
    </div>
  );
}

function HealthMetric({ label, value, unit, color }: { label: string; value: any; unit: string; color: string }) {
  const colors: Record<string, string> = { green: 'text-green-600', blue: 'text-blue-600', red: 'text-red-600' };
  return (
    <div className="bg-gray-50 rounded-lg p-3">
      <p className="text-xs text-gray-500 mb-1">{label}</p>
      <p className={`text-xl font-bold ${colors[color]}`}>{value}<span className="text-xs ml-1 font-normal text-gray-400">{unit}</span></p>
    </div>
  );
}
