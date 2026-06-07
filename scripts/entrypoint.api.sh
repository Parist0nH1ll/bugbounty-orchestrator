#!/bin/bash
set -e

echo "[entrypoint.api] Starting FastAPI server..."

# 初始化数据库
python3 /app/scripts/init_db.py

# 启动 uvicorn
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --log-level info
