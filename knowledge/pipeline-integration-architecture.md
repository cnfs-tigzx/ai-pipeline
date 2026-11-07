# ai-pipeline × Mem0 × OpenViking × WeKnora 集成架构方案

> 生成日期：2026-11-07 · 类型：产品架构设计文档（已落地并实测验证）
> 结论：采用【无侵入式组合 + 编排层统一】，不做三者源码合并。

## 一、总体架构

```
┌─────────────────────── 用户层 ────────────────────────┐
│  开发者(tigzx)                   业务/产品/测试人员      │
│      │                                │                │
│  Cline 对话 Agent               WeKnora Web 门户        │
│  (Plan/Act 总控编排)            (问答/检索/Wiki)        │
└──────┼─────────────────────────────────┼────────────────┘
       │ 规则驱动(.clinerules P1-P5)       │ MCP(Streamable HTTP)
┌──────▼───── 能力层（三个独立服务进程，可插拔）───────────┐
│ 【经验记忆层 Mem0】     【项目资产层 OpenViking】 【业务门户 WeKnora】 │
│ REST:8888/Dash:3000    viking://:1933           Web:80/API:8080    │
│ 坑点·偏好·结论          源码·文档·表格·SOP        手册·口径·FAQ·Wiki  │
│ MCP已接入(stdio)        L0/L1/L2 分层加载         RAG+RBAC+内置MCP   │
└─────────────────────────────────────────────────────────┘
       ▲ 胶水层（流水线框架自有，可随时替换重写）
│  scripts/ov-sync.sh · scripts/weknora-sync.sh（本次新增）   │
│  mem0-one-key.sh · one-key.sh · pipeline.sh（已有）         │
└─────────────────────────────────────────────────────────┘
```

核心思想：ai-pipeline（规则体系 + Cline）是唯一大脑；三个工程是可插拔器官；
胶水脚本与 MCP 配置是神经。任何器官可单独重启/替换，大脑不受伤。

## 二、组件职责边界（含重叠裁决）

| 层 | 组件 | 存什么 | 谁写入 | 谁读取 | 生命周期 |
|----|------|--------|--------|--------|----------|
| 经验记忆层 | Mem0 | 结构化经验事实（带标签） | Cline（任务闭环时） | Cline（任务开始时检索） | 长期，跨项目 |
| 项目资产层 | OpenViking | 原始资产：源码/SOP/表格/手册 | Cline/同步脚本 | Cline 按需分层加载 | 跟随项目版本 |
| 业务门户层 | WeKnora | 面向人的成品知识 | 同步脚本/Cline | 业务人员 Web + Cline MCP | 跟随文档版本 |

### 2.1 重叠裁决一：OpenViking memories 区 vs Mem0

OpenViking 自带 `user/{uid}/memories/` 记忆区。裁决：Mem0 为唯一经验记忆源；
OpenViking 只使用 `resources/` 区，memories 区不启用双写，避免记忆分裂。

### 2.2 重叠裁决二：同一手册的两份副本

Source of truth = OpenViking（原始结构全文）；WeKnora 存分发副本（分块索引供问答）。
同步方向单向 OpenViking → WeKnora，不回写，允许版本短暂不一致。

## 三、数据流

### 3.1 场景A：二次开发（P3）+ 使用手册

1. Cline 接收 P3 任务 → Mem0.search(labels=[二次开发], project_id={REPO}) 检索历史坑点
2. 开发中 → Cline 经 MCP 读 viking://resources/{REPO}/（L0/L1 定位、按需读 L2）；业务口径经 WeKnora MCP 反向检索
3. 手册生成 → ov-sync.sh 推 OpenViking manuals/ + weknora-sync.sh 推 WeKnora 门户（业务人员立即可问答）
4. 任务闭环 → Mem0.add(本次新坑, labels=[二次开发])（规则 01 §1.3）

### 3.2 场景B：数策中心（P2 扩展）

1. P2 抓取表格 → knowledge/table-{REPO}.json → ov-sync.sh 推 viking://resources/{REPO}/datasets/（L0 摘要标注口径与来源）
2. 分析规则、用户偏好、历史结论 → Mem0
3. 统计口径说明 → weknora-sync.sh 推 WeKnora → 业务人员 Web 直接提问（不依赖 Cline）


## 五、方案对比：无侵入式 vs 源码合并（为什么选无侵入）

