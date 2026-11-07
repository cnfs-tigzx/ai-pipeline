# OpenViking 知识库摘要

> 来源：repos/OpenViking（https://github.com/volcengine/OpenViking），commit 537a38d19 (main)
> 解析产物：readme-parse/OpenViking.json · 部署模式：docker
> 解析日期：2026-11-05 · 任务：20261105-233435

## 一句话定位

火山引擎开源的 **AI Agent 上下文数据库**：用 `viking://` 虚拟文件系统统一存放 Agent 的知识、记忆和技能，Agent 像操作文件一样（ls/tree/read/write/grep）浏览和修改上下文，每个目录带 L0 摘要 / L1 概览 / L2 全文三层加载。

## 核心概念

- **viking:// 虚拟文件系统**：`resources/`（项目文档、代码、网页）+ `user/{user_id}/`（memories、skills、peers）
- **三层上下文**：L0 一句话摘要（.abstract.md）→ L1 结构与要点（.overview.md）→ L2 全文按需加载
- **目录级检索**：语义搜索限定在子树内，不做全库平坦向量扫描；find 直接查，search 从会话上下文规划
- **会话即文件**：提交会话归档对话并抽取记忆为 Markdown，可查看/编辑/合并
- **VikingBot**：基于 OpenViking 的 Agent 框架，官方镜像默认随服务启动

## 技术栈

| 层 | 技术 |
|----|------|
| 核心服务 | Python >= 3.10，FastAPI + uvicorn + litellm + pydantic v2 |
| CLI | Rust（crates/ov_cli，`ov` 命令，Apache 2.0） |
| 文件系统绑定 | Rust→Python（crates/ragfs-python，maturin/PyO3） |
| C++ 扩展 | cmake >= 3.15（src/） |
| Web 控制台 | web-studio（Vite SPA，/studio 路径，Node.js 构建） |
| 反代 | Caddy 2（legacy，端口 1934） |
| 部署 | Docker Compose / Railway / uv tool install / pip |

## 部署要点（docker 模式，推荐）

- **镜像**：`ghcr.io/volcengine/openviking:latest`（多架构，内置 VikingBot + server + console UI）
- **国内镜像站备选**：`openviking-cn-beijing.cr.volces.com/volcengine/openviking:latest`（当前部署实际使用此源，ghcr.io 本地限速 ~0.06MB/s）
- **启动**：`docker compose up -d`（本地模式**无需 .env**）
- **端口**：1933 = openviking 直连（宿主=容器同端口）；1934 = Caddy legacy 反代（旧部署保留，新部署可直连 1933）
- **数据持久化**：`~/.openviking:/app/.openviking`（宿主目录挂载）
- **健康检查**：`openviking-entrypoint --healthcheck`，interval 30s / start_period 30s / retries 3
- **restart**：unless-stopped
- **关键环境变量**：OPENVIKING_SERVER_PORT（默认 1933）、OPENVIKING_PUBLIC_BASE_URL（公网 HTTPS）、OV_ACME_EMAIL、OPENVIKING_GATEWAY_ENABLED/MANAGEMENT_KEY/ENCRYPTION_KEY

## native 模式（备用）

- 向导安装：`uv tool install openviking --upgrade && openviking-server init`（写 `~/.openviking/ov.conf`，前台运行）
- VikingBot：`pip install "openviking[bot]"` → `openviking-server --with-bot` → `ov chat`
- 源码构建（仅开发）：make build / build-cli / build-studio，需 Rust 1.91.1+、CMake 3.15+、Clang 11+/GCC 9+、Node 18+

## 模型供应商（必配才能完整工作）

服务需要 **embedding 模型 + VLM**。配置向导支持：火山方舟、OpenAI、Codex OAuth、Kimi、GLM、本地 Ollama。基准测试用的是 Doubao 2.0 Pro（VLM）+ Doubao-embedding-vision。

**当前部署已配置生效（2026-11-06）**：`~/.openviking/ov.conf` 采用火山方舟双接入点——VLM=GLM-5.3-Flash（ep-20261105181307-4s825，推理模型，带 reasoning_content，支持视觉）；Embedding=Doubao-embedding-vision（ep-20261102001943-79bg5，dense · multimodal · 1024 维）；api_base=https://ark.cn-beijing.volces.com/api/v3；认证 auth_mode=api_key。修改 ov.conf 后需重启容器生效。

