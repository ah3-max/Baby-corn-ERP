'use client';

/**
 * P-07 合約管理頁面（J-02/03/04）
 */
import { useState } from 'react';
import { useTranslations } from 'next-intl';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api';
import { FileCheck, AlertTriangle, Calendar } from 'lucide-react';
import { clsx } from 'clsx';

const STATUS_COLORS: Record<string, string> = {
  draft:      'bg-gray-100 text-gray-600',
  active:     'bg-green-100 text-green-700',
  expired:    'bg-red-100 text-red-700',
  terminated: 'bg-gray-100 text-gray-500',
  pending:    'bg-yellow-100 text-yellow-700',
};

const CONTRACT_TYPE_KEYS = ['sales', 'purchase', 'service', 'lease', 'nda', 'agency', 'other'] as const;
const STATUS_KEYS         = ['draft', 'active', 'expired', 'terminated', 'pending'] as const;

export default function ContractsPage() {
  const t = useTranslations('contracts');
  const [contractType, setContractType] = useState('');
  const [status, setStatus] = useState('active');

  const { data, isLoading } = useQuery({
    queryKey: ['contracts', contractType, status],
    queryFn: async () => {
      const res = await apiClient.get('/compliance/contracts', {
        params: {
          contract_type: contractType || undefined,
          status: status || undefined,
          limit: 50,
        },
      });
      return res.data;
    },
  });

  const contracts = data?.items || [];
  const today = new Date().toISOString().split('T')[0];

  const daysUntil = (dateStr: string) => {
    const diff = new Date(dateStr).getTime() - new Date(today).getTime();
    return Math.ceil(diff / 86400000);
  };

  const expiringCount = contracts.filter((c: any) =>
    c.effective_to && daysUntil(c.effective_to) > 0 && daysUntil(c.effective_to) <= 30
  ).length;

  return (
    <div className="p-6 space-y-6">
      {/* 頁頭 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <FileCheck className="text-primary-600" size={24} />
            {t('title')}
          </h1>
          <p className="text-sm text-gray-500 mt-1">
            {t('subtitle')}
            {expiringCount > 0 && (
              <span className="ml-2 text-orange-600 font-medium">
                {t('expiringAlert', { count: expiringCount })}
              </span>
            )}
          </p>
        </div>
      </div>

      {/* 過濾 */}
      <div className="flex gap-3">
        <select
          value={contractType}
          onChange={e => setContractType(e.target.value)}
          className="border rounded-lg px-3 py-2 text-sm"
        >
          <option value="">{t('allTypes')}</option>
          {CONTRACT_TYPE_KEYS.map(k => (
            <option key={k} value={k}>{t(`type.${k}`)}</option>
          ))}
        </select>
        <select
          value={status}
          onChange={e => setStatus(e.target.value)}
          className="border rounded-lg px-3 py-2 text-sm"
        >
          <option value="">{t('allStatuses')}</option>
          {STATUS_KEYS.map(k => (
            <option key={k} value={k}>{t(`status.${k}`)}</option>
          ))}
        </select>
      </div>

      {/* 合約列表 */}
      <div className="space-y-3">
        {isLoading ? (
          Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="bg-white rounded-xl border p-4 animate-pulse h-24" />
          ))
        ) : contracts.length === 0 ? (
          <div className="bg-white rounded-xl border p-8 text-center text-gray-400">{t('noData')}</div>
        ) : (
          contracts.map((c: any) => {
            const days = c.effective_to ? daysUntil(c.effective_to) : null;
            const isExpiringSoon = days !== null && days > 0 && days <= 30;
            const isExpired = days !== null && days <= 0 && c.status === 'active';

            return (
              <div key={c.id} className={clsx(
                'bg-white rounded-xl border p-4',
                isExpired ? 'border-red-200' : isExpiringSoon ? 'border-orange-200' : ''
              )}>
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <h3 className="font-semibold text-gray-900">{c.title || c.contract_no}</h3>
                      <span className={clsx('px-2 py-0.5 rounded text-xs font-medium', STATUS_COLORS[c.status])}>
                        {t(`status.${c.status}` as any, { defaultValue: c.status })}
                      </span>
                      {c.contract_type && (
                        <span className="px-2 py-0.5 bg-gray-100 text-gray-600 rounded text-xs">
                          {t(`type.${c.contract_type}` as any, { defaultValue: c.contract_type })}
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-4 text-xs text-gray-500">
                      {c.counterparty_name && <span>{t('counterparty', { name: c.counterparty_name })}</span>}
                      {c.total_value && (
                        <span className="text-primary-600 font-medium">
                          {c.currency || 'TWD'} {Number(c.total_value).toLocaleString()}
                        </span>
                      )}
                      {c.effective_from && (
                        <span className="flex items-center gap-1">
                          <Calendar size={11} />{c.effective_from}
                        </span>
                      )}
                    </div>
                  </div>
                  <div className="text-right ml-4 flex-shrink-0">
                    {c.effective_to && (
                      <>
                        <p className="text-sm text-gray-700 font-medium">{t('expireDate', { date: c.effective_to })}</p>
                        {isExpiringSoon && (
                          <p className="text-xs text-orange-600 flex items-center gap-1 justify-end">
                            <AlertTriangle size={11} />
                            {t('daysLeft', { days })}
                          </p>
                        )}
                        {isExpired && (
                          <p className="text-xs text-red-600 flex items-center gap-1 justify-end">
                            <AlertTriangle size={11} />
                            {t('overdue')}
                          </p>
                        )}
                        {!isExpiringSoon && !isExpired && days !== null && (
                          <p className="text-xs text-gray-400">{t('daysLeft', { days })}</p>
                        )}
                      </>
                    )}
                  </div>
                </div>
                {c.notes && (
                  <p className="text-xs text-gray-400 mt-2 truncate">{c.notes}</p>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
