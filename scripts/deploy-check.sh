#!/bin/zsh
set -e

# 入参：仓库短名，例如 WeKnora
PROJECT_NAME="$1"
PIPELINE_ROOT="/Users/tigzx/workspace/ai-pipeline"
REPO_DIR="${PIPELINE_ROOT}/repos/${PROJECT_NAME}"
DEPLOY_LOG="${PIPELINE_ROOT}/output/${PROJECT_NAME}-deploy-log.md"
REPORT="${PIPELINE_ROOT}/output/${PROJECT_NAME}-report.md"

echo "# 部署校验日志 ${PROJECT_NAME}" > "${DEPLOY_LOG}"
echo "时间：$(date '+%Y-%m-%d %H:%M:%S')" >> "${DEPLOY_LOG}"
echo "环境：Mac Mini M6 arm64 + OrbStack" >> "${DEPLOY_LOG}"
echo "---" >> "${DEPLOY_LOG}"

if [ ! -d "${REPO_DIR}" ];then
    echo "❌ 仓库目录不存在：${REPO_DIR}" | tee -a "${DEPLOY_LOG}"
    exit 1
fi

cd "${REPO_DIR}"

# 1. 检查compose文件
COMPOSE_FILE=""
if [ -f "docker-compose.yml" ];then
    COMPOSE_FILE="docker-compose.yml"
elif [ -f "docker-compose.yaml" ];then
    COMPOSE_FILE="docker-compose.yaml"
elif [ -f "compose.yml" ];then
    COMPOSE_FILE="compose.yml"
fi

if [ -z "${COMPOSE_FILE}" ];then
    echo "⚠️ 未找到docker compose文件，跳过compose部署" | tee -a "${DEPLOY_LOG}"
    exit 0
fi

echo "✅ 找到compose文件：${COMPOSE_FILE}" | tee -a "${DEPLOY_LOG}"

# 2. compose语法校验
echo "## 1. compose语法校验" >> "${DEPLOY_LOG}"
if docker compose -f "${COMPOSE_FILE}" config >> "${DEPLOY_LOG}" 2>&1;then
    echo "✅ compose语法校验通过" >> "${DEPLOY_LOG}"
else
    echo "❌ compose语法错误" >> "${DEPLOY_LOG}"
    exit 1
fi

# 3. 启动（后台）
echo "## 2. docker compose 启动" >> "${DEPLOY_LOG}"
echo "执行命令：docker compose -f ${COMPOSE_FILE} up -d" >> "${DEPLOY_LOG}"
docker compose -f "${COMPOSE_FILE}" up -d >> "${DEPLOY_LOG}" 2>&1

# 4. 等待+日志采集
echo "## 3. 容器状态与日志" >> "${DEPLOY_LOG}"
docker compose ps >> "${DEPLOY_LOG}"
echo "### 最近日志" >> "${DEPLOY_LOG}"
docker compose logs --tail 50 >> "${DEPLOY_LOG}"

echo "## 4. 提示：" >> "${DEPLOY_LOG}"
echo "停止命令：docker compose -f ${COMPOSE_FILE} down" >> "${DEPLOY_LOG}"
echo "查看实时日志：docker compose logs -f" >> "${DEPLOY_LOG}"

echo "✅ 部署脚本执行完成，日志已写入 ${DEPLOY_LOG}"
