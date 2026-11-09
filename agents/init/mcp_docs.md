<!-- AUTOGEN:BEGIN（此区由 clinecfg 自动生成，勿手改）-->

# Cline MCP 插件清单（自动生成 · 2026-11-10T00:27:48+08:00）

| 名称 | 类型 | 安装/启动方式 | 功能 | 状态 | 中心授权 |
|---|---|---|---|---|---|
| mem0 | stdio | `python3 /Users/tigzx/workspace/ai-pipeline/repos/mem0/integrations/codex-plugin/core/mcp_server.py` | 联邦遗产（Mem0）· 第一阶段停用 · 恢复见 docs/01 | 联邦遗产（Mem0）· 第一阶段停用 · 恢复见 docs/01 | - |
| openviking | streamableHttp | HTTP 端点直连：http://localhost:1933/mcp | 联邦遗产（OpenViking）· 第一阶段停用 · 恢复见 docs/01 | 联邦遗产（OpenViking）· 第一阶段停用 · 恢复见 docs/01 | - |
| tabclaw | stdio | `python3 repos/TabClaw/integrations/tabclaw-mcp/mcp_server.py` | 交互式表格分析 AI 智能体：拖入 CSV/Excel，自然语言下达需求，先出计划、并行多智能体分析、记住用户偏好、可从交互中提炼可复用技能 | 现役 | eng, data |
| weknora | streamableHttp | HTTP 端点直连：http://localhost:8080/mcp/4fb7fad2-d491-48a8-b75b-e27a68b84db4 | 联邦遗产（WeKnora）· 第一阶段停用 · 恢复见 docs/01 | 联邦遗产（WeKnora）· 第一阶段停用 · 恢复见 docs/01 | - |

## 安装命令速查

- TabClaw MCP（stdio wrapper，现役）：`python3 repos/TabClaw/integrations/tabclaw-mcp/mcp_server.py`（前置：TabClaw 服务运行中 :8000，`services.start` 或 one-key）
- 恢复联邦三件套（mem0/openviking/weknora）：见 `archive/` 与 docs/01 服务化回归路径
- 新增插件正规流程：开发中心 W6（manifest → packages → registry → policy 授权 → 本清单自动更新）

## skills 登记区

- （Cline skills 安装后在此登记：名称 / 来源 / 用途 / 落位 agents/init/skills/）

<!-- AUTOGEN:END -->





































## 人工踩坑记录

- （安装/使用 MCP 时的踩坑与注意事项写在这里，重新生成不会覆盖）
