# 玉米筍 ERP — 完整開發待辦清單（Bloomberg Terminal 版）

> 目標：打造蔬果界的 Bloomberg Terminal
> 全球客戶、全球通路、即時市場情報、數據驅動決策
> 最後更新：2026-03-30

---

## 現有系統規模

- 67 張資料表、147 個 API、24 個前端頁面
- 11 角色、101 權限、3 語系

## 目標系統規模

- **107+ 張資料表**、**300+ API**、**60+ 前端頁面**
- 13 大功能模組 + Bloomberg 情報平台

---

# 區塊 A｜安全加固（8 段）

## A-01｜加密升級
- 檔案：`backend/utils/encryption.py`
- 內容：Fernet → AES-256-GCM
- 格式：`base64(iv):base64(tag):base64(ciphertext)`
- 環境變數：`ENCRYPTION_KEY`（64 字元 hex = 32 bytes）
- 向下相容：解密失敗回傳原值（舊明文不會炸）

## A-02｜稽核日誌強化
- 檔案：`backend/utils/audit.py`
- 加 retry 1 次（500ms 間隔）
- 加欄位：ip_address、user_agent、entity_label
- 最終失敗用 structlog 記錄，不 raise exception

## A-03｜Rate Limiter 升級
- 檔案：`backend/middleware/`
- 一般 API：60 req/min per IP
- 登入 API：10 次/15 分鐘 per email
- IP 偵測：cf-connecting-ip → x-forwarded-for → x-real-ip
- 超限回傳 429 + Retry-After header

## A-04｜序號跨日重置
- 現有 advisory lock 補跨日歸 1
- 超過 9999 自動擴展到 5 位數
- stable_hash 計算 lock_id

## A-05｜Structured Logger
- 新建 `backend/utils/logger.py`
- 用 structlog
- Production：JSON 格式
- Development：ANSI 彩色人類可讀
- 欄位：level, module, message, request_id, error, timestamp

## A-06｜Token Rotation
- User model 加 `token_version INTEGER DEFAULT 0`（Alembic migration）
- JWT payload 加：issued_at, access_expiry, absolute_expiry, token_version
- 剩 < 5 分鐘 → 自動延長 15 分鐘
- 超過 8 小時 absolute → 強制登出
- 撤銷所有 session：token_version + 1

## A-07｜統一錯誤處理
- UniqueViolation → 409
- NoResultFound → 404
- ForeignKeyViolation → 409
- 其他 → 500
- Production 隱藏 stack trace

## A-08｜Nginx + Docker 加固
- nginx.conf 加 CSP、HSTS、X-Frame-Options、X-Content-Type-Options
- limit_req_zone 設定
- docker-compose.yml 加 deploy.resources.limits（backend 1G/1cpu、frontend 512M/0.5cpu、db 2G/2cpu）

---

# 區塊 B｜全域欄位補齊（6 段）

> 現有 67 張表大量缺少 updated_by、deleted_at、currency、exchange_rate 等共用欄位

## B-01｜全表補 updated_by
所有 model 加 `updated_by UUID FK → users.id NULLABLE`：
- batch, purchase_order, supplier, shipment, inventory_lot, sales_order
- cost_event, finance (AR/AP), driver, delivery_order, outbound_order
- processing_order, procurement_plan, qc_inspection, oem_factory, product_type

## B-02｜全表補 deleted_at 軟刪除
以下 model 缺少 `deleted_at DateTime NULLABLE`：
- Batch, PurchaseOrder, Shipment, SalesOrder
- InventoryLot, Warehouse, WarehouseLocation
- Driver, DeliveryOrder, OutboundOrder
- ProcessingOrder, ProcurementPlan, QCInspection
- OEMFactory, ProductType, Notification

## B-03｜採購/銷售/出貨 補幣別+匯率
- PurchaseOrder 加：`currency VARCHAR(3) DEFAULT 'THB'`、`exchange_rate NUMERIC(8,4)`
- SalesOrder 加：`currency VARCHAR(3) DEFAULT 'TWD'`、`exchange_rate NUMERIC(8,4)`、`customer_po_number VARCHAR(100)`、`delivery_address TEXT`、`incoterm VARCHAR(10)`
- Shipment 加：`exchange_rate NUMERIC(8,4)`、`currency VARCHAR(3)`、`incoterm VARCHAR(10)`、`hs_code VARCHAR(20)`、`commercial_invoice_no VARCHAR(100)`、`voyage_no VARCHAR(50)`
- AccountPayable 加：`exchange_rate NUMERIC(8,4)`

## B-04｜供應商 補全球化欄位
- Supplier 加：`country_code VARCHAR(3) DEFAULT 'TH'`、`tax_id VARCHAR(50)`、`vat_no VARCHAR(50)`、`payment_currency VARCHAR(3) DEFAULT 'THB'`、`bank_country VARCHAR(3)`、`bank_swift_code VARCHAR(20)`、`email VARCHAR(255)`、`website VARCHAR(500)`
- Supplier 加農場欄位：`total_area_rai NUMERIC(10,2)`、`cultivated_area_rai NUMERIC(10,2)`、`organic_certified BOOLEAN`、`organic_cert_no VARCHAR(50)`、`organic_cert_expiry DATE`、`annual_capacity_kg NUMERIC(12,2)`

