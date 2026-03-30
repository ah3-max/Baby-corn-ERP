"""
Schema migrations — ADD COLUMN IF NOT EXISTS (safe to run multiple times)
"""
from sqlalchemy import text, inspect

from database import Base


def run_migrations(engine):
    """Add new columns to existing tables without destroying data."""
    with engine.connect() as conn:
        # ── Batch freshness tracking ──────────────────────────────────
        batch_cols = [
            ("harvest_datetime",        "TIMESTAMP"),
            ("harvest_location",        "VARCHAR(200)"),
            ("harvest_temperature",     "NUMERIC(4,1)"),
            ("harvest_weather",         "VARCHAR(50)"),
            ("transport_refrigerated",  "BOOLEAN"),
            ("factory_arrival_dt",      "TIMESTAMP"),
            ("factory_temp_on_arrival", "NUMERIC(4,1)"),
            ("factory_complete_dt",     "TIMESTAMP"),
            ("cold_storage_temp",       "NUMERIC(4,1)"),
            ("packed_dt",               "TIMESTAMP"),
            ("container_loaded_dt",     "TIMESTAMP"),
            ("shelf_life_days",         "INTEGER DEFAULT 23"),
        ]
        for col, typ in batch_cols:
            conn.execute(text(
                f"ALTER TABLE batches ADD COLUMN IF NOT EXISTS {col} {typ}"
            ))
        conn.commit()

        # ── Shipment Module J fields ──────────────────────────────────
        shipment_cols = [
            ("transport_mode",     "VARCHAR(10)"),     # air / sea
            ("shipped_boxes",      "INTEGER"),          # 箱數
            ("shipper_name",       "VARCHAR(100)"),     # 出貨人
            ("export_customs_no",  "VARCHAR(100)"),     # 出口報關號碼
            ("phyto_cert_no",      "VARCHAR(100)"),     # 植檢證號碼
            ("phyto_cert_date",    "DATE"),             # 植檢日期
            ("actual_departure_dt","TIMESTAMP"),        # 實際出發時間
            # 空運專屬
            ("awb_no",             "VARCHAR(100)"),     # AWB 提單號
            ("flight_no",          "VARCHAR(50)"),      # 航班號
            ("airline",            "VARCHAR(100)"),     # 航空公司
            # 海運專屬
            ("container_no",       "VARCHAR(100)"),     # 貨櫃號碼
            ("port_of_loading",    "VARCHAR(100)"),     # 裝載港
            ("port_of_discharge",  "VARCHAR(100)"),     # 卸貨港
            # 補充費用（TWD）
            ("insurance_cost",     "NUMERIC(12,2)"),    # 保險費
            ("handling_cost",      "NUMERIC(12,2)"),    # 搬運/倉儲費
            ("other_cost",         "NUMERIC(12,2)"),    # 其他費用
        ]
        for col, typ in shipment_cols:
            conn.execute(text(
                f"ALTER TABLE shipments ADD COLUMN IF NOT EXISTS {col} {typ}"
            ))

        # ── InventoryLot Module K fields ─────────────────────────────────
        lot_cols = [
            ("import_type",             "VARCHAR(10)"),    # air / sea
            ("customs_declaration_no",  "VARCHAR(100)"),   # 報關號碼
            ("customs_clearance_date",  "DATE"),           # 通關日期
            ("inspection_result",       "VARCHAR(20)"),    # pass/fail/pending/exempted
            ("received_by",             "VARCHAR(100)"),   # 入庫人員
            ("shipment_id",             "UUID REFERENCES shipments(id) ON DELETE SET NULL"),
        ]
        for col, typ in lot_cols:
            conn.execute(text(
                f"ALTER TABLE inventory_lots ADD COLUMN IF NOT EXISTS {col} {typ}"
            ))
        # ── InventoryLot 報關費用欄位 ─────────────────────────────
        lot_fee_cols = [
            ("arrival_weight_kg",    "NUMERIC(10,2)"),   # 實際到貨重量
            ("customs_fee_twd",      "NUMERIC(10,2)"),   # 報關費
            ("quarantine_fee_twd",   "NUMERIC(10,2)"),   # 檢疫費
            ("import_tax_twd",       "NUMERIC(10,2)"),   # 關稅
            ("cold_chain_fee_twd",   "NUMERIC(10,2)"),   # 冷鏈物流費
            ("tw_transport_fee_twd", "NUMERIC(10,2)"),   # 台灣內陸運費
        ]
        for col, typ in lot_fee_cols:
            conn.execute(text(
                f"ALTER TABLE inventory_lots ADD COLUMN IF NOT EXISTS {col} {typ}"
            ))
        conn.commit()

    # ── Roles 三語欄位 ─────────────────────────────────────────────
    with engine.connect() as conn:
        role_new_cols = [
            ("code",    "VARCHAR(30) UNIQUE"),
            ("name_zh", "VARCHAR(50)"),
            ("name_en", "VARCHAR(50)"),
            ("name_th", "VARCHAR(50)"),
        ]
        for col, typ in role_new_cols:
            conn.execute(text(
                f"ALTER TABLE roles ADD COLUMN IF NOT EXISTS {col} {typ}"
            ))
        conn.commit()

    # ── Permissions 三語欄位 ─────────────────────────────────────
    with engine.connect() as conn:
        perm_new_cols = [
            ("code",    "VARCHAR(60) UNIQUE"),
            ("name_zh", "VARCHAR(80)"),
            ("name_en", "VARCHAR(80)"),
            ("name_th", "VARCHAR(80)"),
        ]
        for col, typ in perm_new_cols:
            conn.execute(text(
                f"ALTER TABLE permissions ADD COLUMN IF NOT EXISTS {col} {typ}"
            ))
        conn.commit()

    # ── QC 擴充欄位 ────────────────────────────────────────────────
    with engine.connect() as conn:
        qc_new_cols = [
            ("inspection_type",  "VARCHAR(30)"),
            ("quality_data",     "JSONB DEFAULT '{}'::jsonb"),
            ("defect_rate_pct",  "NUMERIC(5,2)"),
            ("pesticide_name",   "VARCHAR(100)"),
            ("pesticide_value",  "NUMERIC(8,4)"),
            ("pesticide_limit",  "NUMERIC(8,4)"),
            ("photo_count",      "INTEGER DEFAULT 0"),
        ]
        for col, typ in qc_new_cols:
            conn.execute(text(
                f"ALTER TABLE qc_records ADD COLUMN IF NOT EXISTS {col} {typ}"
            ))
        conn.commit()

    # ── Supplier 補強欄位 ────────────────────────────────────────────
    with engine.connect() as conn:
        supplier_new_cols = [
            ("code",            "VARCHAR(10) UNIQUE"),
            ("name_en",         "VARCHAR(100)"),
            ("name_th",         "VARCHAR(100)"),
            ("line_id",         "VARCHAR(50)"),
            ("national_id",     "VARCHAR(20)"),
            ("province",        "VARCHAR(50)"),
            ("district",        "VARCHAR(50)"),
            ("gap_cert_no",     "VARCHAR(50)"),
            ("gap_cert_expiry", "DATE"),
            ("deleted_at",      "TIMESTAMP"),
        ]
        for col, typ in supplier_new_cols:
            conn.execute(text(
                f"ALTER TABLE suppliers ADD COLUMN IF NOT EXISTS {col} {typ}"
            ))
        conn.commit()

    # ── Customer 補強欄位 ────────────────────────────────────────────
    with engine.connect() as conn:
        customer_new_cols = [
            ("code",                    "VARCHAR(20) UNIQUE"),
            ("customer_type",           "VARCHAR(20)"),
            ("market_code",             "VARCHAR(10)"),
            ("preferred_specs",         "JSONB DEFAULT '[]'::jsonb"),
            ("credit_status",           "VARCHAR(10) DEFAULT 'good' NOT NULL"),
            ("assigned_sales_user_id",  "UUID REFERENCES users(id) ON DELETE SET NULL"),
            ("deleted_at",              "TIMESTAMP"),
        ]
        for col, typ in customer_new_cols:
            conn.execute(text(
                f"ALTER TABLE customers ADD COLUMN IF NOT EXISTS {col} {typ}"
            ))
        conn.commit()

    # ── 新增成本與稽核表（不刪除舊表 batch_cost_items）──────────────
    # 匯入所有 model 確保 metadata 包含新表
    import models  # noqa: F401
    inspector = inspect(engine)
    existing = set(inspector.get_table_names())

    # 只建立尚不存在的新表（注意順序：被參照的表要先建）
    new_tables = [
        "product_types", "oem_factories",
        "processing_orders", "processing_batch_links",
        "cost_events", "batch_cost_sheets", "batch_cost_sheet_items",
        "sale_batch_allocations",
        "payment_records",
        "exchange_rates",
        "attachments", "attachment_tags",
        "notifications",
        "system_settings", "i18n_overrides",
        "domain_events", "audit_logs",
        "daily_sales", "daily_sale_items", "market_prices",
    ]
    tables_to_create = [
        Base.metadata.tables[t]
        for t in new_tables
        if t not in existing and t in Base.metadata.tables
    ]
    if tables_to_create:
        Base.metadata.create_all(engine, tables=tables_to_create)

    # ── Batch 品項類型欄位（product_types 表已建好後才加 FK）──────
    if "batches" in existing:
        batch_new_cols = [
            ("product_type_id",  "UUID REFERENCES product_types(id) ON DELETE SET NULL"),
            ("size_grade",       "VARCHAR(5)"),
            ("quality_data",     "JSONB DEFAULT '{}'::jsonb"),
            ("region_code",      "VARCHAR(5)"),
        ]
        with engine.connect() as conn:
            for col, typ in batch_new_cols:
                conn.execute(text(
                    f"ALTER TABLE batches ADD COLUMN IF NOT EXISTS {col} {typ}"
                ))
            conn.commit()

        # ── 採購單新增品項欄位 ──────────────────────────────────
        with engine.connect() as conn:
            conn.execute(text(
                "ALTER TABLE purchase_orders ADD COLUMN IF NOT EXISTS "
                "product_type_id UUID REFERENCES product_types(id) ON DELETE SET NULL"
            ))
            conn.commit()

    # ── WP1-2：sales_order_items 加入成本快照欄位 ─────────────────
    with engine.connect() as conn:
        conn.execute(text(
            "ALTER TABLE sales_order_items ADD COLUMN IF NOT EXISTS "
            "cost_per_kg_twd NUMERIC(10,4)"
        ))
        conn.commit()

    # ── 舊 batch_cost_items 資料遷移 ──────────────────────────────
    if "batch_cost_items" in existing:
        migrate_legacy_cost_items(engine)

    # ── WP3：Customer 擴展欄位 ──────────────────────────────────
    with engine.connect() as conn:
        customer_new_cols = [
            ("channel_type",          "VARCHAR(20)"),        # chain_store/distributor/wholesaler/restaurant/consignee/direct/th_supplier
            ("tier",                  "VARCHAR(10)"),        # vip/a/b/c/potential
            ("credit_limit_twd",      "NUMERIC(14,2)"),      # 信用額度
            ("current_ar_balance_twd", "NUMERIC(14,2) DEFAULT 0"),  # 目前應收餘額（快取）
            ("sales_team_id",         "UUID REFERENCES sales_teams(id) ON DELETE SET NULL"),
        ]
        for col, typ in customer_new_cols:
            try:
                conn.execute(text(f"ALTER TABLE customers ADD COLUMN IF NOT EXISTS {col} {typ}"))
            except Exception:
                pass
        conn.commit()

    # ── P1-4：sales_orders 冪等鍵欄位 ─────────────────────────────
    with engine.connect() as conn:
        conn.execute(text(
            "ALTER TABLE sales_orders ADD COLUMN IF NOT EXISTS "
            "idempotency_key VARCHAR(100) UNIQUE"
        ))
        conn.commit()

    # ── P0-7：suppliers 敏感欄位加寬為 TEXT（Fernet 加密後長度超過 VARCHAR(20/200)）
    with engine.connect() as conn:
        conn.execute(text(
            "ALTER TABLE suppliers ALTER COLUMN national_id TYPE TEXT"
        ))
        conn.execute(text(
            "ALTER TABLE suppliers ALTER COLUMN bank_account TYPE TEXT"
        ))
        conn.commit()

    # ── WP1-3：高頻查詢欄位索引 ──────────────────────────────────
    _create_indexes(engine)


