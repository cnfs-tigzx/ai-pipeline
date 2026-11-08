# 单节点 Docker 智能体流水线架构评估报告

> 日期：2026-11-08 · 类型：架构评估（目标五层架构 vs ai-pipeline 现状实测）
> 结论先行：**总体适配，无硬性冲突**。三处原设计需按本机环境裁决：DinD 弃用、独立 MinIO 弃用、编排层改为「Prefect 宏观 + Cline 微观」双脑分级。资源余量充足。

## 一、现状盘点（实测数据 2026-11-08）

| 维度 | 实测结果 |
|------|----------|
| 宿主资源 | Mac Mini M6 24G · OrbStack VM 限额 19.57GiB（规则文档写 16G 需更新）· 磁盘可用 347G |
| 运行容器 | 8 个约 1.2G：WeKnora×5 + openviking×2 + pipeline-caddy（:9000 门户） |
| 已有联邦 | mem0（MCP stdio + REST :8888 + Dash :3000，当前停置）· OpenViking :1933 · WeKnora :80/:8080 |
| 编排现状 | Cline（VSCode 扩展）唯一大脑，P0-P5 提示词规则流，无 DAG 引擎 |
| 模型接入 | 火山方舟 Ark 直连，凭据分散在 Cline 配置与 WeKnora catalog，无统一网关 |
| 关键发现 | WeKnora compose **已内置 Langfuse v3 全家桶**（web/worker/clickhouse/db-init/langfuse-minio，复用 WeKnora-postgres），profile 未启用；另有独立 minio/neo4j/doris 等 profile |

尚未存在：Prefect、LiteLLM、Langfuse（启用态）、DuckDB、Cline CLI（`which cline` 为空）、DinD。

## 二、逐层适配评估

| 目标层 | 目标组件 | 现状 | 适配度 | 裁决 |
|--------|----------|------|--------|------|
| 编排控制 | Prefect + PostgreSQL | 无 | ★★★☆ | **引入，双脑分级**（见裁决1）；PG 独立新建 postgres:17-alpine |
| 模型网关 | LiteLLM | 无 | ★★★★ | **引入**；收口范围排除 WeKnora（见裁决5） |
| 执行工具 | Cline Headless SDK | VSCode 扩展，无 CLI | ★★☆ | 两阶段：近期保持交互主控，验证 CLI 后渐进接管确定性子任务 |
| 执行工具 | Playwright | 已有 1.64.1 + @playwright/mcp | ★★★★★ | 直接适配，Prefect task 内用 Python SDK |
| 执行工具 | DuckDB | 无（pip 即装） | ★★★★★ | uv 环境直接适配 |
| 执行工具 | Docker DinD | OrbStack | ★☆ | **弃用**，改挂宿主 docker.sock + compose project 隔离（裁决4） |
| 轨迹层 | Langfuse | WeKnora 内置 profile 未启用 | ★★★★★ | **启用内置 profile 即得**，零新增镜像管理（裁决2） |
| 记忆层 | Mem0 | 已部署已接 MCP | ★★★★★ | 补 REST 写入封装供 Prefect 流程闭环调用（对齐规则01） |
| 资产层 | OpenViking + MinIO | OpenViking 已运行且为 source of truth | ★★★★ | **不新增独立 MinIO**，OpenViking 单层承载资产（裁决3） |
| 知识层 | WeKnora | MCP endpoint + KB + ask 已通 | ★★★★★ | 零调整，作为 LiteLLM 收口例外 |

## 三、五个关键架构裁决

### 裁决1：编排双脑分级（最重要）
- **Prefect = 宏观任务编排**：定时触发、节点重试/超时、人工审批挂起、无人值守、执行历史可视化。主战场 = 数策中心周期性数据任务。
- **Cline = 微观执行主控**：开发中心 P1-P5 交互式规则流不动，.clinerules 确认策略保留。
- 依据：开发中心任务人工判断密集（备份/确认点/回滚决策），DAG 化收益低；数策中心抓取-清洗-归档链路确定性高，最适合编排化。
- 若不裁决，两个「大脑」会产生任务归属混乱，必须写入 08 编排规则。

### 裁决2：Langfuse 复用 WeKnora 内置 profile
- WeKnora compose 的 langfuse 全家桶复用 WeKnora-postgres（paradedb pg17，db-init 自动建库），`docker compose --profile langfuse up -d` 即启用。
- 轨迹喂入：LiteLLM 原生 langfuse callback（env 即可）+ Prefect flow 埋点。
- Cline（VSCode）轨迹不硬接 Langfuse，以任务闭环产物（dev-log/change-log/task-log）为准；CLI 模式成熟后再由编排包裹层上报。
- 既定错峰纪律保留：langfuse profile 与 doris/milvus 等重 profile 不并行。

### 裁决3：不新增独立 MinIO
- 规则07已裁决 OpenViking 为唯一资产层（source of truth），数据集/快照/报表入 `viking://resources/{REPO}/datasets|manuals|sop`，血缘记录在文件头元数据。
- WeKnora 内的 langfuse-minio 仅服务 Langfuse 自身事件存储，不承担业务资产。
- 若未来 Prefect 需要 S3 artifact，复用 WeKnora minio profile，注意其默认端口 9000 与 pipeline-caddy 冲突，启用须改 MINIO_PORT。

### 裁决4：DinD 弃用（OrbStack 环境不适配）
- Mac + OrbStack 嵌套 DinD 需 privileged + 双层 VM，内存翻倍且脆弱。
- 替代：Prefect worker / Cline 直接用宿主 Docker（或挂 /var/run/docker.sock），隔离性用 compose project 名 + 独立 network + 自动清理（down --remove-orphans）实现。
- 收益：省 2-4G 内存，且与现有 rebuild-deploy.sh / one-key.sh 脚本体系天然兼容。

