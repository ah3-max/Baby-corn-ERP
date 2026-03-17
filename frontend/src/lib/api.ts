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

// ─── 角色 API ────────────────────────────────────────

export const rolesApi = {
  list: () => apiClient.get('/roles'),
  get: (id: string) => apiClient.get(`/roles/${id}`),
  create: (data: object) => apiClient.post('/roles', data),
  update: (id: string, data: object) => apiClient.put(`/roles/${id}`, data),
  delete: (id: string) => apiClient.delete(`/roles/${id}`),
  listPermissions: () => apiClient.get('/permissions'),
};
