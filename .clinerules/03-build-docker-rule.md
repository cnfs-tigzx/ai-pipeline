# 构建部署规则（03-build-docker-rule）

> 服务阶段：P1（GitHub 拉取代码 → 生成部署文档 → 结合本地配置和环境编译部署 → 一键停止/启动/重新编译部署脚本）。
> 提示词：workflows/P1-fetch-build-deploy.md。章节编号 = 3.x；确认策略/安全红线/备份回滚见 00-base-general.md。
> 执行环境：Mac Mini M6(arm64) + OrbStack（docker context=orbstack），虚拟机内存 ≤ 16G。

## 3.1 P1-A 拉取与解析（生成部署文档）

1. **拉取代码**：Terminal 执行 `scripts/pipeline.sh {REPO_URL}`，仓库落地到 `repos/{REPO}/`
   - **完整性校验**：clone 后执行 `git -C repos/{REPO} fsck --short`，失败自动重试一次；仍失败用 `git clone --depth=1` 浅克隆兜底
2. **定位文档**：扫描仓库根目录，匹配 `README*.md` / `readme*.md`（含 CN/zh/JA/KO 等后缀变体），优先中文版
3. **解析 README（9 维度）**：项目简介、技术栈、依赖清单、启动命令、构建方式、配置项、接口、已知坑、**部署模式标识(docker/native/混合)** → `readme-parse/{REPO}.json`
4. **生成部署知识文档**：基于解析结果 → `knowledge/{REPO}-summary.md`（含依赖清单、启动命令、构建方式、配置项、已知坑）
5. **初始化报告**：`output/{REPO}-report.md` 章节 1-7（任务概要/仓库结构/依赖/启动命令/访问地址/风险/执行记录）
6. 追加 `output/task-log.md`

## 3.2 P1-B 部署校验与编译部署

**执行时机**：README 解析完成后连续执行；**执行范围**：仅在仓库目录内，不修改宿主机全局配置
**确认点**：全阶段仅 1 个——拉起/构建启动命令（§3.2.5/§3.2.6）打印完整命令等待确认

### 3.2.1 部署模式判定

扫描 `repos/{REPO}/` 根目录，按优先级判定 `{DEPLOY_MODE}`：

| 判定条件 | 部署模式 | 说明 |
|----------|----------|------|
| 存在 docker-compose.yml/.yaml | docker | 优先 docker 流程 |
| 存在 Dockerfile 但无 compose | docker | 单容器构建部署 |
| 存在 package.json 且无 docker 配置 | native | Node/npm 项目 |
| 存在 requirements.txt/pyproject.toml 且无 docker | native | Python 项目 |
| 存在 go.mod 且无 docker | native | Go 项目 |
| 同时存在 docker 与 native 配置 | 混合 | 优先 docker，docker 失败时降级 native 重试 |

- 判定结果写入 `readme-parse/{REPO}.json` 的 `deploy_mode` 字段

### 3.2.2 前置检查（docker 模式，4 项可并行）

1. Docker 可用性：`docker info` + `docker compose version`，失败则中止并提示启动 OrbStack
2. 端口占用：检查文档标注端口是否被宿主机占用
3. compose 语法：`docker compose config --quiet`
4. .env：无 `.env` 则从 `.env.example` 复制；无示例则标注风险

### 3.2.3 前置检查（native 模式，4 项可并行）

1. 运行时：Node `node -v`+`npm -v`（或 pnpm/yarn）；Python `python3 --version`+`pip3 --version`；Go `go version`，缺失提示安装并中止
2. 端口占用检查
3. 环境变量：`.env`/配置文件缺失则从示例复制或标注风险
4. 磁盘空间：`df -h`

### 3.2.4 镜像架构识别（仅 docker）

- 拉取前 `docker manifest inspect <image>`（超时不阻塞，标注"待拉取后确认"）
- 拉取后 `docker image inspect <image> --format '{{.Architecture}}'` 补充确认
- 仅 amd64 → 标注 M 芯片风险，可自动追加 `--platform linux/amd64`
- 构建前资源校验（00 §1.2）：OrbStack 内存 ≤16G、磁盘充足

### 3.2.5 执行拉起（docker 模式）⚠️ 唯一确认点

- 打印完整 `docker compose up -d` 命令 → 等待确认 → 执行
- 超时等待服务就绪（healthcheck start_period）

### 3.2.6 构建与启动（native 模式）⚠️ 唯一确认点

