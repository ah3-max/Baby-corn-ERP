/**
 * API 客戶端
 * 統一管理所有後端 API 呼叫，自動帶入 JWT Token
 */
import axios from 'axios';
import Cookies from 'js-cookie';

// ─── Axios 實例 ─────────────────────────────────────
// baseURL 使用相對路徑，讓請求經過 Next.js server-side rewrite 代理到後端
// 這樣無論前端 URL 是 localhost 還是外網 ngrok/Cloudflare URL，API 都能正常運作

export const apiClient = axios.create({
  baseURL: '/api/v1',
  headers: { 'Content-Type': 'application/json' },
});

// 請求攔截器：自動帶入 Access Token
apiClient.interceptors.request.use((config) => {
  const token = Cookies.get('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// 回應攔截器：Token 過期時自動換發
// 注意：登入 endpoint 本身不進行 retry，避免攔截正常的帳密錯誤
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    // 登入 endpoint 的 401 代表帳密錯誤，直接拋出讓元件的 catch 處理
    if (originalRequest.url?.includes('/auth/login')) {
      return Promise.reject(error);
    }

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      const refreshToken = Cookies.get('refresh_token');

      if (refreshToken) {
        try {
          const { data } = await axios.post(`/api/v1/auth/refresh`, {
            refresh_token: refreshToken,
          });
          Cookies.set('access_token', data.access_token, { expires: 1 });
          originalRequest.headers.Authorization = `Bearer ${data.access_token}`;
          return apiClient(originalRequest);
        } catch {
          // Refresh Token 也失效，強制登出
          Cookies.remove('access_token');
          Cookies.remove('refresh_token');
          window.location.href = '/zh-TW/login';
        }
      } else {
        window.location.href = '/zh-TW/login';
      }
    }
    return Promise.reject(error);
  }
);

// ─── 認證 API ────────────────────────────────────────

export const authApi = {
  login: (email: string, password: string) =>
    apiClient.post('/auth/login', { email, password }),

  logout: (refreshToken: string) =>
    apiClient.post('/auth/logout', { refresh_token: refreshToken }),

  getMe: () =>
    apiClient.get('/auth/me'),

  changePassword: (oldPassword: string, newPassword: string) =>
    apiClient.put('/auth/me/password', {
      old_password: oldPassword,
      new_password: newPassword,
    }),

  updateLanguage: (language: string) =>
    apiClient.put(`/auth/me/language?language=${language}`),
};

// ─── 使用者 API ───────────────────────────────────────

export const usersApi = {
  list: () => apiClient.get('/users'),
  get: (id: string) => apiClient.get(`/users/${id}`),
  create: (data: object) => apiClient.post('/users', data),
  update: (id: string, data: object) => apiClient.put(`/users/${id}`, data),
  deactivate: (id: string) => apiClient.delete(`/users/${id}`),
};

// ─── 採購 API ────────────────────────────────────────

export const purchasesApi = {
  list: (params?: { status?: string; keyword?: string }) =>
    apiClient.get('/purchases', { params }),
  get: (id: string) => apiClient.get(`/purchases/${id}`),
  create: (data: object) => apiClient.post('/purchases', data),
  update: (id: string, data: object) => apiClient.put(`/purchases/${id}`, data),
  updateStatus: (id: string, status: string) =>
    apiClient.put(`/purchases/${id}/status`, null, { params: { status } }),
  confirmArrival: (id: string, data: object) =>
    apiClient.post(`/purchases/${id}/arrive`, data),
};

// ─── 供應商 API ───────────────────────────────────────

export const suppliersApi = {
  list: (params?: { supplier_type?: string; keyword?: string; is_active?: boolean }) =>
    apiClient.get('/suppliers', { params }),
  get: (id: string) => apiClient.get(`/suppliers/${id}`),
  create: (data: object) => apiClient.post('/suppliers', data),
  update: (id: string, data: object) => apiClient.put(`/suppliers/${id}`, data),
  deactivate: (id: string) => apiClient.delete(`/suppliers/${id}`),
};

// ─── QC / 工廠 API ────────────────────────────────────────

export const qcApi = {
  listFactoryBatches: () => apiClient.get('/factory/batches'),
  listRecords: (batchId?: string) =>
    apiClient.get('/qc', { params: batchId ? { batch_id: batchId } : {} }),
  create: (data: object) => apiClient.post('/qc', data),
  delete: (id: string) => apiClient.delete(`/qc/${id}`),
};

