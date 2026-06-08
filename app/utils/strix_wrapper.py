"""
Strix 渗透测试工具封装
基于 https://github.com/usestrix/strix 开源项目
安装方式：pip install strix-agent  或  pipx install strix-agent
CLI 用法：strix --target {url} --instruction "{prompt}"
"""
import os
import json
import subprocess
from datetime import datetime
from typing import Optional, Dict
from app.config import settings
from app.utils.logger import get_logger


def run_strix_scan(
    target: str,
    task_id: str,
    context: Optional[Dict] = None,
    timeout: int = None,
) -> Dict:
    """
    对目标执行 strix 扫描。
    target: 域名/IP 或 URL
    context: 动态策略参数（如 skip_redis 等）
    返回: stdout/stderr 和结果文件路径

    Strix 真实 CLI：strix --target https://example.com --instruction "执行安全检测"
    """
    timeout = timeout or settings.strix_scan_timeout
    logger = get_logger()
    context = context or {}

    strix_path = settings.strix_path

    # 结果输出目录
    output_dir = os.path.join(settings.scan_results_dir, task_id)
    os.makedirs(output_dir, exist_ok=True)

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    safe_target = target.replace("://", "_").replace(":", "_").replace("/", "_")
    output_file = os.path.join(output_dir, f"{safe_target}_{timestamp}.json")

    # 检测 strix 是否可用（pip install 后通常在 PATH 中，which strix 验证）
    strix_available = _check_strix_available(strix_path)
    if not strix_available:
        logger.warning(f"strix not found. Install with: curl -sSL https://strix.ai/install | bash")
        return _mock_strix_result(target, output_file, context)

    # 构建指令：target 如果是域名则补全 https://
    if not target.startswith("http://") and not target.startswith("https://"):
        target = f"https://{target}"

    # 构建 strix 指令描述
    instruction = _build_instruction(context)
    env = _build_strix_env()

    cmd = [
        strix_path,
        "--target", target,
        "--instruction", instruction,
    ]

    # Strix 的额外参数（如果支持的话）
    if context.get("timeout"):
        cmd.extend(["--timeout", str(context["timeout"])])

    logger.info(f"Running strix: {' '.join(cmd)}")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout + 300,
            env={**os.environ, **env},  # 注入 STRIX_LLM / LLM_API_KEY
        )

        # 保存原始输出
        with open(output_file, "w") as f:
            f.write(result.stdout)
            if result.stderr:
                f.write("\n--- STDERR ---\n")
                f.write(result.stderr)

        # 尝试解析输出中的漏洞信息
        parsed = _try_parse_json_output(result.stdout)

        return {
            "target": target,
            "output_file": output_file,
            "stdout": result.stdout[:50000],
            "stderr": result.stderr[:5000],
            "returncode": result.returncode,
            "parsed": parsed,
        }
    except subprocess.TimeoutExpired:
        logger.error(f"strix timed out for {target}")
        return {"target": target, "output_file": output_file, "error": "timeout", "stdout": "", "stderr": ""}
    except Exception as e:
        logger.error(f"strix error for {target}: {e}")
        return {"target": target, "output_file": output_file, "error": str(e), "stdout": "", "stderr": ""}


# ==================== 辅助函数 ====================

def _check_strix_available(strix_path: str) -> bool:
    """检测 strix 是否可用（二进制安装到 ~/.strix/bin/strix 或 /usr/local/bin/strix）"""
    if os.path.exists(strix_path):
        return True
    # 如果配置的路径不存在，尝试 which 查找
    try:
        result = subprocess.run(
            ["which", strix_path] if "/" not in strix_path else [strix_path, "--version"],
            capture_output=True, text=True, timeout=5,
        )
        return result.returncode == 0
    except Exception:
        return False


