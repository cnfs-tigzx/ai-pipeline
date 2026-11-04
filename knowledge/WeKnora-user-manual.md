# WeKnora 系统用户使用手册

> 基于 WeKnora v0.9.0 官方文档站（https://weknora.weixin.qq.com/docs/）整理
> 抓取日期：2026-11-04 ｜ 遵循 `.clinerules` →「GitHub 网页使用手册抓取专项规则」
> 本手册面向终端用户，不含部署、编译、开发调试内容

---

## 1. 系统概述

### 1.1 产品简介

WeKnora（维娜拉）是腾讯开源的、基于大语言模型（LLM）的知识管理框架，面向企业级文档理解、语义检索与智能推理场景。它把团队分散的文档汇集起来，用于检索、推理，并随资料更新持续维护。

**核心能力三模式：**

| 模式 | 说明 |
|------|------|
| **RAG（检索问答）** | 回答有据可查，混合检索、多模态解析、原文引用 |
| **Agent（智能推理）** | 用知识和工具完成任务，多步推理、技能与沙箱、本机浏览器、MCP 工具、长期记忆 |
| **Wiki（知识整理）** | 把文档整理成 Wiki，自动组织、知识图谱、版本回滚 |

三者工作在**同一套知识库**上。

### 1.2 v0.9.0 新增能力

- **WeKnora 助手**：解答版本、功能与配置问题，结合当前页面，以你的身份检索资料并处理任务。
- **多智能体协作**：独立处理子任务，再汇总结果。
- **自动化**：按一次性或周期计划执行重复工作。
- **执行权限与审批**：选择只读、修改前确认或自动执行，管理有范围的授权。

### 1.3 适用场景

| 需求 | 对应功能 |
|------|---------|
| 文档格式繁杂，PDF/扫描件/表格难以结构化 | 文档处理流程支持 PDF 版式分析、扫描件 OCR、Office 转换、网页抓取与图片描述 |
| 单一向量检索召回不稳 | 向量 + 关键词（BM25）混合检索，RRF 融合，Rerank 重排，可选知识图谱与 Wiki 导航 |
| 模型绑定单一厂商 | 模型抽象层：Ollama 本地模型与数十家内置厂商均可，LLM/Embedding/Rerank/VLM/ASR 分类管理 |
| 数据安全与私有化 | 全栈可私有部署；敏感凭证 AES-256 加密；多租户隔离 + RBAC 角色鉴权 |
| 多步骤任务与工具调用 | 内置 Agent（ReAct 多步推理）、MCP 工具接入、Agent Skills 沙箱执行、Web 搜索、数据分析 |
| 团队协作 | 租户（工作空间）+ 成员角色 + 组织跨租户知识库共享 + 邀请机制 |

### 1.4 核心概念

**租户与身份：**

| 概念 | 说明 |
|------|------|
| 租户 Tenant（工作空间） | 管理知识库、模型、智能体、会话和存储配额的资源与权限边界 |
| 用户 User | 登录账号，一个用户可加入多个工作空间 |
| 成员 TenantMember | 用户在某个空间中的成员关系，含角色和状态 |
| 角色 TenantRole | Owner、Admin、Contributor、Viewer 四级 |
| API Key | 程序访问凭证，可授予指定能力并限定知识库范围 |
| 组织 Organization | 连接多个工作空间，按组织成员角色共享知识库和智能体 |

**知识域：**

| 概念 | 说明 |
|------|------|
| 知识库 KnowledgeBase | 组织相关资料，配置模型、分块和索引策略。支持文档、FAQ 和 Wiki 类型 |
| 知识 Knowledge | 知识库中的一份文件、网页或手写内容，入库后可查看解析状态 |
| 分块 Chunk | 文档解析后的检索单元，可含文本、图片识别结果、表格等 |
| FAQ | 维护标准问、相似问、反例问和答案的问答条目 |
| Wiki 页面 WikiPage | 从文档生成的主题页面，带来源引用，支持编辑与版本管理 |
| 知识图谱 Entity/Relationship | 文档中的实体与关系，用于补充关联内容检索 |
| 数据源 DataSource | 持续同步外部资料的连接 |

**对话与智能体：**

| 概念 | 说明 |
|------|------|
| 会话 Session | 保存多轮问答及所选智能体、模型、知识范围和工具配置 |
| 消息 Message | 一次提问或回答，可关联图片、附件、引用和工具执行结果 |
| 模型 Model | 提供对话、向量化、重排、视觉或语音能力的模型连接 |
| Agent（自定义智能体） | 按任务配置模型、资料范围和工具，支持快速问答与智能推理 |
| 内置 Agent | 预配置的快速问答、智能推理、数据分析和 Wiki 智能体 |
| MCP 服务 | 为智能体接入外部工具，支持 SSE 和 Streamable HTTP |

### 1.5 系统访问地址

| 服务 | 地址 |
|------|------|
| Web UI | http://localhost |
| 后端 API | http://localhost:8080 |
| 链路追踪 Langfuse（可选） | http://localhost:3000 |
| MCP Server | /mcp/<endpoint_id>（Streamable HTTP） |

---

## 2. 功能模块总览

