#!/bin/zsh
# ============================================================
# ai-pipeline Git 一键仓库管理脚本
# 规范来源：.clinerules →「Git一键仓库管理脚本规范」
# 依赖：git + GitHub CLI (gh)，首次使用前执行 `gh auth login`
# 核心安全：repos/ 整目录被 .gitignore 忽略，绝不上传 GitHub
# ============================================================
set -euo pipefail

# ---------- 配置（按需修改） ----------
PIPELINE_ROOT="/Users/tigzx/workspace/ai-pipeline"
REPO_NAME="ai-pipeline"
BRANCH="main"
# 仓库可见性：true=私有(private) / false=公开(public)
REPO_PRIVATE=false
REPO_DESC="Cline AI 流水线工程｜GLM-5.2 + 火山方舟 + WeKnora 自动化"
LOG_DIR="${PIPELINE_ROOT}/output"
LOG="${LOG_DIR}/git-push.log"
# --------------------------------------

# ---------- 工具函数 ----------
usage() {
    cat <<'EOF'
用法：./scripts/git-push.sh <动作>

动作：
  init     【首次/安全可重入】自动检测 GitHub 仓库是否存在：
           不存在 → 自动新建仓库并提交推送；已存在 → 直接关联推送。
           重复执行不会重复创建、不会报错。
  sync     【提交更新】本地脚本/规则/报告改动后，一键提交并推送到 GitHub；
           推送被拒时自动 rebase 后重试。
  pull     【拉取更新】拉取 GitHub 远端流水线代码更新本地（多机器同步）；
           遇冲突暂停，人工处理冲突后重新 sync。
  status   查看 git 状态、远程地址，并打开 GitHub 仓库网页。
  --help / -h / help
           输出本用法。

约束：
  - repos/ 整目录被 .gitignore 忽略，下游项目源码/备份/产物不上传。
  - 仅托管 ai-pipeline 流水线框架本身。

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
    echo "===== Git流水线脚本｜$(date '+%Y-%m-%d %H:%M:%S') 动作：${ACTION} ====="
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
        log "🔧 [init] 本地 git 初始化 + GitHub 仓库自动检测/创建"

        # 1. 本地 git 初始化（已存在则跳过，分支对齐为 main）
        if [ ! -d ".git" ]; then
            git init -q
            git branch -M "${BRANCH}" 2>/dev/null || true
            log "✅ 已执行 git init，默认分支 ${BRANCH}"
        else
            git branch -M "${BRANCH}" 2>/dev/null || true
            log "ℹ️ 本地已是 git 仓库，跳过 init（分支已对齐为 ${BRANCH}）"
        fi

        # ===== 【移动到这里！】安全闸门：repos/ 必须被忽略，杜绝下游源码泄漏 =====
        if ! grep -qE '^repos/?$' .gitignore; then
            die "安全检查未通过：repos/ 未被 .gitignore 忽略，拒绝提交以防下游项目源码上传 GitHub。请在 .gitignore 加入 repos/"
        fi
        log "🔒 repos/ 已被 .gitignore 忽略（下游源码/备份/产物不会上传 GitHub）"

        # 2. GitHub 仓库检测 / 自动创建（owner 限定，避免裸名解析歧义）
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

        # 3. 关联 origin（已存在则更新指向）
        REMOTE_URL="$(gh repo view "${REPO_FULL}" --json url -q .url 2>/dev/null || true)"
        [ -n "${REMOTE_URL}" ] || die "无法读取远端仓库 url"
        log "🔗 远程地址：${REMOTE_URL}"
        if git remote | grep -qx origin; then
            git remote set-url origin "${REMOTE_URL}"
            log "⚙️ 已更新 origin 指向"
        else
            git remote add origin "${REMOTE_URL}"
            log "⚙️ 已新增 origin"
        fi

        # 4. 提交（repos/ 已被忽略，不会上传）
        log "📦 暂存并提交（repos/ 整目录被忽略，不会上传 GitHub）"
        git add -A
        if git commit -m "feat: ai-pipeline 流水线初始化提交" 2>/dev/null; then
            log "✅ 已生成提交"
        else
            log "ℹ️ 无新变更，跳过 commit"
        fi

        # 5. 推送（被拒则 rebase 后重试）
        log "🚀 推送到 origin/${BRANCH}"
        if git push -u origin "${BRANCH}" 2>&1 | tee -a "${LOG}"; then
            log "✅ init 完成，仓库地址：${REMOTE_URL}"
        else
            log "⚠️ 首次推送被拒（远端可能已有提交），尝试 rebase 后重推..."
            if git pull --rebase origin "${BRANCH}" 2>&1 | tee -a "${LOG}"; then
                git push -u origin "${BRANCH}" 2>&1 | tee -a "${LOG}" \
                    || die "推送仍失败，请检查网络/权限后重试"
                log "✅ init 完成（rebase 后推送成功），仓库地址：${REMOTE_URL}"
            else
                die "rebase 失败，请人工处理冲突后执行：./scripts/git-push.sh sync"
            fi
        fi
        ;;

    sync)
        log "🔄 [sync] 提交本地变更并推送（repos/ 自动忽略）"
        # sync 分支里也加上安全校验
        if ! grep -qE '^repos/?$' .gitignore; then
            die "安全检查未通过：repos/ 未被 .gitignore 忽略，拒绝提交以防下游项目源码上传 GitHub。请在 .gitignore 加入 repos/"
        fi
        log "🔒 repos/ 已被 .gitignore 忽略（下游源码/备份/产物不会上传 GitHub）"

        git add -A
        if git commit -m "chore: auto sync $(date '+%Y-%m-%d %H:%M')" 2>/dev/null; then
            log "✅ 已提交变更"
        else
            log "ℹ️ 无变更，无需提交"
        fi
        log "🚀 推送至 origin/${BRANCH}"
        if git push origin "${BRANCH}" 2>&1 | tee -a "${LOG}"; then
            log "✅ sync 完成"
        else
            log "⚠️ 推送被拒，尝试 rebase 后重推..."
            if git pull --rebase origin "${BRANCH}" 2>&1 | tee -a "${LOG}"; then
                git push origin "${BRANCH}" 2>&1 | tee -a "${LOG}" || die "推送失败"
                log "✅ sync 完成（rebase 后推送成功）"
            else
                die "rebase 失败，请人工处理冲突后重新执行 sync"
            fi
        fi
        ;;

    pull)
        log "⬇️ [pull] 拉取远端最新流水线代码（repos/ 不会被拉取）"
        git fetch origin 2>&1 | tee -a "${LOG}" || true
        if git pull --rebase origin "${BRANCH}" 2>&1 | tee -a "${LOG}"; then
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