def _build_instruction(context: Dict) -> str:
    """
    根据动态策略构建 strix 的 --instruction 描述。
    Strix 使用自然语言指令而非传统参数来控制扫描行为。
    """
    parts = ["执行安全漏洞检测"]

    if context.get("sql_injection_deep"):
        parts.append("重点关注 SQL 注入漏洞")
    if context.get("focus_auth_bypass"):
        parts.append("重点关注认证绕过漏洞")
    if context.get("depth"):
        parts.append(f"测试深度设为 {context['depth']} 级")

    # 排除特定服务
    skips = []
    if context.get("skip_redis"):
        skips.append("Redis")
    if context.get("skip_mysql"):
        skips.append("MySQL")
    if context.get("skip_mongodb"):
        skips.append("MongoDB")
    if context.get("skip_postgres"):
        skips.append("PostgreSQL")
    if context.get("skip_elasticsearch"):
        skips.append("Elasticsearch")
    if skips:
        parts.append(f"跳过以下服务相关漏洞：{', '.join(skips)}")

    return "。".join(parts) + "。"


def _build_strix_env() -> Dict[str, str]:
    """
    构建 strix 运行所需的环境变量。
    Strix 使用 STRIX_LLM 和 LLM_API_KEY 来配置自己的 AI 模型。
    如果用户未单独设置 STRIX_LLM，则复用项目的 LLM 配置。
    """
    env = {
        "LLM_API_KEY": settings.llm_api_key,
    }
    strix_llm = getattr(settings, "strix_llm", None)
    if strix_llm:
        env["STRIX_LLM"] = strix_llm
    else:
        # 复用项目 LLM 配置，映射 model 名称到 strix 格式
        env["STRIX_LLM"] = f"openai/{settings.llm_model}"
    return env


def _try_parse_json_output(stdout: str) -> Optional[Dict]:
    """尝试从 strix 文本输出中提取 JSON 数据"""
    if not stdout:
        return None
    # Strix 的 TUI 输出通常是混排文本，尝试提取 JSON 块
    try:
        return json.loads(stdout)
    except json.JSONDecodeError:
        # 尝试从 markdown 代码块中提取
        if "```json" in stdout:
            try:
                block = stdout.split("```json")[1].split("```")[0]
                return json.loads(block)
            except Exception:
                pass
        return None


def _mock_strix_result(target: str, output_file: str, context: Dict) -> Dict:
    """
    Mock strix 结果 - 当 strix 不可用时返回示意数据。
    安装命令：pip install strix-agent
    """
    mock_result = {
        "target": target,
        "timestamp": datetime.utcnow().isoformat(),
        "vulnerabilities": [
            {
                "name": "Open Port: 80 (HTTP)",
                "severity": "info",
                "description": f"Port 80 is open on {target}",
            },
            {
                "name": "HTTP Security Headers Missing",
                "severity": "medium",
                "description": f"Missing Content-Security-Policy header on {target}",
            },
        ],
        "note": "This is a mock result - install: curl -sSL https://strix.ai/install | bash",
        "context_used": context,
    }

    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, "w") as f:
        json.dump(mock_result, f, indent=2)

    return {
        "target": target,
        "output_file": output_file,
        "stdout": json.dumps(mock_result),
        "stderr": "",
        "returncode": 0,
    }


# ==================== 输出解析 ====================

def extract_vulnerability_summary(strix_output: str) -> Dict:
    """
    从 strix 原始输出中提取摘要信息。
    优先解析 JSON，失败则返回原始文本的前 3000 字符。
    """
    try:
        data = json.loads(strix_output)
        vulns = data.get("vulnerabilities", [])
        cves = []
        for v in vulns:
            for cve in v.get("cves", []) or []:
                cves.append(cve)
        return {
            "vulnerability_count": len(vulns),
            "cves": cves[:50],  # 最多保留 50 个 CVE
            "severity_breakdown": _count_severity(vulns),
            "raw_summary": strix_output[:3000],
        }
    except json.JSONDecodeError:
        # 非 JSON 输出，提取前 3000 字符
        return {
            "vulnerability_count": 0,
            "cves": [],
            "severity_breakdown": {},
            "raw_summary": strix_output[:3000],
        }


def _count_severity(vulns: list) -> Dict:
    counts = {}
    for v in vulns:
        sev = (v.get("severity") or v.get("risk") or "unknown").lower()
        counts[sev] = counts.get(sev, 0) + 1
    return counts
