'use client';

/**
 * 計劃管理 — 採購計劃 + 天氣 + 財務計劃
 */
import { useEffect, useState } from 'react';
import { CalendarRange, Cloud, DollarSign, TrendingUp, Plus, X } from 'lucide-react';
import { planningApi } from '@/lib/api';
import { useToast } from '@/contexts/ToastContext';

export default function PlanningPage() {
  const { showToast } = useToast();
  const [tab, setTab] = useState<'procurement' | 'weather' | 'financial'>('procurement');
  const [procPlans, setProcPlans] = useState<any[]>([]);
  const [weather, setWeather] = useState<any[]>([]);
  const [finPlans, setFinPlans] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);

  const STATUS_LABELS: Record<string, string> = {
    draft: '草稿', approved: '已核准', in_progress: '執行中', completed: '已完成',
  };
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
        <h1 className="text-2xl font-bold text-gray-800">計劃管理</h1>
        <button onClick={() => setShowCreate(true)} className="btn-primary flex items-center gap-2">
          <Plus size={16} /> {tab === 'procurement' ? '新增採購計劃' : tab === 'weather' ? '新增天氣' : '新增財務計劃'}
        </button>
      </div>

      <div className="flex gap-1 mb-5 bg-gray-100 p-1 rounded-lg w-fit">
        {[
          { key: 'procurement', label: '採購計劃', icon: CalendarRange },
          { key: 'weather', label: '天氣預報', icon: Cloud },
          { key: 'financial', label: '財務計劃', icon: DollarSign },
        ].map(t => (
          <button key={t.key} onClick={() => setTab(t.key as any)}
            className={`flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium ${tab === t.key ? 'bg-white shadow-sm text-gray-800' : 'text-gray-500'}`}>
            <t.icon size={15} /> {t.label}
          </button>
        ))}
      </div>

      {loading ? <div className="text-center py-16 text-gray-400">載入中...</div> : (
        <>
          {tab === 'procurement' && (
            <div className="space-y-3">
              {procPlans.length === 0 ? <p className="text-gray-400 text-center py-10">尚無採購計劃</p> : procPlans.map((p: any) => (
                <div key={p.id} className="card p-4">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-3">
                      <span className="font-mono text-sm font-medium text-gray-700">{p.plan_no}</span>
                      <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_COLORS[p.status]}`}>
                        {STATUS_LABELS[p.status]}
                      </span>
                    </div>
                    <span className="text-sm text-gray-500">{p.plan_month}</span>
                  </div>
                  <div className="flex items-center gap-6 text-sm text-gray-600">
                    {p.target_quantity_kg && <span>目標：{p.target_quantity_kg} kg</span>}
                    {p.target_budget_thb && <span>預算：฿{Math.round(p.target_budget_thb).toLocaleString()}</span>}
                    {p.actual_quantity_kg > 0 && <span className="text-green-600">實際：{p.actual_quantity_kg} kg</span>}
                  </div>
                  {p.weather_risk_note && <p className="mt-2 text-xs text-orange-600">天氣風險：{p.weather_risk_note}</p>}
                  {p.items && p.items.length > 0 && (
                    <div className="mt-3 text-xs text-gray-500">
                      {p.items.length} 筆明細（{p.items.map((i: any) => `W${i.week_number}`).join(', ')}）
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}

          {tab === 'weather' && (
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
              {weather.length === 0 ? <p className="text-gray-400 text-center py-10 col-span-3">尚無天氣資料</p> : weather.map((w: any) => (
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
                      影響程度：{w.impact_level} {w.impact_note ? `— ${w.impact_note}` : ''}
                    </p>
                  )}
                </div>
              ))}
            </div>
          )}

          {tab === 'financial' && (
            <div className="space-y-3">
              {finPlans.length === 0 ? <p className="text-gray-400 text-center py-10">尚無財務計劃</p> : finPlans.map((fp: any) => (
                <div key={fp.id} className="card p-4">
                  <div className="flex items-center justify-between mb-3">
                    <span className="font-medium text-gray-800">{fp.plan_month}</span>
                    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_COLORS[fp.status]}`}>
                      {STATUS_LABELS[fp.status] || fp.status}
                    </span>
                  </div>
                  <div className="grid grid-cols-3 gap-4 text-sm">
                    <div>
                      <p className="text-xs text-gray-400">計劃營收</p>
                      <p className="font-semibold">NT${Math.round(fp.planned_revenue_twd || 0).toLocaleString()}</p>
                    </div>
                    <div>
                      <p className="text-xs text-gray-400">計劃毛利</p>
                      <p className="font-semibold">NT${Math.round(fp.planned_gross_profit_twd || 0).toLocaleString()}</p>
                    </div>
                    <div>
                      <p className="text-xs text-gray-400">實際營收</p>
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
                {tab === 'procurement' ? '新增採購計劃' : tab === 'weather' ? '新增天氣記錄' : '新增財務計劃'}
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
                showToast('建立成功', 'success');
              } catch { showToast('建立失敗', 'error'); }
            }} className="space-y-3">
              {tab === 'procurement' && (
                <>
                  <div><label className="text-xs font-medium text-gray-600 block mb-1">計劃月份 *</label><input name="plan_month" type="month" required className="input w-full" /></div>
                  <div><label className="text-xs font-medium text-gray-600 block mb-1">目標採購量 (kg)</label><input name="target_quantity_kg" type="number" className="input w-full" /></div>
                  <div><label className="text-xs font-medium text-gray-600 block mb-1">預算 (THB)</label><input name="target_budget_thb" type="number" className="input w-full" /></div>
                  <div><label className="text-xs font-medium text-gray-600 block mb-1">天氣風險備註</label><textarea name="weather_risk_note" className="input w-full h-16 resize-none" /></div>
                </>
              )}
              {tab === 'weather' && (
                <>
                  <div><label className="text-xs font-medium text-gray-600 block mb-1">日期 *</label><input name="forecast_date" type="date" required className="input w-full" /></div>
                  <div><label className="text-xs font-medium text-gray-600 block mb-1">地區 *</label>
                    <select name="region" required className="input w-full">
                      <option value="nakhon_pathom">Nakhon Pathom</option>
                      <option value="kanchanaburi">Kanchanaburi</option>
                      <option value="ratchaburi">Ratchaburi</option>
                      <option value="other">其他</option>
                    </select>
                  </div>
                  <div><label className="text-xs font-medium text-gray-600 block mb-1">天氣 *</label>
                    <select name="condition" required className="input w-full">
                      {['sunny','cloudy','rainy','storm','flood'].map(c => <option key={c} value={c}>{c}</option>)}
                    </select>
                  </div>
                  <div className="grid grid-cols-3 gap-2">
                    <div><label className="text-xs text-gray-500 block">高溫</label><input name="temperature_high" type="number" step="0.1" className="input w-full" /></div>
                    <div><label className="text-xs text-gray-500 block">低溫</label><input name="temperature_low" type="number" step="0.1" className="input w-full" /></div>
                    <div><label className="text-xs text-gray-500 block">降雨mm</label><input name="rainfall_mm" type="number" className="input w-full" /></div>
                  </div>
                  <div><label className="text-xs font-medium text-gray-600 block mb-1">影響程度</label>
                    <select name="impact_level" className="input w-full">
                      <option value="none">無</option><option value="low">低</option><option value="medium">中</option><option value="high">高</option>
                    </select>
                  </div>
                </>
              )}
              {tab === 'financial' && (
                <>
                  <div><label className="text-xs font-medium text-gray-600 block mb-1">計劃月份 *</label><input name="plan_month" type="month" required className="input w-full" /></div>
                  <div><label className="text-xs font-medium text-gray-600 block mb-1">計劃營收 (TWD)</label><input name="planned_revenue_twd" type="number" className="input w-full" /></div>
                  <div><label className="text-xs font-medium text-gray-600 block mb-1">計劃成本 (TWD)</label><input name="planned_cogs_twd" type="number" className="input w-full" /></div>
                  <div><label className="text-xs font-medium text-gray-600 block mb-1">計劃毛利 (TWD)</label><input name="planned_gross_profit_twd" type="number" className="input w-full" /></div>
                </>
              )}
              <div className="flex gap-2 mt-4">
                <button type="button" onClick={() => setShowCreate(false)} className="btn-secondary flex-1">取消</button>
                <button type="submit" className="btn-primary flex-1">建立</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
