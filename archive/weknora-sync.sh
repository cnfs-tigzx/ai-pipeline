#!/usr/bin/env bash
# weknora-sync.sh — 上传文档到 WeKnora 知识库（REST API + tenant API Key）
# 用法: weknora-sync.sh <本地文件> [kb-id] [自定义文件名]
# 示例: weknora-sync.sh knowledge/WeKnora-user-manual.md
# 凭据优先级: 环境变量 WEKNORA_API_KEY > local-secrets.md（行锚点"WeKnora Sync API Key"）
set -euo pipefail

BASE="${WEKNORA_BASE:-http://localhost:8080}"
SECRETS="${SECRETS_FILE:-/Users/tigzx/workspace/ai-pipeline/local-secrets.md}"

usage() { sed -n '2,5p' "$0"; exit 1; }
[ $# -ge 1 ] || usage

FILE="$1"; shift || true
KB="${1:-}"; if [ -n "$KB" ]; then shift || true; fi
NAME="${1:-$(basename "$FILE")}"

KEY="${WEKNORA_API_KEY:-}"
if [ -z "$KEY" ] && [ -f "$SECRETS" ]; then
  KEY=$(grep -m1 'WeKnora Sync API Key' "$SECRETS" | sed 's/.*：//' | tr -d '[:space:]' || true)
fi
[ -n "$KEY" ] || { echo "ERROR: WeKnora API key 未找到（设 WEKNORA_API_KEY 或检查 $SECRETS）" >&2; exit 1; }

if [ -z "$KB" ]; then
  KB="${WEKNORA_KB_ID:-}"
  [ -n "$KB" ] || KB=$(grep -m1 'WeKnora KB ID' "$SECRETS" | grep -oE '[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}' | head -1 || true)
fi
[ -n "$KB" ] || { echo "ERROR: kb-id 未指定（参数 2 或 WEKNORA_KB_ID 或 secrets 中 WeKnora KB ID）" >&2; exit 1; }

RESP=$(curl -sf -X POST "$BASE/api/v1/knowledge-bases/$KB/knowledge/file" \
  -H "X-API-Key: $KEY" \
  -F "file=@$FILE" \
  -F "fileName=$NAME")

echo "$RESP" | python3 -c '
import sys,json
d=json.load(sys.stdin)
data=d.get("data") or d
kid=data.get("id") or ""
print("OK knowledge_id:",kid,"| file:",data.get("file_name") or data.get("name") or "")
if kid: open("/tmp/wk-last-knowledge-id","w").write(kid)'