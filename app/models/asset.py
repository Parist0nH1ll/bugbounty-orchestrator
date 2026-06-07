"""
重点资产模型
"""
from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field, Column
from sqlalchemy import JSON, Text


class Asset(SQLModel, table=True):
    __tablename__ = "assets"

    id: Optional[int] = Field(default=None, primary_key=True)
    task_id: str = Field(index=True)
    domain: str = Field(index=True)
    ips: str = Field(default="[]", sa_column=Column(JSON))  # JSON array
    priority: int = Field(default=1)  # 1=普通, 2=重要, 3=高危
    matched_rules: str = Field(default="[]", sa_column=Column(JSON))  # 匹配到的规则
    open_ports: Optional[str] = Field(default=None, sa_column=Column(JSON))
    scanned: bool = Field(default=False)  # 是否已进行 strix 扫描
    created_at: datetime = Field(default_factory=datetime.utcnow)
