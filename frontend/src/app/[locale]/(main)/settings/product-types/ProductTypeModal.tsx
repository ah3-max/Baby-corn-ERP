'use client';

/**
 * 品項新增/編輯 Modal
 */
import { useState } from 'react';
import { useTranslations } from 'next-intl';
import { X } from 'lucide-react';
import { productTypesApi } from '@/lib/api';
import type { ProductType } from '@/types';

interface Props {
  item: ProductType | null;  // null = 新增模式
  onClose: () => void;
  onDone: () => void;
}

export default function ProductTypeModal({ item, onClose, onDone }: Props) {
  const t = useTranslations('productTypes');
  const tc = useTranslations('common');

  const [form, setForm] = useState({
    code:             item?.code ?? '',
    batch_prefix:     item?.batch_prefix ?? '',
    name_zh:          item?.name_zh ?? '',
    name_en:          item?.name_en ?? '',
    name_th:          item?.name_th ?? '',
    shelf_life_days:  item?.shelf_life_days?.toString() ?? '',
    temp_min:         item?.storage_req?.temp_min?.toString() ?? '',
    temp_max:         item?.storage_req?.temp_max?.toString() ?? '',
    humidity_pct:     item?.storage_req?.humidity_pct?.toString() ?? '',
    processing_steps: item?.processing_steps?.join('、') ?? '',
  });
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState('');

  const set = (k: keyof typeof form, v: string) => setForm(f => ({ ...f, [k]: v }));

  const submit = async () => {
    if (!form.code || !form.batch_prefix || !form.name_zh) {
      setErr('品項代碼、批次前綴、中文名稱為必填');
      return;
    }
    setSaving(true);
    setErr('');
    try {
      const payload: Record<string, unknown> = {
        code: form.code,
        batch_prefix: form.batch_prefix,
        name_zh: form.name_zh,
        name_en: form.name_en || null,
        name_th: form.name_th || null,
        shelf_life_days: form.shelf_life_days ? parseInt(form.shelf_life_days) : null,
        processing_steps: form.processing_steps
          ? form.processing_steps.split(/[、,，]/).map(s => s.trim()).filter(Boolean)
          : [],
        storage_req: {},
      };

      // 儲藏條件
      const storage: Record<string, number> = {};
      if (form.temp_min) storage.temp_min = parseFloat(form.temp_min);
      if (form.temp_max) storage.temp_max = parseFloat(form.temp_max);
      if (form.humidity_pct) storage.humidity_pct = parseFloat(form.humidity_pct);
      payload.storage_req = storage;

      // 編輯模式保留原有的 quality_schema 和 size_grades
      if (item) {
        payload.quality_schema = item.quality_schema;
        payload.size_grades = item.size_grades;
        await productTypesApi.update(item.id, payload);
      } else {
        await productTypesApi.create(payload);
      }
      onDone();
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setErr(msg || tc('error'));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-lg p-6">
        <div className="flex items-center justify-between mb-5">
          <h3 className="font-bold text-gray-800 text-lg">
            {item ? t('editProductType') : t('addProductType')}
          </h3>
          <button onClick={onClose}><X size={18} className="text-gray-400" /></button>
        </div>

        <div className="space-y-3">
          {/* 基本資訊 */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-medium text-gray-600 mb-1 block">{t('code')} *</label>
              <input value={form.code} onChange={e => set('code', e.target.value)}
                className="input w-full" placeholder={t('codePlaceholder')}
                disabled={!!item} />
            </div>
            <div>
              <label className="text-xs font-medium text-gray-600 mb-1 block">{t('batchPrefix')} *</label>
              <input value={form.batch_prefix} onChange={e => set('batch_prefix', e.target.value.toUpperCase())}
                className="input w-full" placeholder={t('batchPrefixPlaceholder')}
                maxLength={5} disabled={!!item} />
            </div>
          </div>

          {/* 三語名稱 */}
          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="text-xs font-medium text-gray-600 mb-1 block">{t('nameZh')} *</label>
              <input value={form.name_zh} onChange={e => set('name_zh', e.target.value)} className="input w-full" />
            </div>
            <div>
              <label className="text-xs font-medium text-gray-600 mb-1 block">{t('nameEn')}</label>
              <input value={form.name_en} onChange={e => set('name_en', e.target.value)} className="input w-full" />
            </div>
            <div>
              <label className="text-xs font-medium text-gray-600 mb-1 block">{t('nameTh')}</label>
              <input value={form.name_th} onChange={e => set('name_th', e.target.value)} className="input w-full" />
            </div>
          </div>

          {/* 保質期 */}
          <div>
            <label className="text-xs font-medium text-gray-600 mb-1 block">{t('shelfLifeDays')}</label>
            <input type="number" min="1" value={form.shelf_life_days}
              onChange={e => set('shelf_life_days', e.target.value)} className="input w-32" />
          </div>

          {/* 儲藏條件 */}
          <div>
            <label className="text-xs font-medium text-gray-600 mb-1 block">{t('storageReq')}</label>
            <div className="grid grid-cols-3 gap-3">
              <div>
                <span className="text-xs text-gray-400">{t('tempRange')} (°C)</span>
                <div className="flex items-center gap-1 mt-1">
                  <input type="number" value={form.temp_min} onChange={e => set('temp_min', e.target.value)}
                    className="input w-full text-sm" placeholder="min" />
                  <span className="text-gray-400">~</span>
                  <input type="number" value={form.temp_max} onChange={e => set('temp_max', e.target.value)}
                    className="input w-full text-sm" placeholder="max" />
                </div>
              </div>
              <div>
                <span className="text-xs text-gray-400">{t('humidity')} (%)</span>
                <input type="number" min="0" max="100" value={form.humidity_pct}
                  onChange={e => set('humidity_pct', e.target.value)} className="input w-full text-sm mt-1" />
              </div>
            </div>
          </div>

          {/* 加工步驟 */}
          <div>
            <label className="text-xs font-medium text-gray-600 mb-1 block">{t('processingSteps')}</label>
            <input value={form.processing_steps}
              onChange={e => set('processing_steps', e.target.value)}
              className="input w-full" placeholder="例如：選果、清洗、分級、秤重、包裝、冷藏（用頓號分隔）" />
          </div>
        </div>

        {err && <p className="text-xs text-red-600 mt-2">{err}</p>}

        <div className="flex gap-2 mt-5">
          <button onClick={onClose} className="btn-secondary flex-1">{tc('cancel')}</button>
          <button onClick={submit} disabled={saving} className="btn-primary flex-1">
            {saving ? tc('loading') : tc('save')}
          </button>
        </div>
      </div>
    </div>
  );
}
