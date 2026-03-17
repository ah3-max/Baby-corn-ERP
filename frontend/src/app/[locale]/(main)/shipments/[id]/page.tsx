'use client';

/**
 * 出貨單詳情頁 /shipments/[id]
 * UI重點：
 * - 狀態時間軸
 * - 推進狀態按鈕（自動聯動批次）
 * - 出貨資訊（船名、B/L、日期、費用）
 * - Module J 出口文件資料（inline edit）
 * - 列印出貨單 + Excel 匯出
 * - 連結批次列表（即時顯示批次狀態）
 */
import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import { useTranslations, useLocale } from 'next-intl';
import Link from 'next/link';
import {
  ChevronLeft, ArrowRight, Check, Ship, Package,
  Calendar, DollarSign, FileText, Pencil, X, Save,
  Printer, Download, BoxesIcon,
} from 'lucide-react';
import { shipmentsApi, inventoryApi } from '@/lib/api';
import { useToast } from '@/contexts/ToastContext';
import { useUser } from '@/contexts/UserContext';
import type { Shipment, ShipmentStatus, InventoryLot } from '@/types';
import { SHIPMENT_STATUS_NEXT } from '@/types';
import { exportShipmentToExcel } from '@/lib/exportExcel';

const SHIPMENT_STATUSES: ShipmentStatus[] = [
  'preparing', 'customs_th', 'in_transit', 'customs_tw', 'arrived_tw',
];

const STATUS_COLORS: Record<ShipmentStatus, { badge: string; dot: string }> = {
  preparing:  { badge: 'bg-yellow-100 text-yellow-700',  dot: 'bg-yellow-400' },
  customs_th: { badge: 'bg-orange-100 text-orange-700',  dot: 'bg-orange-400' },
  in_transit: { badge: 'bg-blue-100 text-blue-700',      dot: 'bg-blue-400' },
  customs_tw: { badge: 'bg-purple-100 text-purple-700',  dot: 'bg-purple-400' },
  arrived_tw: { badge: 'bg-green-100 text-green-700',    dot: 'bg-green-400' },
};

const BATCH_STATUS_COLORS: Record<string, string> = {
  processing:      'bg-orange-100 text-orange-700',
  qc_pending:      'bg-yellow-100 text-yellow-700',
  qc_done:         'bg-blue-100 text-blue-700',
  packaging:       'bg-purple-100 text-purple-700',
  ready_to_export: 'bg-indigo-100 text-indigo-700',
  exported:        'bg-cyan-100 text-cyan-700',
  in_transit_tw:   'bg-teal-100 text-teal-700',
  in_stock:        'bg-green-100 text-green-700',
  sold:            'bg-emerald-100 text-emerald-700',
  closed:          'bg-gray-100 text-gray-500',
};

// ── Inline editable field ────────────────────────────────────────────────────
function EditableField({
  label,
  value,
  displayValue,
  onSave,
  inputType = 'text',
  canEdit,
}: {
  label: string;
  value: string;
  displayValue?: string;
  onSave: (val: string) => Promise<void>;
  inputType?: string;
  canEdit: boolean;
}) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(value);
  const [saving, setSaving] = useState(false);

  const handleSave = async () => {
    setSaving(true);
    try {
      await onSave(draft);
      setEditing(false);
    } finally {
      setSaving(false);
    }
  };

  if (editing) {
    return (
      <div className="flex items-center gap-2">
        <span className="text-gray-400 text-sm w-32 flex-shrink-0">{label}</span>
        <input
          type={inputType}
          value={draft}
          onChange={e => setDraft(e.target.value)}
          className="input text-sm py-1 flex-1"
          autoFocus
          onKeyDown={e => { if (e.key === 'Enter') handleSave(); if (e.key === 'Escape') setEditing(false); }}
        />
        <button onClick={handleSave} disabled={saving} className="p-1 text-green-600 hover:bg-green-50 rounded">
          <Save size={14} />
        </button>
        <button onClick={() => setEditing(false)} className="p-1 text-gray-400 hover:bg-gray-100 rounded">
          <X size={14} />
        </button>
      </div>
    );
  }

  return (
    <div className="flex items-center justify-between group">
      <span className="text-gray-400 text-sm">{label}</span>
      <div className="flex items-center gap-1">
        <span className="font-medium text-gray-700 text-sm">{displayValue ?? (value || '—')}</span>
        {canEdit && (
          <button
            onClick={() => { setDraft(value); setEditing(true); }}
            className="p-1 text-gray-300 hover:text-gray-600 opacity-0 group-hover:opacity-100 transition-opacity rounded"
          >
            <Pencil size={12} />
          </button>
        )}
      </div>
    </div>
  );
}

