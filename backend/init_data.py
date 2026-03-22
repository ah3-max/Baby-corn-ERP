"""
初始資料建立腳本
在第一次啟動時執行，建立預設角色、權限、管理員帳號、品項、系統設定
執行方式：python init_data.py

使用 INSERT ... ON CONFLICT DO NOTHING 避免重複建立。
"""
import json
from sqlalchemy.orm import Session
from sqlalchemy import text
from database import SessionLocal, engine, Base
from models.user import User, Role, Permission, RolePermission
from utils.security import hash_password

# ═══════════════════════════════════════════════════════════════════
# 權限定義 — module.action 格式
# ═══════════════════════════════════════════════════════════════════
PERMISSIONS = [
    # 供應商
    {"code": "supplier.create",  "module": "supplier",  "action": "create",  "name_zh": "新增供應商",      "name_en": "Create Supplier",         "name_th": "สร้างซัพพลายเออร์"},
    {"code": "supplier.read",    "module": "supplier",  "action": "read",    "name_zh": "查看供應商",      "name_en": "View Supplier",           "name_th": "ดูซัพพลายเออร์"},
    {"code": "supplier.update",  "module": "supplier",  "action": "update",  "name_zh": "編輯供應商",      "name_en": "Edit Supplier",           "name_th": "แก้ไขซัพพลายเออร์"},
    {"code": "supplier.delete",  "module": "supplier",  "action": "delete",  "name_zh": "刪除供應商",      "name_en": "Delete Supplier",         "name_th": "ลบซัพพลายเออร์"},
    # 採購
    {"code": "purchase.create",  "module": "purchase",  "action": "create",  "name_zh": "新增採購單",      "name_en": "Create Purchase",         "name_th": "สร้างใบสั่งซื้อ"},
    {"code": "purchase.read",    "module": "purchase",  "action": "read",    "name_zh": "查看採購單",      "name_en": "View Purchase",           "name_th": "ดูใบสั่งซื้อ"},
    {"code": "purchase.update",  "module": "purchase",  "action": "update",  "name_zh": "編輯採購單",      "name_en": "Edit Purchase",           "name_th": "แก้ไขใบสั่งซื้อ"},
    {"code": "purchase.delete",  "module": "purchase",  "action": "delete",  "name_zh": "刪除採購單",      "name_en": "Delete Purchase",         "name_th": "ลบใบสั่งซื้อ"},
    # 批次
    {"code": "batch.create",     "module": "batch",     "action": "create",  "name_zh": "新增批次",        "name_en": "Create Batch",            "name_th": "สร้างล็อต"},
    {"code": "batch.read",       "module": "batch",     "action": "read",    "name_zh": "查看批次",        "name_en": "View Batch",              "name_th": "ดูล็อต"},
    {"code": "batch.update",     "module": "batch",     "action": "update",  "name_zh": "編輯批次",        "name_en": "Edit Batch",              "name_th": "แก้ไขล็อต"},
    {"code": "batch.delete",     "module": "batch",     "action": "delete",  "name_zh": "刪除批次",        "name_en": "Delete Batch",            "name_th": "ลบล็อต"},
    {"code": "batch.export",     "module": "batch",     "action": "export",  "name_zh": "匯出批次",        "name_en": "Export Batch",            "name_th": "ส่งออกล็อต"},
    # 加工
    {"code": "processing.create","module": "processing","action": "create",  "name_zh": "新增加工單",      "name_en": "Create Processing",       "name_th": "สร้างใบแปรรูป"},
    {"code": "processing.read",  "module": "processing","action": "read",    "name_zh": "查看加工單",      "name_en": "View Processing",         "name_th": "ดูใบแปรรูป"},
    {"code": "processing.update","module": "processing","action": "update",  "name_zh": "編輯加工單",      "name_en": "Edit Processing",         "name_th": "แก้ไขใบแปรรูป"},
    {"code": "processing.delete","module": "processing","action": "delete",  "name_zh": "刪除加工單",      "name_en": "Delete Processing",       "name_th": "ลบใบแปรรูป"},
    # OEM 工廠
    {"code": "oem_factory.create","module": "oem_factory","action": "create","name_zh": "新增代工廠",      "name_en": "Create OEM Factory",      "name_th": "สร้างโรงงาน OEM"},
    {"code": "oem_factory.read",  "module": "oem_factory","action": "read",  "name_zh": "查看代工廠",      "name_en": "View OEM Factory",        "name_th": "ดูโรงงาน OEM"},
    {"code": "oem_factory.update","module": "oem_factory","action": "update","name_zh": "編輯代工廠",      "name_en": "Edit OEM Factory",        "name_th": "แก้ไขโรงงาน OEM"},
    {"code": "oem_factory.delete","module": "oem_factory","action": "delete","name_zh": "刪除代工廠",      "name_en": "Delete OEM Factory",      "name_th": "ลบโรงงาน OEM"},
    # QC
    {"code": "qc.create",       "module": "qc",       "action": "create",  "name_zh": "新增 QC 記錄",    "name_en": "Create QC Record",        "name_th": "สร้างบันทึก QC"},
    {"code": "qc.read",         "module": "qc",       "action": "read",    "name_zh": "查看 QC 記錄",    "name_en": "View QC Record",          "name_th": "ดูบันทึก QC"},
    {"code": "qc.update",       "module": "qc",       "action": "update",  "name_zh": "編輯 QC 記錄",    "name_en": "Edit QC Record",          "name_th": "แก้ไขบันทึก QC"},
    {"code": "qc.delete",       "module": "qc",       "action": "delete",  "name_zh": "刪除 QC 記錄",    "name_en": "Delete QC Record",        "name_th": "ลบบันทึก QC"},
    # 出口
    {"code": "shipment.create",  "module": "shipment",  "action": "create",  "name_zh": "新增出口單",      "name_en": "Create Shipment",         "name_th": "สร้างใบส่งออก"},
    {"code": "shipment.read",    "module": "shipment",  "action": "read",    "name_zh": "查看出口單",      "name_en": "View Shipment",           "name_th": "ดูใบส่งออก"},
    {"code": "shipment.update",  "module": "shipment",  "action": "update",  "name_zh": "編輯出口單",      "name_en": "Edit Shipment",           "name_th": "แก้ไขใบส่งออก"},
    {"code": "shipment.delete",  "module": "shipment",  "action": "delete",  "name_zh": "刪除出口單",      "name_en": "Delete Shipment",         "name_th": "ลบใบส่งออก"},
    # 進口通關
    {"code": "import.create",    "module": "import",    "action": "create",  "name_zh": "新增進口記錄",    "name_en": "Create Import",           "name_th": "สร้างบันทึกนำเข้า"},
    {"code": "import.read",      "module": "import",    "action": "read",    "name_zh": "查看進口記錄",    "name_en": "View Import",             "name_th": "ดูบันทึกนำเข้า"},
    {"code": "import.update",    "module": "import",    "action": "update",  "name_zh": "編輯進口記錄",    "name_en": "Edit Import",             "name_th": "แก้ไขบันทึกนำเข้า"},
    {"code": "import.delete",    "module": "import",    "action": "delete",  "name_zh": "刪除進口記錄",    "name_en": "Delete Import",           "name_th": "ลบบันทึกนำเข้า"},
    # 倉庫
    {"code": "warehouse.create", "module": "warehouse", "action": "create",  "name_zh": "新增倉庫",        "name_en": "Create Warehouse",        "name_th": "สร้างคลังสินค้า"},
    {"code": "warehouse.read",   "module": "warehouse", "action": "read",    "name_zh": "查看倉庫",        "name_en": "View Warehouse",          "name_th": "ดูคลังสินค้า"},
    {"code": "warehouse.update", "module": "warehouse", "action": "update",  "name_zh": "編輯倉庫",        "name_en": "Edit Warehouse",          "name_th": "แก้ไขคลังสินค้า"},
    {"code": "warehouse.delete", "module": "warehouse", "action": "delete",  "name_zh": "刪除倉庫",        "name_en": "Delete Warehouse",        "name_th": "ลบคลังสินค้า"},
    # 庫存
    {"code": "stock.create",     "module": "stock",     "action": "create",  "name_zh": "新增庫存",        "name_en": "Create Stock",            "name_th": "สร้างสต็อก"},
    {"code": "stock.read",       "module": "stock",     "action": "read",    "name_zh": "查看庫存",        "name_en": "View Stock",              "name_th": "ดูสต็อก"},
    {"code": "stock.update",     "module": "stock",     "action": "update",  "name_zh": "編輯庫存",        "name_en": "Edit Stock",              "name_th": "แก้ไขสต็อก"},
    {"code": "stock.delete",     "module": "stock",     "action": "delete",  "name_zh": "刪除庫存",        "name_en": "Delete Stock",            "name_th": "ลบสต็อก"},
    # 日常銷售
    {"code": "daily_sale.create","module": "daily_sale","action": "create",  "name_zh": "新增銷售單",      "name_en": "Create Daily Sale",       "name_th": "สร้างรายการขาย"},
    {"code": "daily_sale.read",  "module": "daily_sale","action": "read",    "name_zh": "查看銷售單",      "name_en": "View Daily Sale",         "name_th": "ดูรายการขาย"},
    {"code": "daily_sale.update","module": "daily_sale","action": "update",  "name_zh": "編輯銷售單",      "name_en": "Edit Daily Sale",         "name_th": "แก้ไขรายการขาย"},
    {"code": "daily_sale.delete","module": "daily_sale","action": "delete",  "name_zh": "刪除銷售單",      "name_en": "Delete Daily Sale",       "name_th": "ลบรายการขาย"},
    # 成本
    {"code": "cost_sheet.create","module": "cost_sheet","action": "create",  "name_zh": "新增成本項目",    "name_en": "Create Cost Sheet",       "name_th": "สร้างรายการต้นทุน"},
    {"code": "cost_sheet.read",  "module": "cost_sheet","action": "read",    "name_zh": "查看成本項目",    "name_en": "View Cost Sheet",         "name_th": "ดูรายการต้นทุน"},
    {"code": "cost_sheet.update","module": "cost_sheet","action": "update",  "name_zh": "編輯成本項目",    "name_en": "Edit Cost Sheet",         "name_th": "แก้ไขรายการต้นทุน"},
    {"code": "cost_sheet.delete","module": "cost_sheet","action": "delete",  "name_zh": "刪除成本項目",    "name_en": "Delete Cost Sheet",       "name_th": "ลบรายการต้นทุน"},
    # 利潤
    {"code": "profit.read",      "module": "profit",    "action": "read",    "name_zh": "查看利潤分析",    "name_en": "View Profit Analysis",    "name_th": "ดูการวิเคราะห์กำไร"},
    {"code": "profit.export",    "module": "profit",    "action": "export",  "name_zh": "匯出利潤報表",    "name_en": "Export Profit Report",    "name_th": "ส่งออกรายงานกำไร"},
    # 客戶
    {"code": "customer.create",  "module": "customer",  "action": "create",  "name_zh": "新增客戶",        "name_en": "Create Customer",         "name_th": "สร้างลูกค้า"},
    {"code": "customer.read",    "module": "customer",  "action": "read",    "name_zh": "查看客戶",        "name_en": "View Customer",           "name_th": "ดูลูกค้า"},
    {"code": "customer.update",  "module": "customer",  "action": "update",  "name_zh": "編輯客戶",        "name_en": "Edit Customer",           "name_th": "แก้ไขลูกค้า"},
    {"code": "customer.delete",  "module": "customer",  "action": "delete",  "name_zh": "刪除客戶",        "name_en": "Delete Customer",         "name_th": "ลบลูกค้า"},
    # 收付款
    {"code": "payment.create",   "module": "payment",   "action": "create",  "name_zh": "新增付款記錄",    "name_en": "Create Payment",          "name_th": "สร้างบันทึกการชำระเงิน"},
    {"code": "payment.read",     "module": "payment",   "action": "read",    "name_zh": "查看付款記錄",    "name_en": "View Payment",            "name_th": "ดูบันทึกการชำระเงิน"},
    {"code": "payment.update",   "module": "payment",   "action": "update",  "name_zh": "編輯付款記錄",    "name_en": "Edit Payment",            "name_th": "แก้ไขบันทึกการชำระเงิน"},
    {"code": "payment.delete",   "module": "payment",   "action": "delete",  "name_zh": "刪除付款記錄",    "name_en": "Delete Payment",          "name_th": "ลบบันทึกการชำระเงิน"},
    # 使用者
    {"code": "user.create",      "module": "user",      "action": "create",  "name_zh": "新增使用者",      "name_en": "Create User",             "name_th": "สร้างผู้ใช้"},
    {"code": "user.read",        "module": "user",      "action": "read",    "name_zh": "查看使用者",      "name_en": "View User",               "name_th": "ดูผู้ใช้"},
    {"code": "user.update",      "module": "user",      "action": "update",  "name_zh": "編輯使用者",      "name_en": "Edit User",               "name_th": "แก้ไขผู้ใช้"},
    {"code": "user.delete",      "module": "user",      "action": "delete",  "name_zh": "刪除使用者",      "name_en": "Delete User",             "name_th": "ลบผู้ใช้"},
    # 系統設定
    {"code": "system.read",      "module": "system",    "action": "read",    "name_zh": "查看系統設定",    "name_en": "View System Settings",    "name_th": "ดูการตั้งค่าระบบ"},
    {"code": "system.update",    "module": "system",    "action": "update",  "name_zh": "編輯系統設定",    "name_en": "Edit System Settings",    "name_th": "แก้ไขการตั้งค่าระบบ"},
    # 附件
    {"code": "attachment.create","module": "attachment","action": "create",  "name_zh": "上傳附件",        "name_en": "Upload Attachment",       "name_th": "อัปโหลดไฟล์แนบ"},
    {"code": "attachment.read",  "module": "attachment","action": "read",    "name_zh": "查看附件",        "name_en": "View Attachment",         "name_th": "ดูไฟล์แนบ"},
    {"code": "attachment.delete","module": "attachment","action": "delete",  "name_zh": "刪除附件",        "name_en": "Delete Attachment",       "name_th": "ลบไฟล์แนบ"},
    # 通知
    {"code": "notification.read",  "module": "notification","action": "read",  "name_zh": "查看通知",      "name_en": "View Notification",       "name_th": "ดูการแจ้งเตือน"},
    {"code": "notification.update","module": "notification","action": "update","name_zh": "管理通知",      "name_en": "Manage Notification",     "name_th": "จัดการการแจ้งเตือน"},
]