| 模块 | 功能要点 |
|------|---------|
| 注册与登录 | 密码注册/登录、OIDC 单点登录、三档注册模式、邀请机制 |
| 知识库管理 | 创建文档/FAQ/Wiki 库、上传文件、导入网页、手写 Markdown、文件夹与标签、分块编辑、画廊、批量下载 |
| 文档解析 | 支持 PDF/Word/Excel/PPT/Markdown/HTML/图片/音频等；按文件类型选解析引擎；OCR 与多模态描述 |
| 分块机制 | 自适应分块（标题/启发式/递归）、父子分块、参数可调、预览调试 |
| 检索引擎 | 向量+BM25 混合检索、RRF 融合、Rerank 重排、多向量数据库可选、知识图谱增强 |
| 模型管理 | 5 类模型（LLM/Embedding/Rerank/VLM/ASR）、29 家厂商、Ollama 本地、协议兼容覆盖 |
| Agent 引擎 | 快速问答 / 智能推理、自定义智能体、类型预设、技能沙箱、工具审批 |
| MCP 集成 | 接入外部 MCP 服务、内置 MCP Server 端点、OAuth 授权、工具审批 |
| 知识图谱 | 实体关系抽取、GraphRAG 增强检索、Neo4j 存储 |
| 数据源导入 | 飞书/Notion/Confluence/语雀/钉钉/IMA/GitLab/RSS/Seafile 定时同步 |
| 网络搜索 | 14 个搜索引擎、web_search/web_fetch 工具、SearXNG 自建 |
| IM 集成 | 企业微信/飞书/Slack/Telegram/钉钉等 10 个平台、流式回复、内置命令 |
| 网页嵌入 | 嵌入渠道 widget、安全模式、域名白名单、限流 |
| Wiki 能力 | 自动生成主题页面、目录树、图谱布局、编辑与版本回滚 |
| 权限与安全 | 多空间 RBAC、API Key、组织共享、执行权限与审批 |
| 本机浏览器 | BrowserSkill 扩展、Chrome/Edge 插件、配对与任务管理 |

---

## 3. 各模块操作步骤

### 3.1 注册与登录

**注册要求：**
- 用户名 2–50 个字符
- 密码 8–32 位，至少包含字母和数字
- 启用复杂密码策略后，还须同时包含大小写字母和特殊字符

**注册模式（三档，可在全局设置即时切换）：**

| 模式 | 公开注册 | 有效邀请链接注册 | 已有账号接受邀请 |
|------|---------|----------------|----------------|
| self_serve（开放注册） | 允许 | 允许 | 允许 |
| invite_register（仅限邀请注册） | 禁止 | 允许 | 允许 |
| invite_only（禁止注册） | 禁止 | 禁止 | 允许 |

**登录方式：**
- 密码登录：`POST /api/v1/auth/login`，返回 token + refresh_token + 当前工作空间
- OIDC 单点登录：由 IdP 策略控制
- 桌面应用：免注册，启动即自动创建本地账号
- API 访问：使用 API Key（`X-API-Key` 请求头）

**空间与平台权限：**
- 空间 Owner 管理所在空间的成员、模型和知识库
- 全局系统设置、平台任务队列及跨空间审计需系统管理员身份，两类权限独立授予
- 首次设置系统管理员：先注册账号，再配置 `WEKNORA_BOOTSTRAP_SYSTEM_ADMIN_EMAIL=<该账号邮箱>` 并重启

### 3.2 知识库管理

**创建知识库并导入资料：**
1. 在「知识库」页点「新建」，填名称，选类型：`document`（普通文档库）或 `faq`（问答对库）
2. 在初始化向导里选模型（对话模型 LLM、向量模型 Embedding，可选 Rerank/VLM/ASR/知识图谱/问题生成）
3. 用「测试」按钮确认模型连接正常后保存
4. 进入知识库，拖入文件或粘贴网页 URL
5. 在上传确认对话框中设置标签和解析选项

> **注意**：向量存储创建后不可更改，应在建库前确定。更换向量模型需要重建索引。

**管理操作入口：**

| 操作 | 界面入口 |
|------|---------|
| 建库、改分块大小与索引开关 | 知识库编辑弹窗的「分块」「索引策略」页签 |
| 上传文件、导入网页或编写 Markdown | 文档列表页的上传区，或「新建」下拉 |
| 调整文档列表顺序 | 文档列表工具栏的「排序」 |
| 查看解析进度或排查卡住的文档 | 文档卡片上的状态，或打开解析时间线 |
| 用文件夹整理文档 | 文档列表左侧的文件夹树；上传整个目录保留结构 |
| 给文档打标签 | 单篇在详情里改；多篇勾选后批量操作 |
| 检查解析结果、改错字 | 打开文档 → 分块列表 → 直接编辑分块 |
| 查看操作记录 | 知识库设置 → 活动 |
| 复制知识库或跨库移动文档 | 知识库列表的复制，或文档批量操作里的移动 |
| 批量下载原始文件 | 勾选文档后，批量操作栏的「批量下载」 |

**查看解析进度：**
- 文档状态依次：`pending` → `processing` → `finalizing` → `completed`
- 超过 20 分钟无进展，状态变为「排队中」或「疑似卡住」
- 解析时间线按阶段展示耗时与结果，失败时顶部错误卡片说明原因并提供重试入口

**浏览画廊：**
- 文档知识库的「画廊」页签汇总从文档提取的图片，瀑布流持续加载
- 可搜索图片描述和 OCR 文字，按图片属性、来源文档筛选
- 点击图片查看大图、描述、OCR 与来源

**整理文件夹与标签：**
- 文件夹：按目录归档，一篇文档只属于一个文件夹；上传整个目录保留层级结构
- 标签：交叉分类，一篇文档可关联多个标签；按多标签筛选时匹配任一即可
- 自动标签：解析完成时从已有候选标签中选择，默认每篇最多 3 个

