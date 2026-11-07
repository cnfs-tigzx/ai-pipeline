---
disabled: true
---
【前置环境预检 增强版规则】
适用范围：ai-pipeline 流水线
任何拉取代码、git推送、docker编译部署、npm安装、调用火山方舟API、访问github资源的任务，**必须优先执行 ./scripts/preflight-check.sh**，读取 preflight-report.md 报告
---
模式区分：
1. Plan模式：执行预检，输出完整报告给用户审阅，仅做分析，不阻止思考，不执行变更
2. Act模式：
   - 如果报告包含【存在异常】：立刻停止所有高危操作（禁止git、docker、npm、模型调用），完整展示报告，询问用户是否【强制继续】
   - 用户回复【强制继续】之后，才允许继续执行后续流水线
3. 豁免规则（可以跳过预检）：纯本地文件读取、代码静态分析、文档编写、Mem0记忆读写、本地注释修改
4. 缓存机制：脚本自带5分钟缓存，短时间连续下发任务不会重复检测；需要强制刷新检测，手动删除 .preflight-cache.ts
5. 禁止：预检未完成前，不启动克隆、打包、部署、推送等高危操作
6. 报告输出：markdown格式展示，重点标红❌异常项

【高危任务清单（强制预检）】
git clone / git pull / git push / docker build / docker compose / npm install / yarn install / 火山方舟模型API调用
【低风险任务清单（豁免预检）】
读文件、代码阅读、写文档、整理知识库、mem0记忆存取、本地简单注释修改