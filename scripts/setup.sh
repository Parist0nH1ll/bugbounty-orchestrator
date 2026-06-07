#!/usr/bin/env bash
# ============================================================
# AI 漏洞挖掘平台 - 一键依赖安装脚本
# 支持 macOS (Homebrew) 和 Ubuntu/Debian (apt)
# 用法: bash scripts/setup.sh
# ============================================================
set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

log_info()  { echo -e "${GREEN}[✓]${NC} $1"; }
log_warn()  { echo -e "${YELLOW}[!]${NC} $1"; }
log_error() { echo -e "${RED}[✗]${NC} $1"; }
log_step()  { echo -e "\n${CYAN}==>${NC} $1"; }

# -----------------------------------------------------------
# 0. 检测系统
# -----------------------------------------------------------
detect_os() {
    case "$(uname -s)" in
        Darwin)  OS="macos" ;;
        Linux)   OS="linux"
                 if [ -f /etc/os-release ]; then
                     . /etc/os-release
                     DISTRO="$ID"
                 fi ;;
        *)       log_error "不支持的操作系统"; exit 1 ;;
    esac
    log_info "检测到系统: $OS${DISTRO:+ ($DISTRO)}"
}

# -----------------------------------------------------------
# 1. Python3 + pip
# -----------------------------------------------------------
install_python() {
    log_step "1/7 Python3 + pip"
    if command -v python3 &>/dev/null; then
        log_info "python3 已安装: $(python3 --version)"
    else
        log_warn "正在安装 python3..."
        case "$OS" in
            macos) brew install python@3.11 ;;
            linux) sudo apt-get update -qq && sudo apt-get install -y -qq python3 python3-pip python3-dev ;;
        esac
        log_info "python3 安装完成"
    fi

    if command -v pip3 &>/dev/null; then
        PIP="pip3"
    elif python3 -m pip --version &>/dev/null; then
        PIP="python3 -m pip"
    else
        log_warn "正在安装 pip..."
        curl -sS https://bootstrap.pypa.io/get-pip.py | python3
        PIP="pip3"
    fi
    log_info "pip 可用: $($PIP --version)"
}

# -----------------------------------------------------------
# 2. Python 依赖包
# -----------------------------------------------------------
install_python_deps() {
    log_step "2/7 Python 依赖包"
    cd "$PROJECT_DIR"
    $PIP install --upgrade pip -q
    $PIP install -r requirements.txt -q
    log_info "Python 依赖安装完成"
}

# -----------------------------------------------------------
# 3. Redis
# -----------------------------------------------------------
install_redis() {
    log_step "3/7 Redis"
    if command -v redis-server &>/dev/null && redis-cli ping &>/dev/null; then
        log_info "Redis 已运行: $(redis-cli --version)"
        return
    fi

    if command -v redis-server &>/dev/null; then
        log_info "redis-server 已安装，正在启动..."
        redis-server --daemonize yes --port 6379 2>/dev/null || true
        sleep 1
        if redis-cli ping &>/dev/null; then
            log_info "Redis 启动成功"
            return
        fi
    fi

    log_warn "正在安装 Redis..."
    case "$OS" in
        macos)
            brew install redis && brew services start redis
            ;;
        linux)
            sudo apt-get update -qq && sudo apt-get install -y -qq redis-server
            sudo systemctl enable redis-server && sudo systemctl start redis-server
            ;;
    esac
    sleep 2
    if redis-cli ping &>/dev/null; then
        log_info "Redis 安装并启动成功"
    else
        log_error "Redis 启动失败，请手动安装"
    fi
}

# -----------------------------------------------------------
# 4. Subfinder
# -----------------------------------------------------------
install_subfinder() {
    log_step "4/7 Subfinder (子域名发现)"
    if command -v subfinder &>/dev/null; then
        log_info "subfinder 已安装: $(subfinder -version 2>&1 | head -1)"
        return
    fi

    log_warn "正在安装 subfinder..."
    case "$OS" in
        macos)
            brew install subfinder
            ;;
        linux)
            SUBFINDER_VER="2.6.6"
            wget -q "https://github.com/projectdiscovery/subfinder/releases/download/v${SUBFINDER_VER}/subfinder_${SUBFINDER_VER}_linux_amd64.zip" \
                -O /tmp/subfinder.zip
            unzip -o /tmp/subfinder.zip -d /tmp/subfinder_out
            sudo mv /tmp/subfinder_out/subfinder /usr/local/bin/
            sudo chmod +x /usr/local/bin/subfinder
            rm -rf /tmp/subfinder.zip /tmp/subfinder_out
            ;;
    esac
    if command -v subfinder &>/dev/null; then
        log_info "subfinder 安装完成"
    else
        log_warn "subfinder 安装失败，不影响主流程（可使用回退模式）"
    fi
}