# ═══════════════════════════════════════════════════════════════════
# 角色定義
# ═══════════════════════════════════════════════════════════════════
ROLES = [
    {
        "code": "admin",
        "name": "系統管理員", "name_zh": "系統管理員",
        "name_en": "System Admin", "name_th": "ผู้ดูแลระบบ",
        "is_system": True,
        "all_permissions": True,
    },
    {
        "code": "th_manager",
        "name": "泰方管理員", "name_zh": "泰方管理員",
        "name_en": "TH Operations", "name_th": "ผู้จัดการฝ่ายไทย",
        "is_system": True,
        "permissions": [
            "supplier.create", "supplier.read", "supplier.update", "supplier.delete",
            "purchase.create", "purchase.read", "purchase.update", "purchase.delete",
            "batch.read",
            "processing.create", "processing.read", "processing.update", "processing.delete",
            "oem_factory.create", "oem_factory.read", "oem_factory.update", "oem_factory.delete",
            "qc.create", "qc.read", "qc.update", "qc.delete",
            "shipment.create", "shipment.read", "shipment.update", "shipment.delete",
            "cost_sheet.read", "stock.read",
            "attachment.create", "attachment.read",
            "notification.read",
        ],
    },
    {
        "code": "tw_manager",
        "name": "台方管理員", "name_zh": "台方管理員",
        "name_en": "TW Operations", "name_th": "ผู้จัดการฝ่ายไต้หวัน",
        "is_system": True,
        "permissions": [
            "import.create", "import.read", "import.update", "import.delete",
            "warehouse.create", "warehouse.read", "warehouse.update", "warehouse.delete",
            "stock.create", "stock.read", "stock.update", "stock.delete",
            "daily_sale.create", "daily_sale.read", "daily_sale.update", "daily_sale.delete",
            "cost_sheet.create", "cost_sheet.read", "cost_sheet.update", "cost_sheet.delete",
            "profit.read", "profit.export",
            "customer.create", "customer.read", "customer.update", "customer.delete",
            "payment.create", "payment.read", "payment.update", "payment.delete",
            "batch.read", "batch.export",
            "shipment.read", "supplier.read",
            "attachment.create", "attachment.read",
            "notification.read",
        ],
    },
    {
        "code": "market_sales",
        "name": "市場銷售員", "name_zh": "市場銷售員",
        "name_en": "Market Sales", "name_th": "พนักงานขายตลาด",
        "is_system": True,
        "permissions": [
            "daily_sale.create", "daily_sale.read", "daily_sale.update", "daily_sale.delete",
            "stock.read",
            "batch.read",
            "customer.read",
            "payment.create", "payment.read",
            "attachment.create", "attachment.read",
            "notification.read",
        ],
    },
    {
        "code": "viewer",
        "name": "唯讀檢視者", "name_zh": "唯讀檢視者",
        "name_en": "Read-Only Viewer", "name_th": "ผู้ชมอ่านอย่างเดียว",
        "is_system": True,
        "permissions": [p["code"] for p in PERMISSIONS if p["action"] == "read"],
    },
]

