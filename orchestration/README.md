# orchestration — DAG 执行器、断点、卡点、重试

> 契约 5（Orchestrator）的实现。替代 WeKnora 的流程承载位与曾评估的 Prefect（见 archive/orchestration-upgrade-assessment.md）。

## runner.py（单宿主进程）

- 启动三检查：目录可写 / config 可解析 / 模型密钥（缺失 → 离线模式，见 docs/04）
- 节点类型：
  - `script`：调用 capabilities 模块函数（`call: 包.模块.函数`，args 支持 `{node}` / `{node.field}` 模板引用上游输出）
  - `llm`：`llm.complete(center, ...)`，degraded=true 时视为失败（按 on_fail 处理）
  - `gate`：写 `data/runs/<run_id>/gate.json` 等人工 decision（pending/approved/rejected；改名节点为 decision 值）
  - `envelope`：send / poll / claim_and_reply（文件信封，见 capabilities/mailbox）
- 断点续跑：`data/runs/<run_id>/state.json` 保存节点状态 + context 快照；`resume` 从未完成节点继续
- 失败策略：节点 `retry: n` → 超限按 `on_fail: abort(默认)/skip/gate`
- 多实例：state.json 带 lock 字段（holder+heartbeat），同一 run 仅一个 runner

## 用法

```
python3 orchestration/runner.py run   orchestration/flows/data-table-import.flow.yaml --inputs '{}' [--auto-approve]
python3 orchestration/runner.py resume <run_id> [--auto-approve]
python3 orchestration/runner.py status <run_id>
```

--auto-approve 仅供自测/演示（gate 自动放行），生产禁用。

## flows

| 文件 | 中心 | 说明 |
|---|---|---|
| data-table-import.flow.yaml | data | 网页→二维表→SQLite→登记（演示版用本地样例，真实换 fetch 节点） |
| solution-manual.flow.yaml | solution | 资料收集→大纲→卡点→登记（outline degraded 时转 gate） |
| dev-import-plugin.flow.yaml | eng | 环境检查→信封消费→registry 重建（W6-C 编排部分） |

## 轨迹

每节点前后写 `data/trace/<center>/<run_id>.jsonl`（capabilities/trace），审计回放以 trace + 信封 + run 目录三处为准。
