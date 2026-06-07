"""
文件上传 API 端点 - 接收域名列表文件并启动任务
"""
import uuid
from fastapi import APIRouter, UploadFile, File, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.schemas import DomainUploadRequest
from app.tasks.workflow import launch_pipeline
from app.utils.logger import get_logger

router = APIRouter(prefix="/api/upload", tags=["upload"])
logger = get_logger("api.upload")


@router.post("/domains", response_model=DomainUploadRequest)
async def upload_domains(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    上传域名列表文件（每行一个根域名），启动漏洞挖掘流水线。

    文件格式示例：
    ```
    example.com
    test.com
    myapp.cn
    ```
    """
    # 读取并解析域名
    content = await file.read()
    text = content.decode("utf-8", errors="ignore")

    # 提取域名行（过滤空行和注释）
    domains = []
    for line in text.splitlines():
        line = line.strip().lower()
        if not line or line.startswith("#"):
            continue
        # 简单校验：不含协议前缀和路径
        if "://" in line:
            line = line.split("://")[1].split("/")[0]
        domains.append(line)

    if not domains:
        return DomainUploadRequest(
            task_id="",
            domains_count=0,
            message="No valid domains found in file",
        )

    # 去重
    domains = sorted(set(domains))

    # 生成任务 ID 并启动流水线
    task_id = str(uuid.uuid4())[:8]
    launch_pipeline(task_id, domains)

    logger.info(f"Uploaded {len(domains)} domains, task_id={task_id}")

    return DomainUploadRequest(
        task_id=task_id,
        domains_count=len(domains),
        message=f"Task {task_id} started with {len(domains)} domains",
    )
