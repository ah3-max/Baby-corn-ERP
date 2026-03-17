'use client';

/**
 * 到廠確認 Modal
 * 一條龍流程：到廠確認後自動建立批次，提供一鍵跳轉
 */
import { useState, useMemo } from 'react';
import { useTranslations, useLocale } from 'next-intl';
import { useRouter } from 'next/navigation';
import { X, Package, AlertTriangle, CheckCircle2, ArrowRight } from 'lucide-react';
import { purchasesApi } from '@/lib/api';
import { useToast } from '@/contexts/ToastContext';
import type { PurchaseOrder } from '@/types';

interface Props {
  purchase: PurchaseOrder;
  onClose: (refresh?: boolean) => void;
}

// 自動建立的批次資訊
interface AutoCreatedBatch {
  id: string;
  batch_no: string;
  initial_weight: number;
  status: string;
}

export default function ArrivalModal({ purchase, onClose }: Props) {
  const t  = useTranslations('purchases');
  const tc = useTranslations('common');
  const { showToast } = useToast();
  const router = useRouter();
  const locale = useLocale();

  const now = new Date().toISOString().slice(0, 16);

  const [form, setForm] = useState({
    arrived_at:      now,
    received_weight: '',
    defect_weight:   '0',
    arrival_note:    '',
  });
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState('');
  // 到廠確認成功後，顯示自動建立的批次資訊
  const [createdBatch, setCreatedBatch] = useState<AutoCreatedBatch | null>(null);

  const set = (key: string, val: string) => setForm((f) => ({ ...f, [key]: val }));

  // 即時計算
  const calc = useMemo(() => {
    const received = parseFloat(form.received_weight) || 0;
    const defect   = parseFloat(form.defect_weight)   || 0;
    const usable   = Math.max(received - defect, 0);
    const rate     = received > 0 ? (defect / received * 100) : 0;
    return { received, defect, usable, rate };
  }, [form.received_weight, form.defect_weight]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (calc.defect > calc.received) {
      setError(t('defectOverError'));
      return;
    }
    setError('');
    setLoading(true);
    try {
      const { data } = await purchasesApi.confirmArrival(purchase.id, {
        arrived_at:      form.arrived_at,
        received_weight: calc.received,
        defect_weight:   calc.defect,
        arrival_note:    form.arrival_note || null,
      });
      // 後端回傳自動建立的批次資訊
      if (data.auto_created_batch) {
        setCreatedBatch(data.auto_created_batch);
        showToast(t('arrivalSuccess'), 'success');
      } else {
        showToast(t('arrivalSuccess'), 'success');
        onClose(true);
      }
    } catch (err: any) {
      const msg = err?.response?.data?.detail ?? tc('error');
      setError(msg);
      showToast(msg, 'error');
    } finally {
      setLoading(false);
    }
  };

  // 跳轉到新建立的批次詳情頁
  const goToBatch = () => {
    if (createdBatch) {
      onClose(true);
      router.push(`/${locale}/batches/${createdBatch.id}`);
    }
  };

  // ─── 成功畫面：顯示自動建立的批次 ───
  if (createdBatch) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
        <div className="card w-full max-w-md shadow-xl">
          <div className="px-6 py-8 text-center">
            <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <CheckCircle2 size={32} className="text-green-600" />
            </div>
            <h2 className="text-xl font-bold text-gray-800 mb-2">{t('arrivalSuccess')}</h2>
            <p className="text-sm text-gray-500 mb-6">{t('batchAutoCreated')}</p>

            {/* 批次資訊卡片 */}
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6 text-left">
              <div className="flex items-center gap-2 mb-2">
                <Package size={16} className="text-blue-600" />
                <span className="font-mono font-bold text-blue-700">{createdBatch.batch_no}</span>
              </div>
              <div className="grid grid-cols-2 gap-2 text-sm">
                <div>
                  <span className="text-gray-400">{t('receivedWeight')}</span>
                  <p className="font-semibold text-gray-700">{calc.received.toLocaleString()} kg</p>
                </div>
                <div>
                  <span className="text-gray-400">{t('usableWeight')}</span>
                  <p className="font-semibold text-green-600">{createdBatch.initial_weight.toLocaleString()} kg</p>
                </div>
              </div>
            </div>

            {/* 操作按鈕 */}
            <div className="flex gap-3">
              <button
                onClick={() => onClose(true)}
                className="btn-secondary flex-1"
              >
                {t('stayHere')}
              </button>
              <button
                onClick={goToBatch}
                className="btn-primary flex-1 flex items-center justify-center gap-2"
              >
                {t('goToBatch')} <ArrowRight size={16} />
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // ─── 表單畫面 ───
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="card w-full max-w-md shadow-xl">
        {/* 標題 */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <div className="flex items-center gap-2">
            <CheckCircle2 size={20} className="text-green-600" />
            <h2 className="text-lg font-semibold text-gray-800">{t('arrivalConfirm')}</h2>
          </div>
          <button onClick={() => onClose()} className="text-gray-400 hover:text-gray-600">
            <X size={20} />
          </button>
        </div>

        {/* 採購單資訊摘要 */}
        <div className="px-6 py-3 bg-gray-50 border-b border-gray-200">
          <p className="text-sm font-mono text-gray-500">{purchase.order_no}</p>
          <p className="font-semibold text-gray-800">{purchase.supplier?.name}</p>
          <p className="text-sm text-gray-500">{tc('estimatedWeight')}：{Number(purchase.estimated_weight).toLocaleString()} kg</p>
        </div>

        {/* 一條龍提示 */}
        <div className="px-6 py-2 bg-blue-50 border-b border-blue-100">
          <p className="text-xs text-blue-600 flex items-center gap-1">
            <Package size={12} />
            {t('autoCreateBatchHint')}
          </p>
        </div>

        <form onSubmit={handleSubmit} className="px-6 py-5 space-y-4">
          {/* 到廠時間 */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              {t('arrivedAt')} <span className="text-red-500">*</span>
            </label>
            <input type="datetime-local" value={form.arrived_at}
              onChange={(e) => set('arrived_at', e.target.value)}
              required className="input" />
          </div>

          {/* 收貨 / 不良重量並排 */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                {t('receivedWeight')} <span className="text-red-500">*</span>
              </label>
              <input type="number" step="0.01" min="0"
                value={form.received_weight}
                onChange={(e) => set('received_weight', e.target.value)}
                required className="input" placeholder="0.00" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t('defectWeight')}</label>
              <input type="number" step="0.01" min="0"
                value={form.defect_weight}
                onChange={(e) => set('defect_weight', e.target.value)}
                className="input" placeholder="0.00" />
            </div>
          </div>

          {/* 即時計算結果卡 */}
          {calc.received > 0 && (
            <div className="rounded-lg border border-gray-200 overflow-hidden">
              <div className="grid grid-cols-3 divide-x divide-gray-200">
                <div className="p-3 text-center bg-green-50">
                  <p className="text-xs text-gray-500 mb-1 flex items-center justify-center gap-1">
                    <Package size={11} /> {t('usableWeight')}
                  </p>
                  <p className="text-lg font-bold text-green-700">{calc.usable.toFixed(1)}</p>
                  <p className="text-xs text-gray-400">kg</p>
                </div>
                <div className={`p-3 text-center ${calc.rate > 10 ? 'bg-red-50' : 'bg-gray-50'}`}>
                  <p className="text-xs text-gray-500 mb-1 flex items-center justify-center gap-1">
                    {calc.rate > 10 && <AlertTriangle size={11} className="text-red-500" />}
                    {t('defectRate')}
                  </p>
                  <p className={`text-lg font-bold ${calc.rate > 10 ? 'text-red-600' : 'text-gray-700'}`}>
                    {calc.rate.toFixed(1)}%
                  </p>
                </div>
                <div className="p-3 text-center bg-gray-50">
                  <p className="text-xs text-gray-500 mb-1">{t('vsEstimated')}</p>
                  <p className={`text-lg font-bold ${
                    calc.received >= Number(purchase.estimated_weight) ? 'text-green-600' : 'text-orange-500'
                  }`}>
                    {calc.received >= Number(purchase.estimated_weight) ? '▲' : '▼'}
                    {Math.abs(calc.received - Number(purchase.estimated_weight)).toFixed(1)}
                  </p>
                  <p className="text-xs text-gray-400">kg</p>
                </div>
              </div>
            </div>
          )}

          {/* 備註 */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">{t('arrivalNote')}</label>
            <textarea value={form.arrival_note} onChange={(e) => set('arrival_note', e.target.value)}
              rows={2} className="input resize-none" placeholder={t('abnormalNote')} />
          </div>

          {error && (
            <div className="bg-red-50 border border-red-200 text-red-600 text-sm px-4 py-2 rounded-md">
              {error}
            </div>
          )}

          <div className="flex justify-end gap-3 pt-1">
            <button type="button" onClick={() => onClose()} className="btn-secondary">
              {tc('cancel')}
            </button>
            <button type="submit" disabled={loading || !form.received_weight}
              className="btn-primary flex items-center gap-2">
              <CheckCircle2 size={15} />
              {loading ? '...' : t('confirmArrival')}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
