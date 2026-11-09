# agent_init_rules — Cline 启动默认加载 · MCP/插件安装登记纪律

> 本文件位于 `.clinerules/`，Cline 每次会话自动加载。生效范围：安装 MCP 服务、插件服务、skills 时。

## 一、安装即登记（三步纪律，缺一不可）

Cline 每次安装 MCP server 或插件服务时，**必须同步完成**：

### 步骤 1 · 配置参数 → `agents/init/cline_mcp_settings.json`

- 将该 MCP/插件的配置参数（type/command/args/url/env 键名）写入工程内配置副本
- **凭据一律脱敏**：env 值写 `$KEEP` 占位（真实凭据仅存全局 `cline_mcp_settings.json` / 密钥文件 / 环境变量，禁止写入本副本与任何被推送文件——docs/05 安全红线）
- 推荐方式：经 `capabilities/clinecfg.clinecfg.upsert_server()`（自动双写+备份+审计）；
  人工编辑副本时保持 `$KEEP` 占位不破

### 步骤 2 · 安装命令与功能 → `agents/init/mcp_docs.md`

- 在 **AUTOGEN 区**登记（或触发 `capabilities/clinecfg.clinecfg.regen_mcp_docs()` 重新生成）：
  安装/启动命令、功能描述、类型（stdio/streamableHttp）、状态、中心授权
- **人工踩坑记录写 AUTOGEN 区之外**（`## 人工踩坑记录` 区），重新生成不会覆盖

### 步骤 3 · 正规上架（有 manifest 的插件）

- 走开发中心 W6 工作流：`plugins/manifests/<slug>/ov-plugin.yaml`（含结构化 `mcp_server` 定义）
  → `plugins/packages/` 登记 → `python3 scripts/gen-registry.py`（registry 版本+1）
  → `plugins/policy.yaml` 授权矩阵（三中心可见性）
- 一次性工具型 MCP（无 manifest）至少完成步骤 1/2 登记并写审计

## 二、skills 登记

- Cline skills 安装后：技能包落 `agents/init/skills/<name>/`，并在 `mcp_docs.md` 的 skills 登记区
  补一行：名称 / 来源 / 用途 / 落位路径
- 禁止将 skills 内容写入记忆分区（skills 是资产不是经验）

## 三、恢复与迁移

- 新机器：`cp agents/init/cline_mcp_settings.json` 结构参考 → 用 `clinecfg.upsert_server` 重建
  （`$KEEP` 自动回填：优先全局旧值，其次 manifest 的 `$ENV{}`/`$FILE{}` 引用，最后 missing_env 提示人工补配）
- 索引：本规则与 init 资产的关系见 `.clinerules/README.md` 与 `agents/init/`

## 四、违规判定

- 副本出现明文凭据（ark-…/密码字面量）→ 违反 docs/05 §二密钥隔离，立即清除并轮换密钥
- 安装后未登记（副本/mcp_docs 缺条目）→ 任务不算闭环，不得进入记忆归档
