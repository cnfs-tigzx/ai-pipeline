# P4 · Git 仓库初始化与上传（git-init-upload）

> 五大阶段之 P4。触发：流水线框架仓库首次创建/推送，或日常变更提交上传。
> 工作根目录：/Users/tigzx/workspace/ai-pipeline
> 引用规则：rules/git-sync-rule.md（§2.1 脚本定义 / §2.2 动作表 / §2.3 前置检查 / §2.4 推送容错 / §2.5 安全约束）；MCP → docs/05-安全与确认策略.md

**输入**：动作可选（init 默认 / sync / pull / status）
**确认点**：push 属展示后执行；`git push --force` 永久禁止（00 §1.2）

## 任务步骤

1. **前置检查**（§2.3）：
   - `command -v gh`，缺失则提示 `brew install gh && gh auth login` 并中止
   - `gh auth status` 登录态，未登录则提示 `gh auth login` 并中止
2. **脚本就绪**：确认 `scripts/git-push.sh`（v2）存在且可执行；缺失或需升级时按 §2.1-§2.4 重新生成并赋执行权限
3. **安全校验**（§2.5）：
   - `.gitignore` 必须忽略整个 `repos/`（含 output/），未忽略则拒绝提交并退出
   - 确认待提交文件不含密钥（API Key/token/密码）——README、脚本、规则、日志均不得含密钥
4. **执行动作**（§2.2）：
   - **init**：安全可重入——远端仓库不存在则创建（`gh repo create`，owner 限定名检测 `<login>/ai-pipeline`）并推送；已存在则关联推送；可重复执行不报错
   - **sync**：提交所有变更并推送；被拒时自动 rebase 重试，冲突则暂停提示
   - **pull**：拉取远端更新；遇冲突暂停，人工处理后重新 sync
   - **status**：查看 git 状态、远程地址，打开仓库网页
5. **推送容错**（§2.4，脚本 v2 已内置）：默认 SSH 协议；推送被拒 → `git pull --rebase` 重试一次（无共同祖先用 `--allow-unrelated-histories`）；HTTPS 失败自动切 SSH；SSH 也失败提示检查网络/代理，不无限重试
6. report 追加章节 13（Git 自动化仓库管理脚本：路径、动作表、日志路径）；追加 `output/task-log.md`；输出使用指引（`./scripts/git-push.sh --help`）

## 使用示例

```
执行 P4（git-init-upload），动作 init
或直接调用：./scripts/git-push.sh sync
```
