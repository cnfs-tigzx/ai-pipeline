# Mirobody 知识库摘要

## 一、项目定位

Mirobody 是 Theta Health 开源的个人健康数据平台（Apache-2.0）。它把体检报告、穿戴设备导出、基因数据和健康日记汇入同一份记录，用随包发布的 LOINC/UCUM 词表离线标准化指标名称与单位，再由 AI agent 基于真实记录（而非模型记忆）回答可追溯的问题。开源版把记录留在用户自己的机器上。

- 仓库：https://github.com/thetahealth/mirobody
- 在线演示：https://chat.mirobody.cn/demo
- PyPI 包：`mirobody`（当前 1.5.10）
- 本地路径：`repos/mirobody/`

## 二、技术架构

| 层 | 技术 | 说明 |
|---|---|---|
| 后端 | Python 3.12 | `pyproject.toml` 的 `[app]` extra；`mirobody serve` 启动 |
| 前端 | 预构建静态资源 | `frontend/` 是 Vite 产物（React + Ant Design），无源码 |
| 数据库 | PostgreSQL 17 + pgvector 0.8.6 | `holistic_db` / schema `theta_ai` |
| 模型 | llama.cpp（本地）或云端 API | OpenAI/OpenRouter/Gemini/Anthropic/DeepSeek/DashScope |
| 标准化 | LOINC 2.83 / UCUM / ICPC-3 / CPIC | 离线词表，随包发布 |
| 部署 | Docker Compose | `deploy.sh` 一键拉起 pg + mirobody + worker +（可选）llama |

三段流水线：① 收集（`mirobody/collect/`）→ ② 标准化（`mirobody/engine/` + `mirobody/standardize/`）→ ③ 智能体（`mirobody/agent/`）。

## 三、服务拓扑（compose.yaml）

| 服务 | 镜像 | 端口 | 作用 |
|---|---|---|---|
| `pg` | pgvector/pgvector:0.8.6-pg17-trixie | 127.0.0.1:18062→5432 | 数据库，healthcheck pg_isready |
| `mirobody_init` | thetahealth4mirobody/mirobody:1.5.10 | 无 | 一次性修复 upload 目录属主（uid 10001） |
| `mirobody` | thetahealth4mirobody/mirobody:1.5.10 | 127.0.0.1:18060→18060 | 应用（Web + API），HEALTHCHECK /api/health |
| `mirobody_worker` | 同 mirobody | 无 | 后台任务，依赖 pg + mirobody 健康 |
| `llama` / `llama_cpu` | ghcr.io/ggml-org/llama.cpp | 内部 8080 | 本地模型（profile local / local-cpu，Mac 用 CPU） |

卷：`mirobody_postgres`、`mirobody_upload`、`mirobody_models`。

## 四、部署方式

### Docker（推荐）
```
cd repos/mirobody && ./deploy.sh
```
`deploy.sh` 自动：创建 `.env`（umask 600）、生成 PG_PASSWORD/JWT_KEY/PG_ENCRYPTION_KEY、预检端口 18060/18062、检测 Docker Hub 可达性并按需写入 `DOCKER_MIRROR`（mirror.gcr.io / docker.1ms.run）、镜像拉取失败时本地 build。

### 100% 本地（含本地模型）
```
COMPOSE_PROFILES=local-cpu ./deploy.sh
```
建议 16G 内存、Docker 分配 ≥8G。Mac 无法用 GPU，llama-server 在宿主机运行。

### 不用 Docker（Debian/Ubuntu）
```
scripts/install_native.sh   # PostgreSQL 16 + pgvector + Python 包 + .env
scripts/start_native.sh     # worker + 应用，端口 18060
```

## 五、关键配置（config.yaml / .env）

- `ENV`：覆盖文件后缀，默认 `localdb`（生成 `config.localdb.yaml`）
- `MIROBODY_HOST_PORT` / `PG_HOST_PORT`：默认 18060 / 18062
- `MIROBODY_BIND`：默认 `127.0.0.1`（仅本机）；`0.0.0.0` 暴露全网（先读 SECURITY.md）
- `SEED_DEMO_DATA`：`true` 注入演示数据（2 账号 2019 读数）
- `PRODUCTION`：`true` 时拒绝预置验证码 / `REPLACE_THIS_VALUE` 启动
- `BOOTSTRAP_SCHEMA`：`true` 每次启动回放 `mirobody/schema/*.sql`
- 演示账号：`you@mirobody.ai` / `mom@mirobody.ai`，验证码 `111111`（mom 只读共享）

## 六、接入与扩展

- MCP：应用内「设置 → MCP 链接」生成 `/mcp/{secret}` bearer（TTL 10 天）；或 `uvx --python 3.12 mirobody mcp` stdio
- 库：`pip install mirobody`，离线 `resolve()`/`resolve_reading()`，仅依赖 numpy
- 设备 provider：放 `mirobody/collect/providers/`
- agent 工具：放 `mirobody/agent/tools/`

## 七、Logo 与品牌资源

| 文件 | 类型 | 用途 |
|---|---|---|
| `frontend/mirobody.svg` | SVG 图标 | favicon（index.html 引用） |
| `frontend/light.svg` / `frontend/dark.svg` | SVG wordmark | 浅/深色文字标 |
| `frontend/assets/logo-wordmark-light-*.svg` | SVG wordmark | 构建产物内引用 |
| `frontend/assets/logo-Pe7DjLtQ.js` | JS（内联 SVG path） | React Logo 组件 |
| `docs/images/mirobody-icon.svg` / `mirobody-icon-dark.svg` | SVG | README 图标 |
| `frontend/index.html` | HTML | `<title>Mirobody</title>`、favicon link |

注意：`frontend/` 是预构建产物，修改后需 `docker compose build mirobody` 重建镜像（frontend 被 COPY 进镜像）。

## 部署踩坑清单

1. **HTTPS 不可达 → SSH + 镜像站兜底**：github.com / registry-1.docker.io HTTPS 不通；git clone 用 SSH（git@github.com）成功；deploy.sh 自动检测 Docker Hub 不可达，写入 DOCKER_MIRROR（mirror.gcr.io / docker.1ms.run）后镜像成功拉取，无需手动干预。
2. **模型 Key 未配的预期报错**：首次启动日志出现 ERROR「no LLM model on any surface」+ 8 条 WARNING（各模型 API Key placeholder）。这是 demo 模式未配 Key 的正常提示，不影响 Web 浏览/标准化引擎/数据查看。在 http://127.0.0.1:18060/setup 填 Key 或 .env 写入后消失。
3. **前端是预构建产物**：`frontend/` 是 Vite 构建产物（非源码），Logo/文字替换需改静态文件后 `docker compose build mirobody` 重建镜像。
4. **双镜像 arm64 原生**：mirobody + pgvector 均有 arm64 版本，Apple Silicon 原生运行，无 amd64 兼容问题。
5. **deploy.sh 自动化程度高**：自动生成 .env（umask 600）、PG_PASSWORD/JWT_KEY/PG_ENCRYPTION_KEY、端口预检、镜像站检测、项目名冲突检测，几乎无需手动配置。