**编辑分块与补充元数据：**
- 在文档详情中编辑文本分块，可修正解析错误并重建索引
- 每次编辑或回滚生成新版本；其他用户已更新同一分块时提示刷新重试
- 自定义元数据补充部门、密级等信息，最多 20 项

**批量下载原始文件：**
- 勾选文档后点击「批量下载」，打包为 ZIP 并保留文件夹结构
- 每批最多 200 个文档、原始文件合计不超过 512 MiB
- 需要 Contributor 及以上且对知识库有编辑权限

### 3.3 文档解析

**支持的格式：**

| 类别 | 格式 |
|------|------|
| 文档 | PDF、Word（doc/docx）、PPT（ppt/pptx）、Excel（xls/xlsx）、EPUB、XMind |
| 文本 | txt、Markdown、CSV、JSON |
| 网页 | 在线 URL 抓取、本地 HTML / MHTML 归档 |
| 图片 | jpg、png、gif、bmp、tiff、webp（需配置视觉模型） |
| 音频 | mp3、wav、m4a、flac、ogg（需配置语音识别模型） |

**解析结果不理想时的调整：**

| 现象 | 建议 |
|------|------|
| PDF 版式还原差、表格错位 | 在知识库解析设置里为 pdf 指定其他解析引擎（MarkItDown / OpenDataLoader / MinerU） |
| 扫描件没识别出文字 | 确认已配置视觉模型，必要时强制走扫描件模式 |
| Excel 首行是列名却被当成数据 | 为 xlsx/xls 打开「首行作为表头」 |
| 分块内容需要修正 | 在分块列表中编辑正文 |

### 3.4 分块机制

**分块参数：**

| 参数 | 默认值 | 说明 |
|------|--------|------|
| chunk_size | 512（字符） | 单块目标大小 |
| chunk_overlap | 80（约 15%） | 相邻块重叠字符数 |
| separators | ["\n\n", "\n", "。"] | 递归分块分隔符优先级 |
| strategy | auto（自适应） | auto / heading / heuristic / recursive / legacy |
| enable_parent_child | false | 启用父子分块（子块检索、父块回答） |
| parent_chunk_size | 4096 | 父块大小（父子模式） |
| child_chunk_size | 384 | 子块大小（父子模式） |

**调优建议：**

| 遇到的情况 | 建议 |
|-----------|------|
| 回答缺上下文、信息不完整 | 调大 chunk_size，或开启父子分块 |
| 检索命中的块跟问题关系不大 | 调小 chunk_size，让每块主题更集中 |
| 资料是条目式的（FAQ、字典、参数表） | 重叠设为 0 |
| 资料是长篇叙述（报告、论文） | 重叠调到 150–200 |
| 精确检索 + 长上下文 | 开启父子分块，parent 4096 / child 384 |

> 可用 `POST /api/v1/chunker/preview` 预览分块结果，不写入数据库。修改分块配置后，已有文档需重新解析。

### 3.5 检索引擎

**混合检索流程：** 向量检索 + 关键词（BM25）检索 → RRF 加权融合 → Rerank 重排

**调整混合检索：**
- RRF 使用各路结果的排名融合向量与关键词检索，可调整平滑参数及两路权重
- 建议用同一组有代表性的问题比较结果再决定是否保存
- 只有一路结果时不执行双路 RRF

**向量数据库选项（RETRIEVE_DRIVER）：**

| 引擎 | 适用场景 |
|------|---------|
| PostgreSQL（ParadeDB） | 默认选择，与业务同库 |
| SQLite | 桌面版/开发/微型部署 |
| Elasticsearch v8 | 已有 ES 8 集群 |
| OpenSearch | 需审计/别名/reindex 的生产方案 |
| Qdrant | 纯向量为主、需 payload 过滤 |
| Milvus | 大规模向量、需原生 BM25 混检 |
| Weaviate | GraphQL 生态 |
| Doris | 已有 Doris 数仓 |
| 腾讯云 VectorDB | 腾讯云托管 |

> 切换引擎需重建索引。知识库绑定的向量存储创建后不可修改。

**知识图谱增强（GraphRAG）：**
- 在文档入库时提取实体与关系（Neo4j 存储）
- 问答时沿关联关系检索更多相关片段
- 适用于人物、组织、产品或条款之间关系较多的资料
- 开启需两级开关：全局 `NEO4J_ENABLE=true` + 知识库 `IndexingStrategy.GraphEnabled`

### 3.6 模型管理

**模型类型：**

| 类型 | 用途 |
|------|------|
| 对话模型（LLM） | 生成问答、摘要和智能推理内容 |
| 向量模型（Embedding） | 将文档与问题转换为向量，支持语义检索 |
| 重排模型（Rerank） | 对召回片段重新排序 |
| 视觉模型（VLM） | 识别文档或对话中的图片 |
| 语音模型（ASR） | 将音频转写为文本 |

**添加与验证连接：**
1. 在「设置 → 模型」选类型和来源：「API」接入远程服务，「Ollama」使用本地模型
2. 选择服务商（列表只显示支持当前模型类型的厂商）
3. 填写模型名称（可从厂商内置目录选择）
4. 填写 Base URL 与 API Key
5. 核对「实际调用方式」面板
6. 测试连接后保存

**内置厂商（29 家）：** OpenAI、Azure OpenAI、Anthropic、DeepSeek、Qwen（阿里云）、智谱、混元、豆包（火山引擎）、Gemini、MiniMax、NVIDIA、SiliconFlow、OpenRouter、LiteLLM、Ollama 等

