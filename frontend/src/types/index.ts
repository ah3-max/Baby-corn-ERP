// ─── 認證相關 ────────────────────────────────────────

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface UserMe {
  id: string;
  email: string;
  full_name: string;
  preferred_language: string;
  role: RoleSimple | null;
  permissions: string[];
}

// ─── 使用者相關 ────────────────────────────────────────

export interface User {
  id: string;
  email: string;
  full_name: string;
  preferred_language: string;
  is_active: boolean;
  note: string | null;
  created_at: string;
  updated_at: string;
  role: RoleSimple | null;
}

export interface UserCreate {
  email: string;
  password: string;
  full_name: string;
  role_id?: string;
  preferred_language: string;
  note?: string;
}

export interface UserUpdate {
  full_name?: string;
  role_id?: string;
  preferred_language?: string;
  is_active?: boolean;
  note?: string;
}

// ─── 角色相關 ────────────────────────────────────────

export interface RoleSimple {
  id: string;
  name: string;
}

export interface Permission {
  id: string;
  module: string;
  action: string;
}

export interface Role {
  id: string;
  name: string;
  description: string | null;
  is_system: boolean;
  created_at: string;
  permissions: Permission[];
}

export interface RoleCreate {
  name: string;
  description?: string;
  permission_ids: string[];
}

export interface RoleUpdate {
  name?: string;
  description?: string;
  permission_ids?: string[];
}

// ─── 採購相關 ────────────────────────────────────────

export type PurchaseStatus = 'draft' | 'confirmed' | 'in_transit' | 'arrived' | 'closed';

export interface PurchaseSupplierSimple {
  id: string;
  name: string;
  supplier_type: string;
}

export interface PurchaseOrder {
  id: string;
  order_no: string;
  order_date: string;
  supplier_id: string;
  supplier: PurchaseSupplierSimple | null;
  source_farmer_id: string | null;
  source_farmer: PurchaseSupplierSimple | null;
  estimated_weight: number;
  unit_price: number;
  total_amount: number;
  expected_arrival: string | null;
  status: PurchaseStatus;
  arrived_at: string | null;
  received_weight: number | null;
  defect_weight: number | null;
  usable_weight: number | null;
  defect_rate: number | null;
  arrival_note: string | null;
  note: string | null;
  created_at: string;
  updated_at: string;
}

// ─── 供應商相關 ────────────────────────────────────────

export type SupplierType = 'farmer' | 'broker' | 'factory' | 'logistics' | 'customs' | 'packaging';