## B-05｜品質/工廠 補認證欄位
- QCInspection 加：`certification_standard VARCHAR(50)`（ISO22000/HACCP/BRC/IFS/ORGANIC）、`heavy_metal_test JSON`、`microbial_test JSON`
- OEMFactory 加：`country_code VARCHAR(3) DEFAULT 'TH'`、`haccp_cert_no VARCHAR(50)`、`haccp_cert_expiry DATE`、`iso22000_cert_no VARCHAR(50)`、`capacity_per_day_kg NUMERIC(10,2)`、`lead_time_days INTEGER`
- ProductType 加：`hs_code VARCHAR(20)`、`base_uom VARCHAR(10) DEFAULT 'kg'`、`min_order_qty NUMERIC(10,2)`、`certifications_required JSON`

## B-06｜庫存 補冷鏈欄位
- Warehouse 加：`storage_type VARCHAR(20)`（frozen/chilled/ambient）、`temperature_min NUMERIC(5,2)`、`temperature_max NUMERIC(5,2)`、`humidity_min NUMERIC(5,2)`、`humidity_max NUMERIC(5,2)`、`total_capacity_pallets INTEGER`、`country_code VARCHAR(3)`
- InventoryLot 加：`actual_temp_on_arrival NUMERIC(5,2)`、`humidity_on_arrival NUMERIC(5,2)`、`expiry_date DATE`、`quality_status VARCHAR(20) DEFAULT 'approved'`（approved/on_hold/rejected/quarantine）

---

# 區塊 C｜人事與權限（7 段）

## C-01｜EmployeeProfile 人事檔案
```
id, user_id (FK UNIQUE), employee_code, national_id (加密), birthday, gender,
marital_status, emergency_contact_name, emergency_contact_phone,
bank_name, bank_account (加密), bank_branch,
labor_insurance_date, health_insurance_date,
education, certifications,
work_location (thailand_factory/taiwan_hq/overseas),
country_code, hire_date, employment_type (full_time/part_time/contract)
```

## C-02｜Department 部門
```
id, department_code, department_name, department_name_en, department_name_th,
parent_department_id (FK self), manager_user_id (FK),
cost_center_code, country_code, is_active
```

## C-03｜Appointment 職務異動
```
id, user_id (FK), effective_date, type (hire/promote/transfer/resign/terminate),
from_role, to_role, from_department, to_department,
from_title, to_title, reason, approved_by (FK), approved_at,
created_at
```

## C-04｜Attendance 出勤
```
id, user_id (FK), date, clock_in, clock_out,
status (present/absent/late/leave/holiday),
leave_type (annual/sick/personal/official/bereavement/marriage),
overtime_hours NUMERIC(4,1),
notes
@@unique([user_id, date])
```

## C-05｜PayrollRecord 薪資
```
id, user_id (FK), period_year, period_month,
base_salary, currency (THB/TWD),
allowances, overtime_pay, bonus,
deductions, labor_insurance, health_insurance, tax,
net_pay,
status (draft/confirmed/paid), paid_at
@@unique([user_id, period_year, period_month])
```

## C-06｜員工等級分類
User model 加：
- `employee_level VARCHAR(20)`（junior/mid/senior/lead/manager/director/vp/c_level）
- `department_id UUID FK`
- `reports_to_user_id UUID FK`（直屬主管）
- `job_title VARCHAR(100)`
- `commission_rate NUMERIC(5,2)`（佣金比例）

## C-07｜權限擴充
- 更新 init_data.py，新增以下模組的權限：
  - hr（人事）、petty_cash（零用金）、contract（合約）、announcement（公告）
  - calendar（行事曆）、meeting（會議）、quotation（報價）、visit（拜訪）
  - sample（樣品）、opportunity（商機）、budget（預算）
  - market_intel（市場情報）、trade_doc（貿易文件）、compliance（法規合規）
- 每個模組：create/read/update/delete/approve/export = 6 權限
- 預估新增 14 模組 × 6 = 84 權限 → 總計 185 權限

---

# 區塊 D｜CRM 基礎（5 段）

## D-01｜Customer Model 擴充
新增 20+ 欄位（Alembic migration）：
```python
# CRM 追蹤
dev_status = Column(String(30), default="potential")
# potential→contacted→visited→negotiating→trial→closed→stable_repurchase→dormant→churned
grade = Column(String(1))  # A/B/C/D
health_score = Column(Integer, default=100)
health_level = Column(String(10), default="GREEN")
health_updated_at = Column(DateTime)
last_order_date = Column(DateTime)
last_contact_date = Column(DateTime)
next_follow_up_date = Column(DateTime)
is_follow_up = Column(Boolean, default=True)
avg_order_interval = Column(Integer)  # 天
lifetime_value = Column(Numeric(14, 2))
is_key_account = Column(Boolean, default=False)
visit_frequency_days = Column(Integer)
churn_reason = Column(String(200))
churn_date = Column(DateTime)
churn_note = Column(Text)
predicted_next_order = Column(DateTime)
prediction_confidence = Column(String(10))
order_trend = Column(String(10))
# 全球化
country_code = Column(String(3), default="TW")
tax_id = Column(String(50))
default_currency = Column(String(3), default="TWD")
default_incoterm = Column(String(10))
default_payment_method = Column(String(30))
```

## D-02｜CustomerContact 客戶聯絡人（新表）
```
id, customer_id (FK), contact_name, contact_title, department,
phone, mobile, email, line_id, wechat_id,
is_primary, is_decision_maker, preferred_language,
notes, is_active
```

