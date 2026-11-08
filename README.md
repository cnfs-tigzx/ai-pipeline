# ai-three-center（原地重构自 ai-pipeline）

三中心智能体工程：开发中心 · 数策中心 · 方案中心。
第一阶段**零第三方组件**：全部能力以仓库内目录与文件实现，零容器、零端口、零 pip 安装、零数据库服务（docs/04）。

## 三中心速览

| 中心 | 内核 | 模型（火山方舟） | 职责 |
|---|---|---|---|
| 开发 engineering | Cline act | GLM 系列 | GitHub 拉取/编译/二次开发/打包插件 → 上架 Plugin Hub → 安装到三中心 |
| 数策 data | Cline | deepseek 系列 | 网页/Excel → 二维表 → SQLite；统计分析与决策支持；信封供数 |
| 方案 solution | Cline plan | doubao 系列 | 资料库（L0/L1/full）；产品方案与论文；大纲卡点 → 成文 |

中心间只走文件信封 `data/mailbox/<from>_<to>/`（可回放、可审计、离线可用）。

## 目录导航

| 目录 | 内容 |
|---|---|
| docs/ | 设计与契约：01 能力映射 · 02 目录规范 · 03 接口契约 · 04 运行降级 · 05 安全确认 |
| config/ | models.yaml（模型路由）· centers.yaml（三中心定义）· runtime.yaml · tools.registry.json |
| capabilities/ | 十个能力模块（llm/memory/assets/tools/trace/scrape/vcs/runtime/db/mailbox）+ _yamlmini + selftest |
| orchestration/ | runner.py（DAG/断点/卡点/重试）+ flows/（三条示例流程） |
| agents/ | 三中心本体：README + rules/ + workflows/（Cline 加载执行） |
| plugins/ | Plugin Hub：README（清单规范/生命周期）· policy.yaml（授权矩阵）· manifests/ · packages/ |
| plugins-registry.html | 插件列表页（纯静态，gen-registry.py 刷新） |
| data/ db/ repos/ | 运行期落盘 / SQLite / 下游工作区（均 gitignored） |
| archive/ | 联邦遗产（Mem0/OpenViking/WeKnora 规则与脚本）与历史评估 |
| scripts/ | git-push.sh · pipeline.sh · deploy-check.sh · one-key.sh · rebuild-deploy.sh · preflight-check.sh · gen-registry.py |
| .clinerules/ | Cline 兼容入口（仅索引，按需加载各中心规则） |

## 快速开始

```
python3 capabilities/selftest.py --skip-llm     # 能力自测（无网络）
python3 capabilities/selftest.py                # 含方舟真实调用
python3 orchestration/runner.py run orchestration/flows/data-table-import.flow.yaml
python3 scripts/gen-registry.py --html          # 刷新工具注册表与插件列表页
./scripts/git-push.sh sync                      # Git 同步（见 agents/engineering/rules/git-sync-rule.md）
```

## 敏感信息管理（本地保留，严禁上传）

| 本地文件 | 内容 |
|---|---|
| `火山方舟模型API` | 火山引擎 Ark API Key、GLM / Doubao-embedding 接入点 ID |
| `local-secrets.md` | 历史联邦凭据（Mem0 / WeKnora / MCP 数据库 Key，第一阶段停用） |

均已在 `.gitignore`，`capabilities/llm` 只从 `ARK_API_KEY` 环境变量或密钥文件读取，禁止出现在任何被推送文件与日志中。

## 演进路线

- 第二阶段起：doubao/deepseek 接入点补齐（config/models.yaml）→ cline CLI headless 评估 →
  按需回归服务化适配器（LiteLLM/Mem0/OpenViking/WeKnora，只换 capabilities 适配层，见 docs/01 映射表）
