#!/usr/bin/env python3
"""
AI 漏洞挖掘平台 - 交互式配置向导
从 .env.example 模板出发，引导用户配置 LLM、数据库等选项。
用法: python3 scripts/configure.py
"""
import os
import sys
import re
import subprocess
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
ENV_EXAMPLE = PROJECT_DIR / ".env.example"
ENV_FILE = PROJECT_DIR / ".env"

# ==================== 颜色 ====================
GREEN = "\033[0;32m"
CYAN  = "\033[0;36m"
YELLOW= "\033[1;33m"
RED   = "\033[0;31m"
BOLD  = "\033[1m"
NC    = "\033[0m"

def c(tag, text): return f"{tag}{text}{NC}"


# ==================== 预设 LLM 提供商 ====================
LLM_PROVIDERS = {
    "1": {
        "name": "OpenAI",
        "base": "https://api.openai.com/v1",
        "models": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "o3-mini"],
        "default_model": "gpt-4o",
        "env_key": "OPENAI_API_KEY",
    },
    "2": {
        "name": "Anthropic Claude",
        "base": "https://api.anthropic.com/v1",
        "models": ["claude-sonnet-4-20250514", "claude-3-5-sonnet-20241022", "claude-3-opus-20240229"],
        "default_model": "claude-sonnet-4-20250514",
        "env_key": "ANTHROPIC_API_KEY",
    },
    "3": {
        "name": "DeepSeek",
        "base": "https://api.deepseek.com/v1",
        "models": ["deepseek-chat", "deepseek-reasoner"],
        "default_model": "deepseek-chat",
        "env_key": "DEEPSEEK_API_KEY",
    },
    "4": {
        "name": "Ollama (本地)",
        "base": "http://localhost:11434/v1",
        "models": ["llama3", "qwen2.5", "mistral", "deepseek-r1"],
        "default_model": "llama3",
        "env_key": None,
    },
    "5": {
        "name": "自定义 (手动输入)",
        "base": "",
        "models": [],
        "default_model": "",
        "env_key": None,
    },
}


def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")


def print_banner():
    print()
    print(c(BOLD, "╔══════════════════════════════════════════════╗"))
    print(c(BOLD, "║   🛡️  AI 漏洞挖掘平台 - 配置向导           ║"))
    print(c(BOLD, "╚══════════════════════════════════════════════╝"))
    print()


def prompt(prompt_text: str, default: str = "") -> str:
    """带默认值的输入提示"""
    if default:
        result = input(f"  {prompt_text} [{c(CYAN, default)}]: ").strip()
        return result if result else default
    return input(f"  {prompt_text}: ").strip()


