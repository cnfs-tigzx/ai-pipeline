#!/usr/bin/env bash
# pipeline-services.sh — 三层上下文联邦统一编排（无侵入原则：各栈沿用自身 compose 文件与项目名）
# 栈清单：mem0（经验记忆层）· openviking（项目资产层）· weknora（业务门户层）· caddy（统一入口门户 :9000）
# 用法: pipeline-services.sh <start|stop|restart|status|health> [mem0|openviking|weknora|caddy|all]
# 日志: output/pipeline-services.log
set -uo pipefail

ROOT="/Users/tigzx/workspace/ai-pipeline"
LOG="${ROOT}/output/pipeline-services.log"
mkdir -p "${ROOT}/output"
log() { echo "$1" | tee -a "${LOG}"; }

stack_dir() {
    case "$1" in
        mem0)       echo "${ROOT}/repos/mem0/server" ;;
        openviking) echo "${ROOT}/repos/OpenViking" ;;
        weknora)    echo "${ROOT}/repos/WeKnora" ;;
        caddy)      echo "${ROOT}/docker/pipeline-caddy" ;;
        *)          echo "" ;;
    esac
}

stacks_for() {
    case "$1" in
        mem0|openviking|weknora|caddy) echo "$1" ;;
        *) echo "mem0 openviking weknora caddy" ;;
    esac
}

compose_up() {
    local s="$1" d cf
    d=$(stack_dir "$s"); cf=$(ls "${d}"/docker-compose.y*ml 2>/dev/null | head -1)
    if [ -z "${cf}" ]; then log "❌ [${s}] 未找到 compose 文件（${d}）"; return 1; fi
    log "▶️ [${s}] docker compose -f $(basename "${cf}") up -d"
    (cd "${d}" && docker compose -f "$(basename "${cf}")" up -d) 2>&1 | tee -a "${LOG}"
}

compose_down() {
    local s="$1" d cf
    d=$(stack_dir "$s"); cf=$(ls "${d}"/docker-compose.y*ml 2>/dev/null | head -1)
    if [ -z "${cf}" ]; then log "❌ [${s}] 未找到 compose 文件（${d}）"; return 1; fi
    log "⏹️ [${s}] docker compose -f $(basename "${cf}") down"
    (cd "${d}" && docker compose -f "$(basename "${cf}")" down) 2>&1 | tee -a "${LOG}"
}

probe() {
    local name="$1" url="$2" code
    code=$(curl -s -o /dev/null -m 5 -w '%{http_code}' "$url" 2>/dev/null)
    printf '   %-22s %-38s %s\n' "${name}" "${url}" "${code}"
    echo "   probe ${name} ${url} -> ${code}" >> "${LOG}"
}

do_start() { for s in $(stacks_for "$TARGET"); do compose_up "$s"; done; }
do_stop()  { for s in $(stacks_for "$TARGET"); do compose_down "$s"; done; }

do_health() {
    log "🩺 健康探测（${TARGET}）"
    case "$TARGET" in
        all|mem0)       probe "mem0 API"      "http://localhost:8888/docs"
                        probe "mem0 Dashboard" "http://localhost:3000" ;;
        all|openviking) probe "OpenViking"    "http://localhost:1933/health" ;;
        all|weknora)    probe "WeKnora Web"   "http://localhost/"
                        probe "WeKnora API"   "http://localhost:8080/health" ;;
    esac
    case "$TARGET" in
        all|caddy)      probe "统一门户"      "http://localhost:9000/"
                        probe "门户·weknora"  "http://weknora.localhost:9000/"
                        probe "门户·mem0"     "http://mem0.localhost:9000/"
                        probe "门户·studio"   "http://studio.localhost:9000/" ;;
    esac
}

do_status() {
    log "📊 联邦容器全景（${TARGET}）"
    local pat="pipeline-caddy"
    case "$TARGET" in
        all)        pat='mem0|openviking|caddy|WeKnora' ;;
        mem0)       pat='mem0' ;;
        openviking) pat='openviking' ;;
        weknora)    pat='WeKnora' ;;
        caddy)      pat='pipeline-caddy' ;;
    esac
    docker ps -a --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' 2>/dev/null \
        | awk -v p="${pat}" 'NR==1 || $0 ~ p' | tee -a "${LOG}"
    do_health
    log "💾 内存占用（联邦容器）"
    docker stats --no-stream --format 'table {{.Name}}\t{{.MemUsage}}\t{{.CPUPerc}}' 2>/dev/null \
        | awk -v p="${pat}" 'NR==1 || $0 ~ p' | tee -a "${LOG}"
}

[ $# -ge 1 ] || { sed -n '2,7p' "$0"; exit 1; }
ACTION="$1"
TARGET="${2:-all}"
case "$ACTION" in
    start)   do_start ;;
    stop)    do_stop ;;
    restart) do_stop; do_start ;;
    status)  do_status ;;
    health)  do_health ;;
    *) sed -n '2,7p' "$0"; exit 1 ;;
esac
log "✔ 动作完成：${ACTION} ${TARGET} @ $(date '+%Y-%m-%d %H:%M:%S')"