# ── 舊成本資料遷移邏輯 ──────────────────────────────────────────────
# 舊 category → 新 cost_layer 對照
_LEGACY_LAYER_MAP = {
    "freight":    "freight",
    "customs":    "tw_customs",
    "processing": "processing",
    "packaging":  "processing",
    "storage":    "tw_logistics",
    "other":      "material",
}


def migrate_legacy_cost_items(engine):
    """將 batch_cost_items 舊資料搬移到 cost_events（只執行一次）

    遷移條件：cost_events 表為空且 batch_cost_items 有資料時才執行。
    遷移完成後不刪除舊表，保留作為備份。
    """
    with engine.connect() as conn:
        # 檢查是否已有新資料（避免重複遷移）
        result = conn.execute(text("SELECT COUNT(*) FROM cost_events"))
        if result.scalar() > 0:
            return  # 已遷移過，跳過

        # 檢查舊表是否有資料
        result = conn.execute(text("SELECT COUNT(*) FROM batch_cost_items"))
        if result.scalar() == 0:
            return  # 無資料需要遷移

        # 逐筆搬移
        rows = conn.execute(text(
            "SELECT id, batch_id, category, name, amount, currency, note, "
            "created_by, created_at FROM batch_cost_items"
        ))
        for row in rows:
            layer = _LEGACY_LAYER_MAP.get(row.category, "material")
            cost_type = f"legacy_{row.category}"

            # 依據幣別分別填入 amount_thb / amount_twd
            amount_thb = float(row.amount) if row.currency == "THB" else None
            amount_twd = float(row.amount) if row.currency != "THB" else None

            conn.execute(text(
                "INSERT INTO cost_events "
                "(id, batch_id, cost_layer, cost_type, description_zh, "
                " amount_thb, amount_twd, is_adjustment, recorded_at, recorded_by, notes) "
                "VALUES "
                "(:id, :batch_id, :layer, :cost_type, :desc, "
                " :thb, :twd, false, :recorded_at, :recorded_by, :notes)"
            ), {
                "id": row.id,
                "batch_id": row.batch_id,
                "layer": layer,
                "cost_type": cost_type,
                "desc": row.name,
                "thb": amount_thb,
                "twd": amount_twd,
                "recorded_at": row.created_at,
                "recorded_by": row.created_by,
                "notes": row.note,
            })
        conn.commit()


