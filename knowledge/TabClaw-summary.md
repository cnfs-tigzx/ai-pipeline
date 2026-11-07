# TabClaw 知识库摘要

> 来源：repos/TabClaw（https://github.com/fishsure/TabClaw → ustc-table-mining/TabClaw），commit 420125a (main)
> 解析产物：readme-parse/TabClaw.json · 部署模式：native (Python)
> 解析日期：2026-11-08 · 任务：20261108-001602

## 一句话定位

中科大开源的**交互式表格分析 AI 智能体**：拖入 CSV/Excel，自然语言下达需求——先出计划、并行多智能体分析、记住用户偏好、从交互中提炼可复用技能，越用越强（自进化）。

## 核心能力（与流水线联邦的对照）

| TabClaw 内置 | 流水线联邦对应组件 | 说明 |
|--------------|-------------------|------|
| 持久记忆（偏好/术语/格式） | Mem0 经验记忆层 | TabClaw 记忆为项目内单用户，Mem0 为跨项目 agent 级 |
| 技能蒸馏 + ClawHub 导入 | WeKnora 知识库 / OpenViking skills | 思路同源（SKILL.md 包式技能与 ClawHub 生态一致） |
| 长对话压缩 | —（Cline 自管） | — |

## 技术栈与结构

| 层 | 技术 |
|----|------|
| 后端 | Python：FastAPI + uvicorn[standard]（app.py 入口） |
| 数据 | pandas>=2.1.0 + openpyxl + numpy<2 |
| LLM | openai SDK，OpenAI 兼容 BASE_URL |
| 前端 | static/ 静态页（无构建） |
| 其他目录 | agent/（智能体核心）、auth/（多用户+API Key 管理）、skills/ + skill-example/（技能）、docs/（mkdocs 文档站）、demo_data/ |

## 部署要点（native 模式）

1. `cp setting.txt.example setting.txt` → 填 `API_KEY` / `BASE_URL` / `DEFAULT_MODEL`
2. `python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`
3. 启动：`uvicorn app:app --host 0.0.0.0 --port 8000`（后台守护去掉 run.sh 的 `--reload`）
4. 访问：http://localhost:8000（一键体验按钮进入引导演示）

## 本地配置（已配）

- BASE_URL=https://ark.cn-beijing.volces.com/api/v3（火山方舟，OpenAI 兼容）
- DEFAULT_MODEL=ep-20261105181307（GLM-5.3-Flash 接入点，与 OpenViking 同源）
- API_KEY 存 repos/TabClaw/setting.txt（.gitignore 已忽略，不入库）

## 部署踩坑清单

1. **pipeline.sh 相对路径缺陷（本次实修）**：原脚本用 `../repos/` 相对路径，从流水线根目录调用时仓库克隆到了流水线目录之外（/Users/tigzx/workspace/repos/），违反 00 §安全边界；已改为基于脚本自身位置定位 PIPELINE_ROOT，任意 cwd 可用
2. run.sh 的 `--reload` 不适合后台守护（双进程 + 文件监听），部署直接 uvicorn 无 reload
3. numpy 必须 <2（requirements 已锁定，勿升级）
4. 端口 8000 与 mkdocs 本地预览端口相同，避免同时运行