export default function ShipmentDetailPage() {
  const params = useParams();
  const locale = useLocale();
  const t  = useTranslations('shipments');
  const tc = useTranslations('common');
  const tb = useTranslations('batches');
  const { showToast } = useToast();
  const { hasPermission } = useUser();
  const canEdit = hasPermission('shipment', 'edit');

  const [shipment, setShipment]   = useState<Shipment | null>(null);
  const [loading, setLoading]     = useState(true);
  const [advancing, setAdvancing] = useState(false);
  const [inventoryLots, setInventoryLots] = useState<InventoryLot[]>([]);

  const fetchShipment = async () => {
    try {
      const { data } = await shipmentsApi.get(params.id as string);
      setShipment(data);
      // 如果已抵台，撈取對應的台灣庫存批次
      if (data.status === 'arrived_tw') {
        try {
          // 查詢每個關聯批次的庫存 lot（filter by shipment_id 不直接支援，改查各批次）
          const lotPromises = data.shipment_batches.map((sb: any) =>
            inventoryApi.listLots({ batch_id: sb.batch_id, status: 'all' }).catch(() => ({ data: [] }))
          );
          const results = await Promise.all(lotPromises);
          const allLots: InventoryLot[] = results.flatMap((r: any) => r.data ?? []);
          // 只保留 shipment_id 符合本出口單的
          const filtered = allLots.filter((lot: InventoryLot) => lot.shipment_id === params.id);
          setInventoryLots(filtered);
        } catch { /* 庫存資訊非關鍵，失敗不影響頁面 */ }
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchShipment(); }, []);

  const handleAdvance = async () => {
    if (!shipment) return;
    setAdvancing(true);
    try {
      await shipmentsApi.advance(shipment.id);
      showToast(t('advanceSuccess'), 'success');
      fetchShipment();
    } catch (e: any) {
      showToast(e?.response?.data?.detail ?? tc('error'), 'error');
    } finally {
      setAdvancing(false);
    }
  };

  const updateField = async (field: string, value: string | null) => {
    if (!shipment) return;
    try {
      await shipmentsApi.update(shipment.id, { [field]: value || null });
      showToast(t('saveSuccess'), 'success');
      fetchShipment();
    } catch (e: any) {
      showToast(e?.response?.data?.detail ?? tc('error'), 'error');
    }
  };

  if (loading) return <div className="text-center py-16 text-gray-400">{tc('loading')}</div>;
  if (!shipment) return <div className="text-center py-16 text-gray-400">{tc('noData')}</div>;

  const currentIdx = SHIPMENT_STATUSES.indexOf(shipment.status);
  const nextStatus = SHIPMENT_STATUS_NEXT[shipment.status];
  const style      = STATUS_COLORS[shipment.status];

  return (
    <>
      {/* Print styles */}
      <style>{`
        @media print {
          .no-print { display: none !important; }
          .print-only { display: block !important; }
          body { font-size: 12px; }
        }
        .print-only { display: none; }
      `}</style>

      <div className="max-w-3xl">
        {/* 頁首導覽 */}
        <div className="flex items-center gap-3 mb-6 no-print">
          <Link
            href={`/${locale}/shipments`}
            className="flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-700 transition-colors"
          >
            <ChevronLeft size={16} />
            {t('title')}
          </Link>
          <span className="text-gray-300">/</span>
          <span className="text-sm font-mono text-gray-700 font-semibold">{shipment.shipment_no}</span>
        </div>

        {/* ── 標題卡 ── */}
        <div className="card p-6 mb-5">
          <div className="flex items-start justify-between">
            <div>
              <div className="flex items-center gap-3 mb-1">
                <h1 className="text-2xl font-bold text-gray-900 font-mono">{shipment.shipment_no}</h1>
                <span className={`px-3 py-1 rounded-full text-sm font-medium ${style.badge}`}>
                  {t(`status.${shipment.status}` as any)}
                </span>
              </div>
              <p className="text-sm text-gray-400">
                {t('exportDate')}：{shipment.export_date}
              </p>
            </div>

            <div className="flex items-center gap-2 no-print">
              {/* Excel export */}
              <button
                onClick={() => exportShipmentToExcel(shipment)}
                className="btn-secondary flex items-center gap-1.5 py-1.5 px-3 text-sm"
                title={t('exportExcel')}
              >
                <Download size={14} /> Excel
              </button>
              {/* Print */}
              <button
                onClick={() => window.print()}
                className="btn-secondary flex items-center gap-1.5 py-1.5 px-3 text-sm"
                title={t('printShipment')}
              >
                <Printer size={14} /> {t('print')}
              </button>

              {canEdit && nextStatus && (
                <button
                  onClick={handleAdvance}
                  disabled={advancing}
                  className="btn-primary flex items-center gap-2"
                >
                  <ArrowRight size={15} />
                  {advancing ? '...' : t(`nextStatus.${shipment.status}` as any)}
                </button>
              )}
              {!nextStatus && (
                <span className="px-3 py-1.5 text-xs font-medium bg-green-100 text-green-600 rounded-lg flex items-center gap-1">
                  <Check size={13} /> {t('status.arrived_tw')}
                </span>
              )}
            </div>
          </div>
        </div>

        {/* ── 狀態時間軸 ── */}
        <div className="card p-6 mb-5 no-print">
          <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-4">
            {tb('statusFlow')}
          </h2>
          <div className="relative">
            <div className="absolute top-3 left-3 right-3 h-0.5 bg-gray-200" />
            <div
              className="absolute top-3 left-3 h-0.5 bg-primary-400 transition-all duration-500"
              style={{ width: `${(currentIdx / (SHIPMENT_STATUSES.length - 1)) * 100}%`, right: 'auto' }}
            />
            <div className="relative flex justify-between">
              {SHIPMENT_STATUSES.map((st, idx) => {
                const isDone    = idx < currentIdx;
                const isCurrent = idx === currentIdx;
                return (
                  <div key={st} className="flex flex-col items-center gap-1.5">
                    <div className={`w-6 h-6 rounded-full border-2 flex items-center justify-center transition-all ${
                      isDone
                        ? 'bg-primary-500 border-primary-500'
                        : isCurrent
                        ? `${STATUS_COLORS[st].dot} border-white ring-2 ring-offset-1 ring-primary-400`
                        : 'bg-white border-gray-300'
                    }`}>
                      {isDone && <Check size={12} className="text-white" />}
                      {isCurrent && <div className="w-2 h-2 rounded-full bg-white" />}
                    </div>
                    <span className={`text-[10px] text-center max-w-[56px] leading-tight ${
                      isCurrent ? 'text-primary-600 font-semibold' :
                      isDone    ? 'text-gray-500' : 'text-gray-300'
                    }`}>
                      {t(`status.${st}` as any)}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* ── Module J: 出口文件資料 ── */}
        <div className="card p-5 mb-5">
          <div className="flex items-center gap-2 mb-4">
            <FileText size={16} className="text-gray-400" />
            <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wider">
              {t('exportDocuments')}
            </h2>
          </div>
          <div className="space-y-2.5">
            {/* transport_mode */}
            <div className="flex items-center justify-between group">
              <span className="text-gray-400 text-sm">{t('transportMode')}</span>
              <div className="flex items-center gap-1">
                <span className="font-medium text-gray-700 text-sm">
                  {shipment.transport_mode === 'air' ? `✈️ ${t('transportAir')}`
                   : shipment.transport_mode === 'sea' ? `🚢 ${t('transportSea')}`
                   : '—'}
                </span>
                {canEdit && (
                  <select
                    className="input text-xs py-0.5 ml-1 opacity-0 group-hover:opacity-100 transition-opacity w-28"
                    value={shipment.transport_mode ?? ''}
                    onChange={e => updateField('transport_mode', e.target.value || null)}
                  >
                    <option value="">{t('transportUnspecified')}</option>
                    <option value="air">✈️ {t('transportAir')}</option>
                    <option value="sea">🚢 {t('transportSea')}</option>
                  </select>
                )}
              </div>
            </div>

            <EditableField
              label={t('shipperName')}
              value={shipment.shipper_name ?? ''}
              onSave={v => updateField('shipper_name', v)}
              canEdit={canEdit}
            />
            <EditableField
              label={t('shippedBoxes')}
              value={shipment.shipped_boxes != null ? String(shipment.shipped_boxes) : ''}
              onSave={v => updateField('shipped_boxes', v)}
              inputType="number"
              canEdit={canEdit}
            />
            <EditableField
              label={t('exportCustomsNo')}
              value={shipment.export_customs_no ?? ''}
              onSave={v => updateField('export_customs_no', v)}
              canEdit={canEdit}
            />
            <EditableField
              label={t('phytoCertNo')}
              value={shipment.phyto_cert_no ?? ''}
              onSave={v => updateField('phyto_cert_no', v)}
              canEdit={canEdit}
            />
            <EditableField
              label={t('phytoCertDate')}
              value={shipment.phyto_cert_date ?? ''}
              onSave={v => updateField('phyto_cert_date', v)}
              inputType="date"
              canEdit={canEdit}
            />
            <EditableField
              label={t('actualDeparture')}
              value={shipment.actual_departure_dt
                ? new Date(shipment.actual_departure_dt).toISOString().slice(0, 16)
                : ''}
              displayValue={shipment.actual_departure_dt
                ? new Date(shipment.actual_departure_dt).toLocaleString('zh-TW')
                : undefined}
              onSave={v => updateField('actual_departure_dt', v)}
              inputType="datetime-local"
              canEdit={canEdit}
            />
          </div>
        </div>

        {/* ── 運輸資訊（空運 / 海運 分區）── */}
        <div className="card p-5 mb-5">
          <div className="flex items-center gap-2 mb-4">
            {shipment.transport_mode === 'air'
              ? <span className="text-lg">✈️</span>
              : <Ship size={16} className="text-gray-400" />}
            <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wider">
              {shipment.transport_mode === 'air' ? '空運資訊' : shipment.transport_mode === 'sea' ? '海運資訊' : t('basicInfo')}
            </h2>
          </div>
          <div className="space-y-2 text-sm">
            {/* 共用 */}
            {shipment.carrier && (
              <div className="flex justify-between">
                <span className="text-gray-400">{t('carrier')}</span>
                <span className="font-medium text-gray-700">{shipment.carrier}</span>
              </div>
            )}
            <div className="flex justify-between">
              <span className="text-gray-400 flex items-center gap-1"><Calendar size={12} />{t('estimatedArrivalTW')}</span>
              <span className="font-medium text-gray-700">{shipment.estimated_arrival_tw ?? '—'}</span>
            </div>
            {shipment.actual_arrival_tw && (
              <div className="flex justify-between">
                <span className="text-gray-400 flex items-center gap-1"><Calendar size={12} />{t('actualArrivalTW')}</span>
                <span className="font-semibold text-green-600">{shipment.actual_arrival_tw}</span>
              </div>
            )}

            {/* 空運專屬 */}
            {shipment.transport_mode === 'air' && (<>
              {shipment.airline && (
                <div className="flex justify-between">
                  <span className="text-gray-400">航空公司</span>
                  <span className="font-medium text-gray-700">{shipment.airline}</span>
                </div>
              )}
              <EditableField label="AWB 提單號" value={shipment.awb_no ?? ''}
                onSave={v => updateField('awb_no', v)} canEdit={canEdit} />
              <EditableField label="航班號" value={shipment.flight_no ?? ''}
                onSave={v => updateField('flight_no', v)} canEdit={canEdit} />
            </>)}

            {/* 海運專屬 */}
            {shipment.transport_mode === 'sea' && (<>
              <EditableField label={t('vesselName')} value={shipment.vessel_name ?? ''}
                onSave={v => updateField('vessel_name', v)} canEdit={canEdit} />
              <EditableField label={t('blNo')} value={shipment.bl_no ?? ''}
                onSave={v => updateField('bl_no', v)} canEdit={canEdit} />
              <EditableField label="貨櫃號碼" value={shipment.container_no ?? ''}
                onSave={v => updateField('container_no', v)} canEdit={canEdit} />
              <EditableField label="裝載港（泰國）" value={shipment.port_of_loading ?? ''}
                onSave={v => updateField('port_of_loading', v)} canEdit={canEdit} />
              <EditableField label="卸貨港（台灣）" value={shipment.port_of_discharge ?? ''}
                onSave={v => updateField('port_of_discharge', v)} canEdit={canEdit} />
            </>)}

            {/* 未指定時仍顯示船名/B/L（相容舊資料） */}
            {!shipment.transport_mode && (<>
              {shipment.vessel_name && (
                <div className="flex justify-between">
                  <span className="text-gray-400">{t('vesselName')}</span>
                  <span className="font-medium text-gray-700 font-mono">{shipment.vessel_name}</span>
                </div>
              )}
              {shipment.bl_no && (
                <div className="flex justify-between">
                  <span className="text-gray-400">{t('blNo')}</span>
                  <span className="font-medium text-gray-700 font-mono">{shipment.bl_no}</span>
                </div>
              )}
            </>)}
          </div>
        </div>

        {/* ── 費用明細 ── */}
        <div className="card p-5 mb-5">
          <div className="flex items-center gap-2 mb-4">
            <DollarSign size={16} className="text-gray-400" />
            <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wider">
              {t('costs')}
            </h2>
          </div>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-400">{t('totalWeight')}</span>
              <span className="font-semibold text-gray-700">
                {shipment.total_weight != null ? `${Number(shipment.total_weight).toLocaleString()} kg` : '—'}
              </span>
            </div>
            <div className="border-t border-gray-100 pt-2">
              <EditableField
                label={shipment.transport_mode === 'air' ? '空運費（THB）' : '海運費（THB）'}
                value={shipment.freight_cost != null ? String(shipment.freight_cost) : ''}
                displayValue={shipment.freight_cost != null ? `฿${Number(shipment.freight_cost).toLocaleString()}` : '—'}
                onSave={v => updateField('freight_cost', v)}
                inputType="number"
                canEdit={canEdit}
              />
            </div>
            <EditableField
              label={`${t('customsCost')}（TWD）`}
              value={shipment.customs_cost != null ? String(shipment.customs_cost) : ''}
              displayValue={shipment.customs_cost != null ? `NT$${Number(shipment.customs_cost).toLocaleString()}` : '—'}
              onSave={v => updateField('customs_cost', v)}
              inputType="number"
              canEdit={canEdit}
            />
            <EditableField
              label="保險費（TWD）"
              value={shipment.insurance_cost != null ? String(shipment.insurance_cost) : ''}
              displayValue={shipment.insurance_cost != null ? `NT$${Number(shipment.insurance_cost).toLocaleString()}` : '—'}
              onSave={v => updateField('insurance_cost', v)}
              inputType="number"
              canEdit={canEdit}
            />
            <EditableField
              label="搬運/倉儲費（TWD）"
              value={shipment.handling_cost != null ? String(shipment.handling_cost) : ''}
              displayValue={shipment.handling_cost != null ? `NT$${Number(shipment.handling_cost).toLocaleString()}` : '—'}
              onSave={v => updateField('handling_cost', v)}
              inputType="number"
              canEdit={canEdit}
            />
            <EditableField
              label="其他費用（TWD）"
              value={shipment.other_cost != null ? String(shipment.other_cost) : ''}
              displayValue={shipment.other_cost != null ? `NT$${Number(shipment.other_cost).toLocaleString()}` : '—'}
              onSave={v => updateField('other_cost', v)}
              inputType="number"
              canEdit={canEdit}
            />
            {/* 台灣端合計 */}
            {[shipment.customs_cost, shipment.insurance_cost, shipment.handling_cost, shipment.other_cost].some(v => v != null) && (
              <div className="flex justify-between pt-2 border-t border-gray-100 font-semibold text-gray-700">
                <span>台灣端合計</span>
                <span>NT${(
                  (Number(shipment.customs_cost  ?? 0)) +
                  (Number(shipment.insurance_cost ?? 0)) +
                  (Number(shipment.handling_cost  ?? 0)) +
                  (Number(shipment.other_cost     ?? 0))
                ).toLocaleString()}</span>
              </div>
            )}
          </div>
        </div>

        {/* ── 連結批次 ── */}
        <div className="card p-5 mb-5">
          <div className="flex items-center gap-2 mb-4">
            <Package size={16} className="text-gray-400" />
            <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wider">
              {t('linkedBatches')}
            </h2>
            <span className="ml-auto text-xs text-gray-400">{shipment.shipment_batches.length} {tb('title').replace('管理','')}</span>
          </div>

          {shipment.shipment_batches.length === 0 ? (
            <p className="text-sm text-gray-400 text-center py-4">—</p>
          ) : (
            <div className="space-y-2">
              {shipment.shipment_batches.map((sb) => {
                const batch = sb.batch;
                if (!batch) return null;
                const batchBadge = BATCH_STATUS_COLORS[batch.status] ?? 'bg-gray-100 text-gray-500';
                return (
                  <div key={sb.batch_id} className="flex items-center justify-between p-3 bg-gray-50 rounded-xl">
                    <div className="flex items-center gap-3">
                      <Link
                        href={`/${locale}/batches/${batch.id}`}
                        className="font-mono text-sm font-semibold text-primary-600 hover:underline no-print"
                      >
                        {batch.batch_no}
                      </Link>
                      <span className="font-mono text-sm font-semibold text-primary-600 print-only">{batch.batch_no}</span>
                      <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${batchBadge}`}>
                        {tb(`status.${batch.status}` as any)}
                      </span>
                    </div>
                    <span className="text-sm font-semibold text-gray-700">
                      {Number(batch.current_weight).toLocaleString()} kg
                    </span>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* ── 台灣庫存入庫（arrived_tw 自動建立） ── */}
        {shipment.status === 'arrived_tw' && (
          <div className="card p-5 mb-5 border-green-200 bg-green-50/30">
            <div className="flex items-center gap-2 mb-4">
              <BoxesIcon size={16} className="text-green-600" />
              <h2 className="text-sm font-semibold text-green-700 uppercase tracking-wider">
                台灣庫存入庫
              </h2>
              <span className="ml-auto text-xs text-green-600 bg-green-100 px-2 py-0.5 rounded-full">
                自動建立
              </span>
            </div>
            {inventoryLots.length === 0 ? (
              <p className="text-sm text-gray-400 text-center py-4">
                庫存記錄建立中，請稍後重新整理頁面
              </p>
            ) : (
              <div className="space-y-2">
                {inventoryLots.map(lot => (
                  <div key={lot.id} className="flex items-center justify-between p-3 bg-white rounded-xl border border-green-100">
                    <div className="flex items-center gap-3">
                      <Link
                        href={`/${locale}/inventory`}
                        className="font-mono text-sm font-semibold text-green-700 hover:underline"
                      >
                        {lot.lot_no}
                      </Link>
                      <span className="text-xs text-gray-500">{lot.warehouse?.name ?? '—'}</span>
                      {lot.import_type && (
                        <span className="text-xs text-gray-400">
                          {lot.import_type === 'air' ? '✈️ 空運' : '🚢 海運'}
                        </span>
                      )}
                    </div>
                    <span className="text-sm font-semibold text-gray-700">
                      {Number(lot.current_weight_kg).toLocaleString()} kg
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* ── 備註 ── */}
        {shipment.notes && (
          <div className="card p-5">
            <div className="flex items-center gap-2 mb-3">
              <FileText size={16} className="text-gray-400" />
              <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wider">
                {t('notes')}
              </h2>
            </div>
            <p className="text-sm text-gray-600 whitespace-pre-wrap">{shipment.notes}</p>
          </div>
        )}
      </div>
    </>
  );
}
