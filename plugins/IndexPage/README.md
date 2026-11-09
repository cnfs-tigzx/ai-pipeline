# IndexPage — 三中心门户（五视图）

> 纯静态单文件应用 + 本地控制台互联 + launchd 常驻。生成器：`scripts/indexpage.py build`。

## 常驻运行（系统默认启动）

```
./scripts/indexpage-service.sh install     # 安装 launchd 常驻（登录自启 + KeepAlive 崩溃拉起）
./scripts/indexpage-service.sh status      # 查看状态（launchd 注册 + 健康探测）
./scripts/indexpage-service.sh restart     # 重启（**改了 Python 代码后必须 restart**：常驻进程不热更新）
./scripts/indexpage-service.sh uninstall   # 卸载
```

- 服务：`http://127.0.0.1:8765`（页面 + API 同端口；plist 模板 `launchd/com.ai-three-center.indexpage.plist`，安装时自动填充 python3 与工程路径）
- 日志：`output/indexpage-service.log`（logs 子命令）
- 不装 launchd 也可 `python3 scripts/control_server.py` 手动拉起，或 file:// 双击 index.html（离线模式）

## 五个视图（左导航）与其配置文件映射

| 视图 | 功能 | 写回的工程文件 |
|---|---|---|
| 插件与 MCP | 服务启停按钮 / 三中心授权开关 / MCP 盘点（凭据脱敏） | `plugins/policy.yaml`（grants）· `cline_mcp_settings.json`（grant 自动配 MCP，备份 .auto-bak） |
| GitHub 导入 | 地址输入 → 拉取+解析 → 编译部署/停止/构建/状态 | `repos/<repo>/`（源码）· `data/assets/engineering/<repo>/readme-parse.json`（解析产物）；部署经 `scripts/one-key.sh` |
| 产品功能文档 | 主题 → 生成大纲（可人工编辑）→ 按大纲成文 → 归档/列表 | `data/assets/solution/{manuals,papers}/`；模型走 `config/models.yaml` routing.solution |
| Cline 参数配置 | 三中心模型路由（primary 接入点编辑）+ 内核/工作流只读展示 | `config/models.yaml`（routing.eng/data/solution）· `config/centers.yaml`（只读） |
| 全局规则配置 | runner 轮询 / LLM 超时重试 / 信封时限 / 节点重试 / 插件审批 | `config/runtime.yaml` · `plugins/policy.yaml`（approval） |

所有保存动作：**行级写回保留注释** → 先备份 `.auto-bak/<date>-config/` → 审计落 `data/assets/plugins/audit/` → registry 版本联动 +1。

## 动态加入（两种模式，页面自适应）

### 互联模式（常驻后默认）：控制台直控

页面检测 `127.0.0.1:8765` 可达即进入直控（顶部绿点）：按钮/开关点击即时生效并写回上述配置文件；
**grant 同时自动把插件以 MCP 方式写入 Cline 配置**（凭据 `$KEEP` 保留现值）→ 重启 Cline（reload MCP）后三中心智能体即可调用；revoke 仅移除授权矩阵可见性（MCP 条目保留，避免影响其他中心）。

### 离线模式：决策文件闭环

控制台未启动（灰点）：开关 → 导出 decisions.json → `python3 scripts/indexpage.py apply`。

## MCP 服务盘点数据源

Cline 全局配置 `cline_mcp_settings.json`（mem0/openviking/weknora 自动标注「联邦遗产·已停用」+ 恢复指引 docs/01）。

## 文件

| 文件 | 说明 | 入 git |
|---|---|---|
| index.html | 页面（生成产物） | ✅ |
| inventory.json | 盘点+配置快照 | ✅ |
| decisions.json | 离线模式待应用决策（apply 后归档） | ❌ 时效文件 |
| mcp-pending-manual.json | MCP 人工操作清单 | ✅ |