构建启动命令打印完整命令，等待确认后执行：

- **Node/npm**：包管理器识别 pnpm（pnpm-lock.yaml）→ yarn（yarn.lock）→ npm（package-lock.json）；依赖安装 `pnpm install` / `yarn install` / `npm ci`（无 lockfile 用 `npm install`），超时 300s 失败重试一次；有 build 脚本则构建（产物目录 dist/build/out/.next/lib）；启动：生产 `npm start` / `node dist/index.js`，无生产入口用 `npm run dev` 后台
- **Python**：`python3 -m venv .venv` → 激活 → `pip install -r requirements.txt`（或 `pip install -e .` / `poetry install`）→ `python main.py` / `python -m <module>` / `uvicorn main:app`
- **Go**：`go mod download` → `go build -o bin/{REPO} ./...` → `./bin/{REPO}`
- **npm 资源包项目（library）**：仅 build，验证产物入口与 package.json main/module/exports 字段正确，不启动服务
- **进程管理**：后台启动，PID → `output/{REPO}-native.pid`，日志 → `output/{REPO}-native.log`

### 3.2.7 健康检测

- 对文档标注的 Web/API 端口 http 探测（curl），期望 200；非 200 等 30s 重试一次
- native 额外查进程存活：`kill -0 <PID>` / `ps -p <PID>`
- library 项目：无端口探测，验证产物完整性与 package.json 字段即可

### 3.2.8 日志采集与告警

- docker：`docker compose logs --tail 50`；native：tail 50 行 `output/{REPO}-native.log`
- 扫描 WARNING/ERROR 关键字，标注并给出处置建议

### 3.2.9 收尾与诊断

- 成功 → 记录访问地址、启停命令、容器 ID（docker）/PID（native）
- 失败 → 分类诊断（架构不兼容/资源不足/配置缺失/依赖报错/编译失败），给出针对性修复方案；native 终止残留进程（kill PID）并清理临时产物
- 回滚按 00 §1.3

## 3.3 P1-C 一键运维脚本（必做，不可跳过）

生成/更新一键停止、启动、重新编译部署脚本，并实测通过：

### 3.3.1 scripts/one-key.sh（主脚本）

**双模式**：脚本自动检测 `{DEPLOY_MODE}`，docker 走 docker compose，native 走进程管理（读 PID 文件）。

| 项目 | 值 |
|------|-----|
| 路径 | `scripts/one-key.sh` |
| 调用 | `./scripts/one-key.sh <动作>` |
| 日志 | `output/one-key-operation.log` |
| 帮助 | `./scripts/one-key.sh --help`（未知参数报错并显示帮助） |

| 动作 | docker 模式 | native 模式 |
|------|-------------|-------------|
| start | docker compose up -d | 依赖安装 + 构建 + 后台启动进程，记录 PID |
| stop | docker compose down | kill 进程（读取 PID 文件） |
| restart | down + up -d | stop + start |
| build | docker compose build | npm run build / go build 等 |
| status | docker compose ps + 端口探测 | 进程存活 + 端口探测 |

**验收**：按当前 {DEPLOY_MODE} 实测 5 个动作 + `--help` + 非法参数处理，结果记录到日志。

### 3.3.2 配套脚本

- `scripts/pipeline.sh`：拉取/更新仓库（P1-A 已用）
- `scripts/deploy-check.sh {REPO}`：部署校验并生成 `output/{REPO}-deploy-log.md`（P1-B 辅助）
- `scripts/rebuild-deploy.sh {REPO}`：docker 重新构建并发布（P3 改码后重建复用）
- 缺失或与当前仓库不匹配（如 PROJECT_NAME 硬编码）→ 按上表规范生成/参数化新版并赋执行权限

## 3.4 产物输出

- `output/{REPO}-deploy-log.md`（部署信息来源 → 模式判定 → 前置检查 → 镜像拉取/依赖安装 → 容器/进程状态 → HTTP 探测 → 日志摘要 → 架构结论 → 风险提示）
- `output/{REPO}-report.md` 追加章节 8（部署验证）+ 章节 12（一键运维脚本说明）
- `knowledge/{REPO}-summary.md` 补充【部署踩坑清单】
- `output/task-log.md` 追加

## 3.5 构建配置策略

- docker 模式：优先使用支持 multiarch 的 Dockerfile，不强制修改，仅输出修改建议
- native 模式：不修改项目构建配置（webpack/vite/tsconfig 等），仅读取并记录构建方式