| 维度 | 无侵入式（已采用） | 源码合并统一平台 |
|------|------------------|------------------|
| 许可证 | 独立进程独立部署，仅 API/MCP 调用，不触发传染 | OpenViking 主项目 AGPLv3，合并修改后对外提供网络服务 → 整个平台须开源 |
| 上游跟进 | 三者均为周更级活跃项目，随时 pull（mem0 最新提交即 5 个 CRITICAL 漏洞修复） | fork 后 1-3 个月落后主线，安全补丁人工 cherry-pick |
| 技术栈 | Rust+Python / Go / Python+Next.js 各自独立 | 单人维护 4 种技术栈 + 3 套数据库 + 3 套用户体系 |
| 改造成本 | 本方案 2 天完成（实测） | 月级工作量，且必然裁剪功能 |
| 失败半径 | 单组件故障单独重启，大脑（Cline+规则）不受伤 | 一损俱损 |

### 5.1 关键澄清：统一体验 ≠ 统一源码

三套入口的不适感，正解是统一【部署编排 + 反代入口 + 身份】（合并交付形态）；
源码合并不解决 UI 体验问题（界面仍是三套），却引入全部合并成本。

## 六、落地执行记录（2026-11-07，阶段一+二实测）

### 6.1 WeKnora 重新拉起（镜像本地齐备，秒级）

- `cd repos/WeKnora && docker compose up -d` → 5 服务启动，app healthy
- Web :80 → 200；API :8080/health → 200

### 6.2 WeKnora 程序化集成（无侵入，全程公开 API）

| 步骤 | 结果 |
|------|------|
| 注册流水线服务账号 pipeline@tigzx.com（pipeline-bot） | ✅ tenant 10002，workspace owner |
| 创建知识库「产品手册与业务口径」 | ✅ kb_id 61674557-9bcb-4eee-872c-b85cc712d3ce |
| 创建 MCP endpoint（POST /api/v1/mcp-endpoints） | ✅ endpoint_id 4fb7fad2-d491-48a8-b75b-e27a68b84db4 + 一次性 token |
| 创建 tenant API Key（ai-pipeline-sync，full_access） | ✅ 供同步脚本长期使用 |
| MCP 握手 POST /mcp/{endpoint_id} | ✅ serverInfo weknora 1.0.0，工具：list_knowledge_bases/search_knowledge/grep_chunks/read_document/ask |

- Python 版 mcp-server/（compose 的 mcp 服务，full profile）已弃用，未启动
- 凭据全部落盘 local-secrets.md（gitignored）

### 6.3 OpenViking MCP 与 REST 写入

- MCP 握手 POST http://localhost:1933/mcp → 200（dev 模式免认证，Streamable HTTP）
- REST 写入链路实测：POST /resources/temp_upload → temp_file_id → POST /resources {temp_file_id,to,wait} → root_uri `viking://resources/ai-pipeline/sync-test`，语义 1 条 + 嵌入 3 条零错误

### 6.4 Cline MCP 配置更新（cline_mcp_settings.json）

- 原 mem0（stdio）保留不动；新增 openviking（streamableHttp :1933/mcp）与 weknora（streamableHttp :8080/mcp/{endpoint_id} + Bearer）
- 修改前备份：`.auto-bak/20261107-cline-mcp/`
- 生效条件：重启 Cline（reload MCP）

### 6.5 新增流水线资产

| 文件 | 说明 |
|------|------|
| scripts/ov-sync.sh | 文件 → OpenViking（temp_upload + add_resource，wait=true） |
| scripts/weknora-sync.sh | 文档 → WeKnora KB（tenant API Key 认证，凭据自动解析） |
| .clinerules/07-context-federation-rule.md | 三层职责/检索写入纪律/双写禁令/AGPLv3 边界 |
| 00-base-general.md | 规则索引 + 脚本清单已登记 |

## 七、验收清单（全部通过）

- [x] 三服务健康（mem0 8888 · openviking 1933 · weknora 80/8080）
- [x] WeKnora MCP endpoint 握手 + 9 工具（ask/search_knowledge/grep_chunks/list_documents/list_knowledge_bases/read_document/wiki_index/wiki_read_page/wiki_search）
- [x] OpenViking MCP 握手 + REST 资源写入（root_uri viking://resources/OpenViking/sop 实测落位）
- [x] ov-sync.sh 实测：knowledge/OpenViking-summary.md → viking://resources/OpenViking/sop/
- [x] weknora-sync.sh 实测：knowledge/WeKnora-user-manual.md → KB 解析完成（方舟 embedding）
- [x] MCP 语义检索全链路：search_knowledge「这个产品怎么部署启动」hybrid 命中 10 条，指向手册部署分块
- [ ] Cline 重启后三 MCP 工具可见（人工动作：重启 Cline reload MCP）

## 八、WeKnora 模型配置踩坑（2026-11-07 实录）

新 workspace 接入文档解析必读，四处坑逐个踩过：

