'use client';

/**
 * P-05 報價核准頁面（F-07）
 */
import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useTranslations } from 'next-intl';
import { apiClient } from '@/lib/api';
import { FileText, CheckCircle, XCircle, Clock } from 'lucide-react';
import { clsx } from 'clsx';

const STATUS_COLORS: Record<string, string> = {
  pending:  'bg-yellow-100 text-yellow-700',
  approved: 'bg-green-100 text-green-700',
  rejected: 'bg-red-100 text-red-700',
};

export default function QuotationsApprovalPage() {
  const t  = useTranslations('crmQuotations');
  const tc = useTranslations('common');
  const [status, setStatus] = useState('pending');
  const qc = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ['quotation-approvals', status],
    queryFn: async () => {
      const res = await apiClient.get('/crm/quotation-approvals', {
        params: { status: status || undefined, limit: 50 },
      });
      return res.data;
    },
  });

  const decide = useMutation({
    mutationFn: ({ id, decision, comment }: { id: string; decision: 'approved' | 'rejected'; comment?: string }) =>
      apiClient.post(`/crm/quotation-approvals/${id}/decide`, { decision, comment }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['quotation-approvals'] }),
  });

  const approvals = data?.items || [];
  const pendingCount = approvals.filter((a: any) => a.status === 'pending').length;

  const FILTERS = [
    { key: 'pending',  label: t('filter.pending') },
    { key: 'approved', label: t('filter.approved') },
    { key: 'rejected', label: t('filter.rejected') },
    { key: '',         label: t('filter.all') },
  ];

  return (
    <div className="p-6 space-y-6">
      {/* 頁頭 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <FileText className="text-primary-600" size={24} />
            {t('title')}
          </h1>
          <p className="text-sm text-gray-500 mt-1">
            {t('subtitle')}
            {status === 'pending' && pendingCount > 0 && (
              <span className="ml-2 text-orange-600 font-medium">{t('pendingAlert', { count: pendingCount })}</span>
            )}
          </p>
        </div>
      </div>

      {/* 狀態過濾 */}
      <div className="flex gap-2">
        {FILTERS.map(f => (
          <button
            key={f.key}
            onClick={() => setStatus(f.key)}
            className={clsx('px-4 py-2 rounded-lg text-sm font-medium transition-colors',
              status === f.key
                ? 'bg-primary-600 text-white'
                : 'bg-white border text-gray-600 hover:bg-gray-50'
            )}
          >
            {f.label}
          </button>
        ))}
      </div>

      {/* 核准列表 */}
      <div className="bg-white rounded-xl border overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
            <tr>
              <th className="px-4 py-3 text-left">{t('col.quotation')}</th>
              <th className="px-4 py-3 text-left">{t('col.customer')}</th>
              <th className="px-4 py-3 text-left">{t('col.approvalLevel')}</th>
              <th className="px-4 py-3 text-left">{t('col.triggerReason')}</th>
              <th className="px-4 py-3 text-left">{t('col.status')}</th>
              <th className="px-4 py-3 text-left">{t('col.decidedAt')}</th>
              <th className="px-4 py-3 text-left">{t('col.actions')}</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {isLoading ? (
              <tr><td colSpan={7} className="px-4 py-8 text-center text-gray-400">{tc('loading')}</td></tr>
            ) : approvals.length === 0 ? (
              <tr><td colSpan={7} className="px-4 py-8 text-center text-gray-400">
                {status === 'pending' ? t('noPending') : t('noRecords')}
              </td></tr>
            ) : (
              approvals.map((a: any) => (
                <tr key={a.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3">
                    <p className="font-medium text-gray-900">{a.quotation_no || a.quotation_id}</p>
                    {a.total_amount && (
                      <p className="text-xs text-primary-600 font-medium">
                        ${Number(a.total_amount).toLocaleString()}
                      </p>
                    )}
                  </td>
                  <td className="px-4 py-3 text-gray-700">{a.customer_name || '—'}</td>
                  <td className="px-4 py-3">
                    <span className="px-2 py-0.5 bg-gray-100 text-gray-700 rounded text-xs font-medium">
                      Level {a.approval_level}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-xs text-gray-500 max-w-xs truncate">
                    {a.trigger_reason || '—'}
                  </td>
                  <td className="px-4 py-3">
                    <span className={clsx('inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium',
                      STATUS_COLORS[a.status]
                    )}>
                      {a.status === 'pending'  ? <Clock size={11} /> :
                       a.status === 'approved' ? <CheckCircle size={11} /> : <XCircle size={11} />}
                      {t(`status.${a.status}` as any)}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-xs text-gray-500">
                    {a.decided_at ? a.decided_at.split('T')[0] : '—'}
                  </td>
                  <td className="px-4 py-3">
                    {a.status === 'pending' && (
                      <div className="flex items-center gap-1">
                        <button
                          onClick={() => decide.mutate({ id: a.id, decision: 'approved' })}
                          className="flex items-center gap-1 px-2.5 py-1 bg-green-100 text-green-700 rounded text-xs hover:bg-green-200"
                        >
                          <CheckCircle size={12} />
                          {t('approve')}
                        </button>
                        <button
                          onClick={() => decide.mutate({ id: a.id, decision: 'rejected' })}
                          className="flex items-center gap-1 px-2.5 py-1 bg-red-100 text-red-700 rounded text-xs hover:bg-red-200"
                        >
                          <XCircle size={12} />
                          {t('reject')}
                        </button>
                      </div>
                    )}
                    {a.comment && (
                      <p className="text-xs text-gray-400 mt-1 truncate max-w-xs">{a.comment}</p>
                    )}
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
