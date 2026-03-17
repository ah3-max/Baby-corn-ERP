'use client';

/**
 * 銷售訂單詳情頁 /sales/[id]
 * - 狀態時間軸
 * - 推進狀態按鈕
 * - 訂單項目明細
 * - 編輯 Drawer
 */
import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import { useTranslations, useLocale } from 'next-intl';
import Link from 'next/link';
import {
  ChevronLeft, ArrowRight, Check,
  ShoppingCart, User, Calendar, FileText, Package,
  Pencil
} from 'lucide-react';
import { salesApi } from '@/lib/api';
import { useToast } from '@/contexts/ToastContext';
import { useUser } from '@/contexts/UserContext';
import type { SalesOrder, SalesStatus } from '@/types';
import { SALES_STATUS_NEXT } from '@/types';
import SalesDrawer from '../SalesDrawer';

const SALES_STATUSES: SalesStatus[] = ['draft', 'confirmed', 'delivered', 'invoiced', 'closed'];

const STATUS_COLORS: Record<SalesStatus, { badge: string; dot: string }> = {
  draft:     { badge: 'bg-gray-100 text-gray-600',     dot: 'bg-gray-400' },
  confirmed: { badge: 'bg-blue-100 text-blue-700',     dot: 'bg-blue-400' },
  delivered: { badge: 'bg-purple-100 text-purple-700', dot: 'bg-purple-400' },
  invoiced:  { badge: 'bg-orange-100 text-orange-700', dot: 'bg-orange-400' },
  closed:    { badge: 'bg-green-100 text-green-700',   dot: 'bg-green-400' },
};

