# capabilities/tools — 工具注册表与分发（契约 4）

替代 MCP Gateway。`tools.py`：registry + policy 授权过滤 + manifest entry 子进程直调 + 全量审计。

## 接口

```
list(center) -> { version, tools: [{name, description, side_effect, risk}] }
invoke(center, name, args) -> { ok, data, error, audit_id }    # name = {slug}__{tool}
bump_version() -> int                                          # 插件上架/停用后版本 +1
```

## 要点

- 工具可见性：`plugins/policy.yaml` grants.<center> 未授权的插件一律不可见
- 分发不走 MCP：读 `plugins/manifests/<slug>/ov-plugin.yaml` 的 `tools.<tool>.entry`（command + args 模板，支持 `{arg}` 与 `{run_id}` 占位），子进程直调
- MCP 兼容声明保留在 manifest 的 `compat.mcp` 字段（仅供对外），内部不分发
- 审计：`data/assets/plugins/audit/YYYY-MM-DD.jsonl`（center/slug/tool/参数哈希/耗时/状态）
- 高风险工具（class ∈ db_read/db_write/scrape_remote）按 policy `approval.high_risk_tools=gate` 转人工卡点
- `config/tools.registry.json` 由 `scripts/gen-registry.py` 从 manifests 生成，启用/停用插件后版本 +1，调用方以 version 变化刷新工具清单（替代推送通知）
