#!/bin/zsh
# ai-pipeline 环境预检脚本【增强版】
# 检测：代理/VPN、网速、GitHub、火山方舟API、DockerHub、NPM、OrbStack Docker
# 缓存：5分钟有效期，避免重复高频检测
set -euo pipefail

# ========== 配置区 ==========
CACHE_FILE="./.preflight-cache.ts"
CACHE_TTL=300          # 缓存有效期 5分钟，单位秒
REPORT_FILE="./preflight-report.md"
# 火山方舟配置（和你Cline内保持一致）
VOLC_ARK_BASE="https://ark.cn-beijing.volces.com/api/v1"
# 这里填你的推理接入点地址，用于真实模型连通测试
VOLC_ARK_MODEL_ENDPOINT="${VOLC_ARK_BASE}/chat/completions"
# 可选：国内镜像兜底检测地址
NPM_CN_MIRROR="https://registry.npmmirror.com"
# ===========================

# 缓存判断逻辑
now=$(date +%s)
if [[ -f "$CACHE_FILE" ]]; then
  cache_time=$(cat "$CACHE_FILE")
  diff=$(( now - cache_time ))
  if [[ $diff -lt $CACHE_TTL ]]; then
    > $REPORT_FILE
    cat > $REPORT_FILE <<EOF
# 【环境预检报告｜缓存复用】
> 缓存时间：$(date -r $cache_time "+%Y-%m-%d %H:%M:%S")
> 距离上次检测不足5分钟，复用上次结果，如需强制刷新，请删除 \`${CACHE_FILE}\` 再执行
EOF
    cat $REPORT_FILE
    exit 0
  fi
fi
# 更新缓存时间戳
echo $now > $CACHE_FILE

# 初始化报告
> $REPORT_FILE
cat > $REPORT_FILE <<EOF
# 【环境预检报告｜完整检测】
> 检测节点：Mac Mini M6 | OrbStack
> 检测时间：$(date "+%Y-%m-%d %H:%M:%S")
EOF

# --------------------------
# 1. 代理 / VPN 检测
# --------------------------
echo -e "\n## 1. 代理 & VPN 环境" >> $REPORT_FILE
HTTP_PROXY=${HTTP_PROXY:-""}
HTTPS_PROXY=${HTTPS_PROXY:-""}
ALL_PROXY=${ALL_PROXY:-""}
NO_PROXY=${NO_PROXY:-""}

if [[ -n "$HTTP_PROXY" || -n "$HTTPS_PROXY" || -n "$ALL_PROXY" ]]; then
  echo "- ✅ 检测到代理/VPN环境" >> $REPORT_FILE
  echo "  - HTTP_PROXY: $HTTP_PROXY" >> $REPORT_FILE
  echo "  - HTTPS_PROXY: $HTTPS_PROXY" >> $REPORT_FILE
  echo "  - ALL_PROXY: $ALL_PROXY" >> $REPORT_FILE
else
  echo "- ⭕ 无系统代理，直连网络" >> $REPORT_FILE
fi

# --------------------------
# 2. 网速测速（speedtest-cli 可选）
# --------------------------
echo -e "\n## 2. 网速测速" >> $REPORT_FILE
if command -v speedtest-cli &> /dev/null; then
  speed_result=$(speedtest-cli --simple 2>/dev/null) || true
  echo "\`\`\`" >> $REPORT_FILE
  echo "$speed_result" >> $REPORT_FILE
  echo "\`\`\`" >> $REPORT_FILE
else
  echo "- ⚠️ speedtest-cli 未安装，跳过测速；可执行：\`brew install speedtest-cli\`" >> $REPORT_FILE
fi

# --------------------------
# 3. 通用连通性检测函数
# --------------------------
test_endpoint() {
  local name=$1
  local url=$2
  local timeout=8
  echo -e "\n### ${name}" >> $REPORT_FILE
  res=$(curl -s --connect-timeout $timeout -o /dev/null -w "%{http_code},%{time_total}" $url 2>/dev/null) || true
  code=$(echo $res | cut -d',' -f1)
  cost=$(echo $res | cut -d',' -f2)
  if [[ "$code" != "000" ]]; then
    echo "- ✅ 连通，状态码：$code，耗时：${cost}s" >> $REPORT_FILE
  else
    echo "- ❌ 无法连通，超时/访问失败" >> $REPORT_FILE
  fi
}

# --------------------------
# 4. 上游服务连通检测
# --------------------------
echo -e "\n## 3. 外部服务连通检测" >> $REPORT_FILE
test_endpoint "GitHub" "https://github.com"
test_endpoint "DockerHub" "https://hub.docker.com"
test_endpoint "NPM官方源" "https://registry.npmjs.org"
test_endpoint "NPM淘宝镜像" "$NPM_CN_MIRROR"
test_endpoint "火山方舟网关" "${VOLC_ARK_BASE}/models"

# --------------------------
# 5. 火山方舟模型接口专项校验（重点！验证API链路）
# --------------------------
echo -e "\n## 4. 火山方舟模型接口校验" >> $REPORT_FILE
echo "> 注意：此检测仅验证链路通不通，**不会消耗大量token**，仅做轻量握手" >> $REPORT_FILE
# 只做OPTIONS预检，不发prompt，不产生计费
res_ark=$(curl -s --connect-timeout 8 -X OPTIONS $VOLC_ARK_MODEL_ENDPOINT -o /dev/null -w "%{http_code},%{time_total}" 2>/dev/null) || true
ark_code=$(echo $res_ark | cut -d',' -f1)
ark_cost=$(echo $res_ark | cut -d',' -f2)
if [[ "$ark_code" != "000" ]]; then
  echo "- ✅ 模型接口链路正常，状态码：$ark_code，耗时：${ark_cost}s" >> $REPORT_FILE
else
  echo "- ❌ 火山方舟模型接口访问失败，大概率网络拦截或接入点配置错误" >> $REPORT_FILE
fi

# --------------------------
# 6. OrbStack Docker 本地状态
# --------------------------
echo -e "\n## 5. OrbStack Docker 本地状态" >> $REPORT_FILE
if docker info >/dev/null 2>&1; then
  echo "- ✅ Docker守护进程正常，OrbStack就绪" >> $REPORT_FILE
else
  echo "- ❌ Docker不可用，请检查OrbStack是否启动" >> $REPORT_FILE
fi

# --------------------------
# 7. 最终结论
# --------------------------
echo -e "\n## 6. 预检结论" >> $REPORT_FILE
if grep -q "❌" $REPORT_FILE; then
  echo "⚠️ 【存在异常】部分上游服务访问失败！" >> $REPORT_FILE
  echo "> 高危任务（git push / docker build / npm install / 调用方舟大模型）建议暂停，优先修复网络。" >> $REPORT_FILE
  echo "> 如果你确认要无视异常继续，请明确回复【强制继续】" >> $REPORT_FILE
else
  echo "✅ 【全部正常】网络、上游服务连通正常，可以继续执行流水线任务" >> $REPORT_FILE
fi

# 输出报告到stdout，供Cline读取
cat $REPORT_FILE