#!/bin/bash
set -e

echo "[entrypoint.worker] Starting Celery worker..."

# 确保数据目录存在
mkdir -p /app/data /app/scan_results /app/output

# 初始化数据库
python3 /app/scripts/init_db.py

# 启动 Celery worker（并发数可通过 CELERY_CONCURRENCY 环境变量覆盖，默认 8）
# 对于 Strix 扫描密集型任务，建议设置 4-8 并发，确保每个扫描任务有足够资源
CONCURRENCY=${CELERY_CONCURRENCY:-8}
echo "[entrypoint.worker] Starting Celery worker with concurrency=${CONCURRENCY}..."

exec celery -A app.tasks.celery_app worker \
    --loglevel=info \
    --concurrency=${CONCURRENCY} \
    -Q default,subdomain,dns,scan,ai
