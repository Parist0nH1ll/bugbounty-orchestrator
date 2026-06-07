"""
Pydantic 请求/响应模型
"""
from __future__ import annotations
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


# ==================== FilterRule ====================

class FilterRuleCreate(BaseModel):
    name: str = Field(..., description="规则名称")
    rule_type: str = Field(default="keyword", description="keyword / regex")
    pattern: str = Field(..., description="匹配模式")
    priority: int = Field(default=1)
    enabled: bool = Field(default=True)


class FilterRuleUpdate(BaseModel):
    name: Optional[str] = None
    rule_type: Optional[str] = None
    pattern: Optional[str] = None
    priority: Optional[int] = None
    enabled: Optional[bool] = None


class FilterRuleOut(BaseModel):
    id: int
    name: str
    rule_type: str
    pattern: str
    priority: int
    enabled: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ==================== Domain ====================

class DomainUploadRequest(BaseModel):
    """上传域名文件后的响应"""
    task_id: str
    domains_count: int
    message: str


class SubdomainOut(BaseModel):
    id: int
    root_domain: str
    subdomain: str
    source: str
    created_at: datetime

    model_config = {"from_attributes": True}


class DNSRecordOut(BaseModel):
    id: int
    subdomain: str
    record_type: str
    value: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ==================== Asset ====================

class AssetOut(BaseModel):
    id: int
    domain: str
    ips: str  # JSON string of IP list
    priority: int
    matched_rules: str
    open_ports: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


# ==================== Vulnerability ====================

class VulnerabilityOut(BaseModel):
    id: int
    cve_id: Optional[str]
    risk_score: Optional[float]
    affected_component: Optional[str]
    description: Optional[str]
    remediation: Optional[str]
    raw_result: Optional[str]
    task_id: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ==================== AI Analysis Result ====================

class AiVulnerability(BaseModel):
    cve: Optional[str] = None
    risk_score: Optional[float] = None
    affected_component: Optional[str] = None
    description: Optional[str] = None
    remediation: Optional[str] = None


class AiAnalysisResult(BaseModel):
    high_risk_vulnerabilities: List[AiVulnerability] = Field(default_factory=list)
    summary: str = ""


# ==================== Task ====================

class TaskOut(BaseModel):
    id: str
    status: str
    progress: int
    current_step: Optional[str]
    domains_count: int
    subdomains_count: int
    assets_count: int
    vulnerabilities_count: int
    error_message: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TaskListOut(BaseModel):
    tasks: List[TaskOut]
    total: int


# ==================== Agent ====================

class AgentCommand(BaseModel):
    task_id: str
    prompt: str


class AgentResponse(BaseModel):
    task_id: str
    message: str
    parsed_actions: List[str]


# ==================== Report ====================

class ReportOut(BaseModel):
    task_id: str
    domains: List[str]
    vulnerabilities: List[VulnerabilityOut]
    summary: str
    generated_at: datetime


# ==================== Websocket ====================

class WSMessage(BaseModel):
    type: str  # "log" | "progress" | "status" | "error"
    task_id: str
    message: str
    data: Optional[Dict[str, Any]] = None
