'use client';

/**
 * 每日摘要頁面
 */
import { useEffect, useState } from 'react';
import { useTranslations } from 'next-intl';
import { Bell, RefreshCw, DollarSign, Truck, Warehouse } from 'lucide-react';
import { dailySummaryApi } from '@/lib/api';
import { useToast } from '@/contexts/ToastContext';

export default function DailySummaryPage() {
  const t = useTranslations('dailySummary');
  const { showToast } = useToast();
  const [summary, setSummary] = useState<any>(null);
  const [history, setHistory] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);

  useEffect(() => {
    Promise.all([
      dailySummaryApi.today(),
      dailySummaryApi.history(14),
    ]).then(([todayRes, histRes]) => {
      setSummary(todayRes.data);
      setHistory(histRes.data);
    }).catch(console.error).finally(() => setLoading(false));
  }, []);

  const handleGenerate = async () => {
    setGenerating(true);
    try {
      const { data } = await dailySummaryApi.generate();
      setSummary(data.data);
      showToast(t('generateSuccess'), 'success');
    } catch {
      showToast(t('generateError'), 'error');
    } finally {
      setGenerating(false);
    }
  };

  if (loading) return <div className="text-center py-16 text-gray-400">{t('loading')}</div>;

  return (
    <div>
      <div className="flex items-center justify-between mb-5">
        <h1 className="text-2xl font-bold text-gray-800">{t('title')}</h1>
        <button onClick={handleGenerate} disabled={generating}
          className="btn-secondary flex items-center gap-2">
          <RefreshCw size={14} className={generating ? 'animate-spin' : ''} />
          {generating ? t('generating') : t('regenerateBtn')}
        </button>
      </div>

      {summary ? (
        <>
          <p className="text-sm text-gray-500 mb-4">{summary.date}</p>

          {/* KPI 卡片 */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            <div className="card p-4">
              <div className="flex items-center gap-2 mb-1">
                <DollarSign size={16} className="text-green-500" />
                <span className="text-xs text-gray-500">{t('kpiSalesToday')}</span>
              </div>
              <p className="text-xl font-bold text-gray-800">NT${Math.round(summary.sales_today?.total_twd || 0).toLocaleString()}</p>
              <p className="text-xs text-gray-400">
                {t('kpiSalesCount', { count: (summary.sales_today?.so_count || 0) + (summary.sales_today?.ds_count || 0) })}
              </p>
            </div>
            <div className="card p-4">
              <div className="flex items-center gap-2 mb-1">
                <Warehouse size={16} className="text-blue-500" />
                <span className="text-xs text-gray-500">{t('kpiInventory')}</span>
              </div>
              <p className="text-xl font-bold text-gray-800">{summary.inventory?.total_weight_kg?.toLocaleString()} kg</p>
              <p className="text-xs text-gray-400">{t('kpiLotCount', { count: summary.inventory?.lot_count })}</p>
            </div>
            <div className="card p-4">
              <div className="flex items-center gap-2 mb-1">
                <Truck size={16} className="text-orange-500" />
                <span className="text-xs text-gray-500">{t('kpiInTransit')}</span>
              </div>
              <p className="text-xl font-bold text-gray-800">{summary.pending_shipments}</p>
            </div>
            <div className="card p-4">
              <div className="flex items-center gap-2 mb-1">
                <Bell size={16} className="text-red-500" />
                <span className="text-xs text-gray-500">{t('kpiArOverdue')}</span>
              </div>
              <p className="text-xl font-bold text-red-600">NT${Math.round(summary.ar_overdue_twd || 0).toLocaleString()}</p>
            </div>
          </div>

          {/* 庫齡分佈 */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
            <div className="card p-5">
              <h3 className="font-semibold text-gray-800 mb-3">{t('inventoryHealth')}</h3>
              <div className="flex items-center gap-4">
                <div className="flex-1 text-center">
                  <p className="text-2xl font-bold text-green-600">{summary.inventory?.age_ok}</p>
                  <p className="text-xs text-gray-500">{t('ageOk')}</p>
                </div>
                <div className="flex-1 text-center">
                  <p className="text-2xl font-bold text-yellow-600">{summary.inventory?.age_warning}</p>
                  <p className="text-xs text-gray-500">{t('ageWarning')}</p>
                </div>
                <div className="flex-1 text-center">
                  <p className="text-2xl font-bold text-red-600">{summary.inventory?.age_alert}</p>
                  <p className="text-xs text-gray-500">{t('ageAlert')}</p>
                </div>
              </div>
            </div>

            <div className="card p-5">
              <h3 className="font-semibold text-gray-800 mb-3">{t('reorderTitle')}</h3>
              {summary.reorder?.should_reorder ? (
                <div className="bg-red-50 rounded-lg p-3 text-sm">
                  <p className="font-bold text-red-700">{t('reorderNow')}</p>
                  <p className="text-red-600 mt-1">
                    {t('reorderNowDesc', { days: summary.reorder.days_of_stock, kg: summary.reorder.avg_daily_sales_kg })}
                  </p>
                </div>
              ) : (
                <div className="bg-green-50 rounded-lg p-3 text-sm">
                  <p className="font-bold text-green-700">{t('stockOk')}</p>
                  <p className="text-green-600 mt-1">{t('stockOkDesc', { days: summary.reorder?.days_of_stock })}</p>
                </div>
              )}
            </div>
          </div>

          {/* 鮮度告急 */}
          {summary.freshness_alerts?.length > 0 && (
            <div className="card p-5 mb-6 border-l-4 border-red-500">
              <h3 className="font-semibold text-red-700 mb-2">{t('freshnessAlert')}</h3>
              <div className="space-y-1">
                {summary.freshness_alerts.map((a: any) => (
                  <div key={a.lot_no} className="flex items-center justify-between text-sm">
                    <span className="font-mono text-gray-600">{a.lot_no}</span>
                    <span className="text-red-600">{t('freshnessDesc', { days: a.age_days, kg: a.weight_kg })}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* 批次狀態分佈 */}
          <div className="card p-5 mb-6">
            <h3 className="font-semibold text-gray-800 mb-3">{t('batchStatus')}</h3>
            <div className="flex flex-wrap gap-3">
              {summary.batches_by_status && Object.entries(summary.batches_by_status).map(([status, count]: [string, any]) => (
                <div key={status} className="bg-gray-50 rounded-lg px-3 py-2 text-center min-w-[80px]">
                  <p className="text-lg font-bold text-gray-800">{count}</p>
                  <p className="text-xs text-gray-500">{status}</p>
                </div>
              ))}
            </div>
          </div>
        </>
      ) : (
        <div className="text-center py-16 text-gray-400">{t('noSummary')}</div>
      )}

      {/* 歷史摘要 */}
      {history.length > 0 && (
        <div className="card p-5">
          <h3 className="font-semibold text-gray-800 mb-3">{t('historyTitle')}</h3>
          <div className="space-y-2">
            {history.map((h: any) => (
              <div key={h.date} className="flex items-center justify-between py-2 border-b border-gray-50 last:border-0">
                <span className="text-sm font-medium text-gray-700">{h.date}</span>
                <div className="flex items-center gap-4 text-xs text-gray-500">
                  <span>{t('historySales', { amount: Math.round(h.data?.sales_today?.total_twd || 0).toLocaleString() })}</span>
                  <span>{t('historyInventory', { kg: h.data?.inventory?.total_weight_kg || 0 })}</span>
                  <span>{t('historyLots', { count: h.data?.inventory?.lot_count || 0 })}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
