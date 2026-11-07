#!/bin/zsh
# one-key.sh — 通用一键运维脚本（双模式：docker compose / native 进程管理）
# 用法：./scripts/one-key.sh [项目名] <动作>
#       ./scripts/one-key.sh <动作>   （项目名缺省时读取 output/last-task.json）
# 动作：start / stop / restart / build / status / --help
# 模式自动检测：仓库根目录有 docker-compose*.yml → docker；否则按 native 特征（pom.xml+frontend）→ native
# 日志：output/one-key-operation.log（native 运行日志：output/{REPO}-native.log / {REPO}-native-frontend.log）
set -uo pipefail

PIPELINE_ROOT="/Users/tigzx/workspace/ai-pipeline"
LOG_FILE="${PIPELINE_ROOT}/output/one-key-operation.log"
LAST_TASK="${PIPELINE_ROOT}/output/last-task.json"

mkdir -p "${PIPELINE_ROOT}/output"

log() { echo "$1" | tee -a "${LOG_FILE}"; }

usage() {
    cat <<EOF
用法：./scripts/one-key.sh [项目名] <动作>

动作（docker 与 native 通用）：
  start     后台启动全部服务（docker: compose up -d / native: 启动后端+前端双进程）
  stop      停止服务（docker: compose down / native: 按端口+PID 终止进程）
  restart   stop 后 start
  build     重新构建（docker: compose build / native: 后端 mvn package + 前端 npm run build）
  status    查看服务状态（docker: compose ps / native: 进程存活+端口探测）

联邦编排动作：
  services [start|stop|restart|status|health] [mem0|openviking|weknora|caddy|all]
            三层上下文联邦统一编排，转发至 scripts/pipeline-services.sh

示例：
  ./scripts/one-key.sh tigzx-dicom start      指定项目
  ./scripts/one-key.sh start                  使用 last-task.json 中的当前项目
  ./scripts/one-key.sh --help

日志：${LOG_FILE}
EOF
}

# ---------- 参数解析 ----------
if [ "${1:-}" = "services" ]; then
    shift
    exec "${PIPELINE_ROOT}/scripts/pipeline-services.sh" "$@"
fi
if [ "$1" = "-h" ] || [ "$1" = "--help" ] || [ "$1" = "help" ]; then usage; exit 0; fi

if [ $# -ge 2 ]; then
    PROJECT_NAME="$1"; ACTION="$2"
elif [ $# -eq 1 ]; then
    case "$1" in
        start|stop|restart|build|status)
            PROJECT_NAME=$(python3 -c "import json;print(json.load(open('${LAST_TASK}'))['repo'].rstrip('/').split('/')[-1])" 2>/dev/null || echo "")
            [ -z "${PROJECT_NAME}" ] && { echo "❌ 无法从 ${LAST_TASK} 解析项目名，请显式指定：./scripts/one-key.sh <项目名> <动作>"; exit 1; }
            ACTION="$1" ;;
        *) echo "❌ 参数错误：${1}"; usage; exit 1 ;;
    esac
else
    usage; exit 1
fi

REPO_DIR="${PIPELINE_ROOT}/repos/${PROJECT_NAME}"
if [ ! -d "${REPO_DIR}" ]; then
    echo "❌ 仓库目录不存在：${REPO_DIR}"
    exit 1
fi

# ---------- 部署模式自动检测 ----------
DEPLOY_MODE="unknown"
COMPOSE_FILE=""
for f in docker-compose.yml docker-compose.yaml compose.yml compose.yaml; do
    [ -f "${REPO_DIR}/${f}" ] && { COMPOSE_FILE="${f}"; DEPLOY_MODE="docker"; break; }
done
if [ "${DEPLOY_MODE}" = "unknown" ] && [ -f "${REPO_DIR}/backend/pom.xml" ] && [ -d "${REPO_DIR}/frontend" ]; then
    DEPLOY_MODE="native-java-node"
fi
if [ "${DEPLOY_MODE}" = "unknown" ]; then
    echo "❌ 无法识别 ${PROJECT_NAME} 的部署模式（未发现 compose 文件或已支持的 native 特征）"
    exit 1