# ═══════════════════════════════════════════════════════════════════
# 品項 Seed Data
# ═══════════════════════════════════════════════════════════════════
PRODUCT_TYPES = [
    {
        "code": "baby_corn",
        "batch_prefix": "BC",
        "name_zh": "玉米筍",
        "name_en": "Baby Corn",
        "name_th": "ข้าวโพดอ่อน",
        "quality_schema": [
            {"field": "ear_length_cm",   "label_zh": "穗長(cm)",    "type": "numeric", "min": 3,  "max": 15},
            {"field": "diameter_mm",     "label_zh": "直徑(mm)",    "type": "numeric", "min": 5,  "max": 25},
            {"field": "husk_integrity",  "label_zh": "外葉完整度",  "type": "select",  "options": ["intact", "partial", "damaged"]},
            {"field": "color_grade",     "label_zh": "色澤等級",    "type": "select",  "options": ["excellent", "good", "fair", "poor"]},
            {"field": "insect_damage",   "label_zh": "蟲害",        "type": "boolean"},
            {"field": "freshness_score", "label_zh": "新鮮度評分",  "type": "numeric", "min": 1,  "max": 10},
        ],
        "size_grades": [
            {"grade": "S", "label_zh": "小", "min_cm": 4,  "max_cm": 6},
            {"grade": "M", "label_zh": "中", "min_cm": 6,  "max_cm": 9},
            {"grade": "L", "label_zh": "大", "min_cm": 9,  "max_cm": 12},
        ],
        "processing_steps": ["剝葉", "清洗", "分級", "秤重", "包裝", "冷藏"],
        "storage_req": {"temp_min": 2, "temp_max": 5, "humidity_pct": 90},
        "shelf_life_days": 14,
    },
    {
        "code": "durian",
        "batch_prefix": "DR",
        "name_zh": "榴槤",
        "name_en": "Durian",
        "name_th": "ทุเรียน",
        "quality_schema": [
            {"field": "flesh_color",     "label_zh": "果肉色澤",    "type": "select",  "options": ["golden", "yellow", "pale", "brown"]},
            {"field": "sweetness_brix",  "label_zh": "甜度(Brix)",  "type": "numeric", "min": 20, "max": 40},
            {"field": "aroma_grade",     "label_zh": "香氣等級",    "type": "select",  "options": ["strong", "medium", "mild", "off"]},
            {"field": "shell_crack",     "label_zh": "裂果程度",    "type": "select",  "options": ["none", "slight", "moderate", "severe"]},
            {"field": "flesh_texture",   "label_zh": "果肉質地",    "type": "select",  "options": ["creamy", "firm", "dry", "watery"]},
            {"field": "pest_damage",     "label_zh": "蟲害",        "type": "boolean"},
            {"field": "freshness_score", "label_zh": "新鮮度評分",  "type": "numeric", "min": 1,  "max": 10},
        ],
        "size_grades": [
            {"grade": "S",  "label_zh": "小", "min_kg": 1.0, "max_kg": 2.0},
            {"grade": "M",  "label_zh": "中", "min_kg": 2.0, "max_kg": 3.5},
            {"grade": "L",  "label_zh": "大", "min_kg": 3.5, "max_kg": 5.0},
            {"grade": "XL", "label_zh": "特大", "min_kg": 5.0, "max_kg": 8.0},
        ],
        "processing_steps": ["選果", "清潔", "分級", "秤重", "包裝", "急凍"],
        "storage_req": {"temp_min": -25, "temp_max": -18, "humidity_pct": 85},
        "shelf_life_days": 5,
    },
]