**关键注意事项：**
- 更换向量模型需要重建索引
- 保存前测试连接
- 本地 Ollama 和远程模型可组合使用（如本地模型生成向量、远程模型生成回答）
- 后台并发上限限制文档入库等后台任务的并发数，不影响交互式对话

### 3.7 Agent 引擎

**两种模式对比：**

| 模式 | 适用任务 | 执行特点 |
|------|---------|---------|
| 快速问答（quick-answer） | 基于文档的事实查询 | 检索后生成回答，调用次数较少 |
| 智能推理（smart-reasoning） | 跨文档分析、联网查询或工具操作 | 可能执行多轮调用，耗时与用量取决于任务 |

**创建与使用智能体：**
1. 在「智能体」页新建，选择快速问答或智能推理模式
2. 选择模型、知识库范围和提示词（类型预设会预填配置，保存前可调整）
3. 根据任务启用联网搜索或选择 MCP 工具；运行技能脚本需绑定已安装技能的沙箱
4. 保存后在对话页选择该智能体，完成一次提问，检查回答来源与工具结果

**内置智能体：**
- 快速问答：文档查询
- 数据分析智能体：面向 CSV 和 Excel
- Wiki 智能体：浏览和维护 Wiki 内容

**智能体类型预设：**

| 预设 | 适用场景 | 预填工具 |
|------|---------|---------|
| rag-qa | 文档问答 | search_knowledge、read_document、list_documents |
| wiki-qa | Wiki 研究 | wiki_search、wiki_read_page、read_document |
| hybrid-rag-wiki | 混合文档+Wiki | wiki_search、search_knowledge、read_document 等 |
| data-analysis | 数据分析 | data_schema、data_analysis（限定 csv/xlsx） |
| custom | 自定义 | 不预填 |

**处理工具审批与授权：**
- 需要人工审批的 MCP 工具在执行前显示审批卡片，可批准、拒绝或修改参数
- 默认等待上限 10 分钟；拒绝、超时或取消作为工具结果返回
- MCP 服务需要 OAuth 授权时，可在当前对话中完成授权

**使用技能、附件和记忆：**
- 智能推理无需沙箱即可读取会话附件；绑定沙箱后可运行脚本并生成文件
- 可下载产物写入 `/workspace/output`，回答完成后可预览和下载
- 每轮回答结束后为 `/workspace` 记录 git 检查点，分叉和回滚会话时据此恢复
- 长期记忆按空间和调用者隔离，智能体可单独关闭记忆读写

### 3.8 MCP 集成

**两种角色：**
- **WeKnora 作为 MCP 客户端**：在「工具箱 → MCP服务」接入外部 MCP server，工具供 Agent 调用
- **WeKnora 作为 MCP Server**：在「设置 → 发布集成 → MCP Server」创建端点，供外部客户端调用

**接入外部工具：**
1. 空间 Admin 在「工具箱 → MCP服务」新建服务
2. 填写名称、服务 URL，选择 SSE 或 Streamable HTTP 传输
3. 配置认证（无/自定义 Header、API Key/Token、OAuth 2.0）
4. 连接并拉取 Tools，填写「使用说明」
5. 逐个设置「启用工具」和「调用需审批」

**认证方式：** API Key / Bearer / OAuth 2.0（含动态客户端注册与 PKCE）

**供外部客户端调用：**
1. 在「设置 → 发布集成 → MCP Server」新建端点
2. 填写名称、选择可访问的知识库、勾选要暴露的工具
3. 按需指定 ask 使用的默认 Agent 和每分钟调用上限（默认 60 次）
4. 创建后一次性展示令牌和地址 `/mcp/<endpoint_id>`
5. 页面给出 Cursor / VS Code / Claude Code 的客户端配置

**端点暴露的工具按四组勾选（默认只开只读工具）：**

| 组 | 工具 |
|----|------|
| 检索与阅读 | list_knowledge_bases、search_knowledge、grep_chunks、list_documents、read_document |
| 问答 | ask |
| Wiki | wiki_search、wiki_read_page 等 |
| 写入与管理 | create_knowledge_from_file 等（按需开启） |

### 3.9 知识图谱

**说明：** 在文档入库时提取实体与关系（Neo4j 存储），问答时沿关联关系检索更多相关片段，可与向量和关键词检索共同使用。

**适用场景：** 人物、组织、产品或条款之间关系较多的资料。

**开启配置（两级开关）：**
1. 全局：`NEO4J_ENABLE=true`（配合 Neo4j 连接配置）
2. 知识库级：`IndexingStrategy.GraphEnabled` + `ExtractConfig`（含 few-shot 示例）

**配置向导辅助：**
- `POST /initialization/extract/text-relation`：对文本试跑关系抽取，预览效果
- `POST /initialization/extract/fabri-text` / `fabri-tag`：让 LLM 生成示例文本/推荐标签

### 3.10 数据源导入

**说明：** 将飞书、Notion、Confluence、语雀等平台内容持续同步到知识库。

**建立连接并同步：**
1. 以空间管理员身份打开目标知识库的「数据源」设置
2. 选择连接器，填写凭据并测试连接，确认能列出所需资源
3. 选择同步范围与周期，保存后发起首次同步
4. 查看同步状态与日志

**支持的数据源：**

