# plugins — Plugin Hub 落位

> 插件 = 可被三大中心授权使用的工具/服务包。第一阶段无 MCP 传输层：内部按 manifest entry 子进程直调。

## 一、清单规范（ov-plugin.yaml）

落位：`manifests/<slug>/ov-plugin.yaml`（slug 小写中划线）。必填字段：

```yaml
name: 插件名称
slug: plugin-slug
version: 0.1.0
description: 插件功能描述
runtime: native            # native | docker
env:                       # 启动命令环境
  config_files: [setting.txt.example -> setting.txt]
  setup: python3 -m venv .venv && pip install -r requirements.txt
  start: uvicorn app:app --host 0.0.0.0 --port 8000
  health: http GET http://localhost:8000 -> 200
  port: 8000
tools:                     # 对中心暴露的工具（tools.py invoke 的目标）
  analyze_table:
    description: 对 CSV/Excel 表格做自然语言分析
    class: db_read         # 高风险类 → policy gate
    risk: medium
    entry:
      command: python3
      args: ['{plugin_dir}/cli.py', 'analyze', '{input}', '{run_id}']
    timeout_s: 120
compat:                    # 可选：对外 MCP 兼容声明（仅声明，内部分发不走 MCP）
  mcp: stdio:python3 {plugin_dir}/mcp_server.py
```

YAML 写法遵守 docs/02 §五（_yamlmini 子集）。

## 二、生命周期

```
开发（W1/W2 构建产物） → 上架（W6：manifest + packages 登记 + registry 版本+1 + 列表页刷新）
→ 授权（policy.yaml grants 写入，人工确认） → 启用（目标中心按需启动实例）
→ 升级（同 slug 覆盖 manifest，packages 登记新哈希） → 停用（grants 移除，registry 版本+1）
```

- registry 版本：`config/tools.registry.json` 的 `version`，任何上架/停用 +1；调用方据此刷新工具清单（替代推送通知）

## 三、实例策略

- **单例共享**（默认）：同一插件全机一个运行实例（如 TabClaw :8000），三中心经工具调用共享
- **按中心实例**：manifest 声明 `instance: per_center` 时，各中心独立实例，端口由 runtime.yaml 分配段位（eng 810x / data 820x / solution 830x）
- 实例启停记录：`data/assets/plugins/audit/`（start/stop 事件）

## 四、包登记（packages/<slug>/package.json）

字段：`{artifact_path, image_digest?, sha256, built_at, source_repo, source_commit, runtime}`。
产物本体不入 git（大文件落 repos/ 或 data/tmp/），登记可回溯。

## 五、列表页

`plugins-registry.html`（工程根目录，纯静态零服务）：由 `scripts/gen-registry.py --html` 生成，
展示插件名称、启动命令环境、功能描述、授权中心、registry 版本。