fi

log "===== 【${PROJECT_NAME}】一键操作｜时间：$(date '+%Y-%m-%d %H:%M:%S') 模式：${DEPLOY_MODE} 操作：${ACTION} ====="

# ---------- docker 模式 ----------
run_docker() {
    if ! command -v docker >/dev/null 2>&1 || ! docker compose version >/dev/null 2>&1; then
        log "❌ docker/docker compose 不可用，请确认 OrbStack 已启动"; exit 1
    fi
    cd "${REPO_DIR}"
    case "${ACTION}" in
        start)
            log "▶️ docker compose -f ${COMPOSE_FILE} up -d"
            docker compose -f "${COMPOSE_FILE}" up -d 2>&1 | tee -a "${LOG_FILE}"
            log "✅ 启动完成" ;;
        stop)
            log "⏹️ docker compose -f ${COMPOSE_FILE} down"
            docker compose -f "${COMPOSE_FILE}" down 2>&1 | tee -a "${LOG_FILE}"
            log "✅ 服务已停止" ;;
        restart)
            log "🔄 docker compose down + up -d"
            docker compose -f "${COMPOSE_FILE}" down 2>&1 | tee -a "${LOG_FILE}"
            docker compose -f "${COMPOSE_FILE}" up -d 2>&1 | tee -a "${LOG_FILE}"
            log "✅ 重启完成" ;;
        build)
            log "🔨 docker compose -f ${COMPOSE_FILE} build"
            docker compose -f "${COMPOSE_FILE}" build 2>&1 | tee -a "${LOG_FILE}"
            log "✅ 构建完成，如需生效请执行 restart" ;;
        status)
            log "📊 容器状态："
            docker compose -f "${COMPOSE_FILE}" ps 2>&1 | tee -a "${LOG_FILE}" ;;
        *)
            log "❌ 未知动作：${ACTION}（docker 模式支持 start/stop/restart/build/status）"
            usage
            exit 1 ;;
    esac
}

# ---------- native 模式（Java Spring Boot 后端 + Node Vite 前端）----------
JAVA_HOME_DIR="/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home"
BACKEND_PID_FILE="${PIPELINE_ROOT}/output/${PROJECT_NAME}-native.pid"
FRONTEND_PID_FILE="${PIPELINE_ROOT}/output/${PROJECT_NAME}-native-frontend.pid"
BACKEND_LOG="${PIPELINE_ROOT}/output/${PROJECT_NAME}-native.log"
FRONTEND_LOG="${PIPELINE_ROOT}/output/${PROJECT_NAME}-native-frontend.log"
BACKEND_PORT=8080
FRONTEND_PORT=5173

native_env_check() {
    [ -d "${JAVA_HOME_DIR}" ] && export JAVA_HOME="${JAVA_HOME_DIR}" && export PATH="${JAVA_HOME}/bin:${PATH}"
    command -v java >/dev/null 2>&1 || { log "❌ java 不可用"; exit 1; }
    command -v mvn  >/dev/null 2>&1 || { log "❌ mvn 不可用"; exit 1; }
    command -v node >/dev/null 2>&1 || { log "❌ node 不可用"; exit 1; }
    command -v npm  >/dev/null 2>&1 || { log "❌ npm 不可用"; exit 1; }
}

native_start_backend() {
    log "▶️ 启动后端：cd backend && mvn spring-boot:run（日志 ${BACKEND_LOG}）"
    cd "${REPO_DIR}/backend"
    nohup mvn spring-boot:run > "${BACKEND_LOG}" 2>&1 &
    echo $! > "${BACKEND_PID_FILE}"
    log "⏳ 等待后端端口 ${BACKEND_PORT} 就绪（最多 180s）..."
    local i=0
    while [ $i -lt 180 ]; do
        if lsof -nP -iTCP:${BACKEND_PORT} -sTCP:LISTEN >/dev/null 2>&1; then break; fi
        sleep 1; i=$((i+1))
        if ! kill -0 "$(cat "${BACKEND_PID_FILE}")" 2>/dev/null; then
            log "❌ 后端进程启动失败，日志尾部："; tail -20 "${BACKEND_LOG}" | tee -a "${LOG_FILE}"; return 1
        fi
    done
    if lsof -nP -iTCP:${BACKEND_PORT} -sTCP:LISTEN >/dev/null 2>&1; then
        log "✅ 后端就绪：http://127.0.0.1:${BACKEND_PORT}（PID $(cat "${BACKEND_PID_FILE}")）"
    else
        log "⚠️ 后端 ${BACKEND_PORT} 端口未就绪，请检查 ${BACKEND_LOG}"
        return 1
    fi
}