## D-03｜CustomerAddress 客戶多地址（新表）
```
id, customer_id (FK), address_type (billing/shipping/warehouse),
address_line_1, address_line_2, city, state, postal_code,
country_code, is_default, special_instructions
```

## D-04｜Scope 集中管理
新建 `backend/utils/scope.py`：
- `apply_customer_scope(query, model, user)`
- `apply_order_scope(query, model, user)`
- `apply_shipment_scope(query, model, user)`
- FULL_ACCESS：super_admin, gm, finance, admin
- TEAM_ACCESS：sales_manager
- OWN_DATA：sales, cs
- 套到所有 list API router

## D-05｜多通路通知
新建 `backend/services/notification.py`：
- `notify(db, user_ids, title, message, link_url, category, priority)`
- `notify_managers(db, ...)`
- `notify_by_role(db, roles, ...)`
- 支援：in-app（寫 Notification table）+ LINE Notify + Email SMTP
- 環境變數：LINE_NOTIFY_TOKEN、SMTP_HOST/PORT/USER/PASS

---

# 區塊 E｜CRM 進階（8 段）

## E-01｜客戶健康分數
新建 `services/health_score.py`
- 5 維度：訂單新近度 30分 + 逾期 AR 25分 + 互動頻率 20分 + 客訴 15分 + 停供 10分
- 等級：80-100 GREEN / 60-79 YELLOW / 40-59 ORANGE / 0-39 RED
- API：`GET /customers/{id}/health-score`、`POST /customers/health-score-recalc`
- APScheduler 每天 02:00 批次重算

## E-02｜流失預警
新建 `services/churn_detection.py`
- 因素：下單新近度 35分 + 量降趨勢 30分 + 下單頻率 15分 + 互動斷層 15分 + 逾期跟進 5分
- 等級：≥60 CRITICAL / ≥40 HIGH / ≥20 MEDIUM / <20 LOW
- API：`GET /crm/churn-alerts`

## E-03｜訂單預測
新建 `services/order_prediction.py`
- 取最近 20 筆訂單計算平均間隔
- 趨勢偵測（GROWING/DECLINING/STABLE）
- 信心度（≥6筆 HIGH / ≥3筆 MEDIUM / <3筆 LOW）
- API：`POST /customers/predict-next-order`、`GET /customers/reorder-cycle`

## E-04｜KPI 自動連動
新建 SalesTarget table：
```
id, user_id (FK), target_month (Date),
revenue_target (Numeric 14,2), order_target (Int), visit_target (Int),
new_customer_target (Int),
revenue_actual, order_actual, visit_actual, new_customer_actual,
achievement_rate (Numeric 5,2),
@@unique([user_id, target_month])
```
新建 `services/kpi_check.py`：
- 成交後自動觸發 checkKpiMilestone(userId)
- 達 50/80/100% 推播通知（業務本人 + 主管）

## E-05｜業務日報
新建 SalesDailyReport table：
```
id, sales_rep_id (FK), report_date (Date),
visit_count, call_count, order_count, order_amount,
new_customer_count, quote_count,
highlights, obstacles, tomorrow_plan, needs_help,
status (draft/submitted),
manager_comment, reviewed_by (FK), reviewed_at,
@@unique([sales_rep_id, report_date])
```

## E-06｜拜訪頻率 + 智慧告警
- `GET /customers/visit-schedule`（A 級 14 天/B 級 30 天/C 級 60 天）
- `GET /crm/alerts`：7 項告警統一回傳
  1. 7天以上未聯繫
  2. 今天到期跟進
  3. 逾期跟進
  4. 超 30 天報價未成交
  5. 接近回購日
  6. 今天排定活動
  7. 待回饋樣品

## E-07｜主管儀表板
- `GET /crm/dashboard/manager`
- 今日指標：新客戶、拜訪、成交、收款、待辦
- Pipeline 漏斗：各 dev_status 客戶數
- 業務排名（依拜訪/成交/收款排序）
- 權限：sales_manager / gm / super_admin

## E-08｜客戶開發階段 + 漏斗
- `PUT /customers/{id}/dev-status`（狀態轉換 + 記錄時間）
- `GET /customers/funnel`（漏斗分析：各階段客戶數 + 轉化率）

---

# 區塊 F｜銷售業務流程（7 段）

## F-01｜SalesOpportunity 銷售機會（新表）
```
id, opportunity_name, customer_id (FK), source (trade_show/referral/website/cold_call/buyer_directory),
stage (lead→qualified→proposal→negotiation→won/lost),
probability_pct (0-100), expected_amount, expected_currency,
expected_close_date, actual_close_date,
product_interest, competitor_info, loss_reason,
assigned_to (FK), created_by, created_at, updated_at
```

## F-02｜FollowUpLog 統一追蹤（新表）
```
id, customer_id (FK), created_by (FK), log_date,
log_type (call/line/email/meeting/first_visit/second_visit/delivery/expo/other),
method (phone/line/email/onsite/video),
content (必填), result,
customer_reaction (positive/neutral/negative/no_response),
next_follow_up_date, next_action,
has_sample (Boolean), has_quote (Boolean), has_order (Boolean),
opportunity_id (FK), is_follow_up (Boolean default true)
```

## F-03｜VisitRecord 拜訪紀錄（新表）
```
id, customer_id (FK), visited_by (FK), visit_date,
visit_method (onsite/phone/video/other),
purpose (first_visit/follow_up/service/training/signing),
participants, content, customer_needs,
competitor_info, result, next_action,
next_visit_date, follow_up_status (pending/done/overdue),
photos JSON
```

