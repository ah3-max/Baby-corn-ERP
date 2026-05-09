'use client';

/**
 * P-07 車輛管理頁面（H-03/04）
 */
import { useState } from 'react';
import { useTranslations } from 'next-intl';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api';
import { Truck, Plus, AlertTriangle, CheckCircle, Wrench } from 'lucide-react';
import { clsx } from 'clsx';

const VEHICLE_TYPE_KEYS = ['refrigerated_truck', 'dry_truck', 'pickup', 'motorcycle', 'van'] as const;

export default function VehiclesPage() {
  const t = useTranslations('logisticsVehicles');
  const [showForm, setShowForm] = useState(false);
  const [selectedVehicle, setSelectedVehicle] = useState<string | null>(null);
  const [form, setForm] = useState({
    plate_no: '',
    vehicle_type: 'refrigerated_truck',
    brand: '',
    model: '',
    year: new Date().getFullYear(),
    max_weight_kg: '',
    insurance_expiry: '',
    inspection_expiry: '',
  });
  const qc = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ['vehicles'],
    queryFn: async () => {
      const res = await apiClient.get('/logistics/vehicles');
      return res.data;
    },
  });

  const { data: maintenanceData } = useQuery({
    queryKey: ['vehicle-maintenance', selectedVehicle],
    queryFn: async () => {
      if (!selectedVehicle) return null;
      const res = await apiClient.get('/logistics/vehicle-maintenance', {
        params: { vehicle_id: selectedVehicle, limit: 10 },
      });
      return res.data;
    },
    enabled: !!selectedVehicle,
  });

  const addVehicle = useMutation({
    mutationFn: (d: any) => apiClient.post('/logistics/vehicles', d),
    onSuccess: () => {
      setShowForm(false);
      qc.invalidateQueries({ queryKey: ['vehicles'] });
    },
  });

  const vehicles = data?.items || [];
  const maintenances = maintenanceData?.items || [];

  const today = new Date().toISOString().split('T')[0];

  const isExpiringSoon = (dateStr: string | null) => {
    if (!dateStr) return false;
    const diff = new Date(dateStr).getTime() - new Date(today).getTime();
    return diff > 0 && diff < 30 * 86400000;
  };

  const isExpired = (dateStr: string | null) => {
    if (!dateStr) return false;
    return dateStr < today;
  };

  return (
    <div className="p-6 space-y-6">
      {/* 頁頭 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <Truck className="text-primary-600" size={24} />
            {t('title')}
          </h1>
          <p className="text-sm text-gray-500 mt-1">{t('subtitle', { count: vehicles.length })}</p>
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
          <div className="grid grid-cols-4 gap-4 text-sm">
            <div>
              <label className="block text-gray-600 mb-1">{t('labelPlate')} <span className="text-red-500">*</span></label>
              <input
                type="text"
                value={form.plate_no}
                onChange={e => setForm(p => ({ ...p, plate_no: e.target.value }))}
                className="w-full border rounded-lg px-3 py-1.5 text-sm"
                placeholder="ABC-1234"
              />
            </div>
            <div>
              <label className="block text-gray-600 mb-1">{t('labelType')}</label>
              <select
                value={form.vehicle_type}
                onChange={e => setForm(p => ({ ...p, vehicle_type: e.target.value }))}
                className="w-full border rounded-lg px-3 py-1.5 text-sm"
              >
                {VEHICLE_TYPE_KEYS.map(k => (
                  <option key={k} value={k}>{t(`vehicleType.${k}`)}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-gray-600 mb-1">{t('labelBrand')}</label>
              <input type="text" value={form.brand} onChange={e => setForm(p => ({ ...p, brand: e.target.value }))} className="w-full border rounded-lg px-3 py-1.5 text-sm" />
            </div>
            <div>
              <label className="block text-gray-600 mb-1">{t('labelModel')}</label>
              <input type="text" value={form.model} onChange={e => setForm(p => ({ ...p, model: e.target.value }))} className="w-full border rounded-lg px-3 py-1.5 text-sm" />
            </div>
            <div>
              <label className="block text-gray-600 mb-1">{t('labelYear')}</label>
              <input type="number" value={form.year} onChange={e => setForm(p => ({ ...p, year: Number(e.target.value) }))} className="w-full border rounded-lg px-3 py-1.5 text-sm" />
            </div>
            <div>
              <label className="block text-gray-600 mb-1">{t('labelMaxWeight')}</label>
              <input type="number" value={form.max_weight_kg} onChange={e => setForm(p => ({ ...p, max_weight_kg: e.target.value }))} className="w-full border rounded-lg px-3 py-1.5 text-sm" />
            </div>
            <div>
              <label className="block text-gray-600 mb-1">{t('labelInsurance')}</label>
              <input type="date" value={form.insurance_expiry} onChange={e => setForm(p => ({ ...p, insurance_expiry: e.target.value }))} className="w-full border rounded-lg px-3 py-1.5 text-sm" />
            </div>
            <div>
              <label className="block text-gray-600 mb-1">{t('labelInspection')}</label>
              <input type="date" value={form.inspection_expiry} onChange={e => setForm(p => ({ ...p, inspection_expiry: e.target.value }))} className="w-full border rounded-lg px-3 py-1.5 text-sm" />
            </div>
          </div>
          <div className="flex gap-2 justify-end">
            <button onClick={() => setShowForm(false)} className="px-4 py-2 border rounded-lg text-sm">{t('cancelBtn')}</button>
            <button
              onClick={() => addVehicle.mutate({ ...form, max_weight_kg: form.max_weight_kg ? Number(form.max_weight_kg) : undefined })}
              disabled={!form.plate_no}
              className="px-4 py-2 bg-primary-600 text-white rounded-lg text-sm hover:bg-primary-700 disabled:opacity-50"
            >
              {t('saveBtn')}
            </button>
          </div>
        </div>
      )}

      {/* 車輛列表 */}
      <div className="grid grid-cols-3 gap-4">
        {isLoading ? (
          Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="bg-white rounded-xl border p-4 animate-pulse h-40" />
          ))
        ) : vehicles.length === 0 ? (
          <div className="col-span-3 text-center py-12 text-gray-400">{t('noData')}</div>
        ) : (
          vehicles.map((v: any) => {
            const insuranceWarn = isExpiringSoon(v.insurance_expiry);
            const insuranceErr  = isExpired(v.insurance_expiry);
            const inspWarn = isExpiringSoon(v.inspection_expiry);
            const inspErr  = isExpired(v.inspection_expiry);

            return (
              <button
                key={v.id}
                onClick={() => setSelectedVehicle(selectedVehicle === v.id ? null : v.id)}
                className={clsx(
                  'bg-white rounded-xl border p-4 text-left hover:shadow-md transition-shadow',
                  selectedVehicle === v.id && 'ring-2 ring-primary-500'
                )}
              >
                <div className="flex items-start justify-between mb-2">
                  <div>
                    <h3 className="font-bold text-gray-900 text-lg">{v.plate_no}</h3>
                    <p className="text-xs text-gray-500">
                      {t(`vehicleType.${v.vehicle_type}` as any, { defaultValue: v.vehicle_type })}
                      {v.brand && ` · ${v.brand} ${v.model || ''}`}
                      {v.year && ` (${v.year})`}
                    </p>
                  </div>
                  <Truck size={20} className="text-gray-300" />
                </div>
                {v.max_weight_kg && (
                  <p className="text-xs text-gray-500 mb-2">{t('maxLoad', { kg: v.max_weight_kg })}</p>
                )}
                <div className="space-y-1">
                  <div className={clsx('flex items-center gap-1.5 text-xs',
                    insuranceErr ? 'text-red-600' : insuranceWarn ? 'text-orange-500' : 'text-gray-500'
                  )}>
                    {insuranceErr || insuranceWarn
                      ? <AlertTriangle size={11} />
                      : <CheckCircle size={11} className="text-green-500" />}
                    {t('insuranceExpiry')}{v.insurance_expiry || t('notSet')}
                    {insuranceErr && ` (${t('expired')})`}
                    {insuranceWarn && ` (${t('expiringSoon')})`}
                  </div>
                  <div className={clsx('flex items-center gap-1.5 text-xs',
                    inspErr ? 'text-red-600' : inspWarn ? 'text-orange-500' : 'text-gray-500'
                  )}>
                    {inspErr || inspWarn
                      ? <AlertTriangle size={11} />
                      : <CheckCircle size={11} className="text-green-500" />}
                    {t('inspectionExpiry')}{v.inspection_expiry || t('notSet')}
                    {inspErr && ` (${t('expired')})`}
                    {inspWarn && ` (${t('expiringSoon')})`}
                  </div>
                </div>
              </button>
            );
          })
        )}
      </div>

      {/* 保養記錄 */}
      {selectedVehicle && (
        <div className="bg-white rounded-xl border overflow-hidden">
          <div className="px-4 py-3 border-b bg-gray-50 flex items-center gap-2">
            <Wrench size={15} className="text-gray-500" />
            <h2 className="font-semibold text-gray-900 text-sm">{t('maintenanceTitle')}</h2>
          </div>
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
              <tr>
                <th className="px-4 py-2 text-left">{t('colMaintenanceType')}</th>
                <th className="px-4 py-2 text-left">{t('colServiceDate')}</th>
                <th className="px-4 py-2 text-left">{t('colNextService')}</th>
                <th className="px-4 py-2 text-right">{t('colCost')}</th>
                <th className="px-4 py-2 text-left">{t('colNotes')}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {maintenances.length === 0 ? (
                <tr><td colSpan={5} className="px-4 py-8 text-center text-gray-400">{t('noMaintenance')}</td></tr>
              ) : maintenances.map((m: any) => (
                <tr key={m.id} className="hover:bg-gray-50">
                  <td className="px-4 py-2.5 text-gray-900 capitalize">{m.maintenance_type}</td>
                  <td className="px-4 py-2.5 text-gray-600">{m.service_date}</td>
                  <td className="px-4 py-2.5 text-gray-600">{m.next_service_date || '—'}</td>
                  <td className="px-4 py-2.5 text-right font-mono text-gray-900">
                    {m.cost ? `$${Number(m.cost).toLocaleString()}` : '—'}
                  </td>
                  <td className="px-4 py-2.5 text-gray-500 text-xs truncate max-w-xs">{m.notes || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
