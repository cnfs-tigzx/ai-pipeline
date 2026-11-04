#!/bin/zsh
# ============================================================
# ai-pipeline Git 一键仓库管理脚本（v2）
# 规范来源：.clinerules →「Git一键仓库管理脚本规范」
# 依赖：git + GitHub CLI (gh)，首次使用前执行 `gh auth login`
# 核心安全：repos/ 整目录被 .gitignore 忽略，绝不上传 GitHub
#
# v2 改进（基于实战推送经验）：
#   1. 默认 SSH 协议推送——HTTPS(github.com:443) 在部分网络下超时，
#      而 SSH(github.com:22 / ssh.github.com:443) 稳定可达。
#   2. 自动检测/生成/上传 SSH 密钥（ed25519），首次 init 免人工配置。
#   3. origin 始终使用脚本按协议构造的 URL，不再被 gh repo view 的 HTTPS 覆盖。
#   4. 推送被拒时用 --allow-unrelated-histories 处理无共同祖先的历史
#      （如远端含 GitHub 自动生成的 Initial commit）。
#   5. 推送前连通性预检 + 传输超时保护（SSH ConnectTimeout/keepalive，
#      HTTPS 低速超时），避免网络卡死时进程无限挂起。
# ============================================================
set -euo pipefail

# ---------- 配置（按需修改） ----------
PIPELINE_ROOT="/Users/tigzx/workspace/ai-pipeline"
REPO_NAME="ai-pipeline"
BRANCH="main"
# 仓库可见性：true=私有(private) / false=公开(public)
REPO_PRIVATE=false
REPO_DESC="Cline AI 流水线工程｜GLM-5.2 + 火山方舟 + WeKnora 自动化"
# 推送协议：ssh（默认，稳定）/ https（仅当 github.com:443 可达时可用）
GIT_PROTOCOL="ssh"
# SSH 密钥路径
SSH_KEY="${HOME}/.ssh/id_ed25519"
SSH_PUBKEY="${SSH_KEY}.pub"
LOG_DIR="${PIPELINE_ROOT}/output"
LOG="${LOG_DIR}/git-push.log"
# --------------------------------------

# ---------- 工具函数 ----------
usage() {
    cat <<'EOF'
用法：./scripts/git-push.sh <动作>

动作：
  init     【首次/安全可重入】自动检测 GitHub 仓库是否存在：
           不存在 → 自动新建仓库（+ 自动配置 SSH 密钥）并提交推送；
           已存在 → 直接关联推送。重复执行不会重复创建、不会报错。
  sync     【提交更新】本地脚本/规则/报告改动后，一键提交并推送到 GitHub；
           推送被拒时自动 rebase（含无关历史合并）后重试。
  pull     【拉取更新】拉取 GitHub 远端流水线代码更新本地（多机器同步）；
           遇冲突暂停，人工处理冲突后重新 sync。
  status   查看 git 状态、远程地址、协议与 SSH 认证，并打开 GitHub 仓库网页。
  --help / -h / help
           输出本用法。

约束：
  - repos/ 整目录被 .gitignore 忽略，下游项目源码/备份/产物不上传。
  - 仅托管 ai-pipeline 流水线框架本身。
  - 默认 SSH 协议推送（顶部 GIT_PROTOCOL 可切 https）。

示例（在 ai-pipeline 根目录执行）：
  ./scripts/git-push.sh init
  ./scripts/git-push.sh sync
  ./scripts/git-push.sh pull
  ./scripts/git-push.sh status
  ./scripts/git-push.sh --help
EOF
}

log()  { echo "$*" | tee -a "${LOG}"; }
die()  { echo "❌ $*" | tee -a "${LOG}" >&2; exit 1; }

# 按当前协议构造远程 URL
remote_url() {
    case "${GIT_PROTOCOL}" in
        ssh)   echo "git@github.com:${GH_LOGIN}/${REPO_NAME}.git" ;;
        https) echo "https://github.com/${GH_LOGIN}/${REPO_NAME}.git" ;;
        *)     die "未知 GIT_PROTOCOL：${GIT_PROTOCOL}（仅支持 ssh / https）" ;;
    esac
}

