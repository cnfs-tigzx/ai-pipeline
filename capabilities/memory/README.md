# capabilities/memory — 分区记忆（契约 2）

替代 Mem0。`memory.py`：jsonl 分片 + index.json + 朴素检索（tag 交集加权 + 关键词重合度）。

## 接口

```
add(center, content, tags, meta) -> id
search(center, query, tags, limit, cross_domain=false, requester) -> [{id, content, score, tags}]
update(id, patch) -> ok
forget(id, reason) -> ok          # 软删除（标记，不物理抹除）
```

## 要点

- 分区：`data/memory/{eng,data,solution}/shards/YYYY-MM.jsonl` + `index.json`
- `tags` 必填至少一个业务标签（如 安装测试 / 数据口径 / 写作范式）
- 去重合并：同 tag 且摘要前 50 字符重合度 > 0.9 → 合并计数而非新增
- `cross_domain=true` 必须带 `requester`，写入 `data/assets/plugins/audit/`（谁/为什么跨区读）
- 演进位：向量检索（`llm.embed` 已预留接口）、部署 Mem0 后换 REST 适配器
