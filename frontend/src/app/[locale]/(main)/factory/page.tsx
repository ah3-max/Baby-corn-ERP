'use client';

/**
 * Factory / QC 頁面 /factory
 * UI重點：
 * - 左側顯示待處理批次列表，右側或 Modal 記錄 QC
 * - 可記錄多筆 QC，每筆可刪除
 * - 批次狀態色塊、結果徽章
 */
import { useEffect, useState } from 'react';
import { useTranslations } from 'next-intl';
import { Plus, FlaskConical, Trash2, CheckCircle, XCircle, AlertCircle } from 'lucide-react';
import { qcApi } from '@/lib/api';
import { useToast } from '@/contexts/ToastContext';
import { useUser } from '@/contexts/UserContext';
import type { QCRecord } from '@/types';
import QCModal from './QCModal';

interface FactoryBatch {
  id: string;
  batch_no: string;
  status: string;
  current_weight: number;
  purchase_order: { order_no: string; supplier: { name: string } | null } | null;
  qc_count: number;
}

const RESULT_STYLES: Record<string, { badge: string; icon: React.ReactNode }> = {
  pass:             { badge: 'bg-green-100 text-green-700',  icon: <CheckCircle size={13} /> },
  fail:             { badge: 'bg-red-100 text-red-700',      icon: <XCircle size={13} /> },
  conditional_pass: { badge: 'bg-yellow-100 text-yellow-700', icon: <AlertCircle size={13} /> },
};