## 接入方式

- **记忆插件**：`curl -fsSL https://openviking.ai/install | bash`，支持 Claude Code / Codex / Cursor / TRAE / OpenCode 等（Hooks + MCP）
- **CLI**：`ov status / add-resource / task status / ls / tree / find / grep / chat`
- **SDK**：Python / Go / TypeScript + HTTP API + MCP 客户端
- **框架**：LangChain/LangGraph（AGPLv3）、Microsoft Agent Framework（MIT）

## 基准成绩（官方 0.3.22）

- LoCoMo 用户记忆：接入后 3 框架 80-83% 准确率（原生 24-57%），输入 token 降 34.3-91.0%，查询延迟降 58-66%
- tau2-bench 任务成功：+6.87pp（retail）/ +11.87pp（airline）

## 许可证结构

主项目 AGPLv3；crates/ov_cli 与 examples 为 Apache 2.0；LangChain 适配器 AGPLv3、MS Agent Framework 适配器 MIT。禁止整体改写后重新开源、未经书面授权转译代码语言。

## 部署踩坑清单

1. **ghcr.io 国内访问受限**：README 原文注明，失败切火山镜像站（compose 注释里有现成行）
2. **公网暴露必须配认证**：非本机访问前配 guides/04-authentication；OAuth 需 OPENVIKING_PUBLIC_BASE_URL
3. **模型 Key 未配是预期状态**：服务能起，但语义摘要/记忆处理需要 embedding+VLM
4. **端口语义**：1934 是 legacy Caddy 入口，健康探测优先 1933
5. **compose 的 `version: "3.8"` 字段过时**：新 compose v5 仅 WARN 不阻塞
6. **本地克隆**：HTTPS 克隆 OpenViking 一次成功（91659 对象，66198 delta）；`git fsck --short` 在本机 git 不支持，用标准 `git fsck` 校验（退出码 0）
7. **容器 unhealthy = 缺 ov.conf**（2026-11-06 实踩）：首次启动 /health 返回 503 pending_initialization，`~/.openviking/` 为空；修复=把 ov.conf 放进挂载目录（或容器内 `openviking-server init`）；entrypoint 自动等待文件出现后拉起服务，放好配置即可恢复 healthy，无需手动重启
8. **test-model 探测 invalid_request 的真因**：`POST /api/v1/admin/configuration/test-model` 的 `config` 只放敏感字段（provider/api_key），model/api_base 等非敏感字段必须放 `fallback`；把完整配置塞进 config 会触发 VLMConfig 校验失败（ValueError → invalid_request，报 requires 'model' to be set），误判为模型不可用——实际方舟接入点四种调用方式（文本/图片 × chat/completions/responses）全部正常
9. **账户初始化次序**：api_key 模式启动后自动创建 `default` 空壳账户（user_count=0）；POST /api/v1/admin/accounts/default/accounts 会报 ALREADY_EXISTS，正确做法是直接向 `/admin/accounts/default/users` 创建 admin 用户；user_key 只在创建响应中出现一次，务必落盘（本地存 output/.ov-user-key.txt）
10. **dev 免认证模式的三重约束**（2026-11-07 实踩）：① dev 模式强制 loopback 绑定，host=0.0.0.0 直接 sys.exit(1)（auth/plugins/dev.py）；② docker 里 entrypoint 的 --host 默认 0.0.0.0 且**优先于 ov.conf**，必须透传 OPENVIKING_SERVER_HOST=127.0.0.1（compose environment 原本没有这个变量）；③ 容器内绑 loopback 后标准 ports 映射不可达，OrbStack 下用 network_mode: host + 其 VM→Mac loopback 端口转发即可让宿主机 localhost:1933 直连（重建后首几个请求可能 exit 52 空响应，转发链路就绪后恢复）。dev 模式下 /api/v1/admin/* 一律 PERMISSION_DENIED，切回 api_key 模式才能管理账户
