"""
AI 漏洞挖掘平台 - Streamlit 前端
提供：域名上传、任务管理、规则配置、Agent 对话、漏洞报告
"""
import json
import time
import io
import requests
import streamlit as st
import pandas as pd

# ==================== 配置 ====================
st.set_page_config(
    page_title="AI 漏洞挖掘平台",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

API_BASE = "http://api:8000"
WS_BASE = "ws://api:8000"

# ==================== 样式 ====================
st.markdown("""
<style>
    .stApp { background-color: #0e1117; }
    .main-header { color: #00ff88; font-size: 2rem; font-weight: bold; }
    .sub-header { color: #888; font-size: 0.9rem; }
    .vuln-high { color: #ff4444; font-weight: bold; }
    .vuln-medium { color: #ffaa00; }
    .vuln-low { color: #44ff44; }
    .status-running { color: #00ff88; }
    .status-completed { color: #4488ff; }
    .status-failed { color: #ff4444; }
</style>
""", unsafe_allow_html=True)


# ==================== 辅助函数 ====================
def api_get(path: str):
    """GET 请求封装"""
    try:
        resp = requests.get(f"{API_BASE}{path}", timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        st.error(f"API Error: {e}")
        return None


def api_post(path: str, data: dict = None, files: dict = None):
    """POST 请求封装"""
    try:
        if files:
            resp = requests.post(f"{API_BASE}{path}", files=files, timeout=30)
        else:
            resp = requests.post(f"{API_BASE}{path}", json=data, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        st.error(f"API Error: {e}")
        return None


def api_put(path: str, data: dict):
    """PUT 请求封装"""
    try:
        resp = requests.put(f"{API_BASE}{path}", json=data, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        st.error(f"API Error: {e}")
        return None


def api_delete(path: str):
    """DELETE 请求封装"""
    try:
        resp = requests.delete(f"{API_BASE}{path}", timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        st.error(f"API Error: {e}")
        return None


# ==================== 侧边栏 ====================
with st.sidebar:
    st.markdown('<div class="main-header">🛡️ AI 漏洞挖掘</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">全自动子域名→DNS→筛选→扫描→AI分析</div>', unsafe_allow_html=True)
    st.divider()

    page = st.radio(
        "导航",
        ["📤 域名上传", "📋 任务管理", "📏 筛选规则", "🤖 Agent 指令", "📊 漏洞报告", "📜 实时日志"],
        label_visibility="collapsed",
    )

    st.divider()
    # API 连接状态
    try:
        health = requests.get(f"{API_BASE}/health", timeout=3)
        if health.status_code == 200:
            st.success("🟢 API 已连接")
        else:
            st.warning("🟡 API 异常")
    except Exception:
        st.error("🔴 API 不可达")


# ==================== 主导航 ====================
if page == "📤 域名上传":
    st.markdown('<div class="main-header">📤 上传目标域名</div>', unsafe_allow_html=True)
    st.markdown("上传一个文本文件，每行一个根域名，启动全自动漏洞挖掘流水线。")

    col1, col2 = st.columns([2, 1])

    with col1:
        uploaded_file = st.file_uploader(
            "选择域名列表文件 (.txt)",
            type=["txt"],
            help="每行一个域名，如 example.com",
        )

        if uploaded_file:
            domains_preview = uploaded_file.getvalue().decode("utf-8")
            lines = [l.strip() for l in domains_preview.splitlines() if l.strip() and not l.strip().startswith("#")]
            st.info(f"检测到 **{len(lines)}** 个域名")
            with st.expander("预览域名列表"):
                st.code("\n".join(lines[:20]) + ("\n..." if len(lines) > 20 else ""))

            if st.button("🚀 启动扫描流水线", type="primary", use_container_width=True):
                with st.spinner("正在启动流水线..."):
                    uploaded_file.seek(0)
                    files = {"file": (uploaded_file.name, uploaded_file, "text/plain")}
                    result = api_post("/api/upload/domains", files=files)
                    if result and result.get("task_id"):
                        st.success(f"✅ 任务已启动！Task ID: `{result['task_id']}`")
                        st.info(f"域名数：{result['domains_count']}")
                        # 存储到 session
                        if "recent_tasks" not in st.session_state:
                            st.session_state.recent_tasks = []
                        st.session_state.recent_tasks.insert(0, result["task_id"])
                    else:
                        st.error("启动失败，请检查 API 连接")

    with col2:
        st.markdown("### 流水线流程")
        st.markdown("""
        1. 🔍 **子域名发现** (subfinder)
        2. 🌐 **DNS 解析确认** (A/AAAA/CNAME)
        3. 🎯 **重点资产筛选** (规则匹配)
        4. 🛡️ **Strix 漏洞扫描**
        5. 🤖 **AI 智能分析** (LLM)
        """)

        st.markdown("### 文件格式示例")
        st.code("""# 目标域名列表
example.com
test.myapp.cn
api.internal.net
""")

        st.markdown("### 快速域名输入")
        quick_domains = st.text_area(
            "手动输入域名（每行一个）",
            height=150,
            placeholder="example.com\ntest.com",
        )
        if st.button("📝 从文本框启动", use_container_width=True):
            if quick_domains.strip():
                lines = [l.strip() for l in quick_domains.splitlines() if l.strip()]
                file_content = "\n".join(lines)
                files = {"file": ("domains.txt", io.BytesIO(file_content.encode()), "text/plain")}
                result = api_post("/api/upload/domains", files=files)
                if result and result.get("task_id"):
                    st.success(f"✅ 任务已启动！Task ID: `{result['task_id']}`")
                else:
                    st.error("启动失败")


elif page == "📋 任务管理":
    st.markdown('<div class="main-header">📋 任务管理</div>', unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)
    with col1:
        status_filter = st.selectbox("状态筛选", ["all", "pending", "running", "completed", "failed", "cancelled"])
    with col2:
        auto_refresh = st.checkbox("自动刷新 (10s)", value=True)
    with col3:
        if st.button("🔄 刷新"):
            st.rerun()

    # 获取任务列表
    params = {}
    if status_filter != "all":
        params["status"] = status_filter
    tasks_data = api_get(f"/api/tasks/?{'&'.join(f'{k}={v}' for k, v in params.items())}")

    if tasks_data and tasks_data.get("tasks"):
        df_data = []
        for t in tasks_data["tasks"]:
            status_emoji = {
                "pending": "⏳", "running": "🔄", "completed": "✅",
                "failed": "❌", "cancelled": "🚫",
            }.get(t["status"], "❓")
            df_data.append({
                "ID": t["id"],
                "状态": f"{status_emoji} {t['status']}",
                "进度": f"{t['progress']}%",
                "当前步骤": t.get("current_step", "-"),
                "域名数": t["domains_count"],
                "子域名": t["subdomains_count"],
                "资产": t["assets_count"],
                "漏洞": t["vulnerabilities_count"],
                "创建时间": t["created_at"][:19] if t.get("created_at") else "-",
            })

        df = pd.DataFrame(df_data)
        st.dataframe(df, use_container_width=True, hide_index=True)

        # 任务详情
        st.divider()
        selected_task = st.selectbox(
            "选择任务查看详情",
            [t["id"] for t in tasks_data["tasks"]],
        )

        if selected_task:
            detail = api_get(f"/api/tasks/{selected_task}")
            if detail:
                col_a, col_b, col_c, col_d = st.columns(4)
                col_a.metric("状态", detail["status"])
                col_b.metric("进度", f"{detail['progress']}%")
                col_c.metric("子域名", detail["subdomains_count"])
                col_d.metric("漏洞", detail["vulnerabilities_count"])

                if detail.get("error_message"):
                    st.error(f"错误：{detail['error_message']}")

                if detail["status"] in ("running", "pending"):
                    if st.button("🛑 取消任务", type="secondary"):
                        cancel_result = api_post(f"/api/tasks/{selected_task}/cancel")
                        if cancel_result:
                            st.warning(f"任务 {selected_task} 正在取消...")
    else:
        st.info("暂无任务记录。请先上传域名文件启动扫描。")


elif page == "📏 筛选规则":
    st.markdown('<div class="main-header">📏 重点资产筛选规则</div>', unsafe_allow_html=True)
    st.markdown("配置域名筛选规则，支持关键词匹配和正则表达式。匹配到的域名将被标记为重点资产进行深入扫描。")

    # 现有规则列表
    rules = api_get("/api/rules/") or []

    st.markdown("### 现有规则")
    if rules:
        rule_data = []
        for r in rules:
            rule_data.append({
                "ID": r["id"],
                "名称": r["name"],
                "类型": r["rule_type"],
                "模式": r["pattern"][:50],
                "优先级": r["priority"],
                "启用": "✅" if r["enabled"] else "❌",
            })
        st.dataframe(pd.DataFrame(rule_data), use_container_width=True, hide_index=True)
    else:
        st.info("暂无规则")

    # 添加规则
    st.divider()
    st.markdown("### 添加新规则")
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        new_pattern = st.text_input("匹配模式", placeholder="admin 或 admin.*\.com")
    with col2:
        new_type = st.selectbox("类型", ["keyword", "regex"])
    with col3:
        new_priority = st.number_input("优先级", min_value=1, max_value=10, value=1)

    new_name = st.text_input("规则名称", placeholder="keyword:admin")

    if st.button("➕ 添加规则", type="primary"):
        if new_pattern and new_name:
            result = api_post("/api/rules/", {
                "name": new_name,
                "rule_type": new_type,
                "pattern": new_pattern,
                "priority": new_priority,
                "enabled": True,
            })
            if result:
                st.success(f"规则 '{new_name}' 已添加")
                st.rerun()

    # 删除规则
    st.divider()
    st.markdown("### 管理规则")
    if rules:
        rule_to_manage = st.selectbox("选择规则", [f"#{r['id']}: {r['name']}" for r in rules])
        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("🔓 启用/禁用"):
                rule_id = int(rule_to_manage.split(":")[0].replace("#", ""))
                current = next((r for r in rules if r["id"] == rule_id), None)
                if current:
                    api_put(f"/api/rules/{rule_id}", {"enabled": not current["enabled"]})
                    st.rerun()
        with col_b:
            if st.button("🗑️ 删除规则", type="secondary"):
                rule_id = int(rule_to_manage.split(":")[0].replace("#", ""))
                api_delete(f"/api/rules/{rule_id}")
                st.rerun()


elif page == "🤖 Agent 指令":
    st.markdown('<div class="main-header">🤖 Agent 指令交互</div>', unsafe_allow_html=True)
    st.markdown("向 AI Agent ("deepcode") 发送自然语言指令，动态调整后续扫描行为。")

    # 获取运行中的任务
    tasks_data = api_get("/api/tasks/?status=running") or {}
    task_ids = [t["id"] for t in tasks_data.get("tasks", [])]

    if not task_ids:
        st.warning("当前没有运行中的任务。Agent 指令可以指定任意任务。")
        selected_task = st.text_input("输入目标 Task ID", placeholder="例如 a1b2c3d4")
    else:
        selected_task = st.selectbox("选择目标任务", task_ids)

    st.divider()
    st.markdown("### 示例指令")
    examples = {
        "忽略 Redis 漏洞": "忽略所有 Redis 相关的漏洞",
        "增加 SQL 注入深度": "对 api.example.com 增加 SQL 注入测试深度为 5",
        "重分析 + 认证绕过": "重新分析上次扫描的日志，重点关注认证绕过",
        "跳过 MySQL": "忽略 MySQL 相关的漏洞扫描",
    }
    cols = st.columns(len(examples))
    for i, (label, cmd) in enumerate(examples.items()):
        with cols[i]:
            if st.button(f"📌 {label}", use_container_width=True, key=f"example_{i}"):
                st.session_state.agent_prompt = cmd

    st.divider()
    prompt = st.text_area(
        "输入指令",
        value=st.session_state.get("agent_prompt", ""),
        height=100,
        placeholder="例如：忽略所有 Redis 相关的漏洞",
        key="agent_input",
    )

    if st.button("🚀 发送指令", type="primary", use_container_width=True):
        if prompt and selected_task:
            with st.spinner("解析指令..."):
                result = api_post("/api/agent/command", {
                    "task_id": selected_task,
                    "prompt": prompt,
                })
                if result:
                    st.success(f"✅ 指令已应用")
                    st.json({
                        "task_id": result["task_id"],
                        "message": result["message"],
                        "parsed_actions": result["parsed_actions"],
                    })
                    st.info("解析出的操作将影响后续扫描步骤和 AI 分析结果。")

    st.divider()
    st.caption("💡 提示：Agent 通过关键词匹配解析指令，复杂语义理解需要集成 LLM 解析。")


elif page == "📊 漏洞报告":
    st.markdown('<div class="main-header">📊 漏洞报告</div>', unsafe_allow_html=True)

    # 获取已完成的任务
    tasks_data = api_get("/api/tasks/?status=completed") or {}
    completed_tasks = [t["id"] for t in tasks_data.get("tasks", [])]

    if not completed_tasks:
        st.info("暂无已完成的任务。请等待扫描流水线完成。")
    else:
        selected_task = st.selectbox("选择已完成的任务", completed_tasks)

        if selected_task:
            report = api_get(f"/api/reports/{selected_task}")

            if report:
                # 概览指标
                vulns = report.get("vulnerabilities", [])
                high_risk = [v for v in vulns if (v.get("risk_score") or 0) >= 7.0]
                medium_risk = [v for v in vulns if 4.0 <= (v.get("risk_score") or 0) < 7.0]
                low_risk = [v for v in vulns if (v.get("risk_score") or 0) < 4.0]

                col_a, col_b, col_c, col_d = st.columns(4)
                col_a.metric("🟥 高危", len(high_risk))
                col_b.metric("🟧 中危", len(medium_risk))
                col_c.metric("🟩 低危", len(low_risk))
                col_d.metric("📋 总计", len(vulns))

                st.divider()

                # 高危漏洞表格
                if high_risk:
                    st.markdown("### 🔴 高危漏洞列表")
                    high_data = []
                    for v in high_risk:
                        high_data.append({
                            "CVE": v.get("cve_id") or "N/A",
                            "评分": v.get("risk_score", "-"),
                            "域名": v.get("domain", "-"),
                            "组件": v.get("affected_component") or "-",
                            "描述": (v.get("description") or "-")[:100],
                            "修复建议": (v.get("remediation") or "-")[:100],
                        })
                    st.dataframe(pd.DataFrame(high_data), use_container_width=True, hide_index=True)

                # 所有漏洞表格
                if vulns:
                    st.markdown("### 📋 所有漏洞")
                    all_data = []
                    for v in vulns:
                        score = v.get("risk_score") or 0
                        if score >= 7.0:
                            sev = "🔴 高危"
                        elif score >= 4.0:
                            sev = "🟧 中危"
                        else:
                            sev = "🟩 低危"

                        all_data.append({
                            "严重度": sev,
                            "CVE": v.get("cve_id") or "N/A",
                            "评分": score,
                            "域名": v.get("domain", "-"),
                            "组件": v.get("affected_component") or "-",
                            "描述": (v.get("description") or "-")[:80],
                        })
                    st.dataframe(pd.DataFrame(all_data), use_container_width=True, hide_index=True)

                # 整体摘要
                st.divider()
                st.markdown("### 📝 AI 分析摘要")
                st.info(report.get("summary", "暂无分析"))

                # 导出
                st.download_button(
                    "📥 导出 CSV 报告",
                    data=requests.get(f"{API_BASE}/api/reports/{selected_task}/export").content,
                    file_name=f"vulnerability_report_{selected_task}.csv",
                    mime="text/csv",
                )


elif page == "📜 实时日志":
    st.markdown('<div class="main-header">📜 实时日志</div>', unsafe_allow_html=True)

    # 获取运行中的任务
    tasks_data = api_get("/api/tasks/") or {}
    all_tasks = tasks_data.get("tasks", [])

    if not all_tasks:
        st.info("暂无任务。请先上传域名文件启动扫描。")
    else:
        selected_task = st.selectbox(
            "选择任务查看日志",
            [f"{t['id']} - {t['status']} ({t['current_step'] or 'waiting'})" for t in all_tasks],
        )
        task_id = selected_task.split(" - ")[0] if selected_task else None

        if task_id:
            st.caption(f"WebSocket 连接: `{WS_BASE}/ws/{task_id}`")

            # 日志显示区域
            log_container = st.container()
            with log_container:
                st.markdown("#### 日志输出")

                task_detail = api_get(f"/api/tasks/{task_id}")
                if task_detail:
                    st.progress(task_detail.get("progress", 0) / 100)
                    st.caption(f"状态: {task_detail['status']} | 步骤: {task_detail.get('current_step', '-')}")

                # 尝试通过 WebSocket 获取实时日志
                st.code("⚡ 实时日志需通过 WebSocket 连接，请使用前端 WebSocket 客户端直接连接。", language=None)
                st.caption(f"连接地址: {WS_BASE}/ws/{task_id}")

                # 也提供通过 API 轮询的方式
                if st.button("🔄 刷新任务状态"):
                    task_info = api_get(f"/api/tasks/{task_id}")
                    if task_info:
                        st.json({
                            "id": task_info["id"],
                            "status": task_info["status"],
                            "progress": task_info["progress"],
                            "current_step": task_info.get("current_step"),
                            "subdomains": task_info["subdomains_count"],
                            "assets": task_info["assets_count"],
                            "vulnerabilities": task_info["vulnerabilities_count"],
                            "error": task_info.get("error_message"),
                        })


# ==================== 页脚 ====================
st.divider()
st.caption("AI 漏洞挖掘平台 v1.0 | 集成了子域名发现、DNS解析、资产筛选、Strix扫描和LLM智能分析")
