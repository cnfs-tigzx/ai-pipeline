# capabilities/llm — 模型路由与计量（契约 1）

替代 LiteLLM 网关。`llm.py` 用标准库 urllib 直连火山方舟 OpenAI-compatible API。

## 接口

```
complete(center, task, messages, options) -> { text, model, usage, latency_ms, degraded }
embed(center, texts, purpose) -> { vectors[], model }
```

## 要点

- `center ∈ {eng, data, solution}` → 读 `config/models.yaml` 路由（primary → fallback）
- 密钥只由本模块读取：环境变量 `ARK_API_KEY` 优先，缺失回退根目录密钥文件（gitignored）；**禁止**写入日志/manifest/被推送文件
- 每次调用计量落 `data/usage/<center>/YYYY-MM.jsonl`（含 tokens/耗时/degraded）
- 全部模型不可用 → 离线模式：模板占位文本 + `degraded=true`（见 docs/04 §三）
- 已知限制：doubao/deepseek 接入点待补（models.yaml 中 sentinel- 占位），启动检查会标注

## 自测

`python3 capabilities/selftest.py`（t_llm 用例：normal 模式真实调用 GLM 返回 OK；offline 模式断言 degraded=true）
