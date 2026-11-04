#!/bin/zsh
# one-key.sh — WeKnora 一键运维脚本
# 动作：start / stop / restart / build / status
# 适配 OrbStack + Apple Silicon；操作记录写入 output/one-key-operation.log
set -euo pipefail

PROJECT_NAME="WeKnora"
PIPELINE_ROOT="/Users/tigzx/workspace/ai-pipeline"
REPO_DIR="${PIPELINE_ROOT}/repos/${PROJECT_NAME}"
LOG_FILE="${PIPELINE_ROOT}/output/one-key-operation.log"

usage() {
    cat <<EOF
用法：./scripts/one-key.sh <动作>

动作：
  start     后台启动全部服务（docker compose up -d）
  stop      停止并销毁容器（docker compose down）
  restart   停止后重新拉起服务（down + up -d）
  build     重新构建 docker 镜像（修改代码/静态资源后执行；不自动重启）
  status    查看容器运行状态（docker compose ps）

示例（在 ai-pipeline 根目录执行）：
  ./scripts/one-key.sh start
  ./scripts/one-key.sh stop
  ./scripts/one-key.sh restart
  ./scripts/one-key.sh build
  ./scripts/one-key.sh status

日志：${LOG_FILE}
EOF
}

# 前置：docker / docker compose 可用性检查
if ! command -v docker >/dev/null 2>&1; then
    echo "❌ 未检测到 docker 命令，请确认 OrbStack 已启动"
    exit 1
fi
if ! docker compose version >/dev/null 2>&1; then
    echo "❌ docker compose 不可用，请确认 OrbStack/Docker 已启动"
    exit 1
fi

# 仓库目录检查
if [ ! -d "${REPO_DIR}" ]; then
    echo "❌ 仓库目录不存在：${REPO_DIR}"
    exit 1
fi

cd "${REPO_DIR}"

# 自动识别 compose 文件（按常见命名优先级）
COMPOSE_FILE=""
for f in docker-compose.yml docker-compose.yaml compose.yml compose.yaml; do
    if [ -f "${f}" ]; then
        COMPOSE_FILE="${f}"
        break
    fi
done

if [ -z "${COMPOSE_FILE}" ]; then
    echo "❌ 在 ${REPO_DIR} 没有找到 docker compose 配置文件"
    exit 1
fi

ACTION="${1:-}"
if [ -z "${ACTION}" ]; then
    usage
    exit 1
fi

# 确保日志目录存在
mkdir -p "$(dirname "${LOG_FILE}")"

log() {
    echo "$1" | tee -a "${LOG_FILE}"
}

# 统一执行 compose 并记录日志；pipefail 保证 docker 失败时整体非零退出
run_compose() {
    docker compose -f "${COMPOSE_FILE}" "$@" 2>&1 | tee -a "${LOG_FILE}"
}

log "===== 【${PROJECT_NAME}】一键操作｜时间：$(date '+%Y-%m-%d %H:%M:%S') 操作：${ACTION} ====="

case "${ACTION}" in
    start)
        log "▶️ 启动服务：docker compose -f ${COMPOSE_FILE} up -d"
        run_compose up -d
        log "✅ 启动完成，访问地址：http://localhost:8080（前端 http://localhost）"
        ;;
    stop)
        log "⏹️ 停止服务：docker compose -f ${COMPOSE_FILE} down"
        run_compose down
        log "✅ 服务已停止"
        ;;
    restart)
        log "🔄 重启服务（down + up -d）"
        run_compose down
        run_compose up -d
        log "✅ 重启完成，访问地址：http://localhost:8080（前端 http://localhost）"
        ;;
    build)
        log "🔨 重新构建镜像：docker compose -f ${COMPOSE_FILE} build"
        run_compose build
        log "✅ 镜像构建完成，如需生效请执行：./scripts/one-key.sh restart"
        ;;
    status)
        log "📊 当前容器状态"
        run_compose ps
        ;;
    -h|--help|help)
        usage
        ;;
    *)
        echo "❌ 参数错误：${ACTION}"
        usage
        exit 1
        ;;
esac