# ═══════════════════════════════════════════════════════════════════
# 系統設定 Seed Data
# ═══════════════════════════════════════════════════════════════════
SYSTEM_SETTINGS = [
    {"key": "default_exchange_rate",   "value": {"THB_TWD": 0.92},                "description": "預設匯率（THB→TWD）"},
    {"key": "stock_age_warning_days",  "value": 7,                                 "description": "庫存庫齡警告天數"},
    {"key": "stock_age_critical_days", "value": 10,                                "description": "庫存庫齡危急天數"},
    {"key": "supported_locales",       "value": ["zh-TW", "en", "th"],             "description": "支援的語系列表"},
    {"key": "default_locale",          "value": "zh-TW",                           "description": "預設語系"},
    {
        "key": "seller_company",
        "value": {
            "name": "BabyCorn Export Co., Ltd.",
            "address": "123 Moo 5, Nakhon Ratchasima, Thailand 30000",
            "tax_id": "",
            "contact": "",
            "phone": "",
            "email": ""
        },
        "description": "泰方賣方公司資訊（發票用）"
    },
    {
        "key": "buyer_company",
        "value": {
            "name": "玉米筍國際貿易有限公司",
            "address": "台灣宜蘭縣五結鄉利成路二段88號",
            "tax_id": "",
            "contact": "",
            "phone": "",
            "email": ""
        },
        "description": "台方買方公司資訊（發票用）"
    },
]


