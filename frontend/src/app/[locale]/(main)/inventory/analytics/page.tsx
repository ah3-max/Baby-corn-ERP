'use client';

/**
 * 庫存智慧分析頁面
 */
import { useEffect, useState } from 'react';
import { useTranslations } from 'next-intl';
import { ShoppingCart } from 'lucide-react';
import { inventoryAnalyticsApi } from '@/lib/api';

export default function InventoryAnalyticsPage() {
  const t = useTranslations('inventoryAnalytics');
  const [aging, setAging] = useState<any>(null);
  const [turnover, setTurnover] = useState<any>(null);
  const [depletion, setDepletion] = useState<any>(null);
  const [reorder, setReorder] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      inventoryAnalyticsApi.aging(),
      inventoryAnalyticsApi.turnover(),
      inventoryAnalyticsApi.depletionForecast(),
      inventoryAnalyticsApi.reorderSuggestion(),
    ]).then(([a, tv, d, r]) => {
      setAging(a.data); setTurnover(tv.data); setDepletion(d.data); setReorder(r.data);
    }).catch(console.error).finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="text-center py-16 text-gray-400">{t('loading')}</div>;

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-800 mb-5">{t('title')}</h1>

      {/* 下單建議卡片 */}
      {reorder && reorder.should_reorder && (
        <div className={`card p-5 mb-6 border-l-4 ${reorder.urgency === 'immediate' ? 'border-red-500 bg-red-50' : 'border-orange-500 bg-orange-50'}`}>
          <div className="flex items-center gap-3">
            <ShoppingCart size={24} className={reorder.urgency === 'immediate' ? 'text-red-600' : 'text-orange-600'} />
            <div>
              <p className={`font-bold ${reorder.urgency === 'immediate' ? 'text-red-700' : 'text-orange-700'}`}>
                {reorder.urgency === 'immediate' ? t('reorderImmediate') : t('reorderSoon')}
              </p>
              <p className="text-sm text-gray-600 mt-1">
                {t('reorderDesc', {
                  days: reorder.days_of_stock,
                  leadTime: reorder.lead_time_days,
                  safetyDays: reorder.safety_stock_days,
                  qty: reorder.suggested_quantity_kg,
                })}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* KPI 卡片 */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <div className="card p-4">
          <p className="text-xs text-gray-500">{t('kpiStock')}</p>
          <p className="text-xl font-bold text-gray-800">{aging?.total_weight_kg?.toLocaleString()} kg</p>
          <p className="text-xs text-gray-400">{t('kpiStockSub', { lots: aging?.total_lots })}</p>
        </div>
        <div className="card p-4">
          <p className="text-xs text-gray-500">{t('kpiDailySales')}</p>
          <p className="text-xl font-bold text-gray-800">{reorder?.avg_daily_sales_kg} kg</p>
        </div>
        <div className="card p-4">
          <p className="text-xs text-gray-500">{t('kpiDaysOfStock')}</p>
          <p className={`text-xl font-bold ${(reorder?.days_of_stock || 999) <= 7 ? 'text-red-600' : (reorder?.days_of_stock || 999) <= 14 ? 'text-yellow-600' : 'text-green-600'}`}>
            {reorder?.days_of_stock} {t('kpiDaysUnit')}
          </p>
        </div>
        <div className="card p-4">
          <p className="text-xs text-gray-500">{t('kpiTurnover')}</p>
          <p className="text-xl font-bold text-gray-800">{turnover?.turnover_rate}x</p>
          <p className="text-xs text-gray-400">{t('kpiTurnoverSub', { days: turnover?.avg_days_on_hand })}</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* 庫齡分佈 */}
        <div className="card p-5">
          <h3 className="font-semibold text-gray-800 mb-4">{t('agingTitle')}</h3>
          {aging?.buckets && (
            <div className="space-y-3">
              {[
                { key: '0_7',     labelKey: 'age0_7',   color: 'green' },
                { key: '8_14',    labelKey: 'age8_14',  color: 'yellow' },
                { key: '15_21',   labelKey: 'age15_21', color: 'orange' },
                { key: '22_plus', labelKey: 'age22plus', color: 'red' },
              ].map(b => {
                const data = aging.buckets[b.key];
                const pct = aging.total_weight_kg > 0 ? (data.weight_kg / aging.total_weight_kg * 100) : 0;
                return (
                  <div key={b.key}>
                    <div className="flex justify-between text-sm mb-1">
                      <span className="text-gray-600">{t(b.labelKey as any)}</span>
                      <span className="text-gray-800 font-medium">
                        {t('agingUnit', { weight: data.weight_kg, count: data.count })}
                      </span>
                    </div>
                    <div className="bg-gray-100 rounded-full h-3">
                      <div className={`h-3 rounded-full bg-${b.color}-500`} style={{ width: `${Math.min(100, pct)}%` }} />
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* 耗盡預測 */}
        <div className="card p-5">
          <h3 className="font-semibold text-gray-800 mb-4">{t('depletionTitle')}</h3>
          <p className="text-sm text-gray-500 mb-3">
            {depletion?.total_depletion_date && (
              <strong className="text-gray-800">{t('depletionDate', { date: depletion.total_depletion_date })}</strong>
            )}
          </p>
          <div className="space-y-2 max-h-64 overflow-y-auto">
            {(depletion?.lots || []).slice(0, 10).map((lot: any) => (
              <div key={lot.lot_no} className="flex items-center justify-between py-2 border-b border-gray-50 last:border-0">
                <div>
                  <span className="font-mono text-sm text-gray-600">{lot.lot_no}</span>
                  <span className="text-xs text-gray-400 ml-2">{t('lotAge', { days: lot.age_days })}</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-sm text-gray-600">{lot.current_weight_kg} kg</span>
                  <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                    lot.urgency === 'critical' ? 'bg-red-100 text-red-700' :
                    lot.urgency === 'warning'  ? 'bg-yellow-100 text-yellow-700' : 'bg-green-100 text-green-700'
                  }`}>{t('lotDaysLeft', { days: lot.estimated_days_left })}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
