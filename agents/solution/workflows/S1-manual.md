# P2 · 网页抓取与产品说明书（web-capture-manual）

> 五大阶段之 P2。触发：拿到一个已部署/已拉取的项目，要产出《产品说明书》。
> 工作根目录：/Users/tigzx/workspace/ai-pipeline
> 全局约束：docs/05-安全与确认策略.md（确认策略 §1.1 / 日志 §1.4）；浏览器与 MCP 工具约束 → docs/05-安全与确认策略.md
> 引用规则：agents/data/rules/web-capture-rule.md §6.1（浏览器检查）/ §6.2（通用抓取）/ §6.3（表格）/ §6.4（产品说明书双源抓取）

**输入**：{REPO}、{REPO_URL}（可选：产品官网/文档 URL；未提供则从仓库页发现）
**前置**：P1 已完成更佳（可复用 readme-parse/{REPO}.json），非强制
**确认点**：本阶段无高危操作，连续执行

## 任务步骤

1. **浏览器前置检查**（§6.1）：playwright navigate 到 about:blank；失败自动回退 `fetch_web_content`
2. **双源抓取**（§6.4.1）：
   - 源1 GitHub 仓库网页 {REPO_URL}：项目简介、功能亮点、截图、技术栈、Star/Fork、Releases 版本、Wiki/Docs 入口
   - 源2 产品说明网页（官网/文档站/仓库页发现的 docs 链接）：逐页抓取
   - 抓取优先级：Usage → User Guide → 使用教程 → 功能说明 → 操作步骤 → 截图说明 → 业务流程
3. **截断检测**（§6.2）：内容 < 预期 50% 或有"加载更多" → `fetch_web_content` 补充抓取
4. **表格抓取**（§6.3，如有）：表头+全部行 → `knowledge/table-{REPO}.json`
5. **内容清洗**（§6.4.2）：
   - ✅ 保留：产品/功能介绍、操作流程、页面说明、表单字段、使用限制、常见业务问题、版本更新
   - ❌ 剔除：部署、编译、开发、本地启动、源码相关、issues、PR、开发 TODO
6. **原始素材** → `readme-parse/{REPO}-product-capture.json`（来源 URL、抓取时间、章节化内容）
7. **产品说明书** → `knowledge/{REPO}-product-manual.md`，固定七章结构：
   ① 产品概述（含 GitHub 项目信息）→ ② 功能模块总览 → ③ 各模块操作步骤 → ④ 界面与字段说明 → ⑤ 使用示例 → ⑥ 常见使用问题 → ⑦ 版本与更新
8. **产物同步**（07 §7.4）：手册 → 双层落位（失败不阻塞流水线，记 task-log）
   - `scripts/ov-sync.sh knowledge/{REPO}-product-manual.md viking://resources/{REPO}/manuals/ "P2 手册同步"`
   - `scripts/weknora-sync.sh knowledge/{REPO}-product-manual.md`（业务门户立即可问答）
   - 如有表格：`scripts/ov-sync.sh knowledge/table-{REPO}.json viking://resources/{REPO}/datasets/ "P2 表格同步"`
9. report 追加章节 9（产品说明书）；追加 `output/task-log.md`

## 收尾

- 产物核对：`knowledge/{REPO}-product-manual.md` · `readme-parse/{REPO}-product-capture.json`
- 输出总结：双源抓取✓/✗ · 手册章节数 · 截断补充次数 · 遗留缺口

## 使用示例

```
执行 P2（web-capture-manual），参数：
{REPO} = WeKnora
{REPO_URL} = https://github.com/Tencent/WeKnora
```
