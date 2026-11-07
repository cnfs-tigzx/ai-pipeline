# 基础通用规则（00-base-general）

> 全局基础规则：环境变量、阶段路由、安全约束、自动审批（确认策略）、备份回滚、日志与报告模板。
> 五大阶段提示词位于 `workflows/`（只写执行步骤，规则按编号引用）；规则细节位于对应编号规则文件。

## 规则文件索引

| 文件 | 职责 | 服务阶段 |
|------|------|----------|
| 00-base-general.md | 基础通用：环境、路由、安全、确认策略、备份、日志 | 全部 |
| 01-mem0-archive-rule.md | Mem0 记忆归档：边界、标签、检索、写入 | P5 + 全阶段闭环归档 |
| 02-git-sync-rule.md | Git 一键脚本 git-push.sh：init/sync/pull/status | P4 |
| 03-build-docker-rule.md | 拉取解析、部署校验、编译部署、一键运维脚本 | P1 |
| 04-mcp-control-rule.md | MCP 工具调用、stdio 模式、错误排查 | 全部 |
| 05-secondary-dev-rule.md | 二次开发、代码标识替换、Logo 替换 | P3 |
| 06-web-capture-rule.md | 网页抓取、表格抓取、产品说明书生成 | P2 |
| workflows/ | 五大阶段任务提示词（只写步骤，规则引用编号） | — |

## 五大阶段路由表（总入口）

| 阶段 | 任务 | 提示词（workflows/） | 主规则 | 报告章节 |
|------|------|----------------------|--------|----------|
| P1 | GitHub 拉取代码 → 生成部署文档 → 结合本地配置和环境编译部署 → 生成一键停止/启动/重新编译部署脚本 | P1-fetch-build-deploy.md | 03-build-docker-rule.md | 1-8、12 |
| P2 | 抓取 GitHub 仓库网页及产品说明网页 → 产品说明书 | P2-web-capture-manual.md | 06-web-capture-rule.md | 9 |
| P3 | 二次开发任务 + 代码标识替换 + Logo 替换 | P3-secondary-dev-logo.md | 05-secondary-dev-rule.md | 10、11 |
| P4 | Git 仓库初始化与上传 | P4-git-init-upload.md | 02-git-sync-rule.md | 13 |
| P5 | Mem0 存取读写测试 | P5-mem0-rw-test.md | 01-mem0-archive-rule.md | — |

**标准链路**：新项目 P1 → P2 → P3 → P4（顺序执行，前一阶段产物是后一阶段输入）；P5 独立执行（mem0 回归/连通性测试）。单阶段任务直接按路由表进入对应提示词，禁止跨阶段混读无关规则。

## 脚本清单（阶段依赖的真实脚本）

| 脚本 | 用途 | 阶段 |
|------|------|------|
| scripts/pipeline.sh | clone/pull 仓库到 repos/，写 output/last-task.json | P1-A |
| scripts/deploy-check.sh | 部署校验并生成 output/{REPO}-deploy-log.md | P1-B |
| scripts/one-key.sh | 一键运维：start/stop/restart/build/status | P1-C、P3 |
| scripts/rebuild-deploy.sh | docker 重新构建并发布（改码后） | P1-C、P3 |
| scripts/git-push.sh | git 仓库 init/sync/pull/status（v2 默认 SSH） | P4 |
| scripts/mem0-one-key.sh | mem0 服务 status/start/stop | P5 |

---

## 〇、环境与变量

- **工作根目录**：/Users/tigzx/workspace/ai-pipeline
- **执行环境**：Mac Mini M6(arm64) 24G + OrbStack（docker context=orbstack）
- **变量**：`{REPO}`=项目名 · `{REPO_URL}`=仓库地址 · `{BRAND}`=目标品牌名 · `{DEPLOY_MODE}`=部署模式(docker/native/混合)
- **安全边界**：仅在流水线目录内读写，禁止访问上级/系统目录，不修改系统全局环境
- **资源限制**：OrbStack 虚拟机内存 ≤ 16G
- **核心原则**：优先 MCP 工具（filesystem > Terminal > playwright），禁止编造内容/猜测文件/网页输出（MCP 调用细则见 04-mcp-control-rule.md）

---

## 一、通用执行规则

### 1.1 确认策略（分级）

| 级别 | 操作 | 策略 |
|------|------|------|
| 低危 | 文件读取、页面抓取、搜索扫描、日志追加、git status | 连续执行不等待 |
| 中危 | 文件写入、非破坏性脚本执行、git add/commit | 展示命令后执行不等待 |
| 高危 | docker compose up/down、批量文件修改、覆盖图片、rm -rf、docker system prune、git push --force | 打印完整命令，等待人工确认 |

- 阶段开始输出一次完整计划，步骤间不重复输出
- 连续执行阶段仅在高危操作点确认（各阶段提示词中的「确认点」标注即高危点；P1 全程仅 1 个确认点）

### 1.2 安全红线

- **高危命令完整列表**：rm -rf、docker system prune、docker volume rm、git push --force、docker compose down（生产环境）
- 禁止自动执行高风险清理命令
- 构建前校验可用资源（OrbStack 内存 / 系统可用内存 / 磁盘空间）

### 1.3 备份与回滚

- **备份路径**：`repos/{REPO}/.auto-bak/{时间戳}/[子目录/]`
- **备份时机**：任何文件修改/覆盖之前，保持原目录结构
- **回滚**：编译/构建失败 → 从备份恢复全部文件；docker 模式额外恢复上一版本镜像；native 模式终止进程并恢复文件，不保留损坏版本

### 1.4 日志与输出规范

- 任务日志追加 `output/task-log.md`（时间、阶段、动作、结果）
- 脚本日志：one-key.sh → `output/one-key-operation.log`；git-push.sh → `output/git-push.log`
- native 运行日志：`output/{REPO}-native.log`；PID 文件：`output/{REPO}-native.pid`
- 禁止直接输出超 50 行的代码/json/文档，必须 write_file 写入磁盘
- **Markdown 格式规范**：产物 md 文件中禁止写入 shell 注释（`#`开头的非标题行）；标题用 `#`/`##`/`###`，正文不用 `#` 开头
- 推理模式：严谨、结构化，不发散，温度等效 0

### 1.5 报告章节模板

`output/{REPO}-report.md` 固定章节编号（按执行顺序追加，未执行的章节省略；阶段与章节对应关系见上方路由表）：

1. 任务概要 2. 仓库路径与本地结构 3. 依赖清单 4. 启动命令 5. 访问地址 6. 风险点 7. 流水线执行记录 8. 部署验证 9. 产品说明书 10. 源码二次开发记录 11. Logo 与代码标识替换记录 12. 一键运维脚本说明 13. Git 自动化仓库管理脚本
