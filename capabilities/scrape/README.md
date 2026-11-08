# capabilities/scrape — 网页抓取与表格抽取

`scrape.py`：urllib 抓取（playwright 演进位）+ 零依赖 HTML 表格抽取。

## 接口

```
fetch(url, timeout_s=30, save=True) -> { ok, status, text, url, saved_to }
fetch_local_html() -> 本地样例（零网络自测）
to_rows(html_text, table_index=0) -> [[cell...]]   # 表格 → 二维数组（含表头）
```

- 抓取结果存 `data/tmp/scrape/`（7 天可清理）
- 动态渲染页/需登录页 → 演进位挂 playwright（MCP 或 Python SDK）
- 数策中心工作流 D1 调用 `fetch + to_rows` 完成"网页 → 二维表"