export default function SalesDetailPage() {
  const params = useParams();
  const locale = useLocale();
  const t  = useTranslations('sales');
  const tc = useTranslations('common');
  const { showToast } = useToast();
  const { hasPermission } = useUser();
  const canEdit = hasPermission('sales', 'edit');

  const [order, setOrder]       = useState<SalesOrder | null>(null);
  const [loading, setLoading]   = useState(true);
  const [advancing, setAdvancing] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(false);

  const fetchOrder = async () => {
    try {
      const { data } = await salesApi.get(params.id as string);
      setOrder(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchOrder(); }, []);

  const handleAdvance = async () => {
    if (!order) return;
    setAdvancing(true);
    try {
      await salesApi.advance(order.id);
      const nextSt = SALES_STATUS_NEXT[order.status];
      if (nextSt === 'delivered') {
        showToast('訂單已出貨，庫存已依 FIFO 自動扣減', 'success');
      } else {
        showToast(t('advanceSuccess'), 'success');
      }
      fetchOrder();
    } catch (e: any) {
      showToast(e?.response?.data?.detail ?? tc('error'), 'error');
    } finally {
      setAdvancing(false);
    }
  };

  if (loading) return <div className="text-center py-16 text-gray-400">{tc('loading')}</div>;
  if (!order)  return <div className="text-center py-16 text-gray-400">{tc('noData')}</div>;

  const currentIdx = SALES_STATUSES.indexOf(order.status);
  const nextStatus = SALES_STATUS_NEXT[order.status];
  const style      = STATUS_COLORS[order.status];

  return (
    <div className="max-w-3xl">
      {/* 頁首導覽 */}
      <div className="flex items-center gap-3 mb-6">
        <Link
          href={`/${locale}/sales`}
          className="flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-700 transition-colors"
        >
          <ChevronLeft size={16} />
          {t('title')}
        </Link>
        <span className="text-gray-300">/</span>
        <span className="text-sm font-mono text-gray-700 font-semibold">{order.order_no}</span>
      </div>

      {/* ── 標題卡 ── */}
      <div className="card p-6 mb-5">
        <div className="flex items-start justify-between">
          <div>
            <div className="flex items-center gap-3 mb-1">
              <h1 className="text-2xl font-bold text-gray-900 font-mono">{order.order_no}</h1>
              <span className={`px-3 py-1 rounded-full text-sm font-medium ${style.badge}`}>
                {t(`status.${order.status}` as any)}
              </span>
            </div>
            <p className="text-sm text-gray-400">
              {tc('createdAt')}：{new Date(order.created_at).toLocaleDateString()}
            </p>
          </div>

          <div className="flex items-center gap-2">
            {/* 推進狀態 */}
            {canEdit && nextStatus && (
              <button
                onClick={handleAdvance}
                disabled={advancing}
                className="btn-primary flex items-center gap-2"
              >
                <ArrowRight size={15} />
                {advancing ? '...' : t(`nextStatus.${order.status}` as any)}
              </button>
            )}
            {/* 編輯按鈕 */}
            {canEdit && order.status !== 'closed' && (
              <button
                onClick={() => setDrawerOpen(true)}
                className="btn-secondary flex items-center gap-1.5"
              >
                <Pencil size={14} />
                {tc('edit')}
              </button>
            )}
          </div>
        </div>
      </div>

      {/* ── 狀態時間軸 ── */}
      <div className="card p-6 mb-5">
        <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-4">
          狀態流程
        </h2>
        <div className="relative">
          <div className="absolute top-3 left-3 right-3 h-0.5 bg-gray-200" />
          <div
            className="absolute top-3 left-3 h-0.5 bg-primary-400 transition-all duration-500"
            style={{ width: `${(currentIdx / (SALES_STATUSES.length - 1)) * 100}%`, right: 'auto' }}
          />
          <div className="relative flex justify-between">
            {SALES_STATUSES.map((st, idx) => {
              const isDone    = idx < currentIdx;
              const isCurrent = idx === currentIdx;
              return (
                <div key={st} className="flex flex-col items-center gap-1.5">
                  <div className={`w-6 h-6 rounded-full border-2 flex items-center justify-center transition-all ${
                    isDone
                      ? 'bg-primary-500 border-primary-500'
                      : isCurrent
                      ? `${STATUS_COLORS[st as SalesStatus].dot} border-white ring-2 ring-offset-1 ring-primary-400`
                      : 'bg-white border-gray-300'
                  }`}>
                    {isDone    && <Check size={12} className="text-white" />}
                    {isCurrent && <div className="w-2 h-2 rounded-full bg-white" />}
                  </div>
                  <span className={`text-[10px] text-center max-w-[56px] leading-tight ${
                    isCurrent ? 'text-primary-600 font-semibold' :
                    isDone    ? 'text-gray-500' : 'text-gray-300'
                  }`}>
                    {t(`status.${st}` as any)}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* ── 基本資訊 ── */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5 mb-5">
        <div className="card p-5">
          <div className="flex items-center gap-2 mb-4">
            <User size={16} className="text-gray-400" />
            <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wider">
              {t('customer')}
            </h2>
          </div>
          <p className="text-base font-semibold text-gray-800">{order.customer?.name ?? '—'}</p>
        </div>

        <div className="card p-5">
          <div className="flex items-center gap-2 mb-4">
            <Calendar size={16} className="text-gray-400" />
            <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wider">
              {t('orderDate')}
            </h2>
          </div>
          <div className="space-y-1.5 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-400">{t('orderDate')}</span>
              <span className="font-medium text-gray-700">{order.order_date}</span>
            </div>
            {order.delivery_date && (
              <div className="flex justify-between">
                <span className="text-gray-400">{t('deliveryDate')}</span>
                <span className="font-medium text-gray-700">{order.delivery_date}</span>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* ── 訂單項目 ── */}
      <div className="card p-5 mb-5">
        <div className="flex items-center gap-2 mb-4">
          <Package size={16} className="text-gray-400" />
          <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wider">
            {t('items')}
          </h2>
          <span className="ml-auto text-xs text-gray-400">{order.items.length} 項</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100 text-xs text-gray-400 uppercase tracking-wider">
                <th className="text-left py-2 pr-4 font-semibold">{t('batch')}</th>
                <th className="text-right py-2 px-4 font-semibold">{t('quantityKg')}</th>
                <th className="text-right py-2 px-4 font-semibold">{t('unitPriceTWD')}</th>
                <th className="text-right py-2 pl-4 font-semibold">小計（TWD）</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {order.items.map((item) => (
                <tr key={item.id} className="hover:bg-gray-50 transition-colors">
                  <td className="py-3 pr-4">
                    {item.batch ? (
                      <Link
                        href={`/${locale}/batches/${item.batch_id}`}
                        className="font-mono text-primary-600 hover:underline font-medium"
                      >
                        {item.batch.batch_no}
                      </Link>
                    ) : (
                      <span className="text-gray-400">—</span>
                    )}
                    {item.note && (
                      <p className="text-xs text-gray-400 mt-0.5">{item.note}</p>
                    )}
                  </td>
                  <td className="py-3 px-4 text-right font-medium text-gray-700">
                    {Number(item.quantity_kg).toLocaleString()} kg
                  </td>
                  <td className="py-3 px-4 text-right text-gray-600">
                    NT$ {Number(item.unit_price_twd).toLocaleString()}
                  </td>
                  <td className="py-3 pl-4 text-right font-semibold text-gray-800">
                    NT$ {Number(item.total_amount_twd).toLocaleString()}
                  </td>
                </tr>
              ))}
            </tbody>
            <tfoot>
              <tr className="border-t-2 border-gray-200">
                <td colSpan={3} className="pt-3 pr-4 text-right font-semibold text-gray-600 text-sm">
                  {t('totalAmount')}
                </td>
                <td className="pt-3 pl-4 text-right font-bold text-lg text-primary-700">
                  NT$ {Number(order.total_amount_twd).toLocaleString()}
                </td>
              </tr>
            </tfoot>
          </table>
        </div>
      </div>

      {/* ── 備註 ── */}
      {order.note && (
        <div className="card p-5">
          <div className="flex items-center gap-2 mb-3">
            <FileText size={16} className="text-gray-400" />
            <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wider">
              {t('note')}
            </h2>
          </div>
          <p className="text-sm text-gray-600 whitespace-pre-wrap">{order.note}</p>
        </div>
      )}

      {/* 編輯 Drawer */}
      {drawerOpen && (
        <SalesDrawer
          order={order}
          onClose={(r) => {
            setDrawerOpen(false);
            if (r) fetchOrder();
          }}
        />
      )}
    </div>
  );
}
