"""
AI 智能分析 Celery 任务
"""
import json
import redis as redis_lib
from celery import current_task
from app.tasks.celery_app import celery_app
from app.database import get_session
from app.models.task import Task
from app.models.vulnerability import Vulnerability
from app.utils.llm_client import analyze_scan_results
from app.utils.logger import get_logger, TaskLogger


@celery_app.task(bind=True, queue="ai", max_retries=2, default_retry_delay=120)
def analyze_with_ai(self, task_id: str):
    """
    收集 task 下所有 Vulnerability 的 raw_result，
    合并后发送给 LLM 进行智能分析。
    将 AI 结果写回各 Vulnerability 记录。
    """
    logger = get_logger("ai")
    redis_client = redis_lib.from_url("redis://redis:6379/0", decode_responses=True)
    tlog = TaskLogger(task_id, redis_client)

    tlog.info(f"Starting AI analysis for task {task_id}")

    # 收集所有待分析的漏洞记录
    with get_session() as session:
        vulns = (
            session.query(Vulnerability)
            .filter(
                Vulnerability.task_id == task_id,
                Vulnerability.ai_analysis == None,  # 只分析未处理过的
            )
            .all()
        )

        task = session.query(Task).filter(Task.id == task_id).first()
        context = json.loads(task.context or "{}") if task else {}

    if not vulns:
        tlog.info("No unanalyzed vulnerabilities found")
        return {"task_id": task_id, "analyzed": 0}

    tlog.info(f"Analyzing {len(vulns)} vulnerability records")

    analyzed = 0
    for vuln in vulns:
        # 读取 strix 原始输出
        scan_summary = vuln.description or ""
        if vuln.raw_result:
            try:
                with open(vuln.raw_result, "r") as f:
                    raw = f.read()
                scan_summary = raw[:8000]  # 限制 token 长度
            except Exception:
                pass

        if not scan_summary.strip():
            continue

        # 调用 LLM
        ai_result = analyze_scan_results(scan_summary, context)

        # 存储 AI 结果
        with get_session() as session:
            v = session.query(Vulnerability).filter(Vulnerability.id == vuln.id).first()
            if v:
                v.ai_analysis = json.dumps(ai_result)

                # 如果有高危漏洞结果，更新 cve_id 和 risk_score
                high_risks = ai_result.get("high_risk_vulnerabilities", [])
                if high_risks:
                    cves = [h.get("cve") for h in high_risks if h.get("cve")]
                    scores = [h.get("risk_score", 0) for h in high_risks]
                    v.cve_id = ", ".join([c for c in cves if c])
                    v.risk_score = max(scores) if scores else None
                    v.remediation = "; ".join([
                        f"{h.get('cve', '')}: {h.get('remediation', '')}"
                        for h in high_risks
                    ])

                session.commit()

        analyzed += 1
        tlog.info(f"AI analysis complete for {vuln.domain}: {len(high_risks)} high-risk findings")

    tlog.info(f"AI analysis complete: {analyzed} records analyzed")
    return {"task_id": task_id, "analyzed": analyzed}
