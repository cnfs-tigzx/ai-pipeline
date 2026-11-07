#!/bin/zsh
set -e

PROJECT_NAME="$1"
PIPELINE_ROOT="/Users/tigzx/workspace/ai-pipeline"
REPO_DIR="${PIPELINE_ROOT}/repos/${PROJECT_NAME}"
CHANGE_LOG="${PIPELINE_ROOT}/output/${PROJECT_NAME}-change-log.md"

if [ ! -d "${REPO_DIR}" ];then
    echo "❌ 仓库目录不存在：${REPO_DIR}"
    exit 1
fi

cd "${REPO_DIR}"

COMPOSE_FILE=""
if [ -f "docker-compose.yml" ];then
    COMPOSE_FILE="docker-compose.yml"
elif [ -f "docker-compose.yaml" ];then
    COMPOSE_FILE="docker-compose.yaml"
elif [ -f "compose.yml" ];then
    COMPOSE_FILE="compose.yml"
fi

if [ -z "${COMPOSE_FILE}" ];then
    # native 项目（Java/Node 等）无 compose：走 one-key.sh 重建流程
    if [ -d "backend" ] && [ -d "frontend" ];then
        echo "ℹ️ ${PROJECT_NAME} 为 native 项目（无 compose），改用 one-key.sh 重启构建" | tee -a "${CHANGE_LOG}"
        echo "## 1. native 重建（one-key.sh restart）" >> "${CHANGE_LOG}"
        "${PIPELINE_ROOT}/scripts/one-key.sh" "${PROJECT_NAME}" restart >> "${CHANGE_LOG}" 2>&1 || true
        echo "## 2. 服务状态" >> "${CHANGE_LOG}"
        "${PIPELINE_ROOT}/scripts/one-key.sh" "${PROJECT_NAME}" status >> "${CHANGE_LOG}" 2>&1 || true
        echo "✅ native 构建发布完成，变更日志：${CHANGE_LOG}"
        exit 0
    fi
    echo "❌ 未找到compose配置文件，且非已支持的 native 结构"
    exit 1
fi

echo "# 重新构建发布日志 ${PROJECT_NAME}" > "${CHANGE_LOG}"
echo "执行时间：$(date '+%Y-%m-%d %H:%M:%S')" >> "${CHANGE_LOG}"
echo "环境：Mac Mini M6 + OrbStack" >> "${CHANGE_LOG}"
echo "---" >> "${CHANGE_LOG}"

echo "## 1. 重新构建镜像" >> "${CHANGE_LOG}"
docker compose -f "${COMPOSE_FILE}" build >> "${CHANGE_LOG}" 2>&1

echo "## 2. 停止旧服务并启动新版本" >> "${CHANGE_LOG}"
docker compose -f "${COMPOSE_FILE}" down >> "${CHANGE_LOG}" 2>&1
docker compose -f "${COMPOSE_FILE}" up -d >> "${CHANGE_LOG}" 2>&1

echo "## 3. 容器状态" >> "${CHANGE_LOG}"
docker compose ps >> "${CHANGE_LOG}"

echo "## 4. 最近服务日志" >> "${CHANGE_LOG}"
docker compose logs --tail 50 >> "${CHANGE_LOG}"

echo "✅ 构建发布完成，变更日志：${CHANGE_LOG}"
