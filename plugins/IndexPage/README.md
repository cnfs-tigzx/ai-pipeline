# IndexPage — 三中心门户（插件 / Docker 产物 / MCP 服务）

> 纯静态单文件页面（零服务零端口，双击即开）+ 文件决策闭环。生成器：`scripts/indexpage.py`。

## 打开方式

直接双击 `index.html`（file:// 可用，页面数据全部内联，无网络请求）。

## 页面内容（三类资源，build 时自动盘点）

| 类别 | 数据来源 |
|---|---|
| Docker 功能 | `plugins/packages/<slug>/package.json`（runtime=docker 的产物登记：镜像摘要/健康探测） |
| MCP 服务 | Cline 全局配置 `cline_mcp_settings.json`（凭据自动脱敏；mem0/openviking/weknora 标注为联邦遗产·已停用） |
| 插件 | `plugins/manifests/<slug>/ov-plugin.yaml` + registry（工具清单/启动命令环境） |

每个条目带 **eng / data / solution 三中心授权开关**（当前状态读 `plugins/policy.yaml` grants）。

## 动态加入（两种模式，页面自适应）

### 互联模式（推荐）：控制台直控

```
python3 scripts/control_server.py        # 拉起本地控制台（127.0.0.1:8765，非常驻，Ctrl+C 退出）
```

页面自动检测到控制台后进入**按钮直控模式**（顶部绿点提示）：

- **启动/停止服务**：插件卡按钮直发 → native（进程组管理+健康探测）/ docker（compose up/down），
  结果实时刷新（服务状态徽章：运行中/已停止）
- **三中心授权开关**：点击即写回 `plugins/policy.yaml`（registry 版本+1）；
  **grant 时自动把插件以 MCP 方式写入 Cline 配置**（`cline_mcp_settings.json`，写前自动备份 `.auto-bak/`，
  凭据 `$KEEP` 保留现有值）→ 重启 Cline（reload MCP）后三中心智能体即可经 MCP 调用该插件；
  revoke 仅移除授权矩阵可见性（MCP 条目保留，避免影响其他中心）
- 全部动作落审计 `data/assets/plugins/audit/`

### 离线模式：决策文件闭环

控制台未启动时页面自动降级（灰点）：开关→导出 decisions.json→`python3 scripts/indexpage.py apply`（同前文闭环）。

### Cline 配置说明

三中心共用同一 Cline 扩展实例；MCP 条目全局共享，**中心级隔离由 policy.yaml 授权矩阵承担**
（各中心 Agent 经 `capabilities/tools.list('<center>')` 只见已授权插件）。凭据引用：`$KEEP`=保留现值 / `$ENV{NAME}` / `$FILE{relpath}`。

## 文件

| 文件 | 说明 | 入 git |
|---|---|---|
| index.html | 页面（生成产物，可重新生成） | ✅ |
| inventory.json | 盘点快照（含服务状态/Cline MCP 状态） | ✅ |
| decisions.json | 离线模式待应用决策（apply 后自动归档） | ❌ 时效文件 |
| mcp-pending-manual.json | MCP 人工操作清单 | ✅ |

## 兼容

旧版静态列表页 `plugins-registry.html`（gen-registry.py --html）保留可用；本页为增强版（直控 + 三中心开关 + MCP 盘点）。
