'use client';

/**
 * P-07 貿易文件管理頁面（G segment）
 */
import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api';
import { FileText, AlertTriangle, CheckCircle, Clock, Search } from 'lucide-react';
import { clsx } from 'clsx';
import { useTranslations } from 'next-intl';

const DOC_TYPE_KEYS = [
  'commercial_invoice', 'packing_list', 'bill_of_lading', 'certificate_of_origin',
  'phytosanitary', 'fumigation', 'health_certificate', 'letter_of_credit',
  'insurance', 'customs_declaration', 'inspection_certificate', 'other',
] as const;

const STATUS_KEYS = ['draft', 'pending', 'submitted', 'approved', 'rejected', 'expired', 'cancelled'] as const;

const STATUS_COLORS: Record<string, string> = {
  draft:      'bg-gray-100 text-gray-600',
  pending:    'bg-yellow-100 text-yellow-700',
  submitted:  'bg-blue-100 text-blue-700',
  approved:   'bg-green-100 text-green-700',
  rejected:   'bg-red-100 text-red-700',
  expired:    'bg-red-100 text-red-700',
  cancelled:  'bg-gray-100 text-gray-500',
};

export default function TradeDocsPage() {
  const t = useTranslations('tradeDocs');
  const [docType, setDocType] = useState('');
  const [status, setStatus] = useState('');
  const [activeTab, setActiveTab] = useState<'list' | 'expiry'>('list');

  const { data, isLoading } = useQuery({
    queryKey: ['trade-documents', docType, status],
    queryFn: async () => {
      const res = await apiClient.get('/trade-documents/', {
        params: {
          document_type: docType || undefined,
          status: status || undefined,
          limit: 50,
        },
      });
      return res.data;
    },
  });

  const { data: expiryData } = useQuery({
    queryKey: ['trade-doc-expiry'],
    queryFn: async () => {
      const res = await apiClient.get('/trade-documents/expiry-alerts', { params: { days: 30 } });
      return res.data;
    },
  });

  const docs = data?.items || [];
  const expiringDocs = expiryData?.items || [];

  const today = new Date().toISOString().split('T')[0];

  const daysUntil = (dateStr: string) => {
    const diff = new Date(dateStr).getTime() - new Date(today).getTime();
    return Math.ceil(diff / 86400000);
  };

  return (
    <div className="p-6 space-y-6">
      {/* 頁頭 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <FileText className="text-primary-600" size={24} />
            {t('title')}
          </h1>
          <p className="text-sm text-gray-500 mt-1">
            {t('subtitle')}
            {expiringDocs.length > 0 && (
              <span className="ml-2 text-orange-600 font-medium">{t('expiringCount', { count: expiringDocs.length })}</span>
            )}
          </p>
        </div>
      </div>

      {/* 分頁標籤 */}
      <div className="border-b">
        <div className="flex gap-1">
          {[
            { id: 'list',   label: t('tabList') },
            { id: 'expiry', label: t('tabExpiry', { count: expiringDocs.length }) },
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={clsx(
                'px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors',
                activeTab === tab.id
                  ? 'border-primary-500 text-primary-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              )}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* 文件列表 */}
      {activeTab === 'list' && (
        <>
          <div className="flex gap-3">
            <select
              value={docType}
              onChange={e => setDocType(e.target.value)}
              className="border rounded-lg px-3 py-2 text-sm"
            >
              <option value="">{t('filterAllTypes')}</option>
              {DOC_TYPE_KEYS.map(k => (
                <option key={k} value={k}>{t(`docType.${k}`)}</option>
              ))}
            </select>
            <select
              value={status}
              onChange={e => setStatus(e.target.value)}
              className="border rounded-lg px-3 py-2 text-sm"
            >
              <option value="">{t('filterAllStatus')}</option>
              {STATUS_KEYS.map(k => (
                <option key={k} value={k}>{t(`status.${k}`)}</option>
              ))}
            </select>
          </div>

          <div className="bg-white rounded-xl border overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-xs text-gray-500 uppercase">
                <tr>
                  <th className="px-4 py-3 text-left">{t('colDocNo')}</th>
                  <th className="px-4 py-3 text-left">{t('colDocType')}</th>
                  <th className="px-4 py-3 text-left">{t('colShipment')}</th>
                  <th className="px-4 py-3 text-left">{t('colStatus')}</th>
                  <th className="px-4 py-3 text-left">{t('colIssueDate')}</th>
                  <th className="px-4 py-3 text-left">{t('colExpiry')}</th>
                  <th className="px-4 py-3 text-right">{t('colFee')}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {isLoading ? (
                  <tr><td colSpan={7} className="px-4 py-8 text-center text-gray-400">{t('loading')}</td></tr>
                ) : docs.length === 0 ? (
                  <tr><td colSpan={7} className="px-4 py-8 text-center text-gray-400">{t('noData')}</td></tr>
                ) : (
                  docs.map((doc: any) => (
                    <tr key={doc.id} className="hover:bg-gray-50">
                      <td className="px-4 py-2.5 font-mono text-xs text-gray-700">{doc.document_number}</td>
                      <td className="px-4 py-2.5 text-gray-900">
                        {t(`docType.${doc.document_type}` as any, { defaultValue: doc.document_type })}
                      </td>
                      <td className="px-4 py-2.5 text-gray-500 text-xs">{doc.shipment_no || doc.order_no || '—'}</td>
                      <td className="px-4 py-2.5">
                        <span className={clsx('px-2 py-0.5 rounded text-xs font-medium',
                          STATUS_COLORS[doc.status]
                        )}>
                          {t(`status.${doc.status}` as any, { defaultValue: doc.status })}
                        </span>
                      </td>
                      <td className="px-4 py-2.5 text-gray-600">{doc.issue_date || '—'}</td>
                      <td className={clsx('px-4 py-2.5',
                        doc.expiry_date && doc.expiry_date < today ? 'text-red-600 font-medium' :
                        doc.expiry_date && daysUntil(doc.expiry_date) <= 30 ? 'text-orange-600' :
                        'text-gray-600'
                      )}>
                        {doc.expiry_date || '—'}
                      </td>
                      <td className="px-4 py-2.5 text-right font-mono text-gray-700">
                        {doc.document_fee ? `$${Number(doc.document_fee).toLocaleString()}` : '—'}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </>
      )}

      {/* 到期告警 */}
      {activeTab === 'expiry' && (
        <div className="space-y-3">
          {expiringDocs.length === 0 ? (
            <div className="bg-white rounded-xl border p-8 text-center">
              <CheckCircle size={32} className="text-green-500 mx-auto mb-2" />
              <p className="text-gray-400">{t('expiryOk')}</p>
            </div>
          ) : (
            expiringDocs.map((item: any, idx: number) => {
              const days = item.expiry_date ? daysUntil(item.expiry_date) : null;
              return (
                <div key={idx} className={clsx(
                  'bg-white rounded-xl border p-4 flex items-center justify-between',
                  days !== null && days <= 0 ? 'border-red-200 bg-red-50' :
                  days !== null && days <= 7  ? 'border-orange-200 bg-orange-50' :
                  'border-yellow-100 bg-yellow-50'
                )}>
                  <div className="flex items-center gap-3">
                    <AlertTriangle size={18} className={
                      days !== null && days <= 0 ? 'text-red-500' :
                      days !== null && days <= 7  ? 'text-orange-500' : 'text-yellow-500'
                    } />
                    <div>
                      <p className="font-medium text-gray-900">
                        {t(`docType.${item.doc_type || item.document_type}` as any, { defaultValue: item.doc_type || item.document_type })}
                        {item.document_number && <span className="ml-2 font-mono text-xs text-gray-500">#{item.document_number}</span>}
                      </p>
                      <p className="text-xs text-gray-500">
                        {item.shipment_no || item.lc_number || item.co_number || item.bl_number || ''}
                      </p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="font-semibold text-gray-900">{item.expiry_date}</p>
                    <p className={clsx('text-xs font-medium',
                      days !== null && days <= 0 ? 'text-red-600' :
                      days !== null && days <= 7  ? 'text-orange-600' : 'text-yellow-700'
                    )}>
                      {days !== null && days <= 0 ? t('expiredDays', { days: Math.abs(days) }) :
                       days !== null ? t('daysLeft', { days }) : ''}
                    </p>
                  </div>
                </div>
              );
            })
          )}
        </div>
      )}
    </div>
  );
}
