# Mem0 知识库摘要

## 项目概述

Mem0 是一个为 AI Agent 提供持久化记忆层的开源基础设施。支持自托管部署，提供 REST API、Web Dashboard、多用户账号管理、API Key 认证，可作为 SaaS 云服务为多客户端提供记忆存储与检索。

核心能力：记忆添加、语义搜索、实体链接、时序推理、多信号检索（语义+BM25关键词+实体匹配）、Reranker 重排。

## 技术栈

| 维度 | 详情 |
|------|------|
| 后端 | Python 3.12 + FastAPI + uvicorn |
| 前端 | Next.js 15 + React + TypeScript |
| 数据库 | PostgreSQL 17 + pgvector 0.8.0 |
| LLM | OpenAI gpt-5-mini（默认，可换 Anthropic/Google/Ollama） |
| 嵌入 | OpenAI text-embedding-3-small（默认，可换 HuggingFace/Ollama 等） |
| 认证 | JWT（Dashboard 登录）+ X-API-Key（API 调用） |
| 部署 | Docker Compose（3 容器） |

## 仓库结构

```
mem0/
├── mem0/                    Python SDK 源码（pip install mem0ai）
├── mem0-ts/                 TypeScript SDK 源码（npm install mem0ai）
├── server/                  自托管 Server
│   ├── main.py              FastAPI 应用入口
│   ├── auth.py              JWT + API Key 认证
│   ├── models.py            数据模型
│   ├── routers/             API 路由
│   ├── alembic/             数据库迁移
│   ├── dashboard/           Next.js Web 管理后台
│   ├── docker-compose.yaml  3 服务编排
│   ├── Dockerfile           生产镜像
│   ├── dev.Dockerfile       开发镜像
│   ├── Makefile             构建管理入口
│   └── .env.example         环境变量模板
├── cli/                     CLI 工具
├── docs/                    文档
├── .claude-plugin/          Claude Code 插件
├── .codex-plugin/           Codex 插件
├── .cursor-plugin/          Cursor 插件
└── .kimi-plugin/            Kimi 插件
```

## Docker 服务架构

| 服务 | 镜像 | 端口 | 用途 |
|------|------|------|------|
| mem0 | mem0-dev-mem0 (本地构建) | 8888→8000 | FastAPI REST API |
| postgres | pgvector/pgvector:pg17 | 8432→5432 | 向量数据库 |
| mem0-dashboard | mem0-dev-mem0-dashboard (本地构建) | 3000→3000 | Web 管理后台 |

## 访问地址

| 服务 | URL |
|------|-----|
| Dashboard | http://localhost:3000 |
| API | http://localhost:8888 |
| OpenAPI 文档 | http://localhost:8888/docs |

## 多用户与安全

| 能力 | 说明 |
|------|------|
| 多用户隔离 | user_id + agent_id + org_id 多维度 |
| API Key | 每用户独立 API Key，支持创建/吊销 |
| Dashboard 登录 | JWT 认证 |
| 限流 | 内置 rate_limit.py |
| 审计日志 | request_logs 表，append-only |

## 客户端插件

| 插件 | 目录 |
|------|------|
| Claude Code | .claude-plugin/ |
| Codex | .codex-plugin/ |
| Cursor | .cursor-plugin/ |
| Kimi | .kimi-plugin/ |

## SDK

| 语言 | 安装 |
|------|------|
| Python | pip install mem0ai |
| TypeScript | npm install mem0ai |

## 环境变量

| 变量 | 必填 | 说明 |
|------|------|------|
| OPENAI_API_KEY | ✅ | LLM + 嵌入模型 |
| POSTGRES_PASSWORD | ✅ | 数据库密码 |
| JWT_SECRET | ✅ | JWT 签名密钥 |
| ADMIN_API_KEY | 可选 | 管理 API Key |
| ANTHROPIC_API_KEY | 可选 | Anthropic LLM |
| GOOGLE_API_KEY | 可选 | Google LLM |
| MEM0_TELEMETRY | 可选 | 遥测（默认 true） |

## 部署踩坑清单

1. **Docker Hub 完全不可达**：registry-1.docker.io 连接超时，需用 crane 工具从镜像源（docker.1ms.run）拉取基础镜像
2. **OrbStack 代理故障**：proxy.orb.internal:8305 返回 502 Bad Gateway，导致 docker daemon 拉取所有镜像失败
3. **解决方案**：brew install crane → crane pull docker.1ms.run/library/python:3.12 → docker load → docker tag
4. **pgvector 镜像复用**：本地已有 pgvector/pgvector:0.8.6-pg17-trixie（WeKnora 部署时拉取），tag 为 pg17 即可复用
5. **dashboard yarn install**：容器内网络不稳定 ECONNRESET，但 yarn 自动重试（--network-timeout 600000）可成功
6. **OPENAI_API_KEY 必填**：为空时 mem0 API 初始化失败（OpenAI 客户端报错），服务无法正常工作
7. **make bootstrap**：一键启动 + 创建 admin + 生成 API Key，但需先配置 OPENAI_API_KEY
