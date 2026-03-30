'use client';

/**
 * 每日摘要頁面
 */
import { useEffect, useState } from 'react';
import { Bell, RefreshCw, Calendar, Package, Warehouse, DollarSign, Truck } from 'lucide-react';
import { dailySummaryApi } from '@/lib/api';
import { useToast } from '@/contexts/ToastContext';

export default function DailySummaryPage() {
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
      showToast('摘要已重新生成', 'success');
    } catch { showToast('生成失敗', 'error'); }
    finally { setGenerating(false); }
  };

  if (loading) return <div className="text-center py-16 text-gray-400">載入中...</div>;

  return (
    <div>
      <div className="flex items-center justify-between mb-5">
        <h1 className="text-2xl font-bold text-gray-800">每日摘要</h1>
        <button onClick={handleGenerate} disabled={generating}
          className="btn-secondary flex items-center gap-2">
          <RefreshCw size={14} className={generating ? 'animate-spin' : ''} />
          {generating ? '生成中...' : '重新生成'}
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
                <span className="text-xs text-gray-500">今日銷售</span>
              </div>
              <p className="text-xl font-bold text-gray-800">NT${Math.round(summary.sales_today?.total_twd || 0).toLocaleString()}</p>
              <p className="text-xs text-gray-400">{(summary.sales_today?.so_count || 0) + (summary.sales_today?.ds_count || 0)} 筆</p>
            </div>
            <div className="card p-4">
              <div className="flex items-center gap-2 mb-1">
                <Warehouse size={16} className="text-blue-500" />
                <span className="text-xs text-gray-500">在庫總量</span>
              </div>
              <p className="text-xl font-bold text-gray-800">{summary.inventory?.total_weight_kg?.toLocaleString()} kg</p>
              <p className="text-xs text-gray-400">{summary.inventory?.lot_count} 批次</p>
            </div>
            <div className="card p-4">
              <div className="flex items-center gap-2 mb-1">
                <Truck size={16} className="text-orange-500" />
                <span className="text-xs text-gray-500">出口中</span>
              </div>
              <p className="text-xl font-bold text-gray-800">{summary.pending_shipments}</p>
            </div>
            <div className="card p-4">
              <div className="flex items-center gap-2 mb-1">
                <Bell size={16} className="text-red-500" />
                <span className="text-xs text-gray-500">AR 逾期</span>
              </div>
              <p className="text-xl font-bold text-red-600">NT${Math.round(summary.ar_overdue_twd || 0).toLocaleString()}</p>
            </div>
          </div>

          {/* 庫齡分佈 */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
            <div className="card p-5">
              <h3 className="font-semibold text-gray-800 mb-3">庫存健康</h3>
              <div className="flex items-center gap-4">
                <div className="flex-1 text-center">
                  <p className="text-2xl font-bold text-green-600">{summary.inventory?.age_ok}</p>
                  <p className="text-xs text-gray-500">正常 (≤7天)</p>
                </div>
                <div className="flex-1 text-center">
                  <p className="text-2xl font-bold text-yellow-600">{summary.inventory?.age_warning}</p>
                  <p className="text-xs text-gray-500">注意 (8-14天)</p>
                </div>
                <div className="flex-1 text-center">
                  <p className="text-2xl font-bold text-red-600">{summary.inventory?.age_alert}</p>
                  <p className="text-xs text-gray-500">危險 (>14天)</p>
                </div>
              </div>
            </div>

            <div className="card p-5">
              <h3 className="font-semibold text-gray-800 mb-3">下單建議</h3>
              {summary.reorder?.should_reorder ? (
                <div className="bg-red-50 rounded-lg p-3 text-sm">
                  <p className="font-bold text-red-700">建議立即下單</p>
                  <p className="text-red-600 mt-1">庫存可供 {summary.reorder.days_of_stock} 天，日均出庫 {summary.reorder.avg_daily_sales_kg} kg</p>
                </div>
              ) : (
                <div className="bg-green-50 rounded-lg p-3 text-sm">
                  <p className="font-bold text-green-700">庫存充足</p>
                  <p className="text-green-600 mt-1">可供 {summary.reorder?.days_of_stock} 天</p>
                </div>
              )}
            </div>
          </div>

          {/* 鮮度告急 */}
          {summary.freshness_alerts?.length > 0 && (
            <div className="card p-5 mb-6 border-l-4 border-red-500">
              <h3 className="font-semibold text-red-700 mb-2">鮮度告急</h3>
              <div className="space-y-1">
                {summary.freshness_alerts.map((a: any) => (
                  <div key={a.lot_no} className="flex items-center justify-between text-sm">
                    <span className="font-mono text-gray-600">{a.lot_no}</span>
                    <span className="text-red-600">庫齡 {a.age_days} 天 · {a.weight_kg} kg</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* 批次狀態分佈 */}
          <div className="card p-5 mb-6">
            <h3 className="font-semibold text-gray-800 mb-3">批次狀態分佈</h3>
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
        <div className="text-center py-16 text-gray-400">尚無今日摘要，請點擊「重新生成」</div>
      )}

      {/* 歷史摘要 */}
      {history.length > 0 && (
        <div className="card p-5">
          <h3 className="font-semibold text-gray-800 mb-3">歷史摘要（近 14 天）</h3>
          <div className="space-y-2">
            {history.map((h: any) => (
              <div key={h.date} className="flex items-center justify-between py-2 border-b border-gray-50 last:border-0">
                <span className="text-sm font-medium text-gray-700">{h.date}</span>
                <div className="flex items-center gap-4 text-xs text-gray-500">
                  <span>銷售 NT${Math.round(h.data?.sales_today?.total_twd || 0).toLocaleString()}</span>
                  <span>庫存 {h.data?.inventory?.total_weight_kg || 0} kg</span>
                  <span>{h.data?.inventory?.lot_count || 0} 批次</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
