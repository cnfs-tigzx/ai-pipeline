# ai-pipeline
Cline AI 流水线工程｜GLM-5.2 + 火山方舟 + WeKnora 自动化

## 敏感信息管理（本地保留，严禁上传）

所有 API Key / 账号密码 / 接入点 ID 统一保存在本地文件，均已加入 `.gitignore`，不会被提交：

| 本地文件 | 内容 |
|----------|------|
| `火山方舟模型API` | 火山引擎 Ark API Key、GLM / Doubao-embedding 接入点 ID |
| `local-secrets.md` | Mem0 管理员账号密码、ADMIN_API_KEY、MCP 数据库 Key |

如需在其他设备使用，请人工拷贝上述文件，禁止将其提交到 Git。