# ---------- SSH 密钥自动配置（仅 ssh 协议） ----------
ensure_ssh_key() {
    [ "${GIT_PROTOCOL}" = "ssh" ] || return 0

    mkdir -p "${HOME}/.ssh" && chmod 700 "${HOME}/.ssh"

    # 1. 无密钥则生成 ed25519
    if [ ! -f "${SSH_PUBKEY}" ]; then
        log "🔑 未检测到 SSH 密钥，生成 ed25519 密钥对..."
        ssh-keygen -t ed25519 -C "${GH_LOGIN}@users.noreply.github.com" \
            -f "${SSH_KEY}" -N "" >/dev/null 2>&1 \
            || die "SSH 密钥生成失败"
        log "✅ 已生成密钥：${SSH_KEY}"
    else
        log "ℹ️ SSH 密钥已存在：${SSH_KEY}"
    fi

    # 2. 上传公钥到 GitHub（去重：比对已登记 key，避免重复上传）
    #    注：gh ssh-key list 可能因缺 admin:ssh_signing_key scope 而 404，
    #    改用 gh api user/keys（需 admin:public_key scope，gh 登录默认具备）。
    LOCAL_PUB="$(cat "${SSH_PUBKEY}" 2>/dev/null | awk '{print $1" "$2}')"
    REGISTERED="$(gh api user/keys --jq '.[].key' 2>/dev/null | awk '{print $1" "$2}' || true)"
    if [ -n "${REGISTERED}" ] && echo "${REGISTERED}" | grep -qF "${LOCAL_PUB}"; then
        log "ℹ️ 公钥已登记在 GitHub 账号，跳过上传"
    else
        log "📤 上传公钥到 GitHub 账号..."
        if gh ssh-key add "${SSH_PUBKEY}" \
            --title "ai-pipeline $(hostname -s) $(date '+%Y%m%d')" >/dev/null 2>&1; then
            log "✅ 公钥已上传"
        else
            # 重复上传同 key 会报错，但已有 key 仍有效，不致命
            log "⚠️ 公钥上传返回非零（可能已存在），继续验证认证..."
        fi
    fi

    # 3. 验证 SSH 认证（GitHub ssh -T 返回非零，但消息含 "successfully authenticated" 即成功）
    log "🔌 验证 SSH 认证..."
    SSH_MSG="$(ssh -T -o ConnectTimeout=10 -o StrictHostKeyChecking=accept-new \
                git@github.com 2>&1 || true)"
    if echo "${SSH_MSG}" | grep -q "successfully authenticated"; then
        log "✅ SSH 认证成功（${GH_LOGIN}）"
    else
        die "SSH 认证失败：${SSH_MSG}。请检查密钥是否已上传 GitHub 账号"
    fi
}

# ---------- 连通性预检 ----------
# SSH 协议：认证已在 ensure_ssh_key() 用 ssh -T 验证（含 10s 超时），
#   此处不再重复探测，避免单次抖动误判（GitHub SSH 偶发超时但通道可用）。
# HTTPS 协议：github.com:443 在部分网络阻断，需 curl 预检并给出明确提示。
check_connectivity() {
    case "${GIT_PROTOCOL}" in
        ssh)
            log "ℹ️ SSH 通道：认证已验证（github.com:22），跳过重复探测"
            ;;
        https)
            if curl -sS -o /dev/null --max-time 10 https://github.com 2>/dev/null; then
                log "ℹ️ HTTPS 通道（github.com:443）可达"
            else
                die "HTTPS 通道 github.com:443 不可达（超时）。建议改用 SSH：将脚本顶部 GIT_PROTOCOL 设为 ssh"
            fi
            ;;
    esac
}

# ---------- 推送容错（被拒则 rebase 含无关历史合并后重试） ----------
# 用法：push_with_fallback <动作名> <remote_url>
push_with_fallback() {
    local _action="$1" _url="$2"
    # 传输超时保护：SSH 用 ConnectTimeout + keepalive；HTTPS 用低速超时
    export GIT_SSH_COMMAND="ssh -o ConnectTimeout=15 -o ServerAliveInterval=30 -o ServerAliveCountMax=3"
    export GIT_HTTP_LOW_SPEED_LIMIT=1000
    export GIT_HTTP_LOW_SPEED_TIME=30

    log "🚀 推送到 origin/${BRANCH}（${GIT_PROTOCOL}）"
    if git push -u origin "${BRANCH}" 2>&1 | tee -a "${LOG}"; then
        log "✅ ${_action} 完成，仓库地址：${_url}"
        return 0
    fi
    log "⚠️ 首次推送被拒（远端可能已有提交/无共同祖先），尝试 rebase（含无关历史合并）后重推..."
    if git pull --rebase --allow-unrelated-histories origin "${BRANCH}" 2>&1 | tee -a "${LOG}"; then
        git push -u origin "${BRANCH}" 2>&1 | tee -a "${LOG}" \
            || die "推送仍失败，请检查网络/权限后重试"
        log "✅ ${_action} 完成（rebase 后推送成功），仓库地址：${_url}"
    else
        die "rebase 失败，请人工处理冲突后执行：git rebase --continue，再 ./scripts/git-push.sh sync"
    fi
}

