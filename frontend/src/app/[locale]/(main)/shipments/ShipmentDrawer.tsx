'use client';

/**
 * 出口物流新增 / 編輯 Drawer
 * 空運 / 海運 動態切換欄位
 */
import { useState, useEffect } from 'react';
import { useTranslations } from 'next-intl';
import { X, Ship, Plane, Check } from 'lucide-react';
import { shipmentsApi, batchesApi } from '@/lib/api';
import { useToast } from '@/contexts/ToastContext';
import type { Shipment, Batch } from '@/types';

interface Props {
  shipment: Shipment | null;
  onClose: (refresh?: boolean) => void;
}

const LABEL = 'block text-sm font-medium text-gray-700 mb-1';
const OPT   = 'ml-1 text-xs text-gray-400';

export default function ShipmentDrawer({ shipment, onClose }: Props) {
  const t  = useTranslations('shipments');
  const tc = useTranslations('common');
  const { showToast } = useToast();
  const isEdit = !!shipment;

  const today = new Date().toISOString().split('T')[0];

  const [form, setForm] = useState({
    export_date:          shipment?.export_date          ?? today,
    transport_mode:       shipment?.transport_mode        ?? '',
    // 共用
    carrier:              shipment?.carrier               ?? '',
    shipped_boxes:        shipment?.shipped_boxes != null ? String(shipment.shipped_boxes) : '',
    shipper_name:         shipment?.shipper_name          ?? '',
    estimated_arrival_tw: shipment?.estimated_arrival_tw
      ? shipment.estimated_arrival_tw.split('T')[0] : '',
    // 空運欄位
    airline:              shipment?.airline               ?? '',
    awb_no:               shipment?.awb_no                ?? '',
    flight_no:            shipment?.flight_no             ?? '',
    // 海運欄位
    vessel_name:          shipment?.vessel_name           ?? '',
    bl_no:                shipment?.bl_no                 ?? '',
    container_no:         shipment?.container_no          ?? '',
    port_of_loading:      shipment?.port_of_loading       ?? '',
    port_of_discharge:    shipment?.port_of_discharge     ?? '',
    // 費用
    freight_cost:         shipment?.freight_cost  != null ? String(shipment.freight_cost)  : '',
    customs_cost:         shipment?.customs_cost  != null ? String(shipment.customs_cost)  : '',
    insurance_cost:       shipment?.insurance_cost != null ? String(shipment.insurance_cost) : '',
    handling_cost:        shipment?.handling_cost  != null ? String(shipment.handling_cost)  : '',
    other_cost:           shipment?.other_cost     != null ? String(shipment.other_cost)     : '',
    notes:                shipment?.notes          ?? '',
  });

  const [availBatches, setAvailBatches] = useState<Batch[]>([]);
  const [selectedIds, setSelectedIds]   = useState<Set<string>>(
    new Set(shipment?.shipment_batches.map((sb) => sb.batch_id) ?? [])
  );
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState('');

  useEffect(() => {
    batchesApi.list({ status: 'ready_to_export' }).then(({ data }) => {
      if (isEdit) {
        const linkedBatches = (shipment?.shipment_batches ?? [])
          .map((sb) => sb.batch).filter(Boolean)
          .map((b) => ({ ...b as NonNullable<typeof b>, status: (b as any).status }));
        const allBatches = [
          ...linkedBatches.filter((b) => !data.find((d: Batch) => d.id === b.id)),
          ...data,
        ];
        setAvailBatches(allBatches);
      } else {
        setAvailBatches(data);
      }
    });
  }, []);

  const set = (key: string, val: string) => setForm((f) => ({ ...f, [key]: val }));

  const toggleBatch = (id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const payload: Record<string, any> = {
        export_date:          form.export_date,
        transport_mode:       form.transport_mode || null,
        carrier:              form.carrier || null,
        shipped_boxes:        form.shipped_boxes ? parseInt(form.shipped_boxes) : null,
        shipper_name:         form.shipper_name || null,
        estimated_arrival_tw: form.estimated_arrival_tw || null,
        freight_cost:         form.freight_cost  ? parseFloat(form.freight_cost)  : null,
        customs_cost:         form.customs_cost  ? parseFloat(form.customs_cost)  : null,
        insurance_cost:       form.insurance_cost ? parseFloat(form.insurance_cost) : null,
        handling_cost:        form.handling_cost  ? parseFloat(form.handling_cost)  : null,
        other_cost:           form.other_cost     ? parseFloat(form.other_cost)     : null,
        notes:                form.notes || null,
      };

      if (form.transport_mode === 'air') {
        payload.airline   = form.airline   || null;
        payload.awb_no    = form.awb_no    || null;
        payload.flight_no = form.flight_no || null;
      } else if (form.transport_mode === 'sea') {
        payload.vessel_name     = form.vessel_name     || null;
        payload.bl_no           = form.bl_no           || null;
        payload.container_no    = form.container_no    || null;
        payload.port_of_loading = form.port_of_loading || null;
        payload.port_of_discharge = form.port_of_discharge || null;
      }

      if (!isEdit) payload.batch_ids = Array.from(selectedIds);

      if (isEdit) {
        await shipmentsApi.update(shipment.id, payload);
        showToast(t('updateSuccess'), 'success');
      } else {
        await shipmentsApi.create(payload);
        showToast(t('createSuccess'), 'success');
      }
      onClose(true);
    } catch (err: any) {
      const msg = err?.response?.data?.detail ?? tc('error');
      setError(msg);
      showToast(msg, 'error');
    } finally {
      setLoading(false);
    }
  };

  const mode = form.transport_mode;

  return (
    <>
      <div className="fixed inset-0 z-40 bg-black/30" onClick={() => onClose()} />
      <div className="fixed right-0 top-0 bottom-0 z-50 w-full max-w-lg bg-white shadow-2xl flex flex-col">
        {/* 標題 */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <div className="flex items-center gap-2">
            {mode === 'air' ? <Plane size={20} className="text-sky-500" /> : <Ship size={20} className="text-primary-600" />}
            <h2 className="text-lg font-semibold text-gray-800">
              {isEdit ? t('editShipment') : t('addShipment')}
            </h2>
          </div>
          <button onClick={() => onClose()} className="text-gray-400 hover:text-gray-600">
            <X size={20} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="flex flex-col flex-1 min-h-0">
          <div className="flex-1 overflow-y-auto px-6 py-5 space-y-6">

            {/* ── 運輸方式選擇 ── */}
            <div>
              <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">
                運輸方式
              </p>
              <div className="grid grid-cols-3 gap-2">
                {[
                  { val: '',    label: '未指定', icon: null },
                  { val: 'air', label: '✈️ 空運',  icon: null },
                  { val: 'sea', label: '🚢 海運',  icon: null },
                ].map(({ val, label }) => (
                  <button
                    key={val}
                    type="button"
                    onClick={() => set('transport_mode', val)}
                    className={`py-2.5 rounded-lg text-sm font-medium border transition-colors ${
                      mode === val
                        ? 'border-primary-500 bg-primary-50 text-primary-700'
                        : 'border-gray-200 text-gray-500 hover:border-gray-300'
                    }`}
                  >
                    {label}
                  </button>
                ))}
              </div>
            </div>

            {/* ── 基本資訊 ── */}
            <div>
              <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">
                {t('basicInfo')}
              </p>
              <div className="grid grid-cols-2 gap-3">
                <div className="col-span-2">
                  <label className={LABEL}>{t('exportDate')} <span className="text-red-500">*</span></label>
                  <input type="date" value={form.export_date}
                    onChange={(e) => set('export_date', e.target.value)}
                    required className="input" />
                </div>
                <div>
                  <label className={LABEL}>{t('carrier')}<span className={OPT}>{tc('optional')}</span></label>
                  <input type="text" value={form.carrier}
                    onChange={(e) => set('carrier', e.target.value)}
                    className="input" placeholder={mode === 'air' ? 'Thai Airways...' : 'Maersk...'} />
                </div>
                <div>
                  <label className={LABEL}>{t('shippedBoxes')}<span className={OPT}>{tc('optional')}</span></label>
                  <input type="number" min="0" value={form.shipped_boxes}
                    onChange={(e) => set('shipped_boxes', e.target.value)}
                    className="input" placeholder="0" />
                </div>
                <div>
                  <label className={LABEL}>{t('shipperName')}<span className={OPT}>{tc('optional')}</span></label>
                  <input type="text" value={form.shipper_name}
                    onChange={(e) => set('shipper_name', e.target.value)}
                    className="input" />
                </div>
                <div>
                  <label className={LABEL}>{t('estimatedArrivalTW')}<span className={OPT}>{tc('optional')}</span></label>
                  <input type="date" value={form.estimated_arrival_tw}
                    onChange={(e) => set('estimated_arrival_tw', e.target.value)}
                    className="input" />
                </div>
              </div>
            </div>

            {/* ── 空運專屬欄位 ── */}
            {mode === 'air' && (
              <div>
                <p className="text-xs font-semibold text-sky-500 uppercase tracking-wider mb-3 flex items-center gap-1">
                  ✈️ 空運資訊
                </p>
                <div className="grid grid-cols-2 gap-3">
                  <div className="col-span-2">
                    <label className={LABEL}>AWB 提單號<span className={OPT}>{tc('optional')}</span></label>
                    <input type="text" value={form.awb_no}
                      onChange={(e) => set('awb_no', e.target.value)}
                      className="input" placeholder="000-12345678" />
                  </div>
                  <div>
                    <label className={LABEL}>航空公司<span className={OPT}>{tc('optional')}</span></label>
                    <input type="text" value={form.airline}
                      onChange={(e) => set('airline', e.target.value)}
                      className="input" placeholder="Thai Airways..." />
                  </div>
                  <div>
                    <label className={LABEL}>航班號<span className={OPT}>{tc('optional')}</span></label>
                    <input type="text" value={form.flight_no}
                      onChange={(e) => set('flight_no', e.target.value)}
                      className="input" placeholder="TG635" />
                  </div>
                </div>
              </div>
            )}

            {/* ── 海運專屬欄位 ── */}
            {mode === 'sea' && (
              <div>
                <p className="text-xs font-semibold text-blue-500 uppercase tracking-wider mb-3 flex items-center gap-1">
                  🚢 海運資訊
                </p>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className={LABEL}>{t('vesselName')}<span className={OPT}>{tc('optional')}</span></label>
                    <input type="text" value={form.vessel_name}
                      onChange={(e) => set('vessel_name', e.target.value)}
                      className="input" />
                  </div>
                  <div>
                    <label className={LABEL}>{t('blNo')}<span className={OPT}>{tc('optional')}</span></label>
                    <input type="text" value={form.bl_no}
                      onChange={(e) => set('bl_no', e.target.value)}
                      className="input" />
                  </div>
                  <div className="col-span-2">
                    <label className={LABEL}>貨櫃號碼<span className={OPT}>{tc('optional')}</span></label>
                    <input type="text" value={form.container_no}
                      onChange={(e) => set('container_no', e.target.value)}
                      className="input" placeholder="MSCU1234567" />
                  </div>
                  <div>
                    <label className={LABEL}>裝載港（泰國）<span className={OPT}>{tc('optional')}</span></label>
                    <input type="text" value={form.port_of_loading}
                      onChange={(e) => set('port_of_loading', e.target.value)}
                      className="input" placeholder="Laem Chabang" />
                  </div>
                  <div>
                    <label className={LABEL}>卸貨港（台灣）<span className={OPT}>{tc('optional')}</span></label>
                    <input type="text" value={form.port_of_discharge}
                      onChange={(e) => set('port_of_discharge', e.target.value)}
                      className="input" placeholder="Keelung / Taichung" />
                  </div>
                </div>
              </div>
            )}

            {/* ── 費用 ── */}
            <div>
              <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">
                {t('costs')}
              </p>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className={LABEL}>
                    {mode === 'air' ? '空運費（THB）' : '海運費（THB）'}
                    <span className={OPT}>{tc('optional')}</span>
                  </label>
                  <input type="number" step="0.01" min="0"
                    value={form.freight_cost}
                    onChange={(e) => set('freight_cost', e.target.value)}
                    className="input" placeholder="0.00" />
                </div>
                <div>
                  <label className={LABEL}>{t('customsCost')}（TWD）<span className={OPT}>{tc('optional')}</span></label>
                  <input type="number" step="0.01" min="0"
                    value={form.customs_cost}
                    onChange={(e) => set('customs_cost', e.target.value)}
                    className="input" placeholder="0.00" />
                </div>
                <div>
                  <label className={LABEL}>保險費（TWD）<span className={OPT}>{tc('optional')}</span></label>
                  <input type="number" step="0.01" min="0"
                    value={form.insurance_cost}
                    onChange={(e) => set('insurance_cost', e.target.value)}
                    className="input" placeholder="0.00" />
                </div>
                <div>
                  <label className={LABEL}>搬運/倉儲費（TWD）<span className={OPT}>{tc('optional')}</span></label>
                  <input type="number" step="0.01" min="0"
                    value={form.handling_cost}
                    onChange={(e) => set('handling_cost', e.target.value)}
                    className="input" placeholder="0.00" />
                </div>
                <div className="col-span-2">
                  <label className={LABEL}>其他費用（TWD）<span className={OPT}>{tc('optional')}</span></label>
                  <input type="number" step="0.01" min="0"
                    value={form.other_cost}
                    onChange={(e) => set('other_cost', e.target.value)}
                    className="input" placeholder="0.00" />
                </div>
                {/* 費用小計 */}
                {(form.customs_cost || form.insurance_cost || form.handling_cost || form.other_cost) && (
                  <div className="col-span-2 bg-gray-50 rounded-lg px-4 py-2.5 text-sm">
                    <div className="flex justify-between font-semibold text-gray-700">
                      <span>台灣端費用合計（TWD）</span>
                      <span>
                        NT${(
                          (parseFloat(form.customs_cost  || '0')) +
                          (parseFloat(form.insurance_cost || '0')) +
                          (parseFloat(form.handling_cost  || '0')) +
                          (parseFloat(form.other_cost     || '0'))
                        ).toLocaleString()}
                      </span>
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* ── 關聯批次（新建時顯示）── */}
            {!isEdit && (
              <div>
                <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">
                  {t('selectBatches')}
                </p>
                {availBatches.length === 0 ? (
                  <div className="p-4 bg-yellow-50 border border-yellow-200 rounded-lg text-sm text-yellow-700">
                    {t('noBatchAvailable')}
                  </div>
                ) : (
                  <div className="space-y-2 max-h-48 overflow-y-auto">
                    {availBatches.map((b) => {
                      const checked = selectedIds.has(b.id);
                      return (
                        <button
                          key={b.id}
                          type="button"
                          onClick={() => toggleBatch(b.id)}
                          className={`w-full flex items-center gap-3 p-3 rounded-lg border transition-colors text-left ${
                            checked ? 'border-primary-400 bg-primary-50' : 'border-gray-200 hover:border-gray-300'
                          }`}
                        >
                          <div className={`w-5 h-5 rounded flex items-center justify-center flex-shrink-0 ${
                            checked ? 'bg-primary-600' : 'border-2 border-gray-300'
                          }`}>
                            {checked && <Check size={12} className="text-white" />}
                          </div>
                          <div className="flex-1 min-w-0">
                            <p className="font-mono text-sm font-semibold text-gray-700">{b.batch_no}</p>
                            <p className="text-xs text-gray-400">{Number(b.current_weight).toLocaleString()} kg</p>
                          </div>
                        </button>
                      );
                    })}
                  </div>
                )}
                {selectedIds.size > 0 && (
                  <p className="text-xs text-primary-600 mt-2">{selectedIds.size} {t('linkedBatches')}</p>
                )}
              </div>
            )}

            {/* ── 備註 ── */}
            <div>
              <label className={LABEL}>{t('notes')}</label>
              <textarea value={form.notes} onChange={(e) => set('notes', e.target.value)}
                rows={3} className="input resize-none" />
            </div>

            {error && (
              <div className="bg-red-50 border border-red-200 text-red-600 text-sm px-4 py-2 rounded-md">
                {error}
              </div>
            )}
          </div>

          {/* 底部按鈕 */}
          <div className="flex justify-end gap-3 px-6 py-4 border-t border-gray-200">
            <button type="button" onClick={() => onClose()} className="btn-secondary">
              {tc('cancel')}
            </button>
            <button type="submit" disabled={loading} className="btn-primary">
              {loading ? '...' : tc('save')}
            </button>
          </div>
        </form>
      </div>
    </>
  );
}
