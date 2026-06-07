"""
漏洞报告 API 端点 - 查看、导出高危漏洞
"""
import json
import csv
import io
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.task import Task
from app.models.vulnerability import Vulnerability
from app.schemas.schemas import VulnerabilityOut, ReportOut
from app.utils.logger import get_logger

router = APIRouter(prefix="/api/reports", tags=["reports"])
logger = get_logger("api.reports")


@router.get("/{task_id}", response_model=ReportOut)
async def get_report(task_id: str, db: Session = Depends(get_db)):
    """获取任务的完整漏洞报告"""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    vulns = (
        db.query(Vulnerability)
        .filter(Vulnerability.task_id == task_id)
        .all()
    )

    # 从 AI 分析中提取 summary
    summary = "No AI analysis performed"
    for v in vulns:
        if v.ai_analysis:
            try:
                ai_data = json.loads(v.ai_analysis)
                summary = ai_data.get("summary", summary)
                break
            except json.JSONDecodeError:
                pass

    # 获取域名列表
    from app.models.domain import Domain
    domains = [
        d[0] for d in
        db.query(Domain.root_domain).filter(Domain.task_id == task_id).distinct().all()
    ]

    return ReportOut(
        task_id=task_id,
        domains=domains,
        vulnerabilities=[VulnerabilityOut.model_validate(v) for v in vulns],
        summary=summary,
        generated_at=task.updated_at,
    )


@router.get("/{task_id}/high-risk")
async def get_high_risk_vulns(
    task_id: str,
    min_score: float = Query(7.0, description="Minimum CVSS score"),
    db: Session = Depends(get_db),
):
    """获取指定任务的高危漏洞列表"""
    vulns = (
        db.query(Vulnerability)
        .filter(
            Vulnerability.task_id == task_id,
            Vulnerability.risk_score >= min_score,
        )
        .order_by(Vulnerability.risk_score.desc())
        .all()
    )
    return [VulnerabilityOut.model_validate(v) for v in vulns]


@router.get("/{task_id}/export")
async def export_report_csv(task_id: str, db: Session = Depends(get_db)):
    """导出漏洞报告为 CSV 文件"""
    vulns = (
        db.query(Vulnerability)
        .filter(Vulnerability.task_id == task_id)
        .order_by(Vulnerability.risk_score.desc())
        .all()
    )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["CVE", "Risk Score", "Domain", "Affected Component", "Description", "Remediation"])
    for v in vulns:
        writer.writerow([
            v.cve_id or "N/A",
            v.risk_score or "",
            v.domain or "",
            v.affected_component or "",
            v.description or "",
            v.remediation or "",
        ])

    output.seek(0)
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode("utf-8")),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=report_{task_id}.csv"},
    )
