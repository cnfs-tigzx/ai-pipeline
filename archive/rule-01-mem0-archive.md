# Mem0 记忆归档规则（01-mem0-archive-rule）

> 目标：跨会话沉淀踩坑与方案，省 token。临时上下文留 Cline 会话，不进 Mem0。
> 服务阶段：P5（Mem0 存取读写测试）为主；其余阶段仅在任务闭环时按本规则归档。
> 章节编号 = 1.x（引用格式：01-mem0-archive-rule.md §1.2）。

## 1.0 边界

- ✅ 入 Mem0：跨会话长期知识、踩坑记录、架构约定、修改方案
- ❌ 不入 Mem0：当前任务临时上下文、调试草稿、中间思考、完整源码、大段原始日志

## 1.1 分类标签池（多选，仅限以下；存入 metadata.labels）

| 标签 | 适用场景 |
|------|----------|
| 安装测试 | 环境搭建/依赖安装/编译报错/版本兼容/构建测试 |
| 网络 | API超时/ssh/github拉取失败/代理/防火墙/方舟接口连通异常 |
| 二次开发 | 界面修改/Logo替换/功能变更/代码重构/品牌替换/需求迭代 |
| Docker部署 | docker构建/compose启动/容器健康检查/镜像打包 |
| Git同步 | 仓库创建/提交推送/token鉴权/分支冲突/同步脚本异常 |
| 模型配置 | LLM API/embedding/MCP服务配置/Cline参数调试 |

## 1.2 检索（省 token 关键）

- 工具：`mem0__search_memories`（必带 user_id + project_id）
- 触发：仅 新会话启动 / 切换项目 / 切换需求大类
- 禁止：同一会话内连续交互、微调、看日志时重复检索，复用已加载上下文
- 参数：top_k≤5；相似度<0.6 直接丢弃；优先按当前任务标签过滤结果（按 metadata.labels 二次筛）
- 标签→阶段映射：改页面功能→【二次开发】(P3)；github超时→【网络】(P1/P4)；compose启动失败→【Docker部署】(P1)

## 1.3 写入（仅闭环归档）

- 工具：`mem0__add_memory`（必带 user_id + project_id + category + metadata.labels）
  - category 取最接近枚举：踩坑/问题→`problems_and_fixes`；架构约定→`decisions_and_constraints`；流程→`workflows`；结果→`results`；知识→`project_knowledge`
- 触发：仅【完整任务闭环】（成功完成 / 明确失败给结论）
- 禁止：每轮对话、每次回复都写
- 覆盖：用户说「归档本次对话」强制归档；「不要归档本次任务」跳过自动规则
- 摘要模板（固定）：`分类标签 · 问题描述 · 现象 · 根因 · 解决方案 · 遗留约束 · 风险点`

## 1.4 隔离

- 所有读写必带 user_id + project_id，禁止跨用户、跨项目读取
