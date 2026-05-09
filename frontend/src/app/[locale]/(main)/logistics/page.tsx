'use client';

/**
 * 物流配送 — 配送總覽 + 司機管理
 */
import { useEffect, useState } from 'react';
import { useTranslations } from 'next-intl';
import { Truck, Plus, X } from 'lucide-react';
import { logisticsApi } from '@/lib/api';
import { useToast } from '@/contexts/ToastContext';
import { clsx } from 'clsx';

const STATUS_COLORS: Record<string, string> = {
  pending:           'bg-gray-100 text-gray-600',
  accepted:          'bg-blue-100 text-blue-700',
  picking:           'bg-yellow-100 text-yellow-700',
  loaded:            'bg-indigo-100 text-indigo-700',
  in_transit:        'bg-orange-100 text-orange-700',
  delivered:         'bg-green-100 text-green-700',
  partial_delivered: 'bg-amber-100 text-amber-700',
  cancelled:         'bg-red-100 text-red-700',
};

const ORDER_TYPES = ['sales_delivery', 'market_delivery', 'sample', 'return'] as const;
const STATUS_FILTERS = ['', 'pending', 'accepted', 'in_transit', 'delivered'] as const;

export default function LogisticsPage() {
  const t = useTranslations('logistics');
  const { showToast } = useToast();
  const [tab, setTab] = useState<'orders' | 'drivers'>('orders');
  const [orders, setOrders] = useState<any[]>([]);
  const [drivers, setDrivers] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState('');
  const [showCreateOrder, setShowCreateOrder] = useState(false);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      try {
        if (tab === 'orders') {
          const { data } = await logisticsApi.listDeliveryOrders({ status: statusFilter || undefined });
          setOrders(data);
        } else {
          const { data } = await logisticsApi.listDrivers({});
          setDrivers(data);
        }
      } catch (e) { console.error(e); }
      finally { setLoading(false); }
    };
    load();
  }, [tab, statusFilter]);

  return (
    <div>
      <div className="flex items-center justify-between mb-5">
        <h1 className="text-2xl font-bold text-gray-800">{t('title')}</h1>
        <div className="flex gap-2">
          {tab === 'orders' && (
            <button onClick={() => setShowCreateOrder(true)} className="btn-primary flex items-center gap-2">
              <Plus size={16} /> {t('addOrderBtn')}
            </button>
          )}
          {tab === 'drivers' && (
            <button onClick={() => {
              const name = prompt(t('promptDriverName'));
              const phone = prompt(t('promptPhone'));
              const code = prompt(t('promptCode'));
              if (name && code) {
                logisticsApi.createDriver({ driver_code: code, name, phone }).then(() => {
                  showToast(t('toastDriverAdded'), 'success');
                  logisticsApi.listDrivers({}).then(r => setDrivers(r.data));
                }).catch(() => showToast(t('toastDriverFailed'), 'error'));
              }
            }} className="btn-primary flex items-center gap-2"><Plus size={16} /> {t('addDriverBtn')}</button>
          )}
        </div>
      </div>

      <div className="flex gap-1 mb-5 bg-gray-100 p-1 rounded-lg w-fit">
        <button onClick={() => setTab('orders')}
          className={`px-4 py-2 rounded-md text-sm font-medium ${tab === 'orders' ? 'bg-white shadow-sm text-gray-800' : 'text-gray-500'}`}>
          {t('tabOrders')}
        </button>
        <button onClick={() => setTab('drivers')}
          className={`px-4 py-2 rounded-md text-sm font-medium ${tab === 'drivers' ? 'bg-white shadow-sm text-gray-800' : 'text-gray-500'}`}>
          {t('tabDrivers')}
        </button>
      </div>

      {tab === 'orders' && (
        <div className="flex gap-2 mb-4 flex-wrap">
          {STATUS_FILTERS.map(s => (
            <button key={s} onClick={() => setStatusFilter(s)}
              className={`px-3 py-1.5 rounded-full text-xs font-medium transition-colors ${statusFilter === s ? 'bg-primary-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}`}>
              {s === '' ? t('filterAll') : t(`status.${s}` as any, { defaultValue: s })}
            </button>
          ))}
        </div>
      )}

      {loading ? <div className="text-center py-16 text-gray-400">{t('loading')}</div> : (
        <>
          {tab === 'orders' && (
            <div className="space-y-3">
              {orders.length === 0 ? <p className="text-gray-400 text-center py-10">{t('noOrders')}</p> : orders.map((o: any) => (
                <div key={o.id} className="card p-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <Truck size={18} className="text-gray-400" />
                      <span className="font-mono text-sm font-medium text-gray-700">{o.delivery_no}</span>
                      <span className={clsx('px-2 py-0.5 rounded-full text-xs font-medium', STATUS_COLORS[o.status] || 'bg-gray-100 text-gray-600')}>
                        {t(`status.${o.status}` as any, { defaultValue: o.status })}
                      </span>
                    </div>
                    <span className="text-sm text-gray-500">{o.dispatch_date}</span>
                  </div>
                  <div className="mt-2 flex items-center gap-4 text-sm text-gray-500">
                    {o.driver_name && <span>{t('driverLabel')}{o.driver_name}</span>}
                    <span>{o.total_weight_kg} kg · {o.total_boxes} 箱</span>
                    <span>{t('stopsUnit', { n: o.items?.length || 0 })}</span>
                    {o.assigner_name && <span className="text-gray-400">{t('dispatchLabel')}{o.assigner_name}</span>}
                  </div>
                  {o.items && o.items.length > 0 && (
                    <div className="mt-3 space-y-1">
                      {o.items.map((item: any, idx: number) => (
                        <div key={item.id} className="flex items-center gap-2 text-xs text-gray-500 pl-6">
                          <span className="w-5 h-5 rounded-full bg-gray-100 flex items-center justify-center text-[10px] font-bold">{idx + 1}</span>
                          <span className="font-medium">{item.customer_name}</span>
                          <span>{item.quantity_kg}kg</span>
                          <span className={clsx('px-1.5 py-0.5 rounded text-[10px] font-medium',
                            item.status === 'delivered' ? 'bg-green-100 text-green-700' :
                            item.status === 'rejected'  ? 'bg-red-100 text-red-700' : 'bg-gray-100 text-gray-500'
                          )}>
                            {item.status === 'delivered' ? t('itemDelivered') :
                             item.status === 'rejected'  ? t('itemRejected') : t('itemPending')}
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}

          {tab === 'drivers' && (
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
              {drivers.length === 0 ? <p className="text-gray-400 text-center py-10 col-span-3">{t('noDrivers')}</p> : drivers.map((d: any) => (
                <div key={d.id} className={`card p-4 ${!d.is_active ? 'opacity-50' : ''}`}>
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-semibold text-gray-800">{d.name}</span>
                    <span className="font-mono text-xs text-gray-400">{d.driver_code}</span>
                  </div>
                  <div className="space-y-1 text-sm text-gray-500">
                    {d.phone && <p>{d.phone}</p>}
                    {d.vehicle_type && <p>{d.vehicle_type} · {d.vehicle_plate}</p>}
                    {d.max_load_kg && <p>{t('maxLoad', { kg: d.max_load_kg })}</p>}
                  </div>
                </div>
              ))}
            </div>
          )}
        </>
      )}

      {/* 新增配送單 Modal */}
      {showCreateOrder && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-lg p-6 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-bold text-gray-800 text-lg">{t('modalTitle')}</h3>
              <button onClick={() => setShowCreateOrder(false)}><X size={18} className="text-gray-400" /></button>
            </div>
            <form onSubmit={async (e) => {
              e.preventDefault();
              const fd = new FormData(e.currentTarget);
              try {
                await logisticsApi.createDeliveryOrder({
                  order_type: fd.get('order_type'),
                  driver_id: fd.get('driver_id') || undefined,
                  dispatch_date: fd.get('dispatch_date'),
                  route_description: fd.get('route_description') || undefined,
                  items: [{
                    customer_id: fd.get('customer_id'),
                    quantity_kg: Number(fd.get('quantity_kg')),
                    quantity_boxes: Number(fd.get('quantity_boxes')) || undefined,
                    delivery_address: fd.get('delivery_address') || undefined,
                    delivery_sequence: 1,
                  }],
                });
                setShowCreateOrder(false);
                showToast(t('toastCreated'), 'success');
                const { data } = await logisticsApi.listDeliveryOrders({});
                setOrders(data);
              } catch { showToast(t('toastCreateFailed'), 'error'); }
            }} className="space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-medium text-gray-600 mb-1 block">{t('labelType')}</label>
                  <select name="order_type" className="input w-full">
                    {ORDER_TYPES.map(k => (
                      <option key={k} value={k}>{t(`orderType.${k}`)}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="text-xs font-medium text-gray-600 mb-1 block">{t('labelDate')} *</label>
                  <input name="dispatch_date" type="date" required defaultValue={new Date().toISOString().split('T')[0]} className="input w-full" />
                </div>
              </div>
              <div>
                <label className="text-xs font-medium text-gray-600 mb-1 block">{t('labelDriver')}</label>
                <select name="driver_id" className="input w-full">
                  <option value="">{t('driverUnassigned')}</option>
                  {drivers.map((d: any) => <option key={d.id} value={d.id}>{d.name} ({d.driver_code})</option>)}
                </select>
              </div>
              <div>
                <label className="text-xs font-medium text-gray-600 mb-1 block">{t('labelRoute')}</label>
                <input name="route_description" className="input w-full" />
              </div>
              <div className="border-t pt-3 mt-3">
                <p className="text-xs font-semibold text-gray-500 mb-2">{t('stop1Title')}</p>
                <div>
                  <label className="text-xs font-medium text-gray-600 mb-1 block">{t('labelCustomerId')} *</label>
                  <input name="customer_id" required className="input w-full" />
                </div>
                <div className="grid grid-cols-2 gap-3 mt-2">
                  <div>
                    <label className="text-xs font-medium text-gray-600 mb-1 block">{t('labelQtyKg')} *</label>
                    <input name="quantity_kg" type="number" step="0.01" required className="input w-full" />
                  </div>
                  <div>
                    <label className="text-xs font-medium text-gray-600 mb-1 block">{t('labelBoxes')}</label>
                    <input name="quantity_boxes" type="number" className="input w-full" />
                  </div>
                </div>
                <div className="mt-2">
                  <label className="text-xs font-medium text-gray-600 mb-1 block">{t('labelAddress')}</label>
                  <input name="delivery_address" className="input w-full" />
                </div>
              </div>
              <div className="flex gap-2 mt-4">
                <button type="button" onClick={() => setShowCreateOrder(false)} className="btn-secondary flex-1">{t('cancelBtn')}</button>
                <button type="submit" className="btn-primary flex-1">{t('createBtn')}</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