// ─── 出口物流 API ────────────────────────────────────────

export const shipmentsApi = {
  list: (params?: { status?: string }) => apiClient.get('/shipments', { params }),
  get: (id: string) => apiClient.get(`/shipments/${id}`),
  create: (data: object) => apiClient.post('/shipments', data),
  update: (id: string, data: object) => apiClient.put(`/shipments/${id}`, data),
  advance: (id: string) => apiClient.put(`/shipments/${id}/advance`),
  // 刪除出口單（僅限 preparing 狀態）
  delete: (id: string) => apiClient.delete(`/shipments/${id}`),
};

// ─── 客戶 API ────────────────────────────────────────

export const customersApi = {
  list: (params?: { keyword?: string; is_active?: boolean }) =>
    apiClient.get('/customers', { params }),
  get: (id: string) => apiClient.get(`/customers/${id}`),
  create: (data: object) => apiClient.post('/customers', data),
  update: (id: string, data: object) => apiClient.put(`/customers/${id}`, data),
};

// ─── 銷售 API ────────────────────────────────────────

export const salesApi = {
  list: (params?: { status?: string; customer_id?: string; batch_id?: string }) =>
    apiClient.get('/sales', { params }),
  get: (id: string) => apiClient.get(`/sales/${id}`),
  create: (data: object) => apiClient.post('/sales', data),
  update: (id: string, data: object) => apiClient.put(`/sales/${id}`, data),
  advance: (id: string) => apiClient.put(`/sales/${id}/advance`),
  delete: (id: string) => apiClient.delete(`/sales/${id}`),
};

// ─── 分析 API ────────────────────────────────────────

export const analyticsApi = {
  summary: () => apiClient.get('/analytics/summary'),
  batches: (exchangeRate?: number) =>
    apiClient.get('/analytics/batches', {
      params: exchangeRate ? { exchange_rate: exchangeRate } : {},
    }),
  daily: (params?: { date_from?: string; date_to?: string }) =>
    apiClient.get('/analytics/daily', { params }),
  /** 發送成本利潤報表 Email：前端傳入收件人、主旨及 HTML 內容，後端透過 SMTP 發送 */
  sendCostReport: (data: {
    to_emails:    string[];   // 收件人 email 列表
    subject:      string;     // 信件主旨
    html_content: string;     // 報表 HTML 內容
  }) => apiClient.post('/analytics/send-cost-report', data),
};

// ─── 批次 API ────────────────────────────────────────

export const batchesApi = {
  list: (params?: { status?: string; keyword?: string; purchase_order_id?: string }) =>
    apiClient.get('/batches', { params }),
  get: (id: string) => apiClient.get(`/batches/${id}`),
  create: (data: object) => apiClient.post('/batches', data),
  update: (id: string, data: object) => apiClient.put(`/batches/${id}`, data),
  advance: (id: string) => apiClient.put(`/batches/${id}/advance`),
  bulkAdvance: (batchIds: string[]) =>
    apiClient.post('/batches/bulk-advance', { batch_ids: batchIds }),
  delete: (id: string, force = false) =>
    apiClient.delete(`/batches/${id}`, { params: force ? { force: true } : {} }),
};

// ─── 庫存管理 API ────────────────────────────────────────

export const inventoryApi = {
  // 倉庫
  listWarehouses: () => apiClient.get('/inventory/warehouses'),
  createWarehouse: (data: object) => apiClient.post('/inventory/warehouses', data),
  updateWarehouse: (id: string, data: object) => apiClient.put(`/inventory/warehouses/${id}`, data),
  listLocations: (warehouseId: string) => apiClient.get(`/inventory/warehouses/${warehouseId}/locations`),
  createLocation: (warehouseId: string, data: object) =>
    apiClient.post(`/inventory/warehouses/${warehouseId}/locations`, data),
  // 庫存批次
  listLots: (params?: { warehouse_id?: string; status?: string; batch_id?: string }) =>
    apiClient.get('/inventory/lots', { params }),
  createLot: (data: object) => apiClient.post('/inventory/lots', data),
  getLot: (id: string) => apiClient.get(`/inventory/lots/${id}`),
  scrapLot: (id: string, data: { weight_kg: number; reason: string }) =>
    apiClient.post(`/inventory/lots/${id}/scrap`, data),
  adjustLot: (id: string, data: { weight_kg: number; boxes?: number; reason: string }) =>
    apiClient.post(`/inventory/lots/${id}/adjust`, data),
  // 統計
  summary: () => apiClient.get('/inventory/summary'),
};

