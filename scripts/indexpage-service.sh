#!/bin/zsh
# indexpage-service.sh — 三中心门户常驻服务管理（macOS launchd，系统自带零依赖）
# 用法：./scripts/indexpage-service.sh install|uninstall|status|logs|restart
# 效果：登录自启 + 崩溃自动拉起（KeepAlive）；页面 http://127.0.0.1:8765
set -uo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LABEL="com.ai-three-center.indexpage"
PLIST_SRC="${ROOT}/launchd/${LABEL}.plist"
PLIST_DST="${HOME}/Library/LaunchAgents/${LABEL}.plist"
LOG="${ROOT}/output/indexpage-service.log"
PING="http://127.0.0.1:8765/api/ping"

gen_plist() {
  local py
  py="$(command -v python3)"
  [ -x "$py" ] || { echo "[indexpage] 未找到 python3"; return 1; }
  mkdir -p "${ROOT}/launchd" "${ROOT}/output"
  sed -e "s|__PYTHON__|${py}|g" -e "s|__ROOT__|${ROOT}|g" "$PLIST_SRC" > "$PLIST_DST"
  echo "[indexpage] plist 已生成 → ${PLIST_DST}（python3=${py}）"
}

case "${1:-}" in
  install)
    gen_plist || exit 1
    launchctl bootout "gui/$(id -u)/${LABEL}" 2>/dev/null
    launchctl bootstrap "gui/$(id -u)" "$PLIST_DST" \
      || launchctl load "$PLIST_DST"
    sleep 2
    "$0" status
    ;;
  uninstall)
    launchctl bootout "gui/$(id -u)/${LABEL}" 2>/dev/null || launchctl unload "$PLIST_DST" 2>/dev/null
    rm -f "$PLIST_DST"
    pkill -f control_server.py 2>/dev/null
    echo "[indexpage] 常驻服务已卸载（页面仍可 file:// 双击打开或手动 python3 scripts/control_server.py）"
    ;;
  restart)
    "$0" uninstall && sleep 1 && "$0" install
    ;;
  status)
    if launchctl print "gui/$(id -u)/${LABEL}" >/dev/null 2>&1; then
      echo "[indexpage] launchd 状态: 已注册（KeepAlive + RunAtLoad）"
    else
      echo "[indexpage] launchd 状态: 未安装（执行 $0 install）"
    fi
    code="$(curl -s -o /dev/null -w '%{http_code}' --max-time 2 "$PING" 2>/dev/null)"
    if [ "$code" = "200" ]; then
      echo "[indexpage] 服务健康: http://127.0.0.1:8765 → 200"
    else
      echo "[indexpage] 服务健康: 不可达（code=$code）"
    fi
    ;;
  logs)
    tail -30 "$LOG"
    ;;
  *)
    echo "用法: $0 install|uninstall|restart|status|logs"
    ;;
esac
