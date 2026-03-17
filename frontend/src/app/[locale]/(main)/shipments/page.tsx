'use client';

/**
 * 出口物流列表頁 /shipments
 * UI重點：狀態 Tab 快篩、彩色徽章、推進狀態、連結詳情頁
 */
import { useEffect, useState } from 'react';
import { useTranslations } from 'next-intl';
import { useLocale } from 'next-intl';
import Link from 'next/link';
import { Plus, Ship, ChevronRight, ArrowRight, Trash2 } from 'lucide-react';
import { shipmentsApi } from '@/lib/api';
import { useToast } from '@/contexts/ToastContext';
import { useUser } from '@/contexts/UserContext';
import type { Shipment, ShipmentStatus } from '@/types';
import { SHIPMENT_STATUS_NEXT } from '@/types';
import ShipmentDrawer from './ShipmentDrawer';

const STATUS_STYLES: Record<ShipmentStatus, { badge: string; border: string }> = {
  preparing:   { badge: 'bg-yellow-100 text-yellow-700',  border: 'border-l-yellow-400' },
  customs_th:  { badge: 'bg-orange-100 text-orange-700',  border: 'border-l-orange-400' },
  in_transit:  { badge: 'bg-blue-100 text-blue-700',      border: 'border-l-blue-400' },
  customs_tw:  { badge: 'bg-purple-100 text-purple-700',  border: 'border-l-purple-400' },
  arrived_tw:  { badge: 'bg-green-100 text-green-700',    border: 'border-l-green-400' },
};

const TABS: Array<{ key: string; status?: ShipmentStatus }> = [
  { key: 'tabs.all' },
  { key: 'tabs.preparing',  status: 'preparing' },
  { key: 'tabs.customs_th', status: 'customs_th' },
  { key: 'tabs.in_transit', status: 'in_transit' },
  { key: 'tabs.customs_tw', status: 'customs_tw' },
  { key: 'tabs.arrived_tw', status: 'arrived_tw' },
];

export default function ShipmentsPage() {
  const t  = useTranslations('shipments');
  const tc = useTranslations('common');
  const locale = useLocale();
  const { showToast } = useToast();
  const { hasPermission } = useUser();
  const canCreate = hasPermission('shipment', 'create');
  const canEdit   = hasPermission('shipment', 'edit');
  // 是否有刪除出口單的權限
  const canDelete = hasPermission('shipment', 'delete');

  const [shipments, setShipments]   = useState<Shipment[]>([]);
  const [loading, setLoading]       = useState(true);
  const [activeTab, setActiveTab]   = useState<ShipmentStatus | undefined>(undefined);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [editItem, setEditItem]     = useState<Shipment | null>(null);
  const [advancing, setAdvancing]   = useState<string | null>(null);
  // 刪除中的出口單 ID（用於 disabled 狀態）
  const [deleting, setDeleting]     = useState<string | null>(null);

  const fetchShipments = async (status?: ShipmentStatus) => {
    setLoading(true);
    try {
      const { data } = await shipmentsApi.list(status ? { status } : undefined);
      setShipments(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchShipments(activeTab); }, [activeTab]);

  const handleAdvance = async (shipment: Shipment) => {
    setAdvancing(shipment.id);
    try {
      await shipmentsApi.advance(shipment.id);
      showToast(t('advanceSuccess'), 'success');
      fetchShipments(activeTab);
    } catch (e: any) {
      showToast(e?.response?.data?.detail ?? tc('error'), 'error');
    } finally {
      setAdvancing(null);
    }
  };

  // 刪除出口單：需確認後才執行，成功後重新載入列表
  const handleDelete = async (shipment: Shipment) => {
    if (!window.confirm(`確定要刪除出口單 ${shipment.shipment_no} 嗎？此操作無法復原。`)) return;
    setDeleting(shipment.id);
    try {
      await shipmentsApi.delete(shipment.id);
      showToast('出口單已刪除', 'success');
      fetchShipments(activeTab);
    } catch (e: any) {
      showToast(e?.response?.data?.detail ?? tc('error'), 'error');
    } finally {
      setDeleting(null);
    }
  };

  return (
    <div>
      {/* 頁首 */}
      <div className="flex items-center justify-between mb-5">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">{t('title')}</h1>
          <p className="text-sm text-gray-500 mt-0.5">{tc('total', { count: shipments.length })}</p>
        </div>
        {canCreate && (
          <button
            onClick={() => { setEditItem(null); setDrawerOpen(true); }}
            className="btn-primary flex items-center gap-2"
          >
            <Plus size={16} /> {t('addShipment')}
          </button>
        )}
      </div>

      {/* 狀態 Tab */}
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

      {/* 列表 */}
      {loading ? (
        <div className="text-center py-16 text-gray-400">{tc('loading')}</div>
      ) : shipments.length === 0 ? (
        <div className="flex flex-col items-center py-20 text-gray-400">
          <Ship size={40} className="mb-3 opacity-30" />
          <p>{tc('noData')}</p>
        </div>
      ) : (
        <div className="space-y-3">
          {shipments.map((sh) => {
            const style  = STATUS_STYLES[sh.status];
            const nextSt = SHIPMENT_STATUS_NEXT[sh.status];
            const isAdv  = advancing === sh.id;

            return (
              <div
                key={sh.id}
                className={`card border-l-4 ${style.border} p-0 overflow-hidden hover:shadow-md transition-shadow`}
              >
                <div className="flex items-center px-5 py-4 gap-4">
                  {/* 左側 */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="font-mono text-sm font-semibold text-gray-700">
                        {sh.shipment_no}
                      </span>
                      <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${style.badge}`}>
                        {t(`status.${sh.status}` as any)}
                      </span>
                    </div>
                    <div className="flex flex-wrap gap-3 text-xs text-gray-500">
                      <span>{t('exportDate')}: {sh.export_date}</span>
                      {sh.transport_mode === 'air' && (
                        <span className="text-sky-600 font-medium">✈️ 空運</span>
                      )}
                      {sh.transport_mode === 'sea' && (
                        <span className="text-blue-600 font-medium">🚢 海運</span>
                      )}
                      {sh.carrier && <span>{t('carrier')}: {sh.carrier}</span>}
                      {sh.bl_no && <span>B/L: {sh.bl_no}</span>}
                      {sh.awb_no && <span>AWB: {sh.awb_no}</span>}
                    </div>
                  </div>

                  {/* 中間 */}
                  <div className="hidden sm:flex gap-6 text-sm">
                    <div className="text-center">
                      <p className="text-xs text-gray-400 mb-0.5">{t('batchCount')}</p>
                      <p className="font-semibold text-gray-700">{sh.shipment_batches.length}</p>
                    </div>
                    {sh.total_weight != null && (
                      <div className="text-center">
                        <p className="text-xs text-gray-400 mb-0.5">{t('totalWeight')}</p>
                        <p className="font-semibold text-gray-700">
                          {Number(sh.total_weight).toLocaleString()} kg
                        </p>
                      </div>
                    )}
                  </div>

                  {/* 操作 */}
                  <div className="flex items-center gap-2 flex-shrink-0">
                    {canEdit && nextSt && (
                      <button
                        onClick={() => handleAdvance(sh)}
                        disabled={isAdv}
                        className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium bg-primary-50 text-primary-700 border border-primary-200 rounded-md hover:bg-primary-100 transition-colors disabled:opacity-50"
                      >
                        <ArrowRight size={13} />
                        {isAdv ? '...' : t(`nextStatus.${sh.status}` as any)}
                      </button>
                    )}
                    {/* 刪除按鈕：僅在備貨中（preparing）狀態且有刪除權限時顯示 */}
                    {canDelete && sh.status === 'preparing' && (
                      <button
                        onClick={() => handleDelete(sh)}
                        disabled={deleting === sh.id}
                        className="flex items-center gap-1 px-2 py-1.5 text-xs font-medium text-red-600 border border-red-200 rounded-md hover:bg-red-50 transition-colors disabled:opacity-50"
                      >
                        <Trash2 size={12} />
                        {deleting === sh.id ? '...' : '刪除'}
                      </button>
                    )}
                    <Link
                      href={`/${locale}/shipments/${sh.id}`}
                      className="flex items-center gap-1 px-3 py-1.5 text-xs font-medium bg-gray-50 text-gray-600 border border-gray-200 rounded-md hover:bg-gray-100 transition-colors"
                    >
                      {tc('edit')} <ChevronRight size={13} />
                    </Link>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Drawer */}
      {drawerOpen && (
        <ShipmentDrawer
          shipment={editItem}
          onClose={(r) => {
            setDrawerOpen(false);
            setEditItem(null);
            if (r) fetchShipments(activeTab);
          }}
        />
      )}
    </div>
  );
}
