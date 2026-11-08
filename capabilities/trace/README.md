# capabilities/trace — 操作轨迹

`trace.py`：run 级轨迹 jsonl（Langfuse 的文件实现替代）。

## 接口

```
append(run_id, center, event, detail)   # 落 data/trace/<center>/<run_id>.jsonl
read(run_id, center) -> [event...]
centers(run_id) -> [center...]          # 跨中心视图
```

- 节点执行前后、gate 决策、降级事件均应 append，保证断点回放与审计
- 演进位：需要可视化轨迹时启用 WeKnora 内置 langfuse profile（错峰纪律保留）
