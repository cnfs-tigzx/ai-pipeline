# capabilities/assets — 资产库与 URI 寻址（契约 3）

替代 OpenViking。`assets.py`：manifest.json + index.jsonl + `.versions/` 版本快照。

## 接口

```
write(namespace, path, content, meta) -> uri      # viking://<ns>/<path>
read(uri, level) -> { content, level, meta }      # L0 | L1 | full
list(namespace, prefix) -> [{uri, type, size, updated}]
stat(uri) -> meta
delete(uri, reason) -> ok                          # 移入 .trash/，manifest 标记
```

## 要点

- namespace ∈ {engineering, datacenter, solution, plugins}
- 覆盖写自动保留旧版本快照（`.versions/v<N>-<name>`），manifest 版本号自增
- 分层加载控制上下文体积：L0=标题+首段摘要 · L1=标题+小节标题+首段 · full=全文
- URI 保持 `viking://` 前缀仅为兼容历史寻址习惯，不依赖 OpenViking 服务
- 演进位：部署 OpenViking 后换 REST 适配器（AGPLv3 红线：仅 API 调用，禁止源码合并）
