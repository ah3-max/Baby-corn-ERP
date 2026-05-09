'use client';

/**
 * P-07 退貨管理頁面（H-05）
 */
import { useState } from 'react';
import { useTranslations } from 'next-intl';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api';
import { RotateCcw, AlertTriangle, CheckCircle, Clock } from 'lucide-react';
import { clsx } from 'clsx';

const STATUS_COLORS: Record<string, string> = {
  requested:   'bg-gray-100 text-gray-600',
  approved:    'bg-blue-100 text-blue-700',
  in_transit:  'bg-yellow-100 text-yellow-700',
  received:    'bg-purple-100 text-purple-700',
  inspected:   'bg-indigo-100 text-indigo-700',
  settled:     'bg-green-100 text-green-700',
  rejected:    'bg-red-100 text-red-700',
};

const RESPONSIBILITY_COLORS: Record<string, string> = {
  supplier:  'bg-red-100 text-red-700',
  logistics: 'bg-orange-100 text-orange-700',
  ourselves: 'bg-blue-100 text-blue-700',
  customer:  'bg-purple-100 text-purple-700',
};

const STATUS_KEYS = ['requested', 'approved', 'in_transit', 'received', 'inspected', 'settled', 'rejected'] as const;
const RETURN_TYPE_KEYS = ['quality_issue', 'wrong_product', 'overstock'] as const;

export default function ReturnsPage() {
  const t = useTranslations('logisticsReturns');
  const [status, setStatus] = useState('');
  const [returnType, setReturnType] = useState('');

  const { data, isLoading } = useQuery({
    queryKey: ['return-orders', status, returnType],
    queryFn: async () => {
      const res = await apiClient.get('/logistics/returns', {
        params: {
          status: status || undefined,
          return_type: returnType || undefined,
          limit: 50,
        },
      });
      return res.data;
    },
  });

  const returns = data?.items || [];
  const total = data?.total || 0;

  const stats = {
    pending:  returns.filter((r: any) => ['requested', 'approved', 'in_transit', 'received', 'inspected'].includes(r.status)).length,
    settled:  returns.filter((r: any) => r.status === 'settled').length,
    rejected: returns.filter((r: any) => r.status === 'rejected').length,
  };

  return (
    <div className="p-6 space-y-6">
      {/* 頁頭 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <RotateCcw className="text-primary-600" size={24} />
            {t('title')}
          </h1>
          <p className="text-sm text-gray-500 mt-1">{t('subtitle', { total })}</p>
        </div>
      </div>

      {/* 統計卡片 */}
      <div className="grid grid-cols-3 gap-4">
        <div className="bg-white rounded-xl border p-5 flex items-center gap-4">
          <div className="w-10 h-10 rounded-lg bg-yellow-100 flex items-center justify-center">
            <Clock size={20} className="text-yellow-600" />
          </div>
          <div>
            <p className="text-2xl font-bold text-gray-900">{stats.pending}</p>
            <p className="text-sm text-gray-500">{t('statPending')}</p>
          </div>
        </div>
        <div className="bg-white rounded-xl border p-5 flex items-center gap-4">
          <div className="w-10 h-10 rounded-lg bg-green-100 flex items-center justify-center">
            <CheckCircle size={20} className="text-green-600" />
          </div>
          <div>
            <p className="text-2xl font-bold text-gray-900">{stats.settled}</p>
            <p className="text-sm text-gray-500">{t('statSettled')}</p>
          </div>
        </div>
        <div className="bg-white rounded-xl border p-5 flex items-center gap-4">
          <div className="w-10 h-10 rounded-lg bg-red-100 flex items-center justify-center">
            <AlertTriangle size={20} className="text-red-600" />
          </div>
          <div>
            <p className="text-2xl font-bold text-gray-900">{stats.rejected}</p>
            <p className="text-sm text-gray-500">{t('statRejected')}</p>
          </div>
        </div>
      </div>

      {/* 過濾 */}
      <div className="flex gap-3">
        <select value={status} onChange={e => setStatus(e.target.value)} className="border rounded-lg px-3 py-2 text-sm">
          <option value="">{t('filterAllStatus')}</option>
          {STATUS_KEYS.map(k => (
            <option key={k} value={k}>{t(`status.${k}`)}</option>
          ))}
        </select>
        <select value={returnType} onChange={e => setReturnType(e.target.value)} className="border rounded-lg px-3 py-2 text-sm">
          <option value="">{t('filterAllTypes')}</option>
          {RETURN_TYPE_KEYS.map(k => (
            <option key={k} value={k}>{t(`returnType.${k}`)}</option>
          ))}
        </select>
      </div>

      {/* 退貨列表 */}
      <div className="bg-white rounded-xl border overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
            <tr>
              <th className="px-4 py-3 text-left">{t('colReturnNo')}</th>
              <th className="px-4 py-3 text-left">{t('colCustomer')}</th>
              <th className="px-4 py-3 text-left">{t('colType')}</th>
              <th className="px-4 py-3 text-left">{t('colStatus')}</th>
              <th className="px-4 py-3 text-left">{t('colResponsibility')}</th>
              <th className="px-4 py-3 text-right">{t('colRefundAmount')}</th>
              <th className="px-4 py-3 text-left">{t('colRefundStatus')}</th>
              <th className="px-4 py-3 text-left">{t('colDate')}</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {isLoading ? (
              <tr><td colSpan={8} className="px-4 py-8 text-center text-gray-400">{t('loading')}</td></tr>
            ) : returns.length === 0 ? (
              <tr><td colSpan={8} className="px-4 py-8 text-center text-gray-400">{t('noData')}</td></tr>
            ) : (
              returns.map((r: any) => (
                <tr key={r.id} className="hover:bg-gray-50">
                  <td className="px-4 py-2.5 font-mono text-xs text-gray-700">{r.return_no}</td>
                  <td className="px-4 py-2.5 font-medium text-gray-900">{r.customer_name || '—'}</td>
                  <td className="px-4 py-2.5 text-gray-600">
                    {t(`returnType.${r.return_type}` as any, { defaultValue: r.return_type })}
                  </td>
                  <td className="px-4 py-2.5">
                    <span className={clsx('px-2 py-0.5 rounded text-xs font-medium', STATUS_COLORS[r.status])}>
                      {t(`status.${r.status}` as any, { defaultValue: r.status })}
                    </span>
                  </td>
                  <td className="px-4 py-2.5">
                    {r.responsibility && (
                      <span className={clsx('px-2 py-0.5 rounded text-xs font-medium', RESPONSIBILITY_COLORS[r.responsibility])}>
                        {t(`responsibility.${r.responsibility}` as any, { defaultValue: r.responsibility })}
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-2.5 text-right font-mono text-gray-900">
                    {r.refund_amount ? `$${Number(r.refund_amount).toLocaleString()}` : '—'}
                  </td>
                  <td className="px-4 py-2.5 text-xs">
                    {r.refund_status
                      ? <span className={r.refund_status === 'refunded' ? 'text-green-600' : r.refund_status === 'pending' ? 'text-yellow-600' : 'text-gray-400'}>
                          {t(`refundStatus.${r.refund_status}` as any, { defaultValue: r.refund_status })}
                        </span>
                      : '—'}
                  </td>
                  <td className="px-4 py-2.5 text-gray-500">
                    {r.created_at ? r.created_at.split('T')[0] : '—'}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
