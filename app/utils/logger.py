"""
统一日志工具 - 支持同时输出到 stdout 和 Redis (用于 WebSocket 推送)
"""
import logging
import sys
from typing import Optional
from datetime import datetime

# 全局 logger 实例缓存
_loggers = {}


def get_logger(name: str = "orchestrator") -> logging.Logger:
    """获取或创建 logger 实例"""
    if name in _loggers:
        return _loggers[name]

    logger = logging.getLogger(name)

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            "[%(asctime)s] %(levelname)s [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

    _loggers[name] = logger
    return logger


class TaskLogger:
    """
    任务级日志：除打印外，还将消息发布到 Redis，供 WebSocket 消费。
    """

    def __init__(self, task_id: str, redis_client=None):
        self.task_id = task_id
        self.redis = redis_client
        self._logger = get_logger(f"task.{task_id}")

    def _publish(self, level: str, message: str):
        """发布到 Redis channel"""
        if self.redis:
            try:
                import json
                payload = json.dumps({
                    "task_id": self.task_id,
                    "level": level,
                    "message": message,
                    "timestamp": datetime.utcnow().isoformat(),
                })
                self.redis.publish(f"task:{self.task_id}:logs", payload)
            except Exception:
                pass  # Redis 不可用时不阻塞

    def info(self, message: str):
        self._logger.info(message)
        self._publish("INFO", message)

    def warning(self, message: str):
        self._logger.warning(message)
        self._publish("WARNING", message)

    def error(self, message: str):
        self._logger.error(message)
        self._publish("ERROR", message)

    def debug(self, message: str):
        self._logger.debug(message)
        self._publish("DEBUG", message)
