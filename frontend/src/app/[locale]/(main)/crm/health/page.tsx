'use client';

/**
 * P-04 客戶健康分儀表板
 */
import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useTranslations } from 'next-intl';
import { apiClient } from '@/lib/api';
import {
  HeartPulse, AlertTriangle, TrendingDown, TrendingUp,
  Calendar, RefreshCw,
} from 'lucide-react';
import { clsx } from 'clsx';

type HealthLevel = 'GREEN' | 'YELLOW' | 'ORANGE' | 'RED';
type ChurnLevel  = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';

interface CustomerAlert {
  customer_id: string;
  customer_name: string;
  health_level?: HealthLevel;
  health_score?: number;
  churn_level?: ChurnLevel;
  churn_score?: number;
  predicted_next_order?: string;
  confidence?: string;
  days_until_next?: number;
}

const HEALTH_COLORS: Record<HealthLevel, string> = {
  GREEN:  'bg-green-100 text-green-800',
  YELLOW: 'bg-yellow-100 text-yellow-800',
  ORANGE: 'bg-orange-100 text-orange-800',
  RED:    'bg-red-100 text-red-800',
};

const CHURN_COLORS: Record<ChurnLevel, string> = {
  LOW:      'bg-blue-100 text-blue-800',
  MEDIUM:   'bg-yellow-100 text-yellow-800',
  HIGH:     'bg-orange-100 text-orange-800',
  CRITICAL: 'bg-red-100 text-red-800',
};

export default function CrmHealthPage() {
  const t  = useTranslations('crmHealth');
  const tc = useTranslations('common');
  const [activeTab, setActiveTab] = useState<'health' | 'churn' | 'reorder'>('health');

  const { data: healthData, isLoading: healthLoading, refetch: refetchHealth } = useQuery({
    queryKey: ['crm-health-alerts'],
    queryFn: async () => {
      const res = await apiClient.get('/crm/alerts/health-score', { params: { min_level: 'YELLOW' } });
      return res.data;
    },
  });

  const { data: churnData, isLoading: churnLoading } = useQuery({
    queryKey: ['crm-churn-alerts'],
    queryFn: async () => {
      const res = await apiClient.get('/crm/alerts/churn', { params: { min_level: 'MEDIUM' } });
      return res.data;
    },
  });

  const { data: reorderData, isLoading: reorderLoading } = useQuery({
    queryKey: ['crm-reorder-cycle'],
    queryFn: async () => {
      const res = await apiClient.get('/customers/reorder-cycle');
      return res.data;
    },
  });

  const healthAlerts: CustomerAlert[] = healthData?.items || [];
  const churnAlerts:  CustomerAlert[] = churnData?.items  || [];
  const reorderList:  CustomerAlert[] = reorderData        || [];

  const healthStats = {
    GREEN:  healthAlerts.filter(a => a.health_level === 'GREEN').length,
    YELLOW: healthAlerts.filter(a => a.health_level === 'YELLOW').length,
    ORANGE: healthAlerts.filter(a => a.health_level === 'ORANGE').length,
    RED:    healthAlerts.filter(a => a.health_level === 'RED').length,
  };

  return (
    <div className="p-6 space-y-6">
      {/* 頁頭 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <HeartPulse className="text-primary-600" size={24} />
            {t('title')}
          </h1>
          <p className="text-sm text-gray-500 mt-1">{t('subtitle')}</p>
        </div>
        <button
          onClick={() => refetchHealth()}
          className="flex items-center gap-2 px-4 py-2 text-sm bg-white border rounded-lg hover:bg-gray-50"
        >
          <RefreshCw size={14} />
          {t('refresh')}
        </button>
      </div>

      {/* 概覽卡片 */}
      <div className="grid grid-cols-4 gap-4">
        {(['GREEN', 'YELLOW', 'ORANGE', 'RED'] as HealthLevel[]).map((level) => {
          const icons = { GREEN: HeartPulse, YELLOW: AlertTriangle, ORANGE: TrendingDown, RED: AlertTriangle };
          const Icon = icons[level];
          return (
            <div key={level} className="bg-white rounded-xl border p-5 flex items-center gap-4">
              <div className={clsx(
                'w-12 h-12 rounded-xl flex items-center justify-center',
                level === 'GREEN'  ? 'bg-green-100'  :
                level === 'YELLOW' ? 'bg-yellow-100' :
                level === 'ORANGE' ? 'bg-orange-100' : 'bg-red-100'
              )}>
                <Icon size={22} className={
                  level === 'GREEN'  ? 'text-green-600'  :
                  level === 'YELLOW' ? 'text-yellow-600' :
                  level === 'ORANGE' ? 'text-orange-600' : 'text-red-600'
                } />
              </div>
              <div>
                <p className="text-2xl font-bold text-gray-900">{healthStats[level]}</p>
                <p className="text-sm text-gray-500">{t(`levels.${level}`)}</p>
              </div>
            </div>
          );
        })}
      </div>

      {/* 分頁標籤 */}
      <div className="border-b">
        <div className="flex gap-1">
          {([
            { id: 'health',  count: healthAlerts.length },
            { id: 'churn',   count: churnAlerts.length },
            { id: 'reorder', count: reorderList.length },
          ] as const).map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={clsx(
                'px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors',
                activeTab === tab.id
                  ? 'border-primary-500 text-primary-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              )}
            >
              {t(`tabs.${tab.id}`)}
              <span className="ml-1.5 bg-gray-100 text-gray-600 text-xs px-1.5 py-0.5 rounded-full">
                {tab.count}
              </span>
            </button>
          ))}
        </div>
      </div>

      {/* 健康告警列表 */}
      {activeTab === 'health' && (
        <div className="bg-white rounded-xl border overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
              <tr>
                <th className="px-4 py-3 text-left">{t('col.customerName')}</th>
                <th className="px-4 py-3 text-left">{t('col.healthLevel')}</th>
                <th className="px-4 py-3 text-right">{t('col.healthScore')}</th>
                <th className="px-4 py-3 text-left">{t('col.status')}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {healthLoading ? (
                <tr><td colSpan={4} className="px-4 py-8 text-center text-gray-400">{tc('loading')}</td></tr>
              ) : healthAlerts.length === 0 ? (
                <tr><td colSpan={4} className="px-4 py-8 text-center text-gray-400">{t('allGood')}</td></tr>
              ) : (
                healthAlerts.map(alert => (
                  <tr key={alert.customer_id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 font-medium text-gray-900">{alert.customer_name}</td>
                    <td className="px-4 py-3">
                      <span className={clsx('px-2 py-1 rounded-full text-xs font-medium',
                        HEALTH_COLORS[alert.health_level || 'GREEN']
                      )}>
                        {t(`levels.${alert.health_level || 'GREEN'}`)}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right font-mono text-gray-700">
                      {alert.health_score?.toFixed(1) ?? '-'}
                    </td>
                    <td className="px-4 py-3 text-gray-500 text-xs">{t('needFollowUp')}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* 流失風險列表 */}
      {activeTab === 'churn' && (
        <div className="bg-white rounded-xl border overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
              <tr>
                <th className="px-4 py-3 text-left">{t('col.customerName')}</th>
                <th className="px-4 py-3 text-left">{t('col.churnLevel')}</th>
                <th className="px-4 py-3 text-right">{t('col.churnScore')}</th>
                <th className="px-4 py-3 text-left">{t('col.suggestedAction')}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {churnLoading ? (
                <tr><td colSpan={4} className="px-4 py-8 text-center text-gray-400">{tc('loading')}</td></tr>
              ) : churnAlerts.length === 0 ? (
                <tr><td colSpan={4} className="px-4 py-8 text-center text-gray-400">{t('noHighRisk')}</td></tr>
              ) : (
                churnAlerts.map(alert => (
                  <tr key={alert.customer_id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 font-medium text-gray-900">{alert.customer_name}</td>
                    <td className="px-4 py-3">
                      <span className={clsx('px-2 py-1 rounded-full text-xs font-medium',
                        CHURN_COLORS[alert.churn_level || 'LOW']
                      )}>
                        {alert.churn_level}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right font-mono text-gray-700">
                      {alert.churn_score?.toFixed(1) ?? '-'}
                    </td>
                    <td className="px-4 py-3 text-gray-500 text-xs">{t('contactNow')}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* 訂單預測列表 */}
      {activeTab === 'reorder' && (
        <div className="bg-white rounded-xl border overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
              <tr>
                <th className="px-4 py-3 text-left">{t('col.customerName')}</th>
                <th className="px-4 py-3 text-left">{t('col.predictedOrder')}</th>
                <th className="px-4 py-3 text-right">{t('col.avgCycleDays')}</th>
                <th className="px-4 py-3 text-left">{t('col.trend')}</th>
                <th className="px-4 py-3 text-left">{t('col.confidence')}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {reorderLoading ? (
                <tr><td colSpan={5} className="px-4 py-8 text-center text-gray-400">{tc('loading')}</td></tr>
              ) : reorderList.length === 0 ? (
                <tr><td colSpan={5} className="px-4 py-8 text-center text-gray-400">{t('noPrediction')}</td></tr>
              ) : (
                reorderList.map((item: any) => (
                  <tr key={item.customer_id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 font-medium text-gray-900">{item.customer_name}</td>
                    <td className="px-4 py-3 flex items-center gap-1.5 text-gray-700">
                      <Calendar size={13} className="text-gray-400" />
                      {item.predicted_next_order || '—'}
                    </td>
                    <td className="px-4 py-3 text-right text-gray-700">
                      {item.avg_interval_days?.toFixed(1) ?? '—'}
                    </td>
                    <td className="px-4 py-3">
                      {item.order_trend === 'GROWING' ? (
                        <span className="flex items-center gap-1 text-green-600 text-xs">
                          <TrendingUp size={13} />{t('trend.GROWING')}
                        </span>
                      ) : item.order_trend === 'DECLINING' ? (
                        <span className="flex items-center gap-1 text-red-500 text-xs">
                          <TrendingDown size={13} />{t('trend.DECLINING')}
                        </span>
                      ) : (
                        <span className="text-gray-400 text-xs">{t('trend.STABLE')}</span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <span className={clsx('px-2 py-0.5 rounded text-xs font-medium',
                        item.confidence === 'HIGH'   ? 'bg-green-100 text-green-700' :
                        item.confidence === 'MEDIUM' ? 'bg-yellow-100 text-yellow-700' :
                        'bg-gray-100 text-gray-600'
                      )}>
                        {item.confidence}
                      </span>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
