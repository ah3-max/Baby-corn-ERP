"""
FastAPI 應用程式入口
"""
import logging
import logging.config
from pathlib import Path
from fastapi import FastAPI, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.orm import Session
from sqlalchemy import text

# ─── Logging 設定 ────────────────────────────────────────
logging.config.dictConfig({
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s %(levelname)s %(name)s %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "erp.access": {"level": "INFO", "propagate": True},
        "sqlalchemy.engine": {"level": "WARNING", "propagate": True},  # 靜音 SQL 查詢
    },
})

logger = logging.getLogger(__name__)

from routers import (
    auth, users, roles, suppliers, purchases, batches, qc, shipments,
    customers, sales, analytics, costs, inventory, daily_sales,
    oem_factories, processing, payments, notifications,
    attachments, exchange_rates, system_settings, product_types, invoices,
    qc_enhanced, temperature_logs,  # WP2：QC 品質管理強化
    crm,  # WP3：業務 CRM
    delivery_orders, outbound_orders,  # WP4：物流派遣
    finance_ar, finance_ap,  # WP5：財務
    inventory_analytics,  # WP6：庫存分析
    planning,  # WP7：計劃
    daily_summary,  # WP8：每日摘要
)
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from config import settings
from database import Base, engine, get_db
from migrations import run_migrations
from utils.limiter import limiter
from middleware.request_id import RequestIDMiddleware
import models  # noqa: F401 – 確保所有 Model 都已載入，Base.metadata 才完整

# ─── FastAPI 應用程式建立 ─────────────────────────────────
# 正式環境關閉 Swagger UI，避免暴露 API 結構
app = FastAPI(
    title="玉米筍跨境供應鏈 ERP",
    description="Baby Corn Cross-Border Supply Chain ERP System",
    version="1.0.0",
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
    openapi_url="/openapi.json" if not settings.is_production else None,
)

# ─── Rate Limiting（slowapi）────────────────────────────
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)


# ─── 全域例外處理器 ────────────────────────────────────────
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Pydantic 驗證失敗 → 統一 422 JSON 格式，不洩漏內部 traceback"""
    return JSONResponse(
        status_code=422,
        content={
            "error": "validation_error",
            "detail": exc.errors(),
            "message": "請求資料格式錯誤，請檢查輸入欄位",
        },
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """未捕捉的例外 → 正式環境隱藏細節，開發環境顯示訊息"""
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    if settings.is_production:
        content = {"error": "internal_server_error", "message": "伺服器發生錯誤，請聯絡管理員"}
    else:
        content = {"error": "internal_server_error", "message": str(exc), "type": type(exc).__name__}
    return JSONResponse(status_code=500, content=content)


@app.on_event("startup")
def on_startup():
    """建立尚未存在的資料表，並執行 schema 遷移（新增欄位）"""
    Base.metadata.create_all(bind=engine, checkfirst=True)
    run_migrations(engine)
    # WP8：啟動排程引擎
    from scheduler import start_scheduler
    start_scheduler()


@app.on_event("shutdown")
def on_shutdown():
    """停止排程引擎"""
    from scheduler import stop_scheduler
    stop_scheduler()


# ─── Request ID + Access Log Middleware ──────────────────
app.add_middleware(RequestIDMiddleware)

# ─── CORS 設定（從環境變數讀取，不 hardcode）────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
)

# ─── 路由註冊 ─────────────────────────────────────────
app.include_router(auth.router,      prefix="/api/v1")
app.include_router(users.router,     prefix="/api/v1")
app.include_router(roles.router,     prefix="/api/v1")
app.include_router(suppliers.router, prefix="/api/v1")
app.include_router(purchases.router, prefix="/api/v1")
app.include_router(batches.router,   prefix="/api/v1")
app.include_router(qc.router,        prefix="/api/v1")
app.include_router(shipments.router, prefix="/api/v1")
app.include_router(customers.router, prefix="/api/v1")
app.include_router(sales.router,     prefix="/api/v1")
app.include_router(analytics.router, prefix="/api/v1")
app.include_router(costs.router,           prefix="/api/v1")
app.include_router(inventory.router,       prefix="/api/v1")
app.include_router(oem_factories.router,   prefix="/api/v1")
app.include_router(processing.router,      prefix="/api/v1")
app.include_router(payments.router,        prefix="/api/v1")
app.include_router(notifications.router,   prefix="/api/v1")
app.include_router(attachments.router,     prefix="/api/v1")
app.include_router(exchange_rates.router,  prefix="/api/v1")
app.include_router(daily_sales.router,     prefix="/api/v1")
app.include_router(system_settings.router, prefix="/api/v1")
app.include_router(product_types.router,  prefix="/api/v1")
app.include_router(invoices.router,       prefix="/api/v1")
# WP2：QC 品質管理強化
app.include_router(qc_enhanced.router,        prefix="/api/v1")
app.include_router(temperature_logs.router,   prefix="/api/v1")
# WP3：業務 CRM
app.include_router(crm.router,                prefix="/api/v1")
# WP4：物流派遣
app.include_router(delivery_orders.router,    prefix="/api/v1")
app.include_router(outbound_orders.router,    prefix="/api/v1")
# WP5：財務
app.include_router(finance_ar.router,         prefix="/api/v1")
app.include_router(finance_ap.router,         prefix="/api/v1")
# WP6：庫存分析
app.include_router(inventory_analytics.router, prefix="/api/v1")
# WP7：計劃
app.include_router(planning.router,            prefix="/api/v1")
# WP8：每日摘要
app.include_router(daily_summary.router,       prefix="/api/v1")


# ─── 靜態檔案：/uploads 已移除公開掛載（P0-5）─────────────
# 上傳目錄僅供後端讀寫，前端透過 /api/v1/attachments/{id}/download 存取
_upload_dir = Path(settings.UPLOAD_DIR)
_upload_dir.mkdir(parents=True, exist_ok=True)


@app.get("/")
def root():
    return {"message": "Baby Corn ERP API is running", "version": "1.0.0"}


@app.get("/health")
def health_check(db: Session = Depends(get_db)):
    """健康檢查端點，同時驗證 DB 連線"""
    try:
        db.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception:
        db_status = "error"

    status = "ok" if db_status == "ok" else "degraded"
    http_status = 200 if db_status == "ok" else 503
    return JSONResponse(
        status_code=http_status,
        content={
            "status": status,
            "database": db_status,
            "env": settings.ENV,
            "version": "1.0.0",
        },
    )
