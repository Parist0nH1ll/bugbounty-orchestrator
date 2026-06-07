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

## 🔧 核心流程

```
用户上传域名文件
   │
   ▼
[1] Subfinder 子域名发现 (并行 per domain)
   │
   ▼
[2] DNS 解析确认 (A/AAAA/CNAME, 并发 50)
   │
   ▼
[3] 重点资产筛选 (关键词/正则匹配)
   │
   ▼
[4] Strix 漏洞扫描 (并行 per asset)
   │
   ▼
[5] LLM AI 智能分析 (高危漏洞提取)
   │
   ▼
输出：Web 报告 + CSV 导出
```

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
- **漏洞扫描**：Strix (需自行安装或挂载)
- **AI 分析**：OpenAI API 兼容 (支持 Ollama 等代理)
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
# bugbounty-orchestrator
