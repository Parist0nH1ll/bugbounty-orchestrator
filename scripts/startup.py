"""
Digital Ocean 启动脚本
- 初始化数据库（失败不阻塞）
- 后台启动 FastAPI (8000)
- 前台启动 Streamlit ($PORT，DO 注入 8080)
"""
import os
import sys
import time
import subprocess
import threading


def init_database():
    """初始化数据库，超时 10 秒失败不阻塞"""
    try:
        subprocess.run(
            [sys.executable, "/app/scripts/init_db.py"],
            timeout=10,
            capture_output=True,
        )
        print("[startup] Database initialized")
    except Exception as e:
        print(f"[startup] Database init skipped: {e}")


def start_api():
    """后台启动 FastAPI"""
    subprocess.Popen(
        [
            sys.executable, "-m", "uvicorn", "app.main:app",
            "--host", "0.0.0.0", "--port", "8000",
            "--log-level", "warning",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    print("[startup] FastAPI started on :8000")


def start_streamlit():
    """前台启动 Streamlit"""
    port = os.getenv("PORT", "8080")
    print(f"[startup] Streamlit starting on :{port}")
    os.execvp("streamlit", [
        "streamlit", "run", "/app/streamlit_app.py",
        "--server.port", port,
        "--server.address", "0.0.0.0",
        "--server.headless", "true",
        "--browser.gatherUsageStats", "false",
    ])


if __name__ == "__main__":
    init_database()
    start_api()
    start_streamlit()
