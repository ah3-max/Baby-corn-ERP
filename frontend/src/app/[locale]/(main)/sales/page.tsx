'use client';

/**
 * 銷售管理頁 /sales
 * UI重點：
 * - 兩個 Tab：銷售訂單 / 客戶
 * - 訂單狀態徽章
 * - 客戶列表（可新增/編輯/停用）
 */
import { useEffect, useState } from 'react';
import { useTranslations, useLocale } from 'next-intl';
import Link from 'next/link';
import { Plus, ShoppingCart, Users, ToggleLeft, ToggleRight, ArrowRight, Trash2 } from 'lucide-react';
import { salesApi, customersApi } from '@/lib/api';
import { useToast } from '@/contexts/ToastContext';
import { useUser } from '@/contexts/UserContext';
import type { SalesOrder, SalesStatus, Customer } from '@/types';
import { SALES_STATUS_NEXT } from '@/types';
import SalesDrawer from './SalesDrawer';
import CustomerModal from './CustomerModal';

const ORDER_STATUS_STYLES: Record<SalesStatus, string> = {
  draft:     'bg-gray-100 text-gray-600',
  confirmed: 'bg-blue-100 text-blue-700',
  delivered: 'bg-purple-100 text-purple-700',
  invoiced:  'bg-orange-100 text-orange-700',
  closed:    'bg-green-100 text-green-700',
};

const ORDER_TABS: Array<{ key: string; status?: SalesStatus }> = [
  { key: 'tabs.all' },
  { key: 'tabs.draft',     status: 'draft' },
  { key: 'tabs.confirmed', status: 'confirmed' },
  { key: 'tabs.delivered', status: 'delivered' },
  { key: 'tabs.invoiced',  status: 'invoiced' },
  { key: 'tabs.closed',    status: 'closed' },
];

