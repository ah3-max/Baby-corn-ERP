'use client';

/**
 * 供應商新增 / 編輯側邊抽屜（Drawer）
 */
import { useState } from 'react';
import { useTranslations } from 'next-intl';
import { X } from 'lucide-react';
import { suppliersApi } from '@/lib/api';
import { useToast } from '@/contexts/ToastContext';
import type { Supplier, SupplierType } from '@/types';

interface Props {
  supplier: Supplier | null;
  onClose: (refresh?: boolean) => void;
}

const TYPES: SupplierType[] = ['farmer', 'broker', 'factory', 'logistics', 'customs', 'packaging'];

const EMPTY_FORM = {
  name:          '',
  supplier_type: 'farmer' as SupplierType,
  contact_name:  '',
  phone:         '',
  region:        '',
  address:       '',
  payment_terms: '',
  bank_account:  '',
  note:          '',
};

export default function SupplierDrawer({ supplier, onClose }: Props) {
  const t  = useTranslations('suppliers');
  const tc = useTranslations('common');
  const { showToast } = useToast();
  const isEdit = !!supplier;

  const [form, setForm] = useState({
    name:          supplier?.name          ?? '',
    supplier_type: (supplier?.supplier_type ?? 'farmer') as SupplierType,
    contact_name:  supplier?.contact_name  ?? '',
    phone:         supplier?.phone         ?? '',
    region:        supplier?.region        ?? '',
    address:       supplier?.address       ?? '',
    payment_terms: supplier?.payment_terms ?? '',
    bank_account:  supplier?.bank_account  ?? '',
    note:          supplier?.note          ?? '',
  });
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState('');

  const set = (key: string, val: string) => setForm((f) => ({ ...f, [key]: val }));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      // 清空字串轉 null
      const payload = Object.fromEntries(
        Object.entries(form).map(([k, v]) => [k, v === '' ? null : v])
      );
      if (isEdit) {
        await suppliersApi.update(supplier.id, payload);
        showToast(t('updateSuccess'), 'success');
      } else {
        await suppliersApi.create(payload);
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
    <>
      {/* 背景遮罩 */}
      <div className="fixed inset-0 z-40 bg-black/30" onClick={() => onClose()} />

      {/* Drawer 本體 */}
      <div className="fixed right-0 top-0 bottom-0 z-50 w-full max-w-md bg-white shadow-2xl flex flex-col">
        {/* 標題列 */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-800">
            {isEdit ? t('editSupplier') : t('addSupplier')}
          </h2>
          <button onClick={() => onClose()} className="text-gray-400 hover:text-gray-600">
            <X size={20} />
          </button>
        </div>

        {/* 表單內容（可捲動） */}
        <form onSubmit={handleSubmit} className="flex flex-col flex-1 min-h-0">
          <div className="flex-1 overflow-y-auto px-6 py-5 space-y-4">

            {/* 供應商名稱 */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                {t('name')} <span className="text-red-500">*</span>
              </label>
              <input value={form.name} onChange={(e) => set('name', e.target.value)}
                required className="input" placeholder="例：อ.สมชาย ปลูกผัก" />
            </div>

            {/* 類型 */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                {t('type')} <span className="text-red-500">*</span>
              </label>
              <select value={form.supplier_type}
                onChange={(e) => set('supplier_type', e.target.value)} className="input">
                {TYPES.map((type) => (
                  <option key={type} value={type}>{t(`types.${type}` as any)}</option>
                ))}
              </select>
            </div>

            {/* 聯絡人 / 電話（並排） */}
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">{t('contactName')}</label>
                <input value={form.contact_name} onChange={(e) => set('contact_name', e.target.value)}
                  className="input" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">{t('phone')}</label>
                <input value={form.phone} onChange={(e) => set('phone', e.target.value)}
                  className="input" placeholder="+66 xx-xxx-xxxx" />
              </div>
            </div>

            {/* 地區 */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t('region')}</label>
              <input value={form.region} onChange={(e) => set('region', e.target.value)}
                className="input" placeholder="e.g. เชียงราย / Chiang Rai" />
            </div>

            {/* 地址 */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t('address')}</label>
              <textarea value={form.address} onChange={(e) => set('address', e.target.value)}
                rows={2} className="input resize-none" />
            </div>

            {/* 付款條件 */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t('paymentTerms')}</label>
              <input value={form.payment_terms} onChange={(e) => set('payment_terms', e.target.value)}
                className="input" placeholder="e.g. Net 30 / Cash" />
            </div>

            {/* 銀行帳戶 */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t('bankAccount')}</label>
              <input value={form.bank_account} onChange={(e) => set('bank_account', e.target.value)}
                className="input" placeholder="Bank / Account / Name" />
            </div>

            {/* 備註 */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t('note')}</label>
              <textarea value={form.note} onChange={(e) => set('note', e.target.value)}
                rows={3} className="input resize-none" />
            </div>

            {error && (
              <div className="bg-red-50 border border-red-200 text-red-600 text-sm px-4 py-2 rounded-md">
                {error}
              </div>
            )}
          </div>

          {/* 底部按鈕 */}
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
    </>
  );
}
