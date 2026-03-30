'use client';

/**
 * 供應商管理列表頁 /suppliers
 */
import { useEffect, useState } from 'react';
import { useTranslations } from 'next-intl';
import { Plus, Pencil, Search, Phone, MapPin } from 'lucide-react';
import { suppliersApi } from '@/lib/api';
import { useToast } from '@/contexts/ToastContext';
import { useUser } from '@/contexts/UserContext';
import type { Supplier, SupplierType } from '@/types';
import SupplierDrawer from './SupplierDrawer';

// 類型對應的標籤顏色
const TYPE_COLORS: Record<SupplierType, string> = {
  farmer:    'bg-green-100 text-green-700',
  broker:    'bg-blue-100 text-blue-700',
  factory:   'bg-orange-100 text-orange-700',
  logistics: 'bg-purple-100 text-purple-700',
  customs:   'bg-yellow-100 text-yellow-700',
  packaging: 'bg-pink-100 text-pink-700',
};

export default function SuppliersPage() {
  const t  = useTranslations('suppliers');
  const tc = useTranslations('common');
  const { showToast } = useToast();
  const { hasPermission } = useUser();
  const canCreate = hasPermission('supplier', 'create');
  const canEdit   = hasPermission('supplier', 'edit');

  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [loading, setLoading]     = useState(true);
  const [keyword, setKeyword]     = useState('');
  const [typeFilter, setTypeFilter] = useState('');
  const [activeFilter, setActiveFilter] = useState<boolean | undefined>(true);
  const [drawerOpen, setDrawerOpen]   = useState(false);
  const [editing, setEditing]         = useState<Supplier | null>(null);

  const TYPES: SupplierType[] = ['farmer', 'broker', 'factory', 'logistics', 'customs', 'packaging'];

  const fetchSuppliers = async () => {
    setLoading(true);
    try {
      const { data } = await suppliersApi.list({
        supplier_type: typeFilter || undefined,
        keyword:       keyword || undefined,
        is_active:     activeFilter,
      });
      setSuppliers(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchSuppliers(); }, [typeFilter, activeFilter]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    fetchSuppliers();
  };

  const [togglingId, setTogglingId] = useState<string | null>(null);

  const handleToggleActive = async (s: Supplier) => {
    setTogglingId(s.id);
    try {
      await suppliersApi.update(s.id, { is_active: !s.is_active });
      showToast(s.is_active ? '供應商已關閉（不活躍）' : '供應商已開啟（活躍）', 'success');
      fetchSuppliers();
    } catch {
      showToast(tc('error'), 'error');
    } finally {
      setTogglingId(null);
    }
  };

  const handleDrawerClose = (refresh?: boolean) => {
    setDrawerOpen(false);
    setEditing(null);
    if (refresh) fetchSuppliers();
  };

  return (
    <div>
      {/* 頁首 */}
      <div className="flex items-center justify-between mb-5">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">{t('title')}</h1>
          <p className="text-sm text-gray-500 mt-0.5">{tc('total', { count: suppliers.length })}</p>
        </div>
        {canCreate && (
          <button onClick={() => { setEditing(null); setDrawerOpen(true); }}
            className="btn-primary flex items-center gap-2">
            <Plus size={16} /> {t('addSupplier')}
          </button>
        )}
      </div>

      {/* 篩選列 */}
      <div className="card p-4 mb-5 flex flex-wrap items-center gap-3">
        {/* 類型篩選 */}
        <select
          value={typeFilter}
          onChange={(e) => setTypeFilter(e.target.value)}
          className="input w-40"
        >
          <option value="">{t('filterAll')}</option>
          {TYPES.map((type) => (
            <option key={type} value={type}>{t(`types.${type}` as any)}</option>
          ))}
        </select>

        {/* 啟用狀態 */}
        <select
          value={activeFilter === undefined ? '' : String(activeFilter)}
          onChange={(e) => {
            const v = e.target.value;
            setActiveFilter(v === '' ? undefined : v === 'true');
          }}
          className="input w-36"
        >
          <option value="true">{t('filterActive')}</option>
          <option value="false">{t('filterInactive')}</option>
          <option value="">{t('allStatus')}</option>
        </select>

        {/* 關鍵字搜尋 */}
        <form onSubmit={handleSearch} className="flex gap-2 flex-1 min-w-[200px]">
          <div className="relative flex-1">
            <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <input
              value={keyword}
              onChange={(e) => setKeyword(e.target.value)}
              placeholder={t('searchPlaceholder')}
              className="input pl-9"
            />
          </div>
          <button type="submit" className="btn-secondary">{tc('search')}</button>
        </form>
      </div>

      {/* 供應商卡片列表 */}
      {loading ? (
        <div className="text-center py-16 text-gray-400">{tc('loading')}</div>
      ) : suppliers.length === 0 ? (
        <div className="text-center py-16 text-gray-400">{tc('noData')}</div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {suppliers.map((s) => (
            <div
              key={s.id}
              className={`card p-4 hover:shadow-md transition-all ${
                !s.is_active ? 'opacity-50 bg-gray-50' : ''
              }`}
            >
              {/* 卡片頭 */}
              <div className="flex items-start justify-between mb-3">
                <div className="flex-1 min-w-0">
                  <h3 className={`font-semibold truncate ${s.is_active ? 'text-gray-800' : 'text-gray-400'}`}>
                    {s.name}
                  </h3>
                  <span className={`inline-block mt-1 px-2 py-0.5 rounded-full text-xs font-medium ${TYPE_COLORS[s.supplier_type]}`}>
                    {t(`types.${s.supplier_type}` as any)}
                  </span>
                </div>
                {canEdit && (
                  <button
                    onClick={() => { setEditing(s); setDrawerOpen(true); }}
                    className="p-1.5 text-gray-400 hover:text-primary-600 hover:bg-primary-50 rounded transition-colors ml-2 flex-shrink-0"
                    title="編輯"
                  >
                    <Pencil size={14} />
                  </button>
                )}
              </div>

              {/* 卡片內容 */}
              <div className="space-y-1.5 text-sm text-gray-500">
                {s.contact_name && (
                  <div className="flex items-center gap-2">
                    <span className="text-gray-400 text-xs w-16 flex-shrink-0">{t('contact')}</span>
                    <span className="truncate">{s.contact_name}</span>
                  </div>
                )}
                {s.phone && (
                  <div className="flex items-center gap-2">
                    <Phone size={12} className="text-gray-400 flex-shrink-0" />
                    <span>{s.phone}</span>
                  </div>
                )}
                {s.region && (
                  <div className="flex items-center gap-2">
                    <MapPin size={12} className="text-gray-400 flex-shrink-0" />
                    <span className="truncate">{s.region}</span>
                  </div>
                )}
                {s.payment_terms && (
                  <div className="flex items-center gap-2">
                    <span className="text-gray-400 text-xs w-16 flex-shrink-0">{t('payment')}</span>
                    <span className="truncate">{s.payment_terms}</span>
                  </div>
                )}
              </div>

              {/* 活躍/不活躍 Toggle 開關 */}
              {canEdit && (
                <div className="mt-3 pt-3 border-t border-gray-100 flex items-center justify-between">
                  <span className={`text-xs font-medium ${s.is_active ? 'text-green-600' : 'text-gray-400'}`}>
                    {s.is_active ? '活躍' : '不活躍'}
                  </span>
                  <button
                    onClick={() => handleToggleActive(s)}
                    disabled={togglingId === s.id}
                    className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-1 ${
                      s.is_active ? 'bg-green-500' : 'bg-gray-300'
                    } ${togglingId === s.id ? 'opacity-50 cursor-wait' : 'cursor-pointer'}`}
                    title={s.is_active ? '點擊關閉（設為不活躍）' : '點擊開啟（設為活躍）'}
                  >
                    <span
                      className={`inline-block h-4 w-4 transform rounded-full bg-white shadow transition-transform ${
                        s.is_active ? 'translate-x-6' : 'translate-x-1'
                      }`}
                    />
                  </button>
                </div>
              )}
              {!canEdit && !s.is_active && (
                <div className="mt-3 pt-3 border-t border-gray-100">
                  <span className="text-xs text-gray-400 font-medium">不活躍</span>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* 新增/編輯 Drawer */}
      {drawerOpen && (
        <SupplierDrawer
          supplier={editing}
          onClose={handleDrawerClose}
        />
      )}
    </div>
  );
}
