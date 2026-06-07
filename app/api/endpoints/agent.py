"""
Agent Prompt 交互相应 API
接收用户自然语言指令，解析并更新任务的动态策略 (task_context)
"""
import json
import re
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.task import Task
from app.schemas.schemas import AgentCommand, AgentResponse
from app.utils.logger import get_logger

router = APIRouter(prefix="/api/agent", tags=["agent"])
logger = get_logger("api.agent")


def parse_prompt(prompt: str) -> list[str]:
    """
    解析用户自然语言 prompt，提取可执行的指令。
    当前实现：简单关键词匹配，后续可扩展为 LLM 解析。
    返回：解析出的操作列表。
    """
    prompt_lower = prompt.lower()
    actions = []

    # 忽略特定服务类漏洞
    ignore_map = {
        "redis": ("ignore", "skip_redis"),
        "mysql": ("ignore", "skip_mysql"),
        "mongodb": ("ignore", "skip_mongodb"),
        "postgresql": ("ignore", "skip_postgres"),
        "elasticsearch": ("ignore", "skip_elasticsearch"),
    }

    for keyword, (action_type, flag) in ignore_map.items():
        if keyword in prompt_lower and ("忽略" in prompt or "跳过" in prompt or "skip" in prompt_lower or "ignore" in prompt_lower):
            actions.append(f"set_context:{flag}=true")

    # 增加测试深度
    depth_match = re.search(r"深度[\s：:=]*(\d+)", prompt)
    if depth_match:
        depth = int(depth_match.group(1))
        actions.append(f"set_context:depth={depth}")

    # SQL 注入深度
    if "sql" in prompt_lower and ("深度" in prompt or "增加" in prompt or "测试" in prompt):
        actions.append("set_context:sql_injection_deep=true")

    # 重新分析
    if "重新分析" in prompt or "再次分析" in prompt:
        actions.append("action:re_analyze")

    # 认证绕过
    if "认证绕过" in prompt or "authentication bypass" in prompt_lower:
        actions.append("set_context:focus_auth_bypass=true")

    if not actions:
        actions.append("note:prompt_parsed_no_actions")

    return actions


def apply_context_updates(task: Task, actions: list[str]):
    """将解析出的操作应用到 task.context"""
    context = json.loads(task.context or "{}")

    for action in actions:
        if action.startswith("set_context:"):
            kv = action.split("set_context:")[1]
            if "=" in kv:
                key, value = kv.split("=", 1)
                # 类型转换
                if value == "true":
                    value = True
                elif value == "false":
                    value = False
                elif value.isdigit():
                    value = int(value)
                context[key] = value
                logger.info(f"Set task context: {key} = {value}")

    task.context = json.dumps(context)


@router.post("/command", response_model=AgentResponse)
async def agent_command(cmd: AgentCommand, db: Session = Depends(get_db)):
    """
    接收用户自然语言指令，解析并更新任务策略。

    示例：
    - "忽略所有 Redis 相关的漏洞"
    - "对 api.example.com 增加 SQL 注入测试深度为 5"
    - "重新分析上次扫描的日志，重点关注认证绕过"
    """
    task = db.query(Task).filter(Task.id == cmd.task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    logger.info(f"Agent command for task {cmd.task_id}: {cmd.prompt}")

    # 解析 prompt
    actions = parse_prompt(cmd.prompt)

    # 应用到任务上下文
    apply_context_updates(task, actions)
    db.commit()

    return AgentResponse(
        task_id=cmd.task_id,
        message=f"Command applied: {cmd.prompt}",
        parsed_actions=actions,
    )
