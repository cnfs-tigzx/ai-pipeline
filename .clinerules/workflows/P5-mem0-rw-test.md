# P5 · Mem0 存取读写测试（mem0-rw-test）

> 五大阶段之 P5。触发：验证 mem0 经验存入与语义检索功能；mem0 服务修复/升级后回归测试。
> 工作根目录：/Users/tigzx/workspace/ai-pipeline
> 引用规则：01-mem0-archive-rule.md（§1.0 边界 / §1.1 标签池 / §1.2 检索 / §1.3 写入 / §1.4 隔离）；MCP/stdio 排查 → 04-mcp-control-rule.md §4.3

**输入**：无（本地 self-hosted：API http://localhost:8888 · Dashboard http://localhost:3000）
**确认点**：无高危操作，连续执行

## 前置条件

1. **mem0 服务就绪**：`./scripts/mem0-one-key.sh status`（未启动则 start；compose 位于 `repos/mem0/server/`，数据卷 mem0-dev_postgres_db 持久化，stop/down 不删除数据）
2. **MCP 连接可用**：`mem0__search_memories` / `mem0__add_memory` 两个工具出现在工具列表
   - env 约定：`MEM0_API_URL=http://localhost:8888` · `MEM0_USER_ID=cline-tigzx`（本地认证走 `X-API-Key` 请求头，非 Authorization: Token）
   - 服务端为 stdio 模式：`repos/mem0/integrations/codex-plugin/core/mcp_server.py`；stdout 仅协议消息，调试走 stderr
   - 服务端代码变更后需重启 Cline MCP 连接（VS Code 重启扩展，或 MCP 面板重启 mem0 server），否则工具仍连旧代码

## 测试步骤

1. **协议层握手**：MCP `initialize`（期望返回 protocolVersion 2024-11-05）+ `tools/list`（应含 `search_memories` + `add_memory`）
2. **写入测试**（add_memory）：存入 3-5 条带分类标记的测试经验
   - 必带 user_id + project_id + category + metadata.labels（标签仅限 01 规则 §1.1 标签池）
   - 记录每条返回的记忆 id，形成测试清单
3. **读取测试**（search_memories）：
   - 语义查询验证：如 "git clone 超时怎么办"，top_k=5，期望带 score 排序结果且 top-1 语义命中
   - 跨语言召回：中文 query → 英文 memory 命中
   - 相似度 < 0.6 直接丢弃（01 规则 §1.2）
4. **失败排查链路**（固定顺序，源自实测根因）：
   - search 返回 failed → 查服务端调用的 REST 端点：本地仅 `/search`、`/memories`（无 `/v3/*` 云端路径）
   - 401 → 认证方式应为 `X-API-Key` 请求头
   - 404 → `docker logs` mem0 容器核对端点，对照 openapi.json
   - 无写入工具 → 检查 `mcp_server.py` 是否暴露 `add_memory`
   - 定位修复 → 重启 MCP 连接 → 从步骤 1 重测
5. **Dashboard 可视化验证**：访问 http://localhost:3000 检查分类标记与记忆列表；测试数据可经 DELETE /memories/{id} 或 Dashboard 清理
6. **产物**：`output/mem0-test-report.md`（新建或追加：测试时间/目标/环境、协议层结果、写入清单、检索 score 表、闭环结论）；追加 `output/task-log.md`
7. **闭环归档边界**（01 规则 §1.0/§1.3）：仅真实任务闭环时写入正式经验；纯测试数据不归档进 Mem0

## 使用示例

```
执行 P5（mem0-rw-test），无额外参数
```
