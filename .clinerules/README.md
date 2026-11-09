# .clinerules — Cline 自动加载规则（兼容入口）

> 本工程已重构为三中心智能体架构（2026-11-09）。全局规则细化为按中心加载，此处仅保留索引，
> 控制 Cline 启动上下文体积。请按任务所属中心按需读取。

## 规则与文档索引

| 需求 | 读取 |
|---|---|
| 工程设计与契约（5 契约/信封协议/能力映射/运行降级/安全确认） | docs/01 ~ docs/05 |
| 三中心定义与共同纪律 | config/centers.yaml · agents/README.md |
| 开发中心（act+GLM：拉取/构建/二开/打包/插件上架/Git） | agents/engineering/README.md |
| 数策中心（deepseek：抓表入库/统计分析） | agents/data/README.md |
| 方案中心（plan+doubao：说明书/方案/论文） | agents/solution/README.md |
| 能力模块接口（llm/memory/assets/tools/trace/scrape/vcs/runtime/mailbox） | capabilities/*/README.md |
| 插件体系（清单规范/授权矩阵） | plugins/README.md · plugins/policy.yaml |
| **MCP/插件/skills 安装登记纪律（安装即双写 init 资产）** | **.clinerules/agent_init_rules.md · agents/init/** |
| 三中心门户（常驻 :8765 / 五视图 / 服务直控 / 配置编辑） | plugins/IndexPage/README.md |

## 联邦遗产

Mem0/OpenViking/WeKnora 相关规则与脚本已归档 `archive/`，第一阶段不使用（docs/01-底座能力映射.md）。
