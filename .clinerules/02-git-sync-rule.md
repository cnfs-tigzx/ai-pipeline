# Git 自动化仓库管理规则（02-git-sync-rule）

> 服务阶段：P4（Git 仓库初始化与上传）。提示词：workflows/P4-git-init-upload.md。
> 章节编号 = 2.x（引用格式：02-git-sync-rule.md §2.4）。

## 2.1 脚本定义

| 项目 | 值 |
|------|-----|
| 路径 | `scripts/git-push.sh`（v2） |
| 依赖 | git + GitHub CLI gh（首次执行前 `gh auth login`） |
| 仓库名称 | ai-pipeline（可见性由脚本顶部 `REPO_PRIVATE` 切换：true=私有 / false=公开） |
| 推送协议 | 默认 SSH（`GIT_PROTOCOL=ssh`，github.com:22 / ssh.github.com:443 稳定可达）；HTTPS 为备选 |
| 调用 | `./scripts/git-push.sh <动作>` |
| 日志 | `output/git-push.log` |
| 帮助 | `./scripts/git-push.sh --help` |

## 2.2 动作表

| 动作 | 说明 |
|------|------|
| init | 安全可重入：检测仓库是否存在→不存在则创建并推送→已存在则关联推送 |
| sync | 提交所有变更并推送；被拒时自动 rebase 重试，冲突则暂停提示 |
| pull | 拉取远端更新；遇冲突暂停，人工处理后重新 sync |
| status | 查看 git 状态、远程地址，打开仓库网页 |

## 2.3 前置检查

- 执行前检测 `gh` 可用性：`command -v gh`，缺失则提示 `brew install gh && gh auth login` 并中止
- 检测 `gh auth status` 登录态，未登录则提示 `gh auth login` 并中止

## 2.4 推送容错（脚本 v2 已内置）

- 默认 SSH 协议推送；部分网络下 HTTPS(github.com:443) 超时，SSH 仍稳定可达
- 自动检测/生成/上传 SSH 密钥（ed25519），首次 init 免人工配置
- 推送前连通性预检 + 传输超时保护（SSH ConnectTimeout/keepalive；HTTPS 低速超时），避免进程无限挂起
- HTTPS 推送失败（超时/连接拒绝）→ 自动切换 SSH 协议重试
- push 被拒（远端有新提交）→ `git pull --rebase` 后重试一次；无共同祖先历史（如远端 Initial commit）→ `--allow-unrelated-histories` 处理；冲突则停止提示人工处理
- SSH 也失败 → 提示检查网络/代理，不无限重试

## 2.5 安全约束

- `.gitignore` 必须忽略整个 `repos/` 目录（含 output/），脚本每次执行前强制校验，未忽略则拒绝提交并退出
- 远端仓库只存放流水线框架，不托管下游业务项目源码/备份/编译产物
- init 安全可重入：仓库不存在就创建，已存在就关联，可重复执行不报错
- 仓库检测使用 owner 限定名（`<login>/ai-pipeline`），避免裸名解析歧义；`gh repo create` 用裸名创建到当前账号下
- 密钥（API Key/token/密码）禁止进入任何被推送的文件：README、脚本、规则、日志均不得含密钥
