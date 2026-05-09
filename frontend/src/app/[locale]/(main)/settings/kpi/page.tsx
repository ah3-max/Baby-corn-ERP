'use client';

/**
 * O-01/02 KPI 定義與儀表板配置頁面
 */
import { useState } from 'react';
import { useTranslations } from 'next-intl';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api';
import { BarChart3, Plus, TrendingUp, TrendingDown } from 'lucide-react';
import { clsx } from 'clsx';

const FREQUENCY_KEYS = ['daily', 'weekly', 'monthly', 'yearly'] as const;
const DIRECTION_KEYS = ['higher_better', 'lower_better'] as const;

export default function KpiSettingsPage() {
  const t = useTranslations('settingsKpi');
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({
    kpi_code:          '',
    kpi_name:          '',
    unit:              '',
    direction:         'higher_better',
    update_frequency:  'monthly',
    target_value:      '',
    warning_threshold: '',
    critical_threshold:'',
    description:       '',
  });
  const qc = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ['kpi-definitions'],
    queryFn: async () => {
      const res = await apiClient.get('/kpi/definitions', { params: { limit: 50 } });
      return res.data;
    },
  });

  const { data: valuesData } = useQuery({
    queryKey: ['kpi-values-latest'],
    queryFn: async () => {
      const res = await apiClient.get('/kpi/values/latest');
      return res.data;
    },
  });

  const addKpi = useMutation({
    mutationFn: (d: any) => apiClient.post('/kpi/definitions', d),
    onSuccess: () => {
      setShowForm(false);
      qc.invalidateQueries({ queryKey: ['kpi-definitions'] });
    },
  });

  const kpis = data?.items || [];
  const latestValues: Record<string, any> = {};
  (valuesData?.items || []).forEach((v: any) => { latestValues[v.kpi_id] = v; });

  const getStatusColor = (kpi: any, val: any) => {
    if (!val || val.actual_value == null) return 'text-gray-400';
    if (kpi.direction === 'higher_better') {
      if (val.actual_value >= kpi.target_value) return 'text-green-600';
      if (kpi.warning_threshold && val.actual_value >= kpi.warning_threshold) return 'text-yellow-600';
      return 'text-red-600';
    } else {
      if (val.actual_value <= kpi.target_value) return 'text-green-600';
      if (kpi.warning_threshold && val.actual_value <= kpi.warning_threshold) return 'text-yellow-600';
      return 'text-red-600';
    }
  };

  return (
    <div className="p-6 space-y-6">
      {/* 頁頭 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <BarChart3 className="text-primary-600" size={24} />
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
            <div>
              <label className="block text-gray-600 mb-1">{t('labelCode')} <span className="text-red-500">*</span></label>
              <input
                type="text"
                value={form.kpi_code}
                onChange={e => setForm(p => ({ ...p, kpi_code: e.target.value.toUpperCase() }))}
                placeholder="REVENUE_MONTHLY"
                className="w-full border rounded-lg px-3 py-1.5 text-sm font-mono"
              />
            </div>
            <div className="col-span-2">
              <label className="block text-gray-600 mb-1">{t('labelName')} <span className="text-red-500">*</span></label>
              <input
                type="text"
                value={form.kpi_name}
                onChange={e => setForm(p => ({ ...p, kpi_name: e.target.value }))}
                className="w-full border rounded-lg px-3 py-1.5 text-sm"
              />
            </div>
            <div>
              <label className="block text-gray-600 mb-1">{t('labelUnit')}</label>
              <input
                type="text"
                value={form.unit}
                onChange={e => setForm(p => ({ ...p, unit: e.target.value }))}
                placeholder="% / TWD / kg"
                className="w-full border rounded-lg px-3 py-1.5 text-sm"
              />
            </div>
            <div>
              <label className="block text-gray-600 mb-1">{t('labelDirection')}</label>
              <select
                value={form.direction}
                onChange={e => setForm(p => ({ ...p, direction: e.target.value }))}
                className="w-full border rounded-lg px-3 py-1.5 text-sm"
              >
                {DIRECTION_KEYS.map(k => (
                  <option key={k} value={k}>{t(`direction.${k}` as any)}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-gray-600 mb-1">{t('labelFrequency')}</label>
              <select
                value={form.update_frequency}
                onChange={e => setForm(p => ({ ...p, update_frequency: e.target.value }))}
                className="w-full border rounded-lg px-3 py-1.5 text-sm"
              >
                {FREQUENCY_KEYS.map(k => (
                  <option key={k} value={k}>{t(`frequency.${k}` as any)}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-gray-600 mb-1">{t('labelTarget')}</label>
              <input
                type="number"
                value={form.target_value}
                onChange={e => setForm(p => ({ ...p, target_value: e.target.value }))}
                className="w-full border rounded-lg px-3 py-1.5 text-sm"
              />
            </div>
            <div>
              <label className="block text-gray-600 mb-1">{t('labelWarning')}</label>
              <input
                type="number"
                value={form.warning_threshold}
                onChange={e => setForm(p => ({ ...p, warning_threshold: e.target.value }))}
                className="w-full border rounded-lg px-3 py-1.5 text-sm"
              />
            </div>
            <div>
              <label className="block text-gray-600 mb-1">{t('labelCritical')}</label>
              <input
                type="number"
                value={form.critical_threshold}
                onChange={e => setForm(p => ({ ...p, critical_threshold: e.target.value }))}
                className="w-full border rounded-lg px-3 py-1.5 text-sm"
              />
            </div>
            <div className="col-span-3">
              <label className="block text-gray-600 mb-1">{t('labelDesc')}</label>
              <textarea
                value={form.description}
                onChange={e => setForm(p => ({ ...p, description: e.target.value }))}
                className="w-full border rounded-lg px-3 py-2 text-sm h-16"
              />
            </div>
          </div>
          <div className="flex gap-2 justify-end">
            <button onClick={() => setShowForm(false)} className="px-4 py-2 border rounded-lg text-sm">{t('cancelBtn')}</button>
            <button
              onClick={() => addKpi.mutate({
                ...form,
                target_value:      form.target_value      ? Number(form.target_value)      : null,
                warning_threshold: form.warning_threshold ? Number(form.warning_threshold) : null,
                critical_threshold:form.critical_threshold? Number(form.critical_threshold): null,
              })}
              disabled={!form.kpi_code || !form.kpi_name}
              className="px-4 py-2 bg-primary-600 text-white rounded-lg text-sm hover:bg-primary-700 disabled:opacity-50"
            >
              {t('createBtn')}
            </button>
          </div>
        </div>
      )}

      {/* KPI 清單 */}
      <div className="bg-white rounded-xl border overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
            <tr>
              <th className="px-4 py-3 text-left">{t('colCode')}</th>
              <th className="px-4 py-3 text-left">{t('colName')}</th>
              <th className="px-4 py-3 text-left">{t('colFrequency')}</th>
              <th className="px-4 py-3 text-right">{t('colTarget')}</th>
              <th className="px-4 py-3 text-right">{t('colLatest')}</th>
              <th className="px-4 py-3 text-left">{t('colAchievement')}</th>
              <th className="px-4 py-3 text-left">{t('colDirection')}</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {isLoading ? (
              <tr><td colSpan={7} className="px-4 py-8 text-center text-gray-400">{t('loading')}</td></tr>
            ) : kpis.length === 0 ? (
              <tr><td colSpan={7} className="px-4 py-8 text-center text-gray-400">{t('noData')}</td></tr>
            ) : (
              kpis.map((kpi: any) => {
                const val = latestValues[kpi.id];
                const statusColor = getStatusColor(kpi, val);
                const achievement = val && kpi.target_value
                  ? (val.actual_value / kpi.target_value * 100).toFixed(0)
                  : null;

                return (
                  <tr key={kpi.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 font-mono text-xs text-gray-700">{kpi.kpi_code}</td>
                    <td className="px-4 py-3 font-medium text-gray-900">{kpi.kpi_name}</td>
                    <td className="px-4 py-3 text-gray-500">
                      {t(`frequency.${kpi.update_frequency}` as any, { defaultValue: kpi.update_frequency })}
                    </td>
                    <td className="px-4 py-3 text-right font-mono text-gray-700">
                      {kpi.target_value != null ? `${kpi.target_value} ${kpi.unit || ''}` : '—'}
                    </td>
                    <td className={clsx('px-4 py-3 text-right font-mono font-bold', statusColor)}>
                      {val?.actual_value != null ? `${val.actual_value} ${kpi.unit || ''}` : '—'}
                    </td>
                    <td className="px-4 py-3">
                      {achievement ? (
                        <div className="flex items-center gap-2">
                          <div className="w-16 h-1.5 bg-gray-100 rounded-full overflow-hidden">
                            <div
                              className={clsx('h-full rounded-full', statusColor.replace('text-', 'bg-'))}
                              style={{ width: `${Math.min(100, Number(achievement))}%` }}
                            />
                          </div>
                          <span className={clsx('text-xs font-medium', statusColor)}>{achievement}%</span>
                        </div>
                      ) : '—'}
                    </td>
                    <td className="px-4 py-3">
                      <span className="flex items-center gap-1 text-xs text-gray-500">
                        {kpi.direction === 'higher_better'
                          ? <TrendingUp size={12} className="text-green-500" />
                          : <TrendingDown size={12} className="text-blue-500" />}
                        {t(`direction.${kpi.direction}` as any, { defaultValue: kpi.direction })}
                      </span>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