// ─── 成本 API ────────────────────────────────────────

export const costsApi = {
  listEvents: (batchId: string) =>
    apiClient.get(`/batches/${batchId}/costs`),
  createEvent: (batchId: string, data: object) =>
    apiClient.post(`/batches/${batchId}/costs`, data),
  voidEvent: (batchId: string, eventId: string) =>
    apiClient.post(`/batches/${batchId}/costs/${eventId}/void`),
  getSummary: (batchId: string, exchangeRate?: number) =>
    apiClient.get(`/batches/${batchId}/cost-summary`, {
      params: exchangeRate ? { exchange_rate: exchangeRate } : {},
    }),
  // 取得每個成本類型最近一次使用的金額，用於自動帶入
  getRecentValues: () =>
    apiClient.get('/costs/recent-values'),
};

// ─── 即時匯率 API ─────────────────────────────────────

export const exchangeRatesApi = {
  // 取得即時匯率（玉山銀行優先）
  getLive: () =>
    apiClient.get('/exchange-rates/live'),
  // 舊版兩條路線比較
  compare: (amountTwd: number = 100000) =>
    apiClient.get('/exchange-rates/compare', { params: { amount_twd: amountTwd } }),
  // 智慧換匯比較（六條路線，含手續費）
  smartRoute: (amountTwd: number = 100000) =>
    apiClient.get('/exchange-rates/smart-route', { params: { amount_twd: amountTwd } }),
  // 匯率歷史
  list: (fromCurrency = 'THB', toCurrency = 'TWD') =>
    apiClient.get('/exchange-rates', { params: { from_currency: fromCurrency, to_currency: toCurrency } }),
  // 手動新增匯率記錄
  create: (data: object) =>
    apiClient.post('/exchange-rates', data),
};

// ─── 附件 API ────────────────────────────────────────

