"""
FastAPI 应用入口
整合所有 API 路由、WebSocket、CORS、静态文件
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db
from app.api.websocket import router as ws_router
from app.api.endpoints.upload import router as upload_router
from app.api.endpoints.task import router as task_router
from app.api.endpoints.report import router as report_router
from app.api.endpoints.rules import router as rules_router
from app.api.endpoints.agent import router as agent_router
from app.utils.logger import get_logger

logger = get_logger("app.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动时初始化数据库"""
    logger.info("Starting orchestrator API server...")
    init_db()
    logger.info("Database initialized")
    yield
    logger.info("Shutting down API server...")


app = FastAPI(
    title="AI 漏洞挖掘平台",
    description="全自动子域名发现 → DNS 解析 → 资产筛选 → Strix 扫描 → AI 分析流水线",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(ws_router)
app.include_router(upload_router)
app.include_router(task_router)
app.include_router(report_router)
app.include_router(rules_router)
app.include_router(agent_router)


@app.get("/")
async def root():
    """健康检查"""
    return {
        "service": "AI Vulnerability Orchestrator",
        "version": "1.0.0",
        "status": "running",
    }


@app.get("/health")
async def health():
    """健康检查端点"""
    return {"status": "ok"}
