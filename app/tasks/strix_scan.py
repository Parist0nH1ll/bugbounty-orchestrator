"""
Strix 扫描 Celery 任务
"""
import json
import redis as redis_lib
from celery import current_task
from app.tasks.celery_app import celery_app
from app.database import get_session
from app.models.task import Task
from app.models.asset import Asset
from app.models.vulnerability import Vulnerability
from app.utils.strix_wrapper import run_strix_scan, extract_vulnerability_summary
from app.utils.logger import get_logger, TaskLogger


@celery_app.task(bind=True, queue="scan", max_retries=1, default_retry_delay=300)
def scan_asset(self, task_id: str, asset_id: int):
    """
    对单个重点资产执行 strix 扫描。
    扫描结果存入 vulnerabilities 表，标记 asset.scanned = True。
    """
    logger = get_logger("strix")
    redis_client = redis_lib.from_url("redis://redis:6379/0", decode_responses=True)
    tlog = TaskLogger(task_id, redis_client)

    # 获取资产信息
    with get_session() as session:
        asset = session.query(Asset).filter(Asset.id == asset_id).first()
        if not asset:
            tlog.error(f"Asset {asset_id} not found")
            return {"error": "asset_not_found", "asset_id": asset_id}

        if asset.scanned:
            tlog.info(f"Asset {asset.domain} already scanned, skipping")
            return {"task_id": task_id, "asset_id": asset_id, "status": "skipped"}

        target = asset.domain
        tlog.info(f"Starting strix scan for {target}")

        # 读取动态策略
        task = session.query(Task).filter(Task.id == task_id).first()
        context = json.loads(task.context or "{}") if task else {}

    # 执行扫描
    try:
        result = run_strix_scan(target, task_id, context)
    except Exception as exc:
        tlog.error(f"Strix scan failed for {target}: {exc}")
        return {"task_id": task_id, "asset_id": asset_id, "status": "failed", "error": str(exc)}

    # 提取摘要并存储
    summary = extract_vulnerability_summary(result.get("stdout", ""))

    with get_session() as session:
        vuln = Vulnerability(
            task_id=task_id,
            asset_id=asset_id,
            domain=target,
            raw_result=result.get("output_file"),
            cve_id=", ".join(summary.get("cves", [])) if summary.get("cves") else None,
            description=summary.get("raw_summary", ""),
        )
        session.add(vuln)

        # 标记已扫描
        asset = session.query(Asset).filter(Asset.id == asset_id).first()
        if asset:
            asset.scanned = True

        # 更新漏洞计数
        task = session.query(Task).filter(Task.id == task_id).first()
        if task:
            total = session.query(Vulnerability).filter(Vulnerability.task_id == task_id).count()
            task.vulnerabilities_count = total

        session.commit()

    tlog.info(f"Strix scan complete for {target}: {summary.get('vulnerability_count', 0)} vulns found")
    return {"task_id": task_id, "asset_id": asset_id, "vuln_count": summary.get("vulnerability_count", 0)}