export const attachmentsApi = {
  /**
   * 取得指定實體的附件列表
   */
  list: (entityType: string, entityId: string) =>
    apiClient.get('/attachments', { params: { entity_type: entityType, entity_id: entityId } }),

  /**
   * 真實檔案上傳（multipart/form-data）
   * @param file        要上傳的檔案物件
   * @param entityType  實體類型，例如 'batch'
   * @param entityId    實體 UUID
   * @param tags        逗號分隔的 tag 字串（選填）
   */
  upload: (file: File, entityType: string, entityId: string, tags?: string) => {
    const fd = new FormData();
    fd.append('file', file);
    fd.append('entity_type', entityType);
    fd.append('entity_id', entityId);
    if (tags) fd.append('tags', tags);
    // 不設定 Content-Type，讓瀏覽器自動帶入 boundary
    return apiClient.post('/attachments/upload', fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },

  /**
   * 刪除附件
   */
  delete: (id: string) => apiClient.delete(`/attachments/${id}`),
};

// ─── 發票 API ────────────────────────────────────────

export const invoicesApi = {
  list: (params?: { shipment_id?: string; status?: string }) =>
    apiClient.get('/invoices', { params }),
  get: (id: string) => apiClient.get(`/invoices/${id}`),
  create: (data: object) => apiClient.post('/invoices', data),
  update: (id: string, data: object) => apiClient.put(`/invoices/${id}`, data),
  updateStatus: (id: string, status: string) =>
    apiClient.put(`/invoices/${id}/status`, null, { params: { status } }),
  delete: (id: string) => apiClient.delete(`/invoices/${id}`),
  getCompanyDefaults: () => apiClient.get('/invoices/company-defaults'),
  getHtml: (id: string) => apiClient.get(`/invoices/${id}/html`, { responseType: 'text' }),
};

// ─── 品項 API ────────────────────────────────────────

export const productTypesApi = {
  list: () => apiClient.get('/product-types'),
  listAll: () => apiClient.get('/product-types/all'),
  get: (id: string) => apiClient.get(`/product-types/${id}`),
  create: (data: object) => apiClient.post('/product-types', data),
  update: (id: string, data: object) => apiClient.put(`/product-types/${id}`, data),
};

// ─── 角色 API ────────────────────────────────────────

export const rolesApi = {
  list: () => apiClient.get('/roles'),
  get: (id: string) => apiClient.get(`/roles/${id}`),
  create: (data: object) => apiClient.post('/roles', data),
  update: (id: string, data: object) => apiClient.put(`/roles/${id}`, data),
  delete: (id: string) => apiClient.delete(`/roles/${id}`),
  listPermissions: () => apiClient.get('/permissions'),
};

// ─── WP2：QC 品質中心 API ──────────────────────────────────

export const qcEnhancedApi = {
  listInspections: (params?: { batch_id?: string; stage?: string; result?: string }) =>
    apiClient.get('/qc/inspections', { params }),
  getInspection: (id: string) => apiClient.get(`/qc/inspections/${id}`),
  createInspection: (data: object) => apiClient.post('/qc/inspections', data),
  updateInspection: (id: string, data: object) => apiClient.put(`/qc/inspections/${id}`, data),
  deleteInspection: (id: string) => apiClient.delete(`/qc/inspections/${id}`),
  // 照片
  uploadPhoto: (inspectionId: string, formData: FormData) =>
    apiClient.post(`/qc/inspections/${inspectionId}/photos`, formData, { headers: { 'Content-Type': 'multipart/form-data' } }),
  listPhotos: (inspectionId: string) => apiClient.get(`/qc/inspections/${inspectionId}/photos`),
  deletePhoto: (photoId: string) => apiClient.delete(`/qc/photos/${photoId}`),
  // 抽樣規則
  listSamplingRules: () => apiClient.get('/qc/sampling-rules'),
  createSamplingRule: (data: object) => apiClient.post('/qc/sampling-rules', data),
  updateSamplingRule: (id: string, data: object) => apiClient.put(`/qc/sampling-rules/${id}`, data),
  // 通路標準
  listChannelStandards: (params?: { channel_type?: string }) =>
    apiClient.get('/qc/channel-standards', { params }),
  createChannelStandard: (data: object) => apiClient.post('/qc/channel-standards', data),
  updateChannelStandard: (id: string, data: object) => apiClient.put(`/qc/channel-standards/${id}`, data),
  checkBatch: (standardId: string, batchId: string) =>
    apiClient.get(`/qc/channel-standards/${standardId}/check-batch/${batchId}`),
  // 分析
  analyticsTrend: (params?: { date_from?: string; date_to?: string }) =>
    apiClient.get('/qc/analytics/trend', { params }),
  analyticsSupplierQuality: () => apiClient.get('/qc/analytics/supplier-quality'),
  analyticsDefectFrequency: (params?: { date_from?: string; date_to?: string }) =>
    apiClient.get('/qc/analytics/defect-frequency', { params }),
  analyticsBatchRecommendation: (batchId: string) =>
    apiClient.get(`/qc/analytics/batch-recommendation/${batchId}`),
  // 溫度記錄
  listTemperatureLogs: (params?: { entity_type?: string; entity_id?: string }) =>
    apiClient.get('/temperature-logs', { params }),
  createTemperatureLog: (data: object) => apiClient.post('/temperature-logs', data),
};

// ─── WP3：CRM API ─────────────────────────────────────────

export const crmApi = {
  // 團隊
  listTeams: (params?: { region?: string }) => apiClient.get('/crm/teams', { params }),
  createTeam: (data: object) => apiClient.post('/crm/teams', data),
  updateTeam: (id: string, data: object) => apiClient.put(`/crm/teams/${id}`, data),
  addTeamMember: (teamId: string, data: object) => apiClient.post(`/crm/teams/${teamId}/members`, data),
  removeTeamMember: (teamId: string, memberId: string) => apiClient.delete(`/crm/teams/${teamId}/members/${memberId}`),
  // 活動
  listActivities: (params?: { customer_id?: string; user_id?: string }) =>
    apiClient.get('/crm/activities', { params }),
  createActivity: (data: object) => apiClient.post('/crm/activities', data),
  updateActivity: (id: string, data: object) => apiClient.put(`/crm/activities/${id}`, data),
  // 任務
  listTasks: (params?: { assigned_to?: string; status?: string }) =>
    apiClient.get('/crm/tasks', { params }),
  createTask: (data: object) => apiClient.post('/crm/tasks', data),
  updateTask: (id: string, data: object) => apiClient.put(`/crm/tasks/${id}`, data),
  // 分析
  dashboard: () => apiClient.get('/crm/dashboard'),
  userPerformance: (userId: string, month?: string) =>
    apiClient.get(`/crm/user/${userId}/performance`, { params: month ? { month } : {} }),
  customer360: (customerId: string) => apiClient.get(`/crm/customers/360/${customerId}`),
  ranking: (month?: string) => apiClient.get('/crm/ranking', { params: month ? { month } : {} }),
};

// ─── WP4：物流配送 API ─────────────────────────────────────

export const logisticsApi = {
  // 司機
  listDrivers: (params?: { is_active?: boolean }) => apiClient.get('/drivers', { params }),
  createDriver: (data: object) => apiClient.post('/drivers', data),
  updateDriver: (id: string, data: object) => apiClient.put(`/drivers/${id}`, data),
  // 配送單
  listDeliveryOrders: (params?: { status?: string; driver_id?: string; dispatch_date?: string }) =>
    apiClient.get('/delivery-orders', { params }),
  getDeliveryOrder: (id: string) => apiClient.get(`/delivery-orders/${id}`),
  createDeliveryOrder: (data: object) => apiClient.post('/delivery-orders', data),
  updateDeliveryOrder: (id: string, data: object) => apiClient.put(`/delivery-orders/${id}`, data),
  acceptDeliveryOrder: (id: string) => apiClient.put(`/delivery-orders/${id}/accept`),
  advanceDeliveryOrder: (id: string) => apiClient.put(`/delivery-orders/${id}/advance`),
  deliverItem: (orderId: string, itemId: string, data: object) =>
    apiClient.post(`/delivery-orders/${orderId}/items/${itemId}/deliver`, data),
  // 出庫單
  listOutboundOrders: (params?: { status?: string; warehouse_id?: string }) =>
    apiClient.get('/outbound-orders', { params }),
  getOutboundOrder: (id: string) => apiClient.get(`/outbound-orders/${id}`),
  createOutboundOrder: (data: object) => apiClient.post('/outbound-orders', data),
  approveOutbound: (id: string) => apiClient.put(`/outbound-orders/${id}/approve`),
  pickOutbound: (id: string) => apiClient.put(`/outbound-orders/${id}/pick`),
  shipOutbound: (id: string) => apiClient.put(`/outbound-orders/${id}/ship`),
};

// ─── WP5：財務 API ────────────────────────────────────────

export const financeApi = {
  // 應收帳款
  listAR: (params?: { status?: string; customer_id?: string; overdue?: boolean }) =>
    apiClient.get('/finance/ar', { params }),
  createAR: (data: object) => apiClient.post('/finance/ar', data),
  getAR: (id: string) => apiClient.get(`/finance/ar/${id}`),
  updateAR: (id: string, data: object) => apiClient.put(`/finance/ar/${id}`, data),
  arAging: () => apiClient.get('/finance/ar/aging'),
  // 應付帳款
  listAP: (params?: { status?: string; supplier_id?: string }) =>
    apiClient.get('/finance/ap', { params }),
  createAP: (data: object) => apiClient.post('/finance/ap', data),
  getAP: (id: string) => apiClient.get(`/finance/ap/${id}`),
  updateAP: (id: string, data: object) => apiClient.put(`/finance/ap/${id}`, data),
  apAging: () => apiClient.get('/finance/ap/aging'),
  // 摘要 & 報表
  summary: () => apiClient.get('/finance/summary'),
  profitLoss: (params?: { date_from?: string; date_to?: string }) =>
    apiClient.get('/finance/profit-loss', { params }),
};

// ─── WP6：庫存分析 API ─────────────────────────────────────

export const inventoryAnalyticsApi = {
  aging: (params?: { warehouse_id?: string }) =>
    apiClient.get('/inventory/analytics/aging', { params }),
  turnover: (days?: number) =>
    apiClient.get('/inventory/analytics/turnover', { params: days ? { days } : {} }),
  depletionForecast: () => apiClient.get('/inventory/analytics/depletion-forecast'),
  reorderSuggestion: () => apiClient.get('/inventory/analytics/reorder-suggestion'),
};

// ─── WP7：計劃 API ────────────────────────────────────────

export const planningApi = {
  // 採購計劃
  listProcurement: (params?: { month?: string; status?: string }) =>
    apiClient.get('/plans/procurement', { params }),
  createProcurement: (data: object) => apiClient.post('/plans/procurement', data),
  getProcurement: (id: string) => apiClient.get(`/plans/procurement/${id}`),
  updateProcurement: (id: string, data: object) => apiClient.put(`/plans/procurement/${id}`, data),
  approveProcurement: (id: string) => apiClient.put(`/plans/procurement/${id}/approve`),
  // 天氣
  listWeather: (params?: { region?: string; date_from?: string; date_to?: string }) =>
    apiClient.get('/plans/weather', { params }),
  createWeather: (data: object) => apiClient.post('/plans/weather', data),
  // 財務計劃
  listFinancialPlans: (params?: { month?: string }) =>
    apiClient.get('/plans/financial', { params }),
  createFinancialPlan: (data: object) => apiClient.post('/plans/financial', data),
  updateFinancialPlan: (id: string, data: object) => apiClient.put(`/plans/financial/${id}`, data),
  financialVsActual: (month: string) => apiClient.get(`/plans/financial/${month}/vs-actual`),
};

// ─── WP8：每日摘要 API ─────────────────────────────────────

export const dailySummaryApi = {
  today: () => apiClient.get('/daily-summary/today'),
  history: (days?: number) => apiClient.get('/daily-summary/history', { params: days ? { days } : {} }),
  generate: () => apiClient.post('/daily-summary/generate'),
  // 告警規則
  listAlertRules: () => apiClient.get('/alert-rules'),
  createAlertRule: (data: object) => apiClient.post('/alert-rules', data),
  updateAlertRule: (id: string, data: object) => apiClient.put(`/alert-rules/${id}`, data),
  deleteAlertRule: (id: string) => apiClient.delete(`/alert-rules/${id}`),
};

// ─── Bloomberg 段：市場情報 API ────────────────────────────

export const marketIntelApi = {
  // 市場價格
  listPrices:       (params?: object) => apiClient.get('/market/prices/', { params }),
  createPrice:      (data: object)    => apiClient.post('/market/prices/', data),
  // 告警
  listAlerts:       (params?: object) => apiClient.get('/market/alerts/', { params }),
  acknowledgeAlert: (id: string)      => apiClient.post(`/market/alerts/${id}/acknowledge`),
  // 運費指數
  listFreight:      (params?: object) => apiClient.get('/market/freight/', { params }),
  createFreight:    (data: object)    => apiClient.post('/market/freight/', data),
  // 全球買家
  listBuyers:       (params?: object) => apiClient.get('/market/buyers/', { params }),
  createBuyer:      (data: object)    => apiClient.post('/market/buyers/', data),
  // 競爭對手
  listCompetitors:  (params?: object) => apiClient.get('/market/competitors/', { params }),
  createCompetitor: (data: object)    => apiClient.post('/market/competitors/', data),
  listCompetitorPrices: (params?: object) => apiClient.get('/market/competitor-prices/', { params }),
};

// ─── N 段：動態定價 API ────────────────────────────────────

export const pricingApi = {
  calculate:        (data: object)    => apiClient.post('/pricing/calculate', data),
  listPriceLists:   (params?: object) => apiClient.get('/pricing/price-lists', { params }),
  createPriceList:  (data: object)    => apiClient.post('/pricing/price-lists', data),
  getPriceList:     (id: string)      => apiClient.get(`/pricing/price-lists/${id}`),
  updatePriceList:  (id: string, data: object) => apiClient.put(`/pricing/price-lists/${id}`, data),
  listRules:        (params?: object) => apiClient.get('/pricing/rules', { params }),
  createRule:       (data: object)    => apiClient.post('/pricing/rules', data),
};

// ─── G 段：貿易文件 API ────────────────────────────────────

export const tradeDocsApi = {
  list:          (params?: object) => apiClient.get('/trade-documents/', { params }),
  create:        (data: object)    => apiClient.post('/trade-documents/', data),
  get:           (id: string)      => apiClient.get(`/trade-documents/${id}`),
  update:        (id: string, data: object) => apiClient.patch(`/trade-documents/${id}`, data),
  expiryAlerts:  (days?: number)   => apiClient.get('/trade-documents/expiry-alerts', { params: days ? { days } : {} }),
  // 信用狀
  listLC:        (params?: object) => apiClient.get('/trade-documents/letters-of-credit', { params }),
  createLC:      (data: object)    => apiClient.post('/trade-documents/letters-of-credit', data),
  // 提單
  listBL:        (params?: object) => apiClient.get('/trade-documents/bills-of-lading', { params }),
  createBL:      (data: object)    => apiClient.post('/trade-documents/bills-of-lading', data),
};

// ─── I 段：財務擴充 API ────────────────────────────────────

export const financeExtApi = {
  // 損益報表
  getPnl:           (year: number, month: number) => apiClient.get('/finance/pnl', { params: { year, month } }),
  getPnlTrend:      (months?: number) => apiClient.get('/finance/pnl/monthly-trend', { params: months ? { months } : {} }),
  getFxGainLoss:    (params?: object) => apiClient.get('/finance/fx-gain-loss', { params }),
  thaiTax:          (amount_thb: number) => apiClient.get('/finance/thai-tax', { params: { amount_thb } }),
  whtReport:        (params?: object) => apiClient.get('/finance/wht-report', { params }),
  // 零用金
  listPettyCashFunds:   (params?: object) => apiClient.get('/finance/petty-cash/funds', { params }),
  listPettyCashRecords: (params?: object) => apiClient.get('/finance/petty-cash/records', { params }),
  createPettyCashRecord:(data: object)    => apiClient.post('/finance/petty-cash/records', data),
  approvePettyCash:     (id: string)      => apiClient.post(`/finance/petty-cash/records/${id}/approve`),
  // 銀行帳戶
  listBankAccounts:     (params?: object) => apiClient.get('/finance/bank-accounts', { params }),
  listBankTransactions: (params?: object) => apiClient.get('/finance/bank-transactions', { params }),
};

// ─── J/K/L 段：合規管理 API ──────────────────────────────

export const complianceApi = {
  // 合約
  listContracts:    (params?: object) => apiClient.get('/compliance/contracts', { params }),
  createContract:   (data: object)    => apiClient.post('/compliance/contracts', data),
  getContract:      (id: string)      => apiClient.get(`/compliance/contracts/${id}`),
  // 公告
  listAnnouncements:(params?: object) => apiClient.get('/compliance/announcements', { params }),
  createAnnouncement:(data: object)   => apiClient.post('/compliance/announcements', data),
  // 會議記錄
  listMeetings:     (params?: object) => apiClient.get('/compliance/meetings', { params }),
  createMeeting:    (data: object)    => apiClient.post('/compliance/meetings', data),
  getMeeting:       (id: string)      => apiClient.get(`/compliance/meetings/${id}`),
  getMeetingActions:(id: string)      => apiClient.get(`/compliance/meetings/${id}/actions`),
};

// ─── H 段：物流擴充 API ───────────────────────────────────

export const logisticsExtApi = {
  // 車輛
  listVehicles:     (params?: object) => apiClient.get('/logistics/vehicles', { params }),
  createVehicle:    (data: object)    => apiClient.post('/logistics/vehicles', data),
  getVehicle:       (id: string)      => apiClient.get(`/logistics/vehicles/${id}`),
  updateVehicle:    (id: string, data: object) => apiClient.patch(`/logistics/vehicles/${id}`, data),
  listMaintenance:  (params?: object) => apiClient.get('/logistics/vehicle-maintenance', { params }),
  createMaintenance:(data: object)    => apiClient.post('/logistics/vehicle-maintenance', data),
  // 退貨
  listReturns:      (params?: object) => apiClient.get('/logistics/returns', { params }),
  createReturn:     (data: object)    => apiClient.post('/logistics/returns', data),
  updateReturn:     (id: string, data: object) => apiClient.patch(`/logistics/returns/${id}`, data),
};

// ─── CRM 進階 API ─────────────────────────────────────────

export const crmAdvancedApi = {
  // 業務排程
  listSchedules:    (params?: object) => apiClient.get('/crm/schedules', { params }),
  createSchedule:   (data: object)    => apiClient.post('/crm/schedules', data),
  updateSchedule:   (id: string, data: object) => apiClient.patch(`/crm/schedules/${id}`, data),
  // 商機
  listOpportunities:(params?: object) => apiClient.get('/crm/opportunities', { params }),
  createOpportunity:(data: object)    => apiClient.post('/crm/opportunities', data),
  updateOpportunity:(id: string, data: object) => apiClient.patch(`/crm/opportunities/${id}`, data),
  // 報價核准
  listApprovals:    (params?: object) => apiClient.get('/crm/quotation-approvals', { params }),
  decideApproval:   (id: string, data: object) => apiClient.post(`/crm/quotation-approvals/${id}/decide`, data),
  // 健康告警
  healthAlerts:     (params?: object) => apiClient.get('/crm/alerts/health-score', { params }),
  churnAlerts:      (params?: object) => apiClient.get('/crm/alerts/churn', { params }),
};
