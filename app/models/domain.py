"""
域名和子域名模型
"""
from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field


class Domain(SQLModel, table=True):
    __tablename__ = "domains"

    id: Optional[int] = Field(default=None, primary_key=True)
    task_id: str = Field(index=True)
    root_domain: str = Field(index=True)
    subdomain: str = Field(unique=True, index=True)
    source: str = Field(default="subfinder")  # 子域名来源工具
    is_resolved: bool = Field(default=False)
    resolved_ips: Optional[str] = Field(default=None)  # JSON array of IP strings
    created_at: datetime = Field(default_factory=datetime.utcnow)


class DNSRecord(SQLModel, table=True):
    __tablename__ = "dns_records"

    id: Optional[int] = Field(default=None, primary_key=True)
    task_id: str = Field(index=True)
    subdomain: str = Field(index=True)
    record_type: str = Field(index=True)  # A / AAAA / CNAME
    value: str
    ttl: Optional[int] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
