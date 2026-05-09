'use client';

/**
 * P-08 競爭對手分析頁面
 */
import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api';
import { BarChart2, Plus, Search, Globe, TrendingDown, TrendingUp } from 'lucide-react';
import { clsx } from 'clsx';
import { useTranslations } from 'next-intl';

export default function CompetitorsPage() {
  const t = useTranslations('marketCompetitors');
  const [keyword, setKeyword] = useState('');
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({
    company_name: '',
    country_code: '',
    business_type: 'trader',
    key_products: '',
    annual_revenue_estimate: '',
    notes: '',
  });
  const qc = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ['competitors', keyword],
    queryFn: async () => {
      const res = await apiClient.get('/market/competitors/', {
        params: { keyword: keyword || undefined },
      });
      return res.data;
    },
  });

  const { data: priceData } = useQuery({
    queryKey: ['competitor-prices'],
    queryFn: async () => {
      const res = await apiClient.get('/market/competitor-prices/', { params: { limit: 20 } });
      return res.data;
    },
  });

  const addCompetitor = useMutation({
    mutationFn: (d: any) => apiClient.post('/market/competitors/', d),
    onSuccess: () => {
      setShowForm(false);
      qc.invalidateQueries({ queryKey: ['competitors'] });
    },
  });

  const competitors = data?.items || [];
  const prices = priceData?.items || [];

  /* 業務類型選項鍵值 */
  const BTYPE_KEYS = ['farmer', 'processor', 'exporter', 'trader', 'cooperative', 'other'];

  return (
    <div className="p-6 space-y-6">
      {/* 頁頭 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <BarChart2 className="text-primary-600" size={24} />
            {t('title')}
          </h1>
          <p className="text-sm text-gray-500 mt-1">{t('subtitle')}</p>
        </div>
        <button
          onClick={() => setShowForm(!showForm)}
          className="flex items-center gap-1.5 px-4 py-2 bg-primary-600 text-white text-sm rounded-lg hover:bg-primary-700"
        >
          <Plus size={15} />
          {t('addBtn')}
        </button>
      </div>

      {/* 新增表單 */}
      {showForm && (
        <div className="bg-white rounded-xl border p-5 space-y-4">
          <h3 className="font-semibold text-gray-900">{t('formTitle')}</h3>
          <div className="grid grid-cols-3 gap-4 text-sm">
            {[
              { key: 'company_name',            label: t('labelCompany'),  required: true },
              { key: 'country_code',             label: t('labelCountry') },
              { key: 'key_products',             label: t('labelProducts') },
              { key: 'annual_revenue_estimate',  label: t('labelRevenue'), type: 'number' },
            ].map(({ key, label, required, type }) => (
              <div key={key}>
                <label className="block text-gray-600 mb-1">
                  {label}{required && <span className="text-red-500 ml-0.5">*</span>}
                </label>
                <input
                  type={type || 'text'}
                  value={(form as any)[key]}
                  onChange={e => setForm(prev => ({ ...prev, [key]: e.target.value }))}
                  className="w-full border rounded-lg px-3 py-1.5 text-sm"
                />
              </div>
            ))}
            <div>
              <label className="block text-gray-600 mb-1">{t('labelBizType')}</label>
              <select
                value={form.business_type}
                onChange={e => setForm(prev => ({ ...prev, business_type: e.target.value }))}
                className="w-full border rounded-lg px-3 py-1.5 text-sm"
              >
                {BTYPE_KEYS.map(k => (
                  <option key={k} value={k}>{t(`bizType.${k}` as any)}</option>
                ))}
              </select>
            </div>
          </div>
          <div>
            <label className="block text-gray-600 mb-1 text-sm">{t('labelNotes')}</label>
            <textarea
              value={form.notes}
              onChange={e => setForm(prev => ({ ...prev, notes: e.target.value }))}
              className="w-full border rounded-lg px-3 py-2 text-sm h-16"
            />
          </div>
          <div className="flex gap-2 justify-end">
            <button onClick={() => setShowForm(false)} className="px-4 py-2 border rounded-lg text-sm">{t('cancelBtn')}</button>
            <button
              onClick={() => addCompetitor.mutate({
                ...form,
                annual_revenue_estimate: form.annual_revenue_estimate
                  ? Number(form.annual_revenue_estimate)
                  : undefined,
              })}
              disabled={!form.company_name}
              className="px-4 py-2 bg-primary-600 text-white rounded-lg text-sm hover:bg-primary-700 disabled:opacity-50"
            >
              {t('saveBtn')}
            </button>
          </div>
        </div>
      )}

      {/* 搜尋 */}
      <div className="relative max-w-xs">
        <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
        <input
          type="text"
          value={keyword}
          onChange={e => setKeyword(e.target.value)}
          placeholder={t('searchPlaceholder')}
          className="w-full pl-9 pr-4 py-2 border rounded-lg text-sm"
        />
      </div>

      <div className="grid grid-cols-3 gap-6">
        {/* 競業列表 */}
        <div className="col-span-2 space-y-3">
          <h2 className="font-semibold text-gray-900 text-sm">{t('listTitle')}</h2>
          {isLoading ? (
            Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="bg-white rounded-xl border p-4 animate-pulse h-20" />
            ))
          ) : competitors.length === 0 ? (
            <div className="bg-white rounded-xl border p-8 text-center text-gray-400">{t('noCompetitors')}</div>
          ) : (
            competitors.map((c: any) => (
              <div key={c.id} className="bg-white rounded-xl border p-4 hover:shadow-sm transition-shadow">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <h3 className="font-semibold text-gray-900">{c.company_name}</h3>
                      <span className="px-2 py-0.5 bg-gray-100 text-gray-600 rounded text-xs">
                        {t(`bizType.${c.business_type}` as any, { defaultValue: c.business_type })}
                      </span>
                    </div>
                    <div className="flex items-center gap-4 mt-1 text-xs text-gray-500">
                      {c.country_code && (
                        <span className="flex items-center gap-1">
                          <Globe size={11} />
                          {c.country_code}
                        </span>
                      )}
                      {c.key_products && <span>{t('keyProducts')}{c.key_products}</span>}
                      {c.annual_revenue_estimate && (
                        <span>{t('annualRevenue', { amount: Number(c.annual_revenue_estimate).toLocaleString() })}</span>
                      )}
                    </div>
                    {c.notes && <p className="text-xs text-gray-400 mt-1 truncate">{c.notes}</p>}
                  </div>
                </div>
              </div>
            ))
          )}
        </div>

        {/* 競品報價記錄 */}
        <div className="bg-white rounded-xl border p-5">
          <h2 className="font-semibold text-gray-900 mb-3 text-sm">{t('priceTitle')}</h2>
          <div className="space-y-3">
            {prices.length === 0 ? (
              <p className="text-sm text-gray-400 py-4 text-center">{t('noPrices')}</p>
            ) : prices.slice(0, 8).map((p: any) => (
              <div key={p.id} className="border-b last:border-0 pb-2 last:pb-0">
                <div className="flex items-center justify-between">
                  <p className="text-sm font-medium text-gray-900 truncate flex-1 pr-2">
                    {p.competitor_name || '競業'}
                  </p>
                  <p className="text-sm font-bold text-gray-900">
                    {p.price_per_kg ? `$${p.price_per_kg}/kg` : '—'}
                  </p>
                </div>
                <div className="flex items-center justify-between mt-0.5">
                  <p className="text-xs text-gray-400">{p.product_name || '玉米筍'} · {p.observation_date}</p>
                  <p className="text-xs text-gray-500">{p.currency || 'TWD'}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