def prompt_choice(prompt_text: str, options: list[str]) -> str:
    """单选提示，返回选项 key"""
    print(f"\n  {c(BOLD, prompt_text)}")
    for i, opt in enumerate(options, 1):
        print(f"    {c(CYAN, str(i))}. {opt}")
    print(f"    {c(CYAN, str(len(options) + 1))}. 手动输入")
    while True:
        choice = input(f"  请选择 [1-{len(options) + 1}]: ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(options) + 1:
            return choice
        print(f"  {c(RED, '无效选择，请重试')}")


def configure_llm() -> dict:
    """配置 LLM 提供商"""
    print(f"\n{c(BOLD, '━' * 50)}")
    print(f"{c(BOLD, '🤖 步骤 1：选择 LLM 提供商')}")
    print(f"{c(BOLD, '━' * 50)}")

    print(f"\n  {c(YELLOW, 'Strix 和 AI 分析都需要 LLM。请选择：')}")
    for key, prov in LLM_PROVIDERS.items():
        print(f"    {c(CYAN, key)}. {prov['name']}")

    while True:
        choice = input(f"\n  请选择 [{c(CYAN, '1-5')}]: ").strip()
        if choice in LLM_PROVIDERS:
            break
        print(f"  {c(RED, '无效选择，请输入 1-5')}")

    provider = LLM_PROVIDERS[choice]
    name = provider["name"]
    base = provider["base"]
    models = provider["models"]

    print(f"\n  {c(GREEN, '✓')} 已选择: {c(BOLD, name)}")

    # API Key
    if provider["env_key"]:
        hint = provider["env_key"]
        api_key = prompt(f"请输入 {name} API Key ({hint})", "")
        if not api_key:
            api_key = f"sk-your-{name.lower().replace(' ', '-')}-key"
            print(f"  {c(YELLOW, '⚠ 未输入，使用占位值:')} {api_key}")
    elif choice == "4":  # Ollama 不需要 key
        api_key = "ollama"
        print(f"  {c(GREEN, '✓ Ollama 无需 API Key')}")
    else:
        api_key = prompt("请输入 API Key", "")
        if not api_key:
            api_key = "sk-your-custom-key"
            print(f"  {c(YELLOW, '⚠ 未输入，使用占位值')}")

    # Base URL
    if choice == "5":  # 自定义
        base = prompt("请输入 API Base URL", "https://api.openai.com/v1")
    print(f"  {c(GREEN, '✓')} Base URL: {base}")

    # Model
    if models:
        choice_model = prompt_choice("选择默认模型", models)
        idx = int(choice_model) - 1
        if idx < len(models):
            model = models[idx]
        else:
            model = prompt("请输入模型名称", provider["default_model"])
    else:
        model = prompt("请输入模型名称", provider["default_model"] or "gpt-4o")
    print(f"  {c(GREEN, '✓')} 模型: {model}")

    return {
        "api_base": base,
        "api_key": api_key,
        "model": model,
        "provider_name": name,
    }


def configure_database() -> dict:
    """配置数据库"""
    print(f"\n{c(BOLD, '━' * 50)}")
    print(f"{c(BOLD, '🗄️  步骤 2：数据库配置')}")
    print(f"{c(BOLD, '━' * 50)}")

    print(f"\n  {c(YELLOW, '选择数据库类型：')}")
    print(f"    {c(CYAN, '1')}. SQLite (默认，无需额外配置)")
    print(f"    {c(CYAN, '2')}. PostgreSQL")

    while True:
        choice = input(f"\n  请选择 [{c(CYAN, '1-2')}]: ").strip()
        if choice in ("1", "2"):
            break

    if choice == "1":
        db_path = prompt("SQLite 文件路径", "./data/orchestrator.db")
        print(f"  {c(GREEN, '✓')} SQLite: {db_path}")
        return {"database_url": f"sqlite:///{db_path}"}
    else:
        host = prompt("PostgreSQL 主机", "localhost")
        port = prompt("端口", "5432")
        user = prompt("用户名", "orchestrator")
        password = prompt("密码", "orchestrator")
        dbname = prompt("数据库名", "orchestrator")
        url = f"postgresql://{user}:{password}@{host}:{port}/{dbname}"
        print(f"  {c(GREEN, '✓')} PostgreSQL: {host}:{port}/{dbname}")
        return {"database_url": url}


def configure_redis() -> dict:
    """配置 Redis"""
    print(f"\n{c(BOLD, '━' * 50)}")
    print(f"{c(BOLD, '📡 步骤 3：Redis 配置')}")
    print(f"{c(BOLD, '━' * 50)}")

    print(f"\n  {c(YELLOW, 'Redis 用于 Celery 任务队列和 WebSocket 消息推送。')}")
    print(f"    {c(CYAN, '1')}. 默认 (redis://localhost:6379)")
    print(f"    {c(CYAN, '2')}. 自定义地址")

    while True:
        choice = input(f"\n  请选择 [{c(CYAN, '1-2')}]: ").strip()
        if choice in ("1", "2"):
            break

    if choice == "1":
        host = "localhost"
        print(f"  {c(GREEN, '✓')} Redis: {host}:6379")
    else:
        host = prompt("Redis 主机地址", "redis://redis:6379")
        print(f"  {c(GREEN, '✓')} Redis: {host}")

    redis_url = host if "://" in host else f"redis://{host}:6379"
    return {
        "redis_url": f"{redis_url}/0",
        "celery_broker_url": f"{redis_url}/1" if "/0" in redis_url else redis_url.replace("/0", "/1"),
        "celery_result_backend": f"{redis_url}/2" if "/0" in redis_url else redis_url.replace("/0", "/2"),
    }


def configure_tools() -> dict:
    """检测并配置安全工具路径"""
    print(f"\n{c(BOLD, '━' * 50)}")
    print(f"{c(BOLD, '🔧 步骤 4：安全工具路径')}")
    print(f"{c(BOLD, '━' * 50)}")

    def which(cmd: str) -> str | None:
        try:
            result = subprocess.run(["which", cmd], capture_output=True, text=True, timeout=3)
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            pass
        return None

    def detect_or_prompt(name: str, cmd: str, default: str) -> str:
        found = which(cmd)
        if found:
            print(f"  {c(GREEN, '✓')} {name}: {c(CYAN, found)} (自动检测)")
            return found
        else:
            val = prompt(f"{name} 路径 ({c(YELLOW, '未检测到' + name + ', 请输入路径或回车用默认')})", default)
            return val

    subfinder = detect_or_prompt("Subfinder", "subfinder", "/usr/local/bin/subfinder")
    naabu     = detect_or_prompt("Naabu", "naabu", "/usr/local/bin/naabu")
    strix     = detect_or_prompt("Strix", "strix", "strix")

    return {
        "subfinder_path": subfinder,
        "naabu_path": naabu,
        "strix_path": strix,
    }


def configure_advanced() -> dict:
    """高级配置：超时、并发等"""
    print(f"\n{c(BOLD, '━' * 50)}")
    print(f"{c(BOLD, '⚙️  步骤 5：高级配置')}")
    print(f"{c(BOLD, '━' * 50)}")

    use_defaults = prompt("是否使用默认值？(Y/n)", "Y").lower()
    if use_defaults != "n":
        print(f"  {c(GREEN, '✓')} 使用默认超时和并发参数")
        return {}

    print(f"\n  {c(YELLOW, '以下参数影响扫描性能和资源使用：')}")
    subdomain_timeout = prompt("子域名发现超时 (秒)", "600")
    dns_timeout       = prompt("DNS 解析超时 (秒)", "300")
    strix_timeout     = prompt("Strix 扫描超时 (秒)", "7200")
    dns_concurrency   = prompt("DNS 并发数", "50")
    celery_concurrency = prompt("Celery Worker 并发数", "8")

    return {
        "SUBDOMAIN_TIMEOUT": subdomain_timeout,
        "DNS_RESOLVE_TIMEOUT": dns_timeout,
        "STRIX_SCAN_TIMEOUT": strix_timeout,
        "DNS_CONCURRENCY": dns_concurrency,
        "CELERY_CONCURRENCY": celery_concurrency,
    }


def configure_password() -> dict:
    """设置 Web 访问密码"""
    print(f"\n{c(BOLD, '━' * 50)}")
    print(f"{c(BOLD, '🔐 步骤 6：Web 访问密码')}")
    print(f"{c(BOLD, '━' * 50)}")

    print(f"\n  {c(YELLOW, '为 Streamlit 前端和 API 设置访问密码。')}")
    print(f"  {c(YELLOW, '留空则不启用密码保护，任何人均可访问。')}")

    pwd = prompt("Web 访问密码（留空 = 不启用）", "")
    if pwd:
        print(f"  {c(GREEN, '✓')} 密码已设置（{len(pwd)} 个字符）")
    else:
        print(f"  {c(YELLOW, '⚠')} 未设置密码，前端和 API 将无需认证即可访问")
    return {"web_password": pwd}


def write_env_file(llm: dict, db: dict, redis: dict, tools: dict, advanced: dict, password: dict):
    """从 .env.example 模板生成 .env 文件"""
    print(f"\n{c(BOLD, '━' * 50)}")
    print(f"{c(BOLD, '📝 正在生成 .env 文件...')}")
    print(f"{c(BOLD, '━' * 50)}")

    # 读取模板
    if ENV_EXAMPLE.exists():
        template = ENV_EXAMPLE.read_text()
    else:
        template = ""

    # 构建替换规则
    replacements = {
        # LLM
        "LLM_API_BASE=https://api.openai.com/v1":          f"LLM_API_BASE={llm['api_base']}",
        "LLM_API_KEY=sk-your-key-here":                   f"LLM_API_KEY={llm['api_key']}",
        "LLM_MODEL=gpt-4o":                               f"LLM_MODEL={llm['model']}",
        # 数据库
        "DATABASE_URL=postgresql://orchestrator:orchestrator@localhost:5432/orchestrator":   f"DATABASE_URL={db['database_url']}",
        # Redis
        "REDIS_URL=redis://redis:6379/0":                  f"REDIS_URL={redis['redis_url']}",
        "CELERY_BROKER_URL=redis://redis:6379/1":          f"CELERY_BROKER_URL={redis['celery_broker_url']}",
        "CELERY_RESULT_BACKEND=redis://redis:6379/2":      f"CELERY_RESULT_BACKEND={redis['celery_result_backend']}",
        # 工具路径
        "SUBFINDER_PATH=/usr/local/bin/subfinder":          f"SUBFINDER_PATH={tools['subfinder_path']}",
        "STRIX_PATH=strix":                                 f"STRIX_PATH={tools['strix_path']}",
        "NAABU_PATH=/usr/local/bin/naabu":                  f"NAABU_PATH={tools['naabu_path']}",
    }

    # 应用替换
    result = template
    for old, new in replacements.items():
        result = result.replace(old, new)

    # 替换高级参数（如果用户自定义了）
    for key, val in advanced.items():
        pattern = re.compile(rf"^{re.escape(key)}=.*$", re.MULTILINE)
        if pattern.search(result):
            result = pattern.sub(f"{key}={val}", result)
        else:
            result += f"\n{key}={val}"

    # 写入 .env
    ENV_FILE.write_text(result)
    print(f"  {c(GREEN, '✓')} 配置文件已写入: {c(CYAN, str(ENV_FILE))}")
    print(f"  {c(YELLOW, '💡 你可以稍后编辑:')} nano {ENV_FILE}")


def show_summary(llm: dict, db: dict, password: dict):
    """显示配置摘要"""
    print(f"\n{c(BOLD, '╔══════════════════════════════════════════════╗')}")
    print(f"{c(BOLD, '║          📋 配置摘要                        ║')}")
    print(f"{c(BOLD, '╚══════════════════════════════════════════════╝')}")
    print()
    print(f"  {c(BOLD, 'LLM 提供商')}:  {c(CYAN, llm['provider_name'])}")
    print(f"  {c(BOLD, '模型')}:        {c(CYAN, llm['model'])}")
    print(f"  {c(BOLD, 'Base URL')}:   {llm['api_base'][:60]}")
    print(f"  {c(BOLD, '数据库')}:      {db['database_url'][:60]}")
    pwd = password.get('web_password', '')
    if pwd:
        print(f"  {c(BOLD, '密码保护')}:    {c(GREEN, '已启用')} ({len(pwd)} 字符)")
    else:
        print(f"  {c(BOLD, '密码保护')}:    {c(YELLOW, '未启用')}")
    print()
    print(f"  {c(GREEN, '✓')} 配置完成！运行以下命令启动：")
    print()
    print(f"  {c(BOLD, '# 方式 1: Docker 一键启动')}")
    print(f"  docker-compose up -d")
    print()
    print(f"  {c(BOLD, '# 方式 2: 本地开发（三个终端）')}")
    print(f"  uvicorn app.main:app --reload --port 8000")
    print(f"  celery -A app.tasks.celery_app worker -l info -c 8")
    print(f"  streamlit run streamlit_app.py")
    print()


# ==================== 主入口 ====================
def main():
    clear_screen()
    print_banner()

    print(f"  {c(YELLOW, '本向导将引导你配置 AI 漏洞挖掘平台的必要参数。')}")
    print(f"  {c(YELLOW, '所有配置将写入 .env 文件，可随时手动修改。')}")
    print()

    llm      = configure_llm()
    db       = configure_database()
    redis    = configure_redis()
    tools    = configure_tools()
    password = configure_password()

    write_env_file(llm, db, redis, tools, advanced, password)
    show_summary(llm, db, password)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n  {c(YELLOW, '配置已取消。你可以稍后手动编辑 .env 文件。')}")
        sys.exit(0)
    except EOFError:
        print(f"\n\n  {c(YELLOW, '配置已取消。')}")
        sys.exit(0)
