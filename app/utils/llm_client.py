"""
LLM 客户端 - 调用 OpenAI 兼容接口进行智能分析
"""
import json
from typing import List, Dict, Optional
from openai import OpenAI
from app.config import settings
from app.utils.logger import get_logger

# AI 分析 Prompt 模板
ANALYSIS_SYSTEM_PROMPT = """你是一名顶级安全专家。请根据以下漏洞扫描结果进行深度分析。
你必须严格返回 JSON 格式，不要包含任何其他文本。
JSON 格式：

{
  "high_risk_vulnerabilities": [
    {
      "cve": "CVE编号",
      "risk_score": 风险评分(0-10),
      "affected_component": "受影响组件和版本",
      "description": "漏洞利用描述",
      "remediation": "修复建议"
    }
  ],
  "summary": "整体风险评估总结"
}

规则：
1. 仅报告高危漏洞 (risk_score >= 7.0)
2. 如果未发现高危漏洞，返回空列表和总体评估
3. 修复建议必须具体可操作
4. 如果识别到已知 CVE，必须填写正确编号
"""


def analyze_scan_results(
    scan_summary: str,
    task_context: Optional[Dict] = None,
    custom_prompt: Optional[str] = None,
) -> Dict:
    """
    将扫描结果发送给 LLM，获取结构化分析结果。
    """
    logger = get_logger()
    client = OpenAI(
        base_url=settings.llm_api_base,
        api_key=settings.llm_api_key,
    )

    system_prompt = custom_prompt or ANALYSIS_SYSTEM_PROMPT

    # 如果上下文中有"忽略"指令，追加到 prompt
    if task_context:
        skip_items = []
        if task_context.get("skip_redis"):
            skip_items.append("Redis")
        if task_context.get("skip_mysql"):
            skip_items.append("MySQL")
        if skip_items:
            system_prompt += f"\n\n注意：请在分析中忽略以下服务相关的漏洞：{', '.join(skip_items)}"

    user_message = f"以下是漏洞扫描结果，请分析：\n\n```\n{scan_summary}\n```"

    try:
        logger.info(f"Sending scan results to LLM ({settings.llm_model}) for analysis")

        response = client.chat.completions.create(
            model=settings.llm_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            temperature=0.2,
            max_tokens=4096,
        )

        content = response.choices[0].message.content.strip()

        # 提取 JSON（可能被 markdown 包裹）
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()

        result = json.loads(content)
        logger.info(f"LLM analysis complete: {len(result.get('high_risk_vulnerabilities', []))} high-risk vulns found")
        return result

    except json.JSONDecodeError as e:
        logger.error(f"LLM returned invalid JSON: {e}")
        return {
            "high_risk_vulnerabilities": [],
            "summary": f"AI 分析失败：无法解析 LLM 返回的 JSON。原始响应：{content[:500]}",
            "raw_response": content,
        }
    except Exception as e:
        logger.error(f"LLM API error: {e}")
        return {
            "high_risk_vulnerabilities": [],
            "summary": f"AI 分析失败：{str(e)}",
        }
