'use client';

/**
 * P-06 銀行帳戶管理頁面（I-06/07）
 */
import { useState } from 'react';
import { useTranslations } from 'next-intl';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api';
import { Building2, TrendingUp, TrendingDown, RefreshCw } from 'lucide-react';
import { clsx } from 'clsx';

export default function BankAccountsPage() {
  const t = useTranslations('financeBanks');
  const [selectedBank, setSelectedBank] = useState<string | null>(null);

  const { data: accountsData, isLoading: accountsLoading, refetch } = useQuery({
    queryKey: ['bank-accounts'],
    queryFn: async () => {
      const res = await apiClient.get('/finance/bank-accounts');
      return res.data;
    },
  });

  const { data: txData, isLoading: txLoading } = useQuery({
    queryKey: ['bank-transactions', selectedBank],
    queryFn: async () => {
      if (!selectedBank) return null;
      const res = await apiClient.get('/finance/bank-transactions', {
        params: { bank_account_id: selectedBank, limit: 30 },
      });
      return res.data;
    },
    enabled: !!selectedBank,
  });

  const accounts = accountsData?.items || [];
  const transactions = txData?.items || [];

  const totalTWD = accounts
    .filter((a: any) => a.currency === 'TWD')
    .reduce((s: number, a: any) => s + (a.current_balance || 0), 0);

  return (
    <div className="p-6 space-y-6">
      {/* 頁頭 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <Building2 className="text-primary-600" size={24} />
            {t('title')}
          </h1>
          <p className="text-sm text-gray-500 mt-1">{t('subtitle')}</p>
        </div>
        <button onClick={() => refetch()} className="flex items-center gap-2 px-4 py-2 text-sm bg-white border rounded-lg hover:bg-gray-50">
          <RefreshCw size={14} />
          {t('refreshBtn')}
        </button>
      </div>

      {/* 帳戶卡片 */}
      {accountsLoading ? (
        <div className="grid grid-cols-3 gap-4">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="bg-white rounded-xl border p-5 animate-pulse h-32" />
          ))}
        </div>
      ) : (
        <>
          {/* 合計卡 */}
          <div className="bg-gradient-to-r from-primary-600 to-primary-700 rounded-xl p-5 text-white">
            <p className="text-sm text-primary-200">{t('totalBalance')}</p>
            <p className="text-3xl font-bold mt-1">${totalTWD.toLocaleString()}</p>
            <p className="text-sm text-primary-200 mt-2">{t('accountCount', { count: accounts.length })}</p>
          </div>

          <div className="grid grid-cols-3 gap-4">
            {accounts.map((acc: any) => (
              <button
                key={acc.id}
                onClick={() => setSelectedBank(selectedBank === acc.id ? null : acc.id)}
                className={clsx(
                  'bg-white rounded-xl border p-5 text-left hover:shadow-md transition-shadow',
                  selectedBank === acc.id && 'ring-2 ring-primary-500'
                )}
              >
                <div className="flex items-start justify-between mb-3">
                  <div>
                    <p className="font-semibold text-gray-900">{acc.bank_name}</p>
                    <p className="text-xs text-gray-400 mt-0.5">
                      {acc.account_no?.replace(/(\d{4})(?=\d)/g, '$1-')}
                    </p>
                  </div>
                  <span className="px-2 py-0.5 bg-gray-100 text-gray-600 rounded text-xs">
                    {t(`acctType.${acc.account_type}` as any, { defaultValue: acc.account_type })}
                  </span>
                </div>
                <p className="text-2xl font-bold text-gray-900">
                  {acc.currency} {Number(acc.current_balance || 0).toLocaleString()}
                </p>
                {acc.credit_limit && (
                  <p className="text-xs text-gray-400 mt-1">
                    {t('creditLimit', { currency: acc.currency, amount: Number(acc.credit_limit).toLocaleString() })}
                  </p>
                )}
                {acc.swift_code && (
                  <p className="text-xs text-gray-400">SWIFT: {acc.swift_code}</p>
                )}
              </button>
            ))}
          </div>
        </>
      )}

      {/* 交易明細 */}
      {selectedBank && (
        <div className="bg-white rounded-xl border overflow-hidden">
          <div className="px-4 py-3 border-b bg-gray-50">
            <h2 className="font-semibold text-gray-900 text-sm">{t('txTitle')}</h2>
          </div>
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
              <tr>
                <th className="px-4 py-2 text-left">{t('colDate')}</th>
                <th className="px-4 py-2 text-left">{t('colDesc')}</th>
                <th className="px-4 py-2 text-left">{t('colType')}</th>
                <th className="px-4 py-2 text-right">{t('colAmount')}</th>
                <th className="px-4 py-2 text-right">{t('colBalance')}</th>
                <th className="px-4 py-2 text-left">{t('colReconcile')}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {txLoading ? (
                <tr><td colSpan={6} className="px-4 py-8 text-center text-gray-400">{t('txLoading')}</td></tr>
              ) : transactions.length === 0 ? (
                <tr><td colSpan={6} className="px-4 py-8 text-center text-gray-400">{t('txNoData')}</td></tr>
              ) : (
                transactions.map((tx: any) => (
                  <tr key={tx.id} className="hover:bg-gray-50">
                    <td className="px-4 py-2.5 text-gray-600">{tx.transaction_date}</td>
                    <td className="px-4 py-2.5 text-gray-900">{tx.description || '—'}</td>
                    <td className="px-4 py-2.5">
                      <span className={clsx('flex items-center gap-1 text-xs font-medium',
                        tx.direction === 'credit' ? 'text-green-600' : 'text-red-500'
                      )}>
                        {tx.direction === 'credit'
                          ? <TrendingUp size={12} />
                          : <TrendingDown size={12} />}
                        {tx.direction === 'credit' ? t('credit') : t('debit')}
                      </span>
                    </td>
                    <td className={clsx('px-4 py-2.5 text-right font-mono font-bold',
                      tx.direction === 'credit' ? 'text-green-600' : 'text-red-500'
                    )}>
                      {tx.direction === 'credit' ? '+' : '-'}
                      {Number(tx.amount).toLocaleString()}
                    </td>
                    <td className="px-4 py-2.5 text-right font-mono text-gray-700">
                      {tx.balance != null ? Number(tx.balance).toLocaleString() : '—'}
                    </td>
                    <td className="px-4 py-2.5">
                      <span className={clsx('text-xs',
                        tx.is_reconciled ? 'text-green-600' : 'text-gray-400'
                      )}>
                        {tx.is_reconciled ? t('reconciled') : t('unreconciled')}
                      </span>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
