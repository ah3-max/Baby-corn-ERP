'use client';

/**
 * 採購單新增 / 編輯 Drawer
 * UI重點：
 * - 選供應商自動顯示類型
 * - 中盤商時才顯示農民來源欄位
 * - 即時計算總金額
 */
import { useState, useEffect, useMemo } from 'react';
import { useTranslations } from 'next-intl';
import { X, Calculator } from 'lucide-react';
import { purchasesApi, suppliersApi } from '@/lib/api';
import { useToast } from '@/contexts/ToastContext';
import type { PurchaseOrder, Supplier } from '@/types';

interface Props {
  purchase: PurchaseOrder | null;
  onClose: (refresh?: boolean) => void;
}

export default function PurchaseDrawer({ purchase, onClose }: Props) {
  const t  = useTranslations('purchases');
  const tc = useTranslations('common');
  const { showToast } = useToast();
  const isEdit = !!purchase;

  const today = new Date().toISOString().split('T')[0];

  const [form, setForm] = useState({
    order_date:        purchase?.order_date       ?? today,
    supplier_id:       purchase?.supplier_id      ?? '',
    source_farmer_id:  purchase?.source_farmer_id ?? '',
    estimated_weight:  purchase?.estimated_weight ? String(purchase.estimated_weight) : '',
    unit_price:        purchase?.unit_price        ? String(purchase.unit_price)       : '',
    expected_arrival:  purchase?.expected_arrival
      ? new Date(purchase.expected_arrival).toISOString().slice(0, 16)
      : '',
    note: purchase?.note ?? '',
  });

  const [suppliers, setSuppliers]   = useState<Supplier[]>([]);
  const [farmers, setFarmers]       = useState<Supplier[]>([]);
  const [loading, setLoading]       = useState(false);
  const [error, setError]           = useState('');

  // 載入供應商（農民 + 中盤商）
  useEffect(() => {
    suppliersApi.list({ is_active: true }).then(({ data }) => {
      setSuppliers(data.filter((s: Supplier) => ['farmer', 'broker'].includes(s.supplier_type)));
      setFarmers(data.filter((s: Supplier) => s.supplier_type === 'farmer'));
    });
  }, []);

  const set = (key: string, val: string) => setForm((f) => ({ ...f, [key]: val }));

  // 選中的供應商
  const selectedSupplier = suppliers.find((s) => s.id === form.supplier_id);
  const isBroker = selectedSupplier?.supplier_type === 'broker';

  // 即時計算總金額
  const totalAmount = useMemo(() => {
    const w = parseFloat(form.estimated_weight);
    const p = parseFloat(form.unit_price);
    if (!isNaN(w) && !isNaN(p) && w > 0 && p > 0) return (w * p).toFixed(2);
    return null;
  }, [form.estimated_weight, form.unit_price]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const payload = {
        order_date:        form.order_date,
        supplier_id:       form.supplier_id,
        source_farmer_id:  isBroker && form.source_farmer_id ? form.source_farmer_id : null,
        estimated_weight:  parseFloat(form.estimated_weight),
        unit_price:        parseFloat(form.unit_price),
        expected_arrival:  form.expected_arrival || null,
        note:              form.note || null,
      };
      if (isEdit) {
        await purchasesApi.update(purchase.id, payload);
        showToast(t('updateSuccess'), 'success');
      } else {
        await purchasesApi.create(payload);
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
      <div className="fixed inset-0 z-40 bg-black/30" onClick={() => onClose()} />
      <div className="fixed right-0 top-0 bottom-0 z-50 w-full max-w-md bg-white shadow-2xl flex flex-col">
        {/* 標題 */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-800">
            {isEdit ? t('editPurchase') : t('addPurchase')}
          </h2>
          <button onClick={() => onClose()} className="text-gray-400 hover:text-gray-600">
            <X size={20} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="flex flex-col flex-1 min-h-0">
          <div className="flex-1 overflow-y-auto px-6 py-5 space-y-5">

            {/* ── 基本資料 ── */}
            <div>
              <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">{t('basicInfo')}</p>

              {/* 採購日期 */}
              <div className="mb-3">
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  {t('orderDate')} <span className="text-red-500">*</span>
                </label>
                <input type="date" value={form.order_date}
                  onChange={(e) => set('order_date', e.target.value)}
                  required className="input" />
              </div>

              {/* 採購來源 */}
              <div className="mb-3">
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  {t('supplier')} <span className="text-red-500">*</span>
                </label>
                <select value={form.supplier_id}
                  onChange={(e) => { set('supplier_id', e.target.value); set('source_farmer_id', ''); }}
                  required className="input">
                  <option value="">— {t('selectSupplier')} —</option>
                  <optgroup label={`🌾 ${t('farmer')}`}>
                    {suppliers.filter(s => s.supplier_type === 'farmer').map((s) => (
                      <option key={s.id} value={s.id}>{s.name}</option>
                    ))}
                  </optgroup>
                  <optgroup label={`🏪 ${t('broker')}`}>
                    {suppliers.filter(s => s.supplier_type === 'broker').map((s) => (
                      <option key={s.id} value={s.id}>{s.name}</option>
                    ))}
                  </optgroup>
                </select>

                {/* 供應商類型提示 */}
                {selectedSupplier && (
                  <p className={`mt-1.5 text-xs font-medium ${isBroker ? 'text-blue-600' : 'text-green-600'}`}>
                    {isBroker ? `🏪 ${t('brokerMode')}` : `🌾 ${t('farmerDirect')}`}
                  </p>
                )}
              </div>

              {/* 農民來源（僅中盤商時顯示） */}
              {isBroker && (
                <div className="mb-3 pl-3 border-l-2 border-blue-200">
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    {t('sourceFarmer')}
                    <span className="ml-1 text-xs text-gray-400">{tc('optional')}</span>
                  </label>
                  <select value={form.source_farmer_id}
                    onChange={(e) => set('source_farmer_id', e.target.value)}
                    className="input">
                    <option value="">— {t('selectFarmer')} —</option>
                    {farmers.map((f) => (
                      <option key={f.id} value={f.id}>{f.name}</option>
                    ))}
                  </select>
                </div>
              )}
            </div>

            {/* ── 重量與價格 ── */}
            <div>
              <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">{t('weightAndPrice')}</p>

              <div className="grid grid-cols-2 gap-3 mb-3">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    {t('estimatedWeight')} <span className="text-red-500">*</span>
                  </label>
                  <input type="number" step="0.01" min="0"
                    value={form.estimated_weight}
                    onChange={(e) => set('estimated_weight', e.target.value)}
                    required className="input" placeholder="0.00" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    {t('unitPrice')} <span className="text-red-500">*</span>
                  </label>
                  <input type="number" step="0.01" min="0"
                    value={form.unit_price}
                    onChange={(e) => set('unit_price', e.target.value)}
                    required className="input" placeholder="0.00" />
                </div>
              </div>

              {/* 即時計算總金額 */}
              {totalAmount && (
                <div className="flex items-center gap-2 px-4 py-3 bg-primary-50 border border-primary-200 rounded-lg">
                  <Calculator size={16} className="text-primary-600 flex-shrink-0" />
                  <div>
                    <p className="text-xs text-primary-600">{t('totalAmount')}</p>
                    <p className="text-lg font-bold text-primary-700">
                      ฿ {Number(totalAmount).toLocaleString('th-TH', { minimumFractionDigits: 2 })}
                    </p>
                  </div>
                </div>
              )}
            </div>

            {/* ── 時間 ── */}
            <div>
              <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">{t('time')}</p>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">{t('expectedArrival')}</label>
                <input type="datetime-local" value={form.expected_arrival}
                  onChange={(e) => set('expected_arrival', e.target.value)}
                  className="input" />
              </div>
            </div>

            {/* ── 備註 ── */}
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
