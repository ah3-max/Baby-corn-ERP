'use client';

/**
 * 批次詳情頁 /batches/[id]
 * UI重點：
 * - 狀態時間軸（視覺化進度條）
 * - 推進狀態按鈕
 * - 採購單來源資訊
 * - 備註編輯
 * - 成本分析面板
 */
import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import { useTranslations, useLocale } from 'next-intl';
import Link from 'next/link';
import {
  ChevronLeft, ArrowRight,
  ShoppingCart, Scale, FileText, Pencil, Check, X,
  FlaskConical, CheckCircle, XCircle, AlertCircle,
  DollarSign, Plus, Trash2, TrendingUp, TrendingDown, RefreshCw, Clock,
  Ship, PackageOpen, Link2, Paperclip, Loader2, Image as ImageIcon
} from 'lucide-react';
import { batchesApi, qcApi, costsApi, salesApi, shipmentsApi, inventoryApi, attachmentsApi } from '@/lib/api';
import { useToast } from '@/contexts/ToastContext';
import { useUser } from '@/contexts/UserContext';
import type { Batch, BatchStatus, QCRecord, CostEvent, CostLayer, BatchCostSummary, SalesOrder, SalesStatus, Shipment, Warehouse, WarehouseLocation } from '@/types';
import { BATCH_STATUS_NEXT, BATCH_STATUSES, COST_LAYERS, COST_LAYER_PRESETS } from '@/types';

const SALES_STATUS_STYLES: Record<SalesStatus, string> = {
  draft:     'bg-gray-100 text-gray-600',
  confirmed: 'bg-blue-100 text-blue-700',
  delivered: 'bg-purple-100 text-purple-700',
  invoiced:  'bg-orange-100 text-orange-700',
  closed:    'bg-green-100 text-green-700',
};

const QC_RESULT_STYLES: Record<string, { badge: string; icon: React.ReactNode }> = {
  pass:             { badge: 'bg-green-100 text-green-700',  icon: <CheckCircle size={13} /> },
  fail:             { badge: 'bg-red-100 text-red-700',      icon: <XCircle size={13} /> },
  conditional_pass: { badge: 'bg-yellow-100 text-yellow-700', icon: <AlertCircle size={13} /> },
};

// 狀態樣式
const STATUS_COLORS: Record<BatchStatus, { badge: string; dot: string }> = {
  processing:      { badge: 'bg-orange-100 text-orange-700',  dot: 'bg-orange-400' },
  qc_pending:      { badge: 'bg-yellow-100 text-yellow-700',  dot: 'bg-yellow-400' },
  qc_done:         { badge: 'bg-blue-100 text-blue-700',      dot: 'bg-blue-400' },
  packaging:       { badge: 'bg-purple-100 text-purple-700',  dot: 'bg-purple-400' },
  ready_to_export: { badge: 'bg-indigo-100 text-indigo-700',  dot: 'bg-indigo-400' },
  exported:        { badge: 'bg-cyan-100 text-cyan-700',      dot: 'bg-cyan-400' },
  in_transit_tw:   { badge: 'bg-teal-100 text-teal-700',      dot: 'bg-teal-400' },
  in_stock:        { badge: 'bg-green-100 text-green-700',    dot: 'bg-green-400' },
  sold:            { badge: 'bg-emerald-100 text-emerald-700',dot: 'bg-emerald-400' },
  closed:          { badge: 'bg-gray-100 text-gray-500',      dot: 'bg-gray-300' },
};

// 成本層級顏色（七層）
const LAYER_COLORS: Record<string, string> = {
  material:     'bg-orange-100 text-orange-700',
  processing:   'bg-amber-100 text-amber-700',
  th_logistics: 'bg-yellow-100 text-yellow-700',
  freight:      'bg-blue-100 text-blue-700',
  tw_customs:   'bg-indigo-100 text-indigo-700',
  tw_logistics: 'bg-teal-100 text-teal-700',
  market:       'bg-purple-100 text-purple-700',
};

// ─── 鮮度追蹤面板 ──────────────────────────────────────────────────────────────
const FRESHNESS_COLORS = {
  fresh:    { bar: 'bg-green-400',  text: 'text-green-700',  bg: 'bg-green-50 border-green-200',  label: '新鮮' },
  warning:  { bar: 'bg-yellow-400', text: 'text-yellow-700', bg: 'bg-yellow-50 border-yellow-200', label: '請注意' },
  critical: { bar: 'bg-red-400',    text: 'text-red-700',    bg: 'bg-red-50 border-red-200',       label: '緊急出貨' },
  expired:  { bar: 'bg-gray-400',   text: 'text-gray-600',   bg: 'bg-gray-50 border-gray-200',     label: '已超期' },
};

const WEATHER_LABELS: Record<string, string> = {
  sunny: '☀️ 晴', cloudy: '⛅ 多雲', rainy: '🌧 下雨', storm: '⛈ 雷雨', hot: '🔥 高溫',
};

interface MilestoneRowProps {
  icon: string;
  label: string;
  dtValue: string | null | undefined;
  dtField: string;
  hoursFromHarvest?: number | null;
  extraInfo?: React.ReactNode;
  onRecord: (field: string, value: string | null) => void;
  canEdit: boolean;
}

function MilestoneRow({ icon, label, dtValue, dtField, hoursFromHarvest, extraInfo, onRecord, canEdit }: MilestoneRowProps) {
  const [editing, setEditing] = useState(false);
  const [editVal, setEditVal] = useState('');

  const startEdit = () => {
    setEditVal(dtValue ? new Date(dtValue).toISOString().slice(0, 16) : new Date().toISOString().slice(0, 16));
    setEditing(true);
  };

  const save = () => { onRecord(dtField, editVal ? new Date(editVal).toISOString() : null); setEditing(false); };

  return (
    <div className="flex items-start gap-3 py-2.5">
      <div className="w-8 h-8 rounded-full bg-gray-100 flex items-center justify-center text-sm flex-shrink-0 mt-0.5">
        {icon}
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-sm font-medium text-gray-700">{label}</span>
          {hoursFromHarvest !== undefined && hoursFromHarvest !== null && dtValue && (
            <span className="text-xs text-gray-400">（採摘後 {hoursFromHarvest.toFixed(0)}h）</span>
          )}
        </div>
        {editing ? (
          <div className="flex items-center gap-2 mt-1">
            <input type="datetime-local" value={editVal} onChange={e => setEditVal(e.target.value)} className="input text-xs py-1 flex-1" />
            <button onClick={save} className="text-xs btn-primary py-1 px-2">儲存</button>
            <button onClick={() => setEditing(false)} className="text-xs btn-secondary py-1 px-2">取消</button>
          </div>
        ) : dtValue ? (
          <div className="flex items-center gap-2 mt-0.5">
            <span className="text-xs text-gray-500">{new Date(dtValue).toLocaleString('zh-TW')}</span>
            {canEdit && (
              <button onClick={startEdit} className="text-xs text-gray-400 hover:text-primary-600"><Pencil size={11} /></button>
            )}
          </div>
        ) : canEdit ? (
          <div className="flex items-center gap-2 mt-0.5">
            <button onClick={() => onRecord(dtField, new Date().toISOString())} className="text-xs text-primary-600 hover:text-primary-700 font-medium flex items-center gap-1">
              <Clock size={11} /> 記錄現在時間
            </button>
            <span className="text-gray-300 text-xs">·</span>
            <button onClick={startEdit} className="text-xs text-gray-400 hover:text-gray-600">手動輸入</button>
          </div>
        ) : (
          <span className="text-xs text-gray-300">尚未記錄</span>
        )}
        {extraInfo && <div className="mt-1">{extraInfo}</div>}
      </div>
    </div>
  );
}