1. **上传路由**：POST `/api/v1/knowledge-bases/{kb}/knowledge/file`（中间有 `/knowledge` 段），multipart 字段 file/fileName
2. **API Key 认证头**：tenant API Key 用 `X-API-Key` 头（不是 Bearer）；Bearer 保留给 MCP endpoint token
3. **模型 source 枚举**：`source` 必须是 `remote`（API 模型）；传 `volcengine` 会被当 Ollama 本地模型触发下载→download_failed。
   厂商标识放 `parameters.provider="volcengine"`，模型名必须在 catalog（models.generated.json）内
4. **凭据子资源**：创建模型时 `parameters.api_key` 会被剥离（GET 显示 configured:false），必须再调
   `PUT /models/{id}/credentials {"api_key": "..."}` 才生效
5. **KB 绑定**：`PUT /knowledge-bases/{id}` 带 `config.embedding_model_id`（nil=不改动）；文档解析完成后自动 enable
6. **检索**：REST `GET /knowledge/search?keyword=...&kb_ids=["..."]`（keyword 不是 q；kb_ids 是 JSON 数组字符串）；
   语义检索走 MCP `search_knowledge`（hybrid 模式，含 CJK）

## 九、阶段三执行记录（2026-11-07，体验统一已落地）

### 9.1 统一编排（无侵入实现）

- 新增 `scripts/pipeline-services.sh`：三栈统一 start/stop/restart/status/health（mem0 → openviking → weknora → caddy 顺序编排，逆序停止）
- 设计决策：**放弃顶层 compose include**（三栈项目名/卷名/网络各自独立，include 合并会破坏无侵入原则并引发命名冲突），
  改为编排脚本按各栈自身 compose 文件操作，容器命名与数据卷零改动
- `one-key.sh services [动作] [栈]` 转发入口已挂载；全景 status 含容器表 + 8 项端口探测 + 内存占用
- 实测：11 容器全景列出，内存合计约 1.7G（openviking 808M / mem0 410M / WeKnora 488M / caddy 27M），OrbStack 16G 内宽裕

### 9.2 统一入口门户（:9000）

- 新增 `docker/pipeline-caddy/`（Caddyfile + compose + 导航页），caddy:2 本地镜像，新增 12 容器 pipeline-caddy
- 路由：`weknora.localhost:9000` → WeKnora Web · `mem0.localhost:9000` → mem0 Dashboard · `studio.localhost:9000` → OpenViking（含 /studio）· `:9000/` → 联邦导航页
- 实测四路由 200/307/302 全通过（weknora 返回 Tigzx 品牌化页面）；各服务原端口保持直连不变，纯增量

### 9.3 ask 工具补齐（遗留事项 1 完成）

- 知识问答 LLM：catalog 中 `glm-5-3-flash-260828`（volcengine，1M 上下文）→ remote 模型 fa04f489 + 方舟凭据（同 embedding 流程四要点）
- `PATCH /api/v1/agents/builtin-quick-answer {"model_id": ...}` 绑定快速问答 agent
- MCP `ask` 实测：检索 → GLM 合成 → 返回回答 + session_id（连续对话）✅
- 注意：builtin agent 的 GET 单查返回 500，绑定须用 PATCH 部分更新（PUT 全量对 builtin 不可用）

## 十、验收清单

- [x] pipeline-services.sh 全景 status（11 容器 + 8 探测 + 内存视图）
- [x] one-key.sh services 转发
- [x] 门户四路由（含品牌化 WeKnora 页面）
- [x] ask 工具（LLM + 检索 + session）
- [ ] Cline 重启后三 MCP 工具可见（人工动作）

## 十一、当前遗留

1. WeKnora 检索召回质量：ask 回答称"未直接匹配到部署要求"——后续可调 KB 分块配置或为手册补充 FAQ 条目提升命中率
2. OpenViking dev 模式仅本机可达；公网须切 api_key 模式（参考 knowledge/OpenViking-summary.md 踩坑 10）
3. Git 同步：`./scripts/git-push.sh sync` 推送全部集成资产（密钥文件均在 .gitignore，推送前脚本自动复扫）
## 四、接入方式矩阵（已实测）

| 组件 | Cline 接入（机器） | 人工接入（人） | 实测状态 |
|------|-------------------|---------------|----------|
| Mem0 | MCP stdio：mem0__add/search_memories | Dashboard :3000 | 已接入，规则 01 已定义 |
| OpenViking | MCP Streamable HTTP :1933/mcp + REST | web-studio /studio | MCP 握手 200；REST 写入成功 |
| WeKnora | 内置 Go MCP :8080/mcp/{endpoint_id} + REST | Web :80 | MCP 握手成功（5 工具）；REST 全链路打通 |
