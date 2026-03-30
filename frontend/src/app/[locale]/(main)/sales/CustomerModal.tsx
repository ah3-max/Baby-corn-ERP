'use client';

import { useState } from 'react';
import { useTranslations } from 'next-intl';
import { X, Users } from 'lucide-react';
import { customersApi } from '@/lib/api';
import { useToast } from '@/contexts/ToastContext';
import type { Customer } from '@/types';

interface Props {
  customer: Customer | null;
  onClose: (refresh?: boolean) => void;
}

export default function CustomerModal({ customer, onClose }: Props) {
  const t  = useTranslations('customers');
  const tc = useTranslations('common');
  const { showToast } = useToast();
  const isEdit = !!customer;

  const [form, setForm] = useState({
    name:          customer?.name          ?? '',
    contact_name:  customer?.contact_name  ?? '',
    phone:         customer?.phone         ?? '',
    email:         customer?.email         ?? '',
    region:        customer?.region        ?? '',
    address:       customer?.address       ?? '',
    payment_terms: customer?.payment_terms ?? '',
    note:          customer?.note          ?? '',
  });
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState('');

  const set = (key: string, val: string) => setForm((f) => ({ ...f, [key]: val }));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const payload = {
        name:          form.name,
        contact_name:  form.contact_name  || null,
        phone:         form.phone         || null,
        email:         form.email         || null,
        region:        form.region        || null,
        address:       form.address       || null,
        payment_terms: form.payment_terms || null,
        note:          form.note          || null,
      };
      if (isEdit) {
        await customersApi.update(customer.id, payload);
        showToast(t('updateSuccess'), 'success');
      } else {
        await customersApi.create(payload);
        showToast(t('createSuccess'), 'success');
      }
      onClose(true);
    } catch (err: any) {
      const msg = err?.response?.data?.detail ?? tc('error');
      setError(msg);
      showToast(msg, 'error');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/30" onClick={() => onClose()} />
      <div className="relative bg-white rounded-2xl shadow-2xl w-full max-w-md z-10 max-h-[90vh] flex flex-col">
        {/* 標題 */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <div className="flex items-center gap-2">
            <Users size={18} className="text-primary-600" />
            <h2 className="text-lg font-semibold text-gray-800">
              {isEdit ? t('editCustomer') : t('addCustomer')}
            </h2>
          </div>
          <button onClick={() => onClose()} className="text-gray-400 hover:text-gray-600">
            <X size={20} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="flex flex-col flex-1 min-h-0">
          <div className="flex-1 overflow-y-auto px-6 py-5 space-y-4">
            {/* 客戶名稱 */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                {t('name')} <span className="text-red-500">*</span>
              </label>
              <input type="text" value={form.name}
                onChange={(e) => set('name', e.target.value)}
                required className="input" />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  {t('contactName')}
                  <span className="ml-1 text-xs text-gray-400">{tc('optional')}</span>
                </label>
                <input type="text" value={form.contact_name}
                  onChange={(e) => set('contact_name', e.target.value)}
                  className="input" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  {t('phone')}
                  <span className="ml-1 text-xs text-gray-400">{tc('optional')}</span>
                </label>
                <input type="text" value={form.phone}
                  onChange={(e) => set('phone', e.target.value)}
                  className="input" />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                {t('email')}
                <span className="ml-1 text-xs text-gray-400">{tc('optional')}</span>
              </label>
              <input type="email" value={form.email}
                onChange={(e) => set('email', e.target.value)}
                className="input" />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  {t('region')}
                  <span className="ml-1 text-xs text-gray-400">{tc('optional')}</span>
                </label>
                <input type="text" value={form.region}
                  onChange={(e) => set('region', e.target.value)}
                  className="input" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  {t('paymentTerms')}
                  <span className="ml-1 text-xs text-gray-400">{tc('optional')}</span>
                </label>
                <input type="text" value={form.payment_terms}
                  onChange={(e) => set('payment_terms', e.target.value)}
                  className="input" placeholder="Net 30..." />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                {t('address')}
                <span className="ml-1 text-xs text-gray-400">{tc('optional')}</span>
              </label>
              <textarea value={form.address}
                onChange={(e) => set('address', e.target.value)}
                rows={2} className="input resize-none" />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t('note')}</label>
              <textarea value={form.note}
                onChange={(e) => set('note', e.target.value)}
                rows={2} className="input resize-none" />
            </div>

            {error && (
              <div className="bg-red-50 border border-red-200 text-red-600 text-sm px-4 py-2 rounded-md">
                {error}
              </div>
            )}
          </div>

          <div className="flex justify-end gap-3 px-6 py-4 border-t border-gray-200">
            <button type="button" onClick={() => onClose()} className="btn-secondary">
              {tc('cancel')}
            </button>
            <button type="submit" disabled={loading} className="btn-primary">
              {loading ? '...' : tc('save')}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
