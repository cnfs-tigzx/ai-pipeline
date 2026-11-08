#!/usr/bin/env bash
# ov-sync.sh — 推送本地文件到 OpenViking 项目资产层（REST API）
# 用法: ov-sync.sh <本地文件> <viking://目标路径> [reason]
# 示例: ov-sync.sh knowledge/WeKnora-user-manual.md viking://resources/WeKnora/manuals/ "P3 手册同步"
# 说明: dev 模式免认证；生产 api_key 模式请设环境变量 OV_API_KEY
set -euo pipefail

OV_BASE="${OV_BASE:-http://localhost:1933}"

usage() { sed -n '2,6p' "$0"; exit 1; }
[ $# -ge 2 ] || usage

FILE="$1"; TO="$2"; REASON="${3:-ai-pipeline product sync}"
[ -f "$FILE" ] || { echo "ERROR: file not found: $FILE" >&2; exit 1; }

AUTH=()
[ -n "${OV_API_KEY:-}" ] && AUTH=(-H "Authorization: Bearer $OV_API_KEY")

TID=$(curl -sf -X POST "$OV_BASE/api/v1/resources/temp_upload" "${AUTH[@]+${AUTH[@]}}" \
  -F "file=@$FILE" | python3 -c 'import sys,json;print((json.load(sys.stdin).get("result") or {}).get("temp_file_id",""))')
[ -n "$TID" ] || { echo "ERROR: temp_upload failed" >&2; exit 1; }

curl -sf -X POST "$OV_BASE/api/v1/resources" "${AUTH[@]+${AUTH[@]}}" \
  -H 'Content-Type: application/json' \
  -d "{\"temp_file_id\":\"$TID\",\"to\":\"$TO\",\"reason\":\"$REASON\",\"wait\":true}" \
  | python3 -c '
import sys,json
d=json.load(sys.stdin)
if d.get("status")=="ok":
    r=d.get("result") or {}
    print("OK root_uri:",r.get("root_uri"),"| status:",r.get("status"),"| errors:",r.get("errors"))
else:
    print("ERROR:",json.dumps(d,ensure_ascii=False)[:300]); sys.exit(1)'