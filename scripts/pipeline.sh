#!/bin/zsh
set -e

REPO_URL="$1"
TASK_ID=$(date +%Y%m%d-%H%M%S)
REPO_NAME=$(basename "$REPO_URL" .git)
REPO_TARGET="../repos/$REPO_NAME"

echo "===== 流水线启动 [$TASK_ID] 仓库：$REPO_URL ====="

if [ -d "$REPO_TARGET" ];then
  echo "仓库已存在，执行git pull更新"
  cd "$REPO_TARGET" && git pull
else
  echo "克隆新仓库"
  git clone "$REPO_URL" "$REPO_TARGET"
fi

echo "仓库就绪，等待Cline执行README解析、知识库构建"
echo "{\"repo\":\"$REPO_URL\",\"path\":\"$REPO_TARGET\",\"task_id\":\"$TASK_ID\"}" > ../output/last-task.json
