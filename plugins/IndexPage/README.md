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

## 动态加入（决策闭环）

1. 页面上切换目标中心开关（虚线描边 = 待应用；底部面板汇总）
2. 点「导出决策」→ 下载 `decisions.json` → 放到本目录
3. 终端执行 `python3 scripts/indexpage.py apply`：
   - 插件/Docker 类 → 行级写回 `plugins/policy.yaml`（保留注释）→ registry 版本 +1 → 页面重新生成
   - MCP 类 → 输出人工操作清单（`mcp-pending-manual.json`），授权位置在 Cline 扩展设置
4. 刷新页面即见新授权状态（localStorage 待应用项自动对齐清除）

## 文件

| 文件 | 说明 | 入 git |
|---|---|---|
| index.html | 页面（生成产物，可重新生成） | ✅ |
| inventory.json | 盘点快照 | ✅ |
| decisions.json | 待应用决策（apply 后自动归档为 decisions-applied-<ts>.json） | 时效文件，不入库 |
| mcp-pending-manual.json | MCP 人工操作清单 | ✅ |

## 兼容

旧版静态列表页 `plugins-registry.html`（gen-registry.py --html）保留可用；本页为增强版（三中心开关 + MCP 盘点）。