| 连接器 | 类型标识 | 同步对象 |
|--------|---------|---------|
| 飞书 / Lark 知识库 | feishu / lark | Wiki 空间与节点 |
| 飞书云盘 / Lark Drive | feishu_drive / lark_drive | 指定云盘文件夹 |
| Notion | notion | 页面与数据库 |
| Confluence | confluence | Server/DC 或 Cloud 空间页面 |
| 语雀 | yuque | 知识库文档 |
| 钉钉文档 | dingtalk | 知识库、文件夹与在线文档 |
| 腾讯 IMA | ima | 知识库中的文件与笔记 |
| GitLab | gitlab | 仓库指定分支/标签下的目录 |
| Seafile | seafile | 资料库中的目录与文件 |
| RSS / Atom | rss | 订阅源文章 |

**同步计划：** `sync_schedule` 使用六段 cron（含秒），如 `0 0 */6 * * *` 表示每六小时触发；空字符串表示仅手动同步。

**同步模式：** incremental（增量）/ full（全量）。首次同步获取完整内容，后续按连接器游标增量更新。

### 3.11 网络搜索与网页抓取

**说明：** 网络搜索用于补充知识库之外的信息。智能体通过 `web_search` 查找结果，再通过 `web_fetch` 读取网页正文。

**配置：** 在「设置 → 网络搜索」选择提供商、填写凭据并测试连接，然后在智能体中选择该搜索配置。

**支持的搜索引擎（14 个）：**

| 引擎 | 是否需要 API Key | 备注 |
|------|-----------------|------|
| DuckDuckGo | 否 | 免费；可配 proxy_url |
| Google | 是（还需 engine_id） | Google Custom Search API |
| Bing | 是 | — |
| Tavily | 是 | — |
| SearXNG | 否 | 自托管实例，唯一允许自定义地址 |
| 智谱搜索 | 是 | 默认引擎 search_std |
| 秘塔 Metaso | 是 | scope 选择资源范围 |
| Exa | 是 | 可用 include_text 获取正文 |
| 博查 Bocha | 是 | freshness、summary |
| Brave Search | 是 | 支持按次传 country/freshness |
| Serply | 是 | Google 结果 |
| 百度千帆 AI 搜索 | 是 | — |
| Ollama Web Search | 是 | 最多 10 条结果 |
| Keenable | 可选 | 无 Key 走公共限速端点 |

### 3.12 IM 集成

**说明：** 将智能体接入企业微信、飞书、钉钉、Slack、Telegram 等聊天平台。用户可在平台中向机器人提问。

**接入步骤：**
1. 在「设置 → IM 集成」新建渠道
2. 选择平台、填写应用凭据
3. 绑定智能体后启用
4. Webhook 模式需在平台后台填写回调地址；长连接模式无需公网回调地址

**支持的平台（10 个）：**

| 平台 | 接入模式 | 流式回复 | 文件下载 |
|------|---------|---------|---------|
| 企业微信 | websocket（长连接）/ webhook | 仅 websocket | 两种均支持 |
| 飞书 / Lark | websocket / webhook | 是（流式卡片） | 是 |
| Slack | websocket（Socket Mode）/ webhook | 是 | 是 |
| Telegram | websocket（长轮询）/ webhook | 是（消息编辑） | 是 |
| 钉钉 | websocket（Stream 模式） | 是（AI 卡片） | 是 |
| Mattermost | webhook | 是 | 是 |
| 微信（iLink） | longpoll | 否 | 是 |
| QQ 机器人 | websocket | 否 | 否 |
| 云之家 | webhook / websocket | 否 | 是 |

**内置命令：**

| 命令 | 功能 |
|------|------|
| /help [命令名] | 列出全部可用指令，或查看某条指令详细用法 |
| /info | 展示当前绑定 Agent 信息与能力 |
| /search <关键词> | 直接对知识库做混合检索，返回原文片段（不经 AI 总结） |
| /stop | 中止当前正在进行的回答 |
| /clear | 清空对话记忆 |

### 3.13 网页嵌入

**说明：** 在官网或帮助中心提供知识库问答挂件。访客无需 WeKnora 账号即可对话。

**创建嵌入渠道：**
1. 在「设置 → 网页嵌入」新建渠道
2. 绑定智能体
3. 设置允许嵌入的域名
4. 复制接入代码

**三种接入方式：**

| 方式 | 说明 |
|------|------|
| 静态 Token 模式 | token 对访客可见，适合内部站点或低敏感场景 |
| 安全模式（推荐） | publish token 只保存在业务后端，页面通过换取接口获取短效 token |
| 编程式 API | 通过 `WeKnora.init()` 编程初始化 |

**安全要点：**
- 域名白名单：`allowed_origins` 为空时拒绝所有请求；支持 `*.example.com` 子域名通配
- 双 token 体系：安全模式下浏览器只持有 30 分钟短效 `ems_` token
- 三层限流：单 IP/分钟、渠道/分钟、渠道/天

### 3.14 Wiki 能力

**说明：** 将知识库资料整理为相互链接的 Markdown 页面。文档入库后，模型提取人物、产品和概念等条目，生成带来源引用的页面。

**开启并浏览 Wiki：**
1. 编辑知识库 → 「索引策略」里打开 Wiki
2. 上传文档（已有文档也会被纳入，无需重传）
3. 等待生成（异步，文档多时持续一段时间，面包屑有「索引中」提示）
4. 完成后进入知识库的 Wiki 页签浏览，图谱页签查看条目链接关系

**抽取粒度：**

