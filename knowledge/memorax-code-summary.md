# MemoraX Code 知识库摘要

## 项目概述

MemoraX Code 是一个为 Coding Agent 提供持久化记忆的 CLI 工具（npm 包）。它让 Codex、Claude Code、CodeBuddy CLI、WorkBuddy、DeepSeek Harness、OpenCode、Trae、Cursor 和 Qoder 共享一套能够持续积累的记忆系统，在后续任务中找回相关的工作流程和偏好。

核心理念：不是"记得更多"，而是在需要时带回与当前任务相关的 Memory，让 Agent 减少重复搜索和试错，更快进入问题定位与事实验证。

## 技术栈

| 维度 | 详情 |
|------|------|
| 语言 | TypeScript (target: ES2022, module: NodeNext) |
| 运行时 | Node.js >=20（推荐 Node.js 24 LTS） |
| 构建 | tsc → dist/（声明文件同步生成） |
| 包管理 | npm（package-lock.json） |
| 项目结构 | monorepo：packages/ts/（源码）+ packages/npm/（发布包） |
| 运行时依赖 | smol-toml@^1.8.0 |
| 开发依赖 | typescript@^5.9.0, @types/node@^20.0.0 |

## 仓库结构

```
memorax-code/
├── packages/
│   ├── ts/                          TypeScript 源码包
│   │   ├── memorax-code-backend/       核心 Backend（CLI 入口 + server）
│   │   ├── memorax-code-adapter-common/ 适配器公共库
│   │   ├── memorax-code-claude-adapter/  Claude Code 适配器
│   │   ├── memorax-code-codex-adapter/   Codex 适配器
│   │   ├── memorax-code-codebuddy-adapter/ CodeBuddy 适配器
│   │   ├── memorax-code-cursor-adapter/  Cursor 适配器
│   │   ├── memorax-code-dsh-adapter/     DeepSeek Harness 适配器
│   │   ├── memorax-code-opencode-adapter/ OpenCode 适配器
│   │   ├── memorax-code-qoder-adapter/   Qoder 适配器
│   │   └── memorax-code-trae-adapter/    Trae 适配器
│   └── npm/
│       └── memorax-code/               npm 发布包 staging
├── scripts/                          构建/CI/检查脚本
├── docs/                             文档（configuration.md, troubleshooting.md）
├── test/                             共享测试
├── Makefile                          测试与构建入口
├── README.md / README.zh.md          英文/中文文档
├── ARCHITECTURE.md                   架构文档
├── CONTRIBUTING.md                   贡献指南
└── SECURITY.md                       安全策略
```

## 四类 Memory

| Memory 类型 | 回答的问题 | 典型内容 |
|-------------|-----------|---------|
| Coding Memory | 哪些工程经验值得带入下一次任务？ | 已验证的修复、失败方案、设计依据、常见陷阱 |
| Repo Memory | Agent 需要了解这个仓库的哪些信息？ | 架构地图、模块职责、代码入口、Commit/PR/Issue |
| Personal Memory | Agent 应该如何与你沟通和协作？ | 语言、语气、解释深度、结果呈现偏好 |
| Procedure Memory | 这类任务应该如何执行？ | 可复用步骤、检查清单、前置条件、验证要求 |

## 产品能力

- **后台写入记忆**：任务完成后在后台提取可复用知识并写入 Coding Memory
- **用户偏好延续**：在 User Profile 中记录偏好，按设定周期带入后续任务
- **Procedure 自动复用**：记录可复用流程并在后续任务中自动提醒
- **记忆作用反馈**：当记忆指导了任务时，Agent 在回复开头简要说明
- **Repo Memory 后台整理**：基于本地默认分支维护共享基线
- **主动记忆控制**：通过 Skill 或 CLI 主动查找和添加记忆
- **本地可观测性**：通过受内容控制的 trace 和 reconciliation 记录查看活动统计

## CLI 命令

| 命令 | 用途 |
|------|------|
| `npm install -g @memorax/memorax-code` | 全局安装 |
| `memorax-code setup --existing-account` | 已有账号安装引导 |
| `memorax-code setup` | 游客模式（90天） |
| `memorax-code --version` | 查看版本 |
| `memorax-code status` | 检查本地 Backend 和客户端集成 |
| `memorax-cli status` | 检查本地记忆配置和工作区作用域 |
| `memorax-code update` | 更新 |
| `memorax-code uninstall` | 卸载 |

## 支持的客户端

Codex、Claude Code、CodeBuddy CLI、WorkBuddy、DeepSeek Harness (DSH)、OpenCode、Trae、Cursor、Qoder

## 配置位置

| 路径 | 用途 |
|------|------|
| `~/.memorax-code/config.toml` | 主配置（含 API Key） |
| `~/.memorax-code/personal-memory/` | 个人记忆 |
| `MEMORAX_CODE_HOME`（环境变量） | 自定义配置根目录 |

## 部署踩坑清单

1. **HTTPS 克隆超时**：github.com HTTPS 443 端口连接超时，需改用 SSH 协议 `git@github.com:memorax-ai/memorax-code.git`
2. **tsc 不在 PATH**：`npm run build` 调用 `tsc` 报 command not found，需用 `npx tsc` 或确保 devDependencies bin 链接生效
3. **Node 版本要求**：项目 .node-version 指定 24.22.1，engines 要求 >=20；DSH 适配器额外要求 ^22.19.0 || >=24.0.0
4. **Linux libsecret 依赖**：Linux 下游客凭据管理需要 libsecret 提供的 `/usr/bin/secret-tool`
5. **Cursor SQLite 要求**：Cursor 自动 Add 需要带内置 SQLite 的 Node.js 22.13+
6. **Trae 手动开关**：Trae 的 Global Hooks 需手动在 设置 → Hooks → 全局 → 已配置的 Hooks 中开启
7. **DSH 初始化**：使用 DSH 前需先安装/初始化并创建至少一个 Profile；桌面版需先打开一次再完全退出
8. **pnpm 依赖**：使用 npm CLI 时需确保 `pnpm` 在 PATH 中可用
