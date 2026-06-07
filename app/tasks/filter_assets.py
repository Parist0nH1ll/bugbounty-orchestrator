"""
重点资产筛选 Celery 任务
"""
import json
import re
import redis as redis_lib
from celery import current_task
from sqlalchemy import and_
from app.tasks.celery_app import celery_app
from app.database import get_session
from app.models.task import Task
from app.models.domain import Domain
from app.models.asset import Asset
from app.models.rule import FilterRule
from app.utils.logger import get_logger, TaskLogger


@celery_app.task(bind=True, queue="dns", max_retries=1)
def filter_key_assets(self, task_id: str):
    """
    根据筛选规则从已解析子域名中筛选重点资产。
    规则从 filter_rules 表读取，支持 keyword 和 regex。
    """
    logger = get_logger("filter")
    redis_client = redis_lib.from_url("redis://redis:6379/0", decode_responses=True)
    tlog = TaskLogger(task_id, redis_client)

    tlog.info(f"Starting asset filtering for task {task_id}")

    # 获取启用的规则
    with get_session() as session:
        rules = (
            session.query(FilterRule)
            .filter(FilterRule.enabled == True)
            .order_by(FilterRule.priority.desc())
            .all()
        )

        # 获取已解析的域名
        resolved_domains = (
            session.query(Domain)
            .filter(Domain.task_id == task_id, Domain.is_resolved == True)
            .all()
        )

        if not rules:
            tlog.warning("No filter rules configured! Using all resolved domains.")
            return {"task_id": task_id, "assets_count": 0}

        tlog.info(f"Applying {len(rules)} rules to {len(resolved_domains)} resolved domains")

        assets = []
        for domain_record in resolved_domains:
            subdomain_lower = domain_record.subdomain.lower()
            matched_rules = []
            priority = 0

            for rule in rules:
                matched = False
                if rule.rule_type == "keyword":
                    if rule.pattern.lower() in subdomain_lower:
                        matched = True
                elif rule.rule_type == "regex":
                    try:
                        if re.search(rule.pattern, subdomain_lower, re.IGNORECASE):
                            matched = True
                    except re.error:
                        tlog.warning(f"Invalid regex rule: {rule.pattern}")

                if matched:
                    matched_rules.append(rule.name)
                    priority = max(priority, rule.priority)

            if matched_rules:
                ips = json.loads(domain_record.resolved_ips or "[]")
                asset = Asset(
                    task_id=task_id,
                    domain=domain_record.subdomain,
                    ips=json.dumps(ips),
                    priority=priority,
                    matched_rules=json.dumps(matched_rules),
                )
                assets.append(asset)

        if assets:
            session.add_all(assets)

            # 更新任务计数
            task = session.query(Task).filter(Task.id == task_id).first()
            if task:
                total = session.query(Asset).filter(Asset.task_id == task_id).count()
                task.assets_count = total

            session.commit()

        tlog.info(f"Asset filtering complete: {len(assets)} key assets identified")
        return {"task_id": task_id, "assets_count": len(assets)}
