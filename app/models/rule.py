"""
筛选规则模型
"""
from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field
import enum


class RuleType(str, enum.Enum):
    KEYWORD = "keyword"
    REGEX = "regex"


class FilterRule(SQLModel, table=True):
    __tablename__ = "filter_rules"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True)
    rule_type: str = Field(default="keyword")  # keyword / regex
    pattern: str  # 关键词或正则表达式
    priority: int = Field(default=1)
    enabled: bool = Field(default=True, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
