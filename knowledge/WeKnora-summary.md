# WeKnora 知识库摘要

> 本文档由 AI Pipeline 自动生成，基于 `repos/WeKnora/README_CN.md` 解析结果。
> 解析日期：2026-11-04 | 任务 ID：20261104-150243 | 版本：v0.9.0

---

## 一、项目概览

| 属性 | 值 |
|------|-----|
| **项目名称** | WeKnora（维娜拉） |
| **开源方** | Tencent（腾讯） |
| **定位** | 企业级知识管理框架（基于 LLM） |
| **版本** | v0.9.0（2026-10-29） |
| **许可证** | MIT |
| **官网** | https://weknora.weixin.qq.com |
| **文档** | https://weknora.weixin.qq.com/docs/ |
| **仓库** | https://github.com/Tencent/WeKnora |

**一句话定位**：把团队分散的文档汇集起来，用于检索（RAG）、推理（Agent）和知识整理（Wiki），三种能力共享同一知识库。

### 三大核心能力

1. **RAG（检索增强生成）**：混合检索、多模态解析、原文引用，回答有据可查
2. **Agent（智能体）**：多步推理、技能与沙箱（Docker/E2B/Cube）、本机浏览器操作、MCP 工具、长期记忆
3. **Wiki（知识整理）**：自动组织文档为结构化 Wiki、知识图谱、版本回滚

---

## 二、技术架构

| 层 | 技术选型 | 关键文件 |
|----|---------|---------|
| **后端** | Go 1.26.0+，Air 热重载，进程内 anydoc 解析 Office | `go.mod`, `.golangci.yml`, `.air.toml` |
| **前端** | TypeScript + Vue，热重载，类型检查 | `frontend/package.json`, `frontend/Dockerfile` |
| **文档解析** | docreader 模块（anydoc / PaddleOCR-VL / OpenDataLoader） | `docreader/pyproject.toml` |
| **MCP Server** | 内置 Go 版（Streamable HTTP）；Python 版已弃用 | `mcp-server/`（已弃用） |
| **CLI** | `weknora`（Go），Agent 优先，JSON 信封输出 | `cli/` |
| **文档站** | Node.js 24 | `website-docs/` |
| **部署** | Docker Compose / Kubernetes (Helm) / Lite 单二进制 / 桌面版 | `docker-compose.yml`, `helm/` |

---

## 三、快速部署指南（Docker Compose）

### 前置条件

- Docker、Docker Compose、Git

### 部署步骤

```bash
git clone https://github.com/Tencent/WeKnora.git
cd WeKnora
cp .env.example .env    # 按需编辑 .env
docker compose pull     # 拉取最新镜像
docker compose up -d    # 启动核心服务
```

### 访问地址

| 服务 | 地址 |
|------|------|
| Web UI | http://localhost |
| 后端 API | http://localhost:8080 |
| 链路追踪 (Langfuse) | http://localhost:3000 |

### 可选服务（Profile）

| Profile | 说明 |
|---------|------|
| `full` | 全部功能 |
| `neo4j` | 知识图谱 (Neo4j) |
| `minio` | 对象存储 (MinIO) |
| `langfuse` | 链路追踪 (Langfuse) |

```bash
docker compose --profile neo4j --profile minio up -d
docker compose down     # 停止服务
```

### 其他部署方式

| 方式 | 适用场景 |
|------|---------|
| **Docker Compose** | 标准部署，功能完整，多服务 |
| **Kubernetes (Helm)** | 生产集群；Chart 位于 `helm/` |
| **Lite 单二进制** | 本机/低资源，零外部依赖（SQLite + 内存队列） |
| **桌面应用** | 带图形界面的 Lite 运行时（需自行构建） |

---

## 四、开发模式

频繁修改代码时无需每次重建 Docker 镜像：

```bash
make dev-start      # 启动基础设施
make dev-app        # 启动后端（新终端）
make dev-frontend   # 启动前端（新终端）
```

- 前端修改自动热重载（无需重启）
- 后端修改快速重启（5-10 秒，Air 热重载）
- 支持 IDE 断点调试

### 代码质量

