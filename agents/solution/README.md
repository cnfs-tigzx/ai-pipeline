# 方案中心（solution）

> 定位：方案/论文/图谱。内核 = Cline **plan 模式** + 火山方舟 doubao 系列（config/models.yaml routing.solution）。

## 职责

1. 存储各类资料、方案样本、产品说明（`data/assets/solution/` 分层 L0/L1/full）
2. 生成产品方案与论文：plan 模式先出大纲 → 人工卡点确认 → 成文
3. 事实数据经 mailbox 向数策中心发 `read_data` 信封（禁止直接读数策分区）

## 工作流

| 编号 | 文件 | 内容 |
|---|---|---|
| S1 | workflows/S1-manual.md | 产品说明书生成（原 P2 手册部分，双源抓取） |
| S2 | workflows/S2-proposal-paper.md | 产品方案/论文生成（新增） |

## 规则

- 写作范式：结论先行、口径必须来自数策中心信封回执（引用 dataset_uri）、不得编造数据
- plan 模式卡点：大纲未经 gate 放行不得进入成文；degraded=true 时自动转人工
- 表格抓取需求转数策中心 D1（rules/web-capture-rule.md 归属数策）

## 产物落位

- 说明书/方案/论文：`data/assets/solution/manuals|samples|papers/`
- 引用数据集：只记 URI 与口径说明，不复制大表