# -----------------------------------------------------------
# 5. Naabu (可选)
# -----------------------------------------------------------
install_naabu() {
    log_step "5/7 Naabu (快速端口扫描，可选)"
    if command -v naabu &>/dev/null; then
        log_info "naabu 已安装: $(naabu -version 2>&1 | head -1)"
        return
    fi

    log_warn "正在安装 naabu..."
    case "$OS" in
        macos)
            brew install naabu 2>/dev/null || log_warn "brew 安装失败，跳过 naabu"
            ;;
        linux)
            NAABU_VER="2.3.1"
            wget -q "https://github.com/projectdiscovery/naabu/releases/download/v${NAABU_VER}/naabu_${NAABU_VER}_linux_amd64.zip" \
                -O /tmp/naabu.zip
            unzip -o /tmp/naabu.zip -d /tmp/naabu_out
            sudo mv /tmp/naabu_out/naabu /usr/local/bin/
            sudo chmod +x /usr/local/bin/naabu
            rm -rf /tmp/naabu.zip /tmp/naabu_out
            ;;
    esac
    if command -v naabu &>/dev/null; then
        log_info "naabu 安装完成"
    else
        log_warn "naabu 不可用，将回退为 Python socket 端口扫描"
    fi
}

# -----------------------------------------------------------
# 6. Strix (AI 安全扫描)
# -----------------------------------------------------------
install_strix() {
    log_step "6/7 Strix (AI 驱动安全扫描)"
    if command -v strix &>/dev/null; then
        log_info "strix 已安装: $(strix --version 2>&1 | head -1)"
        return
    fi

    log_warn "正在通过 pip 安装 strix-agent..."

    # 尝试 pipx（推荐）
    if command -v pipx &>/dev/null; then
        pipx install strix-agent 2>/dev/null && log_info "strix (pipx) 安装完成" && return
    else
        # 安装 pipx
        $PIP install pipx -q 2>/dev/null
        if command -v pipx &>/dev/null; then
            pipx install strix-agent 2>/dev/null && log_info "strix (pipx) 安装完成" && return
        fi
    fi

    # 回退到 pip
    $PIP install strix-agent -q 2>/dev/null && log_info "strix (pip) 安装完成" && return

    log_warn "strix 安装失败。不影响主流程（将使用 mock 结果）"
    log_warn "手动安装: pipx install strix-agent 或 pip install strix-agent"
}

# -----------------------------------------------------------
# 7. 初始化数据库 + 创建目录
# -----------------------------------------------------------
init_project() {
    log_step "7/7 项目初始化"
    cd "$PROJECT_DIR"

    mkdir -p data scan_results output

    # 如果 .env 不存在，从模板创建
    if [ ! -f .env ]; then
        cp .env.example .env
        log_warn ".env 文件已从模板创建，请编辑填入 LLM_API_KEY"
    fi

    # 初始化数据库
    python3 scripts/init_db.py
    log_info "数据库初始化完成"
}

# -----------------------------------------------------------
# 最终检查
# -----------------------------------------------------------
final_check() {
    echo ""
    echo "============================================"
    echo "  依赖安装检查清单"
    echo "============================================"

    check() {
        local name="$1"
        local cmd="$2"
        local required="${3:-yes}"
        if $cmd &>/dev/null; then
            echo -e "  ${GREEN}✓${NC} $name"
            return 0
        else
            if [ "$required" = "yes" ]; then
                echo -e "  ${RED}✗${NC} $name - 必须安装"
                return 1
            else
                echo -e "  ${YELLOW}○${NC} $name - 未安装（可选）"
                return 0
            fi
        fi
    }

    all_ok=true
    check "Python3"     "python3 --version"               || all_ok=false
    check "pip"         "$PIP --version"                   || all_ok=false
    check "Redis"       "redis-cli ping"                   || all_ok=false
    check "Subfinder"   "subfinder -version 2>/dev/null"   "optional"
    check "Naabu"       "naabu -version 2>/dev/null"        "optional"
    check "Strix"       "strix --version 2>/dev/null"       "optional"

    echo ""
    if $all_ok; then
        echo -e "${GREEN}所有必需依赖已就绪！${NC}"
        echo ""
        echo "  启动 API 服务:  python3 -m uvicorn app.main:app --reload --port 8000"
        echo "  启动 Worker:    celery -A app.tasks.celery_app worker -l info -c 8"
        echo "  启动前端:       streamlit run streamlit_app.py"
        echo "  编辑配置:       nano .env"
    else
        echo -e "${RED}部分必需依赖缺失，请检查后重试${NC}"
    fi
}

# ============================================================
# 主流程
# ============================================================
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

echo ""
echo "============================================"
echo "  AI 漏洞挖掘平台 - 一键安装脚本"
echo "============================================"

detect_os
install_python
install_python_deps
install_redis
install_subfinder
install_naabu
install_strix
init_project
final_check