## F-04｜SalesSchedule 業務行程（新表）
```
id, customer_id (FK), sales_rep_id (FK),
schedule_date, start_time, end_time,
location, schedule_type (first_visit/second_visit/payment_collect/delivery/expo/other),
pre_reminder, post_result,
is_completed (Boolean default false)
```

## F-05｜SampleRecord 樣品管理（新表）
```
id, customer_id (FK), sent_by (FK), sent_date,
items (品項描述), quantity, purpose (trial/comparison/education/negotiation),
tracking_no, recipient,
has_feedback (Boolean), follow_up_date, follow_up_result, outcome,
sample_cost, shipping_cost, total_cost, cost_currency,
is_trial_order (Boolean)
```

## F-06｜Quotation 報價管理（新表）
```
id, quotation_no (unique), customer_id (FK), contact_id (FK),
quotation_date, valid_until,
currency_code, incoterm, payment_terms_days,
origin_port, destination_port,
subtotal, freight_estimate, insurance_estimate, tax_amount, total_amount,
status (draft/sent/negotiating/accepted/rejected/expired/converted),
version (Int default 1), previous_version_id (FK self),
requires_approval (Boolean), approval_status,
sales_rep_id (FK), notes, created_by, created_at, updated_at
```

## F-07｜QuotationItem + QuotationApproval
QuotationItem：
```
id, quotation_id (FK), line_number, product_id (FK),
product_name_snap, description,
qty, uom, unit_price, discount_pct, subtotal,
cost_snap, gross_margin, gross_margin_rate
```
QuotationApproval：
```
id, quotation_id (FK), approval_level (1=主管 2=GM),
approver_role, trigger_reason,
approver_id (FK), status (pending/approved/rejected),
comment, decided_at
```

---

# 區塊 G｜國際貿易文件（5 段）

## G-01｜TradeDocument 貿易文件總表（新表）
```
id, document_type (commercial_invoice/packing_list/bill_of_lading/
  certificate_of_origin/phytosanitary_cert/health_cert/insurance_policy/
  fumigation_cert/weight_cert/inspection_cert),
document_number, shipment_id (FK), sales_order_id (FK), customer_id (FK),
issue_date, expiry_date, issuing_authority, issuing_country,
status (draft/issued/submitted/approved/rejected),
file_url, original_copies_count, copy_copies_count,
notes, created_by, created_at
```

## G-02｜LetterOfCredit 信用狀（新表）
```
id, lc_number, customer_id (FK), sales_order_id (FK),
issuing_bank, issuing_bank_swift, advising_bank, advising_bank_swift,
lc_type (irrevocable/confirmed/transferable/standby),
lc_amount, lc_currency, tolerance_pct,
issue_date, expiry_date, latest_shipment_date,
presentation_days,
required_documents JSON, special_conditions,
status (received/amended/documents_presented/discrepant/paid/expired),
amendment_count, discrepancy_details,
payment_date, payment_amount
```

## G-03｜CustomsDeclaration 報關單（新表）
```
id, declaration_number, declaration_type (export/import),
shipment_id (FK), customs_broker_id (FK supplier),
declaration_date, country_code,
total_declared_value, declared_currency, hs_code,
duty_rate_pct, duty_amount, vat_rate_pct, vat_amount, other_charges,
status (preparing/submitted/inspecting/cleared/rejected),
clearance_date, notes
```

## G-04｜多國法規合規
新建 MRLStandard（各國農藥殘留標準）：
```
id, country_code, regulation_name, product_category,
pesticide_name, pesticide_name_en, cas_number,
mrl_value, mrl_unit (mg/kg), effective_date, source_url
```
新建 Certification（認證管理）：
```
id, certification_type (GLOBALG.A.P./BRC/IFS/HACCP/ORGANIC/HALAL/KOSHER/ISO22000),
certificate_number, issuing_body, scope_description,
certified_entity_type (company/supplier/farm), certified_entity_id,
issue_date, expiry_date, status (active/expired/suspended),
document_url, reminder_days_before_expiry
```

## G-05｜Incoterms + HSCode + Port 基礎主檔
Incoterm：
```
id, code (FOB/CIF/CFR/EXW/DDP/etc), name, description,
risk_transfer_point, cost_responsibility, version_year
```
HSCode：
```
id, hs_code, level (2/4/6/8/10位), description, description_zh,
parent_id (FK self)
```
Port：
```
id, port_code (UN/LOCODE), port_name, port_type (sea/air/inland),
country_code, city, timezone
```

---

# 區塊 H｜泰國端物流與生產（8 段）

## H-01｜SeaFreight 海運強化（改既有 Shipment or 新表）
增加 18+ 里程碑欄位：
```
shipping_mode (FCL/LCL), container_type (20RF/40RF/40HC),
forwarder, customs_broker, shipping_line,
factory_exit_date, consolidation_date, container_loading_date,
customs_declare_date, customs_cleared_date,
transshipment_port, transshipment_date,
destination_customs_date, devanning_date,
warehouse_in_date,
ocean_freight_cost, document_fee, port_charge, trucking_fee,
storage_fee, total_logistics_cost_twd
```

## H-02｜ContainerTemperatureLog 貨櫃溫度（新表）
```
id, container_no, shipment_id (FK),
recorded_at, temperature_c, humidity_pct,
location_gps, data_source (iot/manual),
is_alarm (Boolean), alarm_reason
```

