"""
子域名发现 Celery 任务
"""
import json
from celery import current_task
from app.tasks.celery_app import celery_app
from app.database import get_session
from app.models.task import Task
from app.models.domain import Domain
from app.utils.subfinder_wrapper import run_subfinder
from app.utils.logger import get_logger, TaskLogger
import redis as redis_lib


def _update_progress(task_id: str, progress: int, step: str, message: str):
    """更新 Celery 任务状态和数据库 Task 进度"""
    current_task.update_state(
        state="PROGRESS",
        meta={"progress": progress, "step": step, "message": message},
    )
    try:
        with get_session() as session:
            task = session.query(Task).filter(Task.id == task_id).first()
            if task:
                task.progress = progress
                task.current_step = step
                from datetime import datetime
                task.updated_at = datetime.utcnow()
                session.commit()
    except Exception:
        pass


@celery_app.task(bind=True, queue="subdomain", max_retries=2, default_retry_delay=60)
def discover_subdomains(self, task_id: str, domain: str):
    """
    对单个根域名执行子域名发现。
    结果写入数据库 domains 表。
    """
    logger = get_logger("subdomain")
    redis_client = redis_lib.from_url("redis://redis:6379/0", decode_responses=True)
    tlog = TaskLogger(task_id, redis_client)

    tlog.info(f"Starting subdomain discovery for {domain}")

    try:
        subdomains = run_subfinder(domain)
    except Exception as exc:
        tlog.error(f"Subfinder failed for {domain}: {exc}")
        raise self.retry(exc=exc)

    if not subdomains:
        tlog.warning(f"No subdomains found for {domain}")
        return {"task_id": task_id, "domain": domain, "count": 0}

    # 批量写入数据库
    with get_session() as session:
        count = 0
        for subdomain in subdomains:
            existing = session.query(Domain).filter(Domain.subdomain == subdomain).first()
            if existing:
                continue
            rec = Domain(
                task_id=task_id,
                root_domain=domain,
                subdomain=subdomain,
                source="subfinder",
            )
            session.add(rec)
            count += 1

        # 更新任务的子域名计数
        task = session.query(Task).filter(Task.id == task_id).first()
        if task:
            from sqlalchemy import func
            total = session.query(func.count(Domain.id)).filter(Domain.task_id == task_id).scalar()
            task.subdomains_count = total or 0
            session.commit()

    tlog.info(f"Subdomain discovery complete for {domain}: {count} new subdomains found")
    return {"task_id": task_id, "domain": domain, "count": count}
