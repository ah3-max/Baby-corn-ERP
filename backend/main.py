"""
FastAPI 應用程式入口
"""
import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from routers import (
    auth, users, roles, suppliers, purchases, batches, qc, shipments,
    customers, sales, analytics, costs, inventory, daily_sales,
    oem_factories, processing, payments, notifications,
    attachments, exchange_rates, system_settings,
)
from config import settings
from database import Base, engine
from migrations import run_migrations
import models  # noqa: F401 – 確保所有 Model 都已載入，Base.metadata 才完整

app = FastAPI(
    title="玉米筍跨境供應鏈 ERP",
    description="Baby Corn Cross-Border Supply Chain ERP System",
    version="1.0.0",
)


@app.on_event("startup")
def on_startup():
    """建立尚未存在的資料表，並執行 schema 遷移（新增欄位）"""
    Base.metadata.create_all(bind=engine, checkfirst=True)
    run_migrations(engine)

# ─── CORS 設定 ────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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


# ─── 靜態檔案：上傳目錄對外開放 ───────────────────────
# 確保上傳根目錄存在，避免 StaticFiles 啟動時報錯
_upload_dir = Path(settings.UPLOAD_DIR)
_upload_dir.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(_upload_dir)), name="uploads")


@app.get("/")
def root():
    return {"message": "Baby Corn ERP API is running", "version": "1.0.0"}


@app.get("/health")
def health_check():
    return {"status": "ok"}