## H-03｜Vehicle 車輛管理（改既有 Driver 或新表）
```
id, plate_no (unique), vehicle_type (refrigerated_truck/van/motorcycle),
brand, model, year, max_weight_kg, max_volume_cbm,
insurance_expiry, inspection_expiry,
gps_device_id, is_active
```

## H-04｜VehicleMaintenance 車輛維修（新表）
```
id, vehicle_id (FK), type (regular_service/repair/tire/inspection/insurance),
service_date, next_service_date, next_service_km,
cost, cost_currency, vendor, invoice_no,
odometer_at_service, items JSON, photo_urls JSON
```

## H-05｜DeliveryTrip 強化（改既有 DeliveryOrder）
增加欄位：
```
trip_no, vehicle_id (FK),
total_fuel_cost, toll_fee, driver_allowance, other_cost, total_trip_cost,
actual_stops, total_km, total_hours,
departure_time, return_time,
delivered_count, failed_count,
is_empty_return (Boolean), load_rate NUMERIC(5,2),
route_stops JSON
```

## H-06｜ReturnOrder 退貨管理（新表）
```
id, return_no (unique), sales_order_id (FK), customer_id (FK),
return_type (return/exchange/partial),
reason, disposal_method, responsibility,
status (pending/approved/receiving/received/inspecting/completed/rejected),
request_date, approved_at, received_date,
warehouse_id, refund_amount, refund_currency,
refund_status (pending/refunded/deducted)
```
ReturnOrderItem：
```
id, return_order_id (FK), product_type_id (FK), lot_id (FK),
qty_returned_kg, qty_accepted_kg,
return_reason, quality_notes
```

## H-07｜ContractFarming 契作合約（新表）
```
id, supplier_id (FK), farm_id,
agreement_number, crop_type, planting_area_rai,
expected_yield_kg, guaranteed_price_per_kg, price_currency,
planting_date, expected_harvest_date, seed_variety,
farming_method (conventional/organic/gap),
status (planned/active/harvesting/completed/cancelled)
```

## H-08｜SupplierEvaluation 供應商評鑑（新表）
```
id, supplier_id (FK),
evaluation_period_start, evaluation_period_end,
quality_score (0-100), delivery_score, price_score, service_score,
overall_score, tier_recommendation (A/B/C),
evaluator_id (FK), evaluation_date, comments
```

---

# 區塊 I｜財務完整（10 段）

## I-01｜匯率強化
- 確認自動抓取（玉山→台銀→open.er-api）
- 加交易匯率快照功能
- `GET /exchange-rates/monthly-avg`（月均匯率）
- 每筆 THB 交易自動記錄當時匯率

## I-02｜AP 強化
- 批次綁定（每筆 AP 對應哪個 batch）
- exchange_rate 欄位
- 泰國銀行轉帳格式欄位

## I-03｜AR 強化
- 帳齡分析 30/60/90/120 天
- 逾期自動標記 + 通知
- `GET /finance/ar-aging`

## I-04｜PettyCashFund 零用金帳戶（新表）
```
id, fund_name, holder_name, holder_user_id (FK),
department, balance NUMERIC(12,2) DEFAULT 0,
limit NUMERIC(12,2) DEFAULT 5000,
currency (THB/TWD), is_active
```

## I-05｜PettyCashRecord 零用金記錄（新表）
```
id, fund_id (FK), record_no (unique),
date, category (fuel/meal/transport/office/maintenance/postage/cleaning/other),
description, amount, vendor,
receipt_no, receipt_photos JSON, has_receipt (Boolean),
status (pending/confirmed/rejected/reimbursed),
reviewed_by (FK), reviewed_at, review_note,
submitted_by (FK)
```

## I-06｜BankAccount 銀行帳戶（新表）
```
id, account_name, account_no, bank_name, bank_code,
swift_code, account_type (checking/savings/credit_card),
currency, country_code,
opening_balance, current_balance,
credit_limit (信用卡), statement_day, payment_day,
is_active
```

## I-07｜BankTransaction + Cheque（新表）
BankTransaction：
```
id, bank_account_id (FK), tx_date, description,
direction (debit/credit), amount, balance,
reference_no, category, is_reconciled, reconciled_at
```
Cheque：
```
id, cheque_no, cheque_type (receivable/payable),
bank_name, amount, issue_date, due_date,
status (holding/deposited/cleared/bounced/cancelled),
party_name, party_type (customer/supplier)
```

## I-08｜跨幣別損益表
- 新建 `routers/financial_report.py`
- 營收（TWD）vs 成本（THB × 匯率）
- 月度損益：分幣別 + 合計
- 匯兌損益計算

## I-09｜泰國稅務
- WHT 預扣稅：1%/2%/3% 不同類別
- VAT 7% 計算
- 稅務報表 API

## I-10｜Budget + CashFlowPlan（新表）
Budget：
```
id, budget_year, budget_month (nullable = 年度),
department, category (revenue/cogs/opex/capex/hr/marketing/logistics),
budget_amount, actual_amount, currency, status (draft/approved)
@@unique([budget_year, budget_month, category, department])
```
CashFlowPlan：
```
id, plan_year, plan_month, flow_type (inflow/outflow),
category (sales_receipt/ar_collection/payment/salary/rent/tax),
planned_amount, actual_amount, currency
```

---

# 區塊 J｜退貨與合約（4 段）

