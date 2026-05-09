'use client';

/**
 * P-06 零用金管理頁面（I-04/05）
 */
import { useState } from 'react';
import { useTranslations } from 'next-intl';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api';
import { Wallet, Plus, CheckCircle, Clock, XCircle } from 'lucide-react';
import { clsx } from 'clsx';

const STATUS_COLORS: Record<string, string> = {
  draft:    'bg-gray-100 text-gray-600',
  pending:  'bg-yellow-100 text-yellow-700',
  approved: 'bg-green-100 text-green-700',
  rejected: 'bg-red-100 text-red-700',
};

const STATUS_ICONS: Record<string, any> = {
  pending:  Clock,
  approved: CheckCircle,
  rejected: XCircle,
};

const CATEGORY_KEYS = [
  'office_supply', 'transportation', 'meal', 'postage',
  'petty_repair', 'entertainment', 'cleaning', 'bank_charge', 'other',
] as const;

export default function PettyCashPage() {
  const t = useTranslations('financePettyCash');
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({
    record_date: new Date().toISOString().split('T')[0],
    category: 'other',
    amount: '',
    description: '',
    vendor: '',
    has_receipt: true,
  });
  const qc = useQueryClient();

  const { data: fundsData } = useQuery({
    queryKey: ['petty-cash-funds'],
    queryFn: async () => {
      const res = await apiClient.get('/finance/petty-cash/funds');
      return res.data;
    },
  });

  const { data: recordsData, isLoading } = useQuery({
    queryKey: ['petty-cash-records'],
    queryFn: async () => {
      const res = await apiClient.get('/finance/petty-cash/records', { params: { limit: 50 } });
      return res.data;
    },
  });

  const addRecord = useMutation({
    mutationFn: (d: any) => apiClient.post('/finance/petty-cash/records', d),
    onSuccess: () => {
      setShowForm(false);
      qc.invalidateQueries({ queryKey: ['petty-cash-records'] });
      qc.invalidateQueries({ queryKey: ['petty-cash-funds'] });
    },
  });

  const funds = fundsData?.items || [];
  const records = recordsData?.items || [];

  return (
    <div className="p-6 space-y-6">
      {/* 頁頭 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <Wallet className="text-primary-600" size={24} />
            {t('title')}
          </h1>
          <p className="text-sm text-gray-500 mt-1">{t('subtitle')}</p>
        </div>
        <button
          onClick={() => setShowForm(!showForm)}
          className="flex items-center gap-1.5 px-4 py-2 bg-primary-600 text-white text-sm rounded-lg hover:bg-primary-700"
        >
          <Plus size={15} />
          {t('addBtn')}
        </button>
      </div>

      {/* 零用金基金概覽 */}
      {funds.length > 0 && (
        <div className="grid grid-cols-3 gap-4">
          {funds.map((fund: any) => (
            <div key={fund.id} className="bg-white rounded-xl border p-5">
              <p className="text-sm text-gray-500">{fund.fund_name}</p>
              <p className="text-2xl font-bold text-gray-900 mt-1">
                {fund.currency} {Number(fund.balance).toLocaleString()}
              </p>
              <div className="mt-2 h-1.5 bg-gray-100 rounded-full overflow-hidden">
                <div
                  className="h-full bg-primary-500 rounded-full"
                  style={{ width: `${Math.min(100, (fund.balance / fund.fund_limit) * 100)}%` }}
                />
              </div>
              <p className="text-xs text-gray-400 mt-1">
                {t('fundLimit', {
                  currency: fund.currency,
                  amount: Number(fund.fund_limit).toLocaleString(),
                  holder: fund.holder_name || t('fundHolder'),
                })}
              </p>
            </div>
          ))}
        </div>
      )}

      {/* 新增表單 */}
      {showForm && (
        <div className="bg-white rounded-xl border p-5 space-y-4">
          <h3 className="font-semibold text-gray-900">{t('formTitle')}</h3>
          <div className="grid grid-cols-3 gap-4 text-sm">
            <div>
              <label className="block text-gray-600 mb-1">{t('labelDate')}</label>
              <input
                type="date"
                value={form.record_date}
                onChange={e => setForm(p => ({ ...p, record_date: e.target.value }))}
                className="w-full border rounded-lg px-3 py-1.5 text-sm"
              />
            </div>
            <div>
              <label className="block text-gray-600 mb-1">{t('labelCategory')}</label>
              <select
                value={form.category}
                onChange={e => setForm(p => ({ ...p, category: e.target.value }))}
                className="w-full border rounded-lg px-3 py-1.5 text-sm"
              >
                {CATEGORY_KEYS.map(k => (
                  <option key={k} value={k}>{t(`category.${k}`)}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-gray-600 mb-1">{t('labelAmount')} <span className="text-red-500">*</span></label>
              <div className="flex gap-1">
                <input
                  type="number"
                  value={form.amount}
                  onChange={e => setForm(p => ({ ...p, amount: e.target.value }))}
                  className="flex-1 border rounded-lg px-3 py-1.5 text-sm"
                  placeholder="0"
                />
                <select
                  className="w-20 border rounded-lg px-2 py-1.5 text-sm"
                >
                  {['TWD', 'THB', 'USD'].map(c => <option key={c} value={c}>{c}</option>)}
                </select>
              </div>
            </div>
            <div>
              <label className="block text-gray-600 mb-1">{t('labelVendor')}</label>
              <input
                type="text"
                value={form.vendor}
                onChange={e => setForm(p => ({ ...p, vendor: e.target.value }))}
                className="w-full border rounded-lg px-3 py-1.5 text-sm"
              />
            </div>
            <div className="col-span-2">
              <label className="block text-gray-600 mb-1">{t('labelDesc')} <span className="text-red-500">*</span></label>
              <input
                type="text"
                value={form.description}
                onChange={e => setForm(p => ({ ...p, description: e.target.value }))}
                className="w-full border rounded-lg px-3 py-1.5 text-sm"
              />
            </div>
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="has_receipt"
                checked={form.has_receipt}
                onChange={e => setForm(p => ({ ...p, has_receipt: e.target.checked }))}
                className="w-4 h-4"
              />
              <label htmlFor="has_receipt" className="text-sm text-gray-700">{t('checkReceipt')}</label>
            </div>
          </div>
          <div className="flex gap-2 justify-end">
            <button onClick={() => setShowForm(false)} className="px-4 py-2 border rounded-lg text-sm">{t('cancelBtn')}</button>
            <button
              onClick={() => addRecord.mutate({ ...form, amount: Number(form.amount) })}
              disabled={!form.amount || !form.description}
              className="px-4 py-2 bg-primary-600 text-white rounded-lg text-sm hover:bg-primary-700 disabled:opacity-50"
            >
              {t('submitBtn')}
            </button>
          </div>
        </div>
      )}

      {/* 支出記錄表 */}
      <div className="bg-white rounded-xl border overflow-hidden">
        <div className="px-4 py-3 border-b bg-gray-50">
          <h2 className="font-semibold text-gray-900 text-sm">{t('tableTitle')}</h2>
        </div>
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
            <tr>
              <th className="px-4 py-2 text-left">{t('colNo')}</th>
              <th className="px-4 py-2 text-left">{t('colDate')}</th>
              <th className="px-4 py-2 text-left">{t('colCategory')}</th>
              <th className="px-4 py-2 text-left">{t('colDesc')}</th>
              <th className="px-4 py-2 text-right">{t('colAmount')}</th>
              <th className="px-4 py-2 text-left">{t('colStatus')}</th>
              <th className="px-4 py-2 text-left">{t('colReceipt')}</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {isLoading ? (
              <tr><td colSpan={7} className="px-4 py-8 text-center text-gray-400">{t('loading')}</td></tr>
            ) : records.length === 0 ? (
              <tr><td colSpan={7} className="px-4 py-8 text-center text-gray-400">{t('noData')}</td></tr>
            ) : records.map((r: any) => {
              const StatusIcon = STATUS_ICONS[r.status];
              return (
                <tr key={r.id} className="hover:bg-gray-50">
                  <td className="px-4 py-2.5 font-mono text-xs text-gray-500">{r.record_no}</td>
                  <td className="px-4 py-2.5 text-gray-600">{r.record_date}</td>
                  <td className="px-4 py-2.5 text-gray-700">
                    {t(`category.${r.category}` as any, { defaultValue: r.category })}
                  </td>
                  <td className="px-4 py-2.5 text-gray-900">{r.description}</td>
                  <td className="px-4 py-2.5 text-right font-mono text-gray-900">
                    {r.currency} {Number(r.amount).toLocaleString()}
                  </td>
                  <td className="px-4 py-2.5">
                    <span className={clsx('inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium',
                      STATUS_COLORS[r.status]
                    )}>
                      {StatusIcon && <StatusIcon size={11} />}
                      {t(`status.${r.status}` as any, { defaultValue: r.status })}
                    </span>
                  </td>
                  <td className="px-4 py-2.5 text-xs">
                    {r.has_receipt
                      ? <span className="text-green-600">{t('hasReceipt')}</span>
                      : <span className="text-red-400">{t('noReceipt')}</span>}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