export default function SalesPage() {
  const t  = useTranslations('sales');
  const tc = useTranslations('common');
  const locale = useLocale();
  const tcust = useTranslations('customers');
  const { showToast } = useToast();
  const { hasPermission } = useUser();
  const canCreateOrder    = hasPermission('sales', 'create');
  const canEditOrder      = hasPermission('sales', 'edit');
  const canDeleteOrder    = hasPermission('sales', 'delete');
  const canCreateCustomer = hasPermission('customer', 'create');
  const canEditCustomer   = hasPermission('customer', 'edit');

  const [mainTab, setMainTab]   = useState<'orders' | 'customers'>('orders');

  // ── 訂單狀態 ──
  const [orders, setOrders]         = useState<SalesOrder[]>([]);
  const [orderLoading, setOL]       = useState(true);
  const [orderTab, setOrderTab]     = useState<SalesStatus | undefined>(undefined);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [editOrder, setEditOrder]   = useState<SalesOrder | null>(null);
  const [advancing, setAdvancing]   = useState<string | null>(null);

  // ── 客戶狀態 ──
  const [customers, setCustomers]   = useState<Customer[]>([]);
  const [custLoading, setCL]        = useState(false);
  const [custModal, setCustModal]   = useState(false);
  const [editCust, setEditCust]     = useState<Customer | null>(null);
  const [toggling, setToggling]     = useState<string | null>(null);

  // 載入訂單
  const fetchOrders = async (status?: SalesStatus) => {
    setOL(true);
    try {
      const { data } = await salesApi.list(status ? { status } : undefined);
      setOrders(data);
    } catch (e) {
      console.error(e);
    } finally {
      setOL(false);
    }
  };

  // 載入客戶
  const fetchCustomers = async () => {
    setCL(true);
    try {
      const { data } = await customersApi.list();
      setCustomers(data);
    } catch (e) {
      console.error(e);
    } finally {
      setCL(false);
    }
  };

  const handleDeleteOrder = async (order: SalesOrder) => {
    if (!confirm(`確定要刪除訂單 ${order.order_no}？已扣減的批次重量將會還原。（此操作無法復原）`)) return;
    try {
      await salesApi.delete(order.id);
      showToast(`訂單 ${order.order_no} 已刪除`, 'success');
      fetchOrders(orderTab);
    } catch (e: any) {
      showToast(e?.response?.data?.detail ?? tc('error'), 'error');
    }
  };

  const handleAdvance = async (order: SalesOrder) => {
    setAdvancing(order.id);
    try {
      await salesApi.advance(order.id);
      showToast(t('advanceSuccess'), 'success');
      fetchOrders(orderTab);
    } catch (e: any) {
      showToast(e?.response?.data?.detail ?? tc('error'), 'error');
    } finally {
      setAdvancing(null);
    }
  };

  useEffect(() => { fetchOrders(orderTab); }, [orderTab]);
  useEffect(() => {
    if (mainTab === 'customers') fetchCustomers();
  }, [mainTab]);

  const handleToggleCustomer = async (c: Customer) => {
    if (!confirm(c.is_active ? tcust('confirmDeactivate') : `${tc('activate')} ${c.name}?`)) return;
    setToggling(c.id);
    try {
      await customersApi.update(c.id, { is_active: !c.is_active });
      showToast(c.is_active ? tcust('deactivateSuccess') : tcust('activateSuccess'), 'success');
      fetchCustomers();
    } catch (e: any) {
      showToast(e?.response?.data?.detail ?? tc('error'), 'error');
    } finally {
      setToggling(null);
    }
  };

  return (
    <div>
      {/* 頁首 */}
      <div className="flex items-center justify-between mb-5">
        <h1 className="text-2xl font-bold text-gray-800">{t('title')}</h1>
        {((mainTab === 'orders' && canCreateOrder) || (mainTab === 'customers' && canCreateCustomer)) && (
          <button
            onClick={() => {
              if (mainTab === 'orders') { setEditOrder(null); setDrawerOpen(true); }
              else { setEditCust(null); setCustModal(true); }
            }}
            className="btn-primary flex items-center gap-2"
          >
            <Plus size={16} />
            {mainTab === 'orders' ? t('addOrder') : tcust('addCustomer')}
          </button>
        )}
      </div>

      {/* 主 Tab */}
      <div className="flex gap-1 mb-5 bg-gray-100 p-1 rounded-lg w-fit">
        <button
          onClick={() => setMainTab('orders')}
          className={`flex items-center gap-2 px-4 py-1.5 rounded-md text-sm font-medium transition-colors ${
            mainTab === 'orders' ? 'bg-white text-gray-800 shadow-sm' : 'text-gray-500 hover:text-gray-700'
          }`}
        >
          <ShoppingCart size={15} /> {t('ordersTab')}
        </button>
        <button
          onClick={() => setMainTab('customers')}
          className={`flex items-center gap-2 px-4 py-1.5 rounded-md text-sm font-medium transition-colors ${
            mainTab === 'customers' ? 'bg-white text-gray-800 shadow-sm' : 'text-gray-500 hover:text-gray-700'
          }`}
        >
          <Users size={15} /> {t('customersTab')}
        </button>
      </div>

      {/* ── 訂單 Tab 內容 ── */}
      {mainTab === 'orders' && (
        <>
          {/* 狀態子 Tab */}
          <div className="flex gap-1 mb-5 bg-gray-100 p-1 rounded-lg overflow-x-auto">
            {ORDER_TABS.map(({ key, status }) => (
              <button
                key={key}
                onClick={() => setOrderTab(status)}
                className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors whitespace-nowrap flex-shrink-0 ${
                  orderTab === status
                    ? 'bg-white text-gray-800 shadow-sm'
                    : 'text-gray-500 hover:text-gray-700'
                }`}
              >
                {t(key as any)}
              </button>
            ))}
          </div>

          {/* 訂單列表 */}
          {orderLoading ? (
            <div className="text-center py-16 text-gray-400">{tc('loading')}</div>
          ) : orders.length === 0 ? (
            <div className="flex flex-col items-center py-20 text-gray-400">
              <ShoppingCart size={40} className="mb-3 opacity-30" />
              <p>{tc('noData')}</p>
            </div>
          ) : (
            <div className="bg-white rounded-2xl border border-gray-200 overflow-hidden">
              {/* 表頭 */}
              <div className="grid grid-cols-5 gap-4 px-5 py-3 bg-gray-50 border-b border-gray-200 text-xs font-semibold text-gray-500 uppercase tracking-wider">
                <div>{t('orderNo')}</div>
                <div>{t('customer')}</div>
                <div>{t('orderDate')}</div>
                <div className="text-right">{t('totalAmount')}</div>
                <div className="text-center">{tc('actions')}</div>
              </div>

              {orders.map((o, idx) => {
                const nextSt  = SALES_STATUS_NEXT[o.status];
                const isAdv   = advancing === o.id;
                return (
                <div
                  key={o.id}
                  className={`grid grid-cols-5 gap-4 px-5 py-4 items-center hover:bg-gray-50 transition-colors ${
                    idx < orders.length - 1 ? 'border-b border-gray-100' : ''
                  }`}
                >
                  <div>
                    <Link
                      href={`/${locale}/sales/${o.id}`}
                      className="font-mono text-sm font-semibold text-primary-600 hover:underline"
                    >
                      {o.order_no}
                    </Link>
                    <div className="mt-1">
                      <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${ORDER_STATUS_STYLES[o.status]}`}>
                        {t(`status.${o.status}` as any)}
                      </span>
                    </div>
                  </div>
                  <div className="text-sm text-gray-700 truncate">{o.customer?.name ?? '—'}</div>
                  <div className="text-sm text-gray-500">{o.order_date}</div>
                  <div className="text-right">
                    <span className="font-semibold text-gray-800">
                      NT$ {Number(o.total_amount_twd).toLocaleString()}
                    </span>
                    <p className="text-xs text-gray-400">{o.items.length} {t('items')}</p>
                  </div>
                  <div className="flex items-center justify-center gap-2 flex-wrap">
                    {canEditOrder && nextSt && (
                      <button
                        onClick={() => handleAdvance(o)}
                        disabled={isAdv}
                        className="flex items-center gap-1 px-2 py-1 text-xs font-medium bg-primary-50 text-primary-700 border border-primary-200 rounded-md hover:bg-primary-100 disabled:opacity-50 transition-colors"
                      >
                        <ArrowRight size={12} />
                        {isAdv ? '...' : t(`nextStatus.${o.status}` as any)}
                      </button>
                    )}
                    {canEditOrder && (
                      <button
                        onClick={() => { setEditOrder(o); setDrawerOpen(true); }}
                        className="text-xs text-gray-500 hover:text-primary-600 font-medium"
                      >
                        {tc('edit')}
                      </button>
                    )}
                    {canDeleteOrder && (o.status === 'draft' || o.status === 'confirmed') && (
                      <button
                        onClick={() => handleDeleteOrder(o)}
                        className="flex items-center gap-1 px-2 py-1 text-xs font-medium bg-red-50 text-red-600 border border-red-200 rounded-md hover:bg-red-100 transition-colors"
                        title="刪除訂單"
                      >
                        <Trash2 size={12} />
                      </button>
                    )}
                  </div>
                </div>
                );
              })}
            </div>
          )}
        </>
      )}

      {/* ── 客戶 Tab 內容 ── */}
      {mainTab === 'customers' && (
        <>
          {custLoading ? (
            <div className="text-center py-16 text-gray-400">{tc('loading')}</div>
          ) : customers.length === 0 ? (
            <div className="flex flex-col items-center py-20 text-gray-400">
              <Users size={40} className="mb-3 opacity-30" />
              <p>{tc('noData')}</p>
            </div>
          ) : (
            <div className="bg-white rounded-2xl border border-gray-200 overflow-hidden">
              {/* 表頭 */}
              <div className="grid grid-cols-4 gap-4 px-5 py-3 bg-gray-50 border-b border-gray-200 text-xs font-semibold text-gray-500 uppercase tracking-wider">
                <div>{tcust('name')}</div>
                <div>{tcust('contactName')}</div>
                <div>{tcust('phone')}</div>
                <div className="text-center">{tc('actions')}</div>
              </div>

              {customers.map((c, idx) => (
                <div
                  key={c.id}
                  className={`grid grid-cols-4 gap-4 px-5 py-4 items-center hover:bg-gray-50 transition-colors ${
                    idx < customers.length - 1 ? 'border-b border-gray-100' : ''
                  }`}
                >
                  <div>
                    <p className="font-medium text-gray-800">{c.name}</p>
                    <span className={`text-xs font-medium ${c.is_active ? 'text-green-600' : 'text-gray-400'}`}>
                      {c.is_active ? tc('active') : tc('inactive')}
                    </span>
                  </div>
                  <div className="text-sm text-gray-600">{c.contact_name ?? '—'}</div>
                  <div className="text-sm text-gray-600">{c.phone ?? '—'}</div>
                  <div className="flex items-center justify-center gap-3">
                    {canEditCustomer && (
                      <button
                        onClick={() => { setEditCust(c); setCustModal(true); }}
                        className="text-sm text-primary-600 hover:text-primary-700 font-medium"
                      >
                        {tc('edit')}
                      </button>
                    )}
                    {canEditCustomer && (
                      <button
                        onClick={() => handleToggleCustomer(c)}
                        disabled={toggling === c.id}
                        className={`disabled:opacity-50 ${c.is_active ? 'text-red-400 hover:text-red-600' : 'text-green-500 hover:text-green-700'}`}
                      >
                        {c.is_active
                          ? <ToggleRight size={20} />
                          : <ToggleLeft size={20} />
                        }
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </>
      )}

      {/* 銷售訂單 Drawer */}
      {drawerOpen && (
        <SalesDrawer
          order={editOrder}
          onClose={(r) => {
            setDrawerOpen(false);
            setEditOrder(null);
            if (r) fetchOrders(orderTab);
          }}
        />
      )}

      {/* 客戶 Modal */}
      {custModal && (
        <CustomerModal
          customer={editCust}
          onClose={(r) => {
            setCustModal(false);
            setEditCust(null);
            if (r) fetchCustomers();
          }}
        />
      )}
    </div>
  );
}