| 粒度 | 行为 |
|------|------|
| focused | 仅 3-7 个主要主题 |
| standard（默认） | 主题 + 被实质性讨论的实体概念 |
| exhaustive | 穷举所有命名事物与公认概念 |

**编辑和回滚页面：**
- 在 Wiki 页面中编辑正文后，可查看版本历史并比较改动
- 历史记录区分：自动生成、智能体、人工编辑、回滚
- 回滚以所选历史内容创建新版本，版本号继续递增
- 软上限 50 版：清理自动生成的旧版本；硬上限 200 版：不分作者一律裁剪

**浏览 Wiki 图谱：**
- 图谱按页面关联组织分组布局，展示概括组内内容的主题说明
- 点击分组主题聚焦该组页面，通过「返回全图」或 Esc 退出聚焦
- 可隐藏无关联页面，通过搜索与页面类型筛选定位条目

### 3.15 权限与安全

**成员角色：**

| 角色 | 权限 |
|------|------|
| Owner | 完全控制：删除空间、转移所有权、管理 API Key、成员 |
| Admin | 管理成员、模型、向量库、MCP、IM 等空间基础设施 |
| Contributor | 创建知识库/Agent，编辑自己创建的资源 |
| Viewer | 只读，可浏览和提问 |

**邀请成员与分配角色：**
- 在空间设置的「成员」中邀请用户，分配角色
- 公开注册关闭时，可通过有效邀请完成注册
- 已有用户可接受邀请加入新空间，无需创建第二个账号

**共享知识库与智能体：**
1. 让来源空间和接收空间加入同一组织
2. 由有权限的成员将知识库或智能体共享到该组织
3. 接收方权限受共享记录和成员角色共同限制

**为程序配置 API Key：**
- 在空间设置中创建 API Key，按任务选择能力（检索/问答/入库/管理）
- 需限定资料范围时，指定可访问的知识库
- 程序通过 `X-API-Key` 请求头携带凭据

**执行权限与审批（v0.9.0）：**
- 三档权限：只读、修改前确认、自动执行
- 读取、写入和破坏性操作受审批控制
- 资源权限不会因为协作或授权而扩大

### 3.16 本机浏览器

**说明：** 通过 BrowserSkill 扩展将用户电脑上的浏览器接入智能推理对话。支持 Chrome 和 Microsoft Edge（Chromium 125 及以上）。

**安装扩展（需 0.3.1 及以上）：**
- Chrome：Chrome 应用商店
- Edge：Edge 加载项
- 备用：在「浏览器连接」页下载配套 ZIP，开发者模式加载已解压的扩展程序

**配对与使用：**
1. 打开侧边栏「工具箱 → 浏览器连接」
2. 复制一次性配对链接，在扩展「连接设置 → 远程连接」粘贴并保存
3. 在智能推理输入框开启「本机浏览器」
4. 提交任务；首次调用创建独立任务窗口

**任务管理：**
- 对话预览可定位页面、暂停、继续或结束当前浏览器任务
- 连接状态显示在「浏览器连接」标签上（已连接/离线/未配对）
- 配对链接五分钟有效；设备令牌有效期 90 天，30 天后自动轮换

**人工参与：**
- 登录、验证码或授权步骤由 `request_help` 发起
- 按预览提示进入浏览器完成，在帮助提示中确认
- 帮助等待最多五分钟，超时或取消保留现场并暂停

---

## 4. 界面字段说明

### 4.1 知识库创建表单

| 字段 | 类型 | 说明 |
|------|------|------|
| 名称 | 文本 | 知识库名称 |
| 类型 | 选择 | document（文档库）/ faq（问答对库） |
| 描述 | 文本 | 知识库描述（可选） |

### 4.2 初始化向导模型配置

| 字段 | 说明 |
|------|------|
| 对话模型（LLM） | 生成回答；必选 |
| 向量模型（Embedding） | 将文档转换为向量；必选；更换后需重建索引 |
| 重排 Rerank | 对召回片段重新排序；可选 |
| 图片理解 VLM | 识别文档中的图片；可选 |
| 语音转写 ASR | 将音频转写为文本；可选 |
| 知识图谱抽取 | 提取实体与关系；可选 |
| 问题生成 | 预生成问题；可选 |

### 4.3 分块配置

| 字段 | 默认值 | 说明 |
|------|--------|------|
| chunk_size | 512 | 单块目标大小（字符），范围 100–10000 |
| chunk_overlap | 80 | 相邻块重叠字符数，超过 chunk_size/2 会被钳制 |
| separators | ["\n\n","\n","。"] | 分隔符优先级 |
| strategy | auto | auto/heading/heuristic/recursive/legacy |
| enable_parent_child | false | 父子分块开关 |
| parent_chunk_size | 4096 | 父块大小 |
| child_chunk_size | 384 | 子块大小 |

### 4.4 检索配置

| 参数 | 说明 |
|------|------|
| vector_threshold | 向量检索阈值 |
| keyword_threshold | 关键词检索阈值（默认 0.5） |
| 候选数量 | 召回候选数 |
| RRF K | 平滑参数 |
| vectorWeight / keywordWeight | 两路权重（默认 0.7/0.3） |
| rerank.threshold | 重排阈值（默认 0.2） |

### 4.5 智能体配置

| 字段 | 说明 |
|------|------|
| agent_mode | quick-answer / smart-reasoning |
| agent_type | 智能推理下的预设类别 |
| model_id | 使用的模型 |
| 知识库范围 | 全部/指定/禁用 |
| system_prompt | 系统提示词 |
| reasoning_effort | 思考强度（可在对话时临时调整） |
| 联网搜索 | 开关 |
| MCP 工具 | 选择 MCP 服务 |
| 技能 | 绑定已安装技能的沙箱 |