export interface Supplier {
  id: string;
  name: string;
  supplier_type: SupplierType;
  contact_name: string | null;
  phone: string | null;
  region: string | null;
  address: string | null;
  payment_terms: string | null;
  bank_account: string | null;
  note: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

// ─── 批次相關 ────────────────────────────────────────

export type BatchStatus =
  | 'processing'
  | 'qc_pending'
  | 'qc_done'
  | 'packaging'
  | 'ready_to_export'
  | 'exported'
  | 'in_transit_tw'
  | 'in_stock'
  | 'sold'
  | 'closed';

export interface BatchPO {
  id: string;
  order_no: string;
  supplier: { id: string; name: string } | null;
}

export interface Batch {
  id: string;
  batch_no: string;
  purchase_order_id: string;
  purchase_order: BatchPO | null;
  initial_weight: number;
  current_weight: number;
  status: BatchStatus;
  note: string | null;
  created_at: string;
  updated_at: string;
  // 生鮮時效追蹤
  harvest_datetime?: string | null;
  harvest_location?: string | null;
  harvest_temperature?: number | null;
  harvest_weather?: string | null;
  transport_refrigerated?: boolean | null;
  factory_arrival_dt?: string | null;
  factory_temp_on_arrival?: number | null;
  factory_complete_dt?: string | null;
  cold_storage_temp?: number | null;
  packed_dt?: string | null;
  container_loaded_dt?: string | null;
  shelf_life_days?: number | null;
  // 計算欄位
  hours_since_harvest?: number | null;
  days_since_harvest?: number | null;
  remaining_days?: number | null;
  freshness_status?: 'fresh' | 'warning' | 'critical' | 'expired' | null;
}

// 狀態推進映射（前端用）
export const BATCH_STATUS_NEXT: Record<string, string | null> = {
  processing:      'qc_pending',
  qc_pending:      'qc_done',
  qc_done:         'packaging',
  packaging:       'ready_to_export',
  ready_to_export: 'exported',
  exported:        'in_transit_tw',
  in_transit_tw:   'in_stock',
  in_stock:        'sold',
  sold:            'closed',
  closed:          null,
};

// 所有批次狀態（順序）
export const BATCH_STATUSES: BatchStatus[] = [
  'processing', 'qc_pending', 'qc_done', 'packaging',
  'ready_to_export', 'exported', 'in_transit_tw',
  'in_stock', 'sold', 'closed',
];

// ─── QC 相關 ────────────────────────────────────────

export interface QCRecord {
  id:             string;
  batch_id:       string;
  inspector_name: string;
  checked_at:     string;
  result:         'pass' | 'fail' | 'conditional_pass';
  grade:          string | null;
  weight_checked: number | null;
  notes:          string | null;
  created_at:     string;
}

// ─── 出口物流相關 ────────────────────────────────────────

export type ShipmentStatus = 'preparing' | 'customs_th' | 'in_transit' | 'customs_tw' | 'arrived_tw';

export interface ShipmentBatch {
  batch_id: string;
  batch: { id: string; batch_no: string; current_weight: number; status: string } | null;
}

export interface Shipment {
  id:                   string;
  shipment_no:          string;
  export_date:          string;
  carrier:              string | null;
  vessel_name:          string | null;
  bl_no:                string | null;
  estimated_arrival_tw: string | null;
  actual_arrival_tw:    string | null;
  status:               ShipmentStatus;
  total_weight:         number | null;
  freight_cost:         number | null;
  customs_cost:         number | null;
  insurance_cost:       number | null;
  handling_cost:        number | null;
  other_cost:           number | null;
  notes:                string | null;
  // Module J fields
  transport_mode:       string | null;
  shipped_boxes:        number | null;
  shipper_name:         string | null;
  export_customs_no:    string | null;
  phyto_cert_no:        string | null;
  phyto_cert_date:      string | null;
  actual_departure_dt:  string | null;
  // 空運欄位
  awb_no:               string | null;
  flight_no:            string | null;
  airline:              string | null;
  // 海運欄位
  container_no:         string | null;
  port_of_loading:      string | null;
  port_of_discharge:    string | null;
  shipment_batches:     ShipmentBatch[];
  created_at:           string;
  updated_at:           string;
}

export const SHIPMENT_STATUS_NEXT: Record<string, string | null> = {
  preparing:  'customs_th',
  customs_th: 'in_transit',
  in_transit: 'customs_tw',
  customs_tw: 'arrived_tw',
  arrived_tw: null,
};

// ─── 客戶相關 ────────────────────────────────────────

export interface Customer {
  id:            string;
  name:          string;
  contact_name:  string | null;
  phone:         string | null;
  email:         string | null;
  region:        string | null;
  address:       string | null;
  payment_terms: string | null;
  note:          string | null;
  is_active:     boolean;
  created_at:    string;
  updated_at:    string;
}

// ─── 銷售相關 ────────────────────────────────────────

export type SalesStatus = 'draft' | 'confirmed' | 'delivered' | 'invoiced' | 'closed';

export interface SalesOrderItem {
  id:               string;
  batch_id:         string;
  batch:            { id: string; batch_no: string } | null;
  quantity_kg:      number;
  unit_price_twd:   number;
  total_amount_twd: number;
  note:             string | null;
}

export interface SalesOrder {
  id:               string;
  order_no:         string;
  customer_id:      string;
  customer:         { id: string; name: string } | null;
  order_date:       string;
  delivery_date:    string | null;
  total_amount_twd: number;
  status:           SalesStatus;
  note:             string | null;
  items:            SalesOrderItem[];
  created_at:       string;
  updated_at:       string;
}

export const SALES_STATUS_NEXT: Record<string, string | null> = {
  draft:     'confirmed',
  confirmed: 'delivered',
  delivered: 'invoiced',
  invoiced:  'closed',
  closed:    null,
};

// ─── 成本相關 ────────────────────────────────────────

export type CostLayer = 'material' | 'processing' | 'th_logistics' | 'freight' | 'tw_customs' | 'tw_logistics' | 'market';

// 七層成本的預設類型
export const COST_LAYER_PRESETS: Record<CostLayer, string[]> = {
  material:      ['purchase_price', 'quality_check', 'farm_transport'],
  processing:    ['oem_fee', 'cold_storage_fee', 'packaging_material', 'labor'],
  th_logistics:  ['factory_to_port', 'inland_transport', 'loading_fee'],
  freight:       ['sea_freight', 'air_freight', 'insurance', 'container_fee'],
  tw_customs:    ['customs_duty', 'inspection_fee', 'broker_fee', 'quarantine_fee'],
  tw_logistics:  ['port_to_warehouse', 'cold_storage_tw', 'daily_delivery', 'pickup_fee'],
  market:        ['channel_commission', 'marketing_fee', 'sample_cost', 'return_handling'],
};

export const COST_LAYERS: CostLayer[] = [
  'material', 'processing', 'th_logistics', 'freight', 'tw_customs', 'tw_logistics', 'market',
];

export interface CostEvent {
  id:              string;
  batch_id:        string;
  cost_layer:      CostLayer;
  cost_type:       string;
  description_zh:  string | null;
  amount_thb:      number | null;
  amount_twd:      number | null;
  exchange_rate:   number | null;
  quantity:        number | null;
  unit_cost:       number | null;
  unit_label:      string | null;
  is_adjustment:   boolean;
  adjustment_ref:  string | null;
  notes:           string | null;
  recorded_at:     string;
}

// 舊版相容（保留給可能還在用的地方）
export type CostCategory = 'freight' | 'customs' | 'processing' | 'packaging' | 'storage' | 'other';
export interface CostItem {
  id:         string;
  batch_id:   string;
  category:   CostCategory;
  name:       string;
  amount:     number;
  currency:   'THB' | 'TWD';
  note:       string | null;
  created_at: string;
}

export interface BatchCostSummary {
  batch_id:              string;
  batch_no:              string;
  initial_weight_kg:     number;
  current_weight_kg:     number;
  // 七層成本（TWD）
  layer_material_twd:    number;
  layer_processing_twd:  number;
  layer_th_logistics_twd:number;
  layer_freight_twd:     number;
  layer_tw_customs_twd:  number;
  layer_tw_logistics_twd:number;
  layer_market_twd:      number;
  // 彙總
  total_cost_twd:        number;
  cost_per_kg_twd:       number;
  // 銷售與利潤
  sales_revenue_twd:     number;
  gross_profit_twd:      number;
  gross_margin_pct:      number;
  // 明細
  cost_events:           CostEvent[];
  event_count:           number;
  exchange_rate:         number;
}

// ─── 庫存管理相關 ────────────────────────────────────────

export interface Warehouse {
  id:        string;
  name:      string;
  address:   string | null;
  notes:     string | null;
  is_active: boolean;
}

export interface WarehouseLocation {
  id:           string;
  warehouse_id: string;
  name:         string;
  notes:        string | null;
  is_active:    boolean;
}

export type LotStatus = 'active' | 'low_stock' | 'depleted' | 'scrapped';

export interface InventoryTransaction {
  id:         string;
  txn_type:   'in' | 'out' | 'scrap' | 'adjust';
  weight_kg:  number;
  boxes:      number | null;
  reference:  string | null;
  reason:     string | null;
  created_at: string;
}

export interface InventoryLot {
  id:                 string;
  lot_no:             string;
  batch_id:           string;
  batch:              { id: string; batch_no: string; status: string } | null;
  warehouse_id:       string;
  warehouse:          Warehouse | null;
  location_id:        string | null;
  location:           WarehouseLocation | null;
  spec:               string | null;
  received_date:      string;
  initial_weight_kg:  number;
  initial_boxes:      number | null;
  current_weight_kg:  number;
  current_boxes:      number | null;
  shipped_weight_kg:  number;
  shipped_boxes:      number | null;
  scrapped_weight_kg: number;
  status:             LotStatus;
  notes:              string | null;
  age_days:           number;
  created_at:         string;
  transactions:       InventoryTransaction[];
  // Module K fields
  import_type?: string | null;
  customs_declaration_no?: string | null;
  customs_clearance_date?: string | null;
  inspection_result?: string | null;
  received_by?: string | null;
  shipment_id?: string | null;
}

export interface InventorySummary {
  total_weight_kg: number;
  total_boxes:     number;
  lot_count:       number;
  age_ok:          number;
  age_warning:     number;
  age_alert:       number;
}

// ─── 支援的語言 ────────────────────────────────────────

export type Locale = 'zh-TW' | 'en' | 'th';
