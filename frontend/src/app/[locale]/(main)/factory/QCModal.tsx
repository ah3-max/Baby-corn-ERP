'use client';

import { useState } from 'react';
import { useTranslations } from 'next-intl';
import { X, FlaskConical } from 'lucide-react';
import { qcApi } from '@/lib/api';
import { useToast } from '@/contexts/ToastContext';

interface Props {
  batchId: string;
  batchNo: string;
  onClose: (refresh?: boolean) => void;
}

export default function QCModal({ batchId, batchNo, onClose }: Props) {
  const t  = useTranslations('factory');
  const tc = useTranslations('common');
  const { showToast } = useToast();

  const now = new Date();
  const localDT = new Date(now.getTime() - now.getTimezoneOffset() * 60000)
    .toISOString()
    .slice(0, 16);

  const [form, setForm] = useState({
    inspector_name: '',
    checked_at:     localDT,
    result:         'pass',
    grade:          '',
    weight_checked: '',
    notes:          '',
  });
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState('');

  const set = (key: string, val: string) => setForm((f) => ({ ...f, [key]: val }));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await qcApi.create({
        batch_id:       batchId,
        inspector_name: form.inspector_name,
        checked_at:     new Date(form.checked_at).toISOString(),
        result:         form.result,
        grade:          form.grade || null,
        weight_checked: form.weight_checked ? parseFloat(form.weight_checked) : null,
        notes:          form.notes || null,
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
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/30" onClick={() => onClose()} />
      <div className="relative bg-white rounded-2xl shadow-2xl w-full max-w-md z-10">
        {/* 標題 */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <div className="flex items-center gap-2">
            <FlaskConical size={18} className="text-primary-600" />
            <h2 className="text-lg font-semibold text-gray-800">
              {t('addQC')} — {batchNo}
            </h2>
          </div>
          <button onClick={() => onClose()} className="text-gray-400 hover:text-gray-600">
            <X size={20} />
          </button>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="px-6 py-5 space-y-4">
            {/* 檢驗人員 */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                {t('inspector')} <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                value={form.inspector_name}
                onChange={(e) => set('inspector_name', e.target.value)}
                required
                className="input"
                placeholder="John / สมชาย"
              />
            </div>

            {/* 檢驗時間 */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                {t('checkedAt')} <span className="text-red-500">*</span>
              </label>
              <input
                type="datetime-local"
                value={form.checked_at}
                onChange={(e) => set('checked_at', e.target.value)}
                required
                className="input"
              />
            </div>

            {/* 結果 + 等級 */}
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  {t('result')} <span className="text-red-500">*</span>
                </label>
                <select
                  value={form.result}
                  onChange={(e) => set('result', e.target.value)}
                  required
                  className="input"
                >
                  <option value="pass">{t('results.pass')}</option>
                  <option value="fail">{t('results.fail')}</option>
                  <option value="conditional_pass">{t('results.conditional_pass')}</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  {t('grade')}
                  <span className="ml-1 text-xs text-gray-400">{tc('optional')}</span>
                </label>
                <select
                  value={form.grade}
                  onChange={(e) => set('grade', e.target.value)}
                  className="input"
                >
                  <option value="">—</option>
                  <option value="A">{t('grades.A')}</option>
                  <option value="B">{t('grades.B')}</option>
                  <option value="C">{t('grades.C')}</option>
                  <option value="D">{t('grades.D')}</option>
                </select>
              </div>
            </div>

            {/* 檢驗重量 */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                {t('weightChecked')}
                <span className="ml-1 text-xs text-gray-400">{tc('optional')}</span>
              </label>
              <input
                type="number"
                step="0.01"
                min="0"
                value={form.weight_checked}
                onChange={(e) => set('weight_checked', e.target.value)}
                className="input"
                placeholder="0.00"
              />
            </div>

            {/* 備註 */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                {t('notes')}
              </label>
              <textarea
                value={form.notes}
                onChange={(e) => set('notes', e.target.value)}
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
