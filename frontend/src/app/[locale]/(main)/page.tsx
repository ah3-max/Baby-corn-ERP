'use client';

/**
 * Dashboard 首頁 — 營運總覽
 */
import { useEffect, useState } from 'react';
import { useTranslations, useLocale } from 'next-intl';
import Link from 'next/link';
import {
  Package, ShoppingCart, Warehouse, TrendingUp,
  Users, ArrowRight, Ship, Factory,
  Sprout, Truck, BarChart3, AlertCircle,
  AlertTriangle, Clock, CheckCircle, Zap,
  ThumbsUp,
} from 'lucide-react';
import { purchasesApi, suppliersApi, batchesApi, shipmentsApi, salesApi, inventoryApi } from '@/lib/api';
import type { Batch, InventorySummary } from '@/types';

export default function DashboardPage() {
  const t      = useTranslations('nav');
  const tc     = useTranslations('common');
  const td     = useTranslations('dashboard');
  const locale = useLocale();

  // Core stats
  const [activeSuppliers,    setActiveSuppliers]    = useState(0);
  const [totalPurchases,     setTotalPurchases]      = useState(0);
  const [inTransitPO,        setInTransitPO]         = useState(0);
  const [arrivedPO,          setArrivedPO]           = useState(0);
  const [inStockBatches,     setInStockBatches]      = useState(0);
  const [activeShipments,    setActiveShipments]     = useState(0);
  const [pendingSalesOrders, setPendingSalesOrders]  = useState(0);
  const [qcPendingBatches,   setQcPendingBatches]    = useState(0);

  // Inventory health
  const [invSummary,   setInvSummary]   = useState<InventorySummary | null>(null);
  const [criticalBatches, setCriticalBatches] = useState<Batch[]>([]);
  const [warningBatches,  setWarningBatches]  = useState<Batch[]>([]);
  const [pendingReceipt,  setPendingReceipt]  = useState(0);  // in_stock but no lot

  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchAll = async () => {
      try {
        const [
          suppRes, poAllRes, poTransitRes, poArrivedRes,
          inStockRes, shipmentsRes, salesDraftRes, qcRes,
          invSumRes, lotsRes,
          processingRes, qcDoneRes, packagingRes,
        ] = await Promise.allSettled([
          suppliersApi.list({ is_active: true }),
          purchasesApi.list(),
          purchasesApi.list({ status: 'in_transit' }),
          purchasesApi.list({ status: 'arrived' }),
          batchesApi.list({ status: 'in_stock' }),
          shipmentsApi.list(),
          salesApi.list({ status: 'draft' }),
          batchesApi.list({ status: 'qc_pending' }),
          inventoryApi.summary(),
          inventoryApi.listLots({ status: 'active' }),
          batchesApi.list({ status: 'processing' }),
          batchesApi.list({ status: 'qc_done' }),
          batchesApi.list({ status: 'packaging' }),
        ]);

        const getLen = (r: PromiseSettledResult<any>) =>
          r.status === 'fulfilled' ? (r.value.data?.length ?? 0) : 0;
        const getData = (r: PromiseSettledResult<any>) =>
          r.status === 'fulfilled' ? (r.value.data ?? []) : [];

        setActiveSuppliers(getLen(suppRes));
        setTotalPurchases(getLen(poAllRes));
        setInTransitPO(getLen(poTransitRes));
        setArrivedPO(getLen(poArrivedRes));

        // In-stock batches vs those with lots → pending receipt
        const inStockData: Batch[] = getData(inStockRes);
        setInStockBatches(inStockData.length);
        const lotsData = getData(lotsRes);
        const batchIdsWithLots = new Set(lotsData.map((l: any) => l.batch_id));
        setPendingReceipt(inStockData.filter(b => !batchIdsWithLots.has(b.id)).length);

        // Active shipments
        const allShipments = getData(shipmentsRes);
        setActiveShipments(allShipments.filter((s: any) => s.status !== 'arrived_tw').length);

        setPendingSalesOrders(getLen(salesDraftRes));
        setQcPendingBatches(getLen(qcRes));

        // Inventory summary
        if (invSumRes.status === 'fulfilled') setInvSummary(invSumRes.value.data);

        // Freshness alerts — from all actively-processing batches that have harvest_datetime
        const activeBatches: Batch[] = [
          ...getData(processingRes),
          ...getData(qcRes),       // qc_pending already fetched
          ...getData(qcDoneRes),
          ...getData(packagingRes),
          ...inStockData,
        ];
        const withHarvest = activeBatches.filter(b => b.harvest_datetime && b.freshness_status);
        setCriticalBatches(withHarvest.filter(b => b.freshness_status === 'critical' || b.freshness_status === 'expired'));
        setWarningBatches(withHarvest.filter(b => b.freshness_status === 'warning'));

      } catch {
        // silent
      } finally {
        setLoading(false);
      }
    };
    fetchAll();
  }, []);

  const hasAlerts = criticalBatches.length > 0 || (invSummary?.age_alert ?? 0) > 0 || pendingReceipt > 0;

  return (
    <div className="max-w-6xl">
      {/* 頁首 */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">{t('dashboard')}</h1>
        <p className="text-gray-500 text-sm mt-1">{td('subtitle')}</p>
      </div>

      {/* ── 緊急警示橫幅 ── */}
      {!loading && hasAlerts && (
        <div className="mb-6 space-y-2">
          {criticalBatches.length > 0 && (
            <AlertBanner
              level="critical"
              icon={<AlertTriangle size={16} />}
              message={td('alertFreshnessCritical', { count: criticalBatches.length })}
              href={`/${locale}/batches`}
              detail={criticalBatches.slice(0, 3).map(b =>
                td('alertFreshnessDetail', { batchNo: b.batch_no, days: b.days_since_harvest, remaining: Math.max(0, b.remaining_days ?? 0) })
              ).join('、')}
            />
          )}
          {(invSummary?.age_alert ?? 0) > 0 && (
            <AlertBanner
              level="warning"
              icon={<Clock size={16} />}
              message={td('alertAgeWarning', { count: invSummary!.age_alert })}
              href={`/${locale}/inventory`}
            />
          )}
          {pendingReceipt > 0 && (
            <AlertBanner
              level="info"
              icon={<Package size={16} />}
              message={td('alertPendingReceipt', { count: pendingReceipt })}
              href={`/${locale}/inventory?tab=receive`}
            />
          )}
        </div>
      )}
      {!loading && !hasAlerts && criticalBatches.length === 0 && (
        <div className="mb-6 flex items-center gap-2 px-4 py-2.5 bg-green-50 border border-green-200 rounded-xl text-sm text-green-700">
          <ThumbsUp size={15} />
          <span>{td('allClear')}</span>
        </div>
      )}

      {/* ── 第一列：物流追蹤 ── */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
        <StatCard icon={<Ship size={20} />}       iconBg="bg-blue-50 text-blue-600"
          label={td('activeShipments')} value={activeShipments} loading={loading}
          href={`/${locale}/shipments`} highlight={activeShipments > 0} />
        <StatCard icon={<Truck size={20} />}      iconBg="bg-orange-50 text-orange-600"
          label={td('inTransit')} value={inTransitPO} loading={loading}
          href={`/${locale}/purchases`} />
        <StatCard icon={<AlertCircle size={20} />} iconBg="bg-yellow-50 text-yellow-600"
          label={td('qcPending')} value={qcPendingBatches} loading={loading}
          href={`/${locale}/factory`} highlight={qcPendingBatches > 0} />
        <StatCard icon={<Package size={20} />}    iconBg="bg-purple-50 text-purple-600"
          label={td('pendingArrival')} value={arrivedPO} loading={loading}
          href={`/${locale}/purchases`} highlight={arrivedPO > 0} />
      </div>

      {/* ── 第二列：庫存 + 銷售 ── */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <StatCard icon={<Warehouse size={20} />}   iconBg="bg-green-50 text-green-600"
          label={td('inStockBatches')} value={inStockBatches} loading={loading}
          href={`/${locale}/inventory`} highlight={inStockBatches > 0} />
        <StatCard icon={<ShoppingCart size={20} />} iconBg="bg-indigo-50 text-indigo-600"
          label={td('pendingSalesOrders')} value={pendingSalesOrders} loading={loading}
          href={`/${locale}/sales`} highlight={pendingSalesOrders > 0} />
        <StatCard icon={<Users size={20} />}        iconBg="bg-teal-50 text-teal-600"
          label={td('activeSuppliers')} value={activeSuppliers} loading={loading}
          href={`/${locale}/suppliers`} />
        <StatCard icon={<ShoppingCart size={20} />} iconBg="bg-gray-50 text-gray-600"
          label={td('totalPurchases')} value={totalPurchases} loading={loading}
          href={`/${locale}/purchases`} />
      </div>

      {/* ── 庫存健康 + 鮮度狀態 ── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-6">

        {/* 倉庫庫存健康 */}
        <div className="card p-5">
          <div className="flex items-center gap-2 mb-4">
            <Warehouse size={16} className="text-gray-400" />
            <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wider">{td('warehouseInventory')}</h2>
            <Link href={`/${locale}/inventory`} className="ml-auto text-xs text-primary-600 hover:underline">{td('viewDetails')}</Link>
          </div>
          {loading ? (
            <div className="space-y-2">
              {[1,2,3].map(i => <div key={i} className="h-4 bg-gray-100 rounded animate-pulse" />)}
            </div>
          ) : invSummary ? (
            <div className="space-y-3">
              <div>
                <p className="text-xs text-gray-400 mb-0.5">{td('totalStockWeight')}</p>
                <p className="text-2xl font-bold text-green-700">{invSummary.total_weight_kg.toLocaleString()} <span className="text-sm font-normal text-gray-400">kg</span></p>
                <p className="text-xs text-gray-400">{td('boxesAndLots', { boxes: invSummary.total_boxes, lots: invSummary.lot_count })}</p>
              </div>
              <div className="flex gap-2">
                <AgeChip count={invSummary.age_ok}      color="green"  label="≤30d" />
                <AgeChip count={invSummary.age_warning} color="yellow" label="31-60d" />
                <AgeChip count={invSummary.age_alert}   color="red"    label=">60d" urgent={invSummary.age_alert > 0} />
              </div>
              {pendingReceipt > 0 && (
                <Link href={`/${locale}/inventory`} className="flex items-center gap-1.5 text-xs text-orange-600 hover:text-orange-700 font-medium">
                  <Zap size={12} /> {td('batchesPendingReceipt', { count: pendingReceipt })}
                </Link>
              )}
            </div>
          ) : (
            <p className="text-sm text-gray-400">{td('noInventoryData')}</p>
          )}
        </div>

        {/* 鮮度告急 */}
        <div className="card p-5">
          <div className="flex items-center gap-2 mb-4">
            <span className="text-base">🌿</span>
            <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wider">{td('freshnessAlert')}</h2>
            <Link href={`/${locale}/batches`} className="ml-auto text-xs text-primary-600 hover:underline">{td('batchManagement')}</Link>
          </div>
          {loading ? (
            <div className="space-y-2">{[1,2].map(i=><div key={i} className="h-10 bg-gray-100 rounded animate-pulse"/>)}</div>
          ) : criticalBatches.length === 0 && warningBatches.length === 0 ? (
            <div className="flex flex-col items-center py-4 text-gray-400">
              <CheckCircle size={24} className="text-green-400 mb-1" />
              <p className="text-sm">{td('freshnessGood')}</p>
            </div>
          ) : (
            <div className="space-y-2">
              {[...criticalBatches, ...warningBatches].slice(0, 4).map(b => (
                <Link key={b.id} href={`/${locale}/batches/${b.id}`}
                  className="flex items-center gap-2 p-2 rounded-lg hover:bg-gray-50 transition-colors">
                  <span className={`w-2 h-2 rounded-full flex-shrink-0 ${
                    b.freshness_status === 'critical' || b.freshness_status === 'expired'
                      ? 'bg-red-500' : 'bg-yellow-400'
                  }`} />
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-mono font-semibold text-gray-700 truncate">{b.batch_no}</p>
                    <p className="text-[10px] text-gray-400">{b.purchase_order?.supplier?.name ?? '—'}</p>
                  </div>
                  <span className={`text-xs font-bold flex-shrink-0 ${
                    b.freshness_status === 'critical' || b.freshness_status === 'expired'
                      ? 'text-red-600' : 'text-yellow-600'
                  }`}>
                    {td('remainingDays', { days: Math.max(0, b.remaining_days ?? 0) })}
                  </span>
                </Link>
              ))}
              {(criticalBatches.length + warningBatches.length) > 4 && (
                <p className="text-xs text-gray-400 text-center pt-1">{td('moreAlerts', { count: criticalBatches.length + warningBatches.length - 4 })}</p>
              )}
            </div>
          )}
        </div>

        {/* 供應鏈管線 */}
        <div className="card p-5">
          <div className="flex items-center gap-2 mb-4">
            <Factory size={16} className="text-gray-400" />
            <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wider">{td('supplyChainPipeline')}</h2>
          </div>
          <div className="space-y-2">
            <PipelineRow icon="🌿" label={td('pipelinePurchasing')} count={inTransitPO}   href={`/${locale}/purchases`}  color="orange" />
            <PipelineRow icon="🏭" label={td('pipelineFactory')}    count={qcPendingBatches + arrivedPO} href={`/${locale}/batches`}    color="yellow" />
            <PipelineRow icon="🚢" label={td('pipelineExport')}     count={activeShipments} href={`/${locale}/shipments`}  color="blue" />
            <PipelineRow icon="🏪" label={td('pipelineInStock')}    count={inStockBatches}  href={`/${locale}/inventory`}  color="green" />
            <PipelineRow icon="📋" label={td('pipelinePendingInvoice')} count={pendingSalesOrders} href={`/${locale}/sales`}   color="indigo" />
          </div>
        </div>
      </div>

      {/* ── 快捷操作 + 系統模組 ── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-1">
          <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-4">{td('quickActions')}</h2>
          <div className="space-y-2">
            <QuickAction href={`/${locale}/purchases`}  icon={<ShoppingCart size={18} />} iconBg="bg-purple-100 text-purple-600" label={td('newPurchase')}      desc={td('newPurchaseDesc')} />
            <QuickAction href={`/${locale}/inventory`}  icon={<Warehouse size={18} />}    iconBg="bg-green-100 text-green-600"   label={td('warehouseReceiving')}  desc={td('warehouseReceivingDesc')} />
            <QuickAction href={`/${locale}/sales`}      icon={<BarChart3 size={18} />}     iconBg="bg-blue-100 text-blue-600"    label={td('createSalesOrder')}    desc={td('createSalesOrderDesc')} />
            <QuickAction href={`/${locale}/suppliers`}  icon={<Users size={18} />}         iconBg="bg-teal-100 text-teal-600"    label={td('manageSuppliers')}   desc={td('manageSuppliersDesc')} />
          </div>
        </div>

        <div className="lg:col-span-2">
          <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-4">{td('systemModules')}</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <ModuleCard icon={<Users size={18} />}        label={t('suppliers')}  href={`/${locale}/suppliers`}  />
            <ModuleCard icon={<ShoppingCart size={18} />} label={t('purchases')}  href={`/${locale}/purchases`}  />
            <ModuleCard icon={<Package size={18} />}      label={t('batches')}    href={`/${locale}/batches`}    />
            <ModuleCard icon={<Sprout size={18} />}       label={t('factory')}    href={`/${locale}/factory`}    />
            <ModuleCard icon={<Truck size={18} />}        label={t('shipments')}  href={`/${locale}/shipments`}  />
            <ModuleCard icon={<Warehouse size={18} />}    label={t('inventory')}  href={`/${locale}/inventory`}  />
            <ModuleCard icon={<BarChart3 size={18} />}    label={t('sales')}      href={`/${locale}/sales`}      />
            <ModuleCard icon={<TrendingUp size={18} />}   label={t('cost')}       href={`/${locale}/cost`}       />
          </div>
        </div>
      </div>
    </div>
  );
}

/* ── 子元件 ── */

function AlertBanner({ level, icon, message, href, detail }: {
  level: 'critical' | 'warning' | 'info';
  icon: React.ReactNode;
  message: string;
  href: string;
  detail?: string;
}) {
  const styles = {
    critical: 'bg-red-50 border-red-300 text-red-800',
    warning:  'bg-yellow-50 border-yellow-300 text-yellow-800',
    info:     'bg-blue-50 border-blue-200 text-blue-800',
  };
  return (
    <Link href={href} className={`flex items-start gap-3 px-4 py-3 rounded-xl border ${styles[level]} hover:opacity-90 transition-opacity`}>
      <span className="mt-0.5 flex-shrink-0">{icon}</span>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-semibold">{message}</p>
        {detail && <p className="text-xs mt-0.5 opacity-75 truncate">{detail}</p>}
      </div>
      <ArrowRight size={15} className="mt-0.5 flex-shrink-0 opacity-60" />
    </Link>
  );
}

function AgeChip({ count, color, label, urgent }: { count: number; color: string; label: string; urgent?: boolean }) {
  const colors: Record<string, string> = {
    green:  'bg-green-100 text-green-700',
    yellow: 'bg-yellow-100 text-yellow-700',
    red:    'bg-red-100 text-red-700',
  };
  return (
    <div className={`flex-1 text-center py-1.5 rounded-lg ${colors[color]} ${urgent ? 'ring-1 ring-red-400' : ''}`}>
      <p className="text-lg font-bold leading-none">{count}</p>
      <p className="text-[10px] mt-0.5 opacity-70">{label}</p>
    </div>
  );
}

function PipelineRow({ icon, label, count, href, color }: {
  icon: string; label: string; count: number; href: string; color: string;
}) {
  const barColors: Record<string, string> = {
    orange: 'bg-orange-400', yellow: 'bg-yellow-400', blue: 'bg-blue-400',
    green: 'bg-green-400', indigo: 'bg-indigo-400',
  };
  const maxCount = 10;
  const pct = Math.min(100, (count / maxCount) * 100);
  return (
    <Link href={href} className="flex items-center gap-2.5 hover:opacity-80 transition-opacity group">
      <span className="text-sm w-5 text-center flex-shrink-0">{icon}</span>
      <span className="text-xs text-gray-600 w-24 flex-shrink-0">{label}</span>
      <div className="flex-1 bg-gray-100 rounded-full h-1.5 overflow-hidden">
        <div className={`h-full rounded-full ${barColors[color]} transition-all`} style={{ width: `${pct}%` }} />
      </div>
      <span className={`text-xs font-bold w-6 text-right flex-shrink-0 ${count > 0 ? 'text-gray-700' : 'text-gray-300'}`}>{count}</span>
    </Link>
  );
}

function StatCard({ icon, iconBg, label, value, loading, highlight, href }: {
  icon: React.ReactNode; iconBg: string; label: string; value: number;
  loading: boolean; highlight?: boolean; href?: string;
}) {
  const inner = (
    <div className={`card p-5 transition-all ${highlight ? 'ring-2 ring-primary-300/50' : ''} ${href ? 'hover:shadow-md hover:border-primary-200 cursor-pointer' : ''}`}>
      <div className="flex items-center gap-3 mb-3">
        <div className={`w-9 h-9 rounded-lg flex items-center justify-center ${iconBg}`}>{icon}</div>
        <span className="text-sm text-gray-500 font-medium leading-tight">{label}</span>
      </div>
      <p className="text-3xl font-bold text-gray-900">
        {loading ? <span className="inline-block w-12 h-8 bg-gray-100 rounded animate-pulse" /> : value}
      </p>
    </div>
  );
  return href ? <Link href={href}>{inner}</Link> : inner;
}

function QuickAction({ href, icon, iconBg, label, desc }: {
  href: string; icon: React.ReactNode; iconBg: string; label: string; desc: string;
}) {
  return (
    <Link href={href} className="card flex items-center gap-3 px-4 py-3 hover:shadow-md hover:border-primary-200 transition-all group">
      <div className={`w-9 h-9 rounded-lg flex items-center justify-center ${iconBg}`}>{icon}</div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-semibold text-gray-800">{label}</p>
        <p className="text-xs text-gray-400">{desc}</p>
      </div>
      <ArrowRight size={16} className="text-gray-300 group-hover:text-primary-500 transition-colors" />
    </Link>
  );
}

function ModuleCard({ icon, label, href }: { icon: React.ReactNode; label: string; href: string }) {
  return (
    <Link href={href} className="card flex items-center gap-3 px-4 py-3.5 hover:shadow-md hover:border-primary-200 transition-all cursor-pointer">
      <div className="w-8 h-8 rounded-lg flex items-center justify-center bg-primary-50 text-primary-600">{icon}</div>
      <span className="text-sm font-medium flex-1 text-gray-800">{label}</span>
      <span className="px-2 py-0.5 text-xs font-medium rounded-full ring-1 bg-green-50 text-green-600 ring-green-500/20">
        {useTranslations('dashboard')('moduleReady')}
      </span>
    </Link>
  );
}