export default function FactoryPage() {
  const t  = useTranslations('factory');
  const tc = useTranslations('common');
  const { showToast } = useToast();
  const { hasPermission } = useUser();
  const canCreate = hasPermission('qc', 'create');
  const canDelete = hasPermission('qc', 'delete');

  const [batches, setBatches]         = useState<FactoryBatch[]>([]);
  const [loading, setLoading]         = useState(true);
  const [selectedBatch, setSelected]  = useState<FactoryBatch | null>(null);
  const [qcRecords, setQcRecords]     = useState<QCRecord[]>([]);
  const [modalOpen, setModalOpen]     = useState(false);
  const [deleting, setDeleting]       = useState<string | null>(null);

  const fetchBatches = async () => {
    setLoading(true);
    try {
      const { data } = await qcApi.listFactoryBatches();
      setBatches(data);
      if (data.length > 0 && !selectedBatch) {
        handleSelectBatch(data[0]);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const fetchQC = async (batchId: string) => {
    try {
      const { data } = await qcApi.listRecords(batchId);
      setQcRecords(data);
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => { fetchBatches(); }, []);

  const handleSelectBatch = (batch: FactoryBatch) => {
    setSelected(batch);
    fetchQC(batch.id);
  };

  const handleDelete = async (id: string) => {
    if (!confirm(tc('confirmDelete'))) return;
    setDeleting(id);
    try {
      await qcApi.delete(id);
      showToast(t('deleteSuccess'), 'success');
      if (selectedBatch) fetchQC(selectedBatch.id);
      fetchBatches();
    } catch (e: any) {
      showToast(e?.response?.data?.detail ?? tc('error'), 'error');
    } finally {
      setDeleting(null);
    }
  };

  return (
    <div>
      {/* 頁首 */}
      <div className="mb-5">
        <h1 className="text-2xl font-bold text-gray-800">{t('title')}</h1>
        <p className="text-sm text-gray-500 mt-0.5">{t('pendingBatches')}: {batches.length}</p>
      </div>

      <div className="flex gap-5 h-[calc(100vh-200px)]">
        {/* 左側：批次列表 */}
        <div className="w-72 flex-shrink-0 flex flex-col gap-2 overflow-y-auto pr-1">
          {loading ? (
            <div className="text-center py-10 text-gray-400 text-sm">{tc('loading')}</div>
          ) : batches.length === 0 ? (
            <div className="text-center py-10 text-gray-400 text-sm">{tc('noData')}</div>
          ) : (
            batches.map((b) => (
              <button
                key={b.id}
                onClick={() => handleSelectBatch(b)}
                className={`text-left p-3 rounded-xl border transition-all ${
                  selectedBatch?.id === b.id
                    ? 'border-primary-400 bg-primary-50 shadow-sm'
                    : 'border-gray-200 bg-white hover:border-gray-300 hover:shadow-sm'
                }`}
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="font-mono text-xs font-semibold text-gray-700">{b.batch_no}</span>
                  <span className="text-xs text-gray-400">{b.qc_count} QC</span>
                </div>
                <p className="text-sm font-medium text-gray-800 truncate">
                  {b.purchase_order?.supplier?.name ?? '—'}
                </p>
                <p className="text-xs text-gray-400 mt-0.5">
                  {Number(b.current_weight).toLocaleString()} kg
                </p>
              </button>
            ))
          )}
        </div>

        {/* 右側：QC 紀錄 */}
        <div className="flex-1 flex flex-col bg-white rounded-2xl border border-gray-200 overflow-hidden">
          {!selectedBatch ? (
            <div className="flex flex-col items-center justify-center h-full text-gray-400">
              <FlaskConical size={40} className="mb-3 opacity-30" />
              <p>{t('pendingBatches')}</p>
            </div>
          ) : (
            <>
              {/* QC 面板標題 */}
              <div className="flex items-center justify-between px-5 py-4 border-b border-gray-200">
                <div>
                  <h2 className="font-semibold text-gray-800">{selectedBatch.batch_no}</h2>
                  <p className="text-sm text-gray-500">{selectedBatch.purchase_order?.supplier?.name}</p>
                </div>
                {canCreate && (
                  <button
                    onClick={() => setModalOpen(true)}
                    className="btn-primary flex items-center gap-2 text-sm"
                  >
                    <Plus size={15} /> {t('addQC')}
                  </button>
                )}
              </div>

              {/* QC 紀錄列表 */}
              <div className="flex-1 overflow-y-auto p-5">
                {qcRecords.length === 0 ? (
                  <div className="flex flex-col items-center py-16 text-gray-400">
                    <FlaskConical size={36} className="mb-3 opacity-30" />
                    <p>{t('noQC')}</p>
                  </div>
                ) : (
                  <div className="space-y-3">
                    {qcRecords.map((qc) => {
                      const rs = RESULT_STYLES[qc.result] ?? RESULT_STYLES.fail;
                      return (
                        <div key={qc.id} className="border border-gray-200 rounded-xl p-4">
                          <div className="flex items-start justify-between">
                            <div className="flex-1">
                              <div className="flex items-center gap-2 mb-2">
                                <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${rs.badge}`}>
                                  {rs.icon}
                                  {t(`results.${qc.result}` as any)}
                                </span>
                                {qc.grade && (
                                  <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-600">
                                    {t(`grades.${qc.grade}` as any)}
                                  </span>
                                )}
                              </div>
                              <div className="grid grid-cols-2 gap-x-6 gap-y-1 text-sm">
                                <div>
                                  <span className="text-gray-400 text-xs">{t('inspector')}: </span>
                                  <span className="text-gray-700">{qc.inspector_name}</span>
                                </div>
                                {qc.weight_checked != null && (
                                  <div>
                                    <span className="text-gray-400 text-xs">{t('weightChecked')}: </span>
                                    <span className="text-gray-700">{Number(qc.weight_checked).toLocaleString()} kg</span>
                                  </div>
                                )}
                                <div className="col-span-2">
                                  <span className="text-gray-400 text-xs">{t('checkedAt')}: </span>
                                  <span className="text-gray-700 text-xs">
                                    {new Date(qc.checked_at).toLocaleString()}
                                  </span>
                                </div>
                                {qc.notes && (
                                  <div className="col-span-2">
                                    <span className="text-gray-400 text-xs">{t('notes')}: </span>
                                    <span className="text-gray-600 text-xs">{qc.notes}</span>
                                  </div>
                                )}
                              </div>
                            </div>
                            {canDelete && (
                              <button
                                onClick={() => handleDelete(qc.id)}
                                disabled={deleting === qc.id}
                                className="ml-3 text-gray-300 hover:text-red-500 transition-colors disabled:opacity-50"
                              >
                                <Trash2 size={16} />
                              </button>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            </>
          )}
        </div>
      </div>

      {/* QC 新增 Modal */}
      {modalOpen && selectedBatch && (
        <QCModal
          batchId={selectedBatch.id}
          batchNo={selectedBatch.batch_no}
          onClose={(r) => {
            setModalOpen(false);
            if (r && selectedBatch) {
              fetchQC(selectedBatch.id);
              fetchBatches();
            }
          }}
        />
      )}
    </div>
  );
}