def init_db():
    """建立所有資料庫表格"""
    Base.metadata.create_all(bind=engine)
    print("✅ 資料庫表格建立完成")


def seed_data():
    """植入初始資料"""
    db: Session = SessionLocal()

    try:
        # ─── 建立所有權限項目 ──────────────────────────
        print("📝 建立權限項目...")
        perm_map = {}  # code -> Permission
        for p in PERMISSIONS:
            existing = db.query(Permission).filter(
                Permission.module == p["module"],
                Permission.action == p["action"],
            ).first()
            if existing:
                # 補齊 code 和三語欄位（若尚未設定）
                if not existing.code:
                    existing.code = p["code"]
                if not existing.name_zh:
                    existing.name_zh = p["name_zh"]
                if not existing.name_en:
                    existing.name_en = p["name_en"]
                if not existing.name_th:
                    existing.name_th = p["name_th"]
                perm_map[p["code"]] = existing
            else:
                perm = Permission(
                    code=p["code"], module=p["module"], action=p["action"],
                    name_zh=p["name_zh"], name_en=p["name_en"], name_th=p["name_th"],
                )
                db.add(perm)
                db.flush()
                perm_map[p["code"]] = perm

        db.commit()
        print(f"   ✓ 共 {len(perm_map)} 個權限項目")

        # ─── 建立預設角色 ──────────────────────────────
        print("👥 建立預設角色...")
        for role_data in ROLES:
            existing_role = db.query(Role).filter(Role.code == role_data["code"]).first()
            if not existing_role:
                # 也嘗試用 name 找（相容舊資料）
                existing_role = db.query(Role).filter(Role.name == role_data["name"]).first()

            if existing_role:
                # 補齊新欄位
                if not existing_role.code:
                    existing_role.code = role_data["code"]
                if not existing_role.name_zh:
                    existing_role.name_zh = role_data["name_zh"]
                if not existing_role.name_en:
                    existing_role.name_en = role_data["name_en"]
                if not existing_role.name_th:
                    existing_role.name_th = role_data["name_th"]
                db.commit()
                print(f"   - 角色已存在，已補齊三語：{role_data['code']}")
                continue

            role = Role(
                code=role_data["code"],
                name=role_data["name"],
                name_zh=role_data["name_zh"],
                name_en=role_data["name_en"],
                name_th=role_data["name_th"],
                description=role_data.get("description"),
                is_system=role_data.get("is_system", False),
            )
            db.add(role)
            db.flush()

            # 分配權限
            if role_data.get("all_permissions"):
                for perm in perm_map.values():
                    db.add(RolePermission(role_id=role.id, permission_id=perm.id))
            elif role_data.get("permissions"):
                for perm_code in role_data["permissions"]:
                    perm = perm_map.get(perm_code)
                    if perm:
                        db.add(RolePermission(role_id=role.id, permission_id=perm.id))

            db.commit()
            print(f"   ✓ 建立角色：{role_data['code']}")

        # ─── 建立預設管理員帳號 ────────────────────────
        print("👤 建立預設管理員帳號...")
        admin_role = db.query(Role).filter(Role.code == "admin").first()
        existing_admin = db.query(User).filter(User.email == "admin@babycorn.com").first()

        if not existing_admin:
            admin = User(
                email="admin@babycorn.com",
                password_hash=hash_password("admin1234"),
                full_name="系統管理員",
                role_id=admin_role.id if admin_role else None,
                preferred_language="zh-TW",
            )
            db.add(admin)
            db.commit()
            print("   ✓ 管理員帳號建立完成")
            print("   📧 Email：admin@babycorn.com")
            print("   🔑 密碼：admin1234（請登入後立即修改）")
        else:
            print("   - 管理員帳號已存在，跳過")

        # ─── 品項 Seed Data ────────────────────────────
        print("🌽 建立品項資料...")
        for pt in PRODUCT_TYPES:
            conn = db.connection()
            conn.execute(text(
                "INSERT INTO product_types (id, code, batch_prefix, name_zh, name_en, name_th, "
                "quality_schema, size_grades, processing_steps, storage_req, shelf_life_days, is_active) "
                "VALUES (gen_random_uuid(), :code, :batch_prefix, :name_zh, :name_en, :name_th, "
                ":quality_schema, :size_grades, :processing_steps, :storage_req, :shelf_life_days, true) "
                "ON CONFLICT (code) DO NOTHING"
            ), {
                "code": pt["code"],
                "batch_prefix": pt["batch_prefix"],
                "name_zh": pt["name_zh"],
                "name_en": pt["name_en"],
                "name_th": pt["name_th"],
                "quality_schema": json.dumps(pt["quality_schema"]),
                "size_grades": json.dumps(pt["size_grades"]),
                "processing_steps": json.dumps(pt["processing_steps"]),
                "storage_req": json.dumps(pt["storage_req"]),
                "shelf_life_days": pt["shelf_life_days"],
            })
            db.commit()
            print(f"   ✓ 品項：{pt['code']}")

        # ─── 系統設定 Seed Data ────────────────────────
        print("⚙️  建立系統設定...")
        for s in SYSTEM_SETTINGS:
            conn = db.connection()
            conn.execute(text(
                "INSERT INTO system_settings (id, key, value, description) "
                "VALUES (gen_random_uuid(), :key, :value, :desc) "
                "ON CONFLICT (key) DO NOTHING"
            ), {
                "key": s["key"],
                "value": json.dumps(s["value"]),
                "desc": s["description"],
            })
            db.commit()
            print(f"   ✓ 設定：{s['key']}")

        print("\n🎉 初始資料建立完成！")

    except Exception as e:
        db.rollback()
        print(f"❌ 錯誤：{e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    init_db()
    seed_data()
