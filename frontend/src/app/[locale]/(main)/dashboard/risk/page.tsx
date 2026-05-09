'use client';

/**
 * O-03 風險儀表板
 */
import { useTranslations } from 'next-intl';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api';
import { ShieldAlert, AlertTriangle, TrendingDown, Clock, CloudRain, FileX, DollarSign } from 'lucide-react';
import { clsx } from 'clsx';

type RiskLevel = 'low' | 'medium' | 'high' | 'critical';

interface RiskItem {
  categoryKey: string;
  title: string;
  description: string;
  level: RiskLevel;
  value?: string;
}

const RISK_COLORS: Record<RiskLevel, string> = {
  low:      'bg-green-100 text-green-700 border-green-200',
  medium:   'bg-yellow-100 text-yellow-700 border-yellow-200',
  high:     'bg-orange-100 text-orange-700 border-orange-200',
  critical: 'bg-red-100 text-red-700 border-red-200',
};
const RISK_SCORE: Record<RiskLevel, number> = { low: 1, medium: 2, high: 3, critical: 4 };

export default function RiskDashboard() {
  const t = useTranslations('dashboardRisk');

  const { data: finData }      = useQuery({ queryKey: ['risk-finance'],   queryFn: async () => (await apiClient.get('/finance/summary')).data });
  const { data: invData }      = useQuery({ queryKey: ['risk-inventory'], queryFn: async () => (await apiClient.get('/inventory/summary')).data });
  const { data: batchData }    = useQuery({ queryKey: ['risk-batches'],   queryFn: async () => (await apiClient.get('/batches', { params: { limit: 100 } })).data });
  const { data: contractData } = useQuery({ queryKey: ['risk-contracts'], queryFn: async () => (await apiClient.get('/compliance/contracts', { params: { status: 'active', limit: 50 } })).data });
  const { data: certData }     = useQuery({ queryKey: ['risk-certs'],     queryFn: async () => (await apiClient.get('/trade-documents/certifications', { params: { expiring_days: 60, limit: 20 } })).data });
  const { data: weatherData }  = useQuery({ queryKey: ['risk-weather'],   queryFn: async () => (await apiClient.get('/market-intel/weather-alerts', { params: { is_active: true } })).data });
  const { data: churnData }    = useQuery({ queryKey: ['risk-churn'],     queryFn: async () => (await apiClient.get('/crm/alerts/churn', { params: { min_level: 'MEDIUM' } })).data });

  const arOverdue   = finData?.ar_overdue_twd ?? 0;
  const arTotal     = finData?.ar_total_twd ?? 1;
  const overdueRate = arTotal > 0 ? arOverdue / arTotal : 0;
  const batches     = batchData?.items ?? batchData ?? [];
  const critBatches = (Array.isArray(batches) ? batches : []).filter((b: any) => b.freshness_status === 'critical' || b.freshness_status === 'expired').length;
  const warnBatches = (Array.isArray(batches) ? batches : []).filter((b: any) => b.freshness_status === 'warning').length;
  const ageAlert    = invData?.age_alert ?? 0;
  const contracts   = contractData?.items ?? contractData ?? [];
  const expiringContracts = (Array.isArray(contracts) ? contracts : []).filter((c: any) => {
    if (!c.effective_to) return false;
    const days = Math.ceil((new Date(c.effective_to).getTime() - Date.now()) / 86400000);
    return days > 0 && days <= 30;
  }).length;
  const certs         = certData?.items ?? certData ?? [];
  const expiringCerts = (Array.isArray(certs) ? certs : []).length;
  const weatherAlerts = weatherData?.items ?? weatherData ?? [];
  const highWeather   = (Array.isArray(weatherAlerts) ? weatherAlerts : []).filter((w: any) => w.severity === 'high' || w.severity === 'extreme').length;
  const churnAlerts   = churnData?.items ?? churnData ?? [];
  const highChurn     = (Array.isArray(churnAlerts) ? churnAlerts : []).filter((c: any) => c.churn_level === 'HIGH' || c.churn_level === 'CRITICAL').length;

  const risks: RiskItem[] = [
    {
      categoryKey: 'finance',
      title: t('risk.arOverdueTitle'),
      description: t('risk.arOverdueDesc', { amount: Math.round(arOverdue / 1000), pct: Math.round(overdueRate * 100) }),
      level: overdueRate > 0.2 ? 'critical' : overdueRate > 0.1 ? 'high' : overdueRate > 0.05 ? 'medium' : 'low',
      value: `${Math.round(overdueRate * 100)}%`,
    },
    {
      categoryKey: 'supplyChain',
      title: t('risk.freshnessTitle'),
      description: t('risk.freshnessDesc', { crit: critBatches, warn: warnBatches }),
      level: critBatches > 3 ? 'critical' : critBatches > 0 ? 'high' : warnBatches > 5 ? 'medium' : 'low',
      value: t('risk.freshnessValue', { count: critBatches }),
    },
    {
      categoryKey: 'inventory',
      title: t('risk.ageTitle'),
      description: t('risk.ageDesc', { count: ageAlert }),
      level: ageAlert > 10 ? 'critical' : ageAlert > 5 ? 'high' : ageAlert > 0 ? 'medium' : 'low',
      value: t('risk.ageValue', { count: ageAlert }),
    },
    {
      categoryKey: 'compliance',
      title: t('risk.contractTitle'),
      description: t('risk.contractDesc', { count: expiringContracts }),
      level: expiringContracts > 3 ? 'high' : expiringContracts > 0 ? 'medium' : 'low',
      value: t('risk.contractValue', { count: expiringContracts }),
    },
    {
      categoryKey: 'compliance',
      title: t('risk.certTitle'),
      description: t('risk.certDesc', { count: expiringCerts }),
      level: expiringCerts > 3 ? 'high' : expiringCerts > 0 ? 'medium' : 'low',
      value: t('risk.certValue', { count: expiringCerts }),
    },
    {
      categoryKey: 'external',
      title: t('risk.weatherTitle'),
      description: (Array.isArray(weatherAlerts) ? weatherAlerts : []).length > 0
        ? t('risk.weatherDesc', { total: (Array.isArray(weatherAlerts) ? weatherAlerts : []).length, high: highWeather })
        : t('risk.weatherNoAlert'),
      level: highWeather > 0 ? 'high' : (Array.isArray(weatherAlerts) ? weatherAlerts : []).length > 0 ? 'medium' : 'low',
      value: t('risk.weatherValue', { count: (Array.isArray(weatherAlerts) ? weatherAlerts : []).length }),
    },
    {
      categoryKey: 'crm',
      title: t('risk.churnTitle'),
      description: t('risk.churnDesc', { total: (Array.isArray(churnAlerts) ? churnAlerts : []).length, high: highChurn }),
      level: highChurn > 3 ? 'critical' : highChurn > 0 ? 'high' : (Array.isArray(churnAlerts) ? churnAlerts : []).length > 0 ? 'medium' : 'low',
      value: t('risk.churnValue', { count: highChurn }),
    },
  ];

  risks.sort((a, b) => RISK_SCORE[b.level] - RISK_SCORE[a.level]);

  const maxScore   = risks.length * 4;
  const totalScore = risks.reduce((s, r) => s + RISK_SCORE[r.level], 0);
  const overallPct = Math.round((totalScore / maxScore) * 100);
  const overallLevel: RiskLevel = overallPct >= 70 ? 'critical' : overallPct >= 50 ? 'high' : overallPct >= 30 ? 'medium' : 'low';

  const levelCount = { critical: 0, high: 0, medium: 0, low: 0 };
  risks.forEach(r => levelCount[r.level]++);

  const CATEGORY_ICONS: Record<string, React.ReactNode> = {
    finance:     <DollarSign size={16} />,
    supplyChain: <AlertTriangle size={16} />,
    inventory:   <Clock size={16} />,
    compliance:  <FileX size={16} />,
    external:    <CloudRain size={16} />,
    crm:         <TrendingDown size={16} />,
  };

  return (
    <div className="p-6 space-y-6 max-w-7xl">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
          <ShieldAlert className="text-red-600" size={24} />
          {t('title')}
        </h1>
        <p className="text-sm text-gray-500 mt-1">{t('subtitle')}</p>
      </div>

      {/* 整體風險概覽 */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
        <div className={clsx('lg:col-span-1 rounded-xl border p-5 text-center', RISK_COLORS[overallLevel])}>
          <p className="text-xs font-medium opacity-70 mb-2">{t('overallLevel')}</p>
          <p className="text-4xl font-black">{overallPct}</p>
          <p className="text-xs mt-1 font-medium">{t(`level.${overallLevel}`)}</p>
          <div className="w-full bg-white/50 rounded-full h-2 mt-3">
            <div className="h-2 rounded-full bg-current opacity-60" style={{ width: `${overallPct}%` }} />
          </div>
        </div>
        <div className="lg:col-span-3 grid grid-cols-4 gap-3">
          {(['critical', 'high', 'medium', 'low'] as RiskLevel[]).map(l => (
            <div key={l} className={clsx('rounded-xl border p-4 text-center', RISK_COLORS[l])}>
              <p className="text-3xl font-bold">{levelCount[l]}</p>
              <p className="text-xs font-medium mt-1">{t(`level.${l}`)}</p>
            </div>
          ))}
        </div>
      </div>

      {/* 風險項目列表 */}
      <div className="bg-white rounded-xl border overflow-hidden">
        <div className="px-5 py-4 border-b">
          <h2 className="text-sm font-semibold text-gray-600">{t('riskDetail')}</h2>
        </div>
        <div className="divide-y divide-gray-100">
          {risks.map((r, i) => (
            <div key={i} className="px-5 py-4 flex items-center gap-4 hover:bg-gray-50">
              <div className={clsx('w-2 h-12 rounded-full flex-shrink-0',
                r.level === 'critical' ? 'bg-red-500' :
                r.level === 'high'     ? 'bg-orange-400' :
                r.level === 'medium'   ? 'bg-yellow-400' : 'bg-green-400'
              )} />
              <div className="w-8 text-gray-400 flex-shrink-0">{CATEGORY_ICONS[r.categoryKey]}</div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-0.5">
                  <span className="text-xs text-gray-400 font-medium">{t(`category.${r.categoryKey}`)}</span>
                  <h3 className="text-sm font-semibold text-gray-900">{r.title}</h3>
                </div>
                <p className="text-xs text-gray-500">{r.description}</p>
              </div>
              <div className="text-right flex-shrink-0">
                {r.value && <p className="text-sm font-bold text-gray-800">{r.value}</p>}
                <span className={clsx('px-2 py-0.5 rounded text-xs font-medium border', RISK_COLORS[r.level])}>
                  {t(`level.${r.level}`)}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* 風險熱圖 */}
      <div className="bg-white rounded-xl border p-5">
        <h2 className="text-sm font-semibold text-gray-600 mb-4">{t('heatmap')}</h2>
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="text-gray-400 uppercase">
                <th className="py-2 pr-4 text-left">{t('heatmapColCategory')}</th>
                {risks.map((r, i) => <th key={i} className="py-2 px-2 text-center whitespace-nowrap">{r.title.slice(0, 6)}</th>)}
              </tr>
            </thead>
            <tbody>
              {(['critical', 'high', 'medium', 'low'] as RiskLevel[]).map(level => (
                <tr key={level}>
                  <td className="py-1.5 pr-4 text-gray-500 font-medium whitespace-nowrap">{t(`level.${level}`)}</td>
                  {risks.map((r, i) => (
                    <td key={i} className="py-1.5 px-2 text-center">
                      {r.level === level ? (
                        <div className={clsx('w-6 h-6 rounded-full mx-auto flex items-center justify-center text-white text-xs',
                          level === 'critical' ? 'bg-red-500' :
                          level === 'high'     ? 'bg-orange-400' :
                          level === 'medium'   ? 'bg-yellow-400' : 'bg-green-400'
                        )}>●</div>
                      ) : <div className="w-6 h-6 mx-auto" />}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
