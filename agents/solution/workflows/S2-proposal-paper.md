# S2 · 产品方案/论文生成（proposal-paper）

> 方案中心工作流。内核 = Cline plan 模式：先大纲后成文，人工卡点强制。
> 全局约束：docs/05-安全与确认策略.md；引用：agents/solution/README.md（写作范式）

**输入**：{TOPIC}（选题）、{AUDIENCE}（读者/场景）、{REFERENCES}（参考资料清单，可选）
**确认点**：2 个——大纲 gate、终稿 gate

## A. 资料汇编（plan 阶段）

1. 检索方案中心资产：`assets.list('solution', ...)` + L0/L1 读取，确认可引用样本
2. 需要外部网页资料 → `scrape.fetch` 落 `data/tmp/`，提取后写入 `data/assets/solution/samples/`
3. 需要事实数据 → `mailbox.send('solution', 'data', 'read_data', {need, format:'jsonnl'})`，等待回执；
   禁止编造数据；回执缺失的数字一律标"待补"

## B. 大纲生成 ⚠️ 确认点 1

1. `llm.complete('solution', 'outline', ...)` 生成大纲（章节 + 每章要点 + 引用计划）
2. 大纲写入 `data/runs/<run_id>/artifacts/outline.md`
3. **等待确认**（gate: outline）→ 驳回则按意见修订，最多 2 轮后转人工

## C. 成文（act 前的受控执行）

1. 按大纲逐章生成；每章引用必须带 dataset_uri / 样本路径
2. degraded=true → 停止成文，转人工
3. 全文拼装 → `data/assets/solution/papers/{TOPIC}-draft.md`

## D. 终稿 ⚠️ 确认点 2

1. 自查清单：口径引用完整 / 无编造数据 / 章节完整 / 术语一致
2. **等待确认** → 定稿 `data/assets/solution/papers/{TOPIC}.md`（版本快照由 assets 自动保留）
3. 记忆归档（闭环时）：写作范式/引用坑点 → memory 分区 solution（标签【写作范式】）
4. 追加 `output/task-log.md`
