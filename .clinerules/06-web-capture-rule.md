# 网页内容抓取规则（06-web-capture-rule）

> 服务阶段：P2（抓取 GitHub 仓库网页及产品说明网页 → 产品说明书）。提示词：workflows/P2-web-capture-manual.md。
> 章节编号 = 6.x；确认策略/日志规范见 00-base-general.md；浏览器与 MCP 调用约束见 04-mcp-control-rule.md。

## 6.1 前置检查（浏览器可用性）

- Playwright 启动前检测浏览器：尝试 `playwright navigate` 到 `about:blank`
- **失败回退**：自动切换到 `fetch_web_content` 工具抓取（URL + 提取 prompt），不影响流程
- 不创建/修改 /Applications 下的 Chrome 应用

## 6.2 通用抓取规范

- 等待页面/接口/表格渲染完成，优先语义选择器，不使用硬编码 xpath
- **截断检测**：抓取后检查内容长度，若疑似截断（< 预期 50%）或页面明显有"加载更多"，用 `fetch_web_content` 补充抓取
- 抓取完成后在任务日志追加记录

## 6.3 表格抓取

- 提取表头+全部行，默认输出 JSON
- 结果写入 `knowledge/table-{REPO}.json`
- 自动录入：识别表单字段，按行循环填充提交，捕获报错、截图留存

## 6.4 产品说明书生成（双源抓取）

**目标**：综合 GitHub 仓库网页 + 产品说明网页，生成面向使用者的《产品说明书》

### 6.4.1 双源抓取

| 源 | 内容 |
|----|------|
| 源1 GitHub 仓库网页（{REPO_URL}，非本地 README） | 项目简介、功能亮点/特性列表、截图、技术栈、Star/Fork 数据、Releases 版本记录、Wiki/Docs 入口链接 |
| 源2 产品说明网页（官网/文档站/仓库页发现的 docs 链接） | Usage → User Guide → 使用教程 → 功能说明 → 操作步骤 → 截图说明 → 业务流程 |

- 源2 发现途径：仓库页/README 中的官网或文档链接 → 逐页抓取；无独立文档站时以仓库页 + Wiki 为准
- 抓取优先级：Usage → User Guide → 使用教程 → 功能说明 → 操作步骤 → 截图说明 → 业务流程

### 6.4.2 内容清洗

- ✅ 保留：产品/功能介绍、操作流程、页面说明、表单字段、使用限制、常见业务问题、版本更新
- ❌ 剔除：部署、编译、开发、本地启动、源码相关、issues、PR、开发 TODO

### 6.4.3 产物

- `readme-parse/{REPO}-product-capture.json`：双源原始结构化素材（来源 URL、抓取时间、章节化内容）
- `knowledge/{REPO}-product-manual.md` 产品说明书，固定章节：
  ① 产品概述（含 GitHub 项目信息）→ ② 功能模块总览 → ③ 各模块操作步骤 → ④ 界面与字段说明 → ⑤ 使用示例 → ⑥ 常见使用问题 → ⑦ 版本与更新
- `output/{REPO}-report.md` 追加章节 9（产品说明书）；`output/task-log.md` 追加
