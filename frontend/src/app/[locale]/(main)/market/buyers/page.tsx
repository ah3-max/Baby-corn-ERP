'use client';

/**
 * P-08 全球買家資料庫頁面
 */
import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api';
import { Globe, Plus, Search, Star } from 'lucide-react';
import { clsx } from 'clsx';
import { useTranslations } from 'next-intl';

const INTEREST_COLORS: Record<string, string> = {
  hot:  'bg-red-100 text-red-700',
  warm: 'bg-orange-100 text-orange-700',
  cold: 'bg-blue-100 text-blue-700',
  none: 'bg-gray-100 text-gray-500',
};

export default function GlobalBuyersPage() {
  const t = useTranslations('marketBuyers');
  const [keyword, setKeyword] = useState('');
  const [country, setCountry] = useState('');
  const [interest, setInterest] = useState('');
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({
    company_name: '',
    country_code: '',
    city: '',
    business_type: 'importer',
    contact_name: '',
    contact_email: '',
    interest_level: 'cold',
    data_source: 'trade_show',
    notes: '',
  });
  const qc = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ['global-buyers', keyword, country, interest],
    queryFn: async () => {
      const res = await apiClient.get('/market/buyers/', {
        params: {
          keyword: keyword || undefined,
          country_code: country || undefined,
          interest_level: interest || undefined,
        },
      });
      return res.data;
    },
  });

  const addBuyer = useMutation({
    mutationFn: (data: any) => apiClient.post('/market/buyers/', data),
    onSuccess: () => {
      setShowForm(false);
      qc.invalidateQueries({ queryKey: ['global-buyers'] });
    },
  });

  const buyers = data?.items || [];
  const total = data?.total || 0;

  return (
    <div className="p-6 space-y-6">
      {/* 頁頭 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <Globe className="text-primary-600" size={24} />
            {t('title')}
          </h1>
          <p className="text-sm text-gray-500 mt-1">{t('subtitle', { total })}</p>
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
              { key: 'company_name',  label: t('labelCompany'),  required: true },
              { key: 'country_code',  label: t('labelCountry') },
              { key: 'city',          label: t('labelCity') },
              { key: 'contact_name',  label: t('labelContact') },
              { key: 'contact_email', label: t('labelEmail') },
            ].map(({ key, label, required }) => (
              <div key={key}>
                <label className="block text-gray-600 mb-1">
                  {label}{required && <span className="text-red-500 ml-0.5">*</span>}
                </label>
                <input
                  type="text"
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
                {['importer','distributor','retailer','processor','foodservice','trader'].map(v => (
                  <option key={v} value={v}>{v}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-gray-600 mb-1">{t('labelInterest')}</label>
              <select
                value={form.interest_level}
                onChange={e => setForm(prev => ({ ...prev, interest_level: e.target.value }))}
                className="w-full border rounded-lg px-3 py-1.5 text-sm"
              >
                {['hot','warm','cold','none'].map(v => (
                  <option key={v} value={v}>{t(`interest.${v}` as any)}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-gray-600 mb-1">{t('labelSource')}</label>
              <select
                value={form.data_source}
                onChange={e => setForm(prev => ({ ...prev, data_source: e.target.value }))}
                className="w-full border rounded-lg px-3 py-1.5 text-sm"
              >
                {['trade_show','directory','referral','web_scraping','cold_outreach','other'].map(v => (
                  <option key={v} value={v}>{v}</option>
                ))}
              </select>
            </div>
          </div>
          <div>
            <label className="block text-gray-600 mb-1 text-sm">{t('labelNotes')}</label>
            <textarea
              value={form.notes}
              onChange={e => setForm(prev => ({ ...prev, notes: e.target.value }))}
              className="w-full border rounded-lg px-3 py-2 text-sm h-20"
            />
          </div>
          <div className="flex gap-2 justify-end">
            <button onClick={() => setShowForm(false)} className="px-4 py-2 border rounded-lg text-sm">{t('cancelBtn')}</button>
            <button
              onClick={() => addBuyer.mutate(form)}
              disabled={!form.company_name}
              className="px-4 py-2 bg-primary-600 text-white rounded-lg text-sm hover:bg-primary-700 disabled:opacity-50"
            >
              {t('saveBtn')}
            </button>
          </div>
        </div>
      )}

      {/* 搜尋過濾 */}
      <div className="flex gap-3">
        <div className="relative flex-1 max-w-xs">
          <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            value={keyword}
            onChange={e => setKeyword(e.target.value)}
            placeholder={t('searchPlaceholder')}
            className="w-full pl-9 pr-4 py-2 border rounded-lg text-sm"
          />
        </div>
        <input
          type="text"
          value={country}
          onChange={e => setCountry(e.target.value)}
          placeholder={t('countryPlaceholder')}
          className="border rounded-lg px-3 py-2 text-sm w-40"
        />
        <select
          value={interest}
          onChange={e => setInterest(e.target.value)}
          className="border rounded-lg px-3 py-2 text-sm"
        >
          <option value="">{t('filterAllInterest')}</option>
          {['hot','warm','cold'].map(v => (
            <option key={v} value={v}>{t(`interest.${v}` as any)}</option>
          ))}
        </select>
      </div>

      {/* 買家卡片網格 */}
      <div className="grid grid-cols-3 gap-4">
        {isLoading ? (
          Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="bg-white rounded-xl border p-4 animate-pulse h-36" />
          ))
        ) : buyers.length === 0 ? (
          <div className="col-span-3 text-center py-12 text-gray-400">{t('noData')}</div>
        ) : buyers.map((buyer: any) => (
          <div key={buyer.id} className="bg-white rounded-xl border p-4 hover:shadow-md transition-shadow">
            <div className="flex items-start justify-between mb-2">
              <h3 className="font-semibold text-gray-900 text-sm leading-snug">{buyer.company_name}</h3>
              <span className={clsx('px-1.5 py-0.5 rounded text-xs font-medium flex-shrink-0 ml-2',
                INTEREST_COLORS[buyer.interest_level || 'cold']
              )}>
                {t(`interest.${buyer.interest_level || 'cold'}` as any)}
              </span>
            </div>
            <div className="space-y-1 text-xs text-gray-500">
              {(buyer.country_code || buyer.city) && (
                <p className="flex items-center gap-1">
                  <Globe size={11} />
                  {[buyer.city, buyer.country_code].filter(Boolean).join(', ')}
                </p>
              )}
              {buyer.business_type && (
                <p className="capitalize">{buyer.business_type}</p>
              )}
              {buyer.contact_name && (
                <p>{t('contactLabel')}{buyer.contact_name}</p>
              )}
              {buyer.contact_email && (
                <p className="truncate text-primary-600">{buyer.contact_email}</p>
              )}
              {buyer.last_contacted_date && (
                <p className="text-gray-400">{t('lastContacted')}{buyer.last_contacted_date}</p>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