native_start_frontend() {
    log "▶️ 启动前端：cd frontend && npm run dev -- --host 0.0.0.0（日志 ${FRONTEND_LOG}）"
    cd "${REPO_DIR}/frontend"
    nohup npm run dev -- --host 0.0.0.0 > "${FRONTEND_LOG}" 2>&1 &
    echo $! > "${FRONTEND_PID_FILE}"
    local i=0
    while [ $i -lt 60 ]; do
        if lsof -nP -iTCP:${FRONTEND_PORT} -sTCP:LISTEN >/dev/null 2>&1; then break; fi
        sleep 1; i=$((i+1))
        if ! kill -0 "$(cat "${FRONTEND_PID_FILE}")" 2>/dev/null; then
            log "❌ 前端进程启动失败，日志尾部："; tail -20 "${FRONTEND_LOG}" | tee -a "${LOG_FILE}"; return 1
        fi
    done
    if lsof -nP -iTCP:${FRONTEND_PORT} -sTCP:LISTEN >/dev/null 2>&1; then
        log "✅ 前端就绪：http://127.0.0.1:${FRONTEND_PORT}（PID $(cat "${FRONTEND_PID_FILE}")）"
    else
        log "⚠️ 前端 ${FRONTEND_PORT} 端口未就绪，请检查 ${FRONTEND_LOG}"
        return 1
    fi
}

native_stop() {
    for port in ${BACKEND_PORT} ${FRONTEND_PORT}; do
        local pids=$(lsof -nP -tiTCP:${port} -sTCP:LISTEN 2>/dev/null)
        if [ -n "${pids}" ]; then
            log "⏹️ 终止端口 ${port} 进程：${pids}"
            echo "${pids}" | xargs kill 2>/dev/null
        fi
    done
    for pf in "${BACKEND_PID_FILE}" "${FRONTEND_PID_FILE}"; do
        if [ -f "${pf}" ]; then
            local pid=$(cat "${pf}")
            kill -0 "${pid}" 2>/dev/null && { log "⏹️ 终止 PID ${pid}（${pf}）"; kill "${pid}" 2>/dev/null; }
            rm -f "${pf}"
        fi
    done
    pkill -f "spring-boot:run" 2>/dev/null
    # 等待端口真正释放（Spring Boot 优雅关闭需数秒；要求连续 3 次检测空闲，防 socket 重启间隙误判）
    local wi=0 ok=0
    while [ $wi -lt 30 ] && [ $ok -lt 3 ]; do
        if ! lsof -nP -iTCP:${BACKEND_PORT} -sTCP:LISTEN >/dev/null 2>&1 && ! lsof -nP -iTCP:${FRONTEND_PORT} -sTCP:LISTEN >/dev/null 2>&1; then
            ok=$((ok+1))
        else
            ok=0
        fi
        sleep 1; wi=$((wi+1))
    done
    # 仍在监听则强制 SIGKILL
    for port in ${BACKEND_PORT} ${FRONTEND_PORT}; do
        local left=$(lsof -nP -tiTCP:${port} -sTCP:LISTEN 2>/dev/null)
        [ -n "${left}" ] && { log "⚡ 端口 ${port} 仍在监听（${left}），SIGKILL 强制终止"; echo "${left}" | xargs kill -9 2>/dev/null; }
    done
    sleep 2
    log "✅ 停止完成"
}

