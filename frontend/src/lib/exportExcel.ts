import * as XLSX from 'xlsx';
import type { InventoryLot } from '@/types';

export function exportInventoryToExcel(lots: InventoryLot[]) {
  const rows = lots.map(lot => ({
    '批號': lot.lot_no,
    '批次': lot.batch?.batch_no ?? '',
    '倉庫': lot.warehouse?.name ?? '',
    '庫位': lot.location?.name ?? '',
    '運輸方式': lot.import_type === 'air' ? '空運' : lot.import_type === 'sea' ? '海運' : '',
    '報關號碼': lot.customs_declaration_no ?? '',
    '通關日期': lot.customs_clearance_date ?? '',
    '檢驗結果': ({ pass: '通過', fail: '不合格', pending: '待結果', exempted: '免驗' } as Record<string, string>)[lot.inspection_result ?? ''] ?? '',
    '入庫日期': lot.received_date,
    '入庫人員': lot.received_by ?? '',
    '入庫重量(kg)': lot.initial_weight_kg,
    '入庫箱數': lot.initial_boxes ?? '',
    '在庫重量(kg)': lot.current_weight_kg,
    '在庫箱數': lot.current_boxes ?? '',
    '已出貨(kg)': lot.shipped_weight_kg,
    '庫齡(天)': lot.age_days,
    '狀態': ({ active: '正常', low_stock: '低庫存', depleted: '已出清', scrapped: '已報廢' } as Record<string, string>)[lot.status] ?? lot.status,
    '備註': lot.notes ?? '',
  }));

  const ws = XLSX.utils.json_to_sheet(rows);
  const wb = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(wb, ws, '庫存清單');

  // Auto column widths
  const colWidths = Object.keys(rows[0] ?? {}).map(key => ({ wch: Math.max(key.length * 2, 12) }));
  ws['!cols'] = colWidths;

  const date = new Date().toISOString().split('T')[0];
  XLSX.writeFile(wb, `庫存清單_${date}.xlsx`);
}

export function exportShipmentToExcel(shipment: {
  shipment_no: string;
  export_date: string;
  carrier?: string | null;
  vessel_name?: string | null;
  bl_no?: string | null;
  transport_mode?: string | null;
  shipped_boxes?: number | null;
  shipper_name?: string | null;
  export_customs_no?: string | null;
  phyto_cert_no?: string | null;
  phyto_cert_date?: string | null;
  actual_departure_dt?: string | null;
  estimated_arrival_tw?: string | null;
  total_weight?: number | null;
  shipment_batches: Array<{
    batch_id: string;
    batch?: { batch_no: string; current_weight: number; status: string } | null;
  }>;
}) {
  // Sheet 1: Shipment summary
  const summaryRows = [
    { '欄位': '出口單號', '資料': shipment.shipment_no },
    { '欄位': '出口日期', '資料': shipment.export_date },
    { '欄位': '運輸方式', '資料': shipment.transport_mode === 'air' ? '空運' : shipment.transport_mode === 'sea' ? '海運' : '' },
    { '欄位': '承運商', '資料': shipment.carrier ?? '' },
    { '欄位': '航班/船班', '資料': shipment.vessel_name ?? '' },
    { '欄位': 'AWB/B/L', '資料': shipment.bl_no ?? '' },
    { '欄位': '出貨人', '資料': shipment.shipper_name ?? '' },
    { '欄位': '出口報關號碼', '資料': shipment.export_customs_no ?? '' },
    { '欄位': '植檢證號碼', '資料': shipment.phyto_cert_no ?? '' },
    { '欄位': '植檢日期', '資料': shipment.phyto_cert_date ?? '' },
    { '欄位': '實際出發時間', '資料': shipment.actual_departure_dt ? new Date(shipment.actual_departure_dt).toLocaleString('zh-TW') : '' },
    { '欄位': '預計抵台', '資料': shipment.estimated_arrival_tw ?? '' },
    { '欄位': '總重量(kg)', '資料': shipment.total_weight ?? '' },
    { '欄位': '箱數', '資料': shipment.shipped_boxes ?? '' },
  ];

  // Sheet 2: Batch list
  const batchRows = shipment.shipment_batches.map((sb, i) => ({
    '序號': i + 1,
    '批次號': sb.batch?.batch_no ?? sb.batch_id,
    '重量(kg)': sb.batch?.current_weight ?? '',
    '狀態': sb.batch?.status ?? '',
  }));

  const wb = XLSX.utils.book_new();
  const ws1 = XLSX.utils.json_to_sheet(summaryRows);
  ws1['!cols'] = [{ wch: 20 }, { wch: 30 }];
  XLSX.utils.book_append_sheet(wb, ws1, '出口單資料');

  if (batchRows.length > 0) {
    const ws2 = XLSX.utils.json_to_sheet(batchRows);
    ws2['!cols'] = [{ wch: 8 }, { wch: 20 }, { wch: 12 }, { wch: 15 }];
    XLSX.utils.book_append_sheet(wb, ws2, '批次明細');
  }

  XLSX.writeFile(wb, `出口單_${shipment.shipment_no}.xlsx`);
}
