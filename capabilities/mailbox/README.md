# capabilities/mailbox — 中心间文件信封

`mailbox.py`：三中心唯一跨中心通道（替代 HTTP/MCP/消息队列）。协议详见 docs/03 §中心间文件协议。

## 接口

```
send(from, to, type, payload, run_id?, deadline_s=3600, return_as?, trace?) -> req_id
claim(center) -> env | None     # 原子改名占用 .req.json → .req.lock（超时信封自动转 .err.json）
reply(req_id, result)           # 产出 .res.json 并删除 lock
fail(req_id, error)             # 产出 .err.json 并删除 lock
poll_result(req_id, wait_s=0)   # 投递方轮询；超时未响应返回 pending（编排器按 on_fail 处理）
```

- 落位：`data/mailbox/<from>_<to>/<req_id>.{req,res,err}.json`
- 信封保留 7 天，是唯一跨中心调用凭证，审计查询优先读它
- 禁止任何 Agent 绕过编排器直接读取其他中心的 data/memory 或 data/assets
