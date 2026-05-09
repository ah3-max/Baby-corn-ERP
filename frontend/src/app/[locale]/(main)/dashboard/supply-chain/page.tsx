'use client';

/**
 * O-03 供應鏈儀表板
 */
import { useTranslations } from 'next-intl';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api';
import { Ship, Warehouse, Factory, Package, AlertTriangle, Clock } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import { clsx } from 'clsx';

export default function SupplyChainDashboard() {
  const t = useTranslations('dashboardSupplyChain');

  const { data: batchData }    = useQuery({ queryKey: ['sc-batches'],   queryFn: async () => (await apiClient.get('/batches',         { params: { limit: 100 } })).data });
  const { data: poData }       = useQuery({ queryKey: ['sc-po'],        queryFn: async () => (await apiClient.get('/purchases',       { params: { limit: 50 } })).data });
  const { data: shipData }     = useQuery({ queryKey: ['sc-shipments'], queryFn: async () => (await apiClient.get('/shipments',       { params: { limit: 50 } })).data });
  const { data: invData }      = useQuery({ queryKey: ['sc-inventory'], queryFn: async () => (await apiClient.get('/inventory/summary')).data });
  const { data: supplierData } = useQuery({ queryKey: ['sc-suppliers'], queryFn: async () => (await apiClient.get('/suppliers',       { params: { is_active: true } })).data });

  const batches   = batchData?.items ?? batchData ?? [];
  const pos       = poData?.items    ?? poData    ?? [];
  const shipments = shipData?.items  ?? shipData  ?? [];

  const statusCount: Record<string, number> = {};
  (Array.isArray(batches) ? batches : []).forEach((b: any) => {
    statusCount[b.status] = (statusCount[b.status] || 0) + 1;
  });
  const statusChart = Object.entries(statusCount).map(([s, c]) => ({
    label: t(`batchStatusLabels.${s}` as any, { defaultValue: s }),
    count: c,
  })).sort((a, b) => b.count - a.count);

  const inTransitPO   = (Array.isArray(pos) ? pos : []).filter((p: any) => p.status === 'in_transit').length;
  const arrivedPO     = (Array.isArray(pos) ? pos : []).filter((p: any) => p.status === 'arrived').length;
  const activeShip    = (Array.isArray(shipments) ? shipments : []).filter((s: any) => s.status !== 'arrived_tw').length;
  const critBatches   = (Array.isArray(batches) ? batches : []).filter((b: any) => b.freshness_status === 'critical' || b.freshness_status === 'expired');
  const warnBatches   = (Array.isArray(batches) ? batches : []).filter((b: any) => b.freshness_status === 'warning');
  const totalStock    = invData?.total_weight_kg ?? 0;
  const ageAlert      = invData?.age_alert ?? 0;
  const lotCount      = invData?.lot_count ?? 0;
  const activeSuppliers = Array.isArray(supplierData) ? supplierData.length : (supplierData?.length ?? 0);

  return (
    <div className="p-6 space-y-6 max-w-7xl">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
          <Ship className="text-blue-600" size={24} />
          {t('title')}
        </h1>
        <p className="text-sm text-gray-500 mt-1">{t('subtitle')}</p>
      </div>

      {/* 核心指標 */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard icon={<Ship size={20} />}      color="blue"   label={t('kpiInTransit')} value={inTransitPO} unit={t('kpiInTransitUnit')} />
        <MetricCard icon={<Factory size={20} />}   color="orange" label={t('kpiArrived')}   value={arrivedPO}   unit={t('kpiArrivedUnit')} />
        <MetricCard icon={<Package size={20} />}   color="indigo" label={t('kpiShipments')} value={activeShip}  unit={t('kpiShipmentsUnit')} />
        <MetricCard icon={<Warehouse size={20} />} color="green"  label={t('kpiStock')}     value={totalStock ? `${Math.round(totalStock / 1000)}t` : '0'} unit="" />
      </div>

      {/* 警示 */}
      {(critBatches.length > 0 || ageAlert > 0) && (
        <div className="space-y-2">
          {critBatches.length > 0 && (
            <div className="flex items-center gap-2 px-4 py-3 bg-red-50 border border-red-200 rounded-xl text-sm text-red-700">
              <AlertTriangle size={16} className="flex-shrink-0" />
              <span dangerouslySetInnerHTML={{ __html: t('alertFreshness', {
                count: critBatches.length,
                batches: critBatches.slice(0, 3).map((b: any) => `<strong>${b.batch_no}</strong>`).join('、'),
              }) }} />
            </div>
          )}
          {ageAlert > 0 && (
            <div className="flex items-center gap-2 px-4 py-3 bg-yellow-50 border border-yellow-200 rounded-xl text-sm text-yellow-700">
              <Clock size={16} className="flex-shrink-0" />
              <span>{t('alertAge', { count: ageAlert })}</span>
            </div>
          )}
        </div>
      )}

      {/* 批次狀態 + 庫存健康 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-xl border p-5">
          <h2 className="text-sm font-semibold text-gray-600 mb-4">{t('batchStatus')}</h2>
          {statusChart.length > 0 ? (
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={statusChart}>
                <XAxis dataKey="label" tick={{ fontSize: 10 }} />
                <YAxis tick={{ fontSize: 10 }} />
                <Tooltip />
                <Bar dataKey="count" fill="#3b82f6" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-48 flex items-center justify-center text-gray-300 text-sm">{t('batchStatusNoData')}</div>
          )}
        </div>

        <div className="bg-white rounded-xl border p-5">
          <h2 className="text-sm font-semibold text-gray-600 mb-4">{t('inventoryHealth')}</h2>
          <div className="space-y-4">
            <div>
              <p className="text-xs text-gray-400 mb-1">{t('inventoryLots')}</p>
              <p className="text-3xl font-bold text-green-600">{lotCount} <span className="text-sm font-normal text-gray-400">{t('inventoryLotsUnit')}</span></p>
            </div>
            <div className="grid grid-cols-3 gap-3">
              <AgeBox label={t('ageOk')}   count={invData?.age_ok      ?? 0} color="green" />
              <AgeBox label={t('ageWarn')} count={invData?.age_warning ?? 0} color="yellow" />
              <AgeBox label={t('ageAlert')} count={invData?.age_alert  ?? 0} color="red" urgent={ageAlert > 0} />
            </div>
            <div className="border-t pt-3">
              <div className="flex justify-between text-xs text-gray-500">
                <span>{t('activeSuppliers')}</span>
                <span className="font-bold text-gray-700">{activeSuppliers} {t('activeSuppliersUnit')}</span>
              </div>
              <div className="flex justify-between text-xs text-gray-500 mt-1">
                <span>{t('freshnessStatus')}</span>
                <span className={`font-bold ${critBatches.length > 0 ? 'text-red-600' : warnBatches.length > 0 ? 'text-yellow-600' : 'text-green-600'}`}>
                  {critBatches.length > 0
                    ? t('freshnessCritical', { count: critBatches.length })
                    : warnBatches.length > 0
                      ? t('freshnessWarning', { count: warnBatches.length })
                      : t('freshnessOk')}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* 出貨列表 */}
      <div className="bg-white rounded-xl border overflow-hidden">
        <div className="px-5 py-4 border-b">
          <h2 className="text-sm font-semibold text-gray-600">{t('activeShipments')}</h2>
        </div>
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
            <tr>
              <th className="px-4 py-3 text-left">{t('colShipmentNo')}</th>
              <th className="px-4 py-3 text-left">{t('colCustomer')}</th>
              <th className="px-4 py-3 text-left">{t('colDepartureDate')}</th>
              <th className="px-4 py-3 text-left">{t('colStatus')}</th>
              <th className="px-4 py-3 text-right">{t('colWeight')}</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {(Array.isArray(shipments) ? shipments : []).filter((s: any) => s.status !== 'arrived_tw').slice(0, 8).map((s: any) => (
              <tr key={s.id} className="hover:bg-gray-50">
                <td className="px-4 py-2.5 font-mono text-xs text-gray-700">{s.shipment_no}</td>
                <td className="px-4 py-2.5 text-gray-900">{s.customer?.name || s.customer_name || '—'}</td>
                <td className="px-4 py-2.5 text-gray-500">{s.departure_date || '—'}</td>
                <td className="px-4 py-2.5">
                  <span className="px-2 py-0.5 bg-blue-100 text-blue-700 rounded text-xs font-medium">{s.status}</span>
                </td>
                <td className="px-4 py-2.5 text-right font-mono text-gray-700">{s.total_weight_kg ? Number(s.total_weight_kg).toLocaleString() : '—'}</td>
              </tr>
            ))}
            {(Array.isArray(shipments) ? shipments : []).filter((s: any) => s.status !== 'arrived_tw').length === 0 && (
              <tr><td colSpan={5} className="px-4 py-8 text-center text-gray-400">{t('noShipments')}</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function MetricCard({ icon, color, label, value, unit }: {
  icon: React.ReactNode; color: string; label: string; value: any; unit: string;
}) {
  const colors: Record<string, string> = {
    blue: 'bg-blue-50 text-blue-600', orange: 'bg-orange-50 text-orange-600',
    indigo: 'bg-indigo-50 text-indigo-600', green: 'bg-green-50 text-green-600',
  };
  return (
    <div className="bg-white rounded-xl border p-4">
      <div className={`w-9 h-9 rounded-lg flex items-center justify-center mb-3 ${colors[color]}`}>{icon}</div>
      <p className="text-2xl font-bold text-gray-900">{value}<span className="text-sm font-normal text-gray-400 ml-1">{unit}</span></p>
      <p className="text-xs font-medium text-gray-600 mt-0.5">{label}</p>
    </div>
  );
}

function AgeBox({ label, count, color, urgent }: { label: string; count: number; color: string; urgent?: boolean }) {
  const colors: Record<string, string> = {
    green: 'bg-green-100 text-green-700', yellow: 'bg-yellow-100 text-yellow-700', red: 'bg-red-100 text-red-700',
  };
  return (
    <div className={clsx('text-center py-2 rounded-lg', colors[color], urgent && 'ring-1 ring-red-400')}>
      <p className="text-xl font-bold">{count}</p>
      <p className="text-[10px] opacity-70">{label}</p>
    </div>
  );
}
