'use client';

/**
 * P-08 Bloomberg 市場價格頁面
 */
import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api';
import {
  TrendingUp, TrendingDown, Minus, Plus, Bell, RefreshCw,
} from 'lucide-react';
import { clsx } from 'clsx';
import {
  ResponsiveContainer, LineChart, Line, XAxis, YAxis,
  CartesianGrid, Tooltip,
} from 'recharts';
import { useTranslations } from 'next-intl';

export default function MarketPricesPage() {
  const t = useTranslations('marketPrices');
  const [keyword, setKeyword] = useState('玉米筍');
  const [showAddForm, setShowAddForm] = useState(false);
  const [formData, setFormData] = useState({
    price_date: new Date().toISOString().split('T')[0],
    product_category: '玉米筍',
    market_name: '',
    country_code: 'TW',
    price_avg: '',
    price_low: '',
    price_high: '',
    price_currency: 'TWD',
    price_unit: '元/kg',
    price_trend: 'stable',
  });
  const qc = useQueryClient();

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['market-prices', keyword],
    queryFn: async () => {
      const res = await apiClient.get('/market/prices/', {
        params: { product_category: keyword, limit: 100 },
      });
      return res.data;
    },
  });

  const { data: alerts } = useQuery({
    queryKey: ['market-alerts'],
    queryFn: async () => {
      const res = await apiClient.get('/market/alerts/', { params: { unacknowledged_only: true } });
      return res.data;
    },
  });

  const { data: freight } = useQuery({
    queryKey: ['freight-index'],
    queryFn: async () => {
      const res = await apiClient.get('/market/freight/', { params: { limit: 20 } });
      return res.data;
    },
  });

  const addPrice = useMutation({
    mutationFn: (data: any) => apiClient.post('/market/prices/', data),
    onSuccess: () => {
      setShowAddForm(false);
      qc.invalidateQueries({ queryKey: ['market-prices'] });
    },
  });

  const prices = data?.items || [];
  const priceAlerts = alerts?.items || [];
  const freightList = freight?.items || [];

  // 整理為圖表數據
  const chartData = [...prices]
    .slice(0, 30)
    .reverse()
    .map((p: any) => ({
      date: p.price_date,
      avg: p.price_avg,
      low: p.price_low,
      high: p.price_high,
    }));

  return (
    <div className="p-6 space-y-6">
      {/* 頁頭 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <TrendingUp className="text-primary-600" size={24} />
            {t('title')}
          </h1>
          <p className="text-sm text-gray-500 mt-1">{t('subtitle')}</p>
        </div>
        <div className="flex items-center gap-2">
          {priceAlerts.length > 0 && (
            <div className="flex items-center gap-1.5 bg-red-50 border border-red-200 text-red-700 text-xs px-3 py-1.5 rounded-lg">
              <Bell size={13} />
              {t('alertsCount', { count: priceAlerts.length })}
            </div>
          )}
          <button
            onClick={() => setShowAddForm(!showAddForm)}
            className="flex items-center gap-1.5 px-4 py-2 bg-primary-600 text-white text-sm rounded-lg hover:bg-primary-700"
          >
            <Plus size={15} />
            {t('addBtn')}
          </button>
          <button onClick={() => refetch()} className="p-2 border rounded-lg hover:bg-gray-50">
            <RefreshCw size={15} />
          </button>
        </div>
      </div>

      {/* 新增表單 */}
      {showAddForm && (
        <div className="bg-white rounded-xl border p-5 space-y-4">
          <h3 className="font-semibold text-gray-900">{t('formTitle')}</h3>
          <div className="grid grid-cols-3 gap-4 text-sm">
            {[
              { key: 'price_date',       label: t('labelDate'),     type: 'date' },
              { key: 'product_category', label: t('labelCategory'), type: 'text' },
              { key: 'market_name',      label: t('labelMarket'),   type: 'text' },
              { key: 'country_code',     label: t('labelCountry'),  type: 'text' },
              { key: 'price_avg',        label: t('labelAvgPrice'), type: 'number' },
              { key: 'price_currency',   label: t('labelCurrency'), type: 'text' },
            ].map(({ key, label, type }) => (
              <div key={key}>
                <label className="block text-gray-600 mb-1">{label}</label>
                <input
                  type={type}
                  value={(formData as any)[key]}
                  onChange={e => setFormData(prev => ({ ...prev, [key]: e.target.value }))}
                  className="w-full border rounded-lg px-3 py-1.5 text-sm"
                />
              </div>
            ))}
          </div>
          <div className="flex gap-2 justify-end">
            <button onClick={() => setShowAddForm(false)} className="px-4 py-2 border rounded-lg text-sm">{t('cancelBtn')}</button>
            <button
              onClick={() => addPrice.mutate({
                ...formData,
                price_avg: Number(formData.price_avg),
              })}
              className="px-4 py-2 bg-primary-600 text-white rounded-lg text-sm hover:bg-primary-700"
            >
              {t('saveBtn')}
            </button>
          </div>
        </div>
      )}

      <div className="grid grid-cols-3 gap-6">
        {/* 價格趨勢圖 */}
        <div className="col-span-2 bg-white rounded-xl border p-5">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold text-gray-900">{t('trendTitle')}</h2>
            <input
              type="text"
              value={keyword}
              onChange={e => setKeyword(e.target.value)}
              className="border rounded-lg px-3 py-1 text-sm w-32"
              placeholder={t('searchPlaceholder')}
            />
          </div>
          {chartData.length > 0 ? (
            <ResponsiveContainer width="100%" height={220}>
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="date" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip />
                <Line type="monotone" dataKey="avg" name={t('lineAvg')} stroke="#6366f1" strokeWidth={2} dot={false} />
                <Line type="monotone" dataKey="high" name={t('lineHigh')} stroke="#10b981" strokeWidth={1} dot={false} strokeDasharray="4 2" />
                <Line type="monotone" dataKey="low"  name={t('lineLow')} stroke="#f59e0b" strokeWidth={1} dot={false} strokeDasharray="4 2" />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-52 flex items-center justify-center text-gray-400">{t('noData')}</div>
          )}
        </div>

        {/* 運價指數 */}
        <div className="bg-white rounded-xl border p-5">
          <h2 className="font-semibold text-gray-900 mb-3">{t('freightTitle')}</h2>
          <div className="space-y-3">
            {freightList.slice(0, 5).map((f: any) => (
              <div key={f.id} className="flex items-center justify-between py-2 border-b last:border-0">
                <div>
                  <p className="text-sm font-medium text-gray-900">{f.index_name}</p>
                  <p className="text-xs text-gray-400">{f.index_date}</p>
                </div>
                <div className="text-right">
                  <p className="text-sm font-bold text-gray-900">{f.index_value?.toFixed(0)}</p>
                  {f.wow_change_pct != null && (
                    <p className={clsx('text-xs flex items-center justify-end gap-0.5',
                      f.wow_change_pct > 0 ? 'text-red-500' : 'text-green-500'
                    )}>
                      {f.wow_change_pct > 0 ? <TrendingUp size={11} /> : <TrendingDown size={11} />}
                      {Math.abs(f.wow_change_pct).toFixed(1)}% WoW
                    </p>
                  )}
                </div>
              </div>
            ))}
            {freightList.length === 0 && (
              <p className="text-sm text-gray-400 py-4 text-center">{t('noFreight')}</p>
            )}
          </div>
        </div>
      </div>

      {/* 價格列表 */}
      <div className="bg-white rounded-xl border overflow-hidden">
        <div className="px-4 py-3 border-b bg-gray-50">
          <h2 className="font-semibold text-gray-900 text-sm">{t('recentTitle')}</h2>
        </div>
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
            <tr>
              <th className="px-4 py-2 text-left">{t('colDate')}</th>
              <th className="px-4 py-2 text-left">{t('colCategory')}</th>
              <th className="px-4 py-2 text-left">{t('colMarket')}</th>
              <th className="px-4 py-2 text-right">{t('colAvg')}</th>
              <th className="px-4 py-2 text-right">{t('colRange')}</th>
              <th className="px-4 py-2 text-left">{t('colTrend')}</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {isLoading ? (
              <tr><td colSpan={6} className="px-4 py-8 text-center text-gray-400">{t('loading')}</td></tr>
            ) : prices.slice(0, 20).map((p: any) => (
              <tr key={p.id} className="hover:bg-gray-50">
                <td className="px-4 py-2.5 text-gray-600">{p.price_date}</td>
                <td className="px-4 py-2.5 font-medium text-gray-900">{p.product_category}</td>
                <td className="px-4 py-2.5 text-gray-600">{p.market_name || '—'} {p.country_code && `(${p.country_code})`}</td>
                <td className="px-4 py-2.5 text-right font-mono text-gray-900">
                  {p.price_avg ? `${p.price_avg} ${p.price_currency}` : '—'}
                </td>
                <td className="px-4 py-2.5 text-right text-gray-500 text-xs">
                  {p.price_low ?? '—'} / {p.price_high ?? '—'}
                </td>
                <td className="px-4 py-2.5">
                  {p.price_trend === 'up' ? (
                    <TrendingUp size={14} className="text-red-500" />
                  ) : p.price_trend === 'down' ? (
                    <TrendingDown size={14} className="text-green-500" />
                  ) : (
                    <Minus size={14} className="text-gray-400" />
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
