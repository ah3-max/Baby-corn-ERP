#!/bin/bash
# =============================================================================
# 玉米筍ERP 資料庫備份腳本
# 用法：
#   手動執行：bash scripts/backup.sh
#   Docker 內執行：由 backup service 的 crond 每日 02:00 自動呼叫
# =============================================================================

set -euo pipefail

# ── 設定 ──────────────────────────────────────────────────────────────────────
BACKUP_DIR="${BACKUP_DIR:-/backups}"
POSTGRES_HOST="${POSTGRES_HOST:-db}"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"
POSTGRES_USER="${POSTGRES_USER:-babycorn}"
POSTGRES_DB="${POSTGRES_DB:-babycorn_erp}"
BACKUP_KEEP_DAYS="${BACKUP_KEEP_DAYS:-7}"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="${BACKUP_DIR}/babycorn_erp_${TIMESTAMP}.sql.gz"

# ── 建立備份目錄 ──────────────────────────────────────────────────────────────
mkdir -p "${BACKUP_DIR}"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] 開始備份資料庫 ${POSTGRES_DB}..."

# ── 執行備份 ──────────────────────────────────────────────────────────────────
PGPASSWORD="${POSTGRES_PASSWORD}" pg_dump \
    -h "${POSTGRES_HOST}" \
    -p "${POSTGRES_PORT}" \
    -U "${POSTGRES_USER}" \
    -d "${POSTGRES_DB}" \
    --no-password \
    --format=plain \
    --verbose \
    | gzip -9 > "${BACKUP_FILE}"

BACKUP_SIZE=$(du -sh "${BACKUP_FILE}" | cut -f1)
echo "[$(date '+%Y-%m-%d %H:%M:%S')] 備份完成：${BACKUP_FILE}（${BACKUP_SIZE}）"

# ── 清除過期備份 ──────────────────────────────────────────────────────────────
echo "[$(date '+%Y-%m-%d %H:%M:%S')] 清除超過 ${BACKUP_KEEP_DAYS} 天的舊備份..."
find "${BACKUP_DIR}" -name "babycorn_erp_*.sql.gz" -mtime "+${BACKUP_KEEP_DAYS}" -delete
REMAINING=$(find "${BACKUP_DIR}" -name "babycorn_erp_*.sql.gz" | wc -l | tr -d ' ')
echo "[$(date '+%Y-%m-%d %H:%M:%S')] 目前保留 ${REMAINING} 個備份檔案"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] 備份程序結束"
