#!/usr/bin/env bash
# ============================================================
# Strix Docker 透明代理
# 所有 strix CLI 调用转发到官方镜像，解决 glibc 版本兼容问题
#
# 镜像: ghcr.io/usestrix/strix-agent:latest
# 沙箱: ghcr.io/usestrix/strix-sandbox:1.0.0  (自动拉取)
#
# 用法与原生 strix 完全一致:
#   strix --target https://example.com --instruction "..."
# ============================================================
set -e

STRIX_IMAGE="${STRIX_DOCKER_IMAGE:-ghcr.io/usestrix/strix-agent:latest}"

# ---------- 检测 Docker ----------
if ! command -v docker &>/dev/null; then
    echo '{"error": "Docker not available. Please install Docker to use strix."}' >&2
    exit 1
fi

# ---------- 首次使用时拉取镜像 ----------
if ! docker image inspect "$STRIX_IMAGE" &>/dev/null 2>&1; then
    echo "[strix] Pulling $STRIX_IMAGE ..." >&2
    docker pull "$STRIX_IMAGE" >&2 || {
        echo "{\"error\": \"Failed to pull $STRIX_IMAGE\"}" >&2
        exit 1
    }
fi

# ---------- 透传环境变量 ----------
ENV_ARGS=""
for var in STRIX_LLM LLM_API_KEY OPENAI_API_KEY ANTHROPIC_API_KEY DEEPSEEK_API_KEY STRIX_TIMEOUT; do
    if [ -n "${!var:-}" ]; then
        ENV_ARGS="$ENV_ARGS -e $var=${!var}"
    fi
done

# ---------- 透传 Docker socket（strix 需要启动沙箱容器）----------
# 容器内路径 vs 宿主机路径
if [ -S /var/run/docker.sock ]; then
    SOCK_MOUNT="-v /var/run/docker.sock:/var/run/docker.sock"
else
    SOCK_MOUNT=""
fi

# ---------- 结果输出目录挂载 ----------
if [ -d /app/scan_results ]; then
    RESULT_MOUNT="-v /app/scan_results:/app/scan_results"
elif [ -d "$(pwd)/scan_results" ]; then
    RESULT_MOUNT="-v $(pwd)/scan_results:/app/scan_results"
else
    RESULT_MOUNT=""
fi

# ---------- 执行 ----------
exec docker run --rm \
    --network host \
    $SOCK_MOUNT \
    $RESULT_MOUNT \
    $ENV_ARGS \
    "$STRIX_IMAGE" \
    "$@"
