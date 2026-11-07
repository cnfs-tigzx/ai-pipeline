#!/bin/zsh
set -e

# 路径基准：以脚本自身位置定位流水线根目录，任意 cwd 执行均安全（仓库/产物不逃逸流水线目录）
PIPELINE_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
REPO_URL="$1"
TASK_ID=$(date +%Y%m%d-%H%M%S)
REPO_NAME=$(basename "$REPO_URL" .git)
REPO_TARGET="$PIPELINE_ROOT/repos/$REPO_NAME"

echo "===== 流水线启动 [$TASK_ID] 仓库：$REPO_URL ====="

if [ -d "$REPO_TARGET" ];then
  echo "仓库已存在，执行git pull更新"
  cd "$REPO_TARGET" && git pull
else
  echo "克隆新仓库"
  git clone "$REPO_URL" "$REPO_TARGET"
fi

echo "仓库就绪，等待Cline执行README解析、知识库构建"
echo "{\"repo\":\"$REPO_URL\",\"path\":\"$REPO_TARGET\",\"task_id\":\"$TASK_ID\"}" > "$PIPELINE_ROOT/output/last-task.json"
echo "last-task.json → $PIPELINE_ROOT/output/last-task.json"
