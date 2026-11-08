# P1 · GitHub 拉取代码 → 部署文档 → 编译部署 → 一键脚本（fetch-build-deploy）

> 五大阶段之 P1。触发：拿到一个新的 GitHub 仓库，要在本地完成拉取、解析、编译部署，并产出运维脚本。
> 工作根目录：/Users/tigzx/workspace/ai-pipeline · 环境：Mac Mini M6(arm64) + OrbStack（docker context=orbstack，虚拟机内存 ≤ 16G）
> 全局约束：docs/05-安全与确认策略.md（确认策略 §1.1 / 安全红线 §1.2 / 备份回滚 §1.3 / 日志 §1.4）
> 引用规则：rules/build-deploy-rule.md §3.1（拉取解析）/ §3.2（部署校验）/ §3.3（一键脚本）/ §3.4（产物）

**输入**：{REPO}、{REPO_URL}（{BRAND} 可选，品牌替换属 P3）
**确认点**：全程仅 1 个——拉起/构建启动命令（§3.2.5/§3.2.6）打印完整命令等待确认
**执行方式**：A→F 连续执行，仅在确认点暂停

## 步骤总览

A 拉取解析（部署文档）→ B 部署校验 → C 编译部署 → D 健康探测与日志 → E 一键脚本（必做）→ F 收尾产物

## A. 拉取与解析（规则 §3.1）

1. Terminal 执行 `scripts/pipeline.sh {REPO_URL}` → 仓库落地 `repos/{REPO}/`
   - clone 后 `git -C repos/{REPO} fsck --short` 校验；失败自动重试一次，仍失败 `git clone --depth=1` 浅克隆兜底
2. 扫描 `README*.md`（含 CN/zh/JA/KO 变体，优先中文版）并读取
3. 解析 9 维度（简介/技术栈/依赖清单/启动命令/构建方式/配置项/接口/已知坑/部署模式标识）→ `readme-parse/{REPO}.json`
4. 生成部署知识文档 → `knowledge/{REPO}-summary.md`
5. 初始化报告 `output/{REPO}-report.md` 章节 1-7（任务概要/仓库结构/依赖/启动命令/访问地址/风险/执行记录）
6. 追加 `output/task-log.md`

## B. 部署校验（规则 §3.2.1-§3.2.4）

1. 扫描 `repos/{REPO}/` 根目录判定 {DEPLOY_MODE}（docker/native/混合）→ 写入 `readme-parse/{REPO}.json` 的 `deploy_mode` 字段
2. 前置检查并行 4 项：
   - docker 模式（§3.2.2）：`docker info`+`docker compose version`（失败提示启动 OrbStack 并中止）、端口占用、`docker compose config --quiet`、.env（无则从 .env.example 复制）
   - native 模式（§3.2.3）：运行时版本（node/python/go）、端口占用、环境变量、`df -h` 磁盘
3. docker 模式镜像架构识别（§3.2.4）：`docker manifest inspect` 超时不阻塞；仅 amd64 → 标注 M 芯片风险，可追加 `--platform linux/amd64`
4. 构建前资源校验（00 §1.2）：OrbStack 内存 ≤16G、磁盘充足

## C. 编译部署（规则 §3.2.5-§3.2.6）⚠️ 唯一确认点

- docker 模式：打印完整 `docker compose up -d` 命令 → **等待确认** → 执行（超时等待 healthcheck start_period）
- native 模式：打印完整构建启动命令 → **等待确认** → 执行：
  - Node/npm：包管理器识别（pnpm→yarn→npm）→ 依赖安装（超时 300s 重试 1 次）→ build → 后台启动
  - Python：venv → pip install → 启动（python main.py / uvicorn main:app）
  - Go：go mod download → go build → ./bin/{REPO}
  - npm 资源包（library）：仅 build + 产物完整性校验，不启动
  - PID → `output/{REPO}-native.pid`；日志 → `output/{REPO}-native.log`
- 失败 → 按 00 §1.3 回滚 + 按 §3.2.9 分类诊断（架构/资源/配置/依赖/编译）

## D. 健康探测与日志（规则 §3.2.7-§3.2.8）

1. curl 探测文档标注端口，期望 200；非 200 等 30s 重试一次；native 查 `kill -0 <PID>` 进程存活；library 项目验证产物字段
2. 日志 tail 50（docker compose logs / native log）+ WARNING/ERROR 扫描 → 处置建议
3. 部署日志 → `output/{REPO}-deploy-log.md`；report 追加章节 8（部署验证）

## E. 一键运维脚本（规则 §3.3，必做，不可跳过）

1. 确认/生成 `scripts/one-key.sh`：双模式自动检测 {DEPLOY_MODE}（docker compose / native 进程管理），动作 start/stop/restart/build/status + `--help` + 非法参数报错；日志 → `output/one-key-operation.log`；赋执行权限
2. docker 重新构建发布配套：确认 `scripts/rebuild-deploy.sh {REPO}` 可用（P3 改码后复用）
3. 按当前 {DEPLOY_MODE} 实测 5 个动作 + `--help` + 非法参数处理，结果记入日志
4. report 追加章节 12（一键运维脚本说明：路径、动作表、日志路径）

## F. 收尾

- 产物核对：`readme-parse/{REPO}.json` · `knowledge/{REPO}-summary.md` · `output/{REPO}-report.md`（章节 1-8、12）· `output/{REPO}-deploy-log.md` · `scripts/one-key.sh`
- `knowledge/{REPO}-summary.md` 补充【部署踩坑清单】；task-log 追加
- 输出总结：拉取✓/✗ · 解析✓/✗ · 部署✓/✗ · 部署模式 · 访问地址 · 一键脚本实测✓/✗ · 风险一览

## 使用示例

```
执行 P1（fetch-build-deploy），参数：
{REPO} = WeKnora
{REPO_URL} = https://github.com/Tencent/WeKnora
```
