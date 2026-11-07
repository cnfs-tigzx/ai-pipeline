#!/bin/zsh
# mem0-one-key.sh — Mem0 一键运维脚本（P3）
# 动作：start / stop / restart / build / status
# 适配：mem0 docker 模式（compose 位于 repos/mem0/server/），OrbStack + Apple Silicon
# 操作记录追加写入 output/one-key-operation.log
set -euo pipefail

PROJECT_NAME="mem0"
PIPELINE_ROOT="/Users/tigzx/workspace/ai-pipeline"
REPO_DIR="${PIPELINE_ROOT}/repos/${PROJECT_NAME}/server"
LOG_FILE="${PIPELINE_ROOT}/output/one-key-operation.log"

API_URL="http://localhost:8888"
DASHBOARD_URL="http://localhost:3000"

usage() {
    cat <<EOF
用法：./scripts/mem0-one-key.sh <动作>

动作：
  start     启动全部服务（docker compose up -d，含 postgres/mem0/dashboard）
  stop      停止并销毁容器（docker compose down；数据卷 postgres_db 保留）
  restart   停止后重新拉起服务（down + up -d）
  build     重新构建 mem0 与 dashboard 镜像（修改代码后执行；不自动重启）
  status    查看容器状态 + API/Dashboard HTTP 健康探测

示例（在 ai-pipeline 根目录执行）：
  ./scripts/mem0-one-key.sh start
  ./scripts/mem0-one-key.sh status
  ./scripts/mem0-one-key.sh build

访问地址：
  Dashboard:      ${DASHBOARD_URL}
  API:            ${API_URL}
  OpenAPI 文档:   ${API_URL}/docs

数据持久化：docker volume mem0-dev_postgres_db（stop/down 不删除）
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

# 自动识别 compose 文件（mem0 为 docker-compose.yaml，仍按通用命名兜底）
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

# HTTP 探测（状态汇总用，不因非 200 中断脚本）
probe() {
    local name="$1" url="$2"
    local code
    code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 8 "${url}" || echo 000)
    if [ "${code}" = "200" ]; then
        echo "  ${name}: ${url} → ${code} ✅"
    else
        echo "  ${name}: ${url} → ${code} ⚠️"
    fi
}

wait_api() {
    echo "⏳ 等待 API 就绪（最多 90s）..."
    local i=0
    until curl -fsS --max-time 5 "${API_URL}/auth/setup-status" >/dev/null 2>&1; do
        i=$((i + 5))
        if [ "${i}" -ge 90 ]; then
            echo "⚠️ API 90s 内未就绪，请检查：docker compose logs mem0"
            return 0
        fi
        sleep 5
    done
    echo "✅ API 已就绪"
}

log "===== 【${PROJECT_NAME}】一键操作｜时间：$(date '+%Y-%m-%d %H:%M:%S') 操作：${ACTION} ====="

case "${ACTION}" in
    start)
        log "▶️ 启动服务：docker compose -f ${REPO_DIR}/${COMPOSE_FILE} up -d"
        run_compose up -d
        wait_api
        log "✅ 启动完成，Dashboard: ${DASHBOARD_URL} ｜ API: ${API_URL}"
        ;;
    stop)
        log "⏹️ 停止服务：docker compose -f ${REPO_DIR}/${COMPOSE_FILE} down"
        run_compose down
        log "✅ 服务已停止（postgres 数据卷 mem0-dev_postgres_db 已保留）"
        ;;
    restart)
        log "🔄 重启服务（down + up -d）"
        run_compose down
        run_compose up -d
        wait_api
        log "✅ 重启完成，Dashboard: ${DASHBOARD_URL} ｜ API: ${API_URL}"
        ;;
    build)
        log "🔨 重新构建镜像：docker compose -f ${REPO_DIR}/${COMPOSE_FILE} build"
        run_compose build
        log "✅ 镜像构建完成，如需生效请执行：./scripts/mem0-one-key.sh restart"
        ;;
    status)
        log "📊 当前容器状态"
        run_compose ps
        echo "HTTP 健康探测：" | tee -a "${LOG_FILE}"
        probe "Dashboard" "${DASHBOARD_URL}/api/health" | tee -a "${LOG_FILE}"
        probe "API(docs)" "${API_URL}/docs" | tee -a "${LOG_FILE}"
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
