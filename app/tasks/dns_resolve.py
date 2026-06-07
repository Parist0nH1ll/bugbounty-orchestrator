"""
DNS 解析确认 Celery 任务
"""
import json
import asyncio
import redis as redis_lib
from celery import current_task
from app.tasks.celery_app import celery_app
from app.database import get_session
from app.models.task import Task
from app.models.domain import Domain, DNSRecord
from app.utils.dns_utils import resolve_subdomains
from app.utils.logger import get_logger, TaskLogger


@celery_app.task(bind=True, queue="dns", max_retries=1)
def resolve_all_subdomains(self, task_id: str):
    """
    对 task_id 关联的所有未解析子域名进行 DNS 解析。
    更新 domains.is_resolved 和 resolved_ips，
    写入 dns_records 表。
    """
    logger = get_logger("dns")
    redis_client = redis_lib.from_url("redis://redis:6379/0", decode_responses=True)
    tlog = TaskLogger(task_id, redis_client)

    tlog.info(f"Starting DNS resolution for task {task_id}")

    # 批量取出待解析子域名
    with get_session() as session:
        domains = (
            session.query(Domain)
            .filter(Domain.task_id == task_id, Domain.is_resolved == False)
            .all()
        )
        subdomain_list = [d.subdomain for d in domains]

    if not subdomain_list:
        tlog.info("No unresolved subdomains found")
        return {"task_id": task_id, "resolved": 0, "failed": 0}

    tlog.info(f"Resolving {len(subdomain_list)} subdomains")

    # 在同步 Celery 任务中运行异步 DNS 解析
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        resolved, failed = loop.run_until_complete(resolve_subdomains(subdomain_list))
    finally:
        loop.close()

    # 写入数据库
    with get_session() as session:
        # 更新成功解析的域名
        resolved_map = {r["subdomain"]: r for r in resolved}
        domains_to_update = session.query(Domain).filter(
            Domain.subdomain.in_(list(resolved_map.keys()))
        ).all()

        for d in domains_to_update:
            d.is_resolved = True
            d.resolved_ips = json.dumps(resolved_map[d.subdomain]["ips"])

            # 写入 DNS 记录
            for rec in resolved_map[d.subdomain]["records"]:
                dns_rec = DNSRecord(
                    task_id=task_id,
                    subdomain=d.subdomain,
                    record_type=rec["type"],
                    value=rec["value"],
                )
                session.add(dns_rec)

        session.commit()

    tlog.info(f"DNS resolution complete: {len(resolved)} resolved, {len(failed)} failed")
    return {"task_id": task_id, "resolved": len(resolved), "failed": len(failed)}
