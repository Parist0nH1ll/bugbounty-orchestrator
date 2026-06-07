"""
任务管理 API 端点 - 查询任务状态、取消任务、获取日志
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.task import Task
from app.schemas.schemas import TaskOut, TaskListOut
from app.tasks.workflow import cancel_pipeline
from app.utils.logger import get_logger

router = APIRouter(prefix="/api/tasks", tags=["tasks"])
logger = get_logger("api.tasks")


@router.get("/", response_model=TaskListOut)
async def list_tasks(
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """列出所有任务，支持状态过滤和分页"""
    query = db.query(Task)
    if status:
        query = query.filter(Task.status == status)

    total = query.count()
    tasks = query.order_by(Task.created_at.desc()).offset(offset).limit(limit).all()

    return TaskListOut(
        tasks=[TaskOut.model_validate(t) for t in tasks],
        total=total,
    )


@router.get("/{task_id}", response_model=TaskOut)
async def get_task(task_id: str, db: Session = Depends(get_db)):
    """获取单个任务详情"""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return TaskOut.model_validate(task)


@router.post("/{task_id}/cancel")
async def cancel_task(task_id: str, db: Session = Depends(get_db)):
    """取消任务"""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if task.status not in ("pending", "running"):
        raise HTTPException(status_code=400, detail=f"Cannot cancel task with status {task.status}")

    cancel_pipeline.delay(task_id)
    return {"task_id": task_id, "status": "cancelling"}
