# W6 · 插件上架与三中心安装（plugin-release）

> 开发中心专属工作流。前置：W1（构建部署）已完成，插件工程可运行。
> 全局约束：docs/05-安全与确认策略.md（确认分级/备份回滚）
> 引用规则：rules/build-deploy-rule.md §3.4（产物）、capabilities/tools/README.md（registry 机制）

**输入**：{SLUG}（插件名）、{REPO}（源工程）、{RUNTIME}（native|docker，默认 native）
**确认点**：仅 1 个——步骤 D 写 policy 授权（影响三中心工具可见性）

## A. manifest 生成

1. 在 `plugins/manifests/{SLUG}/` 创建 `ov-plugin.yaml`，必填字段：
   - `name`（插件名称）、`description`（插件功能描述）、`version`、`runtime`（native|docker）
   - `env`（启动命令环境：必需环境变量/启动命令/健康探测方式）
   - `tools.<tool>.{description, class, risk, entry}`（entry: command + args 模板，支持 {arg}/{run_id} 占位）
   - `compat.mcp`（可选：对外 MCP 兼容声明，内部不分发）
2. YAML 遵守 docs/02 §五 _yamlmini 子集限制

## B. 包登记

1. `plugins/packages/{SLUG}/package.json` 登记：构建产物路径、镜像摘要（docker 时 `docker image inspect`）、sha256、构建时间、源仓库 commit
2. native 包：tar 打包产物至 `plugins/packages/{SLUG}/bundle.tar.gz` 并登记哈希

## C. registry 生成与列表页刷新

1. 执行 `python3 scripts/gen-registry.py` → 重建 `config/tools.registry.json` 并版本 +1
2. 执行 `python3 scripts/indexpage.py build` → 生成三中心门户页 `plugins/IndexPage/index.html`
   （插件名称/启动命令环境/功能描述/三中心授权开关；动态授权走页面决策闭环，见该目录 README）

## D. 授权与安装（唯一确认点）⚠️

1. 打印待写入 `plugins/policy.yaml` 的 grants 变更 → **等待确认** → 写入
2. 目标中心如需即时生效：向 `data/mailbox/eng_<center>/` 投递 `plugin_update` 信封（payload 含 slug 与新 registry version）
3. docker 插件：按 rules/build-deploy-rule.md 高危规则执行 compose up（单独确认）

## E. 收尾

1. 资产登记：`data/assets/plugins/` 写上架记录（manifest 摘要 + 包哈希）
2. **init 资产同步（agent_init_rules 纪律）**：确认 `agents/init/cline_mcp_settings.json` 与
   `agents/init/mcp_docs.md` 已含本插件条目（若在步骤 D 做过 grant，clinecfg 已自动双写；否则手动补登记）
3. 记忆归档（任务闭环）：踩坑/决策写入 memory（分区 eng，标签【安装测试】或【二次开发】）
4. 追加 `output/task-log.md`