# ---------- 帮助 / 无参数（优先处理，不依赖环境） ----------
if [ $# -eq 0 ]; then
    usage
    exit 1
fi
case "$1" in
    --help|-h|help) usage; exit 0 ;;
esac

ACTION="$1"

# ---------- 前置检查 ----------
mkdir -p "${LOG_DIR}"
cd "${PIPELINE_ROOT}"

# 日志头
{
    echo ""
    echo "===== Git流水线脚本｜$(date '+%Y-%m-%d %H:%M:%S') 动作：${ACTION} 协议：${GIT_PROTOCOL} ====="
} >> "${LOG}"

log "📍 工作目录：${PIPELINE_ROOT}"

command -v git >/dev/null 2>&1 || die "未找到 git 命令，请先安装 git"
command -v gh  >/dev/null 2>&1 || die "缺少 GitHub CLI gh，请先安装：brew install gh && gh auth login"

# gh 登录态校验（复用 VSCode 登录的 GitHub 账号）
gh auth status >/dev/null 2>&1 || die "gh 未登录，请先执行：gh auth login"

# 读取 GitHub 账号（用于 owner 限定仓库名 + 自动补齐 git 身份）
GH_LOGIN="$(gh api user --jq .login 2>/dev/null || true)"
[ -n "${GH_LOGIN}" ] || die "无法读取 GitHub 登录账号，请确认 gh auth login 已完成"
GH_ID="$(gh api user --jq .id 2>/dev/null || true)"
REPO_FULL="${GH_LOGIN}/${REPO_NAME}"

# git 身份自动补齐（缺失则从 gh 账号取，邮箱用 GitHub noreply）
if [ -z "$(git config user.name)" ]; then
    git config user.name "${GH_LOGIN}"
    log "⚙️ 已自动设置 git user.name = ${GH_LOGIN}（取自 gh 登录账号）"
fi
if [ -z "$(git config user.email)" ]; then
    if [ -n "${GH_ID}" ] && [ -n "${GH_LOGIN}" ]; then
        GIT_EMAIL="${GH_ID}+${GH_LOGIN}@users.noreply.github.com"
    else
        GIT_EMAIL="${GH_LOGIN}@users.noreply.github.com"
    fi
    git config user.email "${GIT_EMAIL}"
    log "⚙️ 已自动设置 git user.email = ${GIT_EMAIL}（GitHub noreply）"
fi

