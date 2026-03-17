'use client';

/**
 * 批次新增 Drawer
 * UI重點：
 * - 僅顯示已到廠的採購單
 * - 選擇 PO 後自動帶入可用重量
 * - 可調整初始重量
 */
import { useState, useEffect } from 'react';
import { useTranslations } from 'next-intl';
import { X, Package } from 'lucide-react';
import { batchesApi, purchasesApi } from '@/lib/api';
import { useToast } from '@/contexts/ToastContext';
import type { PurchaseOrder } from '@/types';

interface Props {
  onClose: (refresh?: boolean) => void;
}

export default function BatchDrawer({ onClose }: Props) {
  const t  = useTranslations('batches');
  const tc = useTranslations('common');
  const { showToast } = useToast();

  const [arrivedPOs, setArrivedPOs] = useState<PurchaseOrder[]>([]);
  const [form, setForm] = useState({
    purchase_order_id: '',
    initial_weight:    '',
    note:              '',
  });
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState('');

  // 載入已到廠的採購單
  useEffect(() => {
    purchasesApi.list({ status: 'arrived' }).then(({ data }) => {
      setArrivedPOs(data);
    });
  }, []);

  const set = (key: string, val: string) => setForm((f) => ({ ...f, [key]: val }));

  // 選擇採購單後自動帶入可用重量
  const handlePOSelect = (poId: string) => {
    set('purchase_order_id', poId);
    const po = arrivedPOs.find((p) => p.id === poId);
    if (po?.usable_weight) {
      set('initial_weight', String(po.usable_weight));
    } else {
      set('initial_weight', '');
    }
  };

  const selectedPO = arrivedPOs.find((p) => p.id === form.purchase_order_id);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await batchesApi.create({
        purchase_order_id: form.purchase_order_id,
        initial_weight:    parseFloat(form.initial_weight),
        note:              form.note || null,
      });
      showToast(t('createSuccess'), 'success');
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
          <div className="flex items-center gap-2">
            <Package size={20} className="text-primary-600" />
            <h2 className="text-lg font-semibold text-gray-800">{t('addBatch')}</h2>
          </div>
          <button onClick={() => onClose()} className="text-gray-400 hover:text-gray-600">
            <X size={20} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="flex flex-col flex-1 min-h-0">
          <div className="flex-1 overflow-y-auto px-6 py-5 space-y-5">

            {/* ── 選擇採購單 ── */}
            <div>
              <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">
                {t('sourceInfo')}
              </p>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  {t('purchaseOrder')} <span className="text-red-500">*</span>
                </label>
                {arrivedPOs.length === 0 ? (
                  <div className="p-4 bg-yellow-50 border border-yellow-200 rounded-lg text-sm text-yellow-700">
                    {t('noPOAvailable')}
                  </div>
                ) : (
                  <select
                    value={form.purchase_order_id}
                    onChange={(e) => handlePOSelect(e.target.value)}
                    required
                    className="input"
                  >
                    <option value="">— {t('selectPO')} —</option>
                    {arrivedPOs.map((po) => (
                      <option key={po.id} value={po.id}>
                        {po.order_no} — {po.supplier?.name ?? ''}
                      </option>
                    ))}
                  </select>
                )}

                {/* 選中採購單的摘要 */}
                {selectedPO && (
                  <div className="mt-2 p-3 bg-gray-50 rounded-lg text-sm space-y-1">
                    <div className="flex justify-between text-gray-600">
                      <span className="text-gray-400">{t('supplier')}</span>
                      <span className="font-medium">{selectedPO.supplier?.name}</span>
                    </div>
                    <div className="flex justify-between text-gray-600">
                      <span className="text-gray-400">{tc('estimatedWeight')}</span>
                      <span className="font-medium">{Number(selectedPO.usable_weight).toLocaleString()} kg</span>
                    </div>
                    {selectedPO.defect_rate != null && (
                      <div className="flex justify-between text-gray-600">
                        <span className="text-gray-400">{t('defectRate')}</span>
                        <span className={`font-medium ${Number(selectedPO.defect_rate) > 10 ? 'text-red-500' : 'text-gray-700'}`}>
                          {Number(selectedPO.defect_rate).toFixed(1)}%
                        </span>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>

            {/* ── 重量資訊 ── */}
            <div>
              <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">
                {t('weightInfo')}
              </p>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  {t('initialWeight')} <span className="text-red-500">*</span>
                </label>
                <input
                  type="number"
                  step="0.01"
                  min="0.01"
                  value={form.initial_weight}
                  onChange={(e) => set('initial_weight', e.target.value)}
                  required
                  className="input"
                  placeholder="0.00"
                />
                <p className="text-xs text-gray-400 mt-1">
                  {t('weightHint')}
                </p>
              </div>
            </div>

            {/* ── 備註 ── */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t('note')}</label>
              <textarea
                value={form.note}
                onChange={(e) => set('note', e.target.value)}
                rows={3}
                className="input resize-none"
              />
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
            <button
              type="submit"
              disabled={loading || !form.purchase_order_id || !form.initial_weight}
              className="btn-primary"
            >
              {loading ? '...' : tc('save')}
            </button>
          </div>
        </form>
      </div>
    </>
  );
}
