'use client';

/**
 * 銷售訂單新增 / 編輯 Drawer
 * UI重點：
 * - 動態新增多個訂單項目
 * - 每項選批次 + 數量 + 單價，即時計算小計
 * - 總金額自動加總
 */
import { useState, useEffect, useMemo } from 'react';
import { useTranslations } from 'next-intl';
import { X, ShoppingCart, Plus, Trash2 } from 'lucide-react';
import { salesApi, customersApi, batchesApi } from '@/lib/api';
import { useToast } from '@/contexts/ToastContext';
import type { SalesOrder, Customer, Batch } from '@/types';

interface ItemForm {
  batch_id:       string;
  quantity_kg:    string;
  unit_price_twd: string;
  note:           string;
}

interface Props {
  order: SalesOrder | null;
  onClose: (refresh?: boolean) => void;
}

export default function SalesDrawer({ order, onClose }: Props) {
  const t  = useTranslations('sales');
  const tc = useTranslations('common');
  const { showToast } = useToast();
  const isEdit = !!order;

  const today = new Date().toISOString().split('T')[0];

  const [form, setForm] = useState({
    customer_id:   order?.customer_id   ?? '',
    order_date:    order?.order_date     ?? today,
    delivery_date: order?.delivery_date  ?? '',
    note:          order?.note           ?? '',
  });
  const [items, setItems] = useState<ItemForm[]>(
    order?.items.map((i) => ({
      batch_id:       i.batch_id,
      quantity_kg:    String(i.quantity_kg),
      unit_price_twd: String(i.unit_price_twd),
      note:           i.note ?? '',
    })) ?? [{ batch_id: '', quantity_kg: '', unit_price_twd: '', note: '' }]
  );

  const [customers, setCustomers] = useState<Customer[]>([]);
  const [batches, setBatches]     = useState<Batch[]>([]);
  const [loading, setLoading]     = useState(false);
  const [error, setError]         = useState('');

  useEffect(() => {
    customersApi.list({ is_active: true }).then(({ data }) => setCustomers(data));
    // 可出售的批次：in_stock 或 sold
    batchesApi.list({ status: 'in_stock' }).then(({ data }) => setBatches(data));
  }, []);

  const set = (key: string, val: string) => setForm((f) => ({ ...f, [key]: val }));

  const setItem = (idx: number, key: keyof ItemForm, val: string) => {
    setItems((prev) => prev.map((it, i) => i === idx ? { ...it, [key]: val } : it));
  };

  const addItem = () => setItems((prev) => [
    ...prev,
    { batch_id: '', quantity_kg: '', unit_price_twd: '', note: '' },
  ]);

  const removeItem = (idx: number) => setItems((prev) => prev.filter((_, i) => i !== idx));

  // 計算總金額
  const totalTWD = useMemo(() => {
    return items.reduce((sum, it) => {
      const q = parseFloat(it.quantity_kg);
      const p = parseFloat(it.unit_price_twd);
      if (!isNaN(q) && !isNaN(p)) return sum + q * p;
      return sum;
    }, 0);
  }, [items]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const validItems = items.filter(
        (it) => it.batch_id && it.quantity_kg && it.unit_price_twd
      );
      if (validItems.length === 0) {
        setError(t('atLeastOneItem'));
        return;
      }
      const payload = {
        customer_id:   form.customer_id,
        order_date:    form.order_date,
        delivery_date: form.delivery_date || null,
        note:          form.note || null,
        items: validItems.map((it) => ({
          batch_id:       it.batch_id,
          quantity_kg:    parseFloat(it.quantity_kg),
          unit_price_twd: parseFloat(it.unit_price_twd),
          note:           it.note || null,
        })),
      };
      if (isEdit) {
        await salesApi.update(order.id, payload);
        showToast(t('updateSuccess'), 'success');
      } else {
        await salesApi.create(payload);
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
      <div className="fixed right-0 top-0 bottom-0 z-50 w-full max-w-xl bg-white shadow-2xl flex flex-col">
        {/* 標題 */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <div className="flex items-center gap-2">
            <ShoppingCart size={20} className="text-primary-600" />
            <h2 className="text-lg font-semibold text-gray-800">
              {isEdit ? t('editOrder') : t('addOrder')}
            </h2>
          </div>
          <button onClick={() => onClose()} className="text-gray-400 hover:text-gray-600">
            <X size={20} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="flex flex-col flex-1 min-h-0">
          <div className="flex-1 overflow-y-auto px-6 py-5 space-y-5">

            {/* ── 基本資訊 ── */}
            <div>
              <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">
                {t('customer')}
              </p>
              <div className="grid grid-cols-2 gap-3">
                <div className="col-span-2">
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    {t('selectCustomer')} <span className="text-red-500">*</span>
                  </label>
                  <select value={form.customer_id}
                    onChange={(e) => set('customer_id', e.target.value)}
                    required className="input">
                    <option value="">—</option>
                    {customers.map((c) => (
                      <option key={c.id} value={c.id}>{c.name}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    {t('orderDate')} <span className="text-red-500">*</span>
                  </label>
                  <input type="date" value={form.order_date}
                    onChange={(e) => set('order_date', e.target.value)}
                    required className="input" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    {t('deliveryDate')}
                    <span className="ml-1 text-xs text-gray-400">{tc('optional')}</span>
                  </label>
                  <input type="date" value={form.delivery_date}
                    onChange={(e) => set('delivery_date', e.target.value)}
                    className="input" />
                </div>
              </div>
            </div>

            {/* ── 訂單項目 ── */}
            <div>
              <div className="flex items-center justify-between mb-3">
                <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider">
                  {t('items')}
                </p>
                <button type="button" onClick={addItem}
                  className="flex items-center gap-1 text-xs text-primary-600 hover:text-primary-700 font-medium">
                  <Plus size={13} /> {t('addItem')}
                </button>
              </div>

              <div className="space-y-3">
                {items.map((it, idx) => {
                  const subtotal = (() => {
                    const q = parseFloat(it.quantity_kg);
                    const p = parseFloat(it.unit_price_twd);
                    return !isNaN(q) && !isNaN(p) ? q * p : null;
                  })();

                  return (
                    <div key={idx} className="border border-gray-200 rounded-xl p-4 relative">
                      {items.length > 1 && (
                        <button type="button" onClick={() => removeItem(idx)}
                          className="absolute top-3 right-3 text-gray-300 hover:text-red-500 transition-colors">
                          <Trash2 size={15} />
                        </button>
                      )}
                      <p className="text-xs font-semibold text-gray-400 mb-3">Item {idx + 1}</p>

                      {/* 選批次 */}
                      <div className="mb-3">
                        <label className="block text-xs text-gray-600 mb-1">
                          {t('selectBatch')} <span className="text-red-500">*</span>
                        </label>
                        <select value={it.batch_id}
                          onChange={(e) => setItem(idx, 'batch_id', e.target.value)}
                          className="input text-sm">
                          <option value="">—</option>
                          {batches.map((b) => (
                            <option key={b.id} value={b.id}>
                              {b.batch_no} ({Number(b.current_weight).toLocaleString()} kg)
                            </option>
                          ))}
                        </select>
                      </div>

                      {/* 數量 + 單價 */}
                      <div className="grid grid-cols-2 gap-3 mb-2">
                        <div>
                          <label className="block text-xs text-gray-600 mb-1">
                            {t('quantityKg')} <span className="text-red-500">*</span>
                          </label>
                          <input type="number" step="0.01" min="0.01"
                            value={it.quantity_kg}
                            onChange={(e) => setItem(idx, 'quantity_kg', e.target.value)}
                            className="input text-sm" placeholder="0.00" />
                        </div>
                        <div>
                          <label className="block text-xs text-gray-600 mb-1">
                            {t('unitPriceTWD')} <span className="text-red-500">*</span>
                          </label>
                          <input type="number" step="0.01" min="0"
                            value={it.unit_price_twd}
                            onChange={(e) => setItem(idx, 'unit_price_twd', e.target.value)}
                            className="input text-sm" placeholder="0.00" />
                        </div>
                      </div>

                      {/* 小計 */}
                      {subtotal != null && (
                        <p className="text-right text-xs text-primary-700 font-semibold">
                          NT$ {subtotal.toLocaleString()}
                        </p>
                      )}
                    </div>
                  );
                })}
              </div>

              {/* 總金額 */}
              {totalTWD > 0 && (
                <div className="mt-3 flex items-center justify-between px-4 py-3 bg-primary-50 border border-primary-200 rounded-lg">
                  <span className="text-sm font-medium text-primary-700">{t('totalAmount')}</span>
                  <span className="text-xl font-bold text-primary-700">
                    NT$ {totalTWD.toLocaleString()}
                  </span>
                </div>
              )}
            </div>

            {/* ── 備註 ── */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t('note')}</label>
              <textarea value={form.note} onChange={(e) => set('note', e.target.value)}
                rows={2} className="input resize-none" />
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
