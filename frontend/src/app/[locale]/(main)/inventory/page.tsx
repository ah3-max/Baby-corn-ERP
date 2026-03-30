'use client';

/**
 * 台灣庫存管理頁 /inventory
 * Module L — 三頁籤:
 *   庫存列表 | 入庫作業 | 倉庫管理
 */
import { useEffect, useState, useCallback } from 'react';
import { useLocale, useTranslations } from 'next-intl';
import Link from 'next/link';
import {
  Warehouse, Package, Plus, ChevronDown, ChevronUp,
  AlertTriangle, CheckCircle, Clock, Trash2, SlidersHorizontal,
  ArrowDownToLine, X, RefreshCw, Truck, Zap, Info,
} from 'lucide-react';
import { inventoryApi, batchesApi, shipmentsApi } from '@/lib/api';
import { exportInventoryToExcel } from '@/lib/exportExcel';
import type {
  InventoryLot, InventorySummary, Warehouse as WH,
  WarehouseLocation, Batch, Shipment,
} from '@/types';

// ─── Age badge ────────────────────────────────────────────────────────────────
function AgeBadge({ days }: { days: number }) {
  if (days <= 30)
    return <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-700">🟢 {days}d</span>;
  if (days <= 60)
    return <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-700">🟡 {days}d</span>;
  return <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-700">🔴 {days}d</span>;
}

// ─── Status badge ──────────────────────────────────────────────────────────────
const LOT_STATUS_STYLES: Record<string, string> = {
  active:    'bg-green-100 text-green-700',
  low_stock: 'bg-yellow-100 text-yellow-700',
  depleted:  'bg-gray-100 text-gray-500',
  scrapped:  'bg-red-100 text-red-600',
};
const LOT_STATUS_LABELS: Record<string, string> = {
  active: '正常', low_stock: '低庫存', depleted: '已出清', scrapped: '已報廢',
};

// ─── Quick Receive Modal ──────────────────────────────────────────────────────
interface QuickReceivePayload {
  batchId: string;
  batchNo: string;
  supplierName: string;
  currentWeight: number;
  arrivalDate: string;    // from shipment actual_arrival_tw or today
  importType: string;     // from shipment transport_mode: 'air' | 'sea' | ''
  shipmentId: string;     // from shipment id（關聯出口單）
  shipmentNo: string;     // 出口單編號（顯示用）
}