```bash
make fmt    # gofmt 格式化（仅在工作区干净时运行）
make lint   # golangci-lint 检查
make test   # 全量测试
```

---

## 五、功能矩阵

### 模型厂商（内置 29 家）

OpenAI / Azure OpenAI / Anthropic / DeepSeek / Qwen / 智谱 / 混元 / 豆包 / Gemini / MiniMax / NVIDIA / SiliconFlow / OpenRouter / LiteLLM / Ollama

### 向量数据库（8 种可选）

PostgreSQL(pgvector+ParadeDB) / Elasticsearch / OpenSearch / Milvus / Weaviate / Qdrant / Apache Doris / 腾讯云 VectorDB

### 对象存储（8 种可选）

本地 / 腾讯云 COS / MinIO / AWS S3 / 火山引擎 TOS / 阿里云 OSS / 金山云 KS3 / 华为云 OBS

### 数据源（11 种）

飞书知识库 / 飞书云盘 / Lark / Confluence / GitLab / 腾讯 IMA / Notion / 语雀 / 钉钉文档 / Seafile / RSS

### IM 渠道（10 种）

企业微信 / 飞书 / Lark / QQBot / Slack / Telegram / 钉钉 / Mattermost / 微信 / 云之家

### 网络搜索（14 种）

DuckDuckGo / Bing / Google / Tavily / Baidu / Ollama / SearXNG / Keenable / 智谱 AI / Exa / Metaso / 博查 / Serply / SearchApi

### 文档格式（13 种）

PDF / Word / PPT / Excel / CSV / TXT / Markdown / HTML / EPUB / MHTML / JSON / XMind / 图片


---

## 六、配置要点

| 配置文件 | 说明 |
|---------|------|
| `.env` | 主配置（从 `.env.example` 复制） |
| `.env.example` | 标准配置示例（约 53KB，约 150 个环境变量） |
| `.env.lite.example` | Lite 版配置示例（约 4KB） |

### 关键环境变量

| 变量名 | 用途 |
|--------|------|
| `WEKNORA_VERSION` | 指定部署版本（如 0.9.0 或 latest） |
| `OLLAMA_BASE_URL` | Ollama 服务地址 |
| `WEKNORA_API_KEY` | 无界面/CI 场景 API Key |
| `WEKNORA_HOST` | 无界面/CI 场景服务地址 |

> 使用本地 Ollama：先运行 `ollama serve > /dev/null 2>&1 &`

---

## 七、安全与运维

### 安全特性

- **认证**：登录鉴权、OIDC JWKS 验签、可选复杂密码
- **授权**：多空间 RBAC（四级角色 Owner/Admin/Contributor/Viewer + 审计日志）
- **加密**：MCP/数据源凭据 AES-256-GCM、API Key AES-256-GCM
- **网络安全**：防 SSRF 出站请求、仅白名单出站模式
- **执行权限**：只读/修改前确认/自动执行三级权限

### 运维特性

- **链路追踪**：Langfuse 追踪 Agent 步骤、Token 用量与任务流水线
- **任务队列**：任务队列面板与 Worker 池治理
- **存储**：每空间多实例存储后端
- **数据库迁移**：版本升级自动迁移
- **审计**：空间审计日志、知识库活动审计

---

## 八、已知坑与避坑指南

| # | 问题 | 避坑方式 |
|---|------|---------|
| 1 | 版本不一致：仅 `docker compose up -d` 会复用缓存镜像 | 升级前必须先 `docker compose pull` |
| 2 | 安全风险：公网暴露导致信息泄露 | 部署在内网，配置防火墙，定期更新 |
| 3 | 不兼容变更（v0.8.2）：钉钉仅 Stream 模式，沙箱默认 root | 升级时阅读升级须知 |
| 4 | Python MCP Server 已弃用 | 迁移到内置 Go 版 MCP Server |
| 5 | `make fmt` 格式化全仓 | 仅在工作区干净时运行，检查 diff |
| 6 | 全量测试依赖本地基础设施 | PR 中提供定向测试结果 |
| 7 | 数据库迁移风险 | 升级时核对迁移、飞书重同步、沙箱开关 |

---