run_native() {
    case "${ACTION}" in
        start)
            native_env_check
            # StarRocks 依赖检查：native 项目的数据库容器（starrocks-tigzx）需在运行
            if docker ps --format '{{.Names}}' 2>/dev/null | grep -q '^starrocks-tigzx$'; then
                log "✅ StarRocks 容器（starrocks-tigzx）运行中"
            elif docker ps -a --format '{{.Names}}' 2>/dev/null | grep -q '^starrocks-tigzx$'; then
                log "▶️ 启动已存在但停止的 StarRocks 容器"
                docker start starrocks-tigzx 2>&1 | tee -a "${LOG_FILE}"
                log "⏳ 等待 StarRocks 9030 就绪（最多 120s）..."
                local si=0
                while [ $si -lt 120 ]; do
                    docker exec starrocks-tigzx bash -c "echo > /dev/tcp/127.0.0.1/9030" 2>/dev/null && break
                    sleep 1; si=$((si+1))
                done
                [ $si -lt 120 ] && log "✅ StarRocks 9030 就绪" || log "⚠️ StarRocks 9030 未就绪（docker logs starrocks-tigzx 查看）"
            else
                log "⚠️ StarRocks 容器不存在（首次部署请执行 /tmp/starrocks-setup.sh 或参考部署日志）"
            fi
            if lsof -nP -iTCP:${BACKEND_PORT} -sTCP:LISTEN >/dev/null 2>&1; then
                log "⚠️ 端口 ${BACKEND_PORT} 已被占用（项目有进程锁，禁止重复启动），如需重启请先 stop"
                exit 1
            fi
            [ -d "${REPO_DIR}/frontend/node_modules" ] || { log "📦 前端依赖缺失，先执行 npm ci"; (cd "${REPO_DIR}/frontend" && npm ci 2>&1 | tail -3 | tee -a "${LOG_FILE}"); }
            native_start_backend && native_start_frontend ;;
        stop)
            native_stop ;;
        restart)
            native_env_check
            native_stop
            native_start_backend && native_start_frontend ;;
        build)
            native_env_check
            log "🔨 后端构建：mvn -f backend/pom.xml package -DskipTests"
            (cd "${REPO_DIR}" && mvn -f backend/pom.xml package -DskipTests 2>&1 | tail -8 | tee -a "${LOG_FILE}")
            log "🔨 前端构建：npm --prefix frontend run build"
            (cd "${REPO_DIR}" && npm --prefix frontend run build 2>&1 | tail -8 | tee -a "${LOG_FILE}")
            log "✅ 构建完成" ;;
        status)
            native_env_check
            log "📊 后端端口 ${BACKEND_PORT}：$(lsof -nP -iTCP:${BACKEND_PORT} -sTCP:LISTEN 2>/dev/null | tail -n +2 | awk '{print $1" pid:"$2}' | head -3 | tr '\n' ' ')"
            log "📊 前端端口 ${FRONTEND_PORT}：$(lsof -nP -iTCP:${FRONTEND_PORT} -sTCP:LISTEN 2>/dev/null | tail -n +2 | awk '{print $1" pid:"$2}' | head -3 | tr '\n' ' ')"
            [ -f "${BACKEND_PID_FILE}" ] && log "📄 后端 PID 文件：$(cat "${BACKEND_PID_FILE}")"
            [ -f "${FRONTEND_PID_FILE}" ] && log "📄 前端 PID 文件：$(cat "${FRONTEND_PID_FILE}")"
            curl -s -o /dev/null -w "📊 后端 HTTP 探测：http://127.0.0.1:${BACKEND_PORT} → %{http_code}\n" "http://127.0.0.1:${BACKEND_PORT}" | tee -a "${LOG_FILE}"
            curl -s -o /dev/null -w "📊 前端 HTTP 探测：http://127.0.0.1:${FRONTEND_PORT} → %{http_code}\n" "http://127.0.0.1:${FRONTEND_PORT}" | tee -a "${LOG_FILE}" ;;
        *)
            log "❌ 未知动作：${ACTION}（native 模式支持 start/stop/restart/build/status）"
            usage
            exit 1 ;;
    esac
}

case "${DEPLOY_MODE}" in
    docker) run_docker ;;
    native-java-node) run_native ;;
esac
