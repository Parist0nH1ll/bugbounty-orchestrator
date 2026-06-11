"""
应用配置 - 从环境变量加载，并提供全局配置对象
"""
import os
from pathlib import Path
from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    # --- 数据库 ---
    database_url: str = "sqlite:///./data/orchestrator.db"

    # --- Redis / Celery ---
    redis_url: str = "redis://redis:6379/0"
    celery_broker_url: str = "redis://redis:6379/1"
    celery_result_backend: str = "redis://redis:6379/2"

    # --- LLM ---
    llm_api_base: str = "https://api.openai.com/v1"
    llm_api_key: str = "sk-your-key-here"
    llm_model: str = "gpt-4o"

    # --- 工具路径 ---
    subfinder_path: str = "/usr/local/bin/subfinder"
    strix_path: str = "strix"  # pip install strix-agent 后命令名为 strix
    naabu_path: str = "/usr/local/bin/naabu"

    # --- Strix LLM 配置（如果不设置则复用项目 LLM 配置）---
    strix_llm: str = ""  # 格式: openai/gpt-4o, 留空则自动复用 llm_model

    # --- 超时 ---
    subdomain_timeout: int = 600
    dns_resolve_timeout: int = 300
    strix_scan_timeout: int = 7200
    port_scan_timeout: int = 300
    ai_analysis_timeout: int = 300

    # --- 并发 ---
    dns_concurrency: int = 50
    subdomain_concurrency: int = 5

    # --- Web ---
    api_port: int = 8000
    frontend_port: int = 80
    streamlit_port: int = 8501
    web_password: str = ""  # 留空不启用密码，设置后前端/API 都需要此密码

    # --- 路径 ---
    data_dir: str = "./data"
    scan_results_dir: str = "./scan_results"
    output_dir: str = "./output"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
