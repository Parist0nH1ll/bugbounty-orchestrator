"""
WebSocket 实时日志推送
- 前端连接 ws://host:8000/ws/{task_id}
- 后端通过 Redis pub/sub 广播日志和状态
"""
import json
import asyncio
import redis.asyncio as aioredis
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.config import settings
from app.utils.logger import get_logger

router = APIRouter()
logger = get_logger("websocket")

# 活跃连接：{task_id: [websocket1, websocket2, ...]}
active_connections: dict[str, list[WebSocket]] = {}


async def broadcast_to_task(task_id: str, message: dict):
    """向订阅某个 task_id 的所有 WebSocket 连接发送消息"""
    connections = active_connections.get(task_id, [])
    dead = []
    for ws in connections:
        try:
            await ws.send_json(message)
        except Exception:
            dead.append(ws)
    for ws in dead:
        connections.remove(ws)


@router.websocket("/ws/{task_id}")
async def websocket_endpoint(websocket: WebSocket, task_id: str):
    """
    WebSocket 连接端点。
    客户端连接到 /ws/{task_id} 接收该任务的实时日志。
    """
    await websocket.accept()
    logger.info(f"WebSocket connected for task {task_id}")

    # 注册连接
    if task_id not in active_connections:
        active_connections[task_id] = []
    active_connections[task_id].append(websocket)

    # 发送历史日志（简单实现：发送连接确认）
    await websocket.send_json({
        "type": "connected",
        "task_id": task_id,
        "message": f"Connected to task {task_id} log stream",
    })

    # 订阅 Redis channel
    redis_client = aioredis.from_url(settings.redis_url, decode_responses=True)
    pubsub = redis_client.pubsub()

    try:
        await pubsub.subscribe(f"task:{task_id}:logs", f"task:{task_id}:status")

        async def redis_listener():
            """监听 Redis 消息并转发到 WebSocket"""
            async for message in pubsub.listen():
                if message["type"] == "message":
                    try:
                        data = json.loads(message["data"])
                        await broadcast_to_task(task_id, {
                            "type": "log",
                            "task_id": task_id,
                            "message": data.get("message", str(data)),
                            "data": data,
                        })
                    except json.JSONDecodeError:
                        pass

        # 并行运行：Redis 监听 + WebSocket 接收
        redis_task = asyncio.create_task(redis_listener())

        # 保持连接，接收客户端消息（如 ping/pong）
        while True:
            try:
                data = await websocket.receive_text()
                # 客户端可以发送指令（如 ping）
                if data == "ping":
                    await websocket.send_json({"type": "pong"})
            except WebSocketDisconnect:
                break
            except Exception:
                break

    except Exception as e:
        logger.error(f"WebSocket error for task {task_id}: {e}")
    finally:
        redis_task.cancel()
        try:
            await redis_task
        except asyncio.CancelledError:
            pass

        await pubsub.unsubscribe()
        await redis_client.close()

        # 移除连接
        if task_id in active_connections:
            connections = active_connections[task_id]
            if websocket in connections:
                connections.remove(websocket)
            if not connections:
                del active_connections[task_id]

        logger.info(f"WebSocket disconnected for task {task_id}")


async def publish_log(task_id: str, level: str, message: str):
    """
    供 Celery 任务调用的日志发布函数。
    由于 Celery 在同步上下文，需使用同步 Redis 客户端。
    此函数为同步版本代理。
    """
    import redis as sync_redis
    try:
        r = sync_redis.from_url(settings.redis_url, decode_responses=True)
        r.publish(f"task:{task_id}:logs", json.dumps({
            "task_id": task_id,
            "level": level,
            "message": message,
        }))
    except Exception:
        pass
