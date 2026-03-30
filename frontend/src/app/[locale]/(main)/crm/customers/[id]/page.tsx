'use client';

/**
 * 客戶 360 度檢視 — 完整交易歷史、拜訪記錄、欠款、偏好
 */
import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { useLocale } from 'next-intl';
import {
  ArrowLeft, User, Phone, Mail, MapPin, CreditCard,
  ShoppingCart, DollarSign, FileText, Activity,
} from 'lucide-react';
import { crmApi } from '@/lib/api';

export default function Customer360Page() {
  const { id } = useParams();
  const locale = useLocale();
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!id) return;
    crmApi.customer360(id as string)
      .then(r => setData(r.data))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) return <div className="text-center py-16 text-gray-400">載入中...</div>;
  if (!data) return <div className="text-center py-16 text-gray-400">客戶不存在</div>;

  const { customer: c, summary: s } = data;

  const CREDIT_COLORS: Record<string, string> = {
    good: 'bg-green-100 text-green-700',
    warning: 'bg-yellow-100 text-yellow-700',
    blocked: 'bg-red-100 text-red-700',
  };

  return (
    <div>
      {/* 返回 */}
      <Link href={`/${locale}/crm`} className="flex items-center gap-1 text-sm text-gray-500 hover:text-primary-600 mb-4">
        <ArrowLeft size={16} /> 返回 CRM
      </Link>

      {/* 客戶基本資訊卡 */}
      <div className="card p-6 mb-6">
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-800">{c.name}</h1>
            <div className="flex items-center gap-3 mt-2">
              {c.code && <span className="font-mono text-sm text-gray-500">{c.code}</span>}
              {c.customer_type && (
                <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-700">
                  {c.customer_type}
                </span>
              )}
              {c.credit_status && (
                <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${CREDIT_COLORS[c.credit_status] || 'bg-gray-100 text-gray-600'}`}>
                  {c.credit_status === 'good' ? '信用良好' : c.credit_status === 'warning' ? '信用警示' : '信用凍結'}
                </span>
              )}
            </div>
          </div>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-4 text-sm">
          {c.contact_name && (
            <div className="flex items-center gap-2 text-gray-600">
              <User size={14} className="text-gray-400" /> {c.contact_name}
            </div>
          )}
          {c.phone && (
            <div className="flex items-center gap-2 text-gray-600">
              <Phone size={14} className="text-gray-400" /> {c.phone}
            </div>
          )}
          {c.email && (
            <div className="flex items-center gap-2 text-gray-600">
              <Mail size={14} className="text-gray-400" /> {c.email}
            </div>
          )}
          {c.region && (
            <div className="flex items-center gap-2 text-gray-600">
              <MapPin size={14} className="text-gray-400" /> {c.region}
            </div>
          )}
          {c.payment_terms && (
            <div className="flex items-center gap-2 text-gray-600">
              <CreditCard size={14} className="text-gray-400" /> {c.payment_terms}
            </div>
          )}
        </div>
      </div>

      {/* KPI 摘要 */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-6">
        <div className="card p-4 text-center">
          <p className="text-xs text-gray-500">累計營收</p>
          <p className="text-lg font-bold text-gray-800">NT${Math.round(s.total_revenue_twd).toLocaleString()}</p>
        </div>
        <div className="card p-4 text-center">
          <p className="text-xs text-gray-500">已收款</p>
          <p className="text-lg font-bold text-green-600">NT${Math.round(s.total_paid_twd).toLocaleString()}</p>
        </div>
        <div className="card p-4 text-center">
          <p className="text-xs text-gray-500">應收餘額</p>
          <p className={`text-lg font-bold ${s.ar_balance_twd > 0 ? 'text-red-600' : 'text-gray-600'}`}>
            NT${Math.round(s.ar_balance_twd).toLocaleString()}
          </p>
        </div>
        <div className="card p-4 text-center">
          <p className="text-xs text-gray-500">訂單數</p>
          <p className="text-lg font-bold text-gray-800">{s.order_count}</p>
        </div>
        <div className="card p-4 text-center">
          <p className="text-xs text-gray-500">市場銷售</p>
          <p className="text-lg font-bold text-gray-800">{s.daily_sale_count}</p>
        </div>
      </div>

      {/* 四格面板 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* 最近訂單 */}
        <div className="card p-5">
          <h3 className="font-semibold text-gray-800 mb-3 flex items-center gap-2">
            <ShoppingCart size={16} /> 最近銷售訂單
          </h3>
          {data.recent_orders?.length > 0 ? (
            <div className="space-y-2">
              {data.recent_orders.map((o: any) => (
                <div key={o.id} className="flex items-center justify-between py-2 border-b border-gray-50 last:border-0">
                  <div>
                    <Link href={`/${locale}/sales/${o.id}`} className="font-mono text-sm text-primary-600 hover:underline">{o.order_no}</Link>
                    <span className="text-xs text-gray-400 ml-2">{o.date}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-semibold">NT${Math.round(o.amount).toLocaleString()}</span>
                    <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${
                      o.status === 'closed' ? 'bg-green-100 text-green-700' :
                      o.status === 'delivered' ? 'bg-purple-100 text-purple-700' :
                      'bg-gray-100 text-gray-600'
                    }`}>{o.status}</span>
                  </div>
                </div>
              ))}
            </div>
          ) : <p className="text-sm text-gray-400">尚無訂單</p>}
        </div>

        {/* 最近市場銷售 */}
        <div className="card p-5">
          <h3 className="font-semibold text-gray-800 mb-3 flex items-center gap-2">
            <DollarSign size={16} /> 最近市場銷售
          </h3>
          {data.recent_daily_sales?.length > 0 ? (
            <div className="space-y-2">
              {data.recent_daily_sales.map((d: any) => (
                <div key={d.id} className="flex items-center justify-between py-2 border-b border-gray-50 last:border-0">
                  <div>
                    <span className="text-sm text-gray-700">{d.date}</span>
                    <span className="text-xs text-gray-400 ml-2">{d.market}</span>
                  </div>
                  <span className="text-sm font-semibold">NT${Math.round(d.amount).toLocaleString()}</span>
                </div>
              ))}
            </div>
          ) : <p className="text-sm text-gray-400">尚無銷售</p>}
        </div>

        {/* 最近付款 */}
        <div className="card p-5">
          <h3 className="font-semibold text-gray-800 mb-3 flex items-center gap-2">
            <FileText size={16} /> 最近付款記錄
          </h3>
          {data.recent_payments?.length > 0 ? (
            <div className="space-y-2">
              {data.recent_payments.map((p: any) => (
                <div key={p.id} className="flex items-center justify-between py-2 border-b border-gray-50 last:border-0">
                  <div>
                    <span className="text-sm text-gray-700">{p.date}</span>
                    <span className="text-xs text-gray-400 ml-2">{p.method}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-semibold">NT${Math.round(p.amount).toLocaleString()}</span>
                    <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${
                      p.status === 'confirmed' ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'
                    }`}>{p.status === 'confirmed' ? '已確認' : '待確認'}</span>
                  </div>
                </div>
              ))}
            </div>
          ) : <p className="text-sm text-gray-400">尚無付款</p>}
        </div>

        {/* CRM 活動 */}
        <div className="card p-5">
          <h3 className="font-semibold text-gray-800 mb-3 flex items-center gap-2">
            <Activity size={16} /> CRM 活動記錄
          </h3>
          {data.recent_activities?.length > 0 ? (
            <div className="space-y-2">
              {data.recent_activities.map((a: any) => (
                <div key={a.id} className="py-2 border-b border-gray-50 last:border-0">
                  <div className="flex items-center justify-between">
                    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                      a.type === 'visit' ? 'bg-blue-100 text-blue-700' :
                      a.type === 'call' ? 'bg-green-100 text-green-700' :
                      a.type === 'complaint' ? 'bg-red-100 text-red-700' :
                      'bg-gray-100 text-gray-600'
                    }`}>{a.type}</span>
                    <span className="text-xs text-gray-400">{a.date?.split('T')[0]}</span>
                  </div>
                  {a.summary && <p className="text-sm text-gray-600 mt-1">{a.summary}</p>}
                  {a.result && (
                    <span className={`text-xs ${a.result === 'positive' ? 'text-green-600' : a.result === 'negative' ? 'text-red-600' : 'text-gray-500'}`}>
                      {a.result === 'positive' ? '正面' : a.result === 'negative' ? '負面' : '中性'}
                    </span>
                  )}
                </div>
              ))}
            </div>
          ) : <p className="text-sm text-gray-400">尚無活動</p>}
        </div>
      </div>
    </div>
  );
}
