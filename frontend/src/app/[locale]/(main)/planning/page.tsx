'use client';

/**
 * 計劃管理 — 採購計劃 + 天氣 + 財務計劃
 */
import { useEffect, useState } from 'react';
import { CalendarRange, Cloud, DollarSign, TrendingUp, Plus, X } from 'lucide-react';
import { planningApi } from '@/lib/api';
import { useToast } from '@/contexts/ToastContext';
import { useTranslations } from 'next-intl';

export default function PlanningPage() {
  const t = useTranslations('planning');
  const { showToast } = useToast();
  const [tab, setTab] = useState<'procurement' | 'weather' | 'financial'>('procurement');
  const [procPlans, setProcPlans] = useState<any[]>([]);
  const [weather, setWeather] = useState<any[]>([]);
  const [finPlans, setFinPlans] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);

  const STATUS_COLORS: Record<string, string> = {
    draft: 'bg-gray-100 text-gray-600', approved: 'bg-blue-100 text-blue-700',
    in_progress: 'bg-orange-100 text-orange-700', completed: 'bg-green-100 text-green-700',
  };
  const WEATHER_ICONS: Record<string, string> = {
    sunny: '☀️', cloudy: '⛅', rainy: '🌧️', storm: '⛈️', flood: '🌊',
  };
  const IMPACT_COLORS: Record<string, string> = {
    none: 'text-green-600', low: 'text-yellow-600', medium: 'text-orange-600', high: 'text-red-600',
  };

  useEffect(() => {
    setLoading(true);
    const load = async () => {
      try {
        if (tab === 'procurement') {
          const { data } = await planningApi.listProcurement({});
          setProcPlans(data);
        } else if (tab === 'weather') {
          const { data } = await planningApi.listWeather({});
          setWeather(data);
        } else {
          const { data } = await planningApi.listFinancialPlans({});
          setFinPlans(data);
        }
      } catch (e) { console.error(e); }
      finally { setLoading(false); }
    };
    load();
  }, [tab]);

  return (
    <div>
      <div className="flex items-center justify-between mb-5">
        <h1 className="text-2xl font-bold text-gray-800">{t('title')}</h1>
        <button onClick={() => setShowCreate(true)} className="btn-primary flex items-center gap-2">
          <Plus size={16} /> {tab === 'procurement' ? t('addProcBtn') : tab === 'weather' ? t('addWeatherBtn') : t('addFinBtn')}
        </button>
      </div>

      <div className="flex gap-1 mb-5 bg-gray-100 p-1 rounded-lg w-fit">
        {[
          { key: 'procurement', label: t('tabProcurement'), icon: CalendarRange },
          { key: 'weather', label: t('tabWeather'), icon: Cloud },
          { key: 'financial', label: t('tabFinancial'), icon: DollarSign },
        ].map(item => (
          <button key={item.key} onClick={() => setTab(item.key as any)}
            className={`flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium ${tab === item.key ? 'bg-white shadow-sm text-gray-800' : 'text-gray-500'}`}>
            <item.icon size={15} /> {item.label}
          </button>
        ))}
      </div>

      {loading ? <div className="text-center py-16 text-gray-400">{t('loading')}</div> : (
        <>
          {tab === 'procurement' && (
            <div className="space-y-3">
              {procPlans.length === 0 ? <p className="text-gray-400 text-center py-10">{t('noProcPlans')}</p> : procPlans.map((p: any) => (
                <div key={p.id} className="card p-4">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-3">
                      <span className="font-mono text-sm font-medium text-gray-700">{p.plan_no}</span>
                      <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_COLORS[p.status]}`}>
                        {t(`status.${p.status}` as any, { defaultValue: p.status })}
                      </span>
                    </div>
                    <span className="text-sm text-gray-500">{p.plan_month}</span>
                  </div>
                  <div className="flex items-center gap-6 text-sm text-gray-600">
                    {p.target_quantity_kg && <span>{t('procTarget')}{p.target_quantity_kg} kg</span>}
                    {p.target_budget_thb && <span>{t('procBudget')}฿{Math.round(p.target_budget_thb).toLocaleString()}</span>}
                    {p.actual_quantity_kg > 0 && <span className="text-green-600">{t('procActual')}{p.actual_quantity_kg} kg</span>}
                  </div>
                  {p.weather_risk_note && <p className="mt-2 text-xs text-orange-600">{t('weatherRisk')}{p.weather_risk_note}</p>}
                  {p.items && p.items.length > 0 && (
                    <div className="mt-3 text-xs text-gray-500">
                      {t('procItems', { count: p.items.length, weeks: p.items.map((i: any) => `W${i.week_number}`).join(', ') })}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}

          {tab === 'weather' && (
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
              {weather.length === 0 ? <p className="text-gray-400 text-center py-10 col-span-3">{t('noWeather')}</p> : weather.map((w: any) => (
                <div key={w.id} className="card p-4">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-2xl">{WEATHER_ICONS[w.condition] || '🌤️'}</span>
                    <span className="text-sm text-gray-500">{w.forecast_date}</span>
                  </div>
                  <p className="font-medium text-gray-800">{w.region}</p>
                  <div className="flex items-center gap-4 text-sm text-gray-600 mt-1">
                    {w.temperature_high && <span>{w.temperature_low}°~{w.temperature_high}°C</span>}
                    {w.rainfall_mm && <span>{w.rainfall_mm}mm</span>}
                  </div>
                  {w.impact_level && w.impact_level !== 'none' && (
                    <p className={`mt-2 text-xs font-medium ${IMPACT_COLORS[w.impact_level]}`}>
                      {t('impactLabel')}{w.impact_level} {w.impact_note ? `— ${w.impact_note}` : ''}
                    </p>
                  )}
                </div>
              ))}
            </div>
          )}

          {tab === 'financial' && (
            <div className="space-y-3">
              {finPlans.length === 0 ? <p className="text-gray-400 text-center py-10">{t('noFinPlans')}</p> : finPlans.map((fp: any) => (
                <div key={fp.id} className="card p-4">
                  <div className="flex items-center justify-between mb-3">
                    <span className="font-medium text-gray-800">{fp.plan_month}</span>
                    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_COLORS[fp.status]}`}>
                      {t(`status.${fp.status}` as any, { defaultValue: fp.status })}
                    </span>
                  </div>
                  <div className="grid grid-cols-3 gap-4 text-sm">
                    <div>
                      <p className="text-xs text-gray-400">{t('finPlannedRevenue')}</p>
                      <p className="font-semibold">NT${Math.round(fp.planned_revenue_twd || 0).toLocaleString()}</p>
                    </div>
                    <div>
                      <p className="text-xs text-gray-400">{t('finPlannedProfit')}</p>
                      <p className="font-semibold">NT${Math.round(fp.planned_gross_profit_twd || 0).toLocaleString()}</p>
                    </div>
                    <div>
                      <p className="text-xs text-gray-400">{t('finActualRevenue')}</p>
                      <p className="font-semibold text-green-600">NT${Math.round(fp.actual_revenue_twd || 0).toLocaleString()}</p>
                      {fp.variance_pct != null && (
                        <span className={`text-xs ${fp.variance_pct >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                          {fp.variance_pct >= 0 ? '+' : ''}{fp.variance_pct}%
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </>
      )}

      {/* 新增 Modal */}
      {showCreate && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-md p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-bold text-gray-800">
                {tab === 'procurement' ? t('modalCreateProc') : tab === 'weather' ? t('modalCreateWeather') : t('modalCreateFin')}
              </h3>
              <button onClick={() => setShowCreate(false)}><X size={18} className="text-gray-400" /></button>
            </div>
            <form onSubmit={async (e) => {
              e.preventDefault();
              const fd = new FormData(e.currentTarget);
              try {
                if (tab === 'procurement') {
                  await planningApi.createProcurement({
                    plan_month: fd.get('plan_month') + '-01',
                    target_quantity_kg: Number(fd.get('target_quantity_kg')) || undefined,
                    target_budget_thb: Number(fd.get('target_budget_thb')) || undefined,
                    weather_risk_note: fd.get('weather_risk_note') || undefined,
                  });
                  const { data } = await planningApi.listProcurement({});
                  setProcPlans(data);
                } else if (tab === 'weather') {
                  await planningApi.createWeather({
                    forecast_date: fd.get('forecast_date'),
                    region: fd.get('region'),
                    condition: fd.get('condition'),
                    temperature_high: Number(fd.get('temperature_high')) || undefined,
                    temperature_low: Number(fd.get('temperature_low')) || undefined,
                    rainfall_mm: Number(fd.get('rainfall_mm')) || undefined,
                    impact_level: fd.get('impact_level') || undefined,
                  });
                  const { data } = await planningApi.listWeather({});
                  setWeather(data);
                } else {
                  await planningApi.createFinancialPlan({
                    plan_month: fd.get('plan_month') + '-01',
                    planned_revenue_twd: Number(fd.get('planned_revenue_twd')) || undefined,
                    planned_cogs_twd: Number(fd.get('planned_cogs_twd')) || undefined,
                    planned_gross_profit_twd: Number(fd.get('planned_gross_profit_twd')) || undefined,
                  });
                  const { data } = await planningApi.listFinancialPlans({});
                  setFinPlans(data);
                }
                setShowCreate(false);
                showToast(t('toastCreated'), 'success');
              } catch { showToast(t('toastFailed'), 'error'); }
            }} className="space-y-3">
              {tab === 'procurement' && (
                <>
                  <div><label className="text-xs font-medium text-gray-600 block mb-1">{t('labelPlanMonth')} *</label><input name="plan_month" type="month" required className="input w-full" /></div>
                  <div><label className="text-xs font-medium text-gray-600 block mb-1">{t('labelTargetQty')}</label><input name="target_quantity_kg" type="number" className="input w-full" /></div>
                  <div><label className="text-xs font-medium text-gray-600 block mb-1">{t('labelBudgetThb')}</label><input name="target_budget_thb" type="number" className="input w-full" /></div>
                  <div><label className="text-xs font-medium text-gray-600 block mb-1">{t('labelWeatherRiskNote')}</label><textarea name="weather_risk_note" className="input w-full h-16 resize-none" /></div>
                </>
              )}
              {tab === 'weather' && (
                <>
                  <div><label className="text-xs font-medium text-gray-600 block mb-1">{t('labelDate')} *</label><input name="forecast_date" type="date" required className="input w-full" /></div>
                  <div><label className="text-xs font-medium text-gray-600 block mb-1">{t('labelRegion')} *</label>
                    <select name="region" required className="input w-full">
                      <option value="nakhon_pathom">Nakhon Pathom</option>
                      <option value="kanchanaburi">Kanchanaburi</option>
                      <option value="ratchaburi">Ratchaburi</option>
                      <option value="other">{t('weatherOther')}</option>
                    </select>
                  </div>
                  <div><label className="text-xs font-medium text-gray-600 block mb-1">{t('labelCondition')} *</label>
                    <select name="condition" required className="input w-full">
                      {['sunny','cloudy','rainy','storm','flood'].map(c => <option key={c} value={c}>{c}</option>)}
                    </select>
                  </div>
                  <div className="grid grid-cols-3 gap-2">
                    <div><label className="text-xs text-gray-500 block">{t('labelTempHigh')}</label><input name="temperature_high" type="number" step="0.1" className="input w-full" /></div>
                    <div><label className="text-xs text-gray-500 block">{t('labelTempLow')}</label><input name="temperature_low" type="number" step="0.1" className="input w-full" /></div>
                    <div><label className="text-xs text-gray-500 block">{t('labelRainfallMm')}</label><input name="rainfall_mm" type="number" className="input w-full" /></div>
                  </div>
                  <div><label className="text-xs font-medium text-gray-600 block mb-1">{t('labelImpactLevel')}</label>
                    <select name="impact_level" className="input w-full">
                      <option value="none">{t('impactNone')}</option>
                      <option value="low">{t('impactLow')}</option>
                      <option value="medium">{t('impactMedium')}</option>
                      <option value="high">{t('impactHigh')}</option>
                    </select>
                  </div>
                </>
              )}
              {tab === 'financial' && (
                <>
                  <div><label className="text-xs font-medium text-gray-600 block mb-1">{t('labelPlanMonth')} *</label><input name="plan_month" type="month" required className="input w-full" /></div>
                  <div><label className="text-xs font-medium text-gray-600 block mb-1">{t('labelPlannedRevenue')}</label><input name="planned_revenue_twd" type="number" className="input w-full" /></div>
                  <div><label className="text-xs font-medium text-gray-600 block mb-1">{t('labelPlannedCogs')}</label><input name="planned_cogs_twd" type="number" className="input w-full" /></div>
                  <div><label className="text-xs font-medium text-gray-600 block mb-1">{t('labelPlannedProfit')}</label><input name="planned_gross_profit_twd" type="number" className="input w-full" /></div>
                </>
              )}
              <div className="flex gap-2 mt-4">
                <button type="button" onClick={() => setShowCreate(false)} className="btn-secondary flex-1">{t('cancelBtn')}</button>
                <button type="submit" className="btn-primary flex-1">{t('createBtn')}</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