def _create_indexes(engine):
    """WP1-3：為高頻查詢欄位建立索引（CREATE INDEX IF NOT EXISTS，可重複執行）"""
    indexes = [
        # batches
        ("ix_batches_status",               "batches",              "status"),
        ("ix_batches_purchase_order_id",    "batches",              "purchase_order_id"),
        ("ix_batches_product_type_id",      "batches",              "product_type_id"),
        ("ix_batches_created_at",           "batches",              "created_at"),
        # purchase_orders
        ("ix_purchase_orders_status",       "purchase_orders",      "status"),
        ("ix_purchase_orders_supplier_id",  "purchase_orders",      "supplier_id"),
        ("ix_purchase_orders_created_at",   "purchase_orders",      "created_at"),
        # qc_records
        ("ix_qc_records_batch_id",          "qc_records",           "batch_id"),
        ("ix_qc_records_result",            "qc_records",           "result"),
        ("ix_qc_records_checked_at",        "qc_records",           "checked_at"),
        # sales_orders
        ("ix_sales_orders_customer_id",     "sales_orders",         "customer_id"),
        ("ix_sales_orders_status",          "sales_orders",         "status"),
        ("ix_sales_orders_created_at",      "sales_orders",         "created_at"),
        # sales_order_items
        ("ix_sales_order_items_batch_id",   "sales_order_items",    "batch_id"),
        ("ix_sales_order_items_order_id",   "sales_order_items",    "sales_order_id"),
        # inventory_lots
        ("ix_inventory_lots_batch_id",      "inventory_lots",       "batch_id"),
        ("ix_inventory_lots_warehouse_id",  "inventory_lots",       "warehouse_id"),
        ("ix_inventory_lots_status",        "inventory_lots",       "status"),
        ("ix_inventory_lots_received_date", "inventory_lots",       "received_date"),
        # inventory_transactions
        ("ix_inv_txn_lot_id",               "inventory_transactions", "lot_id"),
        ("ix_inv_txn_created_at",           "inventory_transactions", "created_at"),
        # cost_events
        ("ix_cost_events_batch_id",         "cost_events",          "batch_id"),
        ("ix_cost_events_cost_layer",       "cost_events",          "cost_layer"),
        ("ix_cost_events_recorded_at",      "cost_events",          "recorded_at"),
        # daily_sales
        ("ix_daily_sales_sale_date",        "daily_sales",          "sale_date"),
        ("ix_daily_sales_customer_id",      "daily_sales",          "customer_id"),
        # payment_records
        ("ix_payment_records_customer_id",  "payment_records",      "customer_id"),
        ("ix_payment_records_sales_order",  "payment_records",      "sales_order_id"),
        ("ix_payment_records_payment_date", "payment_records",      "payment_date"),
        # shipments
        ("ix_shipments_status",             "shipments",            "status"),
        ("ix_shipments_created_at",         "shipments",            "created_at"),
        # processing_orders
        ("ix_processing_orders_status",     "processing_orders",    "status"),
        ("ix_processing_orders_factory_id", "processing_orders",    "oem_factory_id"),
        # suppliers
        ("ix_suppliers_is_active",          "suppliers",            "is_active"),
        # customers
        ("ix_customers_is_active",          "customers",            "is_active"),
    ]
    with engine.connect() as conn:
        for idx_name, table, column in indexes:
            try:
                conn.execute(text(
                    f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table} ({column})"
                ))
            except Exception:
                pass  # 表或欄位可能不存在，跳過
        conn.commit()
