"""
主流水线编排 - 将各步骤串联为完整的 Celery 任务链
支持取消和重试
"""
import json
import uuid
from datetime import datetime
from celery import chain, group, chord, current_task
import redis as redis_lib

from app.tasks.celery_app import celery_app
from app.database import get_session
from app.models.task import Task
from app.models.domain import Domain
from app.models.asset import Asset
from app.models.vulnerability import Vulnerability
from app.utils.logger import get_logger, TaskLogger

from app.tasks.subdomain import discover_subdomains
from app.tasks.dns_resolve import resolve_all_subdomains
from app.tasks.filter_assets import filter_key_assets
from app.tasks.strix_scan import scan_asset
from app.tasks.ai_analyze import analyze_with_ai


def _mark_task_failed(task_id: str, error: str):
    """标记任务失败"""
    try:
        with get_session() as session:
            task = session.query(Task).filter(Task.id == task_id).first()
            if task:
                task.status = "failed"
                task.error_message = error
                task.updated_at = datetime.utcnow()
                session.commit()
    except Exception:
        pass


def _broadcast_status(task_id: str, status: str, message: str):
    """通过 Redis pub/sub 广播任务状态"""
    try:
        r = redis_lib.from_url("redis://redis:6379/0", decode_responses=True)
        r.publish(f"task:{task_id}:status", json.dumps({
            "task_id": task_id,
            "status": status,
            "message": message,
            "timestamp": datetime.utcnow().isoformat(),
        }))
    except Exception:
        pass


# ==================== 回调任务 ====================

@celery_app.task(bind=True, queue="default")
def on_pipeline_success(self, results, task_id: str):
    """流水线成功完成时的回调"""
    logger = get_logger("pipeline")
    logger.info(f"Pipeline completed successfully for task {task_id}")

    with get_session() as session:
        task = session.query(Task).filter(Task.id == task_id).first()
        if task:
            task.status = "completed"
            task.progress = 100
            task.current_step = "done"
            task.updated_at = datetime.utcnow()

            # 刷新最终计数
            task.subdomains_count = session.query(Domain).filter(Domain.task_id == task_id).count()
            task.assets_count = session.query(Asset).filter(Asset.task_id == task_id).count()
            task.vulnerabilities_count = session.query(Vulnerability).filter(Vulnerability.task_id == task_id).count()
            session.commit()

    _broadcast_status(task_id, "completed", f"Task {task_id} completed successfully")


@celery_app.task(bind=True, queue="default")
def on_pipeline_error(self, request, exc, traceback, task_id: str):
    """流水线失败时的回调"""
    logger = get_logger("pipeline")
    logger.error(f"Pipeline failed for task {task_id}: {exc}")

    _mark_task_failed(task_id, str(exc))
    _broadcast_status(task_id, "failed", f"Task {task_id} failed: {exc}")


# ==================== 任务取消 ====================

@celery_app.task(bind=True, queue="default")
def cancel_pipeline(self, task_id: str):
    """取消指定任务的所有子任务"""
    logger = get_logger("pipeline")
    logger.info(f"Cancelling pipeline for task {task_id}")

    # 撤销该任务相关的所有排队任务
    inspector = self.app.control.inspect()
    active_queues = inspector.active() or {}
    reserved_queues = inspector.reserved() or {}
    scheduled_queues = inspector.scheduled() or {}

    all_tasks = {}
    all_tasks.update({t["id"]: t for ts in active_queues.values() for t in ts})
    all_tasks.update({t["id"]: t for ts in reserved_queues.values() for t in ts})
    all_tasks.update({t["id"]: t for ts in scheduled_queues.values() for t in ts})

    cancelled = 0
    for tid, tinfo in all_tasks.items():
        args_str = str(tinfo.get("args", ""))
        if task_id in args_str:
            self.app.control.revoke(tid, terminate=True)
            cancelled += 1

    with get_session() as session:
        task = session.query(Task).filter(Task.id == task_id).first()
        if task:
            task.status = "cancelled"
            task.current_step = "cancelled"
            task.updated_at = datetime.utcnow()
            session.commit()

    _broadcast_status(task_id, "cancelled", f"Task {task_id} cancelled ({cancelled} subtasks revoked)")
    return {"task_id": task_id, "cancelled": cancelled}


# ==================== 流水线启动 ====================

def launch_pipeline(task_id: str, domains: list[str]) -> str:
    """
    启动完整的漏洞挖掘流水线。
    返回 task_id。

    流水线流程：
    1. 并行子域名发现 (group)
    2. DNS 解析确认
    3. 重点资产筛选
    4. 并行 Strix 扫描 (group)
    5. AI 智能分析
    """
    logger = get_logger("pipeline")

    # 创建任务记录
    with get_session() as session:
        task = Task(
            id=task_id,
            status="running",
            progress=0,
            current_step="subdomain_discovery",
            domains_count=len(domains),
        )
        session.add(task)
        session.commit()

    _broadcast_status(task_id, "running", f"Pipeline launched with {len(domains)} domains")

    # Step 1: 并行子域名发现
    subdomain_tasks = group(
        discover_subdomains.s(task_id, domain)
        for domain in domains
    )

    # Step 2: DNS 解析 (在子域名发现之后)
    dns_task = resolve_all_subdomains.s(task_id)

    # Step 3: 重点资产筛选
    filter_task = filter_key_assets.s(task_id)

    # Step 4: 并行 Strix 扫描 (动态获取 asset ids)
    scan_task = _scan_all_assets.s(task_id)

    # Step 5: AI 分析
    ai_task = analyze_with_ai.s(task_id)

    # 构建链: subdomain -> dns -> filter -> scan -> ai
    pipeline = chain(
        subdomain_tasks,
        dns_task,
        filter_task,
        scan_task,
        ai_task,
    )

    # 应用回调
    pipeline.apply_async(
        link=on_pipeline_success.s(task_id=task_id),
        link_error=on_pipeline_error.s(task_id=task_id),
    )

    logger.info(f"Pipeline launched: task_id={task_id}, domains={domains}")
    return task_id


@celery_app.task(bind=True, queue="scan")
def _scan_all_assets(self, result, task_id: str):
    """
    内部任务：查询所有未扫描的重点资产，并行启动 strix 扫描。
    """
    logger = get_logger("pipeline")

    with get_session() as session:
        assets = (
            session.query(Asset)
            .filter(Asset.task_id == task_id, Asset.scanned == False)
            .all()
        )

    if not assets:
        logger.info(f"No assets to scan for task {task_id}")
        return {"task_id": task_id, "scanned": 0}

    asset_ids = [a.id for a in assets]
    logger.info(f"Launching parallel strix scans for {len(asset_ids)} assets (max concurrency controlled by worker --concurrency)")

    # 并行扫描：group 把 N 个 scan_asset 任务同时分发到 scan 队列
    # .apply_async().join() 确保所有扫描都完成后才返回，chain 才会继续到 AI 分析步骤
    scan_group = group(
        scan_asset.s(task_id, aid)
        for aid in asset_ids
    )
    result = scan_group.apply_async()
    result.join()  # 阻塞等待所有并行任务完成
    logger.info(f"All {len(asset_ids)} strix scans completed")