## J-01｜ReturnOrder（已在 H-06 定義）

## J-02｜Contract 合約管理（新表）
```
id, contract_no (unique), title,
contract_type (sales/purchase/service/lease),
status (draft/active/expired/terminated/renewed),
customer_id (FK nullable), supplier_id (FK nullable),
signed_at, effective_from, effective_to,
total_value, currency,
payment_terms, auto_renew (Boolean), reminder_days (default 30),
attachment_url, created_by
```

## J-03｜ContractPaySchedule 付款排程（新表）
```
id, contract_id (FK), due_date, amount, description,
is_paid (Boolean), paid_at
```

## J-04｜ContractRenewal 續約紀錄（新表）
```
id, contract_id (FK), renewed_at, new_effective_to
```

---

# 區塊 K｜公告 / 行事曆 / 會議（6 段）

## K-01｜Announcement 公告（新表）
```
id, title, content, category (general/policy/it/hr/urgent),
priority (low/normal/high/urgent),
is_pinned (Boolean), is_published (Boolean),
published_at, expires_at,
target_roles JSON (角色推播),
created_by (FK)
```

## K-02｜BusinessEvent 公司行事曆（新表）
```
id, event_no (unique), title,
event_type (exhibition/association/channel_promo/weekly_admin/promo/other),
status (planning/confirmed/in_progress/completed/cancelled),
start_date, end_date, all_day (Boolean),
location, venue,
owner_user_id (FK), attendee_user_ids JSON,
budget, actual_cost, currency,
prep_checklist JSON,
tags JSON
```

## K-03｜PromoCalendar 大檔期（新表）
```
id, promo_code (unique), promo_name,
promo_tier (national_major/quarterly/monthly/flash_sale),
year, event_start_date, event_end_date,
prep_start_date, nego_start_date, exec_start_date,
current_phase (preparation/negotiation/execution/live/review),
reminder_days JSON, reminder_sent_at JSON,
revenue_target, revenue_actual,
target_channels JSON, featured_skus JSON,
responsible_user_id (FK)
```

## K-04｜MeetingRecord 會議紀錄（新表）
```
id, meeting_no (unique), title,
meeting_type (weekly_admin/channel_negotiation/supplier_meeting/internal/other),
status (scheduled/in_progress/completed/cancelled),
meeting_date, start_time, end_time,
location, is_online (Boolean), meeting_url,
business_event_id (FK nullable), customer_id (FK nullable),
facilitator_id (FK),
attendees JSON, external_attendees,
agenda, summary, decisions,
photo_urls JSON
```

## K-05｜MeetingActionItem 會議待辦（新表）
```
id, meeting_record_id (FK), action_title, action_description,
owner_user_id (FK), due_date,
status (open/in_progress/done/cancelled),
priority (low/medium/high/urgent),
completion_note, completed_at
```

## K-06｜AI 會議記錄（Phase 3 預留欄位）
MeetingRecord 加：
```
audio_file_url, audio_duration_sec,
transcript_text (Text), transcript_status (pending/processing/completed/failed),
ai_summary (Text), ai_action_items JSON,
ai_processed_at
```

---

# 區塊 L｜客訴與品質追溯（3 段）

## L-01｜CustomerComplaint 客訴管理（新表）
```
id, complaint_no (unique), customer_id (FK),
sales_order_id (FK nullable), shipment_id (FK nullable),
complaint_date, product_type_id (FK), lot_number,
complaint_category (quality/packaging/delivery/documentation/other),
description, severity (critical/major/minor),
photos_url JSON, sample_retained (Boolean),
root_cause_analysis, corrective_action, preventive_action,
compensation_type (credit_note/replacement/refund),
compensation_amount, compensation_currency,
status (open/investigating/resolved/closed),
responsible_person_id (FK),
target_resolution_date, actual_resolution_date
```

## L-02｜LotTraceability 批次追溯強化
在 Batch model 加：
```
parent_batch_ids JSON,  # 上游批次（原料來源）
child_batch_ids JSON,   # 下游批次（加工產出）
farm_origin_id UUID FK, # 農場來源
harvest_field_code VARCHAR(50),  # 田塊代碼
recall_status VARCHAR(20) DEFAULT 'none',  # none/simulated/active/completed
recall_initiated_at DateTime
```

## L-03｜PesticideResidueTest 農藥殘留專表（新表）
```
id, qc_inspection_id (FK), product_type_id (FK), lot_number,
test_date, lab_name, lab_report_number,
sample_origin, test_method (GC-MS/LC-MS),
overall_result (pass/fail), report_url
```
PesticideResidueTestItem：
```
id, test_id (FK), pesticide_name, pesticide_name_en,
cas_number, detected_value, detected_unit (mg/kg),
detection_limit, quantification_limit,
result (not_detected/within_limit/exceeded)
```

---

# 區塊 M｜全球市場情報 — Bloomberg 功能（8 段）

## M-01｜MarketPriceSource 資料來源管理（新表）
```
id, source_code, source_name, source_type (government/exchange/private),
country_code, url, api_endpoint,
data_format, update_frequency, is_active, last_fetched_at
```
來源清單：
- 台灣：農委會農產品批發市場交易行情站（北農、西螺、高雄）
- 泰國：Talaad Thai 市場、泰國農業部
- 日本：東京大田市場、大阪中央市場
- 歐洲：EU Market Observatory
- 北美：USDA Market News
- 中國：各省批發市場