### 4.6 API 认证请求头

| 方式 | 请求头 | 适用 |
|------|--------|------|
| JWT | `Authorization: Bearer <token>` | 浏览器/交互式调用 |
| API Key | `X-API-Key: <key>` | 服务端集成 |
| 指定空间 | `X-Tenant-ID: <id>` | 多空间用户切换 |

### 4.7 API Key 能力

| 能力 | 说明 |
|------|------|
| retrieve | 检索 |
| chat | 问答 |
| ingest | 入库 |
| manage_kbs | 管理知识库 |
| read_agents | 读取智能体 |
| manage_agents | 管理智能体 |
| manage_models | 管理模型 |
| manage_mcp_services | 管理 MCP 服务 |
| manage_datasources | 管理数据源 |
| manage_channels | 管理渠道 |

---

## 5. 使用示例

### 5.1 首次完整流程（Web 界面）

1. 注册并登录（http://localhost）
2. 在「知识库」页新建知识库，选 document 类型
3. 在初始化向导选对话模型和向量模型，测试连接后保存
4. 进入知识库，拖入 PDF/Word 文件，等待解析 completed
5. 进入对话页选择知识库，提问
6. 查看回答与可点击的引用来源

### 5.2 通过 API 完成首次问答

```bash
BASE=http://localhost:8080/api/v1

# 1) 注册
curl -s -X POST $BASE/auth/register -H "Content-Type: application/json" \
  -d '{"username":"admin","email":"admin@example.com","password":"pass123456"}'

# 2) 登录，保存 JWT
LOGIN_RESPONSE=$(curl -s -X POST $BASE/auth/login -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"pass123456"}')
TOKEN=$(printf '%s\n' "$LOGIN_RESPONSE" | jq -r '.token')
AUTH="Authorization: Bearer $TOKEN"

# 3) 创建知识库
KB_ID=$(curl -s -X POST $BASE/knowledge-bases -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"name":"我的知识库","type":"document"}' | jq -r '.data.id')

# 4) 初始化模型（以本地 Ollama 为例）
curl -s -X POST $BASE/initialization/initialize/$KB_ID -H "$AUTH" -H "Content-Type: application/json" -d '{
  "llm":{"source":"local","modelName":"qwen3:8b"},
  "embedding":{"source":"local","modelName":"bge-m3","dimension":1024},
  "rerank":{"enabled":false}}'

# 5) 上传文档
curl -s -X POST $BASE/knowledge-bases/$KB_ID/knowledge/file -H "$AUTH" -F "file=@./demo.pdf"

# 6) 创建会话
SESSION_ID=$(curl -s -X POST $BASE/sessions -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"title":"第一次对话"}' | jq -r '.data.id')

# 7) 知识问答（SSE 流式）
curl -N -X POST $BASE/knowledge-chat/$SESSION_ID -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"query":"这份文档讲了什么？","knowledge_base_ids":["'$KB_ID'"]}'

# 7b) Agent 对话（同为 SSE）
curl -N -X POST $BASE/agent-chat/$SESSION_ID -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"query":"总结文档要点","agent_enabled":true,"agent_id":"builtin-smart-reasoning","knowledge_base_ids":["'$KB_ID'"]}'
```

### 5.3 创建 API Key 用于服务端集成

```bash
# 以空间 Owner 身份创建 API Key
curl -s -X POST $BASE/tenants/$TENANT_ID/api-keys -H "$AUTH" -H "Content-Type: application/json" \
  -d '{"name":"ci-bot","full_access":true}'

# 之后所有请求改用：
curl -s $BASE/knowledge-bases -H "X-API-Key: <创建时返回的 key>"
```

### 5.4 智能推理处理多步骤任务

1. 在「智能体」页新建，选 smart-reasoning 模式
2. 选择模型，限定知识库范围
3. 启用联网搜索（如需）或选择 MCP 工具
4. 保存后在对话页选择该智能体
5. 提问如「比较这两份合同的付款条款差异」

### 5.5 连接飞书数据源

1. 打开目标知识库的「数据源」设置
2. 选 feishu 连接器，填 app_id + app_secret，测试连接
3. 选择要同步的 Wiki 空间节点
4. 设置同步周期（如每 6 小时）
5. 保存后发起首次同步

### 5.6 接入企业微信机器人

1. 在「设置 → IM 集成」新建渠道
2. 选 wecom 平台，选 websocket 模式
3. 填 bot_id、bot_secret、ws_endpoint
4. 绑定智能体
5. 启用后在企业微信群 @机器人提问

---

## 6. 常见使用问题（业务层面）

### 6.1 文档与解析

| 现象 | 检查点与解决 |
|------|------------|
| 上传后一直 processing | 查看文档解析时间线；大文件受 MAX_FILE_SIZE_MB(默认50) 与处理超时(默认2h)约束；PDF 扫描件、大文件会慢一些 |
| 解析状态「疑似卡住」 | 打开解析时间线查看停在哪个阶段，或停止解析后重试；长时间无进展会被标记为失败(TASK_STALLED) |
| PDF 版式还原差、表格错位 | 在知识库解析设置里为 pdf 指定其他解析引擎（MarkItDown/OpenDataLoader/MinerU） |
| 扫描件没识别出文字 | 确认已配置视觉模型(VLM)，必要时强制走扫描件模式 |
| Excel 首行列名被当成数据 | 为 xlsx/xls 打开「首行作为表头」 |
| 图片在本机显示，其他设备打不开 | 检查返回地址是否含 localhost 或不可访问的对象存储地址 |

