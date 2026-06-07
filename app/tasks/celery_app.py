"""
Celery 应用配置
"""
from celery import Celery
from app.config import settings

celery_app = Celery(
    "orchestrator",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "app.tasks.workflow",
        "app.tasks.subdomain",
        "app.tasks.dns_resolve",
        "app.tasks.filter_assets",
        "app.tasks.strix_scan",
        "app.tasks.ai_analyze",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    result_expires=86400 * 7,  # 结果保留 7 天
    task_default_queue="default",
    task_queues={
        "default": {"exchange": "default", "routing_key": "default"},
        "subdomain": {"exchange": "subdomain", "routing_key": "subdomain"},
        "dns": {"exchange": "dns", "routing_key": "dns"},
        "scan": {"exchange": "scan", "routing_key": "scan"},
        "ai": {"exchange": "ai", "routing_key": "ai"},
    },
)
