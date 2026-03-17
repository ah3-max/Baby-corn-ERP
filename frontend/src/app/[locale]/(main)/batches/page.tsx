'use client';

/**
 * 批次管理列表頁 /batches
 * 功能：狀態 Tab 快篩、彩色左邊框、重量追蹤、快速推進狀態
 * 新增：批量選取 + 批量推進狀態操作
 */
import { useEffect, useState } from 'react';
import { useTranslations, useLocale } from 'next-intl';
import { useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { Plus, Package, Search, ChevronRight, ArrowRight, CheckSquare, Square, XCircle, Trash2 } from 'lucide-react';
import { batchesApi } from '@/lib/api';
import { useToast } from '@/contexts/ToastContext';
import { useUser } from '@/contexts/UserContext';
import type { Batch, BatchStatus } from '@/types';
import { BATCH_STATUS_NEXT } from '@/types';
import BatchDrawer from './BatchDrawer';

// 狀態對應樣式
const STATUS_STYLES: Record<BatchStatus, { border: string; badge: string }> = {
  processing:      { border: 'border-l-orange-400',  badge: 'bg-orange-100 text-orange-700' },
  qc_pending:      { border: 'border-l-yellow-400',  badge: 'bg-yellow-100 text-yellow-700' },
  qc_done:         { border: 'border-l-blue-400',    badge: 'bg-blue-100 text-blue-700' },
  packaging:       { border: 'border-l-purple-400',  badge: 'bg-purple-100 text-purple-700' },
  ready_to_export: { border: 'border-l-indigo-400',  badge: 'bg-indigo-100 text-indigo-700' },
  exported:        { border: 'border-l-cyan-400',    badge: 'bg-cyan-100 text-cyan-700' },
  in_transit_tw:   { border: 'border-l-teal-400',    badge: 'bg-teal-100 text-teal-700' },
  in_stock:        { border: 'border-l-green-400',   badge: 'bg-green-100 text-green-700' },
  sold:            { border: 'border-l-emerald-400', badge: 'bg-emerald-100 text-emerald-700' },
  closed:          { border: 'border-l-gray-300',    badge: 'bg-gray-100 text-gray-500' },
};

const TABS: Array<{ key: string; status?: BatchStatus }> = [
  { key: 'tabs.all' },
  { key: 'tabs.processing',      status: 'processing' },
  { key: 'tabs.qc_pending',      status: 'qc_pending' },
  { key: 'tabs.qc_done',         status: 'qc_done' },
  { key: 'tabs.packaging',       status: 'packaging' },
  { key: 'tabs.ready_to_export', status: 'ready_to_export' },
  { key: 'tabs.exported',        status: 'exported' },
  { key: 'tabs.in_transit_tw',   status: 'in_transit_tw' },
  { key: 'tabs.in_stock',        status: 'in_stock' },
  { key: 'tabs.sold',            status: 'sold' },
  { key: 'tabs.closed',          status: 'closed' },
];

export default function BatchesPage() {
  const t  = useTranslations('batches');
  const tc = useTranslations('common');
  const locale = useLocale();
  const searchParams = useSearchParams();
  const { showToast } = useToast();
  const { hasPermission } = useUser();
  const canCreate = hasPermission('batch', 'create');
  const canEdit   = hasPermission('batch', 'edit');
  const canDelete = hasPermission('batch', 'delete');

  const initStatus = searchParams.get('status') as BatchStatus | null;

  const [batches, setBatches]       = useState<Batch[]>([]);
  const [loading, setLoading]       = useState(true);
  const [activeTab, setActiveTab]   = useState<BatchStatus | undefined>(initStatus ?? undefined);
  const [keyword, setKeyword]       = useState('');
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [advancing, setAdvancing]   = useState<string | null>(null);

  // ─── 批量選取狀態 ───
  const [selected, setSelected]         = useState<Set<string>>(new Set());
  const [bulkLoading, setBulkLoading]   = useState(false);

  const fetchBatches = async (status?: BatchStatus, kw?: string) => {
    setLoading(true);
    try {
      const { data } = await batchesApi.list({ status, keyword: kw || undefined });
      setBatches(data);
      setSelected(new Set()); // 切換 tab 或搜尋後清空選取
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchBatches(activeTab); }, [activeTab]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    fetchBatches(activeTab, keyword);
  };

  // 單一批次推進
  const handleAdvance = async (batch: Batch) => {
    setAdvancing(batch.id);
    try {
      await batchesApi.advance(batch.id);
      showToast(t('advanceSuccess'), 'success');
      fetchBatches(activeTab, keyword);
    } catch (e: any) {
      showToast(e?.response?.data?.detail ?? tc('error'), 'error');
    } finally {
      setAdvancing(null);
    }
  };

  // ─── 批量選取操作 ───
  const toggleSelect = (id: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const toggleSelectAll = () => {
    if (selected.size === batches.length) {
      setSelected(new Set());
    } else {
      setSelected(new Set(batches.map((b) => b.id)));
    }
  };

  const clearSelection = () => setSelected(new Set());

  // 批量推進狀態
  const handleBulkAdvance = async () => {
    if (selected.size === 0) return;
    setBulkLoading(true);
    try {
      const { data } = await batchesApi.bulkAdvance(Array.from(selected));
      if (data.failed > 0) {
        // 部分失敗：顯示詳細訊息
        const failedItems = data.results.filter((r: any) => !r.success);
        const failMsg = failedItems.map((r: any) => `${r.batch_no}: ${r.error}`).join('\n');
        showToast(`${t('bulkAdvancePartial', { success: data.success, failed: data.failed })}`, 'warning');
        if (failMsg) console.warn('批量推進失敗項目：', failMsg);
      } else {
        showToast(t('bulkAdvanceSuccess', { count: data.success }), 'success');
      }
      fetchBatches(activeTab, keyword);
    } catch (e: any) {
      showToast(e?.response?.data?.detail ?? tc('error'), 'error');
    } finally {
      setBulkLoading(false);
    }
  };

  // 刪除批次
  const handleDelete = async (batch: Batch) => {
    const lateStatuses = ['exported', 'in_transit_tw', 'in_stock', 'sold', 'closed'];
    const isLate = lateStatuses.includes(batch.status);
    const msg = isLate
      ? `批次 ${batch.batch_no} 已進入「${batch.status}」狀態。確定要強制刪除此批次嗎？（此操作無法復原）`
      : `確定要刪除批次 ${batch.batch_no}？（此操作無法復原）`;
    if (!confirm(msg)) return;
    try {
      await batchesApi.delete(batch.id, isLate);
      showToast(`批次 ${batch.batch_no} 已刪除`, 'success');
      fetchBatches(activeTab, keyword);
    } catch (e: any) {
      showToast(e?.response?.data?.detail ?? tc('error'), 'error');
    }
  };

  // 判斷選中的批次是否都是同一狀態（批量推進才有意義）
  const selectedBatches = batches.filter((b) => selected.has(b.id));
  const canBulkAdvance = selectedBatches.length > 0 &&
    selectedBatches.every((b) => BATCH_STATUS_NEXT[b.status] !== undefined);

  return (
    <div>
      {/* 頁首 */}
      <div className="flex items-center justify-between mb-5">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">{t('title')}</h1>
          <p className="text-sm text-gray-500 mt-0.5">{tc('total', { count: batches.length })}</p>
        </div>
        {canCreate && (
          <button
            onClick={() => setDrawerOpen(true)}
            className="btn-primary flex items-center gap-2"
          >
            <Plus size={16} /> {t('addBatch')}
          </button>
        )}
      </div>

      {/* 狀態 Tab 快篩（橫向可捲動） */}
      <div className="flex gap-1 mb-5 bg-gray-100 p-1 rounded-lg overflow-x-auto">
        {TABS.map(({ key, status }) => (
          <button
            key={key}
            onClick={() => setActiveTab(status)}
            className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors whitespace-nowrap flex-shrink-0 ${
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
          <input
            value={keyword}
            onChange={(e) => setKeyword(e.target.value)}
            placeholder={t('searchPlaceholder')}
            className="input pl-9"
          />
        </div>
        <button type="submit" className="btn-secondary">{tc('search')}</button>
      </form>

      {/* 批次列表 */}
      {loading ? (
        <div className="text-center py-16 text-gray-400">{tc('loading')}</div>
      ) : batches.length === 0 ? (
        <div className="flex flex-col items-center py-20 text-gray-400">
          <Package size={40} className="mb-3 opacity-30" />
          <p>{tc('noData')}</p>
        </div>
      ) : (
        <>
          {/* 批量操作列：全選 + 批量推進 */}
          {canEdit && (
            <div className="flex items-center gap-3 mb-3 px-1">
              <button
                onClick={toggleSelectAll}
                className="flex items-center gap-1.5 text-xs text-gray-500 hover:text-gray-700"
              >
                {selected.size === batches.length
                  ? <CheckSquare size={14} className="text-primary-600" />
                  : <Square size={14} />}
                {selected.size === batches.length ? t('deselectAll') : t('selectAll')}
              </button>
              {selected.size > 0 && (
                <span className="text-xs text-gray-400">
                  {t('selectedCount', { count: selected.size })}
                </span>
              )}
            </div>
          )}

          <div className="space-y-3">
            {batches.map((batch) => {
              const style    = STATUS_STYLES[batch.status];
              const nextSt   = BATCH_STATUS_NEXT[batch.status];
              const isAdv    = advancing === batch.id;
              const isSelected = selected.has(batch.id);

              return (
                <div
                  key={batch.id}
                  className={`card border-l-4 ${style.border} p-0 overflow-hidden hover:shadow-md transition-shadow ${
                    isSelected ? 'ring-2 ring-primary-300 bg-primary-50/30' : ''
                  }`}
                >
                  <div className="flex items-center px-5 py-4 gap-4">
                    {/* 勾選框 */}
                    {canEdit && (
                      <button
                        onClick={() => toggleSelect(batch.id)}
                        className="flex-shrink-0 text-gray-400 hover:text-primary-600"
                      >
                        {isSelected
                          ? <CheckSquare size={18} className="text-primary-600" />
                          : <Square size={18} />}
                      </button>
                    )}

                    {/* 左側：批次編號 + 狀態 + 採購單 */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="font-mono text-sm font-semibold text-gray-700">
                          {batch.batch_no}
                        </span>
                        <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${style.badge}`}>
                          {t(`status.${batch.status}` as any)}
                        </span>
                        {batch.harvest_datetime && batch.freshness_status && (
                          <span className={`text-xs px-2 py-0.5 rounded-full font-semibold ${
                            batch.freshness_status === 'fresh'    ? 'bg-green-100 text-green-700' :
                            batch.freshness_status === 'warning'  ? 'bg-yellow-100 text-yellow-700' :
                            batch.freshness_status === 'critical' ? 'bg-red-100 text-red-700' :
                            'bg-gray-100 text-gray-500'
                          }`}>
                            第{batch.days_since_harvest}d · 剩{Math.max(0, batch.remaining_days ?? 0)}d
                          </span>
                        )}
                      </div>
                      <p className="text-base font-medium text-gray-800 truncate">
                        {batch.purchase_order?.supplier?.name ?? '—'}
                      </p>
                      <p className="text-xs text-gray-400 mt-0.5 font-mono">
                        {batch.purchase_order?.order_no ?? '—'}
                      </p>
                    </div>

                    {/* 中間：重量資訊 */}
                    <div className="hidden sm:flex gap-6 text-sm">
                      <div className="text-center">
                        <p className="text-xs text-gray-400 mb-0.5">{t('initialWeight')}</p>
                        <p className="font-semibold text-gray-700">
                          {Number(batch.initial_weight).toLocaleString()} kg
                        </p>
                      </div>
                      <div className="text-center">
                        <p className="text-xs text-gray-400 mb-0.5">{t('currentWeight')}</p>
                        <p className={`font-semibold ${
                          Number(batch.current_weight) < Number(batch.initial_weight)
                            ? 'text-orange-600'
                            : 'text-green-600'
                        }`}>
                          {Number(batch.current_weight).toLocaleString()} kg
                        </p>
                      </div>
                    </div>

                    {/* 右側：操作按鈕 */}
                    <div className="flex items-center gap-2 flex-shrink-0">
                      {canEdit && nextSt && (
                        <button
                          onClick={() => handleAdvance(batch)}
                          disabled={isAdv}
                          className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium bg-primary-50 text-primary-700 border border-primary-200 rounded-md hover:bg-primary-100 transition-colors disabled:opacity-50"
                        >
                          <ArrowRight size={13} />
                          {isAdv ? '...' : t(`nextStatus.${batch.status}` as any)}
                        </button>
                      )}
                      <Link
                        href={`/${locale}/batches/${batch.id}`}
                        className="flex items-center gap-1 px-3 py-1.5 text-xs font-medium bg-gray-50 text-gray-600 border border-gray-200 rounded-md hover:bg-gray-100 transition-colors"
                      >
                        {tc('edit')} <ChevronRight size={13} />
                      </Link>
                      {canDelete && (
                        <button
                          onClick={() => handleDelete(batch)}
                          className="flex items-center gap-1 px-2 py-1.5 text-xs font-medium bg-red-50 text-red-600 border border-red-200 rounded-md hover:bg-red-100 transition-colors"
                          title="刪除批次"
                        >
                          <Trash2 size={13} />
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </>
      )}

      {/* ─── 底部浮動批量操作列 ─── */}
      {selected.size > 0 && (
        <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-40 bg-white border border-gray-200 shadow-xl rounded-xl px-6 py-3 flex items-center gap-4">
          <span className="text-sm font-medium text-gray-700">
            {t('selectedCount', { count: selected.size })}
          </span>
          <div className="h-5 w-px bg-gray-200" />
          {canBulkAdvance && (
            <button
              onClick={handleBulkAdvance}
              disabled={bulkLoading}
              className="btn-primary text-sm flex items-center gap-1.5"
            >
              <ArrowRight size={14} />
              {bulkLoading ? '...' : t('bulkAdvance')}
            </button>
          )}
          <button
            onClick={clearSelection}
            className="text-gray-400 hover:text-gray-600"
          >
            <XCircle size={18} />
          </button>
        </div>
      )}

      {/* 新增 Drawer */}
      {drawerOpen && (
        <BatchDrawer
          onClose={(r) => {
            setDrawerOpen(false);
            if (r) fetchBatches(activeTab, keyword);
          }}
        />
      )}
    </div>
  );
}
