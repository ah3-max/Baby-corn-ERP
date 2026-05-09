'use client';

/**
 * O-03 市場情報儀表板
 */
import { useTranslations } from 'next-intl';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api';
import { Globe, AlertTriangle, CloudRain } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import { clsx } from 'clsx';

export default function MarketIntelDashboard() {
  const t = useTranslations('dashboardMarket');

  const { data: priceData }      = useQuery({ queryKey: ['mi-prices'],        queryFn: async () => (await apiClient.get('/market-intel/prices',         { params: { limit: 30 } })).data });
  const { data: alertData }      = useQuery({ queryKey: ['mi-price-alerts'],  queryFn: async () => (await apiClient.get('/market-intel/price-alerts',    { params: { is_active: true, limit: 10 } })).data });
  const { data: competitorData } = useQuery({ queryKey: ['mi-competitors'],   queryFn: async () => (await apiClient.get('/market-intel/competitors',     { params: { limit: 10 } })).data });
  const { data: weatherData }    = useQuery({ queryKey: ['mi-weather'],       queryFn: async () => (await apiClient.get('/market-intel/weather-alerts',  { params: { is_active: true, limit: 5 } })).data });
  const { data: freightData }    = useQuery({ queryKey: ['mi-freight'],       queryFn: async () => (await apiClient.get('/market-intel/freight-index',   { params: { limit: 10 } })).data });
  const { data: sdData }         = useQuery({ queryKey: ['mi-supply-demand'], queryFn: async () => (await apiClient.get('/market-intel/supply-demand',   { params: { limit: 10 } })).data });

  const prices         = priceData?.items       ?? priceData       ?? [];
  const priceAlerts    = alertData?.items        ?? alertData        ?? [];
  const competitors    = competitorData?.items   ?? competitorData   ?? [];
  const weatherAlerts  = weatherData?.items      ?? weatherData      ?? [];
  const freightItems   = freightData?.items      ?? freightData      ?? [];
  const sdItems        = sdData?.items           ?? sdData           ?? [];

  const priceTrend = (Array.isArray(prices) ? prices : [])
    .slice(0, 20).reverse()
    .map((p: any) => ({
      date:  (p.price_date || p.recorded_at || '').slice(5, 10),
      price: Number(p.price || p.unit_price || 0),
    }));

  const latestByMarket: Record<string, any> = {};
  (Array.isArray(prices) ? prices : []).forEach((p: any) => {
    const k = p.market_name || p.source_name || 'unknown';
    if (!latestByMarket[k] || p.price_date > latestByMarket[k].price_date) latestByMarket[k] = p;
  });
  const latestPrices = Object.values(latestByMarket).slice(0, 5);
  const latestSD     = (Array.isArray(sdItems) ? sdItems : []).slice(0, 3);

  return (
    <div className="p-6 space-y-6 max-w-7xl">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
          <Globe className="text-violet-600" size={24} />
          {t('title')}
        </h1>
        <p className="text-sm text-gray-500 mt-1">{t('subtitle')}</p>
      </div>

      {/* 天氣告警橫幅 */}
      {(Array.isArray(weatherAlerts) ? weatherAlerts : []).length > 0 && (
        <div className="space-y-2">
          {(Array.isArray(weatherAlerts) ? weatherAlerts : []).map((w: any, i: number) => (
            <div key={i} className="flex items-center gap-3 px-4 py-3 bg-blue-50 border border-blue-200 rounded-xl text-sm text-blue-800">
              <CloudRain size={16} className="flex-shrink-0" />
              <span><strong>{w.affected_region || w.region}：</strong>{w.alert_description || w.description}</span>
              {w.severity && (
                <span className={clsx('ml-auto px-2 py-0.5 rounded text-xs font-medium',
                  w.severity === 'high' ? 'bg-red-100 text-red-700' : 'bg-yellow-100 text-yellow-700'
                )}>{w.severity}</span>
              )}
            </div>
          ))}
        </div>
      )}

      {/* 最新行情 */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {latestPrices.map((p: any, i: number) => (
          <div key={i} className="bg-white rounded-xl border p-4">
            <p className="text-xs text-gray-400 mb-1 truncate">{p.market_name || p.source_name}</p>
            <p className="text-2xl font-bold text-violet-700">{p.price} <span className="text-sm font-normal text-gray-400">{p.currency || 'TWD'}/{p.unit || 'kg'}</span></p>
            <p className="text-xs text-gray-400 mt-1">{p.price_date || p.recorded_at?.split('T')[0]}</p>
          </div>
        ))}
        {latestPrices.length === 0 && (
          <div className="col-span-4 bg-white rounded-xl border p-8 text-center text-gray-400 text-sm">{t('noPrices')}</div>
        )}
      </div>

      {/* 價格趨勢 + 競爭對手 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-xl border p-5">
          <h2 className="text-sm font-semibold text-gray-600 mb-4">{t('priceTrend')}</h2>
          {priceTrend.length > 0 ? (
            <ResponsiveContainer width="100%" height={200}>
              <LineChart data={priceTrend}>
                <XAxis dataKey="date" tick={{ fontSize: 10 }} />
                <YAxis tick={{ fontSize: 10 }} />
                <Tooltip />
                <Line type="monotone" dataKey="price" stroke="#7c3aed" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-48 flex items-center justify-center text-gray-300 text-sm">{t('priceTrendNoData')}</div>
          )}
        </div>

        <div className="bg-white rounded-xl border p-5">
          <h2 className="text-sm font-semibold text-gray-600 mb-4">{t('competitors')}</h2>
          {(Array.isArray(competitors) ? competitors : []).length === 0 ? (
            <p className="text-sm text-gray-400 text-center py-8">{t('competitorsNoData')}</p>
          ) : (
            <div className="space-y-2">
              {(Array.isArray(competitors) ? competitors : []).slice(0, 5).map((c: any) => (
                <div key={c.id} className="flex items-center justify-between py-2 border-b last:border-0">
                  <div>
                    <p className="text-sm font-medium text-gray-800">{c.company_name}</p>
                    <p className="text-xs text-gray-400">{c.country_code || '—'} · {c.market_segment || '—'}</p>
                  </div>
                  <div className="text-right">
                    {c.estimated_market_share_pct && (
                      <p className="text-sm font-bold text-violet-700">{c.estimated_market_share_pct}%</p>
                    )}
                    <p className="text-xs text-gray-400">{t('competitorShare')}</p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* 供需指標 + 運費指數 + 價格告警 */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="bg-white rounded-xl border p-5">
          <h2 className="text-sm font-semibold text-gray-600 mb-4">{t('supplyDemand')}</h2>
          {latestSD.length === 0 ? (
            <p className="text-sm text-gray-400 text-center py-6">{t('supplyDemandNoData')}</p>
          ) : (
            <div className="space-y-3">
              {latestSD.map((sd: any, i: number) => (
                <div key={i} className="bg-gray-50 rounded-lg p-3">
                  <div className="flex justify-between text-xs mb-1">
                    <span className="text-gray-600">{sd.product_name || sd.product_category}</span>
                    <span className={clsx('font-bold',
                      sd.supply_demand_ratio > 1 ? 'text-green-600' : sd.supply_demand_ratio < 0.8 ? 'text-red-600' : 'text-yellow-600'
                    )}>{t('supplyDemandRatio', { ratio: sd.supply_demand_ratio?.toFixed(2) || '—' })}</span>
                  </div>
                  <div className="flex gap-3 text-xs text-gray-400">
                    {sd.supply_volume && <span>{t('supplyLabel', { vol: sd.supply_volume?.toLocaleString() })}</span>}
                    {sd.demand_volume && <span>{t('demandLabel', { vol: sd.demand_volume?.toLocaleString() })}</span>}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="bg-white rounded-xl border p-5">
          <h2 className="text-sm font-semibold text-gray-600 mb-4">{t('freightIndex')}</h2>
          {(Array.isArray(freightItems) ? freightItems : []).length === 0 ? (
            <p className="text-sm text-gray-400 text-center py-6">{t('freightNoData')}</p>
          ) : (
            <div className="space-y-2">
              {(Array.isArray(freightItems) ? freightItems : []).slice(0, 4).map((f: any, i: number) => (
                <div key={i} className="flex items-center justify-between py-2 border-b last:border-0">
                  <div>
                    <p className="text-xs font-medium text-gray-800">{f.route_name || `${f.origin_port} → ${f.dest_port}`}</p>
                    <p className="text-xs text-gray-400">{f.index_date || f.recorded_date}</p>
                  </div>
                  <p className="text-sm font-bold text-gray-900">{f.index_value || f.freight_rate} <span className="text-xs font-normal text-gray-400">{f.currency || 'USD'}</span></p>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="bg-white rounded-xl border p-5">
          <h2 className="text-sm font-semibold text-gray-600 mb-4 flex items-center gap-2">
            <AlertTriangle size={14} /> {t('priceAlerts')}
          </h2>
          {(Array.isArray(priceAlerts) ? priceAlerts : []).length === 0 ? (
            <p className="text-sm text-gray-400 text-center py-6">{t('priceAlertsNoData')}</p>
          ) : (
            <div className="space-y-2">
              {(Array.isArray(priceAlerts) ? priceAlerts : []).slice(0, 4).map((a: any, i: number) => (
                <div key={i} className={clsx('p-3 rounded-lg border',
                  a.alert_type === 'high' ? 'bg-red-50 border-red-200' : 'bg-yellow-50 border-yellow-200'
                )}>
                  <p className="text-xs font-medium text-gray-800">{a.alert_name || a.market_name}</p>
                  <p className="text-xs text-gray-500">
                    {t('priceAlertDesc', { current: a.current_price, threshold: a.threshold_price, currency: a.currency })}
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