### 裁决5：LiteLLM 收口范围 =「AI 能力」，WeKnora 例外
- 收口：Cline 模型配置指向 LiteLLM（OpenAI-compatible，方舟路由）、Prefect 流内 LLM 任务（清洗/提炼）、mem0 server LLM 配置。
- 例外：WeKnora 自带模型 catalog（remote + provider=volcengine + 凭据子资源流程，见集成文档§八踩坑），无侵入原则下不改造其模型层。
- 附带收益：LiteLLM virtual key 统一凭据分发，方舟 key 只在 litellm.env 一处。

## 四、资源核算

| 栈 | 新增容器 | 预估内存 |
|----|----------|----------|
| 现有联邦（常态） | 8 | ~1.2G（mem0 栈拉起后 +1.2G） |
| Prefect | server + worker + postgres:17-alpine | ~0.9-1.3G |
| LiteLLM | proxy | ~0.2G |
| Langfuse（WeKnora profile） | 5 | ~1.5-2G |

常态合计约 5-6G，峰值约 8G，远低于 OrbStack 19.57G 限额。错峰纪律不变。

## 五、若实施：结构调整清单

### 新增
- `docker/litellm/`：docker-compose.yml + config.yaml（方舟模型路由）+ litellm.env（gitignored）
- `docker/prefect/`：docker-compose.yml（server + worker + postgres:17-alpine，prefect :4200）
- `prefect-flows/`：data_center.py（数策中心 flow）、dev_center.py（阶段3）+ requirements.txt
- `scripts/mem0-rest.sh` 或 flows 内 helper：mem0 REST 写入（user_id/project_id/labels 对齐规则01 §1.3 摘要模板）

### 修改
- `scripts/pipeline-services.sh`：stack_dir/stacks_for 增加 litellm、prefect 两个 case（沿用「各栈自身 compose + 编排脚本」无侵入模式，one-key.sh services 自动继承）
- `.clinerules/00-base-general.md`：脚本清单 + 端口登记（litellm :4000、prefect :4200）+ 无人值守流的高危等价确认（Prefect manual approval）
- `.clinerules/07-context-federation-rule.md`：Langfuse 归属（轨迹层，禁入 Mem0）、MinIO 裁决、LiteLLM 例外、OrbStack 限额数字更正
- 新增 `.clinerules/08-orchestration-rule.md`：双脑职责边界、任务归属判定、审批节点设计、flow 与规则流（P2/P3）的映射关系

### Cline 侧
- 模型 provider 指向 `http://localhost:4000`（LiteLLM virtual key）；MCP 配置不变
- 阶段3：安装 cline CLI（`npm i -g @cline/cli`）验证 headless 单任务执行，仅将无歧义子任务（如 readme 解析）先行 DAG 化

## 六、两套测试用例的适配落点

### 用例一（开发中心，现状已覆盖约 7/9 步）
- 历史项目（tigzx-dicom/mirobody/TabClaw/WeKnora 等）已实证：拉取、修改、构建部署、审批、Git 同步、OpenViking 归档、Mem0 沉淀、WeKnora 检索均走通。
- 差异步 = 步骤1（Prefect 触发）与步骤8（Langfuse 轨迹）：前者属阶段3演进项，后者由 LiteLLM callback 补齐模型调用轨迹。
- 建议保持 Cline 交互式主控，不强行 DAG 化。

### 用例二（数策中心，全新建设主战场）
- 10 步全部落在 Prefect flow：playwright(Python SDK) 抓取 → LLM 清洗（LiteLLM）→ DuckDB 分析 → ov-sync.sh 归档（复用）→ Langfuse 埋点 → Mem0 REST 沉淀 → weknora-sync.sh 推规范（复用）。
- 现有 06 规则 + ov-sync/weknora-sync 脚本直接成为被编排的子命令，改造量集中在 flow 编排层。

## 七、实施路线

| 阶段 | 内容 | 工作量 | 出口标准 |
|------|------|--------|----------|
| 0 预检 | cline CLI 可用性实测 · LiteLLM↔方舟连通 · langfuse profile 启动验证 | 0.5 天 | 三项通过或明确降级路径 |
| 1 网关+轨迹 | LiteLLM 上线 + 启用 langfuse profile + Cline 切换 provider | 1 天 | 模型调用在 Langfuse 可见 |
| 2 编排+数策 | Prefect 部署 + data_center flow 全链路（用例二） | 1-2 天 | 用例二通过标准全绿 |
| 3 演进(可选) | cline CLI headless + dev_center flow（用例一编排化） | 按需 | 确定性子任务无人值守 |

## 八、风险清单

| # | 风险 | 缓解 |
|---|------|------|
| 1 | cline CLI 为 beta，headless 成熟度未知 | 阶段0 实测；不通过则开发中心保持交互式，架构仍成立 |
| 2 | langfuse profile 首启 collation/DB 初始化问题 | db-init 已含 template1 refresh 逻辑，仍需实测 |
| 3 | LiteLLM 方舟 provider 参数映射差异 | 阶段0 用 curl 最小复现验证 |
| 4 | WeKnora minio profile 默认 :9000 与 pipeline-caddy 冲突 | 当前未启用；启用时必改 MINIO_PORT |
| 5 | docker.sock 挂载弱化信任边界 | 单人开发机可接受，08 规则中标注生产化时改 agent 容器方案 |
| 6 | 双脑职责未成文导致任务归属混乱 | 08-orchestration-rule.md 必须先于 Prefect 落地 |
| 7 | 规则文档 16G 限额与实际 19.57G 不符 | 07/00 规则修订时一并更正 |
