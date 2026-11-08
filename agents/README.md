# agents — 三中心智能体本体

> 三中心定义唯一注册处：`config/centers.yaml`（内核/分区/工具类别/职责）。本目录只放各中心的规则与工作流。

## 共同纪律（三中心均须遵守）

1. **记忆纪律**（承接原 01-mem0-archive-rule，改用 capabilities/memory 实现）：
   - 写入仅在任务闭环时（成功完成 / 明确失败给结论），带至少一个业务标签；摘要模板：`分类标签 · 问题 · 现象 · 根因 · 解决方案 · 遗留约束 · 风险点`
   - 检索仅在新会话启动/切换项目/切换需求大类时，top_k≤5，复用已加载上下文不重复检索
   - 临时上下文不入记忆；跨分区读必须 cross_domain=true 并带 requester
2. **资产纪律**：产物写 `data/assets/<所属 namespace>/`，先 L0/L1 判断相关性再读 full
3. **信封纪律**：跨中心只走 `capabilities/mailbox`（data/mailbox/），禁止绕过编排器直接读其他中心分区
4. **安全纪律**：docs/05-安全与确认策略.md（确认分级/安全红线/备份回滚/日志规范）
5. **内核执行**：Cline（VSCode 扩展）加载本目录 workflows 执行；模型经 capabilities/llm 路由（禁止私接厂商密钥）

## 迁移说明（2026-11-09 原地重构）

- 原 .clinerules P0-P5 工作流与 00-07 规则已按中心拆分迁移（git mv 保留历史）；
  被引用文档的章节号沿用原文（如 §3.1 指迁移后 rules/build-deploy-rule.md 的 §3.1）
- 联邦遗产（Mem0/OpenViking/WeKnora 规则与同步脚本）归档 `archive/`
- 各中心 workflows 与 docs 的映射：
  - engineering：W0 预检 → W1 拉取构建 → W2 二开品牌 → W4 Git 同步 → W6 插件上架
  - data：D1 表格入库 → D2 统计分析
  - solution：S1 产品说明书 → S2 方案/论文