## M-02｜MarketPrice 市場價格數據（新表）
```
id, source_id (FK), price_date,
product_category, product_name, product_variety,
market_name, country_code, city,
price_low, price_high, price_avg, price_modal,
price_currency, price_unit, volume_traded, volume_unit,
price_trend (up/down/stable)
```

## M-03｜MarketPriceAlert 價格異常警報（新表）
```
id, alert_type (price_spike/price_drop/new_high/new_low),
product_category, market_name, country_code,
trigger_condition, trigger_value, actual_value,
alert_date, severity (info/warning/critical),
is_acknowledged (Boolean), acknowledged_by
```

## M-04｜CompetitorProfile + CompetitorPrice（新表）
CompetitorProfile：
```
id, competitor_name, country_code, business_type,
main_products, annual_revenue_estimate, market_share_estimate,
key_markets JSON, key_customers JSON,
strengths, weaknesses, website, source_info
```
CompetitorPrice：
```
id, competitor_id (FK), product_category, product_name,
market_country, channel_type,
observed_price, price_currency, price_unit,
observed_date, source (store_visit/online/trade_show/intel),
observer_name, photo_url
```

## M-05｜GlobalTradeStatistics 全球貿易統計（新表）
```
id, data_source (UN_Comtrade/national_customs),
reporting_country, partner_country,
trade_flow (import/export), hs_code,
period_year, period_month,
value_usd, quantity_kg, unit_value_usd_per_kg,
yoy_value_change_pct, yoy_qty_change_pct
```

## M-06｜WeatherData + WeatherAlert 強化
現有 WeatherForecast 擴充：
```
gps_latitude, gps_longitude,
humidity_pct, wind_speed_kmh, solar_radiation,
weather_condition, data_source (tmd/openweathermap/manual),
forecast_or_actual (forecast/actual)
```
新建 WeatherAlert：
```
id, alert_type (typhoon/flood/drought/frost/heatwave),
affected_region, country_code, severity (watch/warning/emergency),
start_date, end_date, description,
potential_crop_impact, source, source_url, is_active
```

## M-07｜FreightIndex + SupplyDemandIndicator（新表）
FreightIndex：
```
id, index_name (SCFI/WCI/BDI/custom),
route_origin, route_destination, container_type,
index_date, index_value, index_unit,
wow_change_pct, yoy_change_pct, source
```
SupplyDemandIndicator：
```
id, indicator_type (production_forecast/import_forecast/inventory_level/planting_area),
product_category, country_code, region,
period_year, period_month, value, value_unit,
yoy_change_pct, source, confidence_level (high/medium/low)
```

## M-08｜GlobalBuyerDirectory 全球買家資料庫（新表）
```
id, company_name, country_code, city,
business_type (importer/distributor/retailer/processor/foodservice),
main_import_products, annual_import_volume_estimate,
key_source_countries JSON,
contact_name, contact_email, contact_phone, website,
company_size (small/medium/large/enterprise),
data_source (trade_show/directory/referral/web_scraping),
credit_rating, verified_status (Boolean),
last_contacted_date, interest_level (hot/warm/cold/none),
assigned_sales_rep_id (FK), notes, is_active
```

---

# 區塊 N｜全球定價引擎（3 段）

## N-01｜PriceList + PriceListItem（新表）
PriceList：
```
id, price_list_code, price_list_name,
price_list_type (standard/contract/promotional),
customer_id (FK nullable), customer_tier, channel_type, market_region,
currency_code, incoterm,
effective_date, expiry_date,
status (draft/active/expired), approved_by, approved_at
```
PriceListItem：
```
id, price_list_id (FK), product_type_id (FK), packaging_spec,
unit_price, price_uom,
min_qty, max_qty, discount_pct, floor_price,
cost_reference, target_margin_pct
```

## N-02｜PricingRule 定價規則引擎（新表）
```
id, rule_name, rule_type (volume_discount/early_payment/seasonal/bundle),
priority, conditions JSON, action_type (discount_pct/fixed_price/adjustment),
action_value, effective_date, expiry_date, is_active
```

## N-03｜動態定價 API
- `POST /pricing/calculate` — 輸入客戶+產品+數量 → 回傳建議售價
- 計算邏輯：原料成本 + 加工成本 + 物流成本 + 關稅 + 目標利潤率
- 參考市場行情自動調整
- 低於底價需審核

---

# 區塊 O｜儀表板與報表（4 段）

## O-01｜KPI 定義 + 歷史值（新表）
KPIDefinition：
```
id, kpi_code, kpi_name, kpi_category,
calculation_formula, data_source,
target_value, warning_threshold, critical_threshold,
unit, direction (higher_is_better/lower_is_better),
update_frequency, owner_role
```
KPIValue：
```
id, kpi_id (FK), period_type (daily/weekly/monthly),
period_date, actual_value, target_value,
achievement_pct, status (on_track/warning/critical)
```

## O-02｜DashboardConfig 儀表板配置（新表）
```
id, dashboard_code, dashboard_name,
dashboard_type (executive/sales/supply_chain/finance/quality/market),
layout_config JSON, refresh_interval_seconds,
is_default (Boolean), role_id (FK nullable), user_id (FK nullable)
```

## O-03｜7 大儀表板
1. CEO 戰略：營收趨勢、毛利率、市佔率、風險指標
2. 銷售：各市場/客戶/產品銷售即時數據、訂單管線
3. 供應鏈：庫存水位、在途貨物、交貨準時率、供應商績效
4. 財務：現金流、應收帳齡、匯兌損益、成本趨勢
5. 品質：合格率趨勢、客訴統計、認證到期倒數
6. 市場情報：價格走勢、供需指標、天氣預警、競品動態
7. 風險：綜合風險熱力圖、各風險類別評分

