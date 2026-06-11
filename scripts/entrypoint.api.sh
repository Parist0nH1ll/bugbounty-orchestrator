#!/bin/bash
set -e

echo "[entrypoint.api] Starting FastAPI server..."

# 初始化数据库
python3 /app/scripts/init_db.py

# 启动 uvicorn
# Digital Ocean App Platform 自动注入 $PORT=8080
# Docker Compose / 本地默认 8000
PORT="${PORT:-8000}"
echo "[entrypoint.api] Listening on port $PORT"
exec uvicorn app.main:app --host 0.0.0.0 --port "$PORT" --log-level info
