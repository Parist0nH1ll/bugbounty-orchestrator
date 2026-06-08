# AI 驱动全自动漏洞挖掘平台

> 全自动流水线：子域名发现 → DNS 解析 → 重点资产筛选 → Strix 漏洞扫描 → AI 智能分析

## 🚀 快速开始

### 前置条件

- Docker 20.10+ & Docker Compose 2.0+
- （可选）已安装 Subfinder / Naabu / Strix 或由 Docker 自动下载

### 一键部署

```bash
# 1. 克隆项目
git clone <your-repo-url> orchestrator
cd orchestrator

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env，填入你的 LLM API KEY（OpenAI / Ollama）

# 3. 启动所有服务
docker-compose up -d

# 4. 查看运行状态
docker-compose ps
```

### 服务端口

| 服务 | 端口 | 说明 |
|------|------|------|
| FastAPI | 8000 | 后端 API 接口 |
| Streamlit | 8501 | Web 控制台（快速原型） |
| Redis | 6379 | 消息队列 & 缓存 |
| Celery Worker | - | 后台任务执行 |

### 本地开发（不使用 Docker）

```bash
# 一键安装所有依赖（Python包、Redis、Subfinder、Naabu、Strix）
bash scripts/setup.sh

# 编辑 .env 配置 LLM API Key
nano .env

# 终端 1: 启动 FastAPI
python3 -m uvicorn app.main:app --reload --port 8000

# 终端 2: 启动 Celery Worker
celery -A app.tasks.celery_app worker --loglevel=info --concurrency=8

# 终端 3: 启动 Streamlit 前端
streamlit run streamlit_app.py

# 访问 http://localhost:8501
```

`scripts/setup.sh` 做了什么：
1. 检测系统 (macOS/Ubuntu)
2. 安装 Python3 + pip
3. `pip install -r requirements.txt`
4. 安装并启动 Redis
5. 安装 Subfinder (子域名发现)
6. 安装 Naabu (端口扫描，可选)
7. 安装 Strix (AI 安全扫描)
8. 初始化数据库 + 创建 `.env`

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