function FreshnessPanel({ batch, onUpdate, canEdit }: { batch: Batch; onUpdate: () => void; canEdit: boolean }) {
  const [saving, setSaving] = useState(false);
  const [editingShelf, setEditingShelf] = useState(false);
  const [shelfVal, setShelfVal] = useState(String(batch.shelf_life_days ?? 23));

  const status = batch.freshness_status;
  const colors = status ? FRESHNESS_COLORS[status] : null;
  const shelf  = batch.shelf_life_days ?? 23;
  const used   = batch.days_since_harvest ?? 0;
  const pct    = Math.min(100, Math.round((used / shelf) * 100));

  const record = async (field: string, value: string | null) => {
    setSaving(true);
    try {
      await batchesApi.update(batch.id, { [field]: value });
      onUpdate();
    } catch (e) { console.error(e); }
    finally { setSaving(false); }
  };

  const saveShelf = async () => {
    const n = parseInt(shelfVal);
    if (!isNaN(n) && n > 0) {
      await record('shelf_life_days', String(n));
    }
    setEditingShelf(false);
  };

  // Compute hours from harvest for each milestone
  const harvestDt = batch.harvest_datetime ? new Date(batch.harvest_datetime) : null;
  const hoursTo = (dtStr: string | null | undefined) => {
    if (!harvestDt || !dtStr) return null;
    return (new Date(dtStr).getTime() - harvestDt.getTime()) / 3600000;
  };

  if (!batch.harvest_datetime && !canEdit) return null;

  return (
    <div className={`card p-5 mb-5 border ${colors ? colors.bg : 'border-gray-200'}`}>
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <span className="text-lg">🌿</span>
          <h2 className="text-sm font-semibold text-gray-600 uppercase tracking-wider">生鮮時效追蹤</h2>
          {saving && <span className="text-xs text-gray-400 animate-pulse">儲存中…</span>}
        </div>
        {/* Shelf life setting */}
        <div className="flex items-center gap-2 text-xs text-gray-400">
          <span>有效期</span>
          {editingShelf ? (
            <>
              <input type="number" min="1" max="30" value={shelfVal} onChange={e => setShelfVal(e.target.value)} className="input w-16 text-xs py-0.5 text-center" />
              <span>天</span>
              <button onClick={saveShelf} className="text-green-600 font-semibold">✓</button>
              <button onClick={() => setEditingShelf(false)} className="text-gray-400">✕</button>
            </>
          ) : (
            <>
              <span className="font-semibold text-gray-600">{shelf} 天</span>
              {canEdit && <button onClick={() => setEditingShelf(true)} className="hover:text-primary-600"><Pencil size={11} /></button>}
            </>
          )}
        </div>
      </div>

      {/* Freshness meter */}
      {batch.harvest_datetime && (
        <div className="mb-5">
          <div className="flex items-end justify-between mb-2">
            <div>
              <span className={`text-4xl font-bold ${colors?.text ?? 'text-gray-700'}`}>
                {batch.remaining_days !== null && batch.remaining_days !== undefined
                  ? (batch.remaining_days > 0 ? batch.remaining_days : 0)
                  : '—'}
              </span>
              <span className="text-lg text-gray-400 ml-1">天剩餘</span>
            </div>
            <div className="text-right">
              {colors && (
                <span className={`px-3 py-1 rounded-full text-sm font-bold ${colors.bg} ${colors.text} border`}>
                  {colors.label}
                </span>
              )}
              <p className="text-xs text-gray-400 mt-1">採摘後第 {used} 天 · 共 {shelf} 天</p>
            </div>
          </div>
          {/* Progress bar */}
          <div className="w-full bg-gray-200 rounded-full h-3 overflow-hidden">
            <div
              className={`h-full rounded-full transition-all ${colors?.bar ?? 'bg-gray-400'}`}
              style={{ width: `${pct}%` }}
            />
          </div>
          <div className="flex justify-between text-xs text-gray-400 mt-1">
            <span>採摘</span>
            <span>{pct}% 已用</span>
            <span>到期</span>
          </div>
        </div>
      )}

      {/* Milestone timeline */}
      <div className="border-t border-gray-100 pt-3 divide-y divide-gray-50">
        {/* 採摘 */}
        <MilestoneRow
          icon="🌿" label="田間採摘" dtField="harvest_datetime"
          dtValue={batch.harvest_datetime} hoursFromHarvest={0}
          onRecord={record} canEdit={canEdit}
          extraInfo={
            batch.harvest_datetime ? (
              <div className="flex flex-wrap gap-2 mt-1">
                {batch.harvest_location && <span className="text-xs bg-white border border-gray-200 rounded px-1.5 py-0.5">📍 {batch.harvest_location}</span>}
                {batch.harvest_temperature != null && <span className="text-xs bg-white border border-gray-200 rounded px-1.5 py-0.5">🌡 {batch.harvest_temperature}°C</span>}
                {batch.harvest_weather && <span className="text-xs bg-white border border-gray-200 rounded px-1.5 py-0.5">{WEATHER_LABELS[batch.harvest_weather] ?? batch.harvest_weather}</span>}
                {batch.transport_refrigerated != null && <span className="text-xs bg-white border border-gray-200 rounded px-1.5 py-0.5">{batch.transport_refrigerated ? '🧊 冷藏運輸' : '⚠️ 非冷藏'}</span>}
              </div>
            ) : canEdit ? (
              <div className="flex flex-wrap gap-2 mt-1">
                <HarvestExtraFields batch={batch} onSave={record} />
              </div>
            ) : null
          }
        />
        {/* 到廠 */}
        <MilestoneRow
          icon="🚛" label="抵達工廠"
          dtField="factory_arrival_dt" dtValue={batch.factory_arrival_dt}
          hoursFromHarvest={hoursTo(batch.factory_arrival_dt)}
          onRecord={record} canEdit={canEdit}
          extraInfo={batch.factory_temp_on_arrival != null ? (
            <span className="text-xs bg-white border border-gray-200 rounded px-1.5 py-0.5">🌡 到廠品溫 {batch.factory_temp_on_arrival}°C</span>
          ) : null}
        />
        {/* 加工完成 */}
        <MilestoneRow
          icon="🏭" label="加工完成（冷藏入庫）"
          dtField="factory_complete_dt" dtValue={batch.factory_complete_dt}
          hoursFromHarvest={hoursTo(batch.factory_complete_dt)}
          onRecord={record} canEdit={canEdit}
          extraInfo={batch.cold_storage_temp != null ? (
            <span className="text-xs bg-white border border-gray-200 rounded px-1.5 py-0.5">❄️ 冷藏 {batch.cold_storage_temp}°C</span>
          ) : null}
        />
        {/* 包裝 */}
        <MilestoneRow
          icon="📦" label="包裝完成"
          dtField="packed_dt" dtValue={batch.packed_dt}
          hoursFromHarvest={hoursTo(batch.packed_dt)}
          onRecord={record} canEdit={canEdit}
        />
        {/* 裝貨出口 */}
        <MilestoneRow
          icon="🚢" label="裝貨出口"
          dtField="container_loaded_dt" dtValue={batch.container_loaded_dt}
          hoursFromHarvest={hoursTo(batch.container_loaded_dt)}
          onRecord={record} canEdit={canEdit}
        />
      </div>
    </div>
  );
}

// 採摘額外欄位（溫度、天氣、冷藏）的快速填寫
function HarvestExtraFields({ batch, onSave }: { batch: Batch; onSave: (f: string, v: string | null) => void }) {
  const [loc, setLoc]   = useState(batch.harvest_location ?? '');
  const [temp, setTemp] = useState(batch.harvest_temperature != null ? String(batch.harvest_temperature) : '');
  const [weather, setWeather] = useState(batch.harvest_weather ?? '');
  const [refrig, setRefrig]   = useState<string>(batch.transport_refrigerated != null ? String(batch.transport_refrigerated) : '');
  const [saving, setSaving]   = useState(false);

  const save = async () => {
    setSaving(true);
    try {
      const updates: Record<string, string | null | boolean | number> = {};
      if (loc)     updates.harvest_location = loc;
      if (temp)    updates.harvest_temperature = parseFloat(temp);
      if (weather) updates.harvest_weather = weather;
      if (refrig !== '') updates.transport_refrigerated = refrig === 'true';
      // batch update accepts object, call once
      await batchesApi.update(batch.id, updates);
      onSave('_noop', null); // trigger refresh via parent
    } catch (e) { console.error(e); }
    finally { setSaving(false); }
  };

  return (
    <div className="flex flex-wrap gap-2 items-end">
      <div>
        <label className="text-[10px] text-gray-500 block mb-0.5">地點</label>
        <input value={loc} onChange={e => setLoc(e.target.value)} className="input text-xs py-0.5 w-28" placeholder="農場/地區" />
      </div>
      <div>
        <label className="text-[10px] text-gray-500 block mb-0.5">溫度°C</label>
        <input type="number" value={temp} onChange={e => setTemp(e.target.value)} className="input text-xs py-0.5 w-16" placeholder="30" />
      </div>
      <div>
        <label className="text-[10px] text-gray-500 block mb-0.5">天氣</label>
        <select value={weather} onChange={e => setWeather(e.target.value)} className="input text-xs py-0.5">
          <option value="">選擇</option>
          <option value="sunny">☀️ 晴</option>
          <option value="cloudy">⛅ 多雲</option>
          <option value="rainy">🌧 下雨</option>
          <option value="storm">⛈ 雷雨</option>
          <option value="hot">🔥 高溫</option>
        </select>
      </div>
      <div>
        <label className="text-[10px] text-gray-500 block mb-0.5">冷藏運輸</label>
        <select value={refrig} onChange={e => setRefrig(e.target.value)} className="input text-xs py-0.5">
          <option value="">未填</option>
          <option value="true">✅ 有冷藏</option>
          <option value="false">❌ 無冷藏</option>
        </select>
      </div>
      <button onClick={save} disabled={saving} className="btn-secondary text-xs py-1 px-2">{saving ? '…' : '儲存'}</button>
    </div>
  );
}

