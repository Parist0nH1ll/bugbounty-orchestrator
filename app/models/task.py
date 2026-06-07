"""
任务记录模型
"""
from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field, Column
from sqlalchemy import JSON, Text


class Task(SQLModel, table=True):
    __tablename__ = "tasks"

    id: str = Field(primary_key=True, index=True)
    status: str = Field(default="pending", index=True)  # pending / running / completed / failed / cancelled
    progress: int = Field(default=0)  # 0-100
    current_step: Optional[str] = Field(default=None)
    domains_count: int = Field(default=0)
    subdomains_count: int = Field(default=0)
    assets_count: int = Field(default=0)
    vulnerabilities_count: int = Field(default=0)
    error_message: Optional[str] = Field(default=None, sa_column=Column(Text))
    context: Optional[str] = Field(default="{}", sa_column=Column(JSON))  # 动态策略
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
