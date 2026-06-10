# AI 驱动全自动漏洞挖掘平台

> 全自动流水线：子域名发现 → DNS 解析 → 重点资产筛选 → Strix 漏洞扫描 → AI 智能分析

## 🚀 快速开始

### 前置条件

- **Docker** 20.10+（[安装指南](https://docs.docker.com/get-docker/)）
- **Docker Compose** v2（`docker compose` 命令可用，不是旧版 `docker-compose`）
- 一个 **LLM API Key**（OpenAI / Claude / DeepSeek / Ollama 任选一个）

### 5 分钟上手

```bash
# 1. 克隆项目
git clone https://github.com/your-org/orchestrator.git
cd orchestrator

# 2. 创建配置文件
cp .env.example .env
```

编辑 `.env`，只需填一行：
```bash
LLM_API_KEY=sk-your-api-key-here
```
其他配置有合理默认值，可以不动。

```bash
# 3. 构建并启动（首次构建约 3-5 分钟，下载依赖和工具）
docker compose build
docker compose up -d

# 4. 确认所有服务正常
docker compose ps
```

预期输出：
```
NAME                  STATUS
orchestrator_api_1     running
orchestrator_worker_1  running
orchestrator_streamlit_1 running
orchestrator_redis_1   running (healthy)
```

```bash
# 5. 打开浏览器
open http://localhost:8501
```

### 使用流程

1. 在 Streamlit 页面左侧选择 **📤 域名上传**
2. 上传一个 `.txt` 文件（每行一个根域名，如 `example.com`），或直接在文本框输入
3. 点击 **🚀 启动扫描流水线**
4. 等待流水线完成（进度和日志通过 WebSocket 实时推送）
5. 在 **📊 漏洞报告** 页面查看结果，可导出 CSV

### 服务端口

| 服务 | 端口 | 用途 |
|------|:---:|------|
| Streamlit 前端 | `8501` | Web 控制台，上传域名、查看报告 |
| FastAPI | `8000` | 后端 API，Swagger 文档在 `/docs` |
| Redis | `6379` | Celery 任务队列 + WebSocket 消息广播 |
| Celery Worker | - | 后台执行扫描任务，默认 8 并发 |

### 常用命令

```bash
docker compose up -d              # 启动全部服务
docker compose ps                 # 查看运行状态
docker compose logs -f worker     # 实时查看 Worker 日志
docker compose logs -f api        # 实时查看 API 日志
docker compose restart worker     # 重启 Worker
docker compose down               # 停止并清理容器
docker compose down -v            # 同时删除数据卷（慎用！）
docker compose build --no-cache   # 强制重新构建镜像
```

### 常见问题

<details>
<summary><b>构建时 GitHub 下载卡住或超时？</b></summary>

Dockerfile 已内置重试逻辑（5 次重试）+ 自动回退到 `ghproxy.com` 镜像。
如果 ghproxy 也不可用，可在 `.env` 中添加：
```bash
# 不使用镜像加速的 GitHub 备用域名
# 或自行搭建 ghproxy，修改 Dockerfile 中的 MIRROR_URL
```
</details>

<details>
<summary><b>Streamlit 启动报 "executable file not found"？</b></summary>

确保已重新构建：`docker compose build --no-cache streamlit && docker compose up -d`
</details>

<details>
<summary><b>Worker 报 "strix not found"？</b></summary>

Strix 通过 Docker 镜像运行，需要 Worker 容器能访问 Docker daemon。
确保 `docker-compose.yml` 中 Worker 的 `volumes` 包含：
```yaml
- /var/run/docker.sock:/var/run/docker.sock
```
首次调用 strix 时会自动 `docker pull ghcr.io/usestrix/strix-agent:latest`。
</details>

<details>
<summary><b>如何更换 LLM 提供商？</b></summary>

运行交互式配置向导：
```bash
python3 scripts/configure.py
```
或在 `.env` 中手动修改 `LLM_API_BASE`、`LLM_API_KEY`、`LLM_MODEL`。
</details>

## 📁 项目结构

```
orchestrator/
├── app/                     # 后端核心
│   ├── api/                 # FastAPI 路由与 WebSocket
│   │   ├── endpoints/       # upload, task, report, rules, agent
│   │   └── websocket.py     # 实时日志推送
│   ├── models/              # SQLAlchemy 模型
│   ├── tasks/               # Celery 任务链
│   │   ├── workflow.py      # 主流水线编排
│   │   ├── subdomain.py     # 子域名发现
│   │   ├── dns_resolve.py   # DNS 解析
│   │   ├── filter_assets.py # 资产筛选
│   │   ├── strix_scan.py    # 漏洞扫描
│   │   └── ai_analyze.py    # AI 分析
│   ├── utils/               # 工具封装
│   │   ├── subfinder_wrapper.py
│   │   ├── dns_utils.py
│   │   ├── port_scanner.py
│   │   ├── strix_wrapper.py
│   │   ├── llm_client.py
│   │   └── logger.py
│   ├── schemas/             # Pydantic 模型
│   ├── config.py            # 全局配置
│   ├── database.py          # 数据库初始化
│   └── main.py              # FastAPI 入口
├── frontend/                # Vue 3 前端（可选）
│   └── nginx.conf
├── scripts/                 # 启动 & 初始化脚本
├── streamlit_app.py         # Streamlit 前端
├── docker-compose.yml       # 容器编排
├── Dockerfile.api           # API 镜像
├── Dockerfile.worker        # Worker 镜像（含扫描工具）
├── Dockerfile.frontend      # 前端镜像
├── requirements.txt
└── .env.example
```

## 🏗️ 系统架构

### 服务拓扑

```
                          ┌──────────────┐
                          │   Nginx/     │  (可选)
                          │   Streamlit  │
                          │   :80/:8501  │
                          └──────┬───────┘
                                 │ HTTP/WS
                                 ▼
┌──────────┐  Redis   ┌──────────────────┐  SQLite/   ┌──────────────┐
│  Redis   │◄───────►│     FastAPI       │◄──────────►│   SQLite /   │
│  :6379   │ pub/sub │     :8000         │  SQLAlchemy│  PostgreSQL  │
│ 队列/缓存 │         │  ┌──────────────┐ │            └──────────────┘
└────┬─────┘         │  │  WebSocket   │ │
     │               │  │  /ws/{task}  │ │
     │ 任务投递       │  │  实时日志推送  │ │
     ▼               │  └──────────────┘ │
┌──────────────────┐  └──────────────────┘
│  Celery Worker   │
│  --concurrency=8 │
│  ┌──────────────┐│
│  │ 5 个任务队列:  ││
│  │ subdomain     ││        ┌──────────────┐
│  │ dns           ││        │  Docker Hub  │
│  │ scan ─────────┼┼───────►│  ghcr.io/    │
│  │ ai            ││        │  usestrix/   │
│  │ default       ││        │  strix-agent │
│  └──────────────┘│        │  :latest     │
└──────────────────┘        └──────┬───────┘
     │                            │
     │ docker run                  │ 内嵌 glibc
     ▼                            ▼
┌──────────────────────────────────────────┐
│          Strix 沙箱                       │
│  ghcr.io/usestrix/strix-sandbox:1.0.0    │
│  (AI 渗透测试隔离执行环境)                  │
└──────────────────────────────────────────┘
```

### 请求生命周期

```
POST /api/upload/domains
  │
  ├─► 上传 .txt 文件, 逐行解析域名
  ├─► 生成 task_id (UUID8)
  └─► launch_pipeline(task_id, domains)
        │
        ▼
  ┌─────────────────────────────────────────────────┐
  │ Celery Chain (= 严格顺序, │= 并行)               │
  │                                                 │
  │  Step 1: group(discover_subdomains)             │
  │          │每个根域名并行调用 subfinder           │
  │          │结果写入 domains 表                    │
  │          ▼                                      │
  │  Step 2: resolve_all_subdomains                 │
  │          │asyncio 并发 50 个 A/AAAA/CNAME 查询   │
  │          │过滤未解析域名,写入 dns_records        │
  │          ▼                                      │
  │  Step 3: filter_key_assets                      │
  │          │从 filter_rules 表读取关键词/正则       │
  │          │匹配的域名写入 assets 表,标记优先级      │
  │          ▼                                      │
  │  Step 4: group(scan_asset) + .join()            │
  │          │每个资产并行 docker run strix-agent     │
  │          │--concurrency=8 控制同时扫描数          │
  │          │结果写入 vulnerabilities 表            │
  │          │.join() 阻塞直到全部完成                │
  │          ▼                                      │
  │  Step 5: analyze_with_ai                        │
  │          │收集所有 strix 原始输出                 │
  │          │发送给 LLM (OpenAI/Claude/DeepSeek)    │
  │          │解析 JSON 响应,回写 vulnerability 记录  │
  │          ▼                                      │
  │  Callback: on_pipeline_success                  │
  │          │更新 task.status = "completed"         │
  │          │刷新各计数器                           │
  │          │Redis pub → WebSocket → 前端通知       │
  └─────────────────────────────────────────────────┘
```

### Strix Docker 沙箱（解决 glibc 兼容问题）

```
strix_wrapper.py
  │ subprocess.run(["strix", "--target", url, ...])
  ▼
/usr/local/bin/strix   ← strix-docker-wrapper.sh 透明代理
  │ docker run --rm --network host
  │   -v /var/run/docker.sock:/var/run/docker.sock
  │   -e STRIX_LLM=$STRIX_LLM  -e LLM_API_KEY=$LLM_API_KEY
  │   ghcr.io/usestrix/strix-agent:latest "$@"
  ▼
┌──────────────────────────────┐
│ strix-agent 镜像              │
│ ✅ Go 编译, 内嵌正确 glibc     │  ← 与宿主机 glibc 完全隔离
│ ✅ 独立 LLM 配置               │
│    │                          │
│    │ 渗透测试时:               │
│    ▼                          │
│ docker run ghcr.io/usestrix/  │
│   strix-sandbox:1.0.0         │  ← 代码执行隔离沙箱
└──────────────────────────────┘
```

### 数据模型

```
┌──────────┐     ┌──────────┐     ┌──────────┐     ┌───────────────┐
│  Task    │────→│  Domain  │────→│  Asset   │────→│ Vulnerability │
├──────────┤     ├──────────┤     ├──────────┤     ├───────────────┤
│ id       │     │ id       │     │ id       │     │ id            │
│ status   │     │ task_id  │     │ task_id  │     │ task_id       │
│ progress │     │ root_dom │     │ domain   │     │ asset_id      │
│ step     │     │ subdomain│     │ ips      │     │ cve_id        │
│ counts   │     │ resolved │     │ priority │     │ risk_score    │
│ context  │     │ ips      │     │ rules    │     │ component     │
│ error    │     │ source   │     │ ports    │     │ description   │
└──────────┘     └────┬─────┘     │ scanned  │     │ remediation   │
                      │           └──────────┘     │ raw_result    │
                      │                            │ ai_analysis   │
                      ▼                            └───────────────┘
               ┌──────────┐
               │DNSRecord │         ┌────────────┐
               ├──────────┤         │ FilterRule │
               │ subdomain│         ├────────────┤
               │ type     │         │ name       │
               │ value    │         │ rule_type  │
               │ ttl      │         │ pattern    │
               └──────────┘         │ priority   │
                                    │ enabled    │
                                    └────────────┘
```

## 🔧 核心流程

## 🎯 重点资产筛选规则

默认关键词列表：
`admin, api, vpn, portal, oa, dev, test, staging, backup, console, dashboard, login, manage, ops, monitor, grafana, jenkins, gitlab, kibana, k8s, swagger`

通过 Web 界面 (`/api/rules`) 可增删改查规则，支持：
- **关键词匹配**：域名包含指定字符串即视为重点资产
- **正则表达式**：支持复杂模式匹配

## 🤖 Agent 指令

通过 `/api/agent/command` 或 Web 界面，可发送自然语言指令动态调整扫描行为：

| 指令 | 效果 |
|------|------|
| "忽略所有 Redis 漏洞" | 设置 `task_context.skip_redis=true`，后续扫描跳过 Redis |
| "增加 SQL 注入深度 5" | 设置 `task_context.depth=5`，Strix 使用 `--depth 5` |
| "重新分析，关注认证绕过" | 触发重新分析，聚焦认证绕过相关漏洞 |

## 📊 API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/upload/domains` | 上传域名文件 |
| GET | `/api/tasks/` | 任务列表 |
| GET | `/api/tasks/{id}` | 任务详情 |
| POST | `/api/tasks/{id}/cancel` | 取消任务 |
| GET | `/api/rules/` | 筛选规则列表 |
| POST | `/api/rules/` | 添加规则 |
| DELETE | `/api/rules/{id}` | 删除规则 |
| POST | `/api/agent/command` | Agent 指令 |
| GET | `/api/reports/{task_id}` | 漏洞报告 |
| GET | `/api/reports/{task_id}/export` | 导出 CSV |
| WS | `/ws/{task_id}` | 实时日志 |

## 🛠️ 技术栈

- **后端**：FastAPI + Celery + Redis
- **数据库**：SQLite (默认) / PostgreSQL
- **子域名**：Subfinder (自动安装)
- **端口扫描**：Naabu / Python Socket
- **漏洞扫描**：Strix（通过 Docker 镜像运行，解决 glibc 兼容问题）
- **AI 分析**：OpenAI 兼容接口（支持 Claude、DeepSeek、Ollama 等）
- **前端 A**：Streamlit (快速原型)
- **前端 B**：Vue 3 + Element Plus + Nginx
- **容器化**：Docker Compose

## ⚙️ 配置说明

编辑 `.env` 文件：

```bash
# LLM 配置（必需）
LLM_API_KEY=sk-your-openai-key
LLM_API_BASE=https://api.openai.com/v1  # 或 Ollama: http://host:11434/v1
LLM_MODEL=gpt-4o

# 工具路径（容器内自动设置）
SUBFINDER_PATH=/usr/local/bin/subfinder
STRIX_PATH=/usr/local/bin/strix
```

## 📝 License

MIT