## 九、CLI 工具速查

```bash
weknora profile add prod --host https://kb.example.com --use
weknora auth login
weknora kb list
weknora link --kb my-knowledge-base    # 绑定当前目录
weknora doc upload notes.md
weknora chat "总结一下设计文档"
weknora mcp serve                      # 启动 MCP 工具面
```

> 无界面/CI 场景：设置 `WEKNORA_API_KEY` 与 `WEKNORA_HOST` 即可跳过 `auth login`

---

## 十、扩展点（9 大）

1. 技能沙箱（Docker / E2B / Cube）
2. 空间技能目录（ClawHub / SkillHub / Git / ZIP）
3. 数据源连接器
4. IM 渠道集成
5. MCP 工具接入
6. 模型厂商接入
7. 向量数据库后端
8. 对象存储后端
9. 网络搜索引擎

---

> 📄 结构化解析数据见：`readme-parse/WeKnora.json`
> 📋 完整任务报告见：`output/WeKnora-report.md`
> 📦 部署校验日志见：`output/WeKnora-deploy-log.md`

---

## 十一、M6+OrbStack 部署踩坑

> 实测环境：Mac Mini M6(arm64) 24G + OrbStack（Docker 29.8.2 / Compose v5.5.0）
> 实测日期：2026-11-04 | WeKnora v0.9.0（latest）

### ✅ 默认部署：一次通过

默认 profile（无 `--profile`）仅启动 5 个服务，镜像**全部原生 arm64/linux**，M6 无需任何适配：

| 镜像 | 架构 | 实测 |
|------|------|------|
| wechatopenai/weknora-ui:latest | arm64/linux | ✅ |
| wechatopenai/weknora-app:latest | arm64/linux | ✅ |
| wechatopenai/weknora-docreader:latest | arm64/linux | ✅ |
| paradedb/paradedb:v0.25.11-pg17 | arm64/linux | ✅ |
| redis:7.0-alpine | arm64/linux | ✅ |

启动后 `http://localhost`（Web UI）与 `http://localhost:8080/health`（API）均返回 200。

### ⚠️ 踩坑点

1. **`docker manifest inspect` 超时，但 `docker pull` 正常**
   - 现象：`docker manifest inspect <img>` 报 `context deadline exceeded`（registry-1.docker.io）
   - 原因：manifest CLI 走的 HTTP 通道与 OrbStack pull 通道行为不一致，国内直连 Docker Hub 易超时
   - 对策：架构确认改用 `docker image inspect <img> --format '{{.Architecture}}/{{.Os}}'`（拉取后本地查询，不依赖 registry）

2. **`.env` 必须先创建**
   - compose 文件大量引用 `${WEKNORA_VERSION:-latest}` 等变量，无 `.env` 时虽能用默认值，但 `.env.example` 含约 150 个变量（含 ParadeDB 调优、模型配置等），**必须 `cp .env.example .env`**

3. **docreader 镜像体积大（5.71GB）**
   - 首次拉取约 3 分钟，国内无 mirror 时需预留时间

4. **可选 profile 的 arm64 兼容性未验证**
   - `apache/doris`（fe-4.1.0/be-4.1.0）历史上 arm64 支持薄弱
   - 启用 `--profile` 前**务必**先 `docker manifest inspect` 或拉取后 `docker image inspect` 确认架构，必要时追加 `--platform linux/amd64`（会走 QEMU 仿真，性能下降）

5. **OrbStack 未配置 registry mirror**
   - 国内拉取偏慢（总耗时 ~190s / 9.6GB）
   - 建议：`~/.orbstack/config.yml` 或 docker daemon 配置国内镜像源加速

### 📌 M6 部署速查

```bash
cd /Users/tigzx/workspace/ai-pipeline/repos/WeKnora
cp .env.example .env
docker compose up -d                                    # 默认 5 服务，arm64 原生
docker compose ps                                       # 确认 healthy
curl -s http://localhost:8080/health                    # 期望 {"status":"ok"}
# 可选 profile（先确认 arm64）：
# docker manifest inspect apache/doris:fe-4.1.0
# docker compose --profile neo4j --profile minio up -d
```

