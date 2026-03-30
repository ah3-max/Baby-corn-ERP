'use client';

/**
 * 採購管理列表頁
 * UI重點：狀態 Tab 快篩、彩色左邊框、逾期紅色警示、快速到廠確認
 */
import { useEffect, useState } from 'react';
import { useTranslations, useLocale } from 'next-intl';
import { useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { Plus, Truck, CheckCircle2, AlertCircle, Search, Package } from 'lucide-react';
import { purchasesApi, batchesApi } from '@/lib/api';
import { useToast } from '@/contexts/ToastContext';
import { useUser } from '@/contexts/UserContext';
import type { PurchaseOrder, PurchaseStatus } from '@/types';
import PurchaseDrawer from './PurchaseDrawer';
import ArrivalModal from './ArrivalModal';

// 狀態對應樣式（左邊框顏色 + Badge 顏色）
const STATUS_STYLES: Record<PurchaseStatus, { border: string; badge: string; label: string }> = {
  draft:      { border: 'border-l-gray-300',   badge: 'bg-gray-100 text-gray-600',    label: 'tabs.draft' },
  confirmed:  { border: 'border-l-blue-400',   badge: 'bg-blue-100 text-blue-700',    label: 'tabs.confirmed' },
  in_transit: { border: 'border-l-orange-400', badge: 'bg-orange-100 text-orange-700', label: 'tabs.in_transit' },
  arrived:    { border: 'border-l-green-400',  badge: 'bg-green-100 text-green-700',  label: 'tabs.arrived' },
  closed:     { border: 'border-l-purple-400', badge: 'bg-purple-100 text-purple-700', label: 'tabs.closed' },
};

const TABS: Array<{ key: string; status?: PurchaseStatus }> = [
  { key: 'tabs.all' },
  { key: 'tabs.draft',      status: 'draft' },
  { key: 'tabs.confirmed',  status: 'confirmed' },
  { key: 'tabs.in_transit', status: 'in_transit' },
  { key: 'tabs.arrived',    status: 'arrived' },
  { key: 'tabs.closed',     status: 'closed' },
];

export default function PurchasesPage() {
  const t      = useTranslations('purchases');
  const tc     = useTranslations('common');
  const locale = useLocale();
  const searchParams = useSearchParams();

  // 快取每張採購單對應的批次（key: po.id → batch[]）
  const [batchMap, setBatchMap] = useState<Record<string, { id: string; batch_no: string }[]>>({});
  const { showToast } = useToast();
  const { hasPermission } = useUser();
  const canCreate = hasPermission('purchase', 'create');
  const canEdit   = hasPermission('purchase', 'edit');

  const initStatus = searchParams.get('status') as PurchaseStatus | null;

  const [orders, setOrders]         = useState<PurchaseOrder[]>([]);
  const [loading, setLoading]       = useState(true);
  const [activeTab, setActiveTab]   = useState<PurchaseStatus | undefined>(initStatus ?? undefined);
  const [keyword, setKeyword]       = useState('');
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [editing, setEditing]       = useState<PurchaseOrder | null>(null);
  const [arriving, setArriving]     = useState<PurchaseOrder | null>(null);

  const fetchOrders = async (status?: PurchaseStatus, kw?: string) => {
    setLoading(true);
    try {
      const { data } = await purchasesApi.list({ status, keyword: kw || undefined });
      setOrders(data);
      // 同步查詢每張採購單的批次
      const results = await Promise.allSettled(
        data.map((po: PurchaseOrder) =>
          batchesApi.list({ purchase_order_id: po.id }).then((r) => ({ poId: po.id, batches: r.data }))
        )
      );
      const map: Record<string, { id: string; batch_no: string }[]> = {};
      results.forEach((r) => {
        if (r.status === 'fulfilled') map[r.value.poId] = r.value.batches;
      });
      setBatchMap(map);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchOrders(activeTab); }, [activeTab]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    fetchOrders(activeTab, keyword);
  };

  const isOverdue = (po: PurchaseOrder) =>
    po.expected_arrival &&
    new Date(po.expected_arrival) < new Date() &&
    !['arrived', 'closed'].includes(po.status);

  const refresh = () => fetchOrders(activeTab, keyword);

  return (
    <div>
      {/* 頁首 */}
      <div className="flex items-center justify-between mb-5">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">{t('title')}</h1>
          <p className="text-sm text-gray-500 mt-0.5">{tc('total', { count: orders.length })}</p>
        </div>
        {canCreate && (
          <button onClick={() => { setEditing(null); setDrawerOpen(true); }}
            className="btn-primary flex items-center gap-2">
            <Plus size={16} /> {t('addPurchase')}
          </button>
        )}
      </div>

      {/* 狀態 Tab 快篩 */}
      <div className="flex gap-1 mb-5 bg-gray-100 p-1 rounded-lg w-fit">
        {TABS.map(({ key, status }) => (
          <button
            key={key}
            onClick={() => setActiveTab(status)}
            className={`px-4 py-1.5 rounded-md text-sm font-medium transition-colors ${
              activeTab === status
                ? 'bg-white text-gray-800 shadow-sm'
                : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            {t(key as any)}
          </button>
        ))}
      </div>

      {/* 搜尋列 */}
      <form onSubmit={handleSearch} className="flex gap-2 mb-5">
        <div className="relative flex-1 max-w-sm">
          <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input value={keyword} onChange={(e) => setKeyword(e.target.value)}
            placeholder={t('searchSupplier')}
            className="input pl-9" />
        </div>
        <button type="submit" className="btn-secondary">{tc('search')}</button>
      </form>

      {/* 採購單列表 */}
      {loading ? (
        <div className="text-center py-16 text-gray-400">{tc('loading')}</div>
      ) : orders.length === 0 ? (
        <div className="flex flex-col items-center py-20 text-gray-400">
          <Truck size={40} className="mb-3 opacity-30" />
          <p>{tc('noData')}</p>
        </div>
      ) : (
        <div className="space-y-3">
          {orders.map((po) => {
            const style = STATUS_STYLES[po.status];
            const overdue = isOverdue(po);

            return (
              <div key={po.id}
                className={`card border-l-4 ${style.border} p-0 overflow-hidden hover:shadow-md transition-shadow`}>
                <div className="flex items-center px-5 py-4 gap-4">

                  {/* 左側：編號 + 供應商 */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="font-mono text-sm font-semibold text-gray-700">{po.order_no}</span>
                      <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${style.badge}`}>
                        {t(style.label as any)}
                      </span>
                      {overdue && (
                        <span className="flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-600">
                          <AlertCircle size={11} /> {t('overdue')}
                        </span>
                      )}
                    </div>
                    <p className="text-base font-medium text-gray-800 truncate">
                      {po.supplier?.name ?? '—'}
                      <span className="ml-2 text-xs text-gray-400">
                        {po.supplier?.supplier_type === 'farmer' ? `🌾 ${t('farmer')}` : `🏪 ${t('broker')}`}
                      </span>
                    </p>
                    {po.source_farmer && (
                      <p className="text-xs text-gray-400 mt-0.5">
                        {t('farmerSource')}：{po.source_farmer.name}
                      </p>
                    )}
                    {po.product_type && (
                      <span className="inline-block mt-1 px-2 py-0.5 rounded bg-indigo-50 text-indigo-600 text-xs font-medium">
                        {po.product_type.name_zh}
                      </span>
                    )}
                  </div>

                  {/* 中間：重量 + 金額 */}
                  <div className="hidden sm:flex gap-6 text-sm">
                    <div className="text-center">
                      <p className="text-xs text-gray-400 mb-0.5">單價</p>
                      <p className="font-semibold text-gray-700">฿{Number(po.unit_price).toLocaleString()}/kg</p>
                    </div>
                    <div className="text-center">
                      <p className="text-xs text-gray-400 mb-0.5">{tc('estimatedWeight')}</p>
                      <p className="font-semibold text-gray-700">{Number(po.estimated_weight).toLocaleString()} kg</p>
                    </div>
                    {po.received_weight && (
                      <div className="text-center">
                        <p className="text-xs text-gray-400 mb-0.5">{t('received')}</p>
                        <p className="font-semibold text-green-600">{Number(po.received_weight).toLocaleString()} kg</p>
                      </div>
                    )}
                    <div className="text-center">
                      <p className="text-xs text-gray-400 mb-0.5">{t('totalAmount')}</p>
                      <p className="font-semibold text-gray-700">฿{Number(po.total_amount).toLocaleString()}</p>
                    </div>
                    {po.defect_rate != null && (
                      <div className="text-center">
                        <p className="text-xs text-gray-400 mb-0.5">{t('defectRate')}</p>
                        <p className={`font-semibold ${Number(po.defect_rate) > 10 ? 'text-red-500' : 'text-gray-700'}`}>
                          {Number(po.defect_rate).toFixed(1)}%
                        </p>
                      </div>
                    )}
                  </div>

                  {/* 右側：日期 + 操作 */}
                  <div className="flex flex-col items-end gap-2 flex-shrink-0">
                    <p className={`text-xs ${overdue ? 'text-red-500 font-medium' : 'text-gray-400'}`}>
                      {po.expected_arrival
                        ? `${t('expectedArrival')} ${new Date(po.expected_arrival).toLocaleDateString()}`
                        : `${t('orderDate')} ${new Date(po.order_date).toLocaleDateString()}`
                      }
                    </p>
                    <div className="flex gap-2">
                      {/* 到廠確認按鈕（僅 draft/confirmed/in_transit 顯示） */}
                      {canEdit && !['arrived', 'closed'].includes(po.status) && (
                        <button
                          onClick={() => setArriving(po)}
                          className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium bg-green-50 text-green-700 border border-green-200 rounded-md hover:bg-green-100 transition-colors"
                        >
                          <CheckCircle2 size={13} /> {t('confirmArrival')}
                        </button>
                      )}
                      {/* 編輯按鈕 */}
                      {canEdit && !['arrived', 'closed'].includes(po.status) && (
                        <button
                          onClick={() => { setEditing(po); setDrawerOpen(true); }}
                          className="px-3 py-1.5 text-xs font-medium bg-gray-50 text-gray-600 border border-gray-200 rounded-md hover:bg-gray-100 transition-colors"
                        >
                          {tc('edit')}
                        </button>
                      )}
                    </div>
                  </div>
                </div>

                {/* 到廠後的詳細資訊欄（展開顯示） */}
                {po.status === 'arrived' && po.received_weight && (
                  <div className="px-5 py-3 bg-green-50 border-t border-green-100 flex gap-6 text-xs text-green-700">
                    <span>✅ {t('arrivalTime')}：{new Date(po.arrived_at!).toLocaleString()}</span>
                    <span>{t('received')}：{Number(po.received_weight).toLocaleString()} kg</span>
                    <span>{t('defect')}：{Number(po.defect_weight ?? 0).toLocaleString()} kg</span>
                    <span>{t('usable')}：{Number(po.usable_weight ?? 0).toLocaleString()} kg</span>
                    <span>{t('defectRate')}：{Number(po.defect_rate ?? 0).toFixed(1)}%</span>
                  </div>
                )}

                {/* 關聯批次列 */}
                {(batchMap[po.id] ?? []).length > 0 && (
                  <div className="px-5 py-2.5 bg-blue-50 border-t border-blue-100 flex items-center gap-2 flex-wrap">
                    <Package size={13} className="text-blue-400" />
                    <span className="text-xs text-blue-500 font-medium">{t('title') === 'Purchase Management' ? 'Batches' : '批次'}：</span>
                    {(batchMap[po.id] ?? []).map((b) => (
                      <Link
                        key={b.id}
                        href={`/${locale}/batches/${b.id}`}
                        className="font-mono text-xs font-semibold text-blue-600 hover:underline bg-white px-2 py-0.5 rounded border border-blue-200"
                      >
                        {b.batch_no}
                      </Link>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* 新增/編輯 Drawer */}
      {drawerOpen && (
        <PurchaseDrawer
          purchase={editing}
          onClose={(r) => { setDrawerOpen(false); setEditing(null); if (r) refresh(); }}
        />
      )}

      {/* 到廠確認 Modal */}
      {arriving && (
        <ArrivalModal
          purchase={arriving}
          onClose={(r) => { setArriving(null); if (r) refresh(); }}
        />
      )}
    </div>
  );
}