export default function BatchDetailPage() {
  const params = useParams();
  const locale = useLocale();
  const t  = useTranslations('batches');
  const tc = useTranslations('common');
  const tco = useTranslations('cost');
  const { showToast } = useToast();
  const { hasPermission } = useUser();
  const canEdit     = hasPermission('batch', 'edit');
  const canViewCost = hasPermission('cost', 'view_cost');

  const [batch, setBatch]           = useState<Batch | null>(null);
  const [loading, setLoading]       = useState(true);
  const [advancing, setAdvancing]   = useState(false);
  const [editNote, setEditNote]     = useState(false);
  const [noteVal, setNoteVal]       = useState('');
  const [saving, setSaving]         = useState(false);
  const [editWeight, setEditWeight] = useState(false);
  const [weightVal, setWeightVal]   = useState('');
  const [savingW, setSavingW]       = useState(false);
  const [qcRecords, setQcRecords]   = useState<QCRecord[]>([]);
  const tf = useTranslations('factory');

  // ─── QC 快速新增 ───
  const [showQCForm, setShowQCForm]     = useState(false);
  const [qcForm, setQcForm]             = useState({
    inspector_name: '', result: 'pass', grade: '', weight_checked: '', notes: '',
  });
  const [addingQC, setAddingQC]         = useState(false);
  const canCreateQC = hasPermission('qc', 'create');

  // ─── 出口單快速建立 / 關聯 ───
  const [showShipForm, setShowShipForm]       = useState(false);
  const [shipForm, setShipForm]               = useState({
    export_date: new Date().toISOString().slice(0, 10),
    carrier: '', vessel_name: '', estimated_arrival_tw: '', notes: '',
  });
  const [addingShip, setAddingShip]           = useState(false);
  const [existingShipments, setExistingShipments] = useState<Shipment[]>([]);
  const [linkingShipment, setLinkingShipment] = useState<string | null>(null);
  const canCreateShipment = hasPermission('shipment', 'create');

  // ─── 入庫快速操作 ───
  const [showLotForm, setShowLotForm]       = useState(false);
  const [warehouses, setWarehouses]         = useState<Warehouse[]>([]);
  const [locations, setLocations]           = useState<WarehouseLocation[]>([]);
  const [lotForm, setLotForm]               = useState({
    warehouse_id: '', location_id: '', received_date: new Date().toISOString().slice(0, 10),
    initial_weight_kg: '', initial_boxes: '', notes: '',
  });
  const [addingLot, setAddingLot]           = useState(false);
  const canCreateInventory = hasPermission('inventory', 'create');

  // 關聯銷售訂單
  const [salesOrders, setSalesOrders] = useState<SalesOrder[]>([]);
  const canViewSales = hasPermission('sales', 'view');

  // 關聯出口單 & 庫存批次
  const [relatedShipments, setRelatedShipments] = useState<Shipment[]>([]);
  const [relatedLots, setRelatedLots]           = useState<any[]>([]);
  const canViewShipment  = hasPermission('shipment', 'view');
  const canViewInventory = hasPermission('inventory', 'view');

  // 成本相關狀態
  const [costSummary, setCostSummary]     = useState<BatchCostSummary | null>(null);
  const [costLoading, setCostLoading]     = useState(false);
  const [exchangeRate, setExchangeRate]   = useState(0.92);
  const [showAddCost, setShowAddCost]     = useState(false);
  const [voidingId, setVoidingId]         = useState<string | null>(null);
  // 每個成本類型最近一次使用的值，用於自動帶入
  const [recentValues, setRecentValues]   = useState<Record<string, any>>({});
  const [newCost, setNewCost]             = useState({
    cost_layer:         'material' as CostLayer,
    cost_type:          '',
    custom_type:        '',
    description_zh:     '',
    amount_thb:         '',
    amount_twd:         '',
    quantity:           '',       // 數量（例：500 kg）
    unit_cost:          '',       // 單價（例：8 THB/kg）
    unit_label:         'kg',     // 單位標籤（kg/箱/次）
    item_exchange_rate: '',       // 此筆成本的匯率（可覆蓋全域匯率）
    notes:              '',
  });
  const [addingCost, setAddingCost]       = useState(false);

  // ─── 附件 / 照片 ───
  const [attachments, setAttachments]   = useState<any[]>([]);
  const [uploadingFile, setUploadingFile] = useState(false);

  const fetchBatch = async () => {
    try {
      const { data } = await batchesApi.get(params.id as string);
      setBatch(data);
      setNoteVal(data.note ?? '');
      setWeightVal(String(data.current_weight));
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

  const fetchSalesOrders = async (batchId: string) => {
    if (!canViewSales) return;
    try {
      const { data } = await salesApi.list({ batch_id: batchId });
      setSalesOrders(data);
    } catch (e) {
      console.error(e);
    }
  };

  // 取得關聯出口單
  const fetchRelatedShipments = async (batchId: string) => {
    if (!canViewShipment) return;
    try {
      const { data } = await shipmentsApi.list();
      // 篩選包含此批次的出口單
      const related = data.filter((s: Shipment) =>
        s.shipment_batches?.some((sb: any) => sb.batch_id === batchId)
      );
      setRelatedShipments(related);
    } catch (e) { console.error(e); }
  };

  // 取得關聯庫存批次
  const fetchRelatedLots = async (batchId: string) => {
    if (!canViewInventory) return;
    try {
      const { data } = await inventoryApi.listLots({ batch_id: batchId });
      setRelatedLots(data);
    } catch (e) { console.error(e); }
  };

  const fetchCostSummary = async (batchId: string, rate = exchangeRate) => {
    if (!canViewCost) return;
    setCostLoading(true);
    try {
      const { data } = await costsApi.getSummary(batchId, rate);
      setCostSummary(data);
    } catch (e) {
      console.error(e);
    } finally {
      setCostLoading(false);
    }
  };

  // ─── 附件：載入、上傳、刪除 ───

  /**
   * 載入此批次的所有附件
   */
  const fetchAttachments = async (batchId: string) => {
    try {
      const { data } = await attachmentsApi.list('batch', batchId);
      setAttachments(data);
    } catch (e) {
      console.error('載入附件失敗', e);
    }
  };

  /**
   * 處理檔案上傳事件
   * 使用者透過隱藏的 <input type="file"> 選取檔案後觸發
   */
  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !batch) return;

    setUploadingFile(true);
    try {
      await attachmentsApi.upload(file, 'batch', batch.id);
      await fetchAttachments(batch.id);
      showToast('附件上傳成功', 'success');
    } catch (err: any) {
      const msg = err?.response?.data?.detail || '上傳失敗，請稍後再試';
      showToast(msg, 'error');
    } finally {
      setUploadingFile(false);
      // 清除 input 值，讓同一個檔案可再次觸發 onChange
      e.target.value = '';
    }
  };

  /**
   * 刪除附件
   */
  const handleDeleteAttachment = async (id: string) => {
    if (!confirm('確定要刪除此附件？')) return;
    try {
      await attachmentsApi.delete(id);
      setAttachments(prev => prev.filter(a => a.id !== id));
      showToast('附件已刪除', 'success');
    } catch (e) {
      showToast('刪除失敗', 'error');
    }
  };

  // 取得備貨完成的出口單（供關聯用）
  const fetchPreparingShipments = async () => {
    try {
      const { data } = await shipmentsApi.list({ status: 'preparing' });
      setExistingShipments(data);
    } catch (e) { console.error(e); }
  };

  // 取得倉庫列表
  const fetchWarehouses = async () => {
    try {
      const { data } = await inventoryApi.listWarehouses();
      setWarehouses(data);
    } catch (e) { console.error(e); }
  };

  // 取得儲位列表
  const fetchLocations = async (warehouseId: string) => {
    try {
      const { data } = await inventoryApi.listLocations(warehouseId);
      setLocations(data);
    } catch (e) { console.error(e); }
  };

  // ─── QC 新增 ───
  const handleAddQC = async () => {
    if (!batch || !qcForm.inspector_name) return;
    setAddingQC(true);
    try {
      await qcApi.create({
        batch_id: batch.id,
        inspector_name: qcForm.inspector_name,
        checked_at: new Date().toISOString(),
        result: qcForm.result,
        grade: qcForm.grade || null,
        weight_checked: qcForm.weight_checked ? parseFloat(qcForm.weight_checked) : null,
        notes: qcForm.notes || null,
      });
      showToast(tf('createSuccess'), 'success');
      setShowQCForm(false);
      setQcForm({ inspector_name: '', result: 'pass', grade: '', weight_checked: '', notes: '' });
      fetchQC(batch.id);
    } catch (e: any) {
      showToast(e?.response?.data?.detail ?? tc('error'), 'error');
    } finally {
      setAddingQC(false);
    }
  };

  // ─── 刪除 QC 紀錄 ───
  const handleDeleteQC = async (qcId: string) => {
    if (!batch) return;
    try {
      await qcApi.delete(qcId);
      showToast(tf('deleteSuccess'), 'success');
      fetchQC(batch.id);
    } catch (e: any) {
      showToast(e?.response?.data?.detail ?? tc('error'), 'error');
    }
  };

  // ─── 快速建立出口單（含此批次） ───
  const handleCreateShipment = async () => {
    if (!batch) return;
    setAddingShip(true);
    try {
      await shipmentsApi.create({
        export_date: shipForm.export_date,
        carrier: shipForm.carrier || null,
        vessel_name: shipForm.vessel_name || null,
        estimated_arrival_tw: shipForm.estimated_arrival_tw || null,
        notes: shipForm.notes || null,
        batch_ids: [batch.id],
      });
      showToast(t('shipmentCreated'), 'success');
      setShowShipForm(false);
      fetchBatch();
    } catch (e: any) {
      showToast(e?.response?.data?.detail ?? tc('error'), 'error');
    } finally {
      setAddingShip(false);
    }
  };

  // ─── 關聯到既有出口單 ───
  const handleLinkShipment = async (shipmentId: string) => {
    if (!batch) return;
    setLinkingShipment(shipmentId);
    try {
      const { data: shipment } = await shipmentsApi.get(shipmentId);
      const existingBatchIds = shipment.shipment_batches?.map((sb: any) => sb.batch_id) ?? [];
      await shipmentsApi.update(shipmentId, {
        batch_ids: [...existingBatchIds, batch.id],
      });
      showToast(t('shipmentLinked'), 'success');
      fetchBatch();
      fetchPreparingShipments();
    } catch (e: any) {
      showToast(e?.response?.data?.detail ?? tc('error'), 'error');
    } finally {
      setLinkingShipment(null);
    }
  };

  // ─── 快速入庫 ───
  const handleCreateLot = async () => {
    if (!batch || !lotForm.warehouse_id || !lotForm.initial_weight_kg) return;
    setAddingLot(true);
    try {
      await inventoryApi.createLot({
        batch_id: batch.id,
        warehouse_id: lotForm.warehouse_id,
        location_id: lotForm.location_id || null,
        received_date: lotForm.received_date,
        initial_weight_kg: parseFloat(lotForm.initial_weight_kg),
        initial_boxes: lotForm.initial_boxes ? parseInt(lotForm.initial_boxes) : null,
        notes: lotForm.notes || null,
      });
      showToast(t('lotCreated'), 'success');
      setShowLotForm(false);
      fetchBatch();
    } catch (e: any) {
      showToast(e?.response?.data?.detail ?? tc('error'), 'error');
    } finally {
      setAddingLot(false);
    }
  };

  useEffect(() => {
    fetchBatch();
  }, []);

  useEffect(() => {
    if (params.id) {
      fetchQC(params.id as string);
      fetchCostSummary(params.id as string);
      fetchSalesOrders(params.id as string);
      fetchRelatedShipments(params.id as string);
      fetchRelatedLots(params.id as string);
      fetchRecentValues();        // 載入成本歷史記憶
      fetchAttachments(params.id as string);  // 載入附件列表
    }
  }, [params.id]);

  // 根據批次狀態載入相關資料
  useEffect(() => {
    if (!batch) return;
    if (batch.status === 'ready_to_export') fetchPreparingShipments();
    if (batch.status === 'in_stock' || batch.status === 'in_transit_tw') {
      fetchWarehouses();
      setLotForm(prev => ({ ...prev, initial_weight_kg: String(batch.current_weight) }));
    }
  }, [batch?.status]);

  const handleAdvance = async () => {
    if (!batch) return;
    setAdvancing(true);
    try {
      await batchesApi.advance(batch.id);
      showToast(t('advanceSuccess'), 'success');
      fetchBatch();
    } catch (e: any) {
      showToast(e?.response?.data?.detail ?? tc('error'), 'error');
    } finally {
      setAdvancing(false);
    }
  };

  const handleSaveNote = async () => {
    if (!batch) return;
    setSaving(true);
    try {
      await batchesApi.update(batch.id, { note: noteVal || null });
      showToast(t('updateSuccess'), 'success');
      setEditNote(false);
      fetchBatch();
    } catch {
      showToast(tc('error'), 'error');
    } finally {
      setSaving(false);
    }
  };

  const handleSaveWeight = async () => {
    if (!batch) return;
    const w = parseFloat(weightVal);
    if (isNaN(w) || w < 0) {
      showToast(tc('error'), 'error');
      return;
    }
    setSavingW(true);
    try {
      await batchesApi.update(batch.id, { current_weight: w });
      showToast(t('updateSuccess'), 'success');
      setEditWeight(false);
      fetchBatch();
    } catch {
      showToast(tc('error'), 'error');
    } finally {
      setSavingW(false);
    }
  };

  // 取得每個成本類型最近一次使用的值（用於自動帶入）
  const fetchRecentValues = async () => {
    try {
      const { data } = await costsApi.getRecentValues();
      setRecentValues(data);
    } catch (e) {
      // 靜默失敗，不影響主流程
    }
  };

  // 選擇成本類型時，自動帶入上次使用的值
  const handleCostTypeChange = (costType: string) => {
    if (costType === '_custom') {
      setNewCost(p => ({ ...p, cost_type: costType }));
      return;
    }
    const key = `${newCost.cost_layer}__${costType}`;
    const recent = recentValues[key];
    if (recent) {
      setNewCost(p => ({
        ...p,
        cost_type:      costType,
        amount_thb:     recent.amount_thb     ? String(recent.amount_thb)     : '',
        amount_twd:     recent.amount_twd     ? String(recent.amount_twd)     : '',
        unit_cost:      recent.unit_cost      ? String(recent.unit_cost)      : '',
        unit_label:     recent.unit_label     || 'kg',
        quantity:       recent.quantity       ? String(recent.quantity)       : '',
        description_zh: recent.description_zh || '',
      }));
    } else {
      setNewCost(p => ({ ...p, cost_type: costType }));
    }
  };

  // 數量或單價改變時，自動計算 THB 總金額 = 數量 × 單價
  const handleQtyOrUnitChange = (field: 'quantity' | 'unit_cost', value: string) => {
    setNewCost(p => {
      const next = { ...p, [field]: value };
      const qty = parseFloat(field === 'quantity' ? value : p.quantity);
      const uc  = parseFloat(field === 'unit_cost' ? value : p.unit_cost);
      if (!isNaN(qty) && !isNaN(uc) && qty > 0 && uc > 0) {
        const totalThb = (qty * uc).toFixed(2);
        next.amount_thb = totalThb;
        // 同步換算 TWD
        const rate = parseFloat(next.item_exchange_rate) || exchangeRate;
        if (rate > 0) next.amount_twd = Math.round(qty * uc * rate).toString();
      }
      return next;
    });
  };

  // 填入 THB 金額時，自動換算 TWD
  const handleThbChange = (value: string) => {
    setNewCost(p => {
      const next = { ...p, amount_thb: value };
      const thb  = parseFloat(value);
      const rate = parseFloat(p.item_exchange_rate) || exchangeRate;
      if (!isNaN(thb) && thb > 0 && rate > 0) {
        next.amount_twd = Math.round(thb * rate).toString();
      }
      return next;
    });
  };

  // 匯率改變時，重新換算 TWD（若 THB 有值）
  const handleItemRateChange = (value: string) => {
    setNewCost(p => {
      const next = { ...p, item_exchange_rate: value };
      const thb  = parseFloat(p.amount_thb);
      const rate = parseFloat(value);
      if (!isNaN(thb) && thb > 0 && !isNaN(rate) && rate > 0) {
        next.amount_twd = Math.round(thb * rate).toString();
      }
      return next;
    });
  };

  // 重置表單（保留層級）
  const resetCostForm = () => setNewCost(p => ({
    cost_layer: p.cost_layer, cost_type: '', custom_type: '',
    description_zh: '', amount_thb: '', amount_twd: '',
    quantity: '', unit_cost: '', unit_label: 'kg', item_exchange_rate: '', notes: '',
  }));

  const handleAddCost = async (keepOpen = false) => {
    if (!batch) return;
    const costType = newCost.cost_type === '_custom' ? newCost.custom_type : newCost.cost_type;
    if (!costType) return;
    const hasAmount = newCost.amount_thb || newCost.amount_twd;
    if (!hasAmount) return;
    setAddingCost(true);
    try {
      await costsApi.createEvent(batch.id, {
        cost_layer:    newCost.cost_layer,
        cost_type:     costType,
        description_zh: newCost.description_zh || null,
        amount_thb:    newCost.amount_thb    ? parseFloat(newCost.amount_thb)    : null,
        amount_twd:    newCost.amount_twd    ? parseFloat(newCost.amount_twd)    : null,
        exchange_rate: newCost.item_exchange_rate ? parseFloat(newCost.item_exchange_rate) : null,
        quantity:      newCost.quantity      ? parseFloat(newCost.quantity)      : null,
        unit_cost:     newCost.unit_cost     ? parseFloat(newCost.unit_cost)     : null,
        unit_label:    newCost.unit_label    || null,
        notes:         newCost.notes         || null,
      });
      showToast(tco('eventAdded'), 'success');
      fetchRecentValues();        // 更新記憶
      fetchCostSummary(batch.id);
      if (keepOpen) {
        // 繼續新增：清空金額但保留層級，讓使用者快速連續新增
        resetCostForm();
      } else {
        setShowAddCost(false);
        resetCostForm();
      }
    } catch (e: any) {
      showToast(e?.response?.data?.detail ?? tc('error'), 'error');
    } finally {
      setAddingCost(false);
    }
  };

  const handleVoidCost = async (eventId: string) => {
    if (!batch) return;
    setVoidingId(eventId);
    try {
      await costsApi.voidEvent(batch.id, eventId);
      showToast(tco('eventVoided'), 'success');
      fetchCostSummary(batch.id);
    } catch (e: any) {
      showToast(e?.response?.data?.detail ?? tc('error'), 'error');
    } finally {
      setVoidingId(null);
    }
  };

  if (loading) {
    return <div className="text-center py-16 text-gray-400">{tc('loading')}</div>;
  }

  if (!batch) {
    return <div className="text-center py-16 text-gray-400">{tc('noData')}</div>;
  }

  const currentIdx = BATCH_STATUSES.indexOf(batch.status);
  const nextStatus = BATCH_STATUS_NEXT[batch.status];
  const style      = STATUS_COLORS[batch.status];

  return (
    <div className="max-w-3xl">
      {/* 頁首導覽 */}
      <div className="flex items-center gap-3 mb-6">
        <Link
          href={`/${locale}/batches`}
          className="flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-700 transition-colors"
        >
          <ChevronLeft size={16} />
          {t('title')}
        </Link>
        <span className="text-gray-300">/</span>
        <span className="text-sm font-mono text-gray-700 font-semibold">{batch.batch_no}</span>
      </div>

      {/* ── 批次標題卡 ── */}
      <div className="card p-6 mb-5">
        <div className="flex items-start justify-between">
          <div>
            <div className="flex items-center gap-3 mb-1">
              <h1 className="text-2xl font-bold text-gray-900 font-mono">{batch.batch_no}</h1>
              <span className={`px-3 py-1 rounded-full text-sm font-medium ${style.badge}`}>
                {t(`status.${batch.status}` as any)}
              </span>
            </div>
            <p className="text-sm text-gray-400">
              {tc('createdAt')}：{new Date(batch.created_at).toLocaleDateString()}
            </p>
          </div>

          {/* 推進狀態按鈕 */}
          {canEdit && nextStatus && !['exported', 'in_transit_tw'].includes(batch.status) && (
            <button
              onClick={handleAdvance}
              disabled={advancing}
              className="btn-primary flex items-center gap-2"
            >
              <ArrowRight size={15} />
              {advancing ? '...' : t(`nextStatus.${batch.status}` as any)}
            </button>
          )}
          {/* exported / in_transit_tw：由出口單自動推進，顯示說明並連結出口單 */}
          {['exported', 'in_transit_tw'].includes(batch.status) && (
            <div className="flex flex-col items-end gap-1.5">
              <span className="text-xs text-gray-400 flex items-center gap-1">
                <Ship size={12} />
                由出口單自動推進
              </span>
              {relatedShipments.length > 0 && (
                <Link
                  href={`/${locale}/shipments/${relatedShipments[0].id}`}
                  className="text-xs text-primary-600 hover:underline font-mono font-semibold"
                >
                  → {relatedShipments[0].shipment_no}
                </Link>
              )}
            </div>
          )}
          {(!nextStatus || !canEdit) && batch.status === 'closed' && (
            <span className="px-3 py-1.5 text-xs font-medium bg-gray-100 text-gray-500 rounded-lg">
              {t('status.closed')}
            </span>
          )}
        </div>
      </div>

      {/* ── 狀態時間軸 ── */}
      <div className="card p-6 mb-5">
        <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-4">
          {t('statusFlow')}
        </h2>
        <div className="relative">
          {/* 進度條背景 */}
          <div className="absolute top-3 left-3 right-3 h-0.5 bg-gray-200" />
          {/* 進度條填充 */}
          <div
            className="absolute top-3 left-3 h-0.5 bg-primary-400 transition-all duration-500"
            style={{
              width: `${(currentIdx / (BATCH_STATUSES.length - 1)) * 100}%`,
              right: 'auto',
            }}
          />
          {/* 狀態節點 */}
          <div className="relative flex justify-between">
            {BATCH_STATUSES.map((st, idx) => {
              const isDone    = idx < currentIdx;
              const isCurrent = idx === currentIdx;
              return (
                <div key={st} className="flex flex-col items-center gap-1.5">
                  <div className={`w-6 h-6 rounded-full border-2 flex items-center justify-center transition-all ${
                    isDone
                      ? 'bg-primary-500 border-primary-500'
                      : isCurrent
                      ? `${STATUS_COLORS[st as BatchStatus].dot} border-white ring-2 ring-offset-1 ring-primary-400`
                      : 'bg-white border-gray-300'
                  }`}>
                    {isDone && <Check size={12} className="text-white" />}
                    {isCurrent && <div className="w-2 h-2 rounded-full bg-white" />}
                  </div>
                  <span className={`text-[10px] text-center max-w-[52px] leading-tight ${
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

      <FreshnessPanel batch={batch} onUpdate={fetchBatch} canEdit={canEdit} />

      <div className="grid grid-cols-1 md:grid-cols-2 gap-5 mb-5">
        {/* ── 來源採購單 ── */}
        <div className="card p-5">
          <div className="flex items-center gap-2 mb-4">
            <ShoppingCart size={16} className="text-gray-400" />
            <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wider">
              {t('sourceInfo')}
            </h2>
          </div>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-400">{t('purchaseOrder')}</span>
              <Link
                href={`/${locale}/purchases`}
                className="font-mono font-semibold text-primary-600 hover:underline"
              >
                {batch.purchase_order?.order_no ?? '—'}
              </Link>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">{t('supplier')}</span>
              <span className="font-medium text-gray-700">
                {batch.purchase_order?.supplier?.name ?? '—'}
              </span>
            </div>
          </div>
        </div>

        {/* ── 重量資訊 ── */}
        <div className="card p-5">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Scale size={16} className="text-gray-400" />
              <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wider">
                {t('weightInfo')}
              </h2>
            </div>
            {canEdit && !editWeight && batch.status !== 'closed' && (
              <button
                onClick={() => setEditWeight(true)}
                className="flex items-center gap-1 text-xs text-gray-400 hover:text-primary-600 transition-colors"
              >
                <Pencil size={13} /> {tc('edit')}
              </button>
            )}
          </div>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-400">{t('initialWeight')}</span>
              <span className="font-semibold text-gray-700">
                {Number(batch.initial_weight).toLocaleString()} kg
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-gray-400">{t('currentWeight')}</span>
              {editWeight ? (
                <div className="flex items-center gap-1.5">
                  <input
                    type="number"
                    value={weightVal}
                    onChange={(e) => setWeightVal(e.target.value)}
                    step="0.1"
                    min="0"
                    className="input w-28 text-right py-1 text-sm"
                    autoFocus
                  />
                  <span className="text-gray-400 text-xs">kg</span>
                  <button
                    onClick={handleSaveWeight}
                    disabled={savingW}
                    className="p-1 text-green-600 hover:text-green-700"
                  >
                    <Check size={15} />
                  </button>
                  <button
                    onClick={() => { setEditWeight(false); setWeightVal(String(batch.current_weight)); }}
                    className="p-1 text-gray-400 hover:text-gray-600"
                  >
                    <X size={15} />
                  </button>
                </div>
              ) : (
                <span className={`font-semibold ${
                  Number(batch.current_weight) < Number(batch.initial_weight)
                    ? 'text-orange-600' : 'text-green-600'
                }`}>
                  {Number(batch.current_weight).toLocaleString()} kg
                </span>
              )}
            </div>
            {Number(batch.current_weight) < Number(batch.initial_weight) && (
              <div className="flex justify-between text-xs">
                <span className="text-gray-400">{t('processingLoss')}</span>
                <span className="text-orange-500">
                  -{(Number(batch.initial_weight) - Number(batch.current_weight)).toFixed(1)} kg
                </span>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* ── 備註 ── */}
      <div className="card p-5 mb-5">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <FileText size={16} className="text-gray-400" />
            <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wider">
              {t('note')}
            </h2>
          </div>
          {canEdit && !editNote && batch.status !== 'closed' && (
            <button
              onClick={() => setEditNote(true)}
              className="flex items-center gap-1 text-xs text-gray-400 hover:text-primary-600 transition-colors"
            >
              <Pencil size={13} /> {tc('edit')}
            </button>
          )}
        </div>

        {editNote ? (
          <div>
            <textarea
              value={noteVal}
              onChange={(e) => setNoteVal(e.target.value)}
              rows={4}
              className="input resize-none mb-3"
            />
            <div className="flex gap-2 justify-end">
              <button
                onClick={() => { setEditNote(false); setNoteVal(batch.note ?? ''); }}
                className="btn-secondary flex items-center gap-1.5"
              >
                <X size={14} /> {tc('cancel')}
              </button>
              <button
                onClick={handleSaveNote}
                disabled={saving}
                className="btn-primary flex items-center gap-1.5"
              >
                <Check size={14} />
                {saving ? '...' : tc('save')}
              </button>
            </div>
          </div>
        ) : (
          <p className="text-sm text-gray-600 whitespace-pre-wrap min-h-[2rem]">
            {batch.note || <span className="text-gray-300 italic">—</span>}
          </p>
        )}
      </div>

      {/* ── QC 紀錄（含快速新增） ── */}
      <div className="card p-5 mb-5">
        <div className="flex items-center gap-2 mb-4">
          <FlaskConical size={16} className="text-gray-400" />
          <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wider">
            {tf('qcHistory')}
          </h2>
          <span className="text-xs text-gray-400">{qcRecords.length} {tc('total', { count: qcRecords.length }).replace(/\d+ /, '')}</span>
          {/* QC 新增按鈕：加工中 / 待 QC 狀態時顯示 */}
          {canCreateQC && ['processing', 'qc_pending'].includes(batch.status) && !showQCForm && (
            <button
              onClick={() => setShowQCForm(true)}
              className="ml-auto btn-primary text-xs flex items-center gap-1.5 py-1.5 px-3"
            >
              <Plus size={13} /> {tf('addQC')}
            </button>
          )}
        </div>

        {/* QC 快速新增表單 */}
        {showQCForm && (
          <div className="border border-dashed border-green-300 rounded-xl p-4 mb-4 bg-green-50/30 space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs text-gray-500 mb-1 block">{tf('inspector')} *</label>
                <input
                  type="text"
                  value={qcForm.inspector_name}
                  onChange={e => setQcForm(p => ({ ...p, inspector_name: e.target.value }))}
                  placeholder="John / สมชาย"
                  className="input py-1.5 text-sm"
                />
              </div>
              <div>
                <label className="text-xs text-gray-500 mb-1 block">{tf('result')} *</label>
                <select
                  value={qcForm.result}
                  onChange={e => setQcForm(p => ({ ...p, result: e.target.value }))}
                  className="input py-1.5 text-sm"
                >
                  <option value="pass">{tf('results.pass')}</option>
                  <option value="fail">{tf('results.fail')}</option>
                  <option value="conditional_pass">{tf('results.conditional_pass')}</option>
                </select>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs text-gray-500 mb-1 block">{tf('grade')}</label>
                <select
                  value={qcForm.grade}
                  onChange={e => setQcForm(p => ({ ...p, grade: e.target.value }))}
                  className="input py-1.5 text-sm"
                >
                  <option value="">—</option>
                  <option value="A">{tf('grades.A')}</option>
                  <option value="B">{tf('grades.B')}</option>
                  <option value="C">{tf('grades.C')}</option>
                  <option value="D">{tf('grades.D')}</option>
                </select>
              </div>
              <div>
                <label className="text-xs text-gray-500 mb-1 block">{tf('weightChecked')}</label>
                <input
                  type="number"
                  value={qcForm.weight_checked}
                  onChange={e => setQcForm(p => ({ ...p, weight_checked: e.target.value }))}
                  step="0.01"
                  min="0"
                  className="input py-1.5 text-sm"
                />
              </div>
            </div>
            <div>
              <label className="text-xs text-gray-500 mb-1 block">{tf('notes')}</label>
              <textarea
                value={qcForm.notes}
                onChange={e => setQcForm(p => ({ ...p, notes: e.target.value }))}
                rows={2}
                className="input py-1.5 text-sm resize-none"
              />
            </div>
            <div className="flex gap-2 justify-end">
              <button onClick={() => setShowQCForm(false)} className="btn-secondary text-sm py-1.5">{tc('cancel')}</button>
              <button
                onClick={handleAddQC}
                disabled={addingQC || !qcForm.inspector_name}
                className="btn-primary text-sm py-1.5 flex items-center gap-1.5"
              >
                <Check size={14} /> {addingQC ? '...' : tc('save')}
              </button>
            </div>
          </div>
        )}

        {qcRecords.length === 0 ? (
          <div className="flex flex-col items-center py-8 text-gray-300">
            <FlaskConical size={32} className="mb-2 opacity-50" />
            <p className="text-sm">{tf('noQC')}</p>
          </div>
        ) : (
          <div className="space-y-3">
            {qcRecords.map((qc) => {
              const rs = QC_RESULT_STYLES[qc.result] ?? QC_RESULT_STYLES.fail;
              return (
                <div key={qc.id} className="border border-gray-100 rounded-xl p-4 bg-gray-50">
                  <div className="flex items-center gap-2 mb-2">
                    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${rs.badge}`}>
                      {rs.icon}
                      {tf(`results.${qc.result}` as any)}
                    </span>
                    {qc.grade && (
                      <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-white border border-gray-200 text-gray-600">
                        {tf(`grades.${qc.grade}` as any)}
                      </span>
                    )}
                    <span className="ml-auto text-xs text-gray-400">
                      {new Date(qc.checked_at).toLocaleString()}
                    </span>
                    {canEdit && (
                      <button
                        onClick={() => handleDeleteQC(qc.id)}
                        className="p-1 text-gray-300 hover:text-red-500 transition-colors"
                        title={tc('delete')}
                      >
                        <Trash2 size={13} />
                      </button>
                    )}
                  </div>
                  <div className="grid grid-cols-2 gap-x-6 gap-y-1 text-sm">
                    <div>
                      <span className="text-gray-400 text-xs">{tf('inspector')}：</span>
                      <span className="text-gray-700">{qc.inspector_name}</span>
                    </div>
                    {qc.weight_checked != null && (
                      <div>
                        <span className="text-gray-400 text-xs">{tf('weightChecked')}：</span>
                        <span className="text-gray-700">{Number(qc.weight_checked).toLocaleString()} kg</span>
                      </div>
                    )}
                    {qc.notes && (
                      <div className="col-span-2">
                        <span className="text-gray-400 text-xs">{tf('notes')}：</span>
                        <span className="text-gray-600 text-xs">{qc.notes}</span>
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* ── 出口單快速操作（備貨完成時顯示） ── */}
      {canCreateShipment && batch.status === 'ready_to_export' && (
        <div className="card p-5 mb-5 border-l-4 border-l-indigo-400">
          <div className="flex items-center gap-2 mb-4">
            <Ship size={16} className="text-indigo-500" />
            <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wider">
              {t('shipmentAction')}
            </h2>
          </div>

          {!showShipForm ? (
            <div className="space-y-3">
              {/* 建立新出口單 */}
              <button
                onClick={() => setShowShipForm(true)}
                className="w-full flex items-center gap-3 p-3 rounded-xl border-2 border-dashed border-indigo-200 text-indigo-600 hover:bg-indigo-50 transition-colors"
              >
                <Plus size={16} />
                <span className="font-medium text-sm">{t('createShipment')}</span>
              </button>

              {/* 或關聯到既有出口單 */}
              {existingShipments.length > 0 && (
                <div>
                  <p className="text-xs text-gray-400 mb-2 flex items-center gap-1.5">
                    <Link2 size={12} /> {t('orLinkExisting')}
                  </p>
                  <div className="space-y-2">
                    {existingShipments.map(ship => (
                      <div
                        key={ship.id}
                        className="flex items-center justify-between p-3 rounded-xl bg-gray-50 border border-gray-100"
                      >
                        <div>
                          <span className="font-mono text-sm font-semibold text-gray-700">{ship.shipment_no}</span>
                          <span className="text-xs text-gray-400 ml-2">
                            {ship.export_date} · {ship.shipment_batches?.length ?? 0} 批次
                          </span>
                        </div>
                        <button
                          onClick={() => handleLinkShipment(ship.id)}
                          disabled={linkingShipment === ship.id}
                          className="btn-secondary text-xs py-1.5 flex items-center gap-1"
                        >
                          <Link2 size={12} />
                          {linkingShipment === ship.id ? '...' : t('linkToThis')}
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : (
            /* 出口單建立表單 */
            <div className="border border-dashed border-indigo-300 rounded-xl p-4 space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-gray-500 mb-1 block">{t('exportDate')} *</label>
                  <input
                    type="date"
                    value={shipForm.export_date}
                    onChange={e => setShipForm(p => ({ ...p, export_date: e.target.value }))}
                    className="input py-1.5 text-sm"
                  />
                </div>
                <div>
                  <label className="text-xs text-gray-500 mb-1 block">{t('carrier')}</label>
                  <input
                    type="text"
                    value={shipForm.carrier}
                    onChange={e => setShipForm(p => ({ ...p, carrier: e.target.value }))}
                    placeholder="Maersk..."
                    className="input py-1.5 text-sm"
                  />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-gray-500 mb-1 block">{t('vesselName')}</label>
                  <input
                    type="text"
                    value={shipForm.vessel_name}
                    onChange={e => setShipForm(p => ({ ...p, vessel_name: e.target.value }))}
                    className="input py-1.5 text-sm"
                  />
                </div>
                <div>
                  <label className="text-xs text-gray-500 mb-1 block">{t('estimatedArrivalTW')}</label>
                  <input
                    type="date"
                    value={shipForm.estimated_arrival_tw}
                    onChange={e => setShipForm(p => ({ ...p, estimated_arrival_tw: e.target.value }))}
                    className="input py-1.5 text-sm"
                  />
                </div>
              </div>
              <div>
                <label className="text-xs text-gray-500 mb-1 block">{t('shipNotes')}</label>
                <textarea
                  value={shipForm.notes}
                  onChange={e => setShipForm(p => ({ ...p, notes: e.target.value }))}
                  rows={2}
                  className="input py-1.5 text-sm resize-none"
                />
              </div>
              <div className="flex gap-2 justify-end">
                <button onClick={() => setShowShipForm(false)} className="btn-secondary text-sm py-1.5">{tc('cancel')}</button>
                <button
                  onClick={handleCreateShipment}
                  disabled={addingShip || !shipForm.export_date}
                  className="btn-primary text-sm py-1.5 flex items-center gap-1.5"
                >
                  <Ship size={14} /> {addingShip ? '...' : t('createShipment')}
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ── 入庫快速操作（台灣運輸中 / 台灣庫存 時顯示） ── */}
      {canCreateInventory && ['in_transit_tw', 'in_stock'].includes(batch.status) && (
        <div className="card p-5 mb-5 border-l-4 border-l-green-400">
          <div className="flex items-center gap-2 mb-4">
            <PackageOpen size={16} className="text-green-500" />
            <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wider">
              {t('inventoryAction')}
            </h2>
            {!showLotForm && (
              <button
                onClick={() => setShowLotForm(true)}
                className="ml-auto btn-primary text-xs flex items-center gap-1.5 py-1.5 px-3"
              >
                <Plus size={13} /> {t('quickReceive')}
              </button>
            )}
          </div>

          {showLotForm && (
            <div className="border border-dashed border-green-300 rounded-xl p-4 space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-gray-500 mb-1 block">{t('warehouse')} *</label>
                  <select
                    value={lotForm.warehouse_id}
                    onChange={e => {
                      const wId = e.target.value;
                      setLotForm(p => ({ ...p, warehouse_id: wId, location_id: '' }));
                      if (wId) fetchLocations(wId);
                      else setLocations([]);
                    }}
                    className="input py-1.5 text-sm"
                  >
                    <option value="">{t('selectWarehouse')}</option>
                    {warehouses.map(w => (
                      <option key={w.id} value={w.id}>{w.name}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="text-xs text-gray-500 mb-1 block">{t('location')}</label>
                  <select
                    value={lotForm.location_id}
                    onChange={e => setLotForm(p => ({ ...p, location_id: e.target.value }))}
                    className="input py-1.5 text-sm"
                    disabled={!lotForm.warehouse_id}
                  >
                    <option value="">—</option>
                    {locations.map(l => (
                      <option key={l.id} value={l.id}>{l.name}</option>
                    ))}
                  </select>
                </div>
              </div>
              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="text-xs text-gray-500 mb-1 block">{t('receivedDate')} *</label>
                  <input
                    type="date"
                    value={lotForm.received_date}
                    onChange={e => setLotForm(p => ({ ...p, received_date: e.target.value }))}
                    className="input py-1.5 text-sm"
                  />
                </div>
                <div>
                  <label className="text-xs text-gray-500 mb-1 block">{t('receiveWeight')} *</label>
                  <input
                    type="number"
                    value={lotForm.initial_weight_kg}
                    onChange={e => setLotForm(p => ({ ...p, initial_weight_kg: e.target.value }))}
                    step="0.01"
                    min="0.01"
                    className="input py-1.5 text-sm"
                  />
                </div>
                <div>
                  <label className="text-xs text-gray-500 mb-1 block">{t('receiveBoxes')}</label>
                  <input
                    type="number"
                    value={lotForm.initial_boxes}
                    onChange={e => setLotForm(p => ({ ...p, initial_boxes: e.target.value }))}
                    min="1"
                    className="input py-1.5 text-sm"
                  />
                </div>
              </div>
              <div>
                <label className="text-xs text-gray-500 mb-1 block">{t('receiveNotes')}</label>
                <textarea
                  value={lotForm.notes}
                  onChange={e => setLotForm(p => ({ ...p, notes: e.target.value }))}
                  rows={2}
                  placeholder={t('receiveNotesPlaceholder')}
                  className="input py-1.5 text-sm resize-none"
                />
              </div>
              <div className="flex gap-2 justify-end">
                <button onClick={() => setShowLotForm(false)} className="btn-secondary text-sm py-1.5">{tc('cancel')}</button>
                <button
                  onClick={handleCreateLot}
                  disabled={addingLot || !lotForm.warehouse_id || !lotForm.initial_weight_kg}
                  className="btn-primary text-sm py-1.5 flex items-center gap-1.5"
                >
                  <PackageOpen size={14} /> {addingLot ? '...' : t('confirmReceive')}
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ── 關聯出口單 ── */}
      {canViewShipment && relatedShipments.length > 0 && (
        <div className="card p-5 mb-5">
          <div className="flex items-center gap-2 mb-4">
            <Ship size={16} className="text-gray-400" />
            <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wider">
              {t('relatedShipments')}
            </h2>
            <span className="ml-auto text-xs text-gray-400">{relatedShipments.length} {t('shipmentCount')}</span>
          </div>
          <div className="space-y-2">
            {relatedShipments.map(ship => (
              <Link
                key={ship.id}
                href={`/${locale}/shipments/${ship.id}`}
                className="flex items-center justify-between p-3 rounded-xl bg-gray-50 hover:bg-indigo-50 hover:border-indigo-200 border border-transparent transition-colors group"
              >
                <div className="flex items-center gap-3">
                  <span className="font-mono text-sm font-semibold text-indigo-600 group-hover:underline">
                    {ship.shipment_no}
                  </span>
                  <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-indigo-100 text-indigo-700">
                    {ship.status}
                  </span>
                </div>
                <div className="flex items-center gap-4 text-sm text-gray-500">
                  {ship.carrier && <span>{ship.carrier}</span>}
                  <span className="text-xs text-gray-400">{ship.export_date}</span>
                </div>
              </Link>
            ))}
          </div>
        </div>
      )}

      {/* ── 關聯庫存批次 ── */}
      {canViewInventory && relatedLots.length > 0 && (
        <div className="card p-5 mb-5">
          <div className="flex items-center gap-2 mb-4">
            <PackageOpen size={16} className="text-gray-400" />
            <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wider">
              {t('relatedLots')}
            </h2>
            <span className="ml-auto text-xs text-gray-400">{relatedLots.length} {t('lotCount')}</span>
          </div>
          <div className="space-y-2">
            {relatedLots.map((lot: any) => (
              <div
                key={lot.id}
                className="flex items-center justify-between p-3 rounded-xl bg-gray-50 border border-transparent"
              >
                <div className="flex items-center gap-3">
                  <span className="font-mono text-sm font-semibold text-teal-600">{lot.lot_no}</span>
                  <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                    lot.status === 'active' ? 'bg-green-100 text-green-700' :
                    lot.status === 'low_stock' ? 'bg-yellow-100 text-yellow-700' :
                    lot.status === 'depleted' ? 'bg-gray-100 text-gray-500' :
                    'bg-red-100 text-red-700'
                  }`}>
                    {t(`lotStatus.${lot.status}` as any)}
                  </span>
                </div>
                <div className="flex items-center gap-4 text-sm">
                  <span className="text-gray-500">{lot.warehouse?.name}</span>
                  <span className="font-semibold text-gray-700">
                    {Number(lot.current_weight_kg).toLocaleString()} kg
                  </span>
                  <span className="text-xs text-gray-400">{t('ageDays', { days: lot.age_days })}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── 關聯銷售訂單 ── */}
      {canViewSales && (
        <div className="card p-5 mb-5">
          <div className="flex items-center gap-2 mb-4">
            <ShoppingCart size={16} className="text-gray-400" />
            <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wider">
              {t('relatedSales')}
            </h2>
            <span className="ml-auto text-xs text-gray-400">{salesOrders.length} {t('salesCount')}</span>
          </div>

          {salesOrders.length === 0 ? (
            <div className="flex flex-col items-center py-6 text-gray-300">
              <ShoppingCart size={28} className="mb-2 opacity-50" />
              <p className="text-sm">{t('noSalesYet')}</p>
            </div>
          ) : (
            <div className="space-y-2">
              {salesOrders.map((so) => (
                <Link
                  key={so.id}
                  href={`/${locale}/sales/${so.id}`}
                  className="flex items-center justify-between p-3 rounded-xl bg-gray-50 hover:bg-primary-50 hover:border-primary-200 border border-transparent transition-colors group"
                >
                  <div className="flex items-center gap-3">
                    <span className="font-mono text-sm font-semibold text-primary-600 group-hover:underline">
                      {so.order_no}
                    </span>
                    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${SALES_STATUS_STYLES[so.status]}`}>
                      {so.status}
                    </span>
                  </div>
                  <div className="flex items-center gap-4 text-sm text-gray-500">
                    <span>{so.customer?.name}</span>
                    <span className="font-semibold text-gray-700">
                      NT$ {Number(so.total_amount_twd).toLocaleString()}
                    </span>
                    <span className="text-gray-300 text-xs">{so.order_date}</span>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ── 七層成本分析（Excel 風格） ── */}
      {canViewCost && (
        <div className="card p-5">
          <div className="flex items-center gap-2 mb-4">
            <DollarSign size={16} className="text-gray-400" />
            <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wider">
              {tco('title')}
            </h2>
            <div className="ml-auto flex items-center gap-2">
              <span className="text-xs text-gray-400">THB→TWD</span>
              <input
                type="number"
                value={exchangeRate}
                onChange={(e) => setExchangeRate(parseFloat(e.target.value) || 0.92)}
                step="0.01"
                min="0.1"
                max="2"
                className="input w-20 py-1 text-sm text-right"
              />
              <button
                onClick={() => fetchCostSummary(batch!.id, exchangeRate)}
                className="p-1.5 rounded-lg bg-gray-100 hover:bg-gray-200 text-gray-500 transition-colors"
                title={tco('recalculate')}
              >
                <RefreshCw size={14} />
              </button>
            </div>
          </div>

          {costLoading ? (
            <div className="text-center py-8 text-gray-300">{tc('loading')}</div>
          ) : costSummary ? (
            <div className="space-y-4">
              {/* ─── 七層成本條形圖 ─── */}
              <div className="bg-gray-50 rounded-xl p-4">
                {(() => {
                  const layerData: Array<{ key: string; label: string; value: number; color: string; barColor: string }> = [
                    { key: 'material',      label: tco('layers.material'),      value: costSummary.layer_material_twd ?? 0,     color: 'text-orange-700 bg-orange-100',  barColor: 'bg-orange-400' },
                    { key: 'processing',    label: tco('layers.processing'),    value: costSummary.layer_processing_twd ?? 0,   color: 'text-amber-700 bg-amber-100',    barColor: 'bg-amber-400' },
                    { key: 'th_logistics',  label: tco('layers.th_logistics'),  value: costSummary.layer_th_logistics_twd ?? 0, color: 'text-yellow-700 bg-yellow-100',  barColor: 'bg-yellow-400' },
                    { key: 'freight',       label: tco('layers.freight'),       value: costSummary.layer_freight_twd ?? 0,      color: 'text-blue-700 bg-blue-100',      barColor: 'bg-blue-400' },
                    { key: 'tw_customs',    label: tco('layers.tw_customs'),    value: costSummary.layer_tw_customs_twd ?? 0,   color: 'text-indigo-700 bg-indigo-100',  barColor: 'bg-indigo-400' },
                    { key: 'tw_logistics',  label: tco('layers.tw_logistics'),  value: costSummary.layer_tw_logistics_twd ?? 0, color: 'text-teal-700 bg-teal-100',      barColor: 'bg-teal-400' },
                    { key: 'market',        label: tco('layers.market'),        value: costSummary.layer_market_twd ?? 0,       color: 'text-purple-700 bg-purple-100',  barColor: 'bg-purple-400' },
                  ];
                  const total = costSummary.total_cost_twd || 1;
                  return (
                    <div className="space-y-2">
                      {layerData.map(ld => {
                        const pct = (ld.value / total) * 100;
                        return (
                          <div key={ld.key} className="flex items-center gap-2">
                            <span className={`w-20 flex-shrink-0 px-1.5 py-0.5 rounded text-[10px] font-medium text-center ${ld.color}`}>
                              {ld.label}
                            </span>
                            <div className="flex-1 bg-gray-200 rounded-full h-4 overflow-hidden">
                              <div className={`h-full rounded-full ${ld.barColor} transition-all`} style={{ width: `${Math.max(pct, 1)}%` }} />
                            </div>
                            <span className="w-20 text-right text-xs font-semibold text-gray-700 flex-shrink-0">
                              {ld.value > 0 ? `NT$${ld.value.toLocaleString(undefined, { maximumFractionDigits: 0 })}` : '—'}
                            </span>
                          </div>
                        );
                      })}
                    </div>
                  );
                })()}

                {/* 總計 */}
                <div className="border-t border-gray-200 pt-3 mt-3 space-y-1">
                  <div className="flex justify-between text-sm font-semibold">
                    <span className="text-gray-700">{tco('totalLanded')}</span>
                    <span className="text-gray-900">
                      NT${costSummary.total_cost_twd.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                    </span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-500">{tco('perKg')}</span>
                    <span className="font-bold text-primary-700 text-base">
                      NT${costSummary.cost_per_kg_twd.toLocaleString(undefined, { minimumFractionDigits: 1, maximumFractionDigits: 1 })} / kg
                    </span>
                  </div>
                </div>
              </div>

              {/* ─── 成本事件明細（Excel 風格） ─── */}
              {costSummary.cost_events && costSummary.cost_events.length > 0 && (
                <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
                  <div className="bg-gray-50 px-4 py-2 border-b border-gray-200 flex items-center justify-between">
                    <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">
                      {tco('eventList')} ({costSummary.event_count ?? costSummary.cost_events.length})
                    </span>
                  </div>
                  <div className="divide-y divide-gray-50">
                    {costSummary.cost_events.map((evt: CostEvent) => (
                      <div
                        key={evt.id}
                        className={`flex items-center gap-2 px-4 py-2.5 text-sm hover:bg-gray-50 transition-colors ${
                          evt.is_adjustment ? 'bg-red-50/30 line-through opacity-60' : ''
                        }`}
                      >
                        {/* 層級標籤 */}
                        <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium flex-shrink-0 ${
                          LAYER_COLORS[evt.cost_layer as CostLayer] ?? 'bg-gray-100 text-gray-500'
                        }`}>
                          {tco(`layers.${evt.cost_layer}` as any)}
                        </span>
                        {/* 類型 + 描述 */}
                        <div className="flex-1 min-w-0">
                          <span className="text-gray-700 font-medium">
                            {tco(`costTypes.${evt.cost_type}` as any) !== `costTypes.${evt.cost_type}`
                              ? tco(`costTypes.${evt.cost_type}` as any)
                              : evt.cost_type.replace(/_/g, ' ')}
                          </span>
                          {evt.description_zh && (
                            <span className="text-gray-400 text-xs ml-2">{evt.description_zh}</span>
                          )}
                          {evt.is_adjustment && (
                            <span className="text-red-500 text-xs ml-1">[{tco('voided')}]</span>
                          )}
                        </div>
                        {/* 金額 */}
                        <div className="flex items-center gap-3 flex-shrink-0">
                          {evt.amount_thb != null && (
                            <span className="text-xs text-gray-500">
                              ฿{Number(evt.amount_thb).toLocaleString(undefined, { minimumFractionDigits: 2 })}
                            </span>
                          )}
                          {evt.amount_twd != null && (
                            <span className="font-semibold text-gray-700">
                              NT${Number(evt.amount_twd).toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })}
                            </span>
                          )}
                          {/* 沖銷按鈕 */}
                          {canEdit && !evt.is_adjustment && (
                            <button
                              onClick={() => handleVoidCost(evt.id)}
                              disabled={voidingId === evt.id}
                              className="p-1 text-gray-300 hover:text-red-500 transition-colors"
                              title={tco('void')}
                            >
                              <XCircle size={14} />
                            </button>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* ─── 銷售與毛利 ─── */}
              {costSummary.sales_revenue_twd > 0 && (
                <div className="bg-gray-50 rounded-xl p-4 space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-500">{tco('salesRevenue')}</span>
                    <span className="font-semibold text-gray-700">
                      NT${costSummary.sales_revenue_twd.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                    </span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-500">{tco('grossProfit')}</span>
                    <span className={`font-semibold flex items-center gap-1 ${costSummary.gross_profit_twd >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                      {costSummary.gross_profit_twd >= 0 ? <TrendingUp size={14} /> : <TrendingDown size={14} />}
                      NT${costSummary.gross_profit_twd.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                    </span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-500">{tco('marginPct')}</span>
                    <span className={`font-bold text-base ${costSummary.gross_margin_pct >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                      {costSummary.gross_margin_pct.toFixed(1)}%
                    </span>
                  </div>
                </div>
              )}

              {/* ─── 新增成本事件（Excel 風格） ─── */}
              {canEdit && (
                <div>
                  {!showAddCost ? (
                    <button
                      onClick={() => setShowAddCost(true)}
                      className="flex items-center gap-1.5 text-sm text-primary-600 hover:text-primary-700 font-medium"
                    >
                      <Plus size={15} /> {tco('addEvent')}
                    </button>
                  ) : (
                    <div className="border border-dashed border-primary-300 rounded-xl p-4 space-y-3 bg-primary-50/30">

                      {/* ── Row 1: 成本層級 + 成本類型 ── */}
                      <div className="grid grid-cols-2 gap-3">
                        <div>
                          <label className="text-xs text-gray-500 mb-1 block">{tco('layer')} *</label>
                          <select
                            value={newCost.cost_layer}
                            onChange={(e) => setNewCost(p => ({ ...p, cost_layer: e.target.value as CostLayer, cost_type: '', custom_type: '', amount_thb: '', amount_twd: '' }))}
                            className="input py-1.5 text-sm"
                          >
                            {COST_LAYERS.map(l => (
                              <option key={l} value={l}>{tco(`layers.${l}` as any)}</option>
                            ))}
                          </select>
                        </div>
                        <div>
                          <div className="flex items-center justify-between mb-1">
                            <label className="text-xs text-gray-500">{tco('costType')} *</label>
                            {/* 有歷史值時顯示「上次」提示 */}
                            {newCost.cost_type && newCost.cost_type !== '_custom' && recentValues[`${newCost.cost_layer}__${newCost.cost_type}`] && (
                              <span className="text-[10px] bg-blue-100 text-blue-600 px-1.5 py-0.5 rounded font-medium">
                                ↩ 已自動帶入上次紀錄
                              </span>
                            )}
                          </div>
                          <select
                            value={newCost.cost_type}
                            onChange={(e) => handleCostTypeChange(e.target.value)}
                            className="input py-1.5 text-sm"
                          >
                            <option value="">{tco('selectType')}</option>
                            {COST_LAYER_PRESETS[newCost.cost_layer].map(ct => {
                              const hasRecent = !!recentValues[`${newCost.cost_layer}__${ct}`];
                              const label = tco(`costTypes.${ct}` as any) !== `costTypes.${ct}`
                                ? tco(`costTypes.${ct}` as any)
                                : ct.replace(/_/g, ' ');
                              return (
                                <option key={ct} value={ct}>
                                  {hasRecent ? `★ ${label}` : label}
                                </option>
                              );
                            })}
                            <option value="_custom">✏️ {tco('customType')}</option>
                          </select>
                        </div>
                      </div>

                      {/* 自訂類型名稱 */}
                      {newCost.cost_type === '_custom' && (
                        <div>
                          <label className="text-xs text-gray-500 mb-1 block">{tco('customTypeName')} *</label>
                          <input
                            type="text"
                            value={newCost.custom_type}
                            onChange={(e) => setNewCost(p => ({ ...p, custom_type: e.target.value }))}
                            placeholder={tco('customTypePlaceholder')}
                            className="input py-1.5 text-sm"
                          />
                        </div>
                      )}

                      {/* ── Row 2: 數量 × 單價 = 自動計算 ── */}
                      <div>
                        <label className="text-xs text-gray-500 mb-1 block">數量 × 單價（選填，自動計算 THB 金額）</label>
                        <div className="flex items-center gap-2">
                          <input
                            type="number"
                            value={newCost.quantity}
                            onChange={(e) => handleQtyOrUnitChange('quantity', e.target.value)}
                            placeholder="數量"
                            step="0.001"
                            min="0"
                            className="input py-1.5 text-sm flex-1"
                          />
                          <select
                            value={newCost.unit_label}
                            onChange={(e) => setNewCost(p => ({ ...p, unit_label: e.target.value }))}
                            className="input py-1.5 text-sm w-20"
                          >
                            <option value="kg">kg</option>
                            <option value="箱">箱</option>
                            <option value="次">次</option>
                            <option value="批">批</option>
                            <option value="公噸">公噸</option>
                          </select>
                          <span className="text-gray-400 text-sm">×</span>
                          <div className="relative flex-1">
                            <span className="absolute left-2 top-1/2 -translate-y-1/2 text-xs text-gray-400">฿</span>
                            <input
                              type="number"
                              value={newCost.unit_cost}
                              onChange={(e) => handleQtyOrUnitChange('unit_cost', e.target.value)}
                              placeholder="單價"
                              step="0.0001"
                              min="0"
                              className="input py-1.5 text-sm pl-6"
                            />
                          </div>
                          {newCost.quantity && newCost.unit_cost && (
                            <span className="text-xs text-primary-600 font-medium whitespace-nowrap">
                              = ฿{(parseFloat(newCost.quantity) * parseFloat(newCost.unit_cost)).toFixed(2)}
                            </span>
                          )}
                        </div>
                      </div>

                      {/* ── Row 3: 金額（雙幣別）+ 匯率 ── */}
                      <div className="grid grid-cols-3 gap-3">
                        <div>
                          <label className="text-xs text-gray-500 mb-1 block">金額 THB *</label>
                          <div className="relative">
                            <span className="absolute left-3 top-1/2 -translate-y-1/2 text-xs text-gray-400">฿</span>
                            <input
                              type="number"
                              value={newCost.amount_thb}
                              onChange={(e) => handleThbChange(e.target.value)}
                              placeholder="0.00"
                              step="0.01"
                              min="0"
                              className="input py-1.5 text-sm pl-7"
                            />
                          </div>
                        </div>
                        <div>
                          <label className="text-xs text-gray-500 mb-1 block">匯率 THB→TWD</label>
                          <input
                            type="number"
                            value={newCost.item_exchange_rate}
                            onChange={(e) => handleItemRateChange(e.target.value)}
                            placeholder={String(exchangeRate)}
                            step="0.001"
                            min="0"
                            className="input py-1.5 text-sm"
                          />
                        </div>
                        <div>
                          <label className="text-xs text-gray-500 mb-1 block">金額 TWD（自動換算）</label>
                          <div className="relative">
                            <span className="absolute left-2 top-1/2 -translate-y-1/2 text-[10px] text-gray-400">NT$</span>
                            <input
                              type="number"
                              value={newCost.amount_twd}
                              onChange={(e) => setNewCost(p => ({ ...p, amount_twd: e.target.value }))}
                              placeholder="0"
                              step="1"
                              min="0"
                              className="input py-1.5 text-sm pl-8"
                            />
                          </div>
                        </div>
                      </div>
                      <p className="text-[11px] text-gray-400 -mt-1">THB 或 TWD 至少填一個。填入 THB 後會依匯率自動換算 TWD（可手動覆蓋）。</p>

                      {/* ── Row 4: 說明 + 備註 ── */}
                      <div className="grid grid-cols-2 gap-3">
                        <div>
                          <label className="text-xs text-gray-500 mb-1 block">{tco('descriptionZh')}</label>
                          <input
                            type="text"
                            value={newCost.description_zh}
                            onChange={(e) => setNewCost(p => ({ ...p, description_zh: e.target.value }))}
                            placeholder={tco('descriptionPlaceholder')}
                            className="input py-1.5 text-sm"
                          />
                        </div>
                        <div>
                          <label className="text-xs text-gray-500 mb-1 block">{tco('notes')}</label>
                          <input
                            type="text"
                            value={newCost.notes}
                            onChange={(e) => setNewCost(p => ({ ...p, notes: e.target.value }))}
                            className="input py-1.5 text-sm"
                          />
                        </div>
                      </div>

                      {/* ── 按鈕列 ── */}
                      <div className="flex gap-2 justify-end">
                        <button
                          onClick={() => { setShowAddCost(false); resetCostForm(); }}
                          className="btn-secondary text-sm py-1.5"
                        >
                          {tc('cancel')}
                        </button>
                        {/* 繼續新增：儲存後保持表單開啟 */}
                        <button
                          onClick={() => handleAddCost(true)}
                          disabled={addingCost || !(newCost.cost_type === '_custom' ? newCost.custom_type : newCost.cost_type) || !(newCost.amount_thb || newCost.amount_twd)}
                          className="btn-secondary text-sm py-1.5 flex items-center gap-1.5"
                        >
                          <Plus size={14} />
                          繼續新增
                        </button>
                        <button
                          onClick={() => handleAddCost(false)}
                          disabled={addingCost || !(newCost.cost_type === '_custom' ? newCost.custom_type : newCost.cost_type) || !(newCost.amount_thb || newCost.amount_twd)}
                          className="btn-primary text-sm py-1.5 flex items-center gap-1.5"
                        >
                          <Plus size={14} />
                          {addingCost ? '...' : tc('add')}
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          ) : (
            <div className="text-center py-8 text-gray-300 text-sm">{tc('noData')}</div>
          )}
        </div>
      )}

      {/* ── 附件 / 照片 ── */}
      <div className="card p-5 mt-5">
        <div className="flex items-center gap-2 mb-4">
          <Paperclip size={16} className="text-gray-400" />
          <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wider">
            附件 / 照片
          </h2>
          <span className="ml-auto text-xs text-gray-400">{attachments.length} 個檔案</span>

          {/* 只有有編輯權限才顯示上傳按鈕 */}
          {canEdit && (
            <label className={`flex items-center gap-1.5 text-sm font-medium cursor-pointer ml-2 ${uploadingFile ? 'text-gray-400' : 'text-primary-600 hover:text-primary-700'}`}>
              {uploadingFile
                ? <><Loader2 size={14} className="animate-spin" /> 上傳中...</>
                : <><Plus size={14} /> 上傳檔案</>
              }
              {/* 隱藏的 file input，只接受圖片與 PDF */}
              <input
                type="file"
                accept="image/*,application/pdf"
                className="hidden"
                disabled={uploadingFile}
                onChange={handleFileUpload}
              />
            </label>
          )}
        </div>

        {attachments.length === 0 ? (
          /* 空狀態提示 */
          <div className="flex flex-col items-center py-8 text-gray-300">
            <Paperclip size={28} className="mb-2 opacity-50" />
            <p className="text-sm">尚無附件</p>
          </div>
        ) : (
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3">
            {attachments.map((att: any) => {
              // 判斷是否為圖片（依 mime_type）
              const isImage = att.mime_type?.startsWith('image/');
              // 後端靜態檔案 URL：/uploads/{storage_path}
              const backendBase = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';
              const fileUrl = `${backendBase}/uploads/${att.storage_path}`;

              return (
                <div
                  key={att.id}
                  className="relative group border border-gray-200 rounded-xl overflow-hidden bg-gray-50 hover:border-primary-300 transition-colors"
                >
                  {/* 圖片縮圖 / 檔案圖示 */}
                  {isImage ? (
                    <a href={fileUrl} target="_blank" rel="noopener noreferrer">
                      {/* eslint-disable-next-line @next/next/no-img-element */}
                      <img
                        src={fileUrl}
                        alt={att.file_name}
                        className="w-full h-28 object-cover"
                      />
                    </a>
                  ) : (
                    <a
                      href={fileUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex flex-col items-center justify-center h-28 gap-2 text-gray-400 hover:text-primary-600 transition-colors"
                    >
                      <ImageIcon size={28} className="opacity-40" />
                      <span className="text-xs text-center px-2 break-all">{att.file_name}</span>
                    </a>
                  )}

                  {/* 下方資訊列 */}
                  <div className="px-2 py-1.5 flex items-center gap-1">
                    <span className="text-[11px] text-gray-500 truncate flex-1" title={att.file_name}>
                      {att.file_name}
                    </span>

                    {/* 刪除按鈕（只有有編輯權限才顯示） */}
                    {canEdit && (
                      <button
                        onClick={() => handleDeleteAttachment(att.id)}
                        className="flex-shrink-0 p-0.5 text-gray-300 hover:text-red-500 transition-colors opacity-0 group-hover:opacity-100"
                        title="刪除附件"
                      >
                        <Trash2 size={13} />
                      </button>
                    )}
                  </div>

                  {/* 上傳日期 */}
                  <div className="px-2 pb-1.5">
                    <span className="text-[10px] text-gray-400">
                      {att.created_at ? new Date(att.created_at).toLocaleDateString('zh-TW') : ''}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