## O-04｜SavedReport 自訂報表（新表）
```
id, report_code, report_name, report_category,
query_definition JSON, filter_config JSON,
output_format (pdf/excel/csv), schedule_cron,
recipients JSON, last_run_at, created_by, is_shared
```

---

# 區塊 P｜前端 + 翻譯 + 上線（10 段）

## P-01｜安裝 shadcn/ui + recharts + sonner
## P-02｜Sidebar 擴充（加入所有新模組導航）
## P-03｜角色專屬 Dashboard + 7 大儀表板
## P-04｜CRM 前端（健康/流失/預測/告警/看板/漏斗）
## P-05｜業務流程前端（商機/追蹤/拜訪/排程/樣品/報價）
## P-06｜財務前端（零用金/銀行/預算/損益/稅務）
## P-07｜物流前端（海運/車隊/配送/簽收/退貨）
## P-08｜Bloomberg 前端（市場價格/競品/天氣/運費/買家）
## P-09｜翻譯同步（所有新功能 zh-TW/en/th 三語）
## P-10｜上線驗收
- 環境變數安全確認
- Alembic migration 完整跑過
- 資料庫索引補齊
- 角色權限測試（185 權限 × 11+ 角色）
- 三語系顯示正確
- Rate limit / 加密 / Token rotation 功能測試
- 冷鏈溫度記錄完整性
- HTTPS / 備份 / 日誌確認
- 管理員帳號密碼修改

---

# 總覽

| 區塊 | 段數 | 涵蓋範圍 |
|------|------|---------|
| A 安全加固 | 8 | 加密、稽核、限流、序號、Logger、Token、錯誤、Nginx/Docker |
| B 全域欄位補齊 | 6 | updated_by、deleted_at、幣別、匯率、全球化、冷鏈 |
| C 人事權限 | 7 | 員工、部門、異動、出勤、薪資、等級、權限擴充 |
| D CRM 基礎 | 5 | Customer 擴充、聯絡人、多地址、Scope、通知 |
| E CRM 進階 | 8 | 健康分數、流失、預測、KPI、日報、拜訪、告警、看板 |
| F 銷售業務 | 7 | 商機、追蹤、拜訪、排程、樣品、報價、審批 |
| G 國際貿易 | 5 | 貿易文件、信用狀、報關、法規合規、基礎主檔 |
| H 物流生產 | 8 | 海運、貨櫃溫度、車輛、維修、配送、退貨、契作、供應商評鑑 |
| I 財務完整 | 10 | 匯率、AP/AR、零用金、銀行、支票、損益、稅務、預算 |
| J 退貨合約 | 4 | 退貨、合約、付款排程、續約 |
| K 公告行事曆 | 6 | 公告、活動、檔期、會議、待辦、AI 預留 |
| L 客訴品質 | 3 | 客訴、追溯、農藥檢測 |
| M Bloomberg 情報 | 8 | 市場價格、警報、競品、貿易統計、天氣、運費、買家庫 |
| N 全球定價 | 3 | 價格表、定價規則、動態定價 |
| O 儀表板報表 | 4 | KPI、儀表板配置、7 大面板、自訂報表 |
| P 前端翻譯上線 | 10 | UI、8 組前端頁面、翻譯、驗收 |
| **合計** | **102 段** | |

---

## 新增資料表預估

| 區塊 | 新表數量 |
|------|---------|
| C 人事 | 4（EmployeeProfile, Department, Appointment, Attendance, PayrollRecord） |
| D CRM | 2（CustomerContact, CustomerAddress） |
| E CRM 進階 | 2（SalesTarget, SalesDailyReport） |
| F 銷售 | 6（SalesOpportunity, FollowUpLog, VisitRecord, SalesSchedule, SampleRecord, Quotation, QuotationItem, QuotationApproval） |
| G 國際貿易 | 7（TradeDocument, LetterOfCredit, LCAmendment, CustomsDeclaration, MRLStandard, Certification, Incoterm, HSCode, Port） |
| H 物流 | 5（ContainerTempLog, Vehicle, VehicleMaintenance, ReturnOrder, ContractFarming, SupplierEvaluation） |
| I 財務 | 6（PettyCashFund, PettyCashRecord, BankAccount, BankTransaction, Cheque, Budget, CashFlowPlan） |
| J 合約 | 3（Contract, ContractPaySchedule, ContractRenewal） |
| K 公告行事曆 | 5（Announcement, BusinessEvent, PromoCalendar, MeetingRecord, MeetingActionItem） |
| L 客訴 | 3（CustomerComplaint, PesticideResidueTest, PesticideResidueTestItem） |
| M Bloomberg | 8（MarketPriceSource, MarketPrice, MarketPriceAlert, CompetitorProfile, CompetitorPrice, GlobalTradeStats, FreightIndex, SupplyDemandIndicator, GlobalBuyerDirectory, WeatherAlert） |
| N 定價 | 3（PriceList, PriceListItem, PricingRule） |
| O 報表 | 4（KPIDefinition, KPIValue, DashboardConfig, SavedReport） |
| **合計** | **~55 張新表** |

**最終系統：67 現有 + 55 新建 = 122+ 張資料表**
