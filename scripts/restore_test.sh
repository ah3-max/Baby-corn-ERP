#!/bin/bash
# =============================================================================
# 玉米筍ERP 備份還原驗證腳本
# 用法：bash scripts/restore_test.sh [備份檔路徑]
# 範例：bash scripts/restore_test.sh /backups/babycorn_erp_20260330_020000.sql.gz
# =============================================================================

set -euo pipefail

# ── 參數 ──────────────────────────────────────────────────────────────────────
BACKUP_FILE="${1:-}"
POSTGRES_HOST="${POSTGRES_HOST:-db}"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"
POSTGRES_USER="${POSTGRES_USER:-babycorn}"
TEST_DB="${POSTGRES_DB:-babycorn_erp}_restore_test"

if [ -z "${BACKUP_FILE}" ]; then
    # 未指定時，自動找最新備份
    BACKUP_DIR="${BACKUP_DIR:-/backups}"
    BACKUP_FILE=$(find "${BACKUP_DIR}" -name "babycorn_erp_*.sql.gz" | sort | tail -n 1)
    if [ -z "${BACKUP_FILE}" ]; then
        echo "[錯誤] 找不到備份檔案，請先執行 backup.sh"
        exit 1
    fi
fi

echo "[$(date '+%Y-%m-%d %H:%M:%S')] 還原驗證開始"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] 備份檔案：${BACKUP_FILE}"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] 測試資料庫：${TEST_DB}"

# ── 建立測試資料庫 ────────────────────────────────────────────────────────────
echo "[$(date '+%Y-%m-%d %H:%M:%S')] 建立測試資料庫..."
PGPASSWORD="${POSTGRES_PASSWORD}" psql \
    -h "${POSTGRES_HOST}" -p "${POSTGRES_PORT}" \
    -U "${POSTGRES_USER}" -d postgres \
    -c "DROP DATABASE IF EXISTS ${TEST_DB};" \
    -c "CREATE DATABASE ${TEST_DB};"

# ── 還原備份 ──────────────────────────────────────────────────────────────────
echo "[$(date '+%Y-%m-%d %H:%M:%S')] 還原備份中..."
gunzip -c "${BACKUP_FILE}" | PGPASSWORD="${POSTGRES_PASSWORD}" psql \
    -h "${POSTGRES_HOST}" -p "${POSTGRES_PORT}" \
    -U "${POSTGRES_USER}" -d "${TEST_DB}" \
    --quiet

# ── 驗證資料完整性 ────────────────────────────────────────────────────────────
echo "[$(date '+%Y-%m-%d %H:%M:%S')] 驗證資料完整性..."
PGPASSWORD="${POSTGRES_PASSWORD}" psql \
    -h "${POSTGRES_HOST}" -p "${POSTGRES_PORT}" \
    -U "${POSTGRES_USER}" -d "${TEST_DB}" \
    -c "SELECT
        (SELECT COUNT(*) FROM batches)       AS batches,
        (SELECT COUNT(*) FROM inventory_lots) AS inventory_lots,
        (SELECT COUNT(*) FROM sales_orders)   AS sales_orders,
        (SELECT COUNT(*) FROM cost_events)    AS cost_events,
        (SELECT COUNT(*) FROM users)          AS users;"

# ── 清除測試資料庫 ────────────────────────────────────────────────────────────
echo "[$(date '+%Y-%m-%d %H:%M:%S')] 清除測試資料庫..."
PGPASSWORD="${POSTGRES_PASSWORD}" psql \
    -h "${POSTGRES_HOST}" -p "${POSTGRES_PORT}" \
    -U "${POSTGRES_USER}" -d postgres \
    -c "DROP DATABASE IF EXISTS ${TEST_DB};"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] ✅ 還原驗證成功，備份檔案可正常還原"
