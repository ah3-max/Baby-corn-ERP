'use client';

/**
 * O-03 銷售儀表板
 */
import { useTranslations } from 'next-intl';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api';
import { ShoppingCart, TrendingUp, Target, Clock } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, LineChart, Line } from 'recharts';
import { clsx } from 'clsx';

const STAGE_COLORS: Record<string, string> = {
  lead:        'bg-gray-100 text-gray-600',
  qualify:     'bg-blue-100 text-blue-700',
  proposal:    'bg-yellow-100 text-yellow-700',
  negotiation: 'bg-orange-100 text-orange-700',
  closed_won:  'bg-green-100 text-green-700',
  closed_lost: 'bg-red-100 text-red-700',
};

export default function SalesDashboard() {
  const t = useTranslations('dashboardSales');

  const { data: salesData } = useQuery({ queryKey: ['sales-dash-orders'], queryFn: async () => (await apiClient.get('/sales/orders',      { params: { limit: 100 } })).data });
  const { data: oppData }   = useQuery({ queryKey: ['sales-dash-opps'],   queryFn: async () => (await apiClient.get('/crm/opportunities', { params: { limit: 50 } })).data });
  const { data: crmData }   = useQuery({ queryKey: ['sales-dash-crm'],    queryFn: async () => (await apiClient.get('/crm/dashboard')).data });
  const { data: dailyData } = useQuery({ queryKey: ['sales-dash-daily'],  queryFn: async () => (await apiClient.get('/daily-sales',       { params: { limit: 14 } })).data });

  const orders     = salesData?.items ?? salesData ?? [];
  const opps       = oppData?.items   ?? oppData   ?? [];
  const dailySales = dailyData?.items ?? dailyData ?? [];

  const statusCount: Record<string, number> = {};
  (Array.isArray(orders) ? orders : []).forEach((o: any) => {
    statusCount[o.status] = (statusCount[o.status] || 0) + 1;
  });

  const stageCount: Record<string, number> = {};
  const stageValue: Record<string, number> = {};
  (Array.isArray(opps) ? opps : []).forEach((o: any) => {
    stageCount[o.stage] = (stageCount[o.stage] || 0) + 1;
    stageValue[o.stage] = (stageValue[o.stage] || 0) + (o.expected_value_twd || 0);
  });
  const STAGE_KEYS = ['lead', 'qualify', 'proposal', 'negotiation', 'closed_won'] as const;
  const funnel = STAGE_KEYS.map(s => ({
    stage: t(`stage.${s}`),
    count: stageCount[s] || 0,
    value: Math.round((stageValue[s] || 0) / 1000),
  }));

  const dailyTrend = (Array.isArray(dailySales) ? dailySales : [])
    .slice(0, 14).reverse()
    .map((d: any) => ({ date: (d.sale_date || '').slice(5), total: Math.round((d.total_amount_twd || 0) / 1000) }));

  const pendingTasks   = crmData?.pending_tasks ?? 0;
  const totalOppValue  = Object.values(stageValue).reduce((a, b) => a + b, 0);
  const wonValue       = stageValue['closed_won'] || 0;
  const winRate        = totalOppValue > 0 ? Math.round((wonValue / totalOppValue) * 100) : 0;

  return (
    <div className="p-6 space-y-6 max-w-7xl">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
          <ShoppingCart className="text-green-600" size={24} />
          {t('title')}
        </h1>
        <p className="text-sm text-gray-500 mt-1">{t('subtitle')}</p>
      </div>

      {/* 核心指標 */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard icon={<ShoppingCart size={20} />} color="green"
          label={t('kpiOrders')} value={Array.isArray(orders) ? orders.length : 0} unit={t('kpiOrdersUnit')} />
        <MetricCard icon={<Target size={20} />} color="blue"
          label={t('kpiOpps')} value={funnel.slice(0, 4).reduce((s, f) => s + f.count, 0)} unit={t('kpiOppsUnit')} />
        <MetricCard icon={<TrendingUp size={20} />} color="indigo"
          label={t('kpiWinRate')} value={`${winRate}%`} unit="" />
        <MetricCard icon={<Clock size={20} />} color={pendingTasks > 0 ? 'orange' : 'gray'}
          label={t('kpiTasks')} value={pendingTasks} unit={t('kpiTasksUnit')} />
      </div>

      {/* 銷售趨勢 + 商機漏斗 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-xl border p-5">
          <h2 className="text-sm font-semibold text-gray-600 mb-4">{t('salesTrend')}</h2>
          {dailyTrend.length > 0 ? (
            <ResponsiveContainer width="100%" height={180}>
              <LineChart data={dailyTrend}>
                <XAxis dataKey="date" tick={{ fontSize: 10 }} />
                <YAxis tick={{ fontSize: 10 }} />
                <Tooltip formatter={(v: any) => [`NT$${v}K`, t('salesTrendTooltip')]} />
                <Line type="monotone" dataKey="total" stroke="#22c55e" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-44 flex items-center justify-center text-gray-300 text-sm">{t('salesTrendNoData')}</div>
          )}
        </div>

        <div className="bg-white rounded-xl border p-5">
          <h2 className="text-sm font-semibold text-gray-600 mb-4">{t('oppFunnel')}</h2>
          {funnel.some(f => f.count > 0) ? (
            <ResponsiveContainer width="100%" height={180}>
              <BarChart data={funnel} layout="vertical">
                <XAxis type="number" tick={{ fontSize: 10 }} />
                <YAxis dataKey="stage" type="category" tick={{ fontSize: 10 }} width={60} />
                <Tooltip formatter={(v: any) => [v, t('oppFunnelTooltip')]} />
                <Bar dataKey="count" fill="#6366f1" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-44 flex items-center justify-center text-gray-300 text-sm">{t('oppFunnelNoData')}</div>
          )}
        </div>
      </div>

      {/* 訂單狀態分布 + 近期商機 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-xl border p-5">
          <h2 className="text-sm font-semibold text-gray-600 mb-4">{t('orderStatus')}</h2>
          {Object.keys(statusCount).length === 0 ? (
            <p className="text-sm text-gray-400 text-center py-8">{t('orderStatusNoData')}</p>
          ) : (
            <div className="space-y-2">
              {Object.entries(statusCount).map(([status, count]) => (
                <div key={status} className="flex items-center gap-3">
                  <span className="text-xs text-gray-500 w-20 flex-shrink-0">{status}</span>
                  <div className="flex-1 bg-gray-100 rounded-full h-2">
                    <div className="h-2 rounded-full bg-green-500"
                      style={{ width: `${Math.min(100, (count / (Array.isArray(orders) ? orders.length : 1)) * 100)}%` }} />
                  </div>
                  <span className="text-xs font-bold text-gray-700 w-6 text-right">{count}</span>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="bg-white rounded-xl border p-5">
          <h2 className="text-sm font-semibold text-gray-600 mb-4">{t('recentOpps')}</h2>
          {(Array.isArray(opps) ? opps : []).length === 0 ? (
            <p className="text-sm text-gray-400 text-center py-8">{t('recentOppsNoData')}</p>
          ) : (
            <div className="space-y-2">
              {(Array.isArray(opps) ? opps : []).slice(0, 5).map((o: any) => (
                <div key={o.id} className="flex items-center justify-between py-2 border-b last:border-0">
                  <div>
                    <p className="text-sm font-medium text-gray-800 truncate max-w-[200px]">{o.opportunity_name || o.title}</p>
                    <p className="text-xs text-gray-400">{o.customer_name || '—'}</p>
                  </div>
                  <div className="flex items-center gap-2">
                    {o.expected_value_twd && (
                      <span className="text-xs font-bold text-green-700">NT${Math.round(o.expected_value_twd / 1000)}K</span>
                    )}
                    <span className={clsx('px-2 py-0.5 rounded text-xs font-medium', STAGE_COLORS[o.stage] || 'bg-gray-100 text-gray-600')}>
                      {t(`stage.${o.stage}` as any, { defaultValue: o.stage })}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function MetricCard({ icon, color, label, value, unit }: {
  icon: React.ReactNode; color: string; label: string; value: any; unit: string;
}) {
  const colors: Record<string, string> = {
    green: 'bg-green-50 text-green-600', blue: 'bg-blue-50 text-blue-600',
    indigo: 'bg-indigo-50 text-indigo-600', orange: 'bg-orange-50 text-orange-600',
    gray: 'bg-gray-50 text-gray-400',
  };
  return (
    <div className="bg-white rounded-xl border p-4">
      <div className={`w-9 h-9 rounded-lg flex items-center justify-center mb-3 ${colors[color]}`}>{icon}</div>
      <p className="text-2xl font-bold text-gray-900">{value}<span className="text-sm font-normal text-gray-400 ml-1">{unit}</span></p>
      <p className="text-xs font-medium text-gray-600 mt-0.5">{label}</p>
    </div>
  );
}
