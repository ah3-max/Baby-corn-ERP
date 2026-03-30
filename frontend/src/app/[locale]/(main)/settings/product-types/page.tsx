'use client';

/**
 * 品項管理頁面 /settings/product-types
 * 列表 + Modal 新增/編輯品項
 */
import { useEffect, useState, useCallback } from 'react';
import { useTranslations } from 'next-intl';
import {
  Sprout, Plus, Pencil, Thermometer, Clock, Package,
  ChevronDown, ChevronUp, Power,
} from 'lucide-react';
import { productTypesApi } from '@/lib/api';
import type { ProductType } from '@/types';
import ProductTypeModal from './ProductTypeModal';

export default function ProductTypesPage() {
  const t = useTranslations('productTypes');
  const tc = useTranslations('common');

  const [items, setItems] = useState<ProductType[]>([]);
  const [loading, setLoading] = useState(true);
  const [editItem, setEditItem] = useState<ProductType | null>(null);
  const [showModal, setShowModal] = useState(false);
  const [expanded, setExpanded] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await productTypesApi.list();
      setItems(res.data);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const openCreate = () => { setEditItem(null); setShowModal(true); };
  const openEdit = (item: ProductType) => { setEditItem(item); setShowModal(true); };
  const onDone = () => { setShowModal(false); load(); };

  const toggleExpand = (id: string) => {
    setExpanded(prev => prev === id ? null : id);
  };

  const handleToggleActive = async (item: ProductType) => {
    if (!confirm(t('confirmDeactivate'))) return;
    await productTypesApi.update(item.id, { is_active: !item.is_active });
    load();
  };

  return (
    <div>
      {/* 標題 */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">{t('title')}</h1>
          <p className="text-sm text-gray-500 mt-0.5">{t('subtitle')}</p>
        </div>
        <button onClick={openCreate} className="btn-primary flex items-center gap-2">
          <Plus size={16} /> {t('addProductType')}
        </button>
      </div>

      {/* 列表 */}
      {loading ? (
        <div className="text-center py-16 text-gray-400">{tc('loading')}</div>
      ) : items.length === 0 ? (
        <div className="flex flex-col items-center py-20 text-gray-400">
          <Sprout size={40} className="mb-3 opacity-30" />
          <p>{t('noProductTypes')}</p>
        </div>
      ) : (
        <div className="space-y-3">
          {items.map(item => (
            <div key={item.id} className="card overflow-hidden">
              {/* 主資訊行 */}
              <div className="flex items-center gap-4 px-5 py-4">
                <div className="w-10 h-10 rounded-xl bg-green-100 flex items-center justify-center flex-shrink-0">
                  <Sprout size={18} className="text-green-600" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <p className="font-bold text-gray-800">{item.name_zh}</p>
                    {item.name_en && <span className="text-xs text-gray-400">({item.name_en})</span>}
                    <span className="px-2 py-0.5 rounded-full text-xs font-mono bg-gray-100 text-gray-600">
                      {item.code}
                    </span>
                  </div>
                  <div className="flex items-center gap-4 mt-1 text-xs text-gray-500">
                    <span className="flex items-center gap-1">
                      <Package size={12} /> {t('batchPrefix')}: <strong>{item.batch_prefix}</strong>
                    </span>
                    {item.shelf_life_days && (
                      <span className="flex items-center gap-1">
                        <Clock size={12} /> {item.shelf_life_days} {t('shelfLifeDays')}
                      </span>
                    )}
                    {item.storage_req?.temp_min != null && (
                      <span className="flex items-center gap-1">
                        <Thermometer size={12} /> {item.storage_req.temp_min}°C ~ {item.storage_req.temp_max}°C
                      </span>
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-1">
                  <button onClick={() => openEdit(item)} className="p-2 rounded-lg text-gray-400 hover:text-blue-600 hover:bg-blue-50">
                    <Pencil size={14} />
                  </button>
                  <button onClick={() => handleToggleActive(item)} className="p-2 rounded-lg text-gray-400 hover:text-orange-600 hover:bg-orange-50">
                    <Power size={14} />
                  </button>
                  <button onClick={() => toggleExpand(item.id)} className="p-2 rounded-lg text-gray-400 hover:text-gray-700 hover:bg-gray-100">
                    {expanded === item.id ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                  </button>
                </div>
              </div>

              {/* 展開區域 */}
              {expanded === item.id && (
                <div className="border-t border-gray-100 bg-gray-50 px-5 py-4">
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    {/* QC 檢查項目 */}
                    <div>
                      <p className="text-xs font-semibold text-gray-500 uppercase mb-2">{t('qualitySchema')}</p>
                      {item.quality_schema.length === 0 ? (
                        <p className="text-xs text-gray-400">—</p>
                      ) : (
                        <div className="space-y-1">
                          {(item.quality_schema as { field: string; label_zh: string; type: string }[]).map((q) => (
                            <div key={q.field} className="flex items-center gap-2 text-xs">
                              <span className="w-1.5 h-1.5 rounded-full bg-green-400" />
                              <span className="text-gray-700">{q.label_zh}</span>
                              <span className="text-gray-400">({q.type})</span>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>

                    {/* 尺寸分級 */}
                    <div>
                      <p className="text-xs font-semibold text-gray-500 uppercase mb-2">{t('sizeGrades')}</p>
                      {item.size_grades.length === 0 ? (
                        <p className="text-xs text-gray-400">—</p>
                      ) : (
                        <div className="flex flex-wrap gap-1">
                          {(item.size_grades as { grade: string; label_zh: string }[]).map((g) => (
                            <span key={g.grade} className="px-2 py-0.5 bg-white border border-gray-200 rounded-full text-xs text-gray-600">
                              {g.grade} · {g.label_zh}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>

                    {/* 加工步驟 */}
                    <div>
                      <p className="text-xs font-semibold text-gray-500 uppercase mb-2">{t('processingSteps')}</p>
                      {item.processing_steps.length === 0 ? (
                        <p className="text-xs text-gray-400">—</p>
                      ) : (
                        <div className="flex flex-wrap gap-1">
                          {item.processing_steps.map((step, i) => (
                            <span key={i} className="px-2 py-0.5 bg-blue-50 border border-blue-100 rounded-full text-xs text-blue-600">
                              {i + 1}. {step}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {showModal && (
        <ProductTypeModal
          item={editItem}
          onClose={() => setShowModal(false)}
          onDone={onDone}
        />
      )}
    </div>
  );
}