function QuickReceiveModal({
  prefill,
  warehouses,
  onClose,
  onDone,
}: {
  prefill: QuickReceivePayload;
  warehouses: WH[];
  onClose: () => void;
  onDone: () => void;
}) {
  const t = useTranslations('inventory');
  const tc = useTranslations('common');
  const [locations, setLocations] = useState<WarehouseLocation[]>([]);
  const [form, setForm] = useState({
    warehouse_id: '',
    location_id: '',
    spec: '',
    received_date: prefill.arrivalDate,
    initial_weight_kg: String(prefill.currentWeight),
    initial_boxes: '',
    notes: '',
    import_type: prefill.importType,      // 自動帶入出口單運輸方式
    customs_declaration_no: '',
    customs_clearance_date: '',
    inspection_result: '',
    received_by: '',
  });
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState('');

  const set = (k: keyof typeof form, v: string) => setForm(f => ({ ...f, [k]: v }));

  // 自動選倉庫：只有一個倉庫時直接選上並載入庫位
  useEffect(() => {
    if (warehouses.length === 1) {
      const wh = warehouses[0];
      setForm(f => ({ ...f, warehouse_id: wh.id, location_id: '' }));
      inventoryApi.listLocations(wh.id).then(res => setLocations(res.data));
    }
  }, [warehouses]);

  const onWarehouseChange = async (whId: string) => {
    set('warehouse_id', whId);
    set('location_id', '');
    if (whId) {
      const res = await inventoryApi.listLocations(whId);
      setLocations(res.data);
    } else {
      setLocations([]);
    }
  };

  // 庫位自動選：若該倉庫只有一個庫位，自動帶入
  useEffect(() => {
    if (locations.length === 1) {
      setForm(f => ({ ...f, location_id: locations[0].id }));
    }
  }, [locations]);

  const submit = async () => {
    if (!form.warehouse_id) { setErr(t('errSelectWarehouse')); return; }
    if (!form.initial_weight_kg) { setErr(t('errFillWeight')); return; }
    const kg = parseFloat(form.initial_weight_kg);
    if (isNaN(kg) || kg <= 0) { setErr(t('errWeightPositive')); return; }
    setSaving(true);
    try {
      await inventoryApi.createLot({
        batch_id: prefill.batchId,
        warehouse_id: form.warehouse_id,
        location_id: form.location_id || null,
        spec: form.spec || null,
        received_date: form.received_date,
        initial_weight_kg: kg,
        initial_boxes: form.initial_boxes ? parseInt(form.initial_boxes) : null,
        notes: form.notes || null,
        import_type: form.import_type || null,
        customs_declaration_no: form.customs_declaration_no || null,
        customs_clearance_date: form.customs_clearance_date || null,
        inspection_result: form.inspection_result || null,
        received_by: form.received_by || null,
        shipment_id: prefill.shipmentId || null,   // 關聯出口單
      });
      onDone();
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setErr(msg || t('receiveFailed'));
    } finally { setSaving(false); }
  };

  return (
    <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-md p-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="font-bold text-gray-800 text-lg">{t('quickReceiveTitle')}</h3>
            <p className="text-xs text-gray-400 mt-0.5">{t('quickReceiveHint')}</p>
          </div>
          <button onClick={onClose}><X size={18} className="text-gray-400" /></button>
        </div>

        {/* Batch info summary */}
        <div className="bg-blue-50 border border-blue-100 rounded-xl px-4 py-3 mb-5">
          <p className="text-xs text-blue-600 font-semibold mb-1">{t('batchInfoConfirmed')}</p>
          <div className="flex justify-between text-sm">
            <span className="font-mono font-bold text-blue-800">{prefill.batchNo}</span>
            <span className="text-blue-600">{prefill.supplierName}</span>
          </div>
          <p className="text-xs text-blue-500 mt-0.5">{t('batchStockWeight')}：<strong>{prefill.currentWeight} kg</strong></p>
          {prefill.shipmentNo && (
            <div className="flex items-center gap-2 mt-1.5 pt-1.5 border-t border-blue-100">
              <span className="text-xs text-blue-400">
                {prefill.importType === 'air' ? '✈️ 空運' : prefill.importType === 'sea' ? '🚢 海運' : ''}
              </span>
              <span className="text-xs text-blue-500 font-mono">{prefill.shipmentNo}</span>
              <span className="text-xs text-blue-400">· 到港：{prefill.arrivalDate}</span>
            </div>
          )}
        </div>

        <div className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-medium text-gray-600 mb-1 block">{t('warehouseRequired')}</label>
              {warehouses.length === 0 ? (
                <p className="text-xs text-orange-500 bg-orange-50 rounded-lg p-2">
                  ⚠️ {t('noWarehouseWarning')}
                </p>
              ) : (
                <select value={form.warehouse_id} onChange={e => onWarehouseChange(e.target.value)} className="input w-full text-sm">
                  <option value="">{t('selectWarehouse')}</option>
                  {warehouses.map(w => <option key={w.id} value={w.id}>{w.name}</option>)}
                </select>
              )}
            </div>
            <div>
              <label className="text-xs font-medium text-gray-600 mb-1 block">{t('locationOptional')}</label>
              <select value={form.location_id} onChange={e => set('location_id', e.target.value)} className="input w-full text-sm" disabled={!form.warehouse_id}>
                <option value="">{t('selectLocation')}</option>
                {locations.map(l => <option key={l.id} value={l.id}>{l.name}</option>)}
              </select>
            </div>
          </div>

          <div>
            <label className="text-xs font-medium text-gray-600 mb-1 block">{t('specOptional')}</label>
            <input value={form.spec} onChange={e => set('spec', e.target.value)} className="input w-full" placeholder={t('specPlaceholder')} />
          </div>

          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="text-xs font-medium text-gray-600 mb-1 block">{t('receivedDate')}</label>
              <input type="date" value={form.received_date} onChange={e => set('received_date', e.target.value)} className="input w-full text-sm" />
            </div>
            <div>
              <label className="text-xs font-medium text-gray-600 mb-1 block">{t('receiveWeightKg')}</label>
              <input type="number" step="0.01" min="0.01" value={form.initial_weight_kg} onChange={e => set('initial_weight_kg', e.target.value)} className="input w-full" />
            </div>
            <div>
              <label className="text-xs font-medium text-gray-600 mb-1 block">{t('boxesOptional')}</label>
              <input type="number" min="1" value={form.initial_boxes} onChange={e => set('initial_boxes', e.target.value)} className="input w-full" placeholder="0" />
            </div>
          </div>

          <div>
            <label className="text-xs font-medium text-gray-600 mb-1 block">{t('notesOptional')}</label>
            <textarea value={form.notes} onChange={e => set('notes', e.target.value)} className="input w-full h-16 resize-none" placeholder={t('notesPlaceholder')} />
          </div>

          {/* Module K fields */}
          <div>
            <label className="text-xs font-medium text-gray-600 mb-1 block">{t('importType')}</label>
            <select value={form.import_type} onChange={e => set('import_type', e.target.value)} className="input w-full text-sm">
              <option value="">{t('importTypeNone')}</option>
              <option value="air">✈️ {t('importTypeAir')}</option>
              <option value="sea">🚢 {t('importTypeSea')}</option>
            </select>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-medium text-gray-600 mb-1 block">{t('customsDeclarationNo')}</label>
              <input value={form.customs_declaration_no} onChange={e => set('customs_declaration_no', e.target.value)} className="input w-full" placeholder={t('customsDeclarationNo')} />
            </div>
            <div>
              <label className="text-xs font-medium text-gray-600 mb-1 block">{t('customsClearanceDate')}</label>
              <input type="date" value={form.customs_clearance_date} onChange={e => set('customs_clearance_date', e.target.value)} className="input w-full" />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-medium text-gray-600 mb-1 block">{t('inspectionResult')}</label>
              <select value={form.inspection_result} onChange={e => set('inspection_result', e.target.value)} className="input w-full text-sm">
                <option value="">{t('inspectionNone')}</option>
                <option value="pass">✅ {t('inspectionPass')}</option>
                <option value="fail">❌ {t('inspectionFail')}</option>
                <option value="pending">⏳ {t('inspectionPending')}</option>
                <option value="exempted">⭕ {t('inspectionExempted')}</option>
              </select>
            </div>
            <div>
              <label className="text-xs font-medium text-gray-600 mb-1 block">{t('receivedBy')}</label>
              <input value={form.received_by} onChange={e => set('received_by', e.target.value)} className="input w-full" placeholder={t('receivedByPlaceholder')} />
            </div>
          </div>
        </div>

        {err && <p className="text-xs text-red-600 mt-2">{err}</p>}
        <div className="flex gap-2 mt-5">
          <button onClick={onClose} className="btn-secondary flex-1">{tc('cancel')}</button>
          <button onClick={submit} disabled={saving || warehouses.length === 0} className="btn-primary flex-1 flex items-center justify-center gap-2">
            <ArrowDownToLine size={15} />
            {saving ? t('receiving') : t('confirmReceive')}
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── Scrap Modal ──────────────────────────────────────────────────────────────
function ScrapModal({
  lot, onClose, onDone,
}: { lot: InventoryLot; onClose: () => void; onDone: () => void }) {
  const t = useTranslations('inventory');
  const tc = useTranslations('common');
  const [weight, setWeight] = useState('');
  const [reason, setReason] = useState('');
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState('');

  const submit = async () => {
    if (!weight || !reason) { setErr(t('errFillScrap')); return; }
    const kg = parseFloat(weight);
    if (isNaN(kg) || kg <= 0) { setErr(t('errWeightPositive')); return; }
    if (kg > lot.current_weight_kg) { setErr(t('errExceedStock', { weight: lot.current_weight_kg })); return; }
    setSaving(true);
    try {
      await inventoryApi.scrapLot(lot.id, { weight_kg: kg, reason });
      onDone();
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setErr(msg || t('scrapFailed'));
    } finally { setSaving(false); }
  };

  return (
    <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-sm p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-bold text-gray-800 text-lg">{t('scrapRecord')}</h3>
          <button onClick={onClose}><X size={18} className="text-gray-400" /></button>
        </div>
        <p className="text-sm text-gray-500 mb-4">{t('lotNo')}：<span className="font-mono font-semibold text-gray-700">{lot.lot_no}</span>　{t('inStock')}：{lot.current_weight_kg} kg</p>
        <div className="space-y-3">
          <div>
            <label className="text-xs font-medium text-gray-600 mb-1 block">{t('scrapWeightKg')}</label>
            <input type="number" step="0.01" min="0.01" value={weight} onChange={e => setWeight(e.target.value)} className="input w-full" placeholder="0.00" />
          </div>
          <div>
            <label className="text-xs font-medium text-gray-600 mb-1 block">{t('scrapReason')}</label>
            <textarea value={reason} onChange={e => setReason(e.target.value)} className="input w-full h-20 resize-none" placeholder={t('scrapReasonPlaceholder')} />
          </div>
        </div>
        {err && <p className="text-xs text-red-600 mt-2">{err}</p>}
        <div className="flex gap-2 mt-5">
          <button onClick={onClose} className="btn-secondary flex-1">{tc('cancel')}</button>
          <button onClick={submit} disabled={saving} className="btn-primary flex-1 bg-red-600 hover:bg-red-700 border-red-600">
            {saving ? t('saving') : t('confirmScrap')}
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── Adjust Modal ─────────────────────────────────────────────────────────────
function AdjustModal({
  lot, onClose, onDone,
}: { lot: InventoryLot; onClose: () => void; onDone: () => void }) {
  const t = useTranslations('inventory');
  const tc = useTranslations('common');
  const [weight, setWeight] = useState('');
  const [boxes, setBoxes] = useState('');
  const [reason, setReason] = useState('');
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState('');

  const submit = async () => {
    if (!weight || !reason) { setErr(t('errFillAdjust')); return; }
    const delta = parseFloat(weight);
    if (isNaN(delta)) { setErr(t('errValidNumber')); return; }
    if (lot.current_weight_kg + delta < 0) { setErr(t('errNegativeStock', { weight: lot.current_weight_kg })); return; }
    setSaving(true);
    try {
      await inventoryApi.adjustLot(lot.id, {
        weight_kg: delta,
        boxes: boxes ? parseInt(boxes) : undefined,
        reason,
      });
      onDone();
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setErr(msg || t('adjustFailed'));
    } finally { setSaving(false); }
  };

  return (
    <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-sm p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-bold text-gray-800 text-lg">{t('adjustTitle')}</h3>
          <button onClick={onClose}><X size={18} className="text-gray-400" /></button>
        </div>
        <p className="text-sm text-gray-500 mb-4">{t('lotNo')}：<span className="font-mono font-semibold text-gray-700">{lot.lot_no}</span>　{t('current')}：{lot.current_weight_kg} kg / {lot.current_boxes ?? '—'} {t('boxes')}</p>
        <div className="space-y-3">
          <div>
            <label className="text-xs font-medium text-gray-600 mb-1 block">{t('adjustWeightLabel')}</label>
            <input type="number" step="0.01" value={weight} onChange={e => setWeight(e.target.value)} className="input w-full" placeholder={t('adjustWeightPlaceholder')} />
          </div>
          <div>
            <label className="text-xs font-medium text-gray-600 mb-1 block">{t('adjustBoxesLabel')}</label>
            <input type="number" value={boxes} onChange={e => setBoxes(e.target.value)} className="input w-full" placeholder="0" />
          </div>
          <div>
            <label className="text-xs font-medium text-gray-600 mb-1 block">{t('adjustReason')}</label>
            <textarea value={reason} onChange={e => setReason(e.target.value)} className="input w-full h-20 resize-none" placeholder={t('adjustReasonPlaceholder')} />
          </div>
        </div>
        {err && <p className="text-xs text-red-600 mt-2">{err}</p>}
        <div className="flex gap-2 mt-5">
          <button onClick={onClose} className="btn-secondary flex-1">{tc('cancel')}</button>
          <button onClick={submit} disabled={saving} className="btn-primary flex-1">
            {saving ? t('saving') : t('confirmAdjust')}
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── Lot Row (expandable) ─────────────────────────────────────────────────────
function LotRow({
  lot, onScrap, onAdjust,
}: { lot: InventoryLot; onScrap: (l: InventoryLot) => void; onAdjust: (l: InventoryLot) => void }) {
  const t = useTranslations('inventory');
  const [expanded, setExpanded] = useState(false);
  const locale = useLocale();

  const shippedPct = lot.initial_weight_kg > 0
    ? Math.round((lot.shipped_weight_kg / lot.initial_weight_kg) * 100) : 0;

  return (
    <>
      <div className="grid grid-cols-[1.8fr_1.2fr_1fr_1fr_1fr_1.2fr_auto] gap-3 px-5 py-3.5 items-center hover:bg-gray-50 transition-colors border-b border-gray-100">
        <div>
          <div className="flex items-center gap-1.5">
            <p className="font-mono text-sm font-semibold text-primary-600">{lot.lot_no}</p>
            {lot.import_type && (
              <span className="text-xs text-gray-400">{lot.import_type === 'air' ? '✈️' : '🚢'}</span>
            )}
          </div>
          <p className="text-xs text-gray-400 mt-0.5">
            {lot.batch ? (
              <Link href={`/${locale}/batches/${lot.batch_id}`} className="hover:underline text-gray-500">{lot.batch.batch_no}</Link>
            ) : '—'}
          </p>
          {lot.spec && <p className="text-xs text-gray-400 truncate max-w-[140px]">{lot.spec}</p>}
          <div className="flex items-center gap-1 mt-0.5">
            {lot.inspection_result && (
              <span className={`text-[10px] px-1.5 py-0.5 rounded font-medium ${
                lot.inspection_result === 'pass' ? 'bg-green-100 text-green-700' :
                lot.inspection_result === 'fail' ? 'bg-red-100 text-red-700' :
                'bg-gray-100 text-gray-500'
              }`}>{lot.inspection_result === 'pass' ? '通過' : lot.inspection_result === 'fail' ? '不通過' : lot.inspection_result}</span>
            )}
            {lot.customs_declaration_no && (
              <span className="text-[10px] text-gray-400">{lot.customs_declaration_no}</span>
            )}
          </div>
        </div>
        <div className="text-sm text-gray-700">
          <p>{lot.warehouse?.name ?? '—'}</p>
          {lot.location && <p className="text-xs text-gray-400">{lot.location.name}</p>}
        </div>
        <div>
          <p className="text-xs text-gray-500">{lot.received_date}</p>
          <div className="mt-0.5"><AgeBadge days={lot.age_days} /></div>
        </div>
        <div className="text-right">
          <p className="font-semibold text-sm text-gray-800">{lot.current_weight_kg.toLocaleString()} kg</p>
          {lot.current_boxes !== null && <p className="text-xs text-gray-400">{lot.current_boxes} {t('boxes')}</p>}
        </div>
        <div className="text-right">
          <p className="text-sm text-gray-500">{lot.shipped_weight_kg.toLocaleString()} kg</p>
          <p className="text-xs text-gray-400">{shippedPct}%</p>
        </div>
        <div>
          <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${LOT_STATUS_STYLES[lot.status] ?? ''}`}>
            {t(`lotStatus.${lot.status}`)}
          </span>
        </div>
        <div className="flex items-center gap-1">
          <button onClick={() => onAdjust(lot)} title={t('adjustTitle')} className="p-1.5 rounded-lg text-gray-400 hover:text-blue-600 hover:bg-blue-50 transition-colors"><SlidersHorizontal size={14} /></button>
          {lot.status !== 'scrapped' && lot.status !== 'depleted' && (
            <button onClick={() => onScrap(lot)} title={t('scrap')} className="p-1.5 rounded-lg text-gray-400 hover:text-red-600 hover:bg-red-50 transition-colors"><Trash2 size={14} /></button>
          )}
          <button onClick={() => setExpanded(p => !p)} className="p-1.5 rounded-lg text-gray-400 hover:text-gray-700 hover:bg-gray-100 transition-colors">
            {expanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
          </button>
        </div>
      </div>

      {expanded && (
        <div className="bg-gray-50 border-b border-gray-100 px-8 py-3">
          {lot.transactions.length === 0 ? (
            <p className="text-xs text-gray-400">{t('noTransactions')}</p>
          ) : (
            <table className="w-full text-xs">
              <thead>
                <tr className="text-gray-400 font-semibold uppercase tracking-wider">
                  <th className="text-left pb-1">{t('txnType')}</th>
                  <th className="text-right pb-1">{t('weight')}</th>
                  <th className="text-right pb-1">{t('boxes')}</th>
                  <th className="text-left pb-1 pl-4">{t('reasonNotes')}</th>
                  <th className="text-right pb-1">{t('time')}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {lot.transactions.map(tx => (
                  <tr key={tx.id} className="text-gray-600">
                    <td className="py-1">
                      <span className={`font-semibold ${
                        tx.txn_type === 'in' ? 'text-green-600' :
                        tx.txn_type === 'out' ? 'text-blue-600' :
                        tx.txn_type === 'scrap' ? 'text-red-500' : 'text-orange-500'
                      }`}>
                        {t(`txn.${tx.txn_type}`)}
                      </span>
                    </td>
                    <td className="text-right py-1">{tx.weight_kg} kg</td>
                    <td className="text-right py-1">{tx.boxes ?? '—'}</td>
                    <td className="pl-4 py-1 text-gray-400">{tx.reason ?? tx.reference ?? '—'}</td>
                    <td className="text-right py-1 text-gray-400">{new Date(tx.created_at).toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </>
  );
}

// ─── Tab: 庫存列表 ─────────────────────────────────────────────────────────────
function LotsTab() {
  const t = useTranslations('inventory');
  const [lots, setLots] = useState<InventoryLot[]>([]);
  const [summary, setSummary] = useState<InventorySummary | null>(null);
  const [warehouses, setWarehouses] = useState<WH[]>([]);
  const [loading, setLoading] = useState(true);
  const [filterWarehouse, setFilterWarehouse] = useState('');
  const [filterStatus, setFilterStatus] = useState('');
  const [scrapLot, setScrapLot] = useState<InventoryLot | null>(null);
  const [adjustLot, setAdjustLot] = useState<InventoryLot | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [lotsRes, sumRes, whRes] = await Promise.all([
        inventoryApi.listLots({ warehouse_id: filterWarehouse || undefined, status: filterStatus || undefined }),
        inventoryApi.summary(),
        inventoryApi.listWarehouses(),
      ]);
      setLots(lotsRes.data);
      setSummary(sumRes.data);
      setWarehouses(whRes.data);
    } catch (e) { console.error(e); }
    finally { setLoading(false); }
  }, [filterWarehouse, filterStatus]);

  useEffect(() => { load(); }, [load]);
  const onDone = () => { setScrapLot(null); setAdjustLot(null); load(); };

  return (
    <div>
      {summary && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <div className="card p-4 bg-gradient-to-br from-green-50 to-emerald-50 border-green-200">
            <p className="text-xs text-green-600 font-medium">{t('totalStockWeight')}</p>
            <p className="text-2xl font-bold text-green-700 mt-1">{summary.total_weight_kg.toLocaleString()} <span className="text-sm font-normal">kg</span></p>
            <p className="text-xs text-green-500 mt-0.5">{summary.total_boxes} {t('boxes')} · {summary.lot_count} {t('lots')}</p>
          </div>
          <div className="card p-4">
            <p className="text-xs text-gray-500 font-medium flex items-center gap-1"><CheckCircle size={12} className="text-green-500" /> {t('ageOk')}</p>
            <p className="text-2xl font-bold text-gray-700 mt-1">{summary.age_ok}</p>
          </div>
          <div className="card p-4">
            <p className="text-xs text-gray-500 font-medium flex items-center gap-1"><Clock size={12} className="text-yellow-500" /> {t('ageWarning')}</p>
            <p className="text-2xl font-bold text-yellow-600 mt-1">{summary.age_warning}</p>
          </div>
          <div className="card p-4">
            <p className="text-xs text-gray-500 font-medium flex items-center gap-1"><AlertTriangle size={12} className="text-red-500" /> {t('ageAlert')}</p>
            <p className="text-2xl font-bold text-red-600 mt-1">{summary.age_alert}</p>
          </div>
        </div>
      )}

      <div className="flex flex-wrap gap-2 mb-4 items-center">
        <select value={filterWarehouse} onChange={e => setFilterWarehouse(e.target.value)} className="input text-sm py-1.5 w-40">
          <option value="">{t('allWarehouses')}</option>
          {warehouses.map(w => <option key={w.id} value={w.id}>{w.name}</option>)}
        </select>
        <select value={filterStatus} onChange={e => setFilterStatus(e.target.value)} className="input text-sm py-1.5 w-36">
          <option value="">{t('lotStatus.activeAndLow')}</option>
          <option value="active">{t('lotStatus.active')}</option>
          <option value="low_stock">{t('lotStatus.low_stock')}</option>
          <option value="depleted">{t('lotStatus.depleted')}</option>
          <option value="scrapped">{t('lotStatus.scrapped')}</option>
        </select>
        <button onClick={load} className="btn-secondary flex items-center gap-1.5 py-1.5 px-3 text-sm"><RefreshCw size={13} /> {t('refresh')}</button>
        <button onClick={() => exportInventoryToExcel(lots)} disabled={lots.length === 0} className="btn-secondary flex items-center gap-1.5 py-1.5 px-3 text-sm">
          📊 {t('exportExcel')}
        </button>
        <span className="ml-auto text-xs text-gray-400">{t('totalRecords', { count: lots.length })} · {t('fifoHint')}</span>
      </div>

      {loading ? (
        <div className="text-center py-16 text-gray-400">{t('loading')}</div>
      ) : lots.length === 0 ? (
        <div className="flex flex-col items-center py-20 text-gray-400">
          <Package size={40} className="mb-3 opacity-30" />
          <p>{t('noLots')}</p>
        </div>
      ) : (
        <div className="bg-white rounded-2xl border border-gray-200 overflow-hidden">
          <div className="grid grid-cols-[1.8fr_1.2fr_1fr_1fr_1fr_1.2fr_auto] gap-3 px-5 py-2.5 bg-gray-50 border-b border-gray-200 text-xs font-semibold text-gray-500 uppercase tracking-wider">
            <div>{t('colLotBatch')}</div><div>{t('colWarehouseLocation')}</div><div>{t('colDateAge')}</div>
            <div className="text-right">{t('colStockWeight')}</div><div className="text-right">{t('colShipped')}</div>
            <div>{t('colStatus')}</div><div></div>
          </div>
          {lots.map(lot => <LotRow key={lot.id} lot={lot} onScrap={setScrapLot} onAdjust={setAdjustLot} />)}
        </div>
      )}

      {scrapLot && <ScrapModal lot={scrapLot} onClose={() => setScrapLot(null)} onDone={onDone} />}
      {adjustLot && <AdjustModal lot={adjustLot} onClose={() => setAdjustLot(null)} onDone={onDone} />}
    </div>
  );
}

// ─── Pending batch card ───────────────────────────────────────────────────────
function PendingBatchCard({
  batch,
  arrivalDate,
  importType,
  shipmentId,
  shipmentNo,
  onReceive,
}: {
  batch: Batch;
  arrivalDate: string;
  importType: string;
  shipmentId: string;
  shipmentNo: string;
  onReceive: (p: QuickReceivePayload) => void;
}) {
  const t = useTranslations('inventory');
  return (
    <div className="bg-white border border-gray-200 rounded-xl p-4 flex items-center gap-4 hover:border-primary-300 transition-colors">
      <div className="w-10 h-10 rounded-xl bg-green-100 flex items-center justify-center flex-shrink-0">
        <Package size={18} className="text-green-600" />
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <p className="font-mono font-bold text-sm text-gray-800">{batch.batch_no}</p>
          {importType === 'air' && <span className="text-xs text-sky-500">✈️ 空運</span>}
          {importType === 'sea' && <span className="text-xs text-blue-500">🚢 海運</span>}
        </div>
        <p className="text-xs text-gray-500 truncate">
          {batch.purchase_order?.supplier?.name ?? '—'} · {shipmentNo || batch.purchase_order?.order_no || '—'}
        </p>
        <p className="text-xs text-green-600 font-medium mt-0.5">{Number(batch.current_weight).toLocaleString()} kg {t('availableToReceive')}</p>
      </div>
      <div className="text-right mr-2">
        <p className="text-xs text-gray-400">{t('arrivalDateTW')}</p>
        <p className="text-xs font-semibold text-gray-600">{arrivalDate}</p>
      </div>
      <button
        onClick={() => onReceive({
          batchId: batch.id,
          batchNo: batch.batch_no,
          supplierName: batch.purchase_order?.supplier?.name ?? '—',
          currentWeight: Number(batch.current_weight),
          arrivalDate,
          importType,
          shipmentId,
          shipmentNo,
        })}
        className="btn-primary flex items-center gap-1.5 text-sm py-1.5 px-3 flex-shrink-0"
      >
        <Zap size={13} /> {t('quickReceiveBtn')}
      </button>
    </div>
  );
}

// ─── Tab: 入庫作業 ─────────────────────────────────────────────────────────────
function ReceiveTab({ onReceived }: { onReceived: () => void }) {
  const t = useTranslations('inventory');
  const [warehouses, setWarehouses] = useState<WH[]>([]);
  const [pendingBatches, setPendingBatches] = useState<Batch[]>([]);  // in_stock, no lot yet
  const [transitBatches, setTransitBatches] = useState<Batch[]>([]);  // in_transit_tw
  const [arrivedShipments, setArrivedShipments] = useState<Shipment[]>([]);
  const [loading, setLoading] = useState(true);
  const [quickReceive, setQuickReceive] = useState<QuickReceivePayload | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [whRes, inStockRes, transitRes, lotsRes, shipmentsRes] = await Promise.all([
        inventoryApi.listWarehouses(),
        batchesApi.list({ status: 'in_stock' }),
        batchesApi.list({ status: 'in_transit_tw' }),
        inventoryApi.listLots({ status: 'active' }),
        shipmentsApi.list({ status: 'arrived_tw' }),
      ]);

      setWarehouses(whRes.data);
      setArrivedShipments(shipmentsRes.data);

      // Determine which in_stock batches already have lots
      const batchIdsWithLots = new Set((lotsRes.data as InventoryLot[]).map(l => l.batch_id));
      // Also include depleted lots (they were received)
      const allLotsRes = await inventoryApi.listLots({ status: 'depleted' });
      (allLotsRes.data as InventoryLot[]).forEach(l => batchIdsWithLots.add(l.batch_id));

      const pending = (inStockRes.data as Batch[]).filter(b => !batchIdsWithLots.has(b.id));
      setPendingBatches(pending);
      setTransitBatches(transitRes.data as Batch[]);
    } catch (e) { console.error(e); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); }, [load]);

  // 取得批次對應的出口單資訊（到港日、運輸方式、出口單編號）
  const getShipmentInfo = (batchId: string) => {
    for (const s of arrivedShipments) {
      if (s.shipment_batches?.some(sb => sb.batch_id === batchId)) {
        return {
          arrivalDate: s.actual_arrival_tw ?? new Date().toISOString().split('T')[0],
          importType:  s.transport_mode ?? '',
          shipmentId:  s.id,
          shipmentNo:  s.shipment_no,
        };
      }
    }
    return {
      arrivalDate: new Date().toISOString().split('T')[0],
      importType:  '',
      shipmentId:  '',
      shipmentNo:  '',
    };
  };

  const onDone = () => {
    setQuickReceive(null);
    onReceived();
    load();
  };

  return (
    <div className="space-y-6">
      {/* Flow guide */}
      <div className="bg-blue-50 border border-blue-100 rounded-xl px-4 py-3 flex items-start gap-3">
        <Info size={16} className="text-blue-500 mt-0.5 flex-shrink-0" />
        <div className="text-xs text-blue-700">
          <p className="font-semibold mb-1">{t('flowGuideTitle')}</p>
          <p>{t('flowGuideDesc')}</p>
        </div>
      </div>

      {/* Pending receipt — in_stock batches without lots */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h3 className="font-bold text-gray-800 flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-green-500 inline-block"></span>
            {t('pendingReceive')}
            {!loading && <span className="text-sm font-normal text-gray-400">({pendingBatches.length})</span>}
          </h3>
          <button onClick={load} className="text-xs text-gray-400 hover:text-gray-600 flex items-center gap-1">
            <RefreshCw size={12} /> {t('refresh')}
          </button>
        </div>

        {loading ? (
          <p className="text-sm text-gray-400 py-4">{t('loading')}</p>
        ) : pendingBatches.length === 0 ? (
          <div className="border border-dashed border-gray-200 rounded-xl py-8 flex flex-col items-center text-gray-400">
            <CheckCircle size={28} className="mb-2 text-green-400" />
            <p className="text-sm">{t('allReceived')}</p>
          </div>
        ) : (
          <div className="space-y-2">
            {pendingBatches.map(b => {
              const info = getShipmentInfo(b.id);
              return (
                <PendingBatchCard
                  key={b.id}
                  batch={b}
                  arrivalDate={info.arrivalDate}
                  importType={info.importType}
                  shipmentId={info.shipmentId}
                  shipmentNo={info.shipmentNo}
                  onReceive={setQuickReceive}
                />
              );
            })}
          </div>
        )}
      </div>

      {/* In transit — upcoming */}
      {transitBatches.length > 0 && (
        <div>
          <h3 className="font-bold text-gray-800 flex items-center gap-2 mb-3">
            <span className="w-2 h-2 rounded-full bg-blue-400 inline-block"></span>
            {t('incomingBatches')}
            <span className="text-sm font-normal text-gray-400">({transitBatches.length})</span>
          </h3>
          <div className="space-y-2">
            {transitBatches.map(b => (
              <div key={b.id} className="bg-blue-50 border border-blue-100 rounded-xl p-4 flex items-center gap-4">
                <div className="w-10 h-10 rounded-xl bg-blue-100 flex items-center justify-center flex-shrink-0">
                  <Truck size={18} className="text-blue-500" />
                </div>
                <div className="flex-1">
                  <p className="font-mono font-bold text-sm text-gray-800">{b.batch_no}</p>
                  <p className="text-xs text-gray-500">{b.purchase_order?.supplier?.name ?? '—'} · {b.purchase_order?.order_no ?? '—'}</p>
                  <p className="text-xs text-blue-500 mt-0.5">{Number(b.current_weight).toLocaleString()} kg</p>
                </div>
                <span className="text-xs text-blue-400 bg-blue-100 px-2 py-1 rounded-full">{t('inTransit')}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Warehouse empty warning */}
      {!loading && warehouses.length === 0 && (
        <div className="bg-orange-50 border border-orange-200 rounded-xl px-4 py-3 flex items-start gap-3">
          <AlertTriangle size={16} className="text-orange-500 mt-0.5 flex-shrink-0" />
          <div className="text-xs text-orange-700">
            <p className="font-semibold">{t('noWarehouseTitle')}</p>
            <p>{t('noWarehouseDesc')}</p>
          </div>
        </div>
      )}

      {quickReceive && (
        <QuickReceiveModal
          prefill={quickReceive}
          warehouses={warehouses}
          onClose={() => setQuickReceive(null)}
          onDone={onDone}
        />
      )}
    </div>
  );
}

// ─── Tab: 倉庫管理 ─────────────────────────────────────────────────────────────
function WarehouseTab() {
  const t = useTranslations('inventory');
  const tc = useTranslations('common');
  const [warehouses, setWarehouses] = useState<WH[]>([]);
  const [locations, setLocations] = useState<Record<string, WarehouseLocation[]>>({});
  const [expandedWh, setExpandedWh] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [whName, setWhName] = useState('');
  const [whAddr, setWhAddr] = useState('');
  const [whNote, setWhNote] = useState('');
  const [savingWh, setSavingWh] = useState(false);
  const [locName, setLocName] = useState<Record<string, string>>({});
  const [savingLoc, setSavingLoc] = useState<Record<string, boolean>>({});

  const loadWarehouses = async () => {
    setLoading(true);
    try { const res = await inventoryApi.listWarehouses(); setWarehouses(res.data); }
    finally { setLoading(false); }
  };
  useEffect(() => { loadWarehouses(); }, []);

  const loadLocations = async (whId: string) => {
    const res = await inventoryApi.listLocations(whId);
    setLocations(prev => ({ ...prev, [whId]: res.data }));
  };

  const toggleWh = (whId: string) => {
    if (expandedWh === whId) { setExpandedWh(null); return; }
    setExpandedWh(whId);
    if (!locations[whId]) loadLocations(whId);
  };

  const createWarehouse = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!whName) return;
    setSavingWh(true);
    try {
      await inventoryApi.createWarehouse({ name: whName, address: whAddr || null, notes: whNote || null });
      setWhName(''); setWhAddr(''); setWhNote('');
      loadWarehouses();
    } finally { setSavingWh(false); }
  };

  const createLocation = async (whId: string) => {
    const name = locName[whId];
    if (!name) return;
    setSavingLoc(p => ({ ...p, [whId]: true }));
    try {
      await inventoryApi.createLocation(whId, { name, notes: null });
      setLocName(p => ({ ...p, [whId]: '' }));
      loadLocations(whId);
    } finally { setSavingLoc(p => ({ ...p, [whId]: false })); }
  };

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
      <div className="card p-5">
        <h3 className="font-bold text-gray-800 mb-4 flex items-center gap-2">
          <Plus size={16} className="text-primary-600" /> {t('addWarehouse')}
        </h3>
        <form onSubmit={createWarehouse} className="space-y-3">
          <div>
            <label className="text-xs font-medium text-gray-600 mb-1 block">{t('warehouseNameRequired')}</label>
            <input value={whName} onChange={e => setWhName(e.target.value)} className="input w-full" placeholder={t('warehouseNamePlaceholder')} />
          </div>
          <div>
            <label className="text-xs font-medium text-gray-600 mb-1 block">{t('addressOptional')}</label>
            <input value={whAddr} onChange={e => setWhAddr(e.target.value)} className="input w-full" placeholder={t('addressPlaceholder')} />
          </div>
          <div>
            <label className="text-xs font-medium text-gray-600 mb-1 block">{t('notesOptional')}</label>
            <input value={whNote} onChange={e => setWhNote(e.target.value)} className="input w-full" placeholder={t('warehouseNotesPlaceholder')} />
          </div>
          <button type="submit" disabled={savingWh || !whName} className="btn-primary w-full">
            {savingWh ? t('creating') : t('createWarehouse')}
          </button>
        </form>
      </div>

      <div>
        <h3 className="font-bold text-gray-800 mb-3">{t('existingWarehouses')}</h3>
        {loading ? (
          <p className="text-sm text-gray-400">{t('loading')}</p>
        ) : warehouses.length === 0 ? (
          <div className="card p-8 flex flex-col items-center text-gray-400">
            <Warehouse size={32} className="mb-2 opacity-30" />
            <p className="text-sm">{t('noWarehousesYet')}</p>
          </div>
        ) : (
          <div className="space-y-2">
            {warehouses.map(wh => (
              <div key={wh.id} className="card overflow-hidden">
                <button
                  onClick={() => toggleWh(wh.id)}
                  className="w-full flex items-center justify-between px-4 py-3 hover:bg-gray-50 transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <Warehouse size={16} className="text-primary-500" />
                    <div className="text-left">
                      <p className="font-semibold text-sm text-gray-800">{wh.name}</p>
                      {wh.address && <p className="text-xs text-gray-400">{wh.address}</p>}
                      {wh.notes && <p className="text-xs text-gray-400">{wh.notes}</p>}
                    </div>
                  </div>
                  {expandedWh === wh.id ? <ChevronUp size={14} className="text-gray-400" /> : <ChevronDown size={14} className="text-gray-400" />}
                </button>

                {expandedWh === wh.id && (
                  <div className="border-t border-gray-100 bg-gray-50 px-4 pb-3 pt-2">
                    <p className="text-xs font-semibold text-gray-500 mb-2">{t('locationManagement')}</p>
                    {(locations[wh.id] ?? []).length === 0 ? (
                      <p className="text-xs text-gray-400 mb-2">{t('noLocations')}</p>
                    ) : (
                      <div className="flex flex-wrap gap-1 mb-2">
                        {(locations[wh.id] ?? []).map(loc => (
                          <span key={loc.id} className="px-2 py-0.5 bg-white border border-gray-200 rounded-full text-xs text-gray-600">{loc.name}</span>
                        ))}
                      </div>
                    )}
                    <div className="flex gap-2">
                      <input
                        value={locName[wh.id] ?? ''}
                        onChange={e => setLocName(p => ({ ...p, [wh.id]: e.target.value }))}
                        placeholder={t('newLocationPlaceholder')}
                        className="input text-xs py-1 flex-1"
                        onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); createLocation(wh.id); } }}
                      />
                      <button onClick={() => createLocation(wh.id)} disabled={savingLoc[wh.id] || !locName[wh.id]} className="btn-primary py-1 px-3 text-xs">
                        {savingLoc[wh.id] ? '…' : tc('add')}
                      </button>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────
export default function InventoryPage() {
  const t = useTranslations('inventory');

  const TABS = [
    { key: 'list',    label: t('tabList') },
    { key: 'receive', label: t('tabReceive') },
    { key: 'wh',      label: t('tabWarehouse') },
  ];
  const [tab, setTab] = useState<'list' | 'receive' | 'wh'>('list');
  const [listKey, setListKey] = useState(0);

  const handleReceived = () => { setListKey(k => k + 1); setTab('list'); };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">{t('pageTitle')}</h1>
          <p className="text-sm text-gray-500 mt-0.5">{t('pageSubtitle')}</p>
        </div>
        <button onClick={() => setTab('receive')} className="btn-primary flex items-center gap-2">
          <ArrowDownToLine size={16} /> {t('tabReceive')}
        </button>
      </div>

      <div className="flex gap-1 bg-gray-100 rounded-xl p-1 mb-6 w-fit">
        {TABS.map(t => (
          <button
            key={t.key}
            onClick={() => setTab(t.key as typeof tab)}
            className={`px-4 py-1.5 rounded-lg text-sm font-medium transition-all ${
              tab === t.key ? 'bg-white text-gray-800 shadow-sm' : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === 'list'    && <LotsTab key={listKey} />}
      {tab === 'receive' && <ReceiveTab onReceived={handleReceived} />}
      {tab === 'wh'      && <WarehouseTab />}
    </div>
  );
}
