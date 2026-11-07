# 上下文联邦规则（07-context-federation-rule）

> 服务阶段：全阶段。定义 Cline 与三层上下文系统（Mem0 / OpenViking / WeKnora）的职责边界、检索与写入纪律。
> 章节编号 = 7.x（引用格式：07-context-federation-rule.md §7.2）。
> 三系统均以独立进程运行，ai-pipeline 仅经 MCP/REST/脚本调用，禁止合并源码（AGPLv3 红线）。

## 7.1 三层职责

| 层 | 系统 | 存什么 | 写入方 | 读取方 |
|----|------|--------|--------|--------|
| 经验记忆层 | Mem0（:8888，MCP 已接） | 结构化经验事实：坑点、修复方案、用户偏好、分析结论（带标签） | Cline（任务闭环，规则 01） | Cline（任务开始） |
| 项目资产层 | OpenViking（:1933） | 原始资产：源码、部署 SOP、抓取表格、数据集、手册全文 | Cline / ov-sync.sh | Cline（L0/L1/L2 按需加载） |
| 业务门户层 | WeKnora（:80/:8080） | 面向人的成品知识：产品手册、统计口径、FAQ | weknora-sync.sh / Cline | 业务人员 Web 问答 + Cline MCP |

## 7.2 检索纪律（优先级固定）

1. **经验类问题**（怎么修、为什么失败、用户偏好）→ 先 Mem0（规则 01 §1.2），命中不足再查 OpenViking resources 内历史变更文档
2. **项目资产类问题**（源码结构、部署方式、表格数据）→ OpenViking `viking://resources/{REPO}/`，先 L0/L1 判断相关性再读 L2
3. **业务口径/产品用法问题** → WeKnora MCP（search_knowledge / ask）
4. 禁止同一会话内重复检索同一层（复用已加载上下文）

## 7.3 写入纪律

- **双写禁令**：OpenViking memories 区不启用；经验事实唯一写入 Mem0
- **单向同步**：OpenViking（source of truth）→ WeKnora（分发副本），禁止回写
- **OpenViking 目标路径约定**：`viking://resources/{REPO}/manuals/`（手册）、`.../datasets/`（表格数据）、`.../sop/`（部署运维文档）
- 触发点：P2 抓表完成 → ov-sync.sh 推 datasets；P3 手册生成 → ov-sync.sh 推 manuals + weknora-sync.sh 推门户；闭环 → Mem0 归档（规则 01 §1.3）

## 7.4 同步脚本

| 脚本 | 用途 | 用法 |
|------|------|------|
| scripts/ov-sync.sh | 本地文件 → OpenViking 资产层 | `ov-sync.sh <file> viking://resources/{REPO}/manuals/ [reason]` |
| scripts/weknora-sync.sh | 本地文档 → WeKnora 知识库 | `weknora-sync.sh <file> [kb-id] [name]`（凭据自动从 local-secrets.md 解析） |

## 7.5 MCP 接入清单

| 服务 | 接入方式 | 认证 |
|------|----------|------|
| mem0 | stdio（repos/mem0/integrations/.../mcp_server.py） | MEM0_API_KEY（Cline 配置内） |
| openviking | Streamable HTTP `http://localhost:1933/mcp` | dev 模式免认证（生产切换 api_key 时补 Bearer） |
| weknora | Streamable HTTP `http://localhost:8080/mcp/<endpoint_id>` | per-endpoint Bearer Token（local-secrets.md） |

WeKnora 凭据（账号/API Key/endpoint/kb-id）统一存 `local-secrets.md`（gitignored），禁止写入任何被推送文件。

## 7.6 边界与风险

- OpenViking 为 AGPLv3：仅可独立进程部署 + API/MCP 调用；严禁将其源码文件复制进 ai-pipeline 或闭源仓库
- 三系统全开约 6-8 容器，OrbStack 16G 上限；WeKnora 重 profile（neo4j/minio/langfuse）任务与抓取错峰
- OpenViking dev 模式仅 loopback 可达；公网暴露前必须切回 api_key 模式并配认证