### 6.2 检索与问答

| 现象 | 检查点与解决 |
|------|------------|
| 问答无引用/召回为空 | 确认知识解析 completed；调低 vector_threshold；检查 embedding 模型与建库时一致 |
| 回答缺上下文、信息不完整 | 调大 chunk_size，或开启父子分块（子块检索、父块回答） |
| 检索命中的块跟问题关系不大 | 调小 chunk_size，让每块主题更集中 |
| rerank 返回 all_below_threshold | 模型认为没有候选相关；换说法重新提问，或调低 rerank.threshold |
| 修改分块配置后已有文档不生效 | 已有文档需重新解析才能使用新配置 |

### 6.3 模型与连接

| 现象 | 检查点与解决 |
|------|------------|
| 初始化时 Ollama 检测失败 | 容器内默认地址 http://host.docker.internal:11434；Linux 需确认 extra_hosts 配置 |
| Agent 提示模型未就绪 | 确认智能体引用的模型仍存在且配置完整，执行模型连通性测试 |
| 更换向量模型后检索异常 | 更换向量模型需要重建索引；新旧向量不能混用 |
| 私网模型/向量库连接被拒绝 | 检查 SSRF 校验和端口策略；按配置放行需要的目标 |

### 6.4 账号与权限

| 现象 | 检查点与解决 |
|------|------------|
| 注册页签消失 | 查 GET /auth/config 的 registration_mode；值可能来自「设置 → 系统」数据库设置 |
| 升级后提示权限不足 | 核对当前空间角色、资源归属与 API Key 能力范围；平台管理员与空间 Owner 不是同一个概念 |
| API Key 请求 403 | Key 的 capabilities 不含所需能力，或知识库白名单未包含目标库 |
| 通过组织共享的知识库无编辑入口 | Viewer 权限访问的知识库不显示上传、编辑、删除和设置入口 |

### 6.5 智能体与工具

| 现象 | 检查点与解决 |
|------|------------|
| 技能已加入目录却不可执行 | 目录收录和沙箱安装是两步；检查安装记录、智能体的沙箱选择与技能范围 |
| 本机浏览器已配对但没有执行网页任务 | 智能推理输入框需要开启本机浏览器；暂停的任务需显式继续 |
| MCP 工具需要审批时卡住 | 默认等待上限 10 分钟；拒绝、超时或取消会作为工具结果返回 |
| 报错提示「仅允许白名单出站」 | 部署开启了 SSRF_DNS_WHITELIST_ONLY，把目标主机加入白名单 |

### 6.6 IM 与嵌入

| 现象 | 检查点与解决 |
|------|------------|
| 升级后钉钉机器人不再回复 | v0.8.2 起钉钉只支持 Stream 模式；需在钉钉开发者后台开启 Stream |
| 嵌入页面加载失败或返回 403 | 白名单填写实际宿主 Origin；检查 CSP、反向代理和安全模式 exchange 的 Origin |
| 飞书应用测试成功但加载不到文件夹 | 连接测试只验证应用身份，文件夹还需授权 |
| 登录接口返回 HTML 404 | 检查 SEARXNG_PORT 是否与 APP_PORT(默认8080)相同 |

### 6.7 升级相关

| 注意事项 | 说明 |
|---------|------|
| 升级前先 docker compose pull | 避免复用缓存镜像导致版本不一致 |
| 嵌入会话签名密钥 | v0.8.2 更换了签名算法，升级前签发的嵌入会话全部失效；配置 SYSTEM_SIGNING_KEY |
| 钉钉 Stream 模式 | 升级迁移会把 webhook 渠道改为 websocket，需在钉钉后台开启 Stream |
| 数据库迁移 | 升级需核对迁移；失败后不要假定已完整回滚 |
| Local 沙箱已移除 | 重新配置 Docker、CubeSandbox 或 E2B |

---

## 附录：API 分组导航

| 分组 | 主要前缀 |
|------|---------|
| 认证与用户 | /auth、/me/invitations |
| 租户（空间）与成员 | /tenants |
| 组织与共享 | /organizations、/shared-* |
| 知识库与知识 | /knowledge-bases、/knowledge |
| 分块与标签 | /chunks、/chunker/preview |
| FAQ 与 Wiki | /faq、/wiki-search |
| 会话、消息与聊天 | /sessions、/knowledge-chat、/agent-chat、/knowledge-search |
| 模型与初始化 | /models、/initialization |
| 系统与平台管理 | /system、/system/admin |
| 基础设施与数据源 | /vector-stores、/storage-backends、/web-search-providers、/datasource |
| Agent 与 MCP | /agents、/mcp-services |
| 内置 MCP Server | /mcp-endpoints、/mcp/:endpoint_id |
| 本机浏览器 | /me/browser、/local-browser |
| IM、Embed 与文件服务 | /im、/im-channels、/embed-channels、/embed、/files |

**限流说明：**
- 公开分享链接接口：每 IP 30 次/分钟
- Embed 公开路由：每(channel,IP) 30次/分钟（默认）；channel 级 600次/分钟；channel 级 10000次/天
- 其余业务接口无全局限流

---

> 📄 原始抓取素材：`readme-parse/WeKnora-user-capture.json`
> 📄 任务报告：`output/WeKnora-report.md`
> 📄 任务日志：`output/task-log.md`