# ---------- 主流程 ----------
case "${ACTION}" in
    init)
        log "🔧 [init] 本地 git 初始化 + SSH 密钥配置 + GitHub 仓库自动检测/创建"

        # 0. SSH 密钥自动配置（ssh 协议时）
        ensure_ssh_key

        # 1. 本地 git 初始化（已存在则跳过，分支对齐为 main）
        if [ ! -d ".git" ]; then
            git init -q
            git branch -M "${BRANCH}" 2>/dev/null || true
            log "✅ 已执行 git init，默认分支 ${BRANCH}"
        else
            git branch -M "${BRANCH}" 2>/dev/null || true
            log "ℹ️ 本地已是 git 仓库，跳过 init（分支已对齐为 ${BRANCH}）"
        fi

        # 2. 安全闸门：repos/ 必须被忽略，杜绝下游源码泄漏
        if ! grep -qE '^repos/?$' .gitignore; then
            die "安全检查未通过：repos/ 未被 .gitignore 忽略，拒绝提交以防下游项目源码上传 GitHub。请在 .gitignore 加入 repos/"
        fi
        log "🔒 repos/ 已被 .gitignore 忽略（下游源码/备份/产物不会上传 GitHub）"

        # 3. GitHub 仓库检测 / 自动创建（owner 限定，避免裸名解析歧义）
        if gh repo view "${REPO_FULL}" >/dev/null 2>&1; then
            log "✅ GitHub 仓库 ${REPO_FULL} 已存在，直接关联"
        else
            log "🌐 GitHub 仓库 ${REPO_FULL} 不存在，自动创建..."
            if [ "${REPO_PRIVATE}" = "true" ]; then
                VIS_FLAG="--private"
                VIS_TEXT="私有"
            else
                VIS_FLAG="--public"
                VIS_TEXT="公开"
            fi
            gh repo create "${REPO_NAME}" ${VIS_FLAG} --description "${REPO_DESC}" --no-readme \
            || die "创建 GitHub 仓库失败，请检查 gh 权限或是否存在同名仓库"
            log "✅ 已创建 GitHub 仓库：${REPO_FULL}（${VIS_TEXT}）"
        fi

        # 4. 关联 origin（使用脚本构造的协议 URL，不被 gh 的 HTTPS 覆盖）
        REMOTE_URL="$(remote_url)"
        log "🔗 远程地址（${GIT_PROTOCOL}）：${REMOTE_URL}"
        if git remote | grep -qx origin; then
            git remote set-url origin "${REMOTE_URL}"
            log "⚙️ 已更新 origin 指向（${GIT_PROTOCOL}）"
        else
            git remote add origin "${REMOTE_URL}"
            log "⚙️ 已新增 origin（${GIT_PROTOCOL}）"
        fi

        # 5. 连通性预检
        check_connectivity

        # 6. 提交（repos/ 已被忽略，不会上传）
        log "📦 暂存并提交（repos/ 整目录被忽略，不会上传 GitHub）"
        git add -A
        if git commit -m "feat: ai-pipeline 流水线初始化提交" 2>/dev/null; then
            log "✅ 已生成提交"
        else
            log "ℹ️ 无新变更，跳过 commit"
        fi

        # 7. 推送（被拒则 rebase 含无关历史合并后重试）
        push_with_fallback "init" "${REMOTE_URL}"
        ;;

    sync)
        log "🔄 [sync] 提交本地变更并推送（repos/ 自动忽略）"

        # 安全闸门
        if ! grep -qE '^repos/?$' .gitignore; then
            die "安全检查未通过：repos/ 未被 .gitignore 忽略，拒绝提交以防下游项目源码上传 GitHub。请在 .gitignore 加入 repos/"
        fi
        log "🔒 repos/ 已被 .gitignore 忽略（下游源码/备份/产物不会上传 GitHub）"

        # 确保 origin 存在且协议正确（防止被外部改为不通的 HTTPS）
        REMOTE_URL="$(remote_url)"
        if git remote | grep -qx origin; then
            CURRENT="$(git remote get-url origin)"
            if [ "${CURRENT}" != "${REMOTE_URL}" ]; then
                git remote set-url origin "${REMOTE_URL}"
                log "⚙️ 已校正 origin 指向（${CURRENT} → ${REMOTE_URL}）"
            fi
        else
            die "未配置 origin，请先执行：./scripts/git-push.sh init"
        fi

        # ssh 协议时确保密钥就绪（换设备后首次 sync 可能尚未配置）
        ensure_ssh_key

        # 连通性预检
        check_connectivity

        git add -A
        if git commit -m "chore: auto sync $(date '+%Y-%m-%d %H:%M')" 2>/dev/null; then
            log "✅ 已提交变更"
        else
            log "ℹ️ 无变更，无需提交"
        fi
        push_with_fallback "sync" "${REMOTE_URL}"
        ;;

    pull)
        log "⬇️ [pull] 拉取远端最新流水线代码（repos/ 不会被拉取）"
        git fetch origin 2>&1 | tee -a "${LOG}" || true
        if git pull --rebase --allow-unrelated-histories origin "${BRANCH}" 2>&1 | tee -a "${LOG}"; then
            log "✅ pull 完成，本地流水线已同步远端"
        else
            die "拉取冲突，请人工处理冲突后执行：git rebase --continue，再 ./scripts/git-push.sh sync"
        fi
        ;;

    status)
        log "📊 [status] 仓库状态"
        echo "--- git status ---"
        git status
        echo "--- remote ---"
        git remote -v 2>/dev/null || echo "(未配置 remote)"
        echo "--- 协议与认证 ---"
        echo "GIT_PROTOCOL=${GIT_PROTOCOL}"
        if [ "${GIT_PROTOCOL}" = "ssh" ]; then
            ssh -T -o ConnectTimeout=8 git@github.com 2>&1 || true
        fi
        echo "--- github ---"
        if gh repo view "${REPO_FULL}" >/dev/null 2>&1; then
            gh repo view "${REPO_FULL}"
            log "🌐 打开仓库网页..."
            gh repo view "${REPO_FULL}" --web 2>/dev/null || true
        else
            log "ℹ️ GitHub 上尚无仓库 ${REPO_FULL}，请先执行 init"
        fi
        ;;

    *)
        echo "❌ 未知参数：${ACTION}" >&2
        usage
        exit 1
        ;;
esac